#!/bin/bash
# QA Test Agent Starter Script
# Starts an individual test agent process

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_ID="${1:-$(uuidgen | tr '[:upper:]' '[:lower:]' | cut -c1-8)}"
LOG_FILE="/var/log/qa-framework/agent_${AGENT_ID}.log"

mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [Agent:$AGENT_ID] $1" | tee -a "$LOG_FILE"
}

cleanup() {
    log "Test agent shutting down..."
    exit 0
}

trap cleanup SIGTERM SIGINT

log "Starting QA test agent..."
log "Agent ID: $AGENT_ID"
log "Process ID: $$"

# Main test agent loop
while true; do
    # Check for test tasks in Redis queue
    if command -v redis-cli >/dev/null 2>&1; then
        TASK=$(redis-cli LPOP test_queue 2>/dev/null || echo "")
        
        if [ -n "$TASK" ] && [ "$TASK" != "(nil)" ]; then
            log "Processing task: $TASK"
            
            # Execute the test task
            case "$TASK" in
                "touch_test")
                    python3 "$SCRIPT_DIR/touch_simulator.py" --test-count 5
                    ;;
                "network_test")
                    python3 "$SCRIPT_DIR/network_test.py" --condition wifi
                    ;;
                "image_test")
                    bash "$SCRIPT_DIR/image_setup.sh"
                    ;;
                *)
                    log "Unknown task type: $TASK"
                    ;;
            esac
            
            log "Task completed: $TASK"
        else
            # No tasks available, sleep briefly
            sleep 10
        fi
    else
        # Redis not available, run periodic tests
        log "Running periodic test cycle..."
        
        # Run touch simulation
        if [ -f "$SCRIPT_DIR/touch_simulator.py" ]; then
            python3 "$SCRIPT_DIR/touch_simulator.py" --test-count 3
        fi
        
        sleep 30
    fi
done