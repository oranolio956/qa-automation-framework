#!/usr/bin/env python3
"""
Database Models and Operations for Telegram Bot
Handles all database interactions for users, orders, payments, and analytics
"""

import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from decimal import Decimal
import logging
from contextlib import asynccontextmanager

import asyncpg
import redis.asyncio as redis
from pydantic import BaseModel, validator

from .config import TelegramBotConfig, OrderStatus, ServiceType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Async database manager for PostgreSQL and Redis with ACID transaction support"""
    
    def __init__(self):
        self.postgres_pool = None
        self.redis_client = None
        self._connection_lock = asyncio.Lock()
        self._pool_ready = asyncio.Event()
        
    async def initialize(self):
        """Initialize database connections with proper connection pooling"""
        try:
            async with self._connection_lock:
                # PostgreSQL connection pool with ACID transaction support
                self.postgres_pool = await asyncpg.create_pool(
                    TelegramBotConfig.DATABASE_URL,
                    min_size=5,
                    max_size=20,
                    command_timeout=60,
                    server_settings={
                        'application_name': 'tinder_bot',
                        'jit': 'off'  # Disable JIT for consistent performance
                    },
                    # Connection factory for transaction isolation
                    init=self._init_connection
                )
            
                # Redis connection with proper connection pooling
                self.redis_client = redis.from_url(
                    TelegramBotConfig.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                    max_connections=20,
                    socket_keepalive=True,
                    socket_keepalive_options={1: 1, 2: 3, 3: 5},
                    retry_on_timeout=True,
                    health_check_interval=30
                )
            
                # Create tables with transaction support
                await self.create_tables()
                
                # Signal that pool is ready
                self._pool_ready.set()
                
                logger.info("✅ Database connections initialized with ACID transaction support")
                return True
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            return False
    
    async def create_tables(self):
        """Create database tables if they don't exist"""
        schema = """
        -- Users table
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username VARCHAR(32),
            first_name VARCHAR(64),
            last_name VARCHAR(64),
            language_code VARCHAR(10) DEFAULT 'en',
            created_at TIMESTAMP DEFAULT NOW(),
            last_active TIMESTAMP DEFAULT NOW(),
            is_premium BOOLEAN DEFAULT FALSE,
            is_banned BOOLEAN DEFAULT FALSE,
            referral_code VARCHAR(32) UNIQUE,
            referred_by_user_id BIGINT,
            total_spent DECIMAL(10,2) DEFAULT 0.00,
            total_orders INTEGER DEFAULT 0,
            success_rate DECIMAL(5,2) DEFAULT 0.00
        );
        
        -- Orders table  
        CREATE TABLE IF NOT EXISTS orders (
            order_id VARCHAR(32) PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(user_id),
            package_id VARCHAR(64) NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            status VARCHAR(32) NOT NULL DEFAULT 'pending_payment',
            total_amount DECIMAL(10,2) NOT NULL,
            discount_amount DECIMAL(10,2) DEFAULT 0.00,
            payment_method VARCHAR(32),
            payment_id VARCHAR(128),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            delivery_started_at TIMESTAMP,
            completed_at TIMESTAMP,
            expected_delivery TIMESTAMP,
            notes TEXT,
            automation_job_id VARCHAR(64),
            delivery_data JSONB,
            error_log TEXT
        );
        
        -- Payments table
        CREATE TABLE IF NOT EXISTS payments (
            payment_id VARCHAR(128) PRIMARY KEY,
            order_id VARCHAR(32) NOT NULL REFERENCES orders(order_id),
            user_id BIGINT NOT NULL REFERENCES users(user_id),
            amount DECIMAL(10,2) NOT NULL,
            currency VARCHAR(3) DEFAULT 'USD',
            provider VARCHAR(32) NOT NULL,
            provider_payment_id VARCHAR(128),
            status VARCHAR(32) NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            webhook_data JSONB,
            retry_count INTEGER DEFAULT 0,
            last_retry_at TIMESTAMP
        );
        
        -- Account deliveries table
        CREATE TABLE IF NOT EXISTS account_deliveries (
            delivery_id VARCHAR(32) PRIMARY KEY,
            order_id VARCHAR(32) NOT NULL REFERENCES orders(order_id),
            user_id BIGINT NOT NULL REFERENCES users(user_id),
            account_type VARCHAR(32) NOT NULL,
            account_data JSONB NOT NULL,
            delivered_at TIMESTAMP DEFAULT NOW(),
            is_working BOOLEAN DEFAULT TRUE,
            quality_score INTEGER DEFAULT 100,
            replacement_count INTEGER DEFAULT 0,
            last_checked TIMESTAMP DEFAULT NOW()
        );
        
        -- Referrals table
        CREATE TABLE IF NOT EXISTS referrals (
            referral_id SERIAL PRIMARY KEY,
            referrer_user_id BIGINT NOT NULL REFERENCES users(user_id),
            referred_user_id BIGINT NOT NULL REFERENCES users(user_id),
            order_id VARCHAR(32) REFERENCES orders(order_id),
            bonus_amount DECIMAL(10,2) NOT NULL,
            status VARCHAR(32) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT NOW(),
            paid_at TIMESTAMP,
            UNIQUE(referrer_user_id, referred_user_id)
        );
        
        -- Bot analytics table
        CREATE TABLE IF NOT EXISTS analytics (
            event_id SERIAL PRIMARY KEY,
            event_type VARCHAR(64) NOT NULL,
            user_id BIGINT,
            order_id VARCHAR(32),
            event_data JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        -- Indexes for performance
        CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
        CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
        CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);
        CREATE INDEX IF NOT EXISTS idx_payments_order_id ON payments(order_id);
        CREATE INDEX IF NOT EXISTS idx_analytics_user_id ON analytics(user_id);
        CREATE INDEX IF NOT EXISTS idx_analytics_event_type ON analytics(event_type);
        """
        
        async with self.postgres_pool.acquire() as connection:
            await connection.execute(schema)
        
        logger.info("✅ Database tables created/verified")
    
    async def _init_connection(self, connection):
        """Initialize database connection with proper settings"""
        await connection.set_type_codec(
            'json',
            encoder=json.dumps,
            decoder=json.loads,
            schema='pg_catalog'
        )
    
    @asynccontextmanager
    async def transaction(self):
        """ACID transaction context manager with proper rollback"""
        # Wait for pool to be ready
        await self._pool_ready.wait()
        
        async with self.postgres_pool.acquire() as connection:
            async with connection.transaction():
                try:
                    yield connection
                except Exception as e:
                    logger.error(f"Transaction failed, rolling back: {e}")
                    raise
    
    @asynccontextmanager 
    async def redis_pipeline(self):
        """Redis pipeline for atomic operations"""
        pipeline = self.redis_client.pipeline()
        try:
            yield pipeline
            await pipeline.execute()
        except Exception as e:
            logger.error(f"Redis pipeline failed: {e}")
            raise
    
    async def health_check(self) -> Dict[str, bool]:
        """Check database connection health"""
        health = {'postgres': False, 'redis': False}
        
        try:
            # Check PostgreSQL
            async with self.postgres_pool.acquire() as conn:
                await conn.fetchval('SELECT 1')
            health['postgres'] = True
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
        
        try:
            # Check Redis
            await self.redis_client.ping()
            health['redis'] = True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
        
        return health

