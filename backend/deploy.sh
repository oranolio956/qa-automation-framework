#!/bin/bash
# Order and Billing Pipeline Deployment Script

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/qa-framework/backend-deploy.log"

mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Starting Order and Billing Pipeline deployment..."

# Configuration
JWT_SECRET="${JWT_SECRET:-$(openssl rand -hex 32)}"
WEBHOOK_SECRET="${WEBHOOK_SECRET:-$(openssl rand -hex 32)}"
REDIS_URL="${REDIS_URL:-redis://localhost:6379}"
PAYMENT_PROVIDER_API_KEY="${PAYMENT_PROVIDER_API_KEY:-}"
API_RATE_LIMIT="${API_RATE_LIMIT:-200}"

# Install dependencies
install_dependencies() {
    log "Installing backend dependencies..."
    
    pip3 install flask pydantic pyjwt requests redis tenacity flask-limiter
    
    log "Dependencies installed successfully"
}

# Build and deploy service
deploy_service() {
    log "Building and deploying order service..."
    
    # Build Docker image
    docker build -t order-service "$SCRIPT_DIR"
    
    # Stop existing container
    docker stop order-service 2>/dev/null || true
    docker rm order-service 2>/dev/null || true
    
    # Start new container
    docker run -d \
        --name order-service \
        -e JWT_SECRET="$JWT_SECRET" \
        -e REDIS_URL="$REDIS_URL" \
        -e WEBHOOK_SECRET="$WEBHOOK_SECRET" \
        -e PAYMENT_PROVIDER_API_KEY="$PAYMENT_PROVIDER_API_KEY" \
        -e API_RATE_LIMIT="$API_RATE_LIMIT" \
        -p 8000:8000 \
        --restart unless-stopped \
        order-service
    
    log "Order service deployed successfully"
}

# Test deployment
test_deployment() {
    log "Testing order service deployment..."
    
    # Wait for service to start
    local max_wait=60
    local wait_time=0
    
    while [ $wait_time -lt $max_wait ]; do
        if curl -f http://localhost:8000/health >/dev/null 2>&1; then
            log "✅ Order service is healthy"
            return 0
        fi
        
        sleep 5
        wait_time=$((wait_time + 5))
    done
    
    log "❌ Order service failed to start within ${max_wait}s"
    docker logs order-service
    return 1
}

# Create test JWT token for development
create_test_token() {
    log "Creating test JWT token..."
    
    # Create a simple test token
    python3 - <<EOF
import jwt
import json
from datetime import datetime, timedelta

payload = {
    'user_id': 'test-user-123',
    'customer_id': 'test-customer-123',
    'email': 'test@example.com',
    'iat': datetime.utcnow(),
    'exp': datetime.utcnow() + timedelta(hours=24)
}

token = jwt.encode(payload, "$JWT_SECRET", algorithm='HS256')
print("Test JWT Token:")
print(token)
print()
print("Use this token in Authorization header: Bearer " + token)
EOF
}

main() {
    install_dependencies
    deploy_service
    
    if test_deployment; then
        create_test_token
        
        log "=== Phase 15 completed successfully ==="
        log "Order and Billing service deployed:"
        log "  - Service URL: http://localhost:8000"
        log "  - Health endpoint: http://localhost:8000/health"
        log "  - Metrics endpoint: http://localhost:8000/metrics"
        log "  - JWT Secret: $JWT_SECRET"
        log "  - Webhook Secret: $WEBHOOK_SECRET"
        
        echo "Phase 15 complete: Order and billing pipeline deployed."
    else
        log "❌ Phase 15 deployment failed"
        exit 1
    fi
}

main "$@"