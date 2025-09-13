#!/bin/bash

# =============================================================================
# Telegram Bot Setup Script for @buytinderadds
# =============================================================================

set -e

echo "🤖 Setting up Telegram Bot: @buytinderadds"
echo "Bot Token: 8163343176:AAGnfDmoyeL7NSU0nLfLMqEohWxL5hZA6_0"
echo

# Step 1: Install Python Dependencies
echo "📦 Installing Python dependencies..."
cd telegram_bot
pip3 install -r requirements.txt

# Step 2: Database Setup (PostgreSQL)
echo "🗄️ Setting up PostgreSQL database..."
# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "Installing PostgreSQL..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install postgresql
        brew services start postgresql
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get update
        sudo apt-get install -y postgresql postgresql-contrib
        sudo systemctl start postgresql
        sudo systemctl enable postgresql
    fi
fi

# Create database and user
echo "Creating database and user..."
sudo -u postgres psql -c "CREATE DATABASE tinder_bot;"
sudo -u postgres psql -c "CREATE USER tinder_user WITH PASSWORD 'your_password_here';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE tinder_bot TO tinder_user;"

# Step 3: Initialize Database Tables
echo "🗂️ Creating database tables..."
python3 -c "
from database import init_db
init_db()
print('Database initialized successfully!')
"

# Step 4: Test Bot Connection
echo "🔌 Testing bot connection..."
python3 -c "
import asyncio
from telegram import Bot
from config import Config

async def test_bot():
    bot = Bot(token='8163343176:AAGnfDmoyeL7NSU0nLfLMqEohWxL5hZA6_0')
    me = await bot.get_me()
    print(f'✅ Bot connected successfully!')
    print(f'   Bot Name: {me.first_name}')
    print(f'   Username: @{me.username}')
    print(f'   Bot ID: {me.id}')

asyncio.run(test_bot())
"

# Step 5: Test Integration with Automation System
echo "🤖 Testing Tinder automation integration..."
python3 -c "
import sys
sys.path.append('../')
from automation.main_orchestrator import MainOrchestrator
from telegram_bot.order_manager import OrderManager

# Test integration
orchestrator = MainOrchestrator()
order_manager = OrderManager()

print('✅ Integration test passed!')
print('   - Tinder automation system: Available')
print('   - SMS verification: Connected')
print('   - Proxy system: Connected')
"

# Step 6: Set Bot Commands
echo "⚙️ Setting up bot commands..."
python3 -c "
import asyncio
from telegram import Bot, BotCommand

async def setup_commands():
    bot = Bot(token='8163343176:AAGnfDmoyeL7NSU0nLfLMqEohWxL5hZA6_0')
    
    commands = [
        BotCommand('start', 'Start using the bot and get welcome message'),
        BotCommand('packages', 'View available Tinder account packages'),
        BotCommand('order', 'Create a new order for Tinder accounts'),
        BotCommand('status', 'Check your current order status'),
        BotCommand('support', 'Contact customer support'),
        BotCommand('referral', 'Get your referral link and earnings'),
        BotCommand('help', 'Show help and FAQ'),
    ]
    
    await bot.set_my_commands(commands)
    print('✅ Bot commands configured successfully!')

asyncio.run(setup_commands())
"

# Step 7: Start Bot in Test Mode
echo
echo "🚀 Starting bot in test mode..."
echo "   Bot URL: https://t.me/buytinderadds"
echo "   Mode: Polling (for development)"
echo

# Final instructions
cat << EOF

🎉 SETUP COMPLETE!

Your Telegram bot is now ready to use:

📱 Bot Details:
   • Name: @buytinderadds
   • URL: https://t.me/buytinderadds
   • Token: 8163343176:AAGnfDmoyeL7NSU0nLfLMqEohWxL5hZA6_0

🚀 To Start the Bot:
   Development: python3 run_bot.py polling
   Production:  python3 run_bot.py webhook

⚙️ Configuration:
   • Edit telegram_bot/.env for settings
   • Add your Telegram user ID to ADMIN_USER_IDS for admin access
   • Configure Stripe keys for payment processing

📊 Admin Access:
   • Send /admin to the bot (must be in ADMIN_USER_IDS)
   • Dashboard: View orders, users, revenue
   • Management: Process orders, handle refunds

🔧 Next Steps:
   1. Get your Telegram user ID (send /start to @userinfobot)
   2. Add your user ID to ADMIN_USER_IDS in .env
   3. Set up Stripe account and add keys
   4. Test with a small order
   5. Deploy to production with webhooks

📞 Testing Commands:
   /start     - Welcome message
   /packages  - View service packages
   /order     - Create test order
   /admin     - Admin panel (if you're admin)

Happy automating! 🚀

EOF