class UserManager:
    """Manages user data and operations"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    async def create_or_update_user(self, user_data: dict) -> bool:
        """Create or update user from Telegram data with ACID transaction"""
        try:
            user_id = user_data['id']
            username = user_data.get('username')
            first_name = user_data.get('first_name', '')
            last_name = user_data.get('last_name', '')
            language_code = user_data.get('language_code', 'en')
            
            # Generate referral code if new user
            referral_code = self._generate_referral_code(user_id)
            
            query = """
            INSERT INTO users (user_id, username, first_name, last_name, language_code, referral_code)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (user_id) DO UPDATE SET
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                language_code = EXCLUDED.language_code,
                last_active = NOW()
            """
            
            # Use ACID transaction for data consistency
            async with self.db.transaction() as connection:
                await connection.execute(
                    query, user_id, username, first_name, 
                    last_name, language_code, referral_code
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating/updating user {user_data.get('id')}: {e}")
            return False
    
    async def get_user(self, user_id: int) -> Optional[dict]:
        """Get user data"""
        try:
            query = "SELECT * FROM users WHERE user_id = $1"
            async with self.db.postgres_pool.acquire() as connection:
                result = await connection.fetchrow(query, user_id)
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    async def update_user_referral(self, user_id: int, referred_by_code: str) -> bool:
        """Update user's referral relationship"""
        try:
            # Find referrer by code
            referrer_query = "SELECT user_id FROM users WHERE referral_code = $1"
            async with self.db.postgres_pool.acquire() as connection:
                referrer = await connection.fetchrow(referrer_query, referred_by_code)
                
                if not referrer:
                    return False
                
                # Update referred user
                update_query = """
                UPDATE users SET referred_by_user_id = $1 
                WHERE user_id = $2 AND referred_by_user_id IS NULL
                """
                result = await connection.execute(update_query, referrer['user_id'], user_id)
                
                return "UPDATE 1" in str(result)
                
        except Exception as e:
            logger.error(f"Error updating referral for user {user_id}: {e}")
            return False
    
    async def get_user_stats(self, user_id: int) -> dict:
        """Get user statistics"""
        try:
            query = """
            SELECT 
                u.total_orders,
                u.total_spent,
                u.success_rate,
                COUNT(o.order_id) as pending_orders,
                COUNT(r.referral_id) as referrals_made,
                COALESCE(SUM(r.bonus_amount), 0) as referral_earnings
            FROM users u
            LEFT JOIN orders o ON u.user_id = o.user_id AND o.status IN ('pending_payment', 'in_progress')
            LEFT JOIN referrals r ON u.user_id = r.referrer_user_id AND r.status = 'paid'
            WHERE u.user_id = $1
            GROUP BY u.user_id, u.total_orders, u.total_spent, u.success_rate
            """
            
            async with self.db.postgres_pool.acquire() as connection:
                result = await connection.fetchrow(query, user_id)
                return dict(result) if result else {}
                
        except Exception as e:
            logger.error(f"Error getting user stats {user_id}: {e}")
            return {}
    
    def _generate_referral_code(self, user_id: int) -> str:
        """Generate unique referral code"""
        raw = f"tinder_bot_{user_id}_{datetime.now().timestamp()}"
        hash_obj = hashlib.md5(raw.encode())
        return f"REF{hash_obj.hexdigest()[:8].upper()}"

