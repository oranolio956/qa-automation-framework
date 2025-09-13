#!/usr/bin/env python3
"""
Webhook Server for Telegram Bot
Handles payment webhooks and bot updates via webhooks instead of polling
"""

import asyncio
import logging
import json
from typing import Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn
from telegram import Update
from telegram.ext import ContextTypes

from .config import TelegramBotConfig
from .main_bot import TinderBotApplication
from .payment_handler import get_payment_processor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebhookServer:
    """FastAPI webhook server for handling payments and bot updates"""
    
    def __init__(self, bot_app: TinderBotApplication):
        self.bot_app = bot_app
        self.payment_processor = get_payment_processor()
        self.app = FastAPI(
            title="Tinder Bot Webhook Server",
            description="Handles payment webhooks and Telegram bot updates",
            version="1.0.0"
        )
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/")
        async def root():
            return {"status": "Tinder Bot Webhook Server", "timestamp": datetime.now().isoformat()}
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "bot_running": self.bot_app.application is not None
            }
        
        @self.app.post("/webhook/telegram")
        async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
            """Handle Telegram bot webhooks"""
            try:
                # Get update data
                data = await request.json()
                update = Update.de_json(data, self.bot_app.application.bot)
                
                if update:
                    # Process update in background
                    background_tasks.add_task(self._process_telegram_update, update)
                    return {"status": "ok"}
                else:
                    raise HTTPException(status_code=400, detail="Invalid update data")
                    
            except Exception as e:
                logger.error(f"Error processing Telegram webhook: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.post("/webhook/stripe")
        async def stripe_webhook(request: Request, background_tasks: BackgroundTasks):
            """Handle Stripe payment webhooks"""
            try:
                # Get raw body and signature
                body = await request.body()
                signature = request.headers.get('stripe-signature')
                
                if not signature:
                    raise HTTPException(status_code=400, detail="Missing signature")
                
                # Process webhook in background
                background_tasks.add_task(self._process_stripe_webhook, body, signature)
                return {"status": "ok"}
                
            except Exception as e:
                logger.error(f"Error processing Stripe webhook: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.post("/webhook/payment/success")
        async def payment_success_webhook(request: Request, background_tasks: BackgroundTasks):
            """Handle payment success notifications from other providers"""
            try:
                data = await request.json()
                
                # Validate webhook data
                required_fields = ['order_id', 'payment_id', 'amount', 'provider']
                if not all(field in data for field in required_fields):
                    raise HTTPException(status_code=400, detail="Missing required fields")
                
                # Process payment success
                background_tasks.add_task(self._process_payment_success, data)
                return {"status": "ok"}
                
            except Exception as e:
                logger.error(f"Error processing payment success webhook: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.post("/webhook/automation/status")
        async def automation_status_webhook(request: Request, background_tasks: BackgroundTasks):
            """Handle automation system status updates"""
            try:
                data = await request.json()
                
                # Validate webhook data
                required_fields = ['order_id', 'status', 'timestamp']
                if not all(field in data for field in required_fields):
                    raise HTTPException(status_code=400, detail="Missing required fields")
                
                # Process automation status update
                background_tasks.add_task(self._process_automation_status, data)
                return {"status": "ok"}
                
            except Exception as e:
                logger.error(f"Error processing automation status webhook: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.get("/admin/stats")
        async def admin_stats():
            """Get system statistics (admin only)"""
            try:
                # In production, add authentication here
                stats = await self._get_system_stats()
                return stats
            except Exception as e:
                logger.error(f"Error getting admin stats: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.post("/admin/broadcast")
        async def admin_broadcast(request: Request, background_tasks: BackgroundTasks):
            """Send broadcast message (admin only)"""
            try:
                # In production, add authentication here
                data = await request.json()
                
                required_fields = ['message', 'target_group']
                if not all(field in data for field in required_fields):
                    raise HTTPException(status_code=400, detail="Missing required fields")
                
                # Process broadcast in background
                background_tasks.add_task(self._process_broadcast, data)
                return {"status": "broadcast_scheduled"}
                
            except Exception as e:
                logger.error(f"Error processing broadcast: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
    
    async def _process_telegram_update(self, update: Update):
        """Process Telegram update"""
        try:
            # Create context
            context = ContextTypes.DEFAULT_TYPE(
                application=self.bot_app.application,
                chat_id=update.effective_chat.id if update.effective_chat else None,
                user_id=update.effective_user.id if update.effective_user else None
            )
            
            # Process update through bot application
            await self.bot_app.application.process_update(update)
            
        except Exception as e:
            logger.error(f"Error processing Telegram update: {e}")
    
    async def _process_stripe_webhook(self, body: bytes, signature: str):
        """Process Stripe webhook"""
        try:
            result = await self.payment_processor.handle_stripe_webhook(body, signature)
            
            if not result['success']:
                logger.error(f"Stripe webhook processing failed: {result['error']}")
            else:
                logger.info(f"Stripe webhook processed: {result['processed']}")
                
        except Exception as e:
            logger.error(f"Error processing Stripe webhook: {e}")
    
    async def _process_payment_success(self, data: Dict[str, Any]):
        """Process payment success notification"""
        try:
            order_id = data['order_id']
            payment_id = data['payment_id']
            amount = data['amount']
            provider = data['provider']
            
            # Update payment status
            from .database import get_payment_manager
            payment_mgr = await get_payment_manager()
            
            await payment_mgr.update_payment_status(
                payment_id, 'completed', data.get('provider_payment_id')
            )
            
            logger.info(f"Payment success processed: {payment_id} for order {order_id}")
            
        except Exception as e:
            logger.error(f"Error processing payment success: {e}")
    
    async def _process_automation_status(self, data: Dict[str, Any]):
        """Process automation status update"""
        try:
            order_id = data['order_id']
            status = data['status']
            timestamp = data['timestamp']
            
            # Update order status
            from .database import get_order_manager
            order_mgr = await get_order_manager()
            
            status_mapping = {
                'started': 'in_progress',
                'completed': 'delivery_ready',
                'delivered': 'completed',
                'failed': 'failed'
            }
            
            new_status = status_mapping.get(status, status)
            await order_mgr.update_order_status(order_id, new_status, f"Automation update: {status}")
            
            # Notify user if needed
            await self._notify_user_status_update(order_id, new_status)
            
            logger.info(f"Automation status updated: {order_id} -> {new_status}")
            
        except Exception as e:
            logger.error(f"Error processing automation status: {e}")
    
    async def _process_broadcast(self, data: Dict[str, Any]):
        """Process broadcast message"""
        try:
            message = data['message']
            target_group = data['target_group']
            
            # Get target users based on group
            user_ids = await self._get_broadcast_targets(target_group)
            
            # Send messages
            sent_count = 0
            failed_count = 0
            
            for user_id in user_ids:
                try:
                    await self.bot_app.application.bot.send_message(
                        chat_id=user_id,
                        text=message,
                        parse_mode='Markdown'
                    )
                    sent_count += 1
                    
                    # Rate limiting
                    await asyncio.sleep(0.05)  # 20 messages per second
                    
                except Exception as e:
                    failed_count += 1
                    logger.warning(f"Failed to send broadcast to {user_id}: {e}")
            
            logger.info(f"Broadcast completed: {sent_count} sent, {failed_count} failed")
            
        except Exception as e:
            logger.error(f"Error processing broadcast: {e}")
    
    async def _notify_user_status_update(self, order_id: str, status: str):
        """Notify user of order status update"""
        try:
            from .database import get_order_manager
            order_mgr = await get_order_manager()
            
            order = await order_mgr.get_order(order_id)
            if not order:
                return
            
            user_id = order['user_id']
            
            status_messages = {
                'in_progress': f"🔄 Your order #{order_id[:8]} is now being processed!",
                'delivery_ready': f"📦 Your order #{order_id[:8]} is ready! Accounts will be delivered shortly.",
                'completed': f"🎉 Your order #{order_id[:8]} is complete! Check your account details.",
                'failed': f"❌ There was an issue with order #{order_id[:8]}. Support has been contacted."
            }
            
            message = status_messages.get(status)
            if message:
                await self.bot_app.application.bot.send_message(
                    chat_id=user_id,
                    text=message
                )
                
        except Exception as e:
            logger.error(f"Error notifying user: {e}")
    
    async def _get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        try:
            from .database import get_database
            db = await get_database()
            
            async with db.postgres_pool.acquire() as connection:
                total_users = await connection.fetchval("SELECT COUNT(*) FROM users")
                total_orders = await connection.fetchval("SELECT COUNT(*) FROM orders")
                revenue_today = await connection.fetchval("""
                    SELECT COALESCE(SUM(total_amount), 0) FROM orders 
                    WHERE status = 'completed' AND created_at >= CURRENT_DATE
                """)
                
            return {
                'total_users': total_users or 0,
                'total_orders': total_orders or 0,
                'revenue_today': float(revenue_today or 0),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {'error': str(e)}
    
    async def _get_broadcast_targets(self, target_group: str) -> list[int]:
        """Get user IDs for broadcast target group"""
        try:
            from .database import get_database
            db = await get_database()
            
            queries = {
                'all': "SELECT user_id FROM users WHERE is_banned = false",
                'premium': "SELECT user_id FROM users WHERE is_premium = true AND is_banned = false",
                'recent': """
                    SELECT DISTINCT user_id FROM orders 
                    WHERE created_at >= NOW() - INTERVAL '30 days'
                """,
                'failed': """
                    SELECT DISTINCT user_id FROM orders 
                    WHERE status = 'failed' AND created_at >= NOW() - INTERVAL '7 days'
                """
            }
            
            query = queries.get(target_group, queries['all'])
            
            async with db.postgres_pool.acquire() as connection:
                results = await connection.fetch(query)
                return [row['user_id'] for row in results]
                
        except Exception as e:
            logger.error(f"Error getting broadcast targets: {e}")
            return []

def create_webhook_server(bot_app: TinderBotApplication) -> WebhookServer:
    """Create webhook server instance"""
    return WebhookServer(bot_app)

async def run_webhook_server(host: str = "0.0.0.0", port: int = 8000):
    """Run webhook server"""
    try:
        # Initialize bot application
        bot_app = TinderBotApplication()
        
        if not await bot_app.initialize():
            raise RuntimeError("Failed to initialize bot application")
        
        # Create webhook server
        webhook_server = create_webhook_server(bot_app)
        
        # Configure uvicorn
        config = uvicorn.Config(
            app=webhook_server.app,
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )
        
        server = uvicorn.Server(config)
        
        logger.info(f"🚀 Starting webhook server on {host}:{port}")
        await server.serve()
        
    except Exception as e:
        logger.error(f"❌ Error running webhook server: {e}")
        raise

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Tinder Bot Webhook Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
    
    args = parser.parse_args()
    
    try:
        asyncio.run(run_webhook_server(args.host, args.port))
    except KeyboardInterrupt:
        print("\nWebhook server stopped by user")
    except Exception as e:
        print(f"Error running webhook server: {e}")
        exit(1)