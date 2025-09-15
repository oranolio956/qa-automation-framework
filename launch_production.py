#!/usr/bin/env python3
"""
Production Launch Script
Launches the /snap command functionality directly for live testing
"""

import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Import the working enhanced integration
import sys
import os
sys.path.append(os.path.dirname(__file__))

from automation.telegram_bot.enhanced_snap_integration import execute_enhanced_snap_command

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ProductionSnapBot:
    def __init__(self):
        self.bot_token = "8163343176:AAGnfDmoyeL7NSU0nLfLMqEohWxL5hZA6_0"
        
    async def snap_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /snap command for live testing"""
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
            
            # Get account count from command args
            account_count = 1
            if context.args and len(context.args) > 0:
                try:
                    account_count = int(context.args[0])
                    account_count = max(1, min(account_count, 100))  # Limit 1-100
                except (ValueError, IndexError):
                    account_count = 1
            
            await update.message.reply_text(
                f"🚀 **PRODUCTION /SNAP INITIATED** 🚀\n\n"
                f"👤 User: {user_id}\n"
                f"📱 Chat: {chat_id}\n"
                f"🎯 Accounts: {account_count}\n\n"
                f"⚡ Enhanced automation system starting..."
            )
            
            # Progress callback for real-time updates
            async def progress_callback(message):
                try:
                    await context.bot.send_message(chat_id=chat_id, text=message)
                except Exception as e:
                    logger.error(f"Progress callback error: {e}")
            
            # Execute the enhanced snap command
            result_id = await execute_enhanced_snap_command(
                user_id=str(user_id),
                chat_id=str(chat_id),
                account_count=account_count,
                progress_callback=progress_callback
            )
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ **PRODUCTION EXECUTION COMPLETED** ✅\n\n"
                     f"🆔 Result ID: {result_id}\n"
                     f"📊 Accounts Processed: {account_count}\n"
                     f"🎉 Enhanced automation system operational!"
            )
            
        except Exception as e:
            logger.error(f"Snap command error: {e}")
            await update.message.reply_text(
                f"❌ **ERROR IN PRODUCTION** ❌\n\n"
                f"Error: {str(e)}\n"
                f"Please check logs for details."
            )
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        await update.message.reply_text(
            "🚀 **PRODUCTION SNAP BOT ONLINE** 🚀\n\n"
            "Commands:\n"
            "• /snap - Create 1 account\n"
            "• /snap 5 - Create 5 accounts\n"
            "• /snap 50 - Create 50 accounts\n\n"
            "⚡ Enhanced automation system ready!"
        )
    
    async def run(self):
        """Run the production bot"""
        try:
            logger.info("🚀 Starting Production Snap Bot...")
            
            # Create application
            application = Application.builder().token(self.bot_token).build()
            
            # Add handlers
            application.add_handler(CommandHandler("start", self.start_command))
            application.add_handler(CommandHandler("snap", self.snap_command))
            
            logger.info("✅ Bot handlers registered")
            logger.info("🎯 Bot token configured")
            logger.info("🚀 Starting bot polling...")
            
            # Start the bot
            await application.run_polling(drop_pending_updates=True)
            
        except Exception as e:
            logger.error(f"❌ Production bot error: {e}")
            raise

if __name__ == "__main__":
    bot = ProductionSnapBot()
    asyncio.run(bot.run())