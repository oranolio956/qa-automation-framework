#!/usr/bin/env python3
"""
Real-Time Order Tracking System for Telegram Bot
Provides beautiful, dynamic UI with live status updates and progress tracking
"""

import asyncio
import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, asdict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrderStatus(Enum):
    """Real-time order status tracking"""
    QUEUED = "⏳ Queued"
    CREATING = "🔧 Creating"
    VERIFYING = "📱 Verifying"
    COMPLETE = "✅ Complete"
    FAILED = "❌ Failed"
    CANCELLED = "🚫 Cancelled"

class AccountStatus(Enum):
    """Individual account status"""
    PENDING = "⏳ Pending"
    CREATING = "🔧 Creating"
    VERIFYING = "📱 Verifying SMS"
    WARMING = "🔥 Warming Up"
    COMPLETE = "✅ Complete"
    FAILED = "❌ Failed"

@dataclass
class AccountProgress:
    """Individual account progress tracking"""
    username: str = ""
    phone: str = ""
    email: str = ""
    status: str = AccountStatus.PENDING.value
    progress: int = 0  # 0-100
    created_at: datetime = None
    completed_at: datetime = None
    error_message: str = ""

@dataclass
class OrderState:
    """Complete order state tracking"""
    order_id: str
    user_id: int
    service: str  # "snapchat", "tinder", etc.
    account_count: int
    total_price: float
    status: str = OrderStatus.QUEUED.value
    progress: int = 0  # Overall progress 0-100
    created_at: datetime = None
    estimated_completion: datetime = None
    payment_confirmed_at: datetime = None
    started_at: datetime = None
    completed_at: datetime = None
    accounts: List[AccountProgress] = None
    
    def __post_init__(self):
        if self.accounts is None:
            self.accounts = []
        if self.created_at is None:
            self.created_at = datetime.now()

