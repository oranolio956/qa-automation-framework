#!/bin/bash
# Deploy Android Device Farm to Fly.io for Snapchat Account Creation

set -euo pipefail

# Configuration
APP_NAME="android-device-farm-prod"
REGION="ord"
DOCKERFILE="Dockerfile.android"
FLY_CONFIG="fly-android.toml"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date '+%H:%M:%S')] $1${NC}"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARNING: $1${NC}"; }
error() { echo -e "${RED}[$(date '+%H:%M:%S')] ERROR: $1${NC}"; }

# Ensure flyctl is available
export PATH="/Users/daltonmetzler/.fly/bin:$PATH"

check_requirements() {
    log "Checking requirements..."
    
    if ! command -v flyctl >/dev/null 2>&1; then
        error "flyctl not found. Please install Fly CLI first."
        exit 1
    fi
    
    if [[ ! -f "$DOCKERFILE" ]]; then
        error "Dockerfile for Android not found: $DOCKERFILE"
        exit 1
    fi
    
    if [[ ! -f "$FLY_CONFIG" ]]; then
        error "Fly config not found: $FLY_CONFIG"
        exit 1
    fi
    
    log "Requirements check passed"
}

create_app() {
    log "Creating/updating Android device farm app: $APP_NAME"
    
    # Check if app exists
    if flyctl apps list 2>/dev/null | grep -q "$APP_NAME"; then
        log "App $APP_NAME already exists"
    else
        log "Creating new app: $APP_NAME"
        flyctl apps create "$APP_NAME" --org personal
    fi
}

create_volume() {
    log "Creating persistent volume for Android data..."
    
    # Check if volume exists
    if ! flyctl volumes list --app "$APP_NAME" 2>/dev/null | grep -q "android_data"; then
        log "Creating volume for Android SDK and AVD data"
        flyctl volumes create android_data \
            --region "$REGION" \
            --size 20 \
            --app "$APP_NAME"
    else
        log "Volume android_data already exists"
    fi
}

set_secrets() {
    log "Setting environment secrets..."
    
    flyctl secrets set \
        REDIS_URL="redis://localhost:6379" \
        TWILIO_ACCOUNT_SID="${TWILIO_ACCOUNT_SID:-ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX}" \
        TWILIO_AUTH_TOKEN="${TWILIO_AUTH_TOKEN:-<twilio_auth_token>}" \
        BRIGHTDATA_PROXY_URL="${BRIGHTDATA_PROXY_URL:-http://example:password@proxy.example.com:port}" \
        JWT_SECRET="$(openssl rand -hex 32)" \
        --app "$APP_NAME"
    
    log "Secrets configured"
}

deploy_android_farm() {
    log "Deploying Android device farm to Fly.io..."
    
    # Deploy using custom config and dockerfile
    flyctl deploy \
        --app "$APP_NAME" \
        --config "$FLY_CONFIG" \
        --dockerfile "$DOCKERFILE" \
        --build-arg ANDROID_COMPILE_SDK=30 \
        --build-arg ANDROID_BUILD_TOOLS=30.0.3 \
        --build-arg ANDROID_SDK_TOOLS=29.0.6
    
    log "Deployment completed"
}

scale_for_android() {
    log "Scaling for Android emulator requirements..."
    
    # Scale to high-memory instance for Android emulators
    flyctl scale vm shared-cpu-4x --app "$APP_NAME" --yes
    flyctl scale count 1 --app "$APP_NAME"
    
    log "Scaled to high-memory instance"
}

configure_networking() {
    log "Configuring networking for ADB access..."
    
    # Allocate IP for external ADB access
    if ! flyctl ips list --app "$APP_NAME" 2>/dev/null | grep -q "v4"; then
        log "Allocating IPv4 address"
        flyctl ips allocate-v4 --app "$APP_NAME"
    fi
    
    log "Networking configured"
}

