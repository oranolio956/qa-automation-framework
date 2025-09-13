#!/usr/bin/env python3
"""
Main Telegram Bot Application
Coordinates all bot functionality including orders, payments, and customer service
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional

from telegram import Update, BotCommand
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler, 
    PreCheckoutQueryHandler,
    filters,
    ContextTypes
)

# Import bot components
from .config import TelegramBotConfig, validate_config
from .database import get_database
from .customer_service import get_customer_service_manager
from .order_manager import get_order_lifecycle_manager
from .payment_handler import get_payment_processor
from .admin_panel import get_admin_panel_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TinderBotApplication:
    """Main bot application class"""
    
    def __init__(self):
        self.application = None
        self.cs_manager = get_customer_service_manager()
        self.order_manager = get_order_lifecycle_manager()
        self.payment_processor = get_payment_processor()
        self.admin_manager = get_admin_panel_manager()
        
        # Rate limiting storage
        self.user_message_counts = {}
        self.user_last_message = {}
    
    async def initialize(self):
        """Initialize the bot application"""
        try:
            # Validate configuration
            validate_config()
            
            # Initialize database
            db = await get_database()
            if not db:
                raise RuntimeError("Failed to initialize database")
            
            # Create application
            self.application = Application.builder().token(TelegramBotConfig.BOT_TOKEN).build()
            
            # Register handlers
            self._register_handlers()
            
            # Set bot commands
            await self._set_bot_commands()
            
            logger.info("✅ Bot application initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize bot: {e}")
            return False
    
    def _register_handlers(self):
        """Register all bot message handlers"""
        
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.cs_manager.handle_start_command))
        self.application.add_handler(CommandHandler("help", self.cs_manager.handle_help_command))
        self.application.add_handler(CommandHandler("packages", self._handle_packages_command))
        self.application.add_handler(CommandHandler("order", self._handle_order_command))
        self.application.add_handler(CommandHandler("status", self._handle_status_command))
        self.application.add_handler(CommandHandler("support", self._handle_support_command))
        self.application.add_handler(CommandHandler("referral", self._handle_referral_command))
        self.application.add_handler(CommandHandler("balance", self._handle_balance_command))
        self.application.add_handler(CommandHandler("history", self._handle_history_command))
        self.application.add_handler(CommandHandler("profile", self._handle_profile_command))
        
        # Admin commands
        self.application.add_handler(CommandHandler("admin", self.admin_manager.handle_admin_command))
        self.application.add_handler(CommandHandler("stats", self._handle_admin_stats))
        self.application.add_handler(CommandHandler("users", self._handle_admin_users))
        self.application.add_handler(CommandHandler("orders", self._handle_admin_orders))
        
        # Callback query handlers
        self.application.add_handler(CallbackQueryHandler(self._handle_callback_query))
        
        # Payment handlers
        self.application.add_handler(PreCheckoutQueryHandler(self.payment_processor.process_telegram_pre_checkout))
        self.application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, self.payment_processor.process_telegram_successful_payment))
        
        # Message handlers
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text_message))
        
        # Error handler
        self.application.add_error_handler(self._handle_error)
        
        logger.info("✅ Bot handlers registered")
    
    async def _set_bot_commands(self):
        """Set bot commands for the menu"""
        commands = [
            BotCommand("start", "🚀 Start using the bot"),
            BotCommand("help", "❓ Get help and instructions"),
            BotCommand("packages", "📦 View available packages"),
            BotCommand("order", "🛒 Create a new order"),
            BotCommand("status", "📊 Check order status"),
            BotCommand("support", "💬 Contact customer support"),
            BotCommand("referral", "🔗 Get referral link"),
            BotCommand("balance", "💰 Check account balance"),
            BotCommand("history", "📋 View order history"),
            BotCommand("profile", "👤 Manage your profile")
        ]
        
        await self.application.bot.set_my_commands(commands)
        logger.info("✅ Bot commands set")
    
    async def _handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all callback queries"""
        try:
            query = update.callback_query
            await query.answer()
            
            data = query.data
            user_id = query.from_user.id
            
            # Rate limiting
            if not await self._check_rate_limit(user_id):
                await query.answer("⚠️ Please slow down! Too many requests.", show_alert=True)
                return
            
            # Route callback queries
            if data == "main_menu":
                keyboard = self.cs_manager.create_main_menu_keyboard()
                await query.edit_message_text(
                    "🏠 **Main Menu**\n\nWhat would you like to do?",
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            
            elif data == "show_packages":
                await self.cs_manager.show_packages(update, context)
            
            elif data == "my_orders":
                await self.cs_manager.show_user_orders(update, context)
            
            elif data == "my_account":
                await self.cs_manager.show_user_account(update, context)
            
            elif data == "show_faq":
                await self.cs_manager.show_faq(update, context)
            
            elif data == "contact_support":
                await self.cs_manager.start_support_ticket(update, context)
            
            elif data.startswith("order_package:"):
                package_id = data.split(":")[1]
                await self._handle_package_order(update, context, package_id)
            
            elif data.startswith("order_details:"):
                order_id = data.split(":")[1]
                await self.cs_manager.show_order_details(update, context, order_id)
            
            elif data.startswith("pay_order:"):
                order_id = data.split(":")[1]
                await self._handle_payment_selection(update, context, order_id)
            
            elif data.startswith("cancel_order:"):
                order_id = data.split(":")[1]
                await self._handle_order_cancellation(update, context, order_id)
            
            elif data.startswith("faq_category:"):
                category = data.split(":")[1]
                await self.cs_manager.show_faq_category(update, context, category)
            
            # Admin callbacks
            elif data.startswith("admin_"):
                if not self.admin_manager.is_admin(user_id):
                    await query.answer("❌ Access denied", show_alert=True)
                    return
                await self._handle_admin_callback(update, context, data)
            
            else:
                await query.answer("❓ Unknown action", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error handling callback query: {e}")
            await query.answer("❌ An error occurred. Please try again.", show_alert=True)
    
    async def _handle_package_order(self, update: Update, context: ContextTypes.DEFAULT_TYPE, package_id: str):
        """Handle package ordering process"""
        try:
            user_id = update.effective_user.id
            
            # Show quantity selection
            package = TelegramBotConfig.get_package(package_id)
            if not package:
                await update.callback_query.answer("❌ Package not found", show_alert=True)
                return
            
            message_text = f"""
🛒 **Order {package.name}**

💰 **Price:** ${package.price_usd} each
⏱️ **Delivery:** {package.delivery_time_hours} hours
📱 **Accounts:** {package.tinder_accounts} Tinder"""
            
            if package.snapchat_accounts > 0:
                message_text += f" + {package.snapchat_accounts} Snapchat"
            
            message_text += f"""

**Features:**
{chr(10).join(['✅ ' + feature for feature in package.features[:5]])}

**Select Quantity:**
            """
            
            # Quantity selection keyboard
            keyboard_buttons = []
            quantities = [1, 2, 3, 5, 10]
            
            for qty in quantities:
                total_price, discount = TelegramBotConfig.get_total_price(package_id, qty)
                button_text = f"{qty}x - ${total_price:.2f}"
                if discount > 0:
                    button_text += f" (Save ${discount:.2f})"
                
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        button_text,
                        callback_data=f"order_confirm:{package_id}:{qty}"
                    )
                ])
            
            keyboard_buttons.extend([
                [InlineKeyboardButton("🔢 Custom Quantity", callback_data=f"custom_quantity:{package_id}")],
                [InlineKeyboardButton("◀️ Back to Packages", callback_data="show_packages")]
            ])
            
            await update.callback_query.edit_message_text(
                message_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard_buttons)
            )
            
        except Exception as e:
            logger.error(f"Error handling package order: {e}")
    
    async def _handle_payment_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str):
        """Handle payment method selection"""
        try:
            user_id = update.effective_user.id
            
            # Get order details
            order_details = await self.order_manager.get_order_details(order_id, user_id)
            if not order_details['success']:
                await update.callback_query.answer("❌ Order not found", show_alert=True)
                return
            
            order = order_details['order']
            
            if order['status'] != 'pending_payment':
                await update.callback_query.answer("❌ Order already paid", show_alert=True)
                return
            
            # Create Telegram invoice
            invoice_data = await self.payment_processor.create_telegram_payment_invoice(
                user_id, order_id, order['package'].id, order['quantity']
            )
            
            if not invoice_data['success']:
                await update.callback_query.answer("❌ Payment error", show_alert=True)
                return
            
            # In demo mode, do not attempt real payments
            if invoice_data.get('demo_mode'):
                await update.callback_query.edit_message_text(
                    f"\n💳 Payment (Demo Mode)\n\nThis environment has payments disabled. Simulated invoice for order `{order_id}`:\n\n• Title: {invoice_data['title']}\n• Amount: ${order['total_amount']:.2f}\n\nAsk an administrator to configure PAYMENT_PROVIDER_TOKEN/STRIPE to enable real payments.",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]])
                )
                return
            
            # Send invoice
            await context.bot.send_invoice(
                chat_id=user_id,
                title=invoice_data['title'],
                description=invoice_data['description'],
                payload=invoice_data['payload'],
                provider_token=TelegramBotConfig.PAYMENT_PROVIDER_TOKEN,
                currency=invoice_data['currency'],
                prices=invoice_data['prices'],
                need_name=True,
                need_email=True,
                is_flexible=False
            )
            
        except Exception as e:
            logger.error(f"Error handling payment selection: {e}")
    
    async def _handle_order_cancellation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str):
        """Handle order cancellation"""
        try:
            user_id = update.effective_user.id
            
            result = await self.order_manager.cancel_order(order_id, user_id, "User cancellation")
            
            if result['success']:
                await update.callback_query.edit_message_text(
                    f"✅ **Order Cancelled**\n\nOrder #{order_id[:8]} has been cancelled successfully.\n\nIf payment was made, refund will be processed within 24 hours.",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
                    ]])
                )
            else:
                await update.callback_query.answer(f"❌ {result['error']}", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error handling order cancellation: {e}")
    
    async def _handle_admin_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle admin callback queries"""
        try:
            if data == "admin_dashboard":
                await self.admin_manager.show_admin_dashboard(update, context)
            elif data == "admin_orders":
                await self.admin_manager.manage_orders(update, context)
            elif data == "admin_users":
                await self.admin_manager.manage_users(update, context)
            elif data == "admin_stats":
                await self.admin_manager.show_statistics(update, context)
            elif data.startswith("admin_order_details:"):
                order_id = data.split(":", 1)[1]
                await self.admin_manager.show_order_details(update, context, order_id)
            else:
                await update.callback_query.answer("🚧 Feature coming soon", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error handling admin callback: {e}")
    
    # Command handlers
    async def _handle_packages_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /packages command"""
        await self.cs_manager.show_packages(update, context)
    
    async def _handle_order_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /order command"""
        await self.cs_manager.show_packages(update, context)
    
    async def _handle_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        await self.cs_manager.show_user_orders(update, context)
    
    async def _handle_support_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /support command"""
        await self.cs_manager.start_support_ticket(update, context)
    
    async def _handle_referral_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /referral command"""
        try:
            user_id = update.effective_user.id
            from .database import get_user_manager
            
            user_mgr = await get_user_manager()
            user = await user_mgr.get_user(user_id)
            
            if not user:
                await update.message.reply_text("❌ User not found. Please use /start first.")
                return
            
            referral_code = user['referral_code']
            referral_link = f"https://t.me/{TelegramBotConfig.BOT_URL.split('/')[-1]}?start={referral_code}"
            
            message_text = f"""
🔗 **Your Referral Program**

💰 **Earn {TelegramBotConfig.REFERRAL_BONUS_PERCENTAGE}% commission** on every sale from your referrals!

🎁 **Your Referral Code:** `{referral_code}`
🔗 **Your Referral Link:** 
`{referral_link}`

**How it works:**
1. Share your referral link
2. When someone orders through your link
3. You earn {TelegramBotConfig.REFERRAL_BONUS_PERCENTAGE}% commission
4. Minimum order amount: ${TelegramBotConfig.MIN_REFERRAL_AMOUNT}

**Current Stats:**
👥 Referrals: Loading...
💰 Earnings: Loading...

Share your link and start earning! 💪
            """
            
            await update.message.reply_text(
                message_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📊 My Account", callback_data="my_account")
                ]])
            )
            
        except Exception as e:
            logger.error(f"Error handling referral command: {e}")
            await update.message.reply_text("❌ Error loading referral information.")
    
    async def _handle_balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /balance command"""
        await self.cs_manager.show_user_account(update, context)
    
    async def _handle_history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /history command"""
        await self.cs_manager.show_user_orders(update, context)
    
    async def _handle_profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /profile command"""
        await self.cs_manager.show_user_account(update, context)
    
    async def _handle_admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats admin command"""
        if not self.admin_manager.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Access denied.")
            return
        await self.admin_manager.show_statistics(update, context)
    
    async def _handle_admin_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /users admin command"""
        if not self.admin_manager.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Access denied.")
            return
        await self.admin_manager.manage_users(update, context)
    
    async def _handle_admin_orders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /orders admin command"""
        if not self.admin_manager.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Access denied.")
            return
        await self.admin_manager.manage_orders(update, context)
    
    async def _handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        try:
            user_id = update.effective_user.id
            
            # Rate limiting
            if not await self._check_rate_limit(user_id):
                return
            
            message_text = update.message.text.lower()
            
            # Simple keyword responses
            if any(word in message_text for word in ['help', 'support', 'problem', 'issue']):
                await update.message.reply_text(
                    "👋 Need help? Use /help to see all available commands or /support to contact our team!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("❓ Get Help", callback_data="show_faq"),
                        InlineKeyboardButton("💬 Support", callback_data="contact_support")
                    ]])
                )
            elif any(word in message_text for word in ['order', 'buy', 'purchase']):
                await update.message.reply_text(
                    "🛒 Ready to order? Check out our packages!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("📦 View Packages", callback_data="show_packages")
                    ]])
                )
            elif any(word in message_text for word in ['price', 'cost', 'how much']):
                await self.cs_manager.show_packages(update, context)
            else:
                # Default response
                await update.message.reply_text(
                    "👋 Hello! I can help you with Tinder accounts. Use /help to see what I can do!",
                    reply_markup=self.cs_manager.create_main_menu_keyboard()
                )
                
        except Exception as e:
            logger.error(f"Error handling text message: {e}")
    
    async def _check_rate_limit(self, user_id: int) -> bool:
        """Check if user is within rate limits"""
        try:
            current_time = datetime.now()
            
            # Clean old entries
            if user_id in self.user_last_message:
                if (current_time - self.user_last_message[user_id]).seconds > 60:
                    self.user_message_counts[user_id] = 0
            
            # Update counters
            self.user_last_message[user_id] = current_time
            self.user_message_counts[user_id] = self.user_message_counts.get(user_id, 0) + 1
            
            # Check limits
            if self.user_message_counts[user_id] > TelegramBotConfig.RATE_LIMITS['messages_per_minute']:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return True  # Allow on error
    
    async def _handle_error(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Handle bot errors"""
        logger.error(f"Bot error: {context.error}")
        
        if update and hasattr(update, 'effective_chat'):
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Sorry, something went wrong. Please try again or contact support if the problem persists."
                )
            except Exception as e:
                logger.error(f"Error sending error message: {e}")
    
    async def start(self):
        """Start the bot"""
        try:
            if not await self.initialize():
                raise RuntimeError("Bot initialization failed")
            
            logger.info("🚀 Starting Tinder bot application...")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(drop_pending_updates=True)
            
            # Keep running
            await self.application.updater.idle()
            
        except Exception as e:
            logger.error(f"❌ Error starting bot: {e}")
            raise
        finally:
            if self.application:
                await self.application.stop()
                await self.application.shutdown()
    
    async def stop(self):
        """Stop the bot"""
        try:
            if self.application:
                await self.application.stop()
                await self.application.shutdown()
            logger.info("🛑 Bot stopped")
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")

async def main():
    """Main entry point"""
    try:
        bot = TinderBotApplication()
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Error running bot: {e}")
        exit(1)