class OrderManager:
    """Manages orders and delivery tracking"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    async def create_order(self, user_id: int, package_id: str, quantity: int = 1) -> Optional[str]:
        """Create new order"""
        try:
            # Generate order ID
            order_id = self._generate_order_id()
            
            # Calculate pricing
            package = TelegramBotConfig.get_package(package_id)
            if not package:
                return None
            
            total_amount, discount_amount = TelegramBotConfig.get_total_price(package_id, quantity)
            expected_delivery = datetime.now() + timedelta(hours=package.delivery_time_hours)
            
            query = """
            INSERT INTO orders (
                order_id, user_id, package_id, quantity, 
                total_amount, discount_amount, expected_delivery, status
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """
            
            async with self.db.postgres_pool.acquire() as connection:
                await connection.execute(
                    query, order_id, user_id, package_id, quantity,
                    total_amount, discount_amount, expected_delivery, 'pending_payment'
                )
            
            # Track analytics
            await self._track_event('order_created', user_id, order_id, {
                'package_id': package_id,
                'quantity': quantity,
                'total_amount': float(total_amount)
            })
            
            return order_id
            
        except Exception as e:
            logger.error(f"Error creating order for user {user_id}: {e}")
            return None
    
    async def update_order_status(self, order_id: str, status: str, notes: str = None) -> bool:
        """Update order status"""
        try:
            query = """
            UPDATE orders 
            SET status = $1, updated_at = NOW(), notes = COALESCE($2, notes)
            WHERE order_id = $3
            """
            
            async with self.db.postgres_pool.acquire() as connection:
                result = await connection.execute(query, status, notes, order_id)
                
            # Update delivery timestamps
            if status == 'in_progress':
                await self._update_delivery_started(order_id)
            elif status == 'completed':
                await self._update_completed(order_id)
            
            return "UPDATE 1" in str(result)
            
        except Exception as e:
            logger.error(f"Error updating order status {order_id}: {e}")
            return False
    
    async def get_user_orders(self, user_id: int, limit: int = 10) -> List[dict]:
        """Get user's orders"""
        try:
            query = """
            SELECT o.*, 
                   COUNT(ad.delivery_id) as accounts_delivered
            FROM orders o
            LEFT JOIN account_deliveries ad ON o.order_id = ad.order_id
            WHERE o.user_id = $1
            GROUP BY o.order_id
            ORDER BY o.created_at DESC
            LIMIT $2
            """
            
            async with self.db.postgres_pool.acquire() as connection:
                results = await connection.fetch(query, user_id, limit)
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error(f"Error getting orders for user {user_id}: {e}")
            return []
    
    async def get_order(self, order_id: str) -> Optional[dict]:
        """Get specific order"""
        try:
            query = "SELECT * FROM orders WHERE order_id = $1"
            async with self.db.postgres_pool.acquire() as connection:
                result = await connection.fetchrow(query, order_id)
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting order {order_id}: {e}")
            return None
    
    async def start_automation_job(self, order_id: str) -> bool:
        """Start automation job for order"""
        try:
            order = await self.get_order(order_id)
            if not order:
                return False
            
            # Import automation orchestrator
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
            from main_orchestrator import TinderAutomationOrchestrator, AutomationConfig
            
            # Create automation config from order
            package = TelegramBotConfig.get_package(order['package_id'])
            config = AutomationConfig(
                tinder_account_count=package.tinder_accounts * order['quantity'],
                snapchat_account_count=package.snapchat_accounts * order['quantity'],
                emulator_count=min(package.tinder_accounts * order['quantity'], 5),
                aggressiveness_level=0.3,
                warming_enabled=True,
                parallel_creation=True,
                output_directory=f"./automation_results/{order_id}",
                headless_emulators=True
            )
            
            # Start automation in background
            job_id = f"automation_{order_id}_{int(datetime.now().timestamp())}"
            
            # Update order with job ID
            await self.update_order_automation_job(order_id, job_id)
            
            # TODO: Start automation job asynchronously
            # For now, mark as in_progress
            await self.update_order_status(order_id, 'in_progress')
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting automation job for order {order_id}: {e}")
            return False
    
    async def update_order_automation_job(self, order_id: str, job_id: str) -> bool:
        """Update order with automation job ID"""
        try:
            query = "UPDATE orders SET automation_job_id = $1 WHERE order_id = $2"
            async with self.db.postgres_pool.acquire() as connection:
                await connection.execute(query, job_id, order_id)
            return True
        except Exception as e:
            logger.error(f"Error updating automation job for order {order_id}: {e}")
            return False
    
    async def _update_delivery_started(self, order_id: str):
        """Update delivery started timestamp"""
        query = "UPDATE orders SET delivery_started_at = NOW() WHERE order_id = $1"
        async with self.db.postgres_pool.acquire() as connection:
            await connection.execute(query, order_id)
    
    async def _update_completed(self, order_id: str):
        """Update completed timestamp"""
        query = "UPDATE orders SET completed_at = NOW() WHERE order_id = $1"
        async with self.db.postgres_pool.acquire() as connection:
            await connection.execute(query, order_id)
    
    async def _track_event(self, event_type: str, user_id: int, order_id: str = None, data: dict = None):
        """Track analytics event"""
        try:
            query = """
            INSERT INTO analytics (event_type, user_id, order_id, event_data)
            VALUES ($1, $2, $3, $4)
            """
            async with self.db.postgres_pool.acquire() as connection:
                await connection.execute(
                    query, event_type, user_id, order_id, 
                    json.dumps(data) if data else None
                )
        except Exception as e:
            logger.error(f"Error tracking event {event_type}: {e}")
    
    def _generate_order_id(self) -> str:
        """Generate unique order ID"""
        timestamp = int(datetime.now().timestamp())
        return f"ORD{timestamp}"

class PaymentManager:
    """Manages payments and webhook processing"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    async def create_payment(self, order_id: str, user_id: int, amount: float, provider: str) -> str:
        """Create payment record"""
        try:
            payment_id = f"PAY_{order_id}_{int(datetime.now().timestamp())}"
            
            query = """
            INSERT INTO payments (payment_id, order_id, user_id, amount, provider, status)
            VALUES ($1, $2, $3, $4, $5, 'pending')
            """
            
            async with self.db.postgres_pool.acquire() as connection:
                await connection.execute(query, payment_id, order_id, user_id, amount, provider)
            
            return payment_id
            
        except Exception as e:
            logger.error(f"Error creating payment for order {order_id}: {e}")
            return None
    
    async def update_payment_status(self, payment_id: str, status: str, provider_payment_id: str = None) -> bool:
        """Update payment status"""
        try:
            query = """
            UPDATE payments 
            SET status = $1, provider_payment_id = COALESCE($2, provider_payment_id), updated_at = NOW()
            WHERE payment_id = $3
            """
            
            async with self.db.postgres_pool.acquire() as connection:
                result = await connection.execute(query, status, provider_payment_id, payment_id)
            
            # If payment successful, update order
            if status == 'completed':
                await self._process_successful_payment(payment_id)
            
            return "UPDATE 1" in str(result)
            
        except Exception as e:
            logger.error(f"Error updating payment status {payment_id}: {e}")
            return False
    
    async def _process_successful_payment(self, payment_id: str):
        """Process successful payment"""
        try:
            # Get payment and order info
            query = """
            SELECT p.order_id, p.user_id, p.amount, o.package_id, o.quantity
            FROM payments p
            JOIN orders o ON p.order_id = o.order_id
            WHERE p.payment_id = $1
            """
            
            async with self.db.postgres_pool.acquire() as connection:
                payment_data = await connection.fetchrow(query, payment_id)
            
            if not payment_data:
                return
            
            # Update order status
            order_manager = OrderManager(self.db)
            await order_manager.update_order_status(payment_data['order_id'], 'payment_confirmed')
            
            # Start automation job
            await order_manager.start_automation_job(payment_data['order_id'])
            
            # Process referral bonus if applicable
            await self._process_referral_bonus(payment_data['user_id'], payment_data['order_id'], payment_data['amount'])
            
        except Exception as e:
            logger.error(f"Error processing successful payment {payment_id}: {e}")
    
    async def _process_referral_bonus(self, user_id: int, order_id: str, amount: float):
        """Process referral bonus"""
        try:
            # Check if user was referred
            query = "SELECT referred_by_user_id FROM users WHERE user_id = $1 AND referred_by_user_id IS NOT NULL"
            async with self.db.postgres_pool.acquire() as connection:
                referrer = await connection.fetchrow(query, user_id)
            
            if not referrer:
                return
            
            # Calculate bonus
            if amount >= TelegramBotConfig.MIN_REFERRAL_AMOUNT:
                bonus_amount = amount * (TelegramBotConfig.REFERRAL_BONUS_PERCENTAGE / 100)
                
                # Create referral record
                referral_query = """
                INSERT INTO referrals (referrer_user_id, referred_user_id, order_id, bonus_amount, status)
                VALUES ($1, $2, $3, $4, 'pending')
                """
                
                await connection.execute(
                    referral_query, referrer['referred_by_user_id'], 
                    user_id, order_id, bonus_amount
                )
                
                logger.info(f"Referral bonus ${bonus_amount:.2f} created for user {referrer['referred_by_user_id']}")
        
        except Exception as e:
            logger.error(f"Error processing referral bonus: {e}")

# Global database instance
_db_manager = None

async def get_database() -> DatabaseManager:
    """Get global database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        await _db_manager.initialize()
    return _db_manager

# Initialize managers
async def get_user_manager() -> UserManager:
    """Get user manager instance"""
    db = await get_database()
    return UserManager(db)

async def get_order_manager() -> OrderManager:
    """Get order manager instance"""
    db = await get_database()
    return OrderManager(db)

async def get_payment_manager() -> PaymentManager:
    """Get payment manager instance"""
    db = await get_database()
    return PaymentManager(db)

if __name__ == "__main__":
    # Test database operations
    async def test_db():
        db = await get_database()
        user_mgr = await get_user_manager()
        order_mgr = await get_order_manager()
        
        # Test user creation
        test_user = {
            'id': 123456,
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        await user_mgr.create_or_update_user(test_user)
        user = await user_mgr.get_user(123456)
        print(f"Created user: {user}")
        
        # Test order creation
        order_id = await order_mgr.create_order(123456, 'starter_pack', 1)
        print(f"Created order: {order_id}")
        
        print("✅ Database tests completed")
    
    asyncio.run(test_db())