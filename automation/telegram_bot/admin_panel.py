#!/usr/bin/env python3
"""
Admin Panel for Telegram Bot
Provides administrative functions for managing orders, users, and system operations
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import csv
from io import StringIO

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Document
from telegram.ext import ContextTypes

from .config import TelegramBotConfig, OrderStatus
from .database import get_database, get_user_manager, get_order_manager, get_payment_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdminPanelManager:
    """Administrative functions for bot management"""
    
    def __init__(self):
        self.admin_commands = {
            'dashboard': self.show_admin_dashboard,
            'orders': self.manage_orders,
            'users': self.manage_users,
            'stats': self.show_statistics,
            'system': self.system_management,
            'payments': self.manage_payments,
            'broadcast': self.broadcast_message,
            'export': self.export_data,
            'maintenance': self.maintenance_mode
        }
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id in TelegramBotConfig.ADMIN_USER_IDS
    
    async def handle_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle admin commands"""
        try:
            user_id = update.effective_user.id
            
            if not self.is_admin(user_id):
                await update.message.reply_text("❌ Access denied. Admin privileges required.")
                return
            
            # Show main admin dashboard
            await self.show_admin_dashboard(update, context)
            
        except Exception as e:
            logger.error(f"Error in admin command: {e}")
            await update.message.reply_text(f"❌ Admin error: {str(e)}")
    
    async def show_admin_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main admin dashboard"""
        try:
            # Get system statistics
            stats = await self._get_system_stats()
            
            message_text = f"""
🔧 **Admin Dashboard**

📊 **System Overview:**
👥 Total Users: {stats['total_users']:,}
📦 Total Orders: {stats['total_orders']:,}
💰 Revenue (30d): ${stats['revenue_30d']:,.2f}
⚡ Active Orders: {stats['active_orders']}

🚨 **Alerts:**
❌ Failed Orders: {stats['failed_orders']}
⏰ Overdue Orders: {stats['overdue_orders']}
💸 Pending Refunds: {stats['pending_refunds']}

📈 **Today's Metrics:**
📋 New Orders: {stats['orders_today']}
👤 New Users: {stats['users_today']}
💳 Payments: ${stats['payments_today']:,.2f}
✅ Success Rate: {stats['success_rate_today']:.1f}%

**System Status:** {'🟢 Operational' if stats['system_healthy'] else '🔴 Issues Detected'}
            """
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📦 Manage Orders", callback_data="admin_orders"),
                    InlineKeyboardButton("👥 Manage Users", callback_data="admin_users")
                ],
                [
                    InlineKeyboardButton("💳 Payments", callback_data="admin_payments"),
                    InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")
                ],
                [
                    InlineKeyboardButton("🔧 System", callback_data="admin_system"),
                    InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")
                ],
                [
                    InlineKeyboardButton("📥 Export Data", callback_data="admin_export"),
                    InlineKeyboardButton("⚙️ Maintenance", callback_data="admin_maintenance")
                ],
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data="admin_dashboard")
                ]
            ])
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    message_text,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            else:
                await update.message.reply_text(
                    message_text,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
                
        except Exception as e:
            logger.error(f"Error showing admin dashboard: {e}")
    
    async def manage_orders(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
        """Manage orders interface"""
        try:
            # Get recent orders
            orders = await self._get_recent_orders(page * 10, 10)
            
            message_text = f"📦 **Order Management** (Page {page + 1})\n\n"
            
            keyboard_buttons = []
            
            for order in orders:
                status_emoji = self._get_status_emoji(order['status'])
                order_text = f"{status_emoji} #{order['order_id'][:8]} - ${order['total_amount']:.2f} - {order['status']}"
                
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        order_text,
                        callback_data=f"admin_order_details:{order['order_id']}"
                    )
                ])
            
            # Navigation buttons
            nav_buttons = []
            if page > 0:
                nav_buttons.append(
                    InlineKeyboardButton("◀️ Previous", callback_data=f"admin_orders:{page-1}")
                )
            nav_buttons.append(
                InlineKeyboardButton("▶️ Next", callback_data=f"admin_orders:{page+1}")
            )
            
            if nav_buttons:
                keyboard_buttons.append(nav_buttons)
            
            # Action buttons
            keyboard_buttons.extend([
                [
                    InlineKeyboardButton("🔍 Search Order", callback_data="admin_search_order"),
                    InlineKeyboardButton("📊 Order Stats", callback_data="admin_order_stats")
                ],
                [
                    InlineKeyboardButton("⚠️ Failed Orders", callback_data="admin_failed_orders"),
                    InlineKeyboardButton("⏰ Overdue Orders", callback_data="admin_overdue_orders")
                ],
                [
                    InlineKeyboardButton("◀️ Back to Dashboard", callback_data="admin_dashboard")
                ]
            ])
            
            await update.callback_query.edit_message_text(
                message_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard_buttons)
            )
            
        except Exception as e:
            logger.error(f"Error managing orders: {e}")
    
    async def show_order_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str):
        """Show detailed order information for admin"""
        try:
            # Get order details
            order_mgr = await get_order_manager()
            order = await order_mgr.get_order(order_id)
            
            if not order:
                await update.callback_query.answer("❌ Order not found")
                return
            
            # Get user info
            user_mgr = await get_user_manager()
            user = await user_mgr.get_user(order['user_id'])
            
            # Get package info
            package = TelegramBotConfig.get_package(order['package_id'])
            
            message_text = f"""
