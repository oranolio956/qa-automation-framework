#!/bin/bash
# Autoscaling and Resource Optimization for QA Framework
# Monitors system resources and scales test agents automatically

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$SCRIPT_DIR/../config"
LOG_FILE="/var/log/qa-framework/autoscale.log"

# Default thresholds (can be overridden by config)
CPU_HIGH_THRESHOLD=${CPU_HIGH_THRESHOLD:-75}
CPU_LOW_THRESHOLD=${CPU_LOW_THRESHOLD:-25}
MEMORY_HIGH_THRESHOLD=${MEMORY_HIGH_THRESHOLD:-80}
QUEUE_BACKLOG_THRESHOLD=${QUEUE_BACKLOG_THRESHOLD:-10}
MIN_REPLICAS=${MIN_REPLICAS:-1}
MAX_REPLICAS=${MAX_REPLICAS:-10}
SCALE_UP_COOLDOWN=${SCALE_UP_COOLDOWN:-300}
SCALE_DOWN_COOLDOWN=${SCALE_DOWN_COOLDOWN:-600}

# State files
STATE_DIR="/tmp/qa-autoscale"
LAST_SCALE_UP_FILE="$STATE_DIR/last_scale_up"
LAST_SCALE_DOWN_FILE="$STATE_DIR/last_scale_down"
CURRENT_REPLICAS_FILE="$STATE_DIR/current_replicas"

mkdir -p "$STATE_DIR" "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

load_config() {
    local config_file="$CONFIG_DIR/autoscale.conf"
    if [ -f "$config_file" ]; then
        log "Loading configuration from $config_file"
        source "$config_file"
    fi
}

get_cpu_usage() {
    # Get average CPU usage across all cores
    if command -v kubectl >/dev/null 2>&1; then
        # Kubernetes environment
        kubectl top nodes --no-headers 2>/dev/null | awk '{sum+=$3} END{print sum/NR}' | sed 's/%//'
    else
        # Local system
        top -l 1 -n 0 | grep "CPU usage" | awk '{print $3}' | sed 's/%//' | head -1
    fi
}

get_memory_usage() {
    if command -v kubectl >/dev/null 2>&1; then
        # Kubernetes environment
        kubectl top nodes --no-headers 2>/dev/null | awk '{sum+=$5} END{print sum/NR}' | sed 's/%//'
    else
        # Local system - macOS specific
        vm_stat | grep "Pages active:" | awk '{print $3}' | sed 's/\.//' || echo "0"
    fi
}

get_queue_length() {
    # Get Redis queue length
    if command -v redis-cli >/dev/null 2>&1; then
        redis-cli LLEN test_queue 2>/dev/null || echo "0"
    else
        echo "0"
    fi
}

get_current_replicas() {
    if [ -f "$CURRENT_REPLICAS_FILE" ]; then
        cat "$CURRENT_REPLICAS_FILE"
    else
        echo "$MIN_REPLICAS"
    fi
}

set_current_replicas() {
    echo "$1" > "$CURRENT_REPLICAS_FILE"
}

get_last_scale_time() {
    local scale_type="$1"
    local file_path
    
    case "$scale_type" in
        "up")
            file_path="$LAST_SCALE_UP_FILE"
            ;;
        "down")
            file_path="$LAST_SCALE_DOWN_FILE"
            ;;
        *)
            echo "0"
            return
            ;;
    esac
    
    if [ -f "$file_path" ]; then
        cat "$file_path"
    else
        echo "0"
    fi
}

set_last_scale_time() {
    local scale_type="$1"
    local timestamp="$(date +%s)"
    
    case "$scale_type" in
        "up")
            echo "$timestamp" > "$LAST_SCALE_UP_FILE"
            ;;
        "down")
            echo "$timestamp" > "$LAST_SCALE_DOWN_FILE"
            ;;
    esac
}

check_cooldown() {
    local scale_type="$1"
    local cooldown_period
    local last_scale_time
    local current_time="$(date +%s)"
    
    case "$scale_type" in
        "up")
            cooldown_period="$SCALE_UP_COOLDOWN"
            ;;
        "down")
            cooldown_period="$SCALE_DOWN_COOLDOWN"
            ;;
        *)
            return 1
            ;;
    esac
    
    last_scale_time="$(get_last_scale_time "$scale_type")"
    
    if [ "$((current_time - last_scale_time))" -lt "$cooldown_period" ]; then
        log "Scale $scale_type in cooldown period ($(((current_time - last_scale_time))) / $cooldown_period seconds)"
        return 1
    fi
    
    return 0
}

