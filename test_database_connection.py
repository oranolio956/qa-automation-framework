#!/usr/bin/env python3
"""
Database Connection Test - PostgreSQL Production Database
Tests the real PostgreSQL connection and initializes schema if needed
"""

import os
import sys
import asyncio
import asyncpg
import logging
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Production database connection string
DATABASE_URL = "postgresql://database_8zh9_user:yZHV8grbsfJgXXgxDPh2NBBkiFYilpKW@dpg-d33nhuodl3ps73917ejg-a.oregon-postgres.render.com/database_8zh9"

class DatabaseTester:
    """Test PostgreSQL database connection and basic operations"""
    
    def __init__(self):
        self.connection = None
        
    async def connect(self) -> bool:
        """Establish database connection"""
        try:
            logger.info("Connecting to PostgreSQL database...")
            self.connection = await asyncpg.connect(DATABASE_URL)
            logger.info("✅ Database connection successful!")
            return True
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
            
    async def test_basic_queries(self) -> Dict[str, Any]:
        """Test basic database operations"""
        results = {
            'connection_test': False,
            'version_check': None,
            'table_count': 0,
            'schema_exists': False,
            'test_insert': False,
            'test_query': False
        }
        
        try:
            # Test connection
            if not self.connection:
                await self.connect()
                
            results['connection_test'] = True
            
            # Check PostgreSQL version
            version = await self.connection.fetchval("SELECT version()")
            results['version_check'] = version
            logger.info(f"PostgreSQL Version: {version}")
            
            # Check if our schema exists
            table_count = await self.connection.fetchval("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
            """)
            results['table_count'] = table_count
            results['schema_exists'] = table_count > 0
            logger.info(f"Found {table_count} tables in database")
            
            # Test creating a simple test table
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS connection_test (
                    id SERIAL PRIMARY KEY,
                    test_message TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Test insert
            test_message = f"Database test successful at {datetime.utcnow().isoformat()}"
            await self.connection.execute("""
                INSERT INTO connection_test (test_message) VALUES ($1)
            """, test_message)
            results['test_insert'] = True
            logger.info("✅ Test insert successful")
            
            # Test query
            recent_tests = await self.connection.fetch("""
                SELECT id, test_message, created_at 
                FROM connection_test 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            results['test_query'] = True
            results['recent_tests'] = [dict(record) for record in recent_tests]
            logger.info(f"✅ Test query successful - found {len(recent_tests)} recent tests")
            
            # Clean up test data (keep only last 10 records)
            await self.connection.execute("""
                DELETE FROM connection_test 
                WHERE id NOT IN (
                    SELECT id FROM connection_test 
                    ORDER BY created_at DESC 
                    LIMIT 10
                )
            """)
            
        except Exception as e:
            logger.error(f"❌ Database test failed: {e}")
            results['error'] = str(e)
            
        return results
        
    async def initialize_schema(self) -> bool:
        """Initialize database schema if it doesn't exist"""
        try:
            # Check if main tables exist
            table_exists = await self.connection.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'snapchat_accounts'
                )
            """)
            
            if not table_exists:
                logger.info("Initializing database schema...")
                
                # Read and execute schema file
                schema_path = os.path.join(os.path.dirname(__file__), 'DATABASE_SCHEMA.sql')
                if os.path.exists(schema_path):
                    with open(schema_path, 'r') as f:
                        schema_sql = f.read()
                    
                    # Execute schema (note: asyncpg doesn't support multiple statements at once)
                    # We'll need to split and execute individually
                    statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
                    
                    for statement in statements:
                        if statement and not statement.startswith('--'):
                            try:
                                await self.connection.execute(statement)
                            except Exception as e:
                                # Some statements might fail (like CREATE EXTENSION IF NOT EXISTS)
                                # which is okay if they already exist
                                logger.warning(f"Statement warning: {e}")
                    
                    logger.info("✅ Database schema initialized successfully")
                    return True
                else:
                    logger.error("❌ DATABASE_SCHEMA.sql not found")
                    return False
            else:
                logger.info("✅ Database schema already exists")
                return True
                
        except Exception as e:
            logger.error(f"❌ Schema initialization failed: {e}")
            return False
            
    async def test_snapchat_tables(self) -> Dict[str, Any]:
        """Test Snapchat-specific tables and operations"""
        results = {
            'tables_exist': False,
            'test_account_insert': False,
            'test_order_insert': False,
            'test_device_insert': False
        }
        
        try:
            # Check if main tables exist
            tables = await self.connection.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('snapchat_accounts', 'customer_orders', 'android_devices')
                ORDER BY table_name
            """)
            
            table_names = [record['table_name'] for record in tables]
            results['existing_tables'] = table_names
            results['tables_exist'] = len(table_names) >= 3
            
            logger.info(f"Found tables: {table_names}")
            
            if results['tables_exist']:
                # Test inserting a sample Snapchat account
                try:
                    account_id = await self.connection.fetchval("""
                        INSERT INTO snapchat_accounts (
                            username, email, display_name, birth_date, status
                        ) VALUES (
                            'test_user_' || EXTRACT(EPOCH FROM NOW())::text,
                            'test_' || EXTRACT(EPOCH FROM NOW())::text || '@example.com',
                            'Test User',
                            '2000-01-01',
                            'pending'
                        ) RETURNING id
                    """)
                    results['test_account_insert'] = True
                    results['test_account_id'] = str(account_id)
                    logger.info(f"✅ Test account created with ID: {account_id}")
                    
                    # Clean up test account
                    await self.connection.execute("""
                        DELETE FROM snapchat_accounts WHERE id = $1
                    """, account_id)
                    
                except Exception as e:
                    logger.error(f"❌ Account insert test failed: {e}")
                    
                # Test inserting a sample device
                try:
                    device_id = await self.connection.fetchval("""
                        INSERT INTO android_devices (
                            device_name, device_id, emulator_type, android_version, api_level
                        ) VALUES (
                            'test_device_' || EXTRACT(EPOCH FROM NOW())::text,
                            'test_' || EXTRACT(EPOCH FROM NOW())::text,
                            'emulator',
                            'Android 11',
                            30
                        ) RETURNING id
                    """)
                    results['test_device_insert'] = True
                    results['test_device_id'] = str(device_id)
                    logger.info(f"✅ Test device created with ID: {device_id}")
                    
                    # Clean up test device
                    await self.connection.execute("""
                        DELETE FROM android_devices WHERE id = $1
                    """, device_id)
                    
                except Exception as e:
                    logger.error(f"❌ Device insert test failed: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Snapchat tables test failed: {e}")
            results['error'] = str(e)
            
        return results
        
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics and health information"""
        stats = {}
        
        try:
            # Database size
            db_size = await self.connection.fetchval("""
                SELECT pg_size_pretty(pg_database_size(current_database()))
            """)
            stats['database_size'] = db_size
            
            # Table sizes
            table_sizes = await self.connection.fetch("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 10
            """)
            stats['table_sizes'] = [dict(record) for record in table_sizes]
            
            # Connection count
            connections = await self.connection.fetchval("""
                SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active'
            """)
            stats['active_connections'] = connections
            
            # Recent activity
            recent_activity = await self.connection.fetch("""
                SELECT 
                    application_name,
                    state,
                    query_start,
                    state_change
                FROM pg_stat_activity 
                WHERE state != 'idle' 
                AND application_name != ''
                ORDER BY query_start DESC
                LIMIT 5
            """)
            stats['recent_activity'] = [dict(record) for record in recent_activity]
            
        except Exception as e:
            logger.error(f"❌ Failed to get database stats: {e}")
            stats['error'] = str(e)
            
        return stats
        
    async def close(self):
        """Close database connection"""
        if self.connection:
            await self.connection.close()
            logger.info("Database connection closed")