📦 **Order Details - Admin View**

**Order Info:**
🔢 ID: `{order['order_id']}`
📦 Package: {package.name if package else 'Unknown'}
🔢 Quantity: {order['quantity']}
💰 Total: ${order['total_amount']:.2f}
💸 Discount: ${order['discount_amount']:.2f}
📊 Status: {order['status']}

**Customer:**
👤 User ID: {user['user_id'] if user else 'Unknown'}
📱 Username: @{user['username'] if user and user['username'] else 'N/A'}
👤 Name: {user['first_name'] if user else 'Unknown'} {user['last_name'] if user and user['last_name'] else ''}

**Timeline:**
📅 Created: {order['created_at'].strftime('%Y-%m-%d %H:%M:%S')}
⏰ Expected: {order['expected_delivery'].strftime('%Y-%m-%d %H:%M:%S') if order['expected_delivery'] else 'TBD'}
🚀 Started: {order['delivery_started_at'].strftime('%Y-%m-%d %H:%M:%S') if order['delivery_started_at'] else 'Not started'}
✅ Completed: {order['completed_at'].strftime('%Y-%m-%d %H:%M:%S') if order['completed_at'] else 'Not completed'}

**Technical:**
🔧 Job ID: {order['automation_job_id'] or 'Not assigned'}
📝 Notes: {order['notes'] or 'None'}
            """
            
            # Action buttons based on status
            keyboard_buttons = []
            
            if order['status'] == 'payment_confirmed':
                keyboard_buttons.append([
                    InlineKeyboardButton("🚀 Start Processing", callback_data=f"admin_start_order:{order_id}")
                ])
            elif order['status'] == 'in_progress':
                keyboard_buttons.append([
                    InlineKeyboardButton("✅ Mark Complete", callback_data=f"admin_complete_order:{order_id}"),
                    InlineKeyboardButton("❌ Mark Failed", callback_data=f"admin_fail_order:{order_id}")
                ])
            elif order['status'] == 'failed':
                keyboard_buttons.append([
                    InlineKeyboardButton("🔄 Retry Order", callback_data=f"admin_retry_order:{order_id}")
                ])
            
            # Always available actions
            keyboard_buttons.extend([
                [
                    InlineKeyboardButton("📝 Add Note", callback_data=f"admin_add_note:{order_id}"),
                    InlineKeyboardButton("💬 Message User", callback_data=f"admin_message_user:{order['user_id']}")
                ],
                [
                    InlineKeyboardButton("💸 Process Refund", callback_data=f"admin_refund:{order_id}"),
                    InlineKeyboardButton("🚫 Cancel Order", callback_data=f"admin_cancel:{order_id}")
                ],
                [
                    InlineKeyboardButton("◀️ Back to Orders", callback_data="admin_orders")
                ]
            ])
            
            await update.callback_query.edit_message_text(
                message_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard_buttons)
            )
            
        except Exception as e:
            logger.error(f"Error showing order details: {e}")
    
    async def manage_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """User management interface"""
        try:
            stats = await self._get_user_stats()
            
            message_text = f"""
👥 **User Management**

