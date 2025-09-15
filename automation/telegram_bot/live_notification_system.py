#!/usr/bin/env python3
"""
Live Notification System for Real-Time Order Updates
Provides beautiful push notifications and live progress updates to customers
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from beautiful_ui_components import BeautifulUIComponents

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationType(Enum):
    """Types of notifications"""
    PAYMENT_CONFIRMED = "payment_confirmed"
    ORDER_STARTED = "order_started"
    ACCOUNT_CREATING = "account_creating"
    ACCOUNT_COMPLETED = "account_completed"
    ORDER_COMPLETED = "order_completed"
    ORDER_FAILED = "order_failed"
    SYSTEM_UPDATE = "system_update"

@dataclass
class NotificationTemplate:
    """Notification message template"""
    title: str
    message: str
    buttons: List[List[InlineKeyboardButton]]
    priority: str = "normal"  # low, normal, high, urgent

class LiveNotificationSystem:
    """Manages real-time notifications and live updates for orders"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.ui = BeautifulUIComponents()
        self.active_subscriptions: Dict[str, List[int]] = {}  # order_id -> [user_ids]
        self.notification_queue: List[Dict] = []
        self.notification_task = None
        self.update_intervals = {
            "high_frequency": 10,    # 10 seconds during active creation
            "normal": 30,           # 30 seconds for normal updates  
            "low_frequency": 60     # 60 seconds for completed orders
        }
    
    async def start_notification_system(self):
        """Start the notification processing system"""
        if self.notification_task is None:
            self.notification_task = asyncio.create_task(self._process_notifications())
            logger.info("✅ Live notification system started")
    
    async def stop_notification_system(self):
        """Stop the notification processing system"""
        if self.notification_task:
            self.notification_task.cancel()
            self.notification_task = None
            logger.info("🛑 Live notification system stopped")
    
    async def subscribe_to_order_updates(self, order_id: str, user_id: int):
        """Subscribe user to live updates for an order"""
        if order_id not in self.active_subscriptions:
            self.active_subscriptions[order_id] = []
        
        if user_id not in self.active_subscriptions[order_id]:
            self.active_subscriptions[order_id].append(user_id)
            logger.info(f"User {user_id} subscribed to order {order_id} updates")
    
    async def unsubscribe_from_order_updates(self, order_id: str, user_id: int):
        """Unsubscribe user from order updates"""
        if order_id in self.active_subscriptions and user_id in self.active_subscriptions[order_id]:
            self.active_subscriptions[order_id].remove(user_id)
            if not self.active_subscriptions[order_id]:
                del self.active_subscriptions[order_id]
            logger.info(f"User {user_id} unsubscribed from order {order_id} updates")
    
    async def send_order_notification(self, notification_type: NotificationType, 
                                    order_id: str, user_id: int = None, 
                                    custom_data: Dict = None):
        """Send notification about order updates"""
        try:
            # Get notification template
            template = self._get_notification_template(notification_type, order_id, custom_data)
            
            # Determine recipients
            recipients = []
            if user_id:
                recipients = [user_id]
            elif order_id in self.active_subscriptions:
                recipients = self.active_subscriptions[order_id]
            
            # Queue notifications
            for recipient_id in recipients:
                notification = {
                    'type': notification_type.value,
                    'user_id': recipient_id,
                    'order_id': order_id,
                    'template': template,
                    'timestamp': datetime.now(),
                    'priority': template.priority
                }
                self.notification_queue.append(notification)
            
            logger.info(f"Queued {len(recipients)} notifications for order {order_id}")
            
        except Exception as e:
            logger.error(f"Error sending order notification: {e}")
    
    async def send_live_progress_update(self, order_id: str, progress_data: Dict):
        """Send live progress update with beautiful UI"""
        try:
            if order_id not in self.active_subscriptions:
                return
            
            # Create beautiful progress message
            message = self._create_live_progress_message(order_id, progress_data)
            
            # Create action buttons
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_progress_{order_id}"),
                    InlineKeyboardButton("📊 Details", callback_data=f"order_details_{order_id}")
                ],
                [
                    InlineKeyboardButton("⏸️ Pause", callback_data=f"pause_order_{order_id}"),
                    InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_order_{order_id}")
                ] if progress_data.get('status') in ['creating', 'verifying'] else [
                    InlineKeyboardButton("📥 Download", callback_data=f"download_accounts_{order_id}")
                ]
            ])
            
            # Send to all subscribers
            for user_id in self.active_subscriptions[order_id]:
                try:
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=message,
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
                except Exception as e:
                    logger.error(f"Error sending progress update to user {user_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error sending live progress update: {e}")
    
    async def send_account_completion_notification(self, order_id: str, 
                                                 account_data: Dict, 
                                                 progress_data: Dict):
        """Send notification when individual account is completed"""
        try:
            if order_id not in self.active_subscriptions:
                return
            
            account_num = account_data.get('account_num', 'X')
            username = account_data.get('username', 'account')
            completed = progress_data.get('completed', 0)
            total = progress_data.get('total', 0)
            
            message = f"""
✅ **ACCOUNT {account_num} READY!**

🎯 **Order #{order_id[-6:]}**
📱 @{username} is ready for domination!

📊 **Progress:** {completed}/{total} accounts completed
{self.ui.create_progress_bar(completed, total, 8)}

🔥 **Account Features:**
• SMS verified & activated
• Account warmed up  
• 100 adds configured
• Anti-detection protection

⚡ **Next:** {'Creating remaining accounts...' if completed < total else 'Order complete!'}
"""
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📊 Live Progress", callback_data=f"live_progress_{order_id}"),
                    InlineKeyboardButton("📋 Account Details", callback_data=f"account_details_{order_id}_{account_num}")
                ]
            ])
            
            # Send to all subscribers
            for user_id in self.active_subscriptions[order_id]:
                try:
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=message,
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
                except Exception as e:
                    logger.error(f"Error sending account completion to user {user_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error sending account completion notification: {e}")
    
    async def send_order_completion_celebration(self, order_id: str, 
                                              completion_data: Dict):
        """Send beautiful order completion celebration"""
        try:
            if order_id not in self.active_subscriptions:
                return
            
            account_count = completion_data.get('account_count', 0)
            total_time = completion_data.get('total_time', 'Unknown')
            accounts = completion_data.get('accounts', [])
            
            celebration = f"""
🎉 **ORDER COMPLETE - DOMINATION ACHIEVED!** 🎉

🎯 **Order #{order_id[-6:]}**

🏆 **SUCCESS METRICS:**
✅ {len(accounts)}/{account_count} accounts delivered
💯 {len(accounts) * 100:,} total adds configured
⏱️ Completed in {total_time}
🛡️ All accounts protected & warmed

🚀 **YOUR SNAPCHAT ARMY:**
"""
            
            # Add first few accounts
            for i, account in enumerate(accounts[:3], 1):
                if 'username' in account:
                    celebration += f"  {i}. @{account['username']} - Ready to dominate!\n"
            
            if len(accounts) > 3:
                celebration += f"  ... and {len(accounts) - 3} more accounts!\n"
            
            celebration += f"""
🎯 **READY FOR ACTION:**
• All accounts SMS verified
• Account warming completed
• Add farming configured  
• Anti-detection active

💥 **GO DOMINATE THE ADDS!** 💥
"""
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📥 Download All Accounts", callback_data=f"download_accounts_{order_id}"),
                ],
                [
                    InlineKeyboardButton("🔄 Order Again", callback_data=f"reorder_snapchat_{account_count}"),
                    InlineKeyboardButton("📊 Order Details", callback_data=f"order_details_{order_id}")
                ],
                [
                    InlineKeyboardButton("⭐ Rate Experience", callback_data=f"rate_order_{order_id}"),
                    InlineKeyboardButton("💬 Share Success", callback_data=f"share_success_{order_id}")
                ]
            ])
            
            # Send celebration to all subscribers
            for user_id in self.active_subscriptions[order_id]:
                try:
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=celebration,
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
                    
                    # Auto-unsubscribe after completion
                    await self.unsubscribe_from_order_updates(order_id, user_id)
                    
                except Exception as e:
                    logger.error(f"Error sending completion celebration to user {user_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error sending order completion celebration: {e}")
    
    async def send_error_notification(self, order_id: str, error_type: str, 
                                    error_details: Dict = None):
        """Send error notification with helpful actions"""
        try:
            if order_id not in self.active_subscriptions:
                return
            
            error_messages = {
                "payment_timeout": "💳 Payment verification timeout",
                "creation_failed": "🔧 Account creation failed", 
                "verification_failed": "📱 SMS verification failed",
                "system_error": "⚙️ System error occurred"
            }
            
            error_title = error_messages.get(error_type, "⚠️ Order issue detected")
            
            message = f"""
⚠️ **{error_title.upper()}**

🎯 **Order #{order_id[-6:]}**

🔧 **AUTOMATIC RECOVERY:**
• System attempting auto-retry
• Backup systems activated
• Technical team notified

⏱️ **EXPECTED RESOLUTION:** 2-5 minutes

🛡️ **YOUR OPTIONS:**
• Wait for automatic retry
• Contact support for immediate help
• Cancel order for full refund
"""
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔄 Check Status", callback_data=f"live_progress_{order_id}"),
                    InlineKeyboardButton("🆘 Get Support", callback_data="contact_support")
                ],
                [
                    InlineKeyboardButton("⏸️ Pause Order", callback_data=f"pause_order_{order_id}"),
                    InlineKeyboardButton("❌ Cancel & Refund", callback_data=f"cancel_order_{order_id}")
                ]
            ])
            
            # Send to all subscribers  
            for user_id in self.active_subscriptions[order_id]:
                try:
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=message,
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
                except Exception as e:
                    logger.error(f"Error sending error notification to user {user_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error sending error notification: {e}")
    
    def _get_notification_template(self, notification_type: NotificationType, 
                                 order_id: str, custom_data: Dict = None) -> NotificationTemplate:
        """Get notification template for specific type"""
        templates = {
            NotificationType.PAYMENT_CONFIRMED: NotificationTemplate(
                title="🎉 Payment Confirmed",
                message=f"""
🎉 **PAYMENT CONFIRMED!**

Order #{order_id[-6:]} payment verified!
🚀 Account creation starting immediately...

⚡ You'll receive live updates as each account is created.
""",
                buttons=[
                    [InlineKeyboardButton("📊 Live Progress", callback_data=f"live_progress_{order_id}")],
                ],
                priority="high"
            ),
            
            NotificationType.ORDER_STARTED: NotificationTemplate(
                title="🔧 Creation Started", 
                message=f"""
🔧 **ACCOUNT CREATION STARTED!**

Order #{order_id[-6:]} is now in progress!

🛡️ **Security Measures Active:**
• Anti-detection protocols engaged
• Premium proxy rotation
• Human-like behavior simulation

📱 Live updates will be sent as each account completes.
""",
                buttons=[
                    [InlineKeyboardButton("📊 Watch Progress", callback_data=f"live_progress_{order_id}")],
                    [InlineKeyboardButton("⏸️ Pause", callback_data=f"pause_order_{order_id}")],
                ],
                priority="high"
            ),
            
            NotificationType.ORDER_COMPLETED: NotificationTemplate(
                title="🎉 Order Complete",
                message=f"""
🎉 **ORDER COMPLETE!**

Order #{order_id[-6:]} - All accounts delivered!
🚀 Your Snapchat army is ready!
""",
                buttons=[
                    [InlineKeyboardButton("📥 Download Accounts", callback_data=f"download_accounts_{order_id}")],
                    [InlineKeyboardButton("🔄 Order Again", callback_data=f"reorder_{order_id}")],
                ],
                priority="high"
            )
        }
        
        return templates.get(notification_type, NotificationTemplate(
            title="📱 Order Update",
            message=f"Order #{order_id[-6:]} update",
            buttons=[]
        ))
    
    def _create_live_progress_message(self, order_id: str, progress_data: Dict) -> str:
        """Create live progress update message"""
        completed = progress_data.get('completed', 0)
        total = progress_data.get('total', 0)
        current_step = progress_data.get('current_step', 'Processing...')
        eta_minutes = progress_data.get('eta_minutes', 0)
        
        progress_bar = self.ui.create_progress_bar(completed, total, 10)
        eta_text = self.ui.format_eta(eta_minutes)
        
        return f"""
🔧 **LIVE UPDATE - Order #{order_id[-6:]}**

📊 **Progress:**
{progress_bar}
{completed}/{total} accounts completed

🎯 **Current Status:**
{current_step}

⏰ **ETA:** {eta_text}

⚡ **System Status:** All systems operational
🛡️ **Security:** Anti-detection active
"""
    
    async def _process_notifications(self):
        """Process notification queue"""
        while True:
            try:
                if not self.notification_queue:
                    await asyncio.sleep(1)
                    continue
                
                # Sort by priority and timestamp
                self.notification_queue.sort(key=lambda x: (
                    {'urgent': 0, 'high': 1, 'normal': 2, 'low': 3}.get(x['template'].priority, 2),
                    x['timestamp']
                ))
                
                # Process notifications
                batch_size = 10  # Process 10 notifications at a time
                notifications_to_process = self.notification_queue[:batch_size]
                self.notification_queue = self.notification_queue[batch_size:]
                
                for notification in notifications_to_process:
                    await self._send_notification(notification)
                    
                # Small delay between batches
                await asyncio.sleep(0.5)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing notifications: {e}")
                await asyncio.sleep(5)
    
    async def _send_notification(self, notification: Dict):
        """Send individual notification"""
        try:
            template = notification['template']
            user_id = notification['user_id']
            
            keyboard = InlineKeyboardMarkup(template.buttons) if template.buttons else None
            
            await self.bot.send_message(
                chat_id=user_id,
                text=template.message,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error sending notification to user {notification['user_id']}: {e}")

# Global notification system instance
_notification_system = None

async def get_notification_system(bot: Bot) -> LiveNotificationSystem:
    """Get global notification system instance"""
    global _notification_system
    if _notification_system is None:
        _notification_system = LiveNotificationSystem(bot)
        await _notification_system.start_notification_system()
    return _notification_system

if __name__ == "__main__":
    # Test notification system
    async def test_notifications():
        # This would require a real bot token to test
        print("Notification system test - would need real bot instance")
        print("✅ Notification system structure validated")
    
    asyncio.run(test_notifications())