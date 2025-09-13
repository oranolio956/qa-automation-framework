#!/usr/bin/env python3
"""
Customer Service System for Telegram Bot
Handles user interactions, support requests, and customer experience
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from .config import TelegramBotConfig, ServicePackage
from .database import get_user_manager, get_order_manager, get_database
from .order_manager import get_order_lifecycle_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SupportTicket:
    """Support ticket data structure"""
    ticket_id: str
    user_id: int
    order_id: Optional[str]
    category: str
    priority: str
    subject: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime
    assigned_to: Optional[int] = None
    resolution: Optional[str] = None

class CustomerServiceManager:
    """Main customer service management class"""
    
    def __init__(self):
        self.support_categories = {
            'order_issue': 'Order Issues',
            'payment_problem': 'Payment Problems',
            'account_quality': 'Account Quality',
            'delivery_delay': 'Delivery Delays',
            'refund_request': 'Refund Request',
            'technical_support': 'Technical Support',
            'general_inquiry': 'General Inquiry'
        }
        
        self.faq_data = self._load_faq_data()
        self.auto_responses = self._load_auto_responses()
    
    async def handle_start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            user = update.effective_user
            
            # Create or update user
            user_mgr = await get_user_manager()
            await user_mgr.create_or_update_user({
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'language_code': user.language_code
            })
            
            # Check for referral code
            referral_code = None
            if context.args:
                referral_code = context.args[0]
                if referral_code.startswith('REF'):
                    await user_mgr.update_user_referral(user.id, referral_code)
            
            # Send welcome message
            keyboard = self.create_main_menu_keyboard()
            
            welcome_text = TelegramBotConfig.WELCOME_MESSAGE
            if referral_code:
                welcome_text += f"\n\n🎁 **Referral Applied!** You'll get special bonuses on your first order."
            
            await update.message.reply_text(
                welcome_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
            # Track user start
            await self._track_user_event(user.id, 'bot_start', {'referral_code': referral_code})
            
        except Exception as e:
            logger.error(f"Error handling start command: {e}")
            await update.message.reply_text(
                "❌ Sorry, there was an error. Please try again or contact support."
            )
    
    async def handle_help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        try:
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📦 View Packages", callback_data="show_packages"),
                    InlineKeyboardButton("🛒 Create Order", callback_data="create_order")
                ],
                [
                    InlineKeyboardButton("📋 My Orders", callback_data="my_orders"),
                    InlineKeyboardButton("💰 My Account", callback_data="my_account")
                ],
                [
                    InlineKeyboardButton("❓ FAQ", callback_data="show_faq"),
                    InlineKeyboardButton("💬 Contact Support", callback_data="contact_support")
                ],
                [
                    InlineKeyboardButton("🔗 Referral Program", callback_data="referral_info")
                ]
            ])
            
            await update.message.reply_text(
                TelegramBotConfig.HELP_MESSAGE,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error handling help command: {e}")
    
    async def show_packages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Display available service packages"""
        try:
            packages = TelegramBotConfig.get_all_packages()
            
            message_text = "📦 **Available Packages:**\n\n"
            keyboard_buttons = []
            
            for package_id, package in packages.items():
                # Create package description
                features_text = '\n'.join([f"  ✅ {feature}" for feature in package.features[:4]])
                if len(package.features) > 4:
                    features_text += f"\n  ✅ And {len(package.features) - 4} more features..."
                
                package_text = f"""
**{package.name}**
💰 Price: ${package.price_usd}
⏱️ Delivery: {package.delivery_time_hours} hours
📱 Accounts: {package.tinder_accounts} Tinder"""
                
                if package.snapchat_accounts > 0:
                    package_text += f" + {package.snapchat_accounts} Snapchat"
                
                package_text += f"""

{features_text}

---
"""
                message_text += package_text
                
                # Add order button
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        f"🛒 Order {package.name}",
                        callback_data=f"order_package:{package_id}"
                    )
                ])
            
            # Add bulk discount info
            message_text += """
💡 **Bulk Discounts Available:**
🔸 3+ packages: 5% off
🔸 5+ packages: 10% off
🔸 10+ packages: 15% off
🔸 25+ packages: 20% off
"""
            
            keyboard_buttons.extend([
                [
                    InlineKeyboardButton("💰 Bulk Orders", callback_data="bulk_order"),
                    InlineKeyboardButton("🤔 Need Help?", callback_data="package_help")
                ],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ])
            
            await update.callback_query.edit_message_text(
                message_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard_buttons)
            )
            
        except Exception as e:
            logger.error(f"Error showing packages: {e}")
    
    async def show_user_orders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user's order history"""
        try:
            user_id = update.effective_user.id
            order_mgr = await get_order_manager()
            orders = await order_mgr.get_user_orders(user_id, limit=10)
            
            if not orders:
                message_text = """
📋 **Your Orders**

You haven't placed any orders yet!

Ready to get started?
                """
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📦 View Packages", callback_data="show_packages")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
                ])
            else:
                message_text = "📋 **Your Orders:**\n\n"
                keyboard_buttons = []
                
                for order in orders[:5]:  # Show last 5 orders
                    status_emoji = self._get_status_emoji(order['status'])
                    package = TelegramBotConfig.get_package(order['package_id'])
                    
                    order_text = f"""
{status_emoji} **Order #{order['order_id'][:8]}**
📦 {package.name if package else 'Unknown Package'}
💰 ${order['total_amount']:.2f}
📅 {order['created_at'].strftime('%Y-%m-%d %H:%M')}

"""
                    message_text += order_text
                    
                    # Add order details button
                    keyboard_buttons.append([
                        InlineKeyboardButton(
                            f"📊 Order #{order['order_id'][:8]}",
                            callback_data=f"order_details:{order['order_id']}"
                        )
                    ])
                
                keyboard_buttons.extend([
                    [
                        InlineKeyboardButton("🔄 Refresh", callback_data="my_orders"),
                        InlineKeyboardButton("📦 New Order", callback_data="show_packages")
                    ],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
                ])
            
            keyboard = InlineKeyboardMarkup(keyboard_buttons)
            
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
            logger.error(f"Error showing user orders: {e}")
    
    async def show_order_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str):
        """Show detailed order information"""
        try:
            user_id = update.effective_user.id
            lifecycle_mgr = get_order_lifecycle_manager()
            
            order_details = await lifecycle_mgr.get_order_details(order_id, user_id)
            
            if not order_details['success']:
                await update.callback_query.answer("❌ Order not found or access denied")
                return
            
            order = order_details['order']
            progress = order_details['progress']
            status_info = order_details['status_info']
            
            # Create detailed message
            status_emoji = self._get_status_emoji(order['status'])
            
            message_text = f"""
{status_emoji} **Order #{order['id'][:8]}**

📦 **Package:** {order['package'].name}
🔢 **Quantity:** {order['quantity']}
💰 **Total:** ${order['total_amount']:.2f}
"""
            
            if order['discount_amount'] > 0:
                message_text += f"💸 **Discount:** ${order['discount_amount']:.2f}\n"
            
            message_text += f"""
📅 **Created:** {order['created_at'].strftime('%Y-%m-%d %H:%M')}
⏰ **Expected:** {order['expected_delivery'].strftime('%Y-%m-%d %H:%M') if order['expected_delivery'] else 'TBD'}

**Status:** {status_info['message']}
{status_info['description']}
"""
            
            # Add progress information
            if progress['accounts_delivered'] > 0:
                message_text += f"""

📊 **Progress:** {progress['overall_progress']:.1f}%
📱 **Accounts Delivered:** {progress['accounts_delivered']}
"""
            
            # Add account breakdown if available
            if progress['account_breakdown']:
                message_text += "\n**Account Breakdown:**\n"
                for acc_type, details in progress['account_breakdown'].items():
                    message_text += f"  • {acc_type.title()}: {details['count']} (Quality: {details['avg_quality']:.1f}/100)\n"
            
            if order['notes']:
                message_text += f"\n**Notes:** {order['notes']}"
            
            # Create keyboard based on status
            keyboard_buttons = []
            
            if order['status'] == 'pending_payment':
                keyboard_buttons.append([
                    InlineKeyboardButton("💳 Pay Now", callback_data=f"pay_order:{order_id}")
                ])
            
            if status_info['can_cancel']:
                keyboard_buttons.append([
                    InlineKeyboardButton("❌ Cancel Order", callback_data=f"cancel_order:{order_id}")
                ])
            
            keyboard_buttons.extend([
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data=f"order_details:{order_id}"),
                    InlineKeyboardButton("💬 Support", callback_data=f"order_support:{order_id}")
                ],
                [
                    InlineKeyboardButton("📋 My Orders", callback_data="my_orders"),
                    InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
                ]
            ])
            
            await update.callback_query.edit_message_text(
                message_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard_buttons)
            )
            
        except Exception as e:
            logger.error(f"Error showing order details {order_id}: {e}")
    
    async def show_user_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user account information and statistics"""
        try:
            user_id = update.effective_user.id
            user_mgr = await get_user_manager()
            
            user = await user_mgr.get_user(user_id)
            stats = await user_mgr.get_user_stats(user_id)
            
            if not user:
                await update.callback_query.answer("❌ User not found")
                return
            
            # Create account summary
            message_text = f"""