**User Statistics:**
📊 Total Users: {stats['total_users']:,}
🆕 New (24h): {stats['new_users_24h']}
🆕 New (7d): {stats['new_users_7d']}
💰 Paying Users: {stats['paying_users']}
⭐ Premium Users: {stats['premium_users']}
🚫 Banned Users: {stats['banned_users']}

**Activity:**
🔄 Active (24h): {stats['active_24h']}
🔄 Active (7d): {stats['active_7d']}
💰 Avg Spend: ${stats['avg_spend_per_user']:.2f}
📦 Avg Orders: {stats['avg_orders_per_user']:.1f}
            """
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔍 Search User", callback_data="admin_search_user"),
                    InlineKeyboardButton("📊 User Analytics", callback_data="admin_user_analytics")
                ],
                [
                    InlineKeyboardButton("⭐ Premium Users", callback_data="admin_premium_users"),
                    InlineKeyboardButton("🚫 Banned Users", callback_data="admin_banned_users")
                ],
                [
                    InlineKeyboardButton("📈 Top Customers", callback_data="admin_top_customers"),
                    InlineKeyboardButton("🆕 Recent Users", callback_data="admin_recent_users")
                ],
                [
                    InlineKeyboardButton("◀️ Back to Dashboard", callback_data="admin_dashboard")
                ]
            ])
            
            await update.callback_query.edit_message_text(
                message_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error managing users: {e}")
    
    async def show_statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show detailed system statistics"""
        try:
            stats = await self._get_detailed_stats()
            
            message_text = f"""
📊 **Detailed Statistics**

**Revenue Analytics:**
💰 Today: ${stats['revenue_today']:,.2f}
💰 This Week: ${stats['revenue_week']:,.2f}
💰 This Month: ${stats['revenue_month']:,.2f}
💰 All Time: ${stats['revenue_total']:,.2f}

**Order Analytics:**
📦 Pending: {stats['orders_pending']}
✅ Completed: {stats['orders_completed']}
❌ Failed: {stats['orders_failed']}
🚫 Cancelled: {stats['orders_cancelled']}
📊 Success Rate: {stats['success_rate']:.1f}%

**Popular Packages:**
"""
            
            for package_id, count in stats['popular_packages'].items():
                package = TelegramBotConfig.get_package(package_id)
                if package:
                    message_text += f"📦 {package.name}: {count} orders\n"
            
            message_text += f"""

**Performance Metrics:**
⚡ Avg Delivery Time: {stats['avg_delivery_time']:.1f} hours
🎯 Quality Score: {stats['avg_quality_score']:.1f}/100
🔄 Retry Rate: {stats['retry_rate']:.1f}%
💸 Refund Rate: {stats['refund_rate']:.1f}%

**System Health:**
🖥️ CPU Usage: {stats['cpu_usage']:.1f}%
💾 Memory Usage: {stats['memory_usage']:.1f}%
💽 Disk Usage: {stats['disk_usage']:.1f}%
            """
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📈 Revenue Chart", callback_data="admin_revenue_chart"),
                    InlineKeyboardButton("📊 Order Chart", callback_data="admin_order_chart")
                ],
                [
                    InlineKeyboardButton("📥 Export Stats", callback_data="admin_export_stats"),
                    InlineKeyboardButton("🔄 Refresh", callback_data="admin_stats")
                ],
                [
                    InlineKeyboardButton("◀️ Back to Dashboard", callback_data="admin_dashboard")
                ]
            ])
            
            await update.callback_query.edit_message_text(
                message_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error showing statistics: {e}")
    
    async def broadcast_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Broadcast message to users"""
        try:
            message_text = """
📢 **Broadcast Message**

Send a message to all users or specific groups.

**Broadcast Options:**
• All Users
• Premium Users Only
• Recent Customers (30 days)
• Failed Order Users

Type your message or use /cancel to abort.
            """
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("👥 All Users", callback_data="broadcast_all"),
                    InlineKeyboardButton("⭐ Premium Only", callback_data="broadcast_premium")
                ],
                [
                    InlineKeyboardButton("🛒 Recent Customers", callback_data="broadcast_recent"),
                    InlineKeyboardButton("❌ Failed Orders", callback_data="broadcast_failed")
                ],
                [
                    InlineKeyboardButton("◀️ Cancel", callback_data="admin_dashboard")
                ]
            ])
            
            await update.callback_query.edit_message_text(
                message_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error in broadcast message: {e}")
    
    async def export_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Export system data"""
        try:
            message_text = """
📥 **Export Data**

Choose what data to export:
            """
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📦 Orders (CSV)", callback_data="export_orders"),
                    InlineKeyboardButton("👥 Users (CSV)", callback_data="export_users")
                ],
                [
                    InlineKeyboardButton("💳 Payments (CSV)", callback_data="export_payments"),
                    InlineKeyboardButton("📊 Analytics (CSV)", callback_data="export_analytics")
                ],
                [
                    InlineKeyboardButton("📈 Daily Stats", callback_data="export_daily_stats"),
                    InlineKeyboardButton("🔧 System Logs", callback_data="export_logs")
                ],
                [
                    InlineKeyboardButton("◀️ Back to Dashboard", callback_data="admin_dashboard")
                ]
            ])
            
            await update.callback_query.edit_message_text(
                message_text,
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error in export data: {e}")
    
    async def _get_system_stats(self) -> Dict[str, any]:
        """Get system statistics for dashboard"""
        try:
            db = await get_database()
            
            async with db.postgres_pool.acquire() as connection:
                # Basic counts
                total_users = await connection.fetchval("SELECT COUNT(*) FROM users")
                total_orders = await connection.fetchval("SELECT COUNT(*) FROM orders")
                
                # Revenue (30 days)
                revenue_30d = await connection.fetchval("""
                    SELECT COALESCE(SUM(total_amount), 0) FROM orders 
                    WHERE status = 'completed' AND created_at >= NOW() - INTERVAL '30 days'
                """)
                
                # Active orders
                active_orders = await connection.fetchval("""
                    SELECT COUNT(*) FROM orders 
                    WHERE status IN ('pending_payment', 'payment_confirmed', 'in_progress')
                """)
                
                # Failed orders
                failed_orders = await connection.fetchval("""
                    SELECT COUNT(*) FROM orders 
                    WHERE status = 'failed'
                """)
                
                # Overdue orders
                overdue_orders = await connection.fetchval("""
                    SELECT COUNT(*) FROM orders 
                    WHERE status IN ('in_progress', 'payment_confirmed') 
                    AND expected_delivery < NOW()
                """)
                
                # Today's metrics
                orders_today = await connection.fetchval("""
                    SELECT COUNT(*) FROM orders 
                    WHERE created_at >= CURRENT_DATE
                """)
                
                users_today = await connection.fetchval("""
                    SELECT COUNT(*) FROM users 
                    WHERE created_at >= CURRENT_DATE
                """)
                
                payments_today = await connection.fetchval("""
                    SELECT COALESCE(SUM(amount), 0) FROM payments 
                    WHERE status = 'completed' AND created_at >= CURRENT_DATE
                """)
                
                # Success rate today
                completed_today = await connection.fetchval("""
                    SELECT COUNT(*) FROM orders 
                    WHERE status = 'completed' AND created_at >= CURRENT_DATE
                """)
                
                success_rate_today = (completed_today / max(orders_today, 1)) * 100
                
            return {
                'total_users': total_users or 0,
                'total_orders': total_orders or 0,
                'revenue_30d': float(revenue_30d or 0),
                'active_orders': active_orders or 0,
                'failed_orders': failed_orders or 0,
                'overdue_orders': overdue_orders or 0,
                'pending_refunds': 0,  # Placeholder
                'orders_today': orders_today or 0,
                'users_today': users_today or 0,
                'payments_today': float(payments_today or 0),
                'success_rate_today': success_rate_today,
                'system_healthy': (failed_orders or 0) < 10  # Simple health check
            }
            
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return self._get_default_stats()
    
    async def _get_recent_orders(self, offset: int, limit: int) -> List[Dict[str, any]]:
        """Get recent orders for admin"""
        try:
            db = await get_database()
            
            query = """
            SELECT * FROM orders 
            ORDER BY created_at DESC 
            LIMIT $1 OFFSET $2
            """
            
            async with db.postgres_pool.acquire() as connection:
                results = await connection.fetch(query, limit, offset)
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error(f"Error getting recent orders: {e}")
            return []
    
    async def _get_user_stats(self) -> Dict[str, any]:
        """Get user statistics"""
        try:
            db = await get_database()
            
            async with db.postgres_pool.acquire() as connection:
                total_users = await connection.fetchval("SELECT COUNT(*) FROM users")
                new_users_24h = await connection.fetchval("""
                    SELECT COUNT(*) FROM users 
                    WHERE created_at >= NOW() - INTERVAL '24 hours'
                """)
                new_users_7d = await connection.fetchval("""
                    SELECT COUNT(*) FROM users 
                    WHERE created_at >= NOW() - INTERVAL '7 days'
                """)
                paying_users = await connection.fetchval("""
                    SELECT COUNT(DISTINCT user_id) FROM orders 
                    WHERE status = 'completed'
                """)
                premium_users = await connection.fetchval("""
                    SELECT COUNT(*) FROM users WHERE is_premium = true
                """)
                banned_users = await connection.fetchval("""
                    SELECT COUNT(*) FROM users WHERE is_banned = true
                """)
                active_24h = await connection.fetchval("""
                    SELECT COUNT(*) FROM users 
                    WHERE last_active >= NOW() - INTERVAL '24 hours'
                """)
                active_7d = await connection.fetchval("""
                    SELECT COUNT(*) FROM users 
                    WHERE last_active >= NOW() - INTERVAL '7 days'
                """)
                avg_spend = await connection.fetchval("""
                    SELECT AVG(total_spent) FROM users WHERE total_spent > 0
                """)
                avg_orders = await connection.fetchval("""
                    SELECT AVG(total_orders) FROM users WHERE total_orders > 0
                """)
            
            return {
                'total_users': total_users or 0,
                'new_users_24h': new_users_24h or 0,
                'new_users_7d': new_users_7d or 0,
                'paying_users': paying_users or 0,
                'premium_users': premium_users or 0,
                'banned_users': banned_users or 0,
                'active_24h': active_24h or 0,
                'active_7d': active_7d or 0,
                'avg_spend_per_user': float(avg_spend or 0),
                'avg_orders_per_user': float(avg_orders or 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {}
    
    async def _get_detailed_stats(self) -> Dict[str, any]:
        """Get detailed statistics"""
        try:
            db = await get_database()
            
            # Placeholder for detailed stats
            # In a real implementation, this would query actual system metrics
            return {
                'revenue_today': 0,
                'revenue_week': 0,
                'revenue_month': 0,
                'revenue_total': 0,
                'orders_pending': 0,
                'orders_completed': 0,
                'orders_failed': 0,
                'orders_cancelled': 0,
                'success_rate': 0,
                'popular_packages': {},
                'avg_delivery_time': 0,
                'avg_quality_score': 0,
                'retry_rate': 0,
                'refund_rate': 0,
                'cpu_usage': 0,
                'memory_usage': 0,
                'disk_usage': 0
            }
            
        except Exception as e:
            logger.error(f"Error getting detailed stats: {e}")
            return {}
    
    def _get_default_stats(self) -> Dict[str, any]:
        """Get default stats when database fails"""
        return {
            'total_users': 0,
            'total_orders': 0,
            'revenue_30d': 0.0,
            'active_orders': 0,
            'failed_orders': 0,
            'overdue_orders': 0,
            'pending_refunds': 0,
            'orders_today': 0,
            'users_today': 0,
            'payments_today': 0.0,
            'success_rate_today': 0.0,
            'system_healthy': False
        }
    
    def _get_status_emoji(self, status: str) -> str:
        """Get emoji for order status"""
        status_emojis = {
            'pending_payment': '💰',
            'payment_confirmed': '✅',
            'in_progress': '🔄',
            'delivery_ready': '📦',
            'completed': '🎉',
            'failed': '❌',
            'cancelled': '🚫',
            'refunded': '💸'
        }
        return status_emojis.get(status, '❓')

# Global admin panel manager
_admin_panel_manager = None

def get_admin_panel_manager() -> AdminPanelManager:
    """Get global admin panel manager"""
    global _admin_panel_manager
    if _admin_panel_manager is None:
        _admin_panel_manager = AdminPanelManager()
    return _admin_panel_manager

if __name__ == "__main__":
    # Test admin panel functionality
    async def test_admin_panel():
        admin_manager = AdminPanelManager()
        
        # Test admin check
        is_admin = admin_manager.is_admin(123456)
        print(f"Is admin: {is_admin}")
        
        # Test stats retrieval
        stats = await admin_manager._get_system_stats()
        print(f"System stats: {stats}")
        
        print("✅ Admin panel tests completed")
    
    asyncio.run(test_admin_panel())