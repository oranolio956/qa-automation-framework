#!/bin/bash
"""
Start Bot Services
Launches both the backend server and Telegram bot
"""

echo "🚀 Starting Tinder Automation Services..."
echo "=========================================="

# Check if required dependencies are installed
echo "🔍 Checking dependencies..."

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.9+"
    exit 1
fi

# Check if pip packages are installed
echo "📦 Checking Python packages..."
python3 -c "import telegram, dotenv, redis, flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Missing required packages. Installing..."
    pip3 install python-telegram-bot python-dotenv redis flask
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please configure environment variables."
    exit 1
fi

# Load environment variables from .env into the current shell
set -a
source .env
set +a

# Ensure TELEGRAM_BOT_TOKEN is set
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ TELEGRAM_BOT_TOKEN is not set. Set it in .env or export it: export TELEGRAM_BOT_TOKEN=\"<your_token>\""
    exit 1
fi

echo "✅ Dependencies check complete"
echo ""

# Function to clean up background processes
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
        echo "   Backend stopped"
    fi
    if [ ! -z "$BOT_PID" ]; then
        kill $BOT_PID 2>/dev/null
        echo "   Bot stopped"
    fi
    echo "✅ Services stopped"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start backend server
echo "🖥️  Starting backend server on port 8000..."
cd backend && python3 app.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "⏳ Waiting for backend to initialize..."
sleep 3

# Check if backend is running
curl -s http://localhost:8000/health > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ Backend server is running"
else
    echo "❌ Backend server failed to start"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# Start Telegram bot
echo "🤖 Starting Telegram bot (real account creation)..."
python3 real_snap_bot.py &
BOT_PID=$!

# Wait for bot to start
echo "⏳ Waiting for bot to initialize..."
sleep 3

echo ""
echo "🎉 SERVICES STARTED SUCCESSFULLY!"
echo "=================================="
echo "📊 Backend:     http://localhost:8000/health"
echo "🤖 Telegram:    Bot is polling for messages"
echo ""
echo "📱 Test your bot by messaging it on Telegram!"
echo "   Commands: /start, /help, /snap, or type numbers 1-10"
echo ""
echo "🛑 Press Ctrl+C to stop all services"
echo ""

# Monitor services
while true; do
    # Check if backend is still running
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        echo "❌ Backend process died"
        cleanup
    fi
    
    # Check if bot is still running
    if ! kill -0 $BOT_PID 2>/dev/null; then
        echo "❌ Bot process died"
        cleanup
    fi
    
    # Check backend health
    if ! curl -s http://localhost:8000/health > /dev/null; then
        echo "❌ Backend health check failed"
        cleanup
    fi
    
    sleep 30
done