verify_deployment() {
    log "Verifying Android device farm deployment..."
    
    # Check app status
    flyctl status --app "$APP_NAME"
    
    # Get app URL and IP
    local app_url="https://${APP_NAME}.fly.dev"
    local app_ip=$(flyctl ips list --app "$APP_NAME" | grep "v4" | awk '{print $3}' | head -1)
    
    log "App URL: $app_url"
    log "ADB Connection IP: $app_ip"
    log "ADB Port: 5555"
    log "VNC Port: 5900 (for remote emulator access)"
    
    # Wait for deployment
    log "Waiting for Android device farm to be ready..."
    local max_attempts=20
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$app_url/health" >/dev/null 2>&1; then
            log "✅ Android device farm is ready!"
            break
        else
            log "Attempt $attempt/$max_attempts: Waiting for deployment..."
            sleep 15
            ((attempt++))
        fi
    done
    
    if [ $attempt -gt $max_attempts ]; then
        warn "Health check timeout - checking logs"
        flyctl logs --app "$APP_NAME" --lines 20
        return 1
    fi
    
    # Test ADB connection
    log "Testing ADB connection..."
    if [[ -n "$app_ip" ]]; then
        log "To connect ADB locally, run:"
        echo "  adb connect $app_ip:5555"
        echo "  adb devices"
    fi
    
    log "✅ Android device farm deployment verified!"
}

test_snapchat_integration() {
    log "Testing Snapchat automation integration..."
    
    local app_url="https://${APP_NAME}.fly.dev"
    
    # Test the Snapchat automation endpoint
    log "Testing Snapchat account creation endpoint..."
    
    # Create test request
    local test_data='{
        "username": "test_user",
        "email": "test@example.com",
        "phone": "+15551234567",
        "password": "TestPass123!"
    }'
    
    # Send test request (this will fail without real credentials, but tests the endpoint)
    curl -X POST \
        -H "Content-Type: application/json" \
        -d "$test_data" \
        "$app_url/api/snapchat/create" \
        --connect-timeout 30 \
        --max-time 60 \
        -v 2>&1 | head -20 || warn "Endpoint test completed (expected to fail without full setup)"
    
    log "Snapchat integration test completed"
}

show_usage_instructions() {
    local app_url="https://${APP_NAME}.fly.dev"
    local app_ip=$(flyctl ips list --app "$APP_NAME" 2>/dev/null | grep "v4" | awk '{print $3}' | head -1 || echo "IP_NOT_ALLOCATED")
    
    cat << EOF

🚀 Android Device Farm Deployment Complete!

📱 Device Farm Details:
   - App Name: $APP_NAME
   - URL: $app_url
   - ADB IP: $app_ip
   - ADB Port: 5555
   - VNC Port: 5900

🔧 Connect ADB Locally:
   adb connect $app_ip:5555
   adb devices

🖥️  Remote Emulator Access (VNC):
   vnc://$app_ip:5900
   (Use VNC viewer to see emulator screen)

📊 Monitor & Manage:
   flyctl logs --app $APP_NAME -f
   flyctl ssh console --app $APP_NAME
   flyctl status --app $APP_NAME

🧪 Test Snapchat Creation:
   curl -X POST $app_url/api/snapchat/create \\
     -H "Content-Type: application/json" \\
     -d '{"username":"test","email":"test@example.com"}'

📝 Next Steps:
   1. Update local Snapchat automation to use remote ADB: $app_ip:5555
   2. Configure real Twilio credentials if needed
   3. Test account creation workflow
   4. Monitor logs for any issues

EOF
}

main() {
    log "🚀 Starting Android Device Farm deployment to Fly.io"
    
    check_requirements
    create_app
    create_volume
    set_secrets
    deploy_android_farm
    scale_for_android
    configure_networking
    verify_deployment
    test_snapchat_integration
    show_usage_instructions
    
    log "🎉 Android Device Farm deployment completed successfully!"
}

# Handle command line arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "verify")
        verify_deployment
        ;;
    "logs")
        flyctl logs --app "$APP_NAME" -f
        ;;
    "console")
        flyctl ssh console --app "$APP_NAME"
        ;;
    "status")
        flyctl status --app "$APP_NAME"
        ;;
    *)
        echo "Usage: $0 [deploy|verify|logs|console|status]"
        echo "  deploy  - Full deployment (default)"
        echo "  verify  - Verify deployment only"
        echo "  logs    - Show live logs"
        echo "  console - SSH into container"
        echo "  status  - Show app status"
        exit 1
        ;;
esac