scale_kubernetes_deployment() {
    local new_replicas="$1"
    local deployment_name="${DEPLOYMENT_NAME:-test-agent}"
    
    log "Scaling Kubernetes deployment $deployment_name to $new_replicas replicas"
    
    if kubectl scale deployment "$deployment_name" --replicas="$new_replicas"; then
        log "Successfully scaled deployment to $new_replicas replicas"
        return 0
    else
        log "Failed to scale deployment"
        return 1
    fi
}

scale_docker_compose() {
    local new_replicas="$1"
    local service_name="${SERVICE_NAME:-qa-test-agent}"
    
    log "Scaling Docker Compose service $service_name to $new_replicas replicas"
    
    if docker-compose up -d --scale "$service_name=$new_replicas"; then
        log "Successfully scaled service to $new_replicas replicas"
        return 0
    else
        log "Failed to scale service"
        return 1
    fi
}

scale_local_processes() {
    local new_replicas="$1"
    local current_replicas="$2"
    local process_script="$SCRIPT_DIR/start_test_agent.sh"
    
    if [ ! -f "$process_script" ]; then
        log "Warning: Test agent script not found at $process_script"
        return 1
    fi
    
    if [ "$new_replicas" -gt "$current_replicas" ]; then
        # Scale up - start new processes
        local processes_to_start="$((new_replicas - current_replicas))"
        log "Starting $processes_to_start new test agent processes"
        
        for i in $(seq 1 "$processes_to_start"); do
            nohup "$process_script" > "/var/log/qa-framework/agent_$((current_replicas + i)).log" 2>&1 &
            log "Started test agent process (PID: $!)"
        done
    else
        # Scale down - stop existing processes
        local processes_to_stop="$((current_replicas - new_replicas))"
        log "Stopping $processes_to_stop test agent processes"
        
        # Find and stop the newest processes
        pkill -f "start_test_agent.sh" -c "$processes_to_stop"
    fi
    
    return 0
}

perform_scaling() {
    local new_replicas="$1"
    local scale_type="$2"
    local current_replicas="$(get_current_replicas)"
    
    if [ "$new_replicas" -eq "$current_replicas" ]; then
        return 0
    fi
    
    log "Scaling from $current_replicas to $new_replicas replicas ($scale_type)"
    
    # Try different scaling methods based on environment
    if command -v kubectl >/dev/null 2>&1 && kubectl cluster-info >/dev/null 2>&1; then
        # Kubernetes environment
        if scale_kubernetes_deployment "$new_replicas"; then
            set_current_replicas "$new_replicas"
            set_last_scale_time "$scale_type"
            return 0
        fi
    elif command -v docker-compose >/dev/null 2>&1 && [ -f "docker-compose.yml" ]; then
        # Docker Compose environment
        if scale_docker_compose "$new_replicas"; then
            set_current_replicas "$new_replicas"
            set_last_scale_time "$scale_type"
            return 0
        fi
    else
        # Local process management
        if scale_local_processes "$new_replicas" "$current_replicas"; then
            set_current_replicas "$new_replicas"
            set_last_scale_time "$scale_type"
            return 0
        fi
    fi
    
    log "Failed to perform scaling operation"
    return 1
}

optimize_host_resources() {
    log "Optimizing host resources..."
    
    # Enable KSM (Kernel Same-page Merging) for memory deduplication on Linux
    if [ -f "/sys/kernel/mm/ksm/run" ]; then
        echo 1 > /sys/kernel/mm/ksm/run 2>/dev/null || true
        echo 500 > /sys/kernel/mm/ksm/pages_to_scan 2>/dev/null || true
        log "Enabled KSM for memory optimization"
    fi
    
    # Optimize VM graphics for headless operation
    if command -v virsh >/dev/null 2>&1; then
        for vm in $(virsh list --name --all | grep "qa-"); do
            if virsh dumpxml "$vm" | grep -q 'graphics type="vnc"'; then
                log "Optimizing graphics for VM: $vm"
                # This would modify the VM configuration to be headless
                # Implementation depends on specific VM setup
            fi
        done
    fi
    
    # Adjust system swappiness for better performance
    if [ -f "/proc/sys/vm/swappiness" ]; then
        echo 10 > /proc/sys/vm/swappiness 2>/dev/null || true
        log "Optimized system swappiness"
    fi
    
    # Clean up old log files
    find /var/log/qa-framework -name "*.log" -mtime +7 -delete 2>/dev/null || true
    
    log "Host resource optimization completed"
}