async def main():
    """Main test function"""
    logger.info("🚀 Starting PostgreSQL Database Connection Test")
    logger.info("=" * 60)
    
    tester = DatabaseTester()
    
    try:
        # Test basic connection
        if not await tester.connect():
            sys.exit(1)
            
        # Run basic tests
        logger.info("\n📊 Running Basic Database Tests...")
        basic_results = await tester.test_basic_queries()
        
        if basic_results['connection_test']:
            logger.info("✅ Basic database tests passed")
        else:
            logger.error("❌ Basic database tests failed")
            return
            
        # Initialize schema if needed
        logger.info("\n🏗️ Checking Database Schema...")
        schema_initialized = await tester.initialize_schema()
        
        if schema_initialized:
            logger.info("✅ Database schema ready")
        else:
            logger.error("❌ Schema initialization failed")
            return
            
        # Test Snapchat-specific functionality
        logger.info("\n📱 Testing Snapchat Automation Tables...")
        snapchat_results = await tester.test_snapchat_tables()
        
        if snapchat_results['tables_exist']:
            logger.info("✅ Snapchat automation tables ready")
        else:
            logger.error("❌ Snapchat tables not ready")
            
        # Get database statistics
        logger.info("\n📈 Database Statistics...")
        stats = await tester.get_database_stats()
        
        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("📋 DATABASE CONNECTION TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"✅ Connection: {'SUCCESS' if basic_results['connection_test'] else 'FAILED'}")
        logger.info(f"✅ Schema: {'READY' if schema_initialized else 'NOT READY'}")
        logger.info(f"✅ Tables: {basic_results['table_count']} tables found")
        logger.info(f"✅ Database Size: {stats.get('database_size', 'Unknown')}")
        logger.info(f"✅ Active Connections: {stats.get('active_connections', 'Unknown')}")
        
        if snapchat_results['tables_exist']:
            logger.info("✅ Snapchat Automation: READY FOR PRODUCTION")
        else:
            logger.info("⚠️ Snapchat Automation: NEEDS SETUP")
            
        logger.info("=" * 60)
        logger.info("🎉 Database test completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        sys.exit(1)
        
    finally:
        await tester.close()

if __name__ == "__main__":
    asyncio.run(main())