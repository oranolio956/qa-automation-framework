#!/usr/bin/env python3
"""
Simple Real Automation Bot - NO FAKE ACCOUNTS
This bot refuses to create fake/demo accounts and only operates with real automation systems
"""

import asyncio
import logging
import json
import random
import os
from datetime import datetime
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor
import functools

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load from parent directory
    env_path = os.path.join(os.path.dirname(__file__), '../../.env')
    load_dotenv(env_path)
    print(f"✅ Environment loaded from: {env_path}")
except ImportError:
    print("⚠️ python-dotenv not available, using system environment variables")
except Exception as e:
    print(f"⚠️ Warning loading .env: {e}")

from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
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
try:
    from .config import TelegramBotConfig, validate_config
except ImportError:
    from .config import TelegramBotConfig, validate_config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleRealAutomationBot:
    """Simple bot that only operates with REAL automation - NO FAKE ACCOUNTS"""
    
    def __init__(self):
        self.config = TelegramBotConfig()
        
        # Validate configuration
        if not validate_config():
            raise ValueError("Invalid bot configuration")
        
        # Create application
        self.application = Application.builder().token(self.config.BOT_TOKEN).build()
        
        # Rate limiting
        self.user_message_counts = {}
        self.user_last_message = {}
        
        # Setup handlers
        self._setup_handlers()
        
        logger.info("✅ Simple Real Automation Bot initialized")
    
    def _setup_handlers(self):
        """Setup command and message handlers"""
        
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("snap", self.snap_command))
        
        # Callback handlers
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Message handlers
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        logger.info("✅ Bot handlers configured")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            user_id = update.effective_user.id
            username = update.effective_user.username or "Unknown"
            
            welcome_message = (
                "🚀 **REAL SNAPCHAT AUTOMATION** 🚀\\n\\n"
                "⚡ **NO FAKE/DEMO ACCOUNTS**\\n"
                "✅ Only REAL working Snapchat accounts\\n"
                "🔥 Real phone verification\\n"
                "📧 Real email addresses\\n"
                "🛡️ Advanced anti-detection\\n\\n"
                "🎯 **Commands:**\\n"
                "• `/snap` - Check automation status\\n"
                "• `/help` - Show help menu\\n\\n"
                "⚠️ **Notice:** This bot only creates REAL accounts.\\n"
                "🚫 No fake/demo accounts will be provided."
            )
            
            keyboard = [[
                InlineKeyboardButton("🔍 Check System Status", callback_data="check_status"),
                InlineKeyboardButton("📞 Contact Support", callback_data="support")
            ]]
            
            await update.message.reply_text(
                welcome_message,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            logger.info(f"User {user_id} ({username}) started the bot")
            
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await update.message.reply_text("❌ Error processing start command. Please try again.")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        try:
            help_message = (
                "🤖 **REAL AUTOMATION BOT HELP** 🤖\\n\\n"
                "📝 **Available Commands:**\\n"
                "• `/start` - Start the bot\\n"
                "• `/snap` - Check automation system status\\n"
                "• `/help` - Show this help message\\n\\n"
                "🚫 **Important Notice:**\\n"
                "This bot ONLY creates REAL Snapchat accounts.\\n"
                "No fake, demo, or simulated accounts are provided.\\n\\n"
                "⚙️ **System Requirements:**\\n"
                "• Real Android emulators\\n"
                "• Real SMS verification\\n"
                "• Real email services\\n"
                "• Working automation components\\n\\n"
                "📞 **Need Help?** Contact support for assistance."
            )
            
            keyboard = [[
                InlineKeyboardButton("🔍 System Status", callback_data="check_status"),
                InlineKeyboardButton("📞 Support", callback_data="support")
            ]]
            
            await update.message.reply_text(
                help_message,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error in help command: {e}")
            await update.message.reply_text("❌ Error showing help. Please try again.")
    
    def _check_automation_status(self) -> tuple[bool, str, list[str]]:
        """Check if real automation components are available"""
        
        missing_components = []
        status_details = []
        
        # Check environment variables for automation services
        required_env_vars = {
            'TWILIO_ACCOUNT_SID': 'SMS verification service',
            'TWILIO_AUTH_TOKEN': 'SMS authentication',
            'TELEGRAM_BOT_TOKEN': 'Telegram integration'
        }
        
        for env_var, description in required_env_vars.items():
            if os.getenv(env_var):
                status_details.append(f"✅ {description}")
            else:
                missing_components.append(f"❌ {description}")
                status_details.append(f"❌ {description} (missing {env_var})")
        
        # Check for automation component files
        automation_files = {
            'automation/snapchat/stealth_creator.py': 'Snapchat automation',
            'automation/android/emulator_manager.py': 'Android emulation',
            'utils/sms_verifier.py': 'SMS verification',
            'automation/email/email_integration.py': 'Email automation'
        }
        
        for file_path, description in automation_files.items():
            full_path = os.path.join(os.path.dirname(__file__), '../../', file_path)
            if os.path.exists(full_path):
                status_details.append(f"✅ {description} file")
            else:
                missing_components.append(f"❌ {description}")
                status_details.append(f"❌ {description} file missing")
        
        # Overall status
        is_ready = len(missing_components) == 0
        
        return is_ready, status_details, missing_components
    
    async def snap_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /snap command - check automation status"""
        try:
            user_id = update.effective_user.id
            
            # Check automation status
            is_ready, status_details, missing_components = self._check_automation_status()
            
            if is_ready:
                status_message = (
                    "🚀 **REAL AUTOMATION STATUS** 🚀\\n\\n"
                    "✅ **SYSTEM READY**\\n\\n"
                    "📊 **Component Status:**\\n"
                    + "\\n".join(status_details) +
                    "\\n\\n🔥 **Ready to create REAL accounts!**\\n"
                    "⚠️ All accounts will be verified and working.\\n\\n"
                    "💰 **Pricing:** Contact support for current rates"
                )
                
                keyboard = [[
                    InlineKeyboardButton("💬 Contact for Order", callback_data="contact_order"),
                    InlineKeyboardButton("📞 Support", callback_data="support")
                ]]
            else:
                status_message = (
                    "❌ **AUTOMATION SYSTEM OFFLINE** ❌\\n\\n"
                    "🚫 **Cannot create accounts at this time**\\n\\n"
                    "📊 **System Status:**\\n"
                    + "\\n".join(status_details) +
                    "\\n\\n⚙️ **Missing Components:**\\n"
                    + "\\n".join(missing_components) +
                    "\\n\\n🔧 Please contact admin to fix the system."
                )
                
                keyboard = [[
                    InlineKeyboardButton("📞 Contact Admin", callback_data="contact_admin"),
                    InlineKeyboardButton("🔄 Retry Check", callback_data="check_status")
                ]]
            
            await update.message.reply_text(
                status_message,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            logger.info(f"User {user_id} checked automation status: {'Ready' if is_ready else 'Not Ready'}")
            
        except Exception as e:
            logger.error(f"Error in snap command: {e}")
            await update.message.reply_text(
                "❌ **ERROR CHECKING SYSTEM**\\n\\n"
                "Could not verify automation status.\\n"
                "Please contact support for assistance.",
                parse_mode='Markdown'
            )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        try:
            query = update.callback_query
            await query.answer()
            
            user_id = query.from_user.id
            data = query.data
            
            if data == "check_status":
                # Re-run automation status check
                is_ready, status_details, missing_components = self._check_automation_status()
                
                if is_ready:
                    message = (
                        "🚀 **AUTOMATION STATUS: READY** 🚀\\n\\n"
                        "✅ All systems operational\\n\\n"
                        "📊 **Components:**\\n"
                        + "\\n".join(status_details) +
                        "\\n\\n🔥 Ready for real account creation!"
                    )
                else:
                    message = (
                        "❌ **AUTOMATION STATUS: OFFLINE** ❌\\n\\n"
                        "📊 **System Check:**\\n"
                        + "\\n".join(status_details) +
                        "\\n\\n🔧 Admin intervention required."
                    )
                
                await query.edit_message_text(
                    text=message,
                    parse_mode='Markdown'
                )
            
            elif data in ["support", "contact_admin", "contact_order"]:
                support_message = (
                    "📞 **CONTACT SUPPORT** 📞\\n\\n"
                    "🔧 **Technical Issues:** @admin\\n"
                    "💰 **Orders & Pricing:** @sales\\n"
                    "❓ **General Help:** @support\\n\\n"
                    "⚡ Response time: Usually within 2-4 hours\\n"
                    "🌍 Available 24/7"
                )
                
                await query.edit_message_text(
                    text=support_message,
                    parse_mode='Markdown'
                )
            
            logger.info(f"User {user_id} clicked button: {data}")
            
        except Exception as e:
            logger.error(f"Error in button callback: {e}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        try:
            user_id = update.effective_user.id
            message_text = update.message.text.lower()
            
            # Rate limiting
            if not await self._check_rate_limit(user_id):
                await update.message.reply_text(
                    "⚠️ Rate limit exceeded. Please wait before sending another message."
                )
                return
            
            # Handle common queries
            if any(word in message_text for word in ["demo", "test", "free", "trial"]):
                response = (
                    "🚫 **NO DEMO/FAKE ACCOUNTS** 🚫\\n\\n"
                    "This bot only creates REAL Snapchat accounts.\\n"
                    "No demos, tests, or fake accounts are provided.\\n\\n"
                    "💰 All accounts are paid services with real verification.\\n"
                    "📞 Contact support for pricing and orders."
                )
            
            elif any(word in message_text for word in ["price", "cost", "buy", "order"]):
                response = (
                    "💰 **PRICING INFORMATION** 💰\\n\\n"
                    "📞 Contact support for current pricing:\\n"
                    "• Real verified Snapchat accounts\\n"
                    "• Bulk discounts available\\n"
                    "• Custom requirements accepted\\n\\n"
                    "⚡ All accounts come with:\\n"
                    "✅ Real phone verification\\n"
                    "✅ Real email addresses\\n"
                    "✅ Working login credentials"
                )
            
            elif any(word in message_text for word in ["status", "ready", "online"]):
                is_ready, _, _ = self._check_automation_status()
                response = (
                    f"📊 **System Status:** {'🟢 ONLINE' if is_ready else '🔴 OFFLINE'}\\n\\n"
                    "Use `/snap` for detailed status check."
                )
            
            else:
                response = (
                    "🤖 **COMMAND NOT RECOGNIZED** 🤖\\n\\n"
                    "Available commands:\\n"
                    "• `/start` - Start the bot\\n"
                    "• `/snap` - Check system status\\n"
                    "• `/help` - Show help\\n\\n"
                    "💬 Or use the buttons for quick actions."
                )
            
            keyboard = [[
                InlineKeyboardButton("🔍 Check Status", callback_data="check_status"),
                InlineKeyboardButton("📞 Support", callback_data="support")
            ]]
            
            await update.message.reply_text(
                response,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await update.message.reply_text("❌ Error processing your message. Please try again.")
    
    async def _check_rate_limit(self, user_id: int) -> bool:
        """Check if user is within rate limits"""
        try:
            import time
            current_time = time.time()
            
            # Initialize user tracking if not exists
            if user_id not in self.user_message_counts:
                self.user_message_counts[user_id] = 0
                self.user_last_message[user_id] = current_time
            
            # Reset counter if minute has passed
            if current_time - self.user_last_message[user_id] > 60:
                self.user_message_counts[user_id] = 0
                self.user_last_message[user_id] = current_time
            
            # Check rate limit (5 messages per minute)
            if self.user_message_counts[user_id] >= 5:
                return False
            
            # Increment counter
            self.user_message_counts[user_id] += 1
            return True
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return True  # Allow if error
    
    async def run(self):
        """Run the bot"""
        try:
            # Set up bot commands
            commands = [
                BotCommand("start", "Start the bot"),
                BotCommand("help", "Show help message"),
                BotCommand("snap", "Check automation system status")
            ]
            await self.application.bot.set_my_commands(commands)
            
            logger.info("🚀 Starting Simple Real Automation Bot...")
            logger.info("🚫 NO FAKE/DEMO ACCOUNTS WILL BE CREATED")
            logger.info("✅ Only real automation systems accepted")
            
            # Start the bot
            await self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            
        except Exception as e:
            logger.error(f"Error running bot: {e}")
            raise

async def main():
    """Main entry point"""
    try:
        bot = SimpleRealAutomationBot()
        await bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())