check_and_scale() {
    log "Checking system metrics for autoscaling..."
    
    # Get current metrics
    local cpu_usage memory_usage queue_length current_replicas
    cpu_usage="$(get_cpu_usage)"
    memory_usage="$(get_memory_usage)"
    queue_length="$(get_queue_length)"
    current_replicas="$(get_current_replicas)"
    
    # Handle case where metrics are not available
    cpu_usage="${cpu_usage:-0}"
    memory_usage="${memory_usage:-0}"
    queue_length="${queue_length:-0}"
    
    log "Current metrics - CPU: ${cpu_usage}%, Memory: ${memory_usage}%, Queue: $queue_length, Replicas: $current_replicas"
    
    # Determine if scaling is needed
    local should_scale_up=false
    local should_scale_down=false
    
    # Scale up conditions
    if (( $(echo "$cpu_usage > $CPU_HIGH_THRESHOLD" | bc -l 2>/dev/null || echo "0") )) || \
       (( $(echo "$memory_usage > $MEMORY_HIGH_THRESHOLD" | bc -l 2>/dev/null || echo "0") )) || \
       [ "$queue_length" -gt "$QUEUE_BACKLOG_THRESHOLD" ]; then
        should_scale_up=true
    fi
    
    # Scale down conditions (only if not scaling up)
    if [ "$should_scale_up" = false ] && \
       (( $(echo "$cpu_usage < $CPU_LOW_THRESHOLD" | bc -l 2>/dev/null || echo "0") )) && \
       [ "$queue_length" -eq 0 ]; then
        should_scale_down=true
    fi
    
    # Perform scaling if needed and not in cooldown
    if [ "$should_scale_up" = true ] && [ "$current_replicas" -lt "$MAX_REPLICAS" ]; then
        if check_cooldown "up"; then
            local new_replicas="$((current_replicas + 1))"
            log "Scaling up due to high resource usage or queue backlog"
            perform_scaling "$new_replicas" "up"
        fi
    elif [ "$should_scale_down" = true ] && [ "$current_replicas" -gt "$MIN_REPLICAS" ]; then
        if check_cooldown "down"; then
            local new_replicas="$((current_replicas - 1))"
            log "Scaling down due to low resource usage"
            perform_scaling "$new_replicas" "down"
        fi
    else
        log "No scaling action needed"
    fi
}

run_continuous_monitoring() {
    local interval="${1:-300}"  # Default 5 minutes
    
    log "Starting continuous autoscaling monitoring (interval: ${interval}s)"
    
    while true; do
        check_and_scale
        
        # Periodic resource optimization
        if [ "$(($(date +%s) % 3600))" -lt "$interval" ]; then
            optimize_host_resources
        fi
        
        sleep "$interval"
    done
}

main() {
    log "Starting QA Framework autoscaler..."
    
    # Load configuration
    load_config
    
    # Parse command line arguments
    case "${1:-check}" in
        "check")
            check_and_scale
            ;;
        "monitor")
            run_continuous_monitoring "${2:-300}"
            ;;
        "optimize")
            optimize_host_resources
            ;;
        "status")
            local cpu_usage memory_usage queue_length current_replicas
            cpu_usage="$(get_cpu_usage)"
            memory_usage="$(get_memory_usage)"
            queue_length="$(get_queue_length)"
            current_replicas="$(get_current_replicas)"
            
            echo "=== QA Framework Status ==="
            echo "CPU Usage: ${cpu_usage}%"
            echo "Memory Usage: ${memory_usage}%"
            echo "Queue Length: $queue_length"
            echo "Current Replicas: $current_replicas"
            echo "=========================="
            ;;
        *)
            echo "Usage: $0 {check|monitor|optimize|status}"
            echo "  check    - Perform one-time scaling check"
            echo "  monitor  - Run continuous monitoring"
            echo "  optimize - Optimize host resources"
            echo "  status   - Show current system status"
            exit 1
            ;;
    esac
    
    log "Autoscaler operation completed"
}

# Check if running as root for certain operations
if [[ $EUID -eq 0 ]] || groups | grep -q sudo; then
    HAS_SUDO=true
else
    HAS_SUDO=false
fi

main "$@"