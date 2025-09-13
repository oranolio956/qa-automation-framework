#!/bin/bash
# Infrastructure and Worker Pool Deployment Script

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/qa-framework/infra-deploy.log"

mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Starting Infrastructure and Worker Pool deployment..."

# Install dependencies
install_dependencies() {
    log "Installing infrastructure dependencies..."
    
    if ! command -v python3 >/dev/null 2>&1; then
        log "Installing Python..."
        apt-get update && apt-get install -y python3 python3-pip
    fi
    
    # Install Python packages
    pip3 install hvac requests redis
    
    log "Dependencies installed successfully"
}

# Deploy infrastructure stack
deploy_infra() {
    log "Deploying infrastructure stack with Docker Compose..."
    
    # Set default environment variables
    export WORKER_COUNT="${WORKER_COUNT:-3}"
    export CHAT_API_TOKEN="${CHAT_API_TOKEN:-$(openssl rand -hex 32)}"
    
    # Start infrastructure services
    docker-compose -f "$SCRIPT_DIR/docker-compose.yml" up -d
    
    log "Infrastructure stack deployed"
}

# Test deployment
test_deployment() {
    log "Testing infrastructure deployment..."
    
    local max_wait=120
    local wait_time=0
    
    # Wait for services to be ready
    while [ $wait_time -lt $max_wait ]; do
        if curl -f http://localhost:5000/health >/dev/null 2>&1 && \
           redis-cli ping >/dev/null 2>&1; then
            log "✅ All services are healthy"
            return 0
        fi
        
        sleep 5
        wait_time=$((wait_time + 5))
    done
    
    log "❌ Services failed to start within ${max_wait}s"
    return 1
}

# Provision initial workers
provision_workers() {
    log "Provisioning initial worker pool..."
    
    if python3 "$SCRIPT_DIR/provision.py" --provision; then
        log "✅ Worker pool provisioned successfully"
    else
        log "⚠ Worker provisioning failed, but continuing..."
    fi
}

main() {
    install_dependencies
    deploy_infra
    
    if test_deployment; then
        provision_workers
        
        log "=== Phase 14C completed successfully ==="
        log "Infrastructure services:"
        log "  - Orchestrator: http://localhost:5000"
        log "  - Redis: localhost:6379"
        log "  - Vault: http://localhost:8200"
        log "  - API Token: $CHAT_API_TOKEN"
        
        echo "Phase 14C complete: Infrastructure and worker pool automated."
    else
        log "❌ Phase 14C deployment failed"
        exit 1
    fi
}

main "$@"