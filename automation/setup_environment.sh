#!/bin/bash
# Environment Setup Script for Snapchat Automation System

echo "🔧 Setting up Snapchat Automation Environment"
echo "=============================================="

# Set basic Redis URL for local development
export REDIS_URL="redis://localhost:6379"
echo "✅ REDIS_URL set to localhost:6379"

# Check if Redis is running, if not, provide instructions
if ! redis-cli ping > /dev/null 2>&1; then
    echo "⚠️  Redis not running. To install and start Redis:"
    echo "   brew install redis"
    echo "   brew services start redis"
    echo "   # or run manually: redis-server"
fi

# Set placeholder values for Twilio (user should replace with real values)
if [ -z "$TWILIO_ACCOUNT_SID" ]; then
    export TWILIO_ACCOUNT_SID="your_twilio_account_sid_here"
    echo "⚠️  TWILIO_ACCOUNT_SID set to placeholder - replace with real value"
fi

if [ -z "$TWILIO_AUTH_TOKEN" ]; then
    export TWILIO_AUTH_TOKEN="your_twilio_auth_token_here"
    echo "⚠️  TWILIO_AUTH_TOKEN set to placeholder - replace with real value"
fi

# Set placeholder for Fly.io
if [ -z "$FLY_API_TOKEN" ]; then
    export FLY_API_TOKEN="your_fly_api_token_here"
    echo "⚠️  FLY_API_TOKEN set to placeholder - replace with real value"
fi

# Set placeholder for proxy
if [ -z "$SMARTPROXY_ENDPOINT" ]; then
    export SMARTPROXY_ENDPOINT="your_proxy_endpoint_here"
    export SMARTPROXY_USERNAME="your_proxy_username_here"
    export SMARTPROXY_PASSWORD="your_proxy_password_here"
    echo "⚠️  SMARTPROXY credentials set to placeholders - replace with real values"
fi

# Create .env file for persistence
cat > .env << EOF
# Environment Variables for Snapchat Automation System
REDIS_URL=redis://localhost:6379

# Twilio SMS Service (REPLACE WITH REAL VALUES)
TWILIO_ACCOUNT_SID=your_twilio_account_sid_here
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here

# Fly.io Cloud Deployment (REPLACE WITH REAL VALUE)
FLY_API_TOKEN=your_fly_api_token_here

# Proxy Service (REPLACE WITH REAL VALUES)
SMARTPROXY_ENDPOINT=your_proxy_endpoint_here
SMARTPROXY_USERNAME=your_proxy_username_here
SMARTPROXY_PASSWORD=your_proxy_password_here

# Optional CAPTCHA Solver
CAPTCHA_SOLVER_API_KEY=your_captcha_api_key_here

# Optional Email Provider
EMAIL_PROVIDER_API_KEY=your_email_api_key_here
EOF

echo "✅ Environment file created: .env"
echo ""
echo "📋 NEXT STEPS:"
echo "1. Start Redis: brew install redis && brew services start redis"
echo "2. Get Twilio credentials from https://console.twilio.com"
echo "3. Get Fly.io token from https://fly.io/dashboard"
echo "4. Update .env file with real credentials"
echo "5. Run: source .env"
echo "6. Test system: python3 automation/SYSTEM_IMPLEMENTATION_TEST.py"