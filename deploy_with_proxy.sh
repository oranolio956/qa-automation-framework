#!/bin/bash
# Complete Deployment Script with Smartproxy Residential Proxy Integration
# Ensures all system components use the residential proxy for network requests

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/tmp/qa-framework-proxy-deploy.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    local status=$1
    local message=$2
    case $status in
        "SUCCESS") echo -e "${GREEN}✅ $message${NC}" ;;
        "WARN") echo -e "${YELLOW}⚠️  $message${NC}" ;;
        "ERROR") echo -e "${RED}❌ $message${NC}" ;;
        "INFO") echo -e "${BLUE}ℹ️  $message${NC}" ;;
    esac
}

log "🚀 Starting QA Framework Deployment with Proxy Integration"
log "========================================================"

# Step 1: Validate proxy configuration
validate_proxy_config() {
    log "Validating Smartproxy configuration..."
    
    # Check environment variables
    local missing_vars=()
    
    if [[ -z "${SMARTPROXY_USER:-}" ]]; then
        missing_vars+=("SMARTPROXY_USER")
    fi
    
    if [[ -z "${SMARTPROXY_PASS:-}" ]]; then
        missing_vars+=("SMARTPROXY_PASS")
    fi
    
    if [[ -z "${SMARTPROXY_HOST:-}" ]]; then
        missing_vars+=("SMARTPROXY_HOST")
    fi
    
    if [[ -z "${SMARTPROXY_PORT:-}" ]]; then
        missing_vars+=("SMARTPROXY_PORT")
    fi
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        print_status "ERROR" "Missing proxy environment variables: ${missing_vars[*]}"
        print_status "INFO" "Please set these variables in your .env file:"
        for var in "${missing_vars[@]}"; do
            echo "  $var=your_value"
        done
        return 1
    fi
    
    print_status "SUCCESS" "Proxy configuration validated"
    log "Proxy: ${SMARTPROXY_HOST}:${SMARTPROXY_PORT} (User: ${SMARTPROXY_USER})"
    
    return 0
}

# Step 2: Test proxy connectivity
test_proxy_connectivity() {
    log "Testing proxy connectivity..."
    
    # Create temporary proxy test script
    cat > /tmp/proxy_test.py << 'EOF'
import os
import requests
import sys

proxy_user = os.environ.get('SMARTPROXY_USER')
proxy_pass = os.environ.get('SMARTPROXY_PASS')
proxy_host = os.environ.get('SMARTPROXY_HOST')
proxy_port = os.environ.get('SMARTPROXY_PORT')

proxy_url = f"socks5://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}"
proxies = {
    'http': proxy_url,
    'https': proxy_url
}

try:
    response = requests.get('https://httpbin.org/ip', proxies=proxies, timeout=15)
    if response.status_code == 200:
        data = response.json()
        print(f"SUCCESS: Connected via proxy - External IP: {data.get('origin', 'unknown')}")
        sys.exit(0)
    else:
        print(f"ERROR: Proxy test failed - Status: {response.status_code}")
        sys.exit(1)
except Exception as e:
    print(f"ERROR: Proxy test failed - {e}")
    sys.exit(1)
EOF
    
    if python3 /tmp/proxy_test.py; then
        print_status "SUCCESS" "Proxy connectivity verified"
        return 0
    else
        print_status "ERROR" "Proxy connectivity test failed"
        return 1
    fi
}

# Step 3: Update .env file with proxy configuration
update_env_file() {
    log "Updating .env file with proxy configuration..."
    
    local env_file=".env"
    
    # Backup existing .env
    if [ -f "$env_file" ]; then
        cp "$env_file" "${env_file}.backup.$(date +%s)"
    fi
    
    # Ensure proxy configuration exists in .env
    local proxy_config="
# Smartproxy Residential Proxy Configuration (Auto-updated)
SMARTPROXY_USER=${SMARTPROXY_USER}
SMARTPROXY_PASS=${SMARTPROXY_PASS}
SMARTPROXY_HOST=${SMARTPROXY_HOST}
SMARTPROXY_PORT=${SMARTPROXY_PORT}
"
    
    # Remove existing proxy config and add new one
    if [ -f "$env_file" ]; then
        # Remove old proxy config
        sed -i.bak '/# Smartproxy/,/^$/d' "$env_file"
    fi
    
    echo "$proxy_config" >> "$env_file"
    
    print_status "SUCCESS" ".env file updated with proxy configuration"
}

