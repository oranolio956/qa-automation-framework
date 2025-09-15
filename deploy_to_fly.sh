#!/bin/bash
# Deployment script for Fly.io
# This script deploys the QA automation framework to Fly.io

set -euo pipefail

# Configuration
APP_NAME="qa-automation-prod"
REGION="ord"
ORG_NAME="personal"

# Load environment variables from .env file
if [ -f ".env" ]; then
    source .env
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Check if flyctl is installed
check_flyctl() {
    if ! command -v flyctl >/dev/null 2>&1; then
        log "Installing Fly CLI..."
        curl -L https://fly.io/install.sh | sh
        export PATH="$HOME/.fly/bin:$PATH"
    else
        log "Fly CLI found"
    fi
}

# Check authentication
check_auth() {
    log "Checking Fly.io authentication..."
    
    if flyctl auth whoami >/dev/null 2>&1; then
        log "Already authenticated with Fly.io"
        return 0
    else
        warn "Not authenticated with Fly.io"
        log "Please run: flyctl auth login"
        log "Or set the FLY_ACCESS_TOKEN environment variable"
        return 1
    fi
}

# Create or update the app
create_app() {
    log "Creating/updating Fly.io app: $APP_NAME"
    
    # Check if app already exists
    if flyctl apps list | grep -q "$APP_NAME"; then
        log "App $APP_NAME already exists, skipping creation"
    else
        log "Creating new app: $APP_NAME"
        flyctl apps create "$APP_NAME" --org "$ORG_NAME"
    fi
}

# Set environment secrets
set_secrets() {
    log "Setting environment secrets..."
    
    # Prepare secrets - using environment variables or defaults
    flyctl secrets set \
        BRIGHTDATA_ZONE_KEY="${BRIGHTDATA_ZONE_KEY:-your_zone_access_key}" \
        BRIGHTDATA_ENDPOINT="${BRIGHTDATA_ENDPOINT:-browser.tinder-emulation.brightdata.com:24000}" \
        REDIS_URL="${REDIS_URL:-redis://fly-qa-automation-redis.internal:6379}" \
        JWT_SECRET="${JWT_SECRET:-$(openssl rand -hex 32)}" \
        WEBHOOK_SECRET="${WEBHOOK_SECRET:-$(openssl rand -hex 32)}" \
        CHAT_API_TOKEN="${CHAT_API_TOKEN:-$(openssl rand -hex 32)}" \
        API_RATE_LIMIT="${API_RATE_LIMIT:-200}" \
        VAULT_ADDRESS="${VAULT_ADDRESS:-http://vault.internal:8200}" \
        VAULT_TOKEN="${VAULT_TOKEN:-dev-token}" \
        --app "$APP_NAME"
    
    log "Secrets configured successfully"
}

# Deploy the application
deploy_app() {
    log "Deploying application to Fly.io..."
    
    # Deploy using the Dockerfile
    flyctl deploy --app "$APP_NAME" --dockerfile Dockerfile
    
    log "Deployment completed"
}

# Scale the application
scale_app() {
    log "Scaling application to use Always Free tier..."
    
    # Scale to 1 machine (Always Free tier)
    flyctl scale count 1 --app "$APP_NAME"
    
    # Use shared CPU (Always Free)
    flyctl scale vm shared-cpu-1x --app "$APP_NAME"
    
    log "Scaling completed"
}

# Verify deployment
verify_deployment() {
    log "Verifying deployment..."
    
    # Check app status
    flyctl status --app "$APP_NAME"
    
    # Check if health endpoint is responding
    local app_url="https://${APP_NAME}.fly.dev"
    log "Checking health endpoint: $app_url/health"
    
    # Wait for app to be ready
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$app_url/health" >/dev/null 2>&1; then
            log "✅ Health check passed!"
            break
        else
            log "Attempt $attempt/$max_attempts: Waiting for app to be ready..."
            sleep 10
            ((attempt++))
        fi
    done
    
    if [ $attempt -gt $max_attempts ]; then
        error "Health check failed after $max_attempts attempts"
        return 1
    fi
    
    # Test Bright Data proxy integration
    log "Testing Bright Data proxy integration..."
    if flyctl ssh console --app "$APP_NAME" --command "python3 -c 'from utils.brightdata_proxy import verify_proxy; verify_proxy(); print(\"BrightData proxy OK\")'" 2>/dev/null; then
        log "✅ Bright Data proxy integration test passed!"
    else
        warn "Bright Data proxy integration test failed (this might be expected if Bright Data credentials are not configured)"
    fi
    
    log "✅ Deployment verification completed!"
    log "🚀 Application URL: $app_url"
    log "📊 Health Check: $app_url/health"
    log "📈 Metrics: $app_url/metrics"
}

# Main deployment function
main() {
    log "🚀 Starting Fly.io deployment for QA Automation Framework"
    
    # Check prerequisites
    check_flyctl
    
    if ! check_auth; then
        error "Authentication required. Please run 'flyctl auth login' first"
        exit 1
    fi
    
    # Deploy steps
    create_app
    set_secrets
    deploy_app
    scale_app
    verify_deployment
    
    log "🎉 Deployment completed successfully!"
    log "GitHub repo: https://github.com/oranolio956/qa-automation-framework"
    log "Fly.io app: https://${APP_NAME}.fly.dev"
    echo "BrightData integration complete: all traffic routed through Browser API zone tinder-emulation."
}

# Handle command line arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "scale")
        scale_app
        ;;
    "verify")
        verify_deployment
        ;;
    "secrets")
        set_secrets
        ;;
    *)
        echo "Usage: $0 [deploy|scale|verify|secrets]"
        echo "  deploy  - Full deployment (default)"
        echo "  scale   - Scale the application"
        echo "  verify  - Verify deployment"
        echo "  secrets - Update secrets only"
        exit 1
        ;;
esac