class RealTimeOrderTracker:
    """Handles real-time order status updates and beautiful UI"""
    
    def __init__(self, bot_application):
        self.bot = bot_application
        self.active_orders: Dict[str, OrderState] = {}
        self.status_messages: Dict[str, int] = {}  # order_id -> message_id
        self.update_tasks: Dict[str, asyncio.Task] = {}
        self.user_orders: Dict[int, List[str]] = {}  # user_id -> [order_ids]
    
    def generate_order_id(self) -> str:
        """Generate unique order ID"""
        return f"ORD{int(datetime.now().timestamp())}{uuid.uuid4().hex[:6].upper()}"
    
    def create_progress_bar(self, completed: int, total: int, width: int = 7) -> str:
        """Create beautiful visual progress bar"""
        if total == 0:
            return "▓" * width + " 100%"
        
        progress_ratio = completed / total
        filled_blocks = int(progress_ratio * width)
        empty_blocks = width - filled_blocks
        
        bar = "▓" * filled_blocks + "░" * empty_blocks
        percentage = int(progress_ratio * 100)
        return f"{bar} {percentage}%"
    
    def format_eta(self, minutes: int) -> str:
        """Format ETA into readable format"""
        if minutes <= 0:
            return "Completing now..."
        elif minutes < 60:
            return f"{minutes} minutes"
        else:
            hours = minutes // 60
            remaining_minutes = minutes % 60
            if remaining_minutes == 0:
                return f"{hours} hour{'s' if hours > 1 else ''}"
            else:
                return f"{hours}h {remaining_minutes}m"
    
    def format_time_elapsed(self, start_time: datetime) -> str:
        """Format time elapsed since start"""
        elapsed = datetime.now() - start_time
        total_seconds = int(elapsed.total_seconds())
        
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    async def create_order(self, user_id: int, service: str, account_count: int, total_price: float) -> str:
        """Create new order with tracking"""
        order_id = self.generate_order_id()
        estimated_time = account_count * 3  # 3 minutes per account
        
        order = OrderState(
            order_id=order_id,
            user_id=user_id,
            service=service,
            account_count=account_count,
            total_price=total_price,
            estimated_completion=datetime.now() + timedelta(minutes=estimated_time),
            accounts=[AccountProgress() for _ in range(account_count)]
        )
        
        self.active_orders[order_id] = order
        
        # Track user orders
        if user_id not in self.user_orders:
            self.user_orders[user_id] = []
        self.user_orders[user_id].append(order_id)
        
        return order_id
    
    async def show_order_creation_interface(self, update: Update, order_id: str) -> None:
        """Show beautiful order creation interface"""
        order = self.active_orders.get(order_id)
        if not order:
            return
        
        estimated_minutes = int((order.estimated_completion - order.created_at).total_seconds() / 60)
        
        message_text = f"""
📋 **New Order #{order_id[-6:]}**
┌─────────────────────────┐
│ Service: {order.service.title()}       │
│ Quantity: {order.account_count} accounts    │
│ Status: {order.status} │
│ ETA: ~{estimated_minutes} minutes        │
└─────────────────────────┘

💰 **Total: ${order.total_price:.2f}**
🎯 **Ready for payment**

Choose your payment method:
"""
        
        keyboard = [
            [
                InlineKeyboardButton("₿ Bitcoin", callback_data=f"pay_bitcoin_{order_id}"),
                InlineKeyboardButton("Ξ Ethereum", callback_data=f"pay_ethereum_{order_id}")
            ],
            [
                InlineKeyboardButton("₮ USDT (TRC20)", callback_data=f"pay_usdt_trc20_{order_id}"),
                InlineKeyboardButton("₮ USDT (ERC20)", callback_data=f"pay_usdt_erc20_{order_id}")
            ],
            [
                InlineKeyboardButton("📊 Details", callback_data=f"order_details_{order_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_order_{order_id}")
            ]
        ]
        
        if hasattr(update, 'message'):
            await update.message.reply_text(
                message_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.callback_query.edit_message_text(
                message_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    async def show_live_progress_dashboard(self, user_id: int, order_id: str, message_id: int = None) -> None:
        """Show beautiful live progress dashboard"""
        order = self.active_orders.get(order_id)
        if not order:
            return
        
        # Calculate overall progress
        completed_accounts = sum(1 for acc in order.accounts if acc.status == AccountStatus.COMPLETE.value)
        order.progress = int((completed_accounts / order.account_count) * 100) if order.account_count > 0 else 0
        
        # Calculate ETA
        if order.started_at:
            elapsed = datetime.now() - order.started_at
            if completed_accounts > 0:
                avg_time_per_account = elapsed.total_seconds() / completed_accounts
                remaining_accounts = order.account_count - completed_accounts
                eta_minutes = int((remaining_accounts * avg_time_per_account) / 60)
            else:
                eta_minutes = order.account_count * 3
        else:
            eta_minutes = order.account_count * 3
        
        # Status emoji
        status_emoji = {
            OrderStatus.QUEUED.value: "⏳",
            OrderStatus.CREATING.value: "🔧",
            OrderStatus.VERIFYING.value: "📱",
            OrderStatus.COMPLETE.value: "🎉",
            OrderStatus.FAILED.value: "❌"
        }.get(order.status, "🔄")
        
        progress_bar = self.create_progress_bar(completed_accounts, order.account_count, 10)
        
        message_text = f"""
🚀 **Order #{order_id[-6:]} Progress**

{status_emoji} **Current Status:** {order.status}
{progress_bar}
📊 **Progress:** {completed_accounts}/{order.account_count} accounts
⏰ **ETA:** {self.format_eta(eta_minutes)}
"""
        
        if order.started_at:
            elapsed_time = self.format_time_elapsed(order.started_at)
            message_text += f"⏱️ **Elapsed:** {elapsed_time}\n"
        
        message_text += "\n**Account Status:**\n"
        
        # Show individual account progress
        for i, account in enumerate(order.accounts, 1):
            if account.status == AccountStatus.COMPLETE.value:
                message_text += f"  {i}. ✅ {account.username} - Complete\n"
            elif account.status == AccountStatus.CREATING.value:
                message_text += f"  {i}. 🔧 Creating account...\n"
            elif account.status == AccountStatus.VERIFYING.value:
                message_text += f"  {i}. 📱 Verifying SMS...\n"
            elif account.status == AccountStatus.WARMING.value:
                message_text += f"  {i}. 🔥 Warming up...\n"
            elif account.status == AccountStatus.FAILED.value:
                message_text += f"  {i}. ❌ Failed - Retrying\n"
            else:
                message_text += f"  {i}. ⏳ Queued\n"
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_progress_{order_id}"),
                InlineKeyboardButton("📊 Details", callback_data=f"order_details_{order_id}")
            ]
        ]
        
        if order.status not in [OrderStatus.COMPLETE.value, OrderStatus.CANCELLED.value]:
            keyboard.append([
                InlineKeyboardButton("⏸️ Pause", callback_data=f"pause_order_{order_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_order_{order_id}")
            ])
        
        if order.status == OrderStatus.COMPLETE.value:
            keyboard.append([
                InlineKeyboardButton("📥 Download All", callback_data=f"download_accounts_{order_id}")
            ])
        
        keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
        
        try:
            if message_id:
                await self.bot.application.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=message_id,
                    text=message_text,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                message = await self.bot.application.bot.send_message(
                    chat_id=user_id,
                    text=message_text,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                self.status_messages[order_id] = message.message_id
                
        except Exception as e:
            logger.error(f"Error updating progress dashboard: {e}")
    
    async def show_order_completion(self, user_id: int, order_id: str) -> None:
        """Show beautiful order completion interface"""
        order = self.active_orders.get(order_id)
        if not order:
            return
        
        completed_accounts = [acc for acc in order.accounts if acc.status == AccountStatus.COMPLETE.value]
        total_time = self.format_time_elapsed(order.started_at) if order.started_at else "Unknown"
        
        message_text = f"""
🎉 **Order #{order_id[-6:]} Complete!**

✅ **{len(completed_accounts)}/{order.account_count} accounts successfully created**
📱 **All accounts verified and ready**
⏱️ **Completed in {total_time}**
🔥 **{len(completed_accounts) * 100} adds configured**

📱 **Your Account Army:**
"""
        
        for i, account in enumerate(completed_accounts, 1):
            message_text += f"  {i}. @{account.username} | {account.phone}\n"
        
        message_text += "\n🚀 **Ready to dominate!**"
        
        keyboard = [
            [
                InlineKeyboardButton("📥 Download All", callback_data=f"download_accounts_{order_id}"),
                InlineKeyboardButton("📊 View Details", callback_data=f"order_details_{order_id}")
            ],
            [
                InlineKeyboardButton("🔄 Order Again", callback_data=f"reorder_{order.service}_{order.account_count}"),
                InlineKeyboardButton("📋 My Orders", callback_data="my_orders")
            ],
            [
                InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
            ]
        ]
        
        await self.bot.application.bot.send_message(
            chat_id=user_id,
            text=message_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def start_account_creation_with_updates(self, order_id: str) -> None:
        """Start account creation with real-time updates"""
        order = self.active_orders.get(order_id)
        if not order:
            return
        
        order.status = OrderStatus.CREATING.value
        order.started_at = datetime.now()
        
        # Start the update task
        if order_id not in self.update_tasks:
            self.update_tasks[order_id] = asyncio.create_task(
                self._account_creation_process(order_id)
            )
    
    async def _account_creation_process(self, order_id: str) -> None:
        """Simulate account creation process with real-time updates"""
        order = self.active_orders.get(order_id)
        if not order:
            return
        
        try:
            for i, account in enumerate(order.accounts):
                # Update account status
                account.status = AccountStatus.CREATING.value
                
                # Update live dashboard
                message_id = self.status_messages.get(order_id)
                if message_id:
                    await self.show_live_progress_dashboard(order.user_id, order_id, message_id)
                
                # Simulate account creation steps
                await self._simulate_account_creation(account, i + 1)
                
                # Small delay between accounts
                if i < len(order.accounts) - 1:
                    await asyncio.sleep(2)
            
            # Mark order as complete
            order.status = OrderStatus.COMPLETE.value
            order.completed_at = datetime.now()
            
            # Final update
            message_id = self.status_messages.get(order_id)
            if message_id:
                await self.show_live_progress_dashboard(order.user_id, order_id, message_id)
            
            # Show completion
            await self.show_order_completion(order.user_id, order_id)
            
        except Exception as e:
            logger.error(f"Error in account creation process: {e}")
            order.status = OrderStatus.FAILED.value
    
    async def _simulate_account_creation(self, account: AccountProgress, account_num: int) -> None:
        """Simulate individual account creation with realistic steps"""
        import random
        
        steps = [
            (AccountStatus.CREATING, "Initializing emulator", 3),
            (AccountStatus.CREATING, "Installing Snapchat", 4),
            (AccountStatus.CREATING, "Generating profile", 2),
            (AccountStatus.VERIFYING, "SMS verification", 5),
            (AccountStatus.WARMING, "Account warming", 3),
            (AccountStatus.COMPLETE, "Finalizing", 1)
        ]
        
        # Generate account details
        female_names = ["Emma", "Olivia", "Ava", "Isabella", "Sophia", "Charlotte", "Mia"]
        account.username = f"{random.choice(female_names).lower()}{random.randint(100, 999)}"
        account.phone = f"+1555{random.randint(1000000, 9999999)}"
        account.email = f"{account.username}@gmail.com"
        account.created_at = datetime.now()
        
        for status, description, duration in steps:
            account.status = status.value
            await asyncio.sleep(duration)
        
        account.completed_at = datetime.now()
        account.progress = 100
    
    async def cancel_order(self, order_id: str, reason: str = "User cancellation") -> bool:
        """Cancel an order"""
        order = self.active_orders.get(order_id)
        if not order:
            return False
        
        order.status = OrderStatus.CANCELLED.value
        
        # Stop any running tasks
        if order_id in self.update_tasks:
            self.update_tasks[order_id].cancel()
            del self.update_tasks[order_id]
        
        return True
    
    def get_user_orders(self, user_id: int) -> List[OrderState]:
        """Get all orders for a user"""
        order_ids = self.user_orders.get(user_id, [])
        return [self.active_orders[oid] for oid in order_ids if oid in self.active_orders]
    
    def get_order(self, order_id: str) -> Optional[OrderState]:
        """Get specific order"""
        return self.active_orders.get(order_id)
    
    async def cleanup_completed_orders(self) -> None:
        """Cleanup old completed orders"""
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        to_remove = []
        for order_id, order in self.active_orders.items():
            if (order.status in [OrderStatus.COMPLETE.value, OrderStatus.CANCELLED.value] and 
                order.completed_at and order.completed_at < cutoff_time):
                to_remove.append(order_id)
        
        for order_id in to_remove:
            del self.active_orders[order_id]
            if order_id in self.status_messages:
                del self.status_messages[order_id]
            if order_id in self.update_tasks:
                self.update_tasks[order_id].cancel()
                del self.update_tasks[order_id]
        
        logger.info(f"Cleaned up {len(to_remove)} old orders")

# Global instance
_order_tracker = None

def get_order_tracker(bot_application) -> RealTimeOrderTracker:
    """Get global order tracker instance"""
    global _order_tracker
    if _order_tracker is None:
        _order_tracker = RealTimeOrderTracker(bot_application)
    return _order_tracker

if __name__ == "__main__":
    # Test order tracking
    async def test_order_tracking():
        tracker = RealTimeOrderTracker(None)
        
        # Create test order
        order_id = await tracker.create_order(
            user_id=123456,
            service="snapchat",
            account_count=3,
            total_price=75.00
        )
        
        print(f"Created order: {order_id}")
        
        # Simulate account creation
        await tracker.start_account_creation_with_updates(order_id)
        
        # Wait for completion
        await asyncio.sleep(30)
        
        print("Order tracking test completed")
    
    asyncio.run(test_order_tracking())