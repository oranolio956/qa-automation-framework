#!/bin/bash
# Worker Warmup Script
# Prepares the worker environment and validates functionality

set -euo pipefail

WORKER_ID="${WORKER_ID:-$(hostname)-$(date +%s)}"
LOG_FILE="/var/log/qa-worker-warmup.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [Warmup:$WORKER_ID] $1" | tee -a "$LOG_FILE"
}

log "Starting worker warmup routine..."

# Test network connectivity
test_connectivity() {
    log "Testing network connectivity..."
    
    local test_urls=(
        "https://google.com"
        "https://httpbin.org/get"
        "${ORCHESTRATOR_URL:-http://orchestrator:5000}/health"
    )
    
    local success_count=0
    for url in "${test_urls[@]}"; do
        if curl -f -s "$url" >/dev/null 2>&1; then
            log "✓ Connectivity test passed: $url"
            ((success_count++))
        else
            log "✗ Connectivity test failed: $url"
        fi
    done
    
    log "Connectivity test results: $success_count/${#test_urls[@]} passed"
    return $((${#test_urls[@]} - success_count))
}

# Test Redis connection
test_redis() {
    log "Testing Redis connection..."
    
    if redis-cli -u "${REDIS_URL:-redis://localhost:6379}" ping >/dev/null 2>&1; then
        log "✓ Redis connection successful"
        return 0
    else
        log "✗ Redis connection failed"
        return 1
    fi
}

# Test Python environment
test_python_env() {
    log "Testing Python environment..."
    
    local required_modules=("requests" "redis" "json" "numpy" "PIL")
    local success_count=0
    
    for module in "${required_modules[@]}"; do
        if python3 -c "import $module" 2>/dev/null; then
            log "✓ Python module available: $module"
            ((success_count++))
        else
            log "✗ Python module missing: $module"
        fi
    done
    
    log "Python environment test: $success_count/${#required_modules[@]} modules available"
    return $((${#required_modules[@]} - success_count))
}

# Test ADB functionality
test_adb() {
    log "Testing ADB functionality..."
    
    if command -v adb >/dev/null 2>&1; then
        adb start-server 2>/dev/null || true
        log "✓ ADB server started"
        
        # Test basic ADB commands
        if adb devices >/dev/null 2>&1; then
            log "✓ ADB devices command working"
            return 0
        else
            log "✗ ADB devices command failed"
            return 1
        fi
    else
        log "✗ ADB not available"
        return 1
    fi
}

# Test Docker functionality
test_docker() {
    log "Testing Docker functionality..."
    
    if command -v docker >/dev/null 2>&1; then
        if docker info >/dev/null 2>&1; then
            log "✓ Docker daemon accessible"
            return 0
        else
            log "✗ Docker daemon not accessible"
            return 1
        fi
    else
        log "✗ Docker not available"
        return 1
    fi
}

# Test image processing capabilities
test_image_processing() {
    log "Testing image processing capabilities..."
    
    local test_passed=0
    
    # Test ImageMagick
    if command -v convert >/dev/null 2>&1; then
        if convert -size 100x100 xc:red /tmp/test_red.jpg 2>/dev/null; then
            log "✓ ImageMagick working"
            rm -f /tmp/test_red.jpg
            test_passed=1
        else
            log "✗ ImageMagick test failed"
        fi
    else
        log "✗ ImageMagick not available"
    fi
    
    # Test Python PIL
    if python3 -c "from PIL import Image; Image.new('RGB', (100,100), 'blue').save('/tmp/test_blue.jpg')" 2>/dev/null; then
        log "✓ Python PIL working"
        rm -f /tmp/test_blue.jpg
        test_passed=1
    else
        log "✗ Python PIL test failed"
    fi
    
    return $((1 - test_passed))
}

# Simulate a basic test job
simulate_test_job() {
    log "Simulating basic test job..."
    
    # Create a simple test script
    cat > /tmp/warmup_test.py << 'EOF'
#!/usr/bin/env python3
import time
import json
import random

def simulate_touch_test():
    """Simulate a touch test"""
    print("Simulating touch test...")
    time.sleep(2)
    return {
        "test_type": "touch_test",
        "gestures_performed": random.randint(10, 20),
        "success_rate": random.uniform(0.8, 1.0),
        "duration_ms": random.randint(2000, 5000)
    }

def simulate_network_test():
    """Simulate a network test"""
    print("Simulating network test...")
    time.sleep(3)
    return {
        "test_type": "network_test",
        "latency_ms": random.randint(20, 200),
        "bandwidth_mbps": random.randint(10, 100),
        "packet_loss_percent": random.uniform(0, 2)
    }

if __name__ == "__main__":
    results = []
    results.append(simulate_touch_test())
    results.append(simulate_network_test())
    
    print(json.dumps(results, indent=2))
EOF
    
    if python3 /tmp/warmup_test.py >/dev/null 2>&1; then
        log "✓ Test job simulation successful"
        rm -f /tmp/warmup_test.py
        return 0
    else
        log "✗ Test job simulation failed"
        rm -f /tmp/warmup_test.py
        return 1
    fi
}

# Register initial capabilities
register_capabilities() {
    log "Registering worker capabilities..."
    
    local capabilities=()
    
    # Test available capabilities
    if python3 -c "import requests" 2>/dev/null; then
        capabilities+=("network_test")
    fi
    
    if command -v adb >/dev/null 2>&1; then
        capabilities+=("touch_test")
    fi
    
    if command -v convert >/dev/null 2>&1 || python3 -c "from PIL import Image" 2>/dev/null; then
        capabilities+=("image_test")
    fi
    
    if command -v docker >/dev/null 2>&1; then
        capabilities+=("container_test")
    fi
    
    # Store capabilities in Redis
    if redis-cli -u "${REDIS_URL:-redis://localhost:6379}" sadd "worker:$WORKER_ID:capabilities" "${capabilities[@]}" >/dev/null 2>&1; then
        log "✓ Capabilities registered: ${capabilities[*]}"
    else
        log "✗ Failed to register capabilities"
    fi
    
    return 0
}

# Performance benchmark
run_benchmark() {
    log "Running performance benchmark..."
    
    local start_time cpu_usage memory_usage disk_usage
    start_time=$(date +%s)
    
    # CPU benchmark - simple calculation
    python3 -c "
import time
start = time.time()
result = sum(i*i for i in range(100000))
duration = time.time() - start
print(f'CPU benchmark: {duration:.3f}s')
" 2>/dev/null || log "CPU benchmark failed"
    
    # Memory usage check
    memory_usage=$(free | grep '^Mem:' | awk '{printf "%.1f", ($3/$2) * 100.0}' 2>/dev/null || echo "unknown")
    log "Memory usage: ${memory_usage}%"
    
    # Disk usage check
    disk_usage=$(df / | tail -1 | awk '{print $5}' 2>/dev/null || echo "unknown")
    log "Disk usage: $disk_usage"
    
    # Store benchmark results
    if redis-cli -u "${REDIS_URL:-redis://localhost:6379}" hset "worker:$WORKER_ID:benchmark" \
        memory_usage "$memory_usage" \
        disk_usage "$disk_usage" \
        benchmark_time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >/dev/null 2>&1; then
        log "✓ Benchmark results stored"
    fi
}

# Main warmup routine
main() {
    log "=== Worker Warmup Started ==="
    
    local tests=(
        "test_connectivity"
        "test_redis" 
        "test_python_env"
        "test_adb"
        "test_docker"
        "test_image_processing"
        "simulate_test_job"
        "register_capabilities"
        "run_benchmark"
    )
    
    local passed=0
    local failed=0
    
    for test in "${tests[@]}"; do
        log "Running: $test"
        if $test; then
            ((passed++))
        else
            ((failed++))
        fi
    done
    
    log "=== Warmup Summary ==="
    log "Tests passed: $passed"
    log "Tests failed: $failed"
    log "Overall status: $( (( failed == 0 )) && echo "READY" || echo "DEGRADED" )"
    
    # Update worker status
    local status="ready"
    (( failed > 0 )) && status="degraded"
    
    redis-cli -u "${REDIS_URL:-redis://localhost:6379}" hset "worker:$WORKER_ID" \
        warmup_status "$status" \
        warmup_completed "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        tests_passed "$passed" \
        tests_failed "$failed" >/dev/null 2>&1 || true
    
    log "=== Worker Warmup Completed ==="
    
    return $failed
}

# Run main function
main "$@"