👤 **Your Account**

🏷️ **Name:** {user['first_name']} {user['last_name'] or ''}
📱 **Telegram:** @{user['username'] or 'N/A'}
🌐 **Language:** {user['language_code']}
📅 **Member Since:** {user['created_at'].strftime('%Y-%m-%d')}

📊 **Statistics:**
🛒 **Total Orders:** {stats.get('total_orders', 0)}
💰 **Total Spent:** ${stats.get('total_spent', 0):.2f}
✅ **Success Rate:** {stats.get('success_rate', 0):.1f}%
⏳ **Pending Orders:** {stats.get('pending_orders', 0)}

🔗 **Referral Program:**
👥 **Referrals Made:** {stats.get('referrals_made', 0)}
💵 **Referral Earnings:** ${stats.get('referral_earnings', 0):.2f}
🎁 **Your Referral Code:** `{user['referral_code']}`
"""
            
            # Add premium status if applicable
            if user.get('is_premium'):
                message_text += "\n⭐ **Premium Member** - Enjoy exclusive benefits!"
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📋 Order History", callback_data="my_orders"),
                    InlineKeyboardButton("🔗 Referral Info", callback_data="referral_info")
                ],
                [
                    InlineKeyboardButton("⚙️ Settings", callback_data="account_settings"),
                    InlineKeyboardButton("💬 Support", callback_data="contact_support")
                ],
                [
                    InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
                ]
            ])
            
            await update.callback_query.edit_message_text(
                message_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error showing user account: {e}")
    
    async def show_faq(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show frequently asked questions"""
        try:
            faq_categories = list(self.faq_data.keys())
            
            message_text = "❓ **Frequently Asked Questions**\n\nChoose a category:"
            
            keyboard_buttons = []
            for category in faq_categories:
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        f"❓ {category.replace('_', ' ').title()}",
                        callback_data=f"faq_category:{category}"
                    )
                ])
            
            keyboard_buttons.extend([
                [
                    InlineKeyboardButton("💬 Still Need Help?", callback_data="contact_support")
                ],
                [
                    InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
                ]
            ])
            
            await update.callback_query.edit_message_text(
                message_text,
                reply_markup=InlineKeyboardMarkup(keyboard_buttons)
            )
            
        except Exception as e:
            logger.error(f"Error showing FAQ: {e}")
    
    async def show_faq_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category: str):
        """Show FAQ for specific category"""
        try:
            if category not in self.faq_data:
                await update.callback_query.answer("❌ Category not found")
                return
            
            faqs = self.faq_data[category]
            
            message_text = f"❓ **{category.replace('_', ' ').title()}**\n\n"
            
            for i, faq in enumerate(faqs, 1):
                message_text += f"**{i}. {faq['question']}**\n{faq['answer']}\n\n"
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("◀️ Back to FAQ", callback_data="show_faq"),
                    InlineKeyboardButton("💬 Still Need Help?", callback_data="contact_support")
                ],
                [
                    InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
                ]
            ])
            
            await update.callback_query.edit_message_text(
                message_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error showing FAQ category {category}: {e}")
    
    async def start_support_ticket(self, update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str = None):
        """Start support ticket creation process"""
        try:
            message_text = """
💬 **Contact Support**

What can we help you with today?
            """
            
            keyboard_buttons = []
            
            for cat_id, cat_name in self.support_categories.items():
                callback_data = f"support_category:{cat_id}"
                if order_id:
                    callback_data += f":{order_id}"
                
                keyboard_buttons.append([
                    InlineKeyboardButton(cat_name, callback_data=callback_data)
                ])
            
            keyboard_buttons.extend([
                [
                    InlineKeyboardButton("◀️ Back", callback_data="main_menu")
                ]
            ])
            
            await update.callback_query.edit_message_text(
                message_text,
                reply_markup=InlineKeyboardMarkup(keyboard_buttons)
            )
            
        except Exception as e:
            logger.error(f"Error starting support ticket: {e}")
    
    def create_main_menu_keyboard(self) -> InlineKeyboardMarkup:
        """Create main menu keyboard"""
        keyboard = [
            [
                InlineKeyboardButton("📦 View Packages", callback_data="show_packages"),
                InlineKeyboardButton("🛒 Create Order", callback_data="create_order")
            ],
            [
                InlineKeyboardButton("📋 My Orders", callback_data="my_orders"),
                InlineKeyboardButton("👤 My Account", callback_data="my_account")
            ],
            [
                InlineKeyboardButton("❓ FAQ", callback_data="show_faq"),
                InlineKeyboardButton("💬 Support", callback_data="contact_support")
            ],
            [
                InlineKeyboardButton("🔗 Referral Program", callback_data="referral_info")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
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
    
    def _load_faq_data(self) -> Dict[str, List[Dict[str, str]]]:
        """Load FAQ data"""
        return {
            'general': [
                {
                    'question': 'What is this service?',
                    'answer': 'We provide high-quality, verified Tinder accounts with phone and email verification, anti-ban protection, and account warming services.'
                },
                {
                    'question': 'How long does delivery take?',
                    'answer': 'Delivery times vary by package: Starter Pack (1 hour), Growth Pack (2 hours), Business Pack (4 hours), Enterprise Pack (6 hours).'
                },
                {
                    'question': 'Are the accounts safe to use?',
                    'answer': 'Yes! All accounts include anti-ban protection, are fully verified, and go through our warming process to ensure safety.'
                }
            ],
            'orders': [
                {
                    'question': 'How do I track my order?',
                    'answer': 'Use /status command or tap "My Orders" to see real-time progress of your order creation and delivery.'
                },
                {
                    'question': 'Can I cancel my order?',
                    'answer': 'Yes, you can cancel orders that haven\'t started processing yet. Refunds are processed automatically for eligible cancellations.'
                },
                {
                    'question': 'What if I need more accounts later?',
                    'answer': 'You can place additional orders anytime! Bulk discounts apply for larger quantities.'
                }
            ],
            'payment': [
                {
                    'question': 'What payment methods do you accept?',
                    'answer': 'We accept Telegram payments and credit/debit cards via Stripe. All transactions are secure and encrypted.'
                },
                {
                    'question': 'Is my payment information safe?',
                    'answer': 'Absolutely! We use industry-standard encryption and don\'t store your payment details. All processing is handled by secure payment providers.'
                },
                {
                    'question': 'Can I get a refund?',
                    'answer': 'Yes, we offer refunds for orders that haven\'t started processing, or if we can\'t deliver as promised. Contact support for assistance.'
                }
            ],
            'technical': [
                {
                    'question': 'What if an account gets banned?',
                    'answer': 'We provide replacements for accounts that get banned within the first 30 days (7 days for Starter Pack), subject to our terms.'
                },
                {
                    'question': 'Do you provide account details?',
                    'answer': 'Yes! Once delivered, you\'ll receive login credentials, email access, phone numbers (where applicable), and usage guidelines.'
                },
                {
                    'question': 'Can I customize the profiles?',
                    'answer': 'Business and Enterprise packages include custom profile creation. Other packages come with pre-optimized profiles.'
                }
            ]
        }
    
    def _load_auto_responses(self) -> Dict[str, str]:
        """Load automatic response templates"""
        return {
            'order_created': 'Your order has been created! Complete payment to start processing.',
            'payment_confirmed': 'Payment confirmed! Your accounts are now being created.',
            'in_progress': 'Your accounts are being created and verified. We\'ll notify you when ready!',
            'completed': 'Your order is complete! Check your account details and enjoy your new accounts.',
            'failed': 'There was an issue with your order. Our team has been notified and will resolve it quickly.',
        }
    
    async def _track_user_event(self, user_id: int, event_type: str, data: Dict[str, Any] = None):
        """Track user interaction events"""
        try:
            db = await get_database()
            query = """
            INSERT INTO analytics (event_type, user_id, event_data)
            VALUES ($1, $2, $3)
            """
            
            async with db.postgres_pool.acquire() as connection:
                await connection.execute(
                    query, event_type, user_id,
                    json.dumps(data) if data else None
                )
                
        except Exception as e:
            logger.error(f"Error tracking user event: {e}")

# Global customer service manager
_customer_service_manager = None

def get_customer_service_manager() -> CustomerServiceManager:
    """Get global customer service manager"""
    global _customer_service_manager
    if _customer_service_manager is None:
        _customer_service_manager = CustomerServiceManager()
    return _customer_service_manager

if __name__ == "__main__":
    # Test customer service functionality
    async def test_customer_service():
        cs_manager = CustomerServiceManager()
        
        print("FAQ Categories:", list(cs_manager.faq_data.keys()))
        print("Support Categories:", cs_manager.support_categories)
        print("✅ Customer service tests completed")
    
    asyncio.run(test_customer_service())