#!/usr/bin/env python3
"""
Bot Startup Script
Provides multiple run modes for the Telegram bot
"""

import asyncio
import sys
import os
import argparse
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from telegram_bot.main_bot import TinderBotApplication
from telegram_bot.webhook_server import run_webhook_server
from telegram_bot.config import TelegramBotConfig, validate_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_polling_mode():
    """Run bot in polling mode (development)"""
    logger.info("🔄 Starting bot in polling mode...")
    
    try:
        bot = TinderBotApplication()
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        raise

async def run_webhook_mode(host: str = "0.0.0.0", port: int = 8000):
    """Run bot in webhook mode (production)"""
    logger.info(f"🌐 Starting bot in webhook mode on {host}:{port}...")
    
    try:
        await run_webhook_server(host, port)
    except KeyboardInterrupt:
        logger.info("Webhook server stopped by user")
    except Exception as e:
        logger.error(f"Error running webhook server: {e}")
        raise

async def test_configuration():
    """Test bot configuration and connections"""
    logger.info("🔧 Testing bot configuration...")
    
    try:
        # Test configuration
        validate_config()
        logger.info("✅ Configuration valid")
        
        # Test database connection
        from telegram_bot.database import get_database
        db = await get_database()
        logger.info("✅ Database connection successful")
        
        # Test bot token
        from telegram import Bot
        bot = Bot(TelegramBotConfig.BOT_TOKEN)
        me = await bot.get_me()
        logger.info(f"✅ Bot token valid: @{me.username}")
        
        # Test payment processor
        from telegram_bot.payment_handler import get_payment_processor
        payment_processor = get_payment_processor()
        logger.info("✅ Payment processor initialized")
        
        logger.info("🎉 All tests passed! Bot is ready to run.")
        return True
        
    except Exception as e:
        logger.error(f"❌ Configuration test failed: {e}")
        return False

def setup_environment():
    """Setup environment from .env file"""
    env_file = Path(__file__).parent / '.env'
    
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
        logger.info(f"✅ Loaded environment from {env_file}")
    else:
        logger.warning(f"⚠️ No .env file found at {env_file}")
        logger.info("Create .env file using .env.example as template")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Tinder Telegram Bot')
    parser.add_argument('mode', choices=['polling', 'webhook', 'test'], 
                       help='Bot run mode')
    parser.add_argument('--host', default='0.0.0.0', 
                       help='Host for webhook mode (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8000,
                       help='Port for webhook mode (default: 8000)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Setup logging
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # Setup environment
    setup_environment()
    
    # Print startup info
    print("=" * 60)
    print("🤖 Tinder Account Services Telegram Bot")
    print("=" * 60)
    print(f"Mode: {args.mode}")
    print(f"Bot URL: {TelegramBotConfig.BOT_URL}")
    print("=" * 60)
    
    try:
        if args.mode == 'test':
            # Test mode
            result = asyncio.run(test_configuration())
            sys.exit(0 if result else 1)
            
        elif args.mode == 'polling':
            # Polling mode
            asyncio.run(run_polling_mode())
            
        elif args.mode == 'webhook':
            # Webhook mode
            asyncio.run(run_webhook_mode(args.host, args.port))
            
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()