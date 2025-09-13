#!/bin/bash
# Worker Registration Script
# Registers the worker with the central orchestrator

set -euo pipefail

WORKER_ID="${WORKER_ID:-$(hostname)-$(date +%s)}"
ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://orchestrator:5000}"
REDIS_URL="${REDIS_URL:-redis://localhost:6379}"
LOG_FILE="/var/log/qa-worker-register.log"

# Smartproxy configuration
SMARTPROXY_USER="${SMARTPROXY_USER:-your_trial_user}"
SMARTPROXY_PASS="${SMARTPROXY_PASS:-your_trial_pass}"
SMARTPROXY_HOST="${SMARTPROXY_HOST:-proxy.smartproxy.com}"
SMARTPROXY_PORT="${SMARTPROXY_PORT:-7000}"
PROXY_URL="socks5://${SMARTPROXY_USER}:${SMARTPROXY_PASS}@${SMARTPROXY_HOST}:${SMARTPROXY_PORT}"

# Proxy-enabled curl function
curl_proxy() {
    curl --proxy-user "${SMARTPROXY_USER}:${SMARTPROXY_PASS}" \
         --socks5-hostname "${SMARTPROXY_HOST}:${SMARTPROXY_PORT}" \
         "$@"
}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [Register:$WORKER_ID] $1" | tee -a "$LOG_FILE"
}

log "Starting worker registration..."

# Get system information
get_system_info() {
    local cpu_count memory_gb disk_gb
    
    cpu_count=$(nproc 2>/dev/null || echo "1")
    memory_gb=$(free -g | awk '/^Mem:/{print $2}' 2>/dev/null || echo "1")
    disk_gb=$(df -BG / | awk 'NR==2{print $2}' | sed 's/G//' 2>/dev/null || echo "10")
    
    echo "$cpu_count,$memory_gb,$disk_gb"
}