# Step 4: Build Docker images with proxy support
build_docker_images() {
    log "Building Docker images with proxy support..."
    
    # Build backend service
    if [ -f "backend/Dockerfile" ]; then
        log "Building backend service..."
        docker build -t qa-backend:proxy \
            --build-arg SMARTPROXY_USER="${SMARTPROXY_USER}" \
            --build-arg SMARTPROXY_PASS="${SMARTPROXY_PASS}" \
            --build-arg SMARTPROXY_HOST="${SMARTPROXY_HOST}" \
            --build-arg SMARTPROXY_PORT="${SMARTPROXY_PORT}" \
            backend/
        
        print_status "SUCCESS" "Backend service image built"
    fi
    
    # Build bot service
    if [ -f "bot/Dockerfile" ]; then
        log "Building bot service..."
        docker build -t qa-bot:proxy \
            --build-arg SMARTPROXY_USER="${SMARTPROXY_USER}" \
            --build-arg SMARTPROXY_PASS="${SMARTPROXY_PASS}" \
            --build-arg SMARTPROXY_HOST="${SMARTPROXY_HOST}" \
            --build-arg SMARTPROXY_PORT="${SMARTPROXY_PORT}" \
            bot/
        
        print_status "SUCCESS" "Bot service image built"
    fi
    
    # Build infrastructure services
    if [ -f "infra/Dockerfile.provisioner" ]; then
        log "Building provisioner service..."
        docker build -t qa-provisioner:proxy \
            --build-arg SMARTPROXY_USER="${SMARTPROXY_USER}" \
            --build-arg SMARTPROXY_PASS="${SMARTPROXY_PASS}" \
            --build-arg SMARTPROXY_HOST="${SMARTPROXY_HOST}" \
            --build-arg SMARTPROXY_PORT="${SMARTPROXY_PORT}" \
            -f infra/Dockerfile.provisioner infra/
        
        print_status "SUCCESS" "Provisioner service image built"
    fi
    
    if [ -f "infra/Dockerfile.manager" ]; then
        log "Building manager service..."
        docker build -t qa-manager:proxy \
            --build-arg SMARTPROXY_USER="${SMARTPROXY_USER}" \
            --build-arg SMARTPROXY_PASS="${SMARTPROXY_PASS}" \
            --build-arg SMARTPROXY_HOST="${SMARTPROXY_HOST}" \
            --build-arg SMARTPROXY_PORT="${SMARTPROXY_PORT}" \
            -f infra/Dockerfile.manager infra/
        
        print_status "SUCCESS" "Manager service image built"
    fi
}