# Detect available capabilities
detect_capabilities() {
    local capabilities=()
    
    # Test for touch testing capability
    if command -v adb >/dev/null 2>&1; then
        capabilities+=("touch_test")
    fi
    
    # Test for network testing capability
    if command -v tc >/dev/null 2>&1 && python3 -c "import requests" 2>/dev/null; then
        capabilities+=("network_test")
    fi
    
    # Test for image processing capability
    if command -v convert >/dev/null 2>&1 || python3 -c "from PIL import Image" 2>/dev/null; then
        capabilities+=("image_test")
    fi
    
    # Test for container capability
    if command -v docker >/dev/null 2>&1; then
        capabilities+=("container_test")
    fi
    
    # Test for load testing capability
    if python3 -c "import asyncio, aiohttp" 2>/dev/null; then
        capabilities+=("load_test")
    fi
    
    # Default capability
    if [ ${#capabilities[@]} -eq 0 ]; then
        capabilities+=("basic_test")
    fi
    
    # Join array with commas
    IFS=','
    echo "${capabilities[*]}"
}

# Register with orchestrator
register_with_orchestrator() {
    log "Registering with orchestrator: $ORCHESTRATOR_URL"
    
    local system_info capabilities registration_data response
    
    # Get system information
    IFS=',' read -r cpu_count memory_gb disk_gb <<< "$(get_system_info)"
    capabilities="$(detect_capabilities)"
    
    # Prepare registration payload
    registration_data=$(cat <<EOF
{
    "worker_id": "$WORKER_ID",
    "hostname": "$(hostname)",
    "ip_address": "$(curl_proxy -s ifconfig.me 2>/dev/null || echo 'unknown')",
    "capabilities": ["${capabilities//,/\", \"}"],
    "system_info": {
        "cpu_cores": $cpu_count,
        "memory_gb": $memory_gb,
        "disk_gb": $disk_gb,
        "os": "$(uname -s)",
        "kernel": "$(uname -r)"
    },
    "max_concurrent_jobs": 3,
    "status": "ready",
    "registered_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "version": "1.0.0"
}
EOF
)
    
    log "Registration data prepared for worker $WORKER_ID"
    log "Capabilities: $capabilities"
    log "System: ${cpu_count}C/${memory_gb}GB RAM/${disk_gb}GB disk"
    
    # Attempt registration with orchestrator
    local max_retries=5
    local retry_count=0
    local success=false
    
    while [ $retry_count -lt $max_retries ] && [ "$success" = false ]; do
        retry_count=$((retry_count + 1))
        
        if response=$(curl_proxy -X POST "$ORCHESTRATOR_URL/workers/register" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer ${CHAT_API_TOKEN:-default}" \
            -d "$registration_data" \
            -w "%{http_code}" \
            -s --connect-timeout 10 --max-time 30 2>/dev/null); then
            
            http_code="${response: -3}"
            response_body="${response%???}"
            
            if [ "$http_code" = "201" ] || [ "$http_code" = "200" ]; then
                log "✓ Successfully registered with orchestrator (HTTP $http_code)"
                success=true
            else
                log "✗ Registration failed with HTTP $http_code: $response_body"
            fi
        else
            log "✗ Registration attempt $retry_count failed (connection error)"
        fi
        
        if [ "$success" = false ] && [ $retry_count -lt $max_retries ]; then
            local wait_time=$((retry_count * 5))
            log "Retrying in ${wait_time}s..."
            sleep $wait_time
        fi
    done
    
    return $([ "$success" = true ] && echo 0 || echo 1)
}

# Store registration in Redis
store_in_redis() {
    log "Storing worker info in Redis..."
    
    if ! command -v redis-cli >/dev/null 2>&1; then
        log "Redis CLI not available, skipping Redis storage"
        return 0
    fi
    
    local system_info
    IFS=',' read -r cpu_count memory_gb disk_gb <<< "$(get_system_info)"
    
    if redis-cli -u "$REDIS_URL" hset "worker:$WORKER_ID" \
        status "ready" \
        registered_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        hostname "$(hostname)" \
        ip_address "$(curl_proxy -s ifconfig.me 2>/dev/null || echo 'unknown')" \
        capabilities "$(detect_capabilities)" \
        cpu_cores "$cpu_count" \
        memory_gb "$memory_gb" \
        disk_gb "$disk_gb" \
        version "1.0.0" >/dev/null 2>&1; then
        
        log "✓ Worker info stored in Redis"
        
        # Add to workers set
        redis-cli -u "$REDIS_URL" sadd "workers" "$WORKER_ID" >/dev/null 2>&1
        
        # Set expiration (7 days)
        redis-cli -u "$REDIS_URL" expire "worker:$WORKER_ID" 604800 >/dev/null 2>&1
        
        return 0
    else
        log "✗ Failed to store worker info in Redis"
        return 1
    fi
}

# Create worker health heartbeat
create_heartbeat() {
    log "Setting up worker heartbeat..."
    
    # Create heartbeat script
    cat > /opt/qa-worker/heartbeat.sh << 'EOF'
#!/bin/bash
# Worker heartbeat script

WORKER_ID="${WORKER_ID:-$(hostname)}"
REDIS_URL="${REDIS_URL:-redis://localhost:6379}"
ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://orchestrator:5000}"

# Update heartbeat in Redis
if command -v redis-cli >/dev/null 2>&1; then
    redis-cli -u "$REDIS_URL" hset "worker:$WORKER_ID" \
        last_heartbeat "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        status "active" >/dev/null 2>&1
fi

# Send heartbeat to orchestrator through proxy
curl --proxy-user "${SMARTPROXY_USER:-your_trial_user}:${SMARTPROXY_PASS:-your_trial_pass}" \
     --socks5-hostname "${SMARTPROXY_HOST:-proxy.smartproxy.com}:${SMARTPROXY_PORT:-7000}" \
     -X POST "$ORCHESTRATOR_URL/workers/$WORKER_ID/heartbeat" \
     -H "Authorization: Bearer ${CHAT_API_TOKEN:-default}" \
     -d '{"timestamp":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' \
     -H "Content-Type: application/json" \
     -s --connect-timeout 5 --max-time 10 >/dev/null 2>&1 || true
EOF
    
    chmod +x /opt/qa-worker/heartbeat.sh
    
    # Schedule heartbeat every 2 minutes
    (crontab -l 2>/dev/null; echo "*/2 * * * * /opt/qa-worker/heartbeat.sh") | crontab -
    
    log "✓ Heartbeat scheduled every 2 minutes"
}

# Test connectivity to key services
test_connectivity() {
    log "Testing connectivity to required services..."
    
    local test_results=()
    
    # Test orchestrator through proxy
    if curl_proxy -f "$ORCHESTRATOR_URL/health" -s --connect-timeout 5 >/dev/null 2>&1; then
        log "✓ Orchestrator connectivity: OK (via proxy)"
        test_results+=("orchestrator:ok")
    else
        log "✗ Orchestrator connectivity: FAILED (via proxy)"
        test_results+=("orchestrator:failed")
    fi
    
    # Test Redis
    if redis-cli -u "$REDIS_URL" ping >/dev/null 2>&1; then
        log "✓ Redis connectivity: OK" 
        test_results+=("redis:ok")
    else
        log "✗ Redis connectivity: FAILED"
        test_results+=("redis:failed")
    fi
    
    # Test internet connectivity through proxy
    if curl_proxy -f "https://httpbin.org/get" -s --connect-timeout 5 >/dev/null 2>&1; then
        log "✓ Internet connectivity: OK (via residential proxy)"
        test_results+=("internet:ok")
    else
        log "✗ Internet connectivity: FAILED (via proxy)"  
        test_results+=("internet:failed")
    fi
    
    # Store test results
    if redis-cli -u "$REDIS_URL" hset "worker:$WORKER_ID" \
        connectivity_test "$(IFS=','; echo "${test_results[*]}")" \
        last_connectivity_check "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >/dev/null 2>&1; then
        log "✓ Connectivity test results stored"
    fi
    
    # Return success if at least orchestrator or Redis works
    local success_count=0
    for result in "${test_results[@]}"; do
        if [[ "$result" == *":ok" ]]; then
            ((success_count++))
        fi
    done
    
    return $((success_count > 0 ? 0 : 1))
}

# Main registration function
main() {
    log "=== Worker Registration Started ==="
    log "Worker ID: $WORKER_ID"
    log "Orchestrator: $ORCHESTRATOR_URL"
    log "Redis: $REDIS_URL"
    
    local registration_success=true
    local redis_success=true
    local connectivity_success=true
    
    # Test connectivity first
    if ! test_connectivity; then
        log "⚠ Connectivity test failed, but continuing registration..."
        connectivity_success=false
    fi
    
    # Register with orchestrator
    if ! register_with_orchestrator; then
        log "✗ Orchestrator registration failed"
        registration_success=false
    fi
    
    # Store in Redis (non-critical)
    if ! store_in_redis; then
        log "⚠ Redis storage failed (non-critical)"
        redis_success=false
    fi
    
    # Set up heartbeat
    create_heartbeat
    
    # Final status
    if [ "$registration_success" = true ]; then
        log "✓ Worker registration completed successfully"
        
        # Update final status
        if redis-cli -u "$REDIS_URL" hset "worker:$WORKER_ID" \
            registration_status "completed" \
            registration_completed_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >/dev/null 2>&1; then
            log "✓ Registration status updated in Redis"
        fi
        
        return 0
    else
        log "✗ Worker registration failed"
        
        # Update failure status
        redis-cli -u "$REDIS_URL" hset "worker:$WORKER_ID" \
            registration_status "failed" \
            registration_failed_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >/dev/null 2>&1 || true
            
        return 1
    fi
}

# Handle graceful shutdown
cleanup() {
    log "Received shutdown signal, deregistering worker..."
    
    # Notify orchestrator of shutdown through proxy
    curl_proxy -X DELETE "$ORCHESTRATOR_URL/workers/$WORKER_ID" \
        -H "Authorization: Bearer ${CHAT_API_TOKEN:-default}" \
        -s --connect-timeout 5 >/dev/null 2>&1 || true
    
    # Update Redis status
    redis-cli -u "$REDIS_URL" hset "worker:$WORKER_ID" \
        status "offline" \
        deregistered_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >/dev/null 2>&1 || true
    
    log "Worker deregistration completed"
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Run main registration
main "$@"