# Step 5: Deploy infrastructure services
deploy_infrastructure() {
    log "Deploying infrastructure services with proxy support..."
    
    # Stop existing services
    docker-compose -f infra/docker-compose.yml down 2>/dev/null || true
    
    # Start services with proxy configuration
    docker-compose -f infra/docker-compose.yml up -d
    
    # Wait for services to start
    log "Waiting for services to start..."
    sleep 30
    
    # Verify service health
    local services=("vault:8200" "redis:6379")
    
    for service in "${services[@]}"; do
        local host=${service%:*}
        local port=${service#*:}
        
        if nc -z localhost "$port" 2>/dev/null; then
            print_status "SUCCESS" "$host service is running"
        else
            print_status "WARN" "$host service may not be ready yet"
        fi
    done
}

# Step 6: Start application services
start_application_services() {
    log "Starting application services..."
    
    # Start backend service
    if [ -f "backend/app.py" ]; then
        log "Starting backend service..."
        cd backend
        
        # Install dependencies if needed
        if [ -f "requirements.txt" ]; then
            pip3 install -r requirements.txt >/dev/null 2>&1 || true
        fi
        
        # Start backend in background
        nohup python3 app.py > /tmp/backend.log 2>&1 &
        BACKEND_PID=$!
        echo $BACKEND_PID > /tmp/backend.pid
        
        cd ..
        
        # Wait a moment and check if it started
        sleep 5
        if kill -0 $BACKEND_PID 2>/dev/null; then
            print_status "SUCCESS" "Backend service started (PID: $BACKEND_PID)"
        else
            print_status "ERROR" "Backend service failed to start"
        fi
    fi
    
    # Start bot service
    if [ -f "bot/app.py" ]; then
        log "Starting bot service..."
        cd bot
        
        # Install dependencies if needed
        if [ -f "requirements.txt" ]; then
            pip3 install -r requirements.txt >/dev/null 2>&1 || true
        fi
        
        # Start bot in background
        nohup python3 app.py > /tmp/bot.log 2>&1 &
        BOT_PID=$!
        echo $BOT_PID > /tmp/bot.pid
        
        cd ..
        
        # Wait a moment and check if it started
        sleep 5
        if kill -0 $BOT_PID 2>/dev/null; then
            print_status "SUCCESS" "Bot service started (PID: $BOT_PID)"
        else
            print_status "ERROR" "Bot service failed to start"
        fi
    fi
}

# Step 7: Run integration tests
run_integration_tests() {
    log "Running proxy integration tests..."
    
    # Wait for services to fully initialize
    sleep 10
    
    if python3 test_proxy_integration.py; then
        print_status "SUCCESS" "Proxy integration tests passed"
        return 0
    else
        print_status "WARN" "Some proxy integration tests failed (check logs)"
        return 1
    fi
}

# Step 8: Generate deployment summary
generate_deployment_summary() {
    log "Generating deployment summary..."
    
    local summary_file="/tmp/qa-framework-deployment-summary.txt"
    
    cat > "$summary_file" << EOF
QA Framework Deployment Summary
==============================
Deployment Time: $(date)
Proxy Configuration: ${SMARTPROXY_HOST}:${SMARTPROXY_PORT}

Services Status:
$(docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -10)

Service URLs:
- Backend API: http://localhost:8000/health
- Bot Service: http://localhost:5000/health
- Vault: http://localhost:8200/v1/sys/health
- Redis: localhost:6379

Log Files:
- Deployment: $LOG_FILE
- Backend: /tmp/backend.log
- Bot: /tmp/bot.log

Next Steps:
1. Verify all services are healthy: curl http://localhost:8000/health
2. Submit a test job: curl -X POST http://localhost:5000/submit -H "Authorization: Bearer \$CHAT_API_TOKEN" -H "Content-Type: application/json" -d '{"job":"touch_test"}'
3. Check proxy status in service health endpoints
4. Monitor logs for proxy connectivity

Configuration Files:
- Environment: .env
- Docker Compose: infra/docker-compose.yml
- Proxy Utils: utils/proxy.py

Troubleshooting:
- Check proxy credentials in .env file
- Verify network connectivity to ${SMARTPROXY_HOST}:${SMARTPROXY_PORT}
- Review service logs if health checks fail
- Test direct proxy connection: python3 test_proxy_integration.py
EOF
    
    print_status "SUCCESS" "Deployment summary generated: $summary_file"
    
    # Display summary
    cat "$summary_file"
}

# Main deployment function
main() {
    log "Starting comprehensive deployment with proxy integration..."
    
    local exit_code=0
    
    # Step-by-step deployment
    validate_proxy_config || exit_code=1
    
    if [ $exit_code -eq 0 ]; then
        test_proxy_connectivity || exit_code=1
    fi
    
    if [ $exit_code -eq 0 ]; then
        update_env_file
        build_docker_images
        deploy_infrastructure
        start_application_services
        
        # Run tests (non-blocking)
        run_integration_tests || true
        
        generate_deployment_summary
    fi
    
    if [ $exit_code -eq 0 ]; then
        print_status "SUCCESS" "🎉 QA Framework deployed successfully with proxy integration!"
        log "Deployment completed successfully"
    else
        print_status "ERROR" "⚠️  Deployment completed with errors. Check logs for details."
        log "Deployment completed with errors"
    fi
    
    return $exit_code
}

# Cleanup function
cleanup() {
    log "Cleaning up temporary files..."
    rm -f /tmp/proxy_test.py
    
    if [ "${1:-}" = "full" ]; then
        log "Performing full cleanup..."
        
        # Stop services
        [ -f /tmp/backend.pid ] && kill $(cat /tmp/backend.pid) 2>/dev/null || true
        [ -f /tmp/bot.pid ] && kill $(cat /tmp/bot.pid) 2>/dev/null || true
        
        # Stop Docker services
        docker-compose -f infra/docker-compose.yml down 2>/dev/null || true
        
        print_status "INFO" "Full cleanup completed"
    fi
}

# Signal handlers
trap 'cleanup; exit 130' INT
trap 'cleanup; exit 143' TERM

# Parse command line arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "test")
        validate_proxy_config && test_proxy_connectivity && python3 test_proxy_integration.py
        ;;
    "cleanup")
        cleanup full
        ;;
    "status")
        echo "Service Status:"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        echo -e "\nHealth Checks:"
        curl -s http://localhost:8000/health 2>/dev/null | jq '.proxy_status // "unknown"' || echo "Backend: unavailable"
        curl -s http://localhost:5000/health 2>/dev/null | jq '.proxy_status // "unknown"' || echo "Bot: unavailable"
        ;;
    "help")
        echo "Usage: $0 [deploy|test|cleanup|status|help]"
        echo "  deploy  - Full deployment with proxy integration (default)"
        echo "  test    - Test proxy connectivity only"
        echo "  cleanup - Stop all services and cleanup"
        echo "  status  - Show service status"
        echo "  help    - Show this help message"
        ;;
    *)
        print_status "ERROR" "Unknown command: $1"
        exit 1
        ;;
esac