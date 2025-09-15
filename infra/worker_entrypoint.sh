#!/bin/bash
# Worker VM Entrypoint Script
# Initializes a worker VM and connects it to the QA testing infrastructure

set -euo pipefail

# Configuration
WORKER_ID="${WORKER_ID:-$(hostname)-$(date +%s)}"
LOG_FILE="/var/log/qa-worker.log"
ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://orchestrator:5000}"
REDIS_URL="${REDIS_URL:-redis://redis:6379}"

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

# Create log directory
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [Worker:$WORKER_ID] $1" | tee -a "$LOG_FILE"
}

log "Starting worker initialization..."
log "Worker ID: $WORKER_ID"

# Step 1: Load secrets from Vault
load_secrets() {
    log "Loading secrets from Vault..."
    
    if [ -f "/infra/vault_loader.py" ]; then
        if python3 /infra/vault_loader.py; then
            log "Secrets loaded from Vault successfully"
        else
            log "Failed to load from Vault, using environment fallback"
        fi
    else
        log "Vault loader not found, using environment variables"
    fi
}

# Step 2: Install required dependencies
install_dependencies() {
    log "Installing worker dependencies..."
    
    # Update system
    apt-get update -y
    
    # Install essential packages
    apt-get install -y \
        python3 \
        python3-pip \
        docker.io \
        redis-tools \
        curl \
        jq \
        android-tools-adb \
        imagemagick \
        ffmpeg \
        git \
        proxychains4 \
        socat \
        iptables \
        netcat-openbsd
    
    # Install Python packages
    pip3 install \
        requests \
        redis \
        hvac \
        flask \
        numpy \
        pillow \
        opencv-python-headless \
        bezier \
        pysocks
    
    # Start Docker
    systemctl enable docker
    systemctl start docker
    
    # Add worker user to docker group
    usermod -aG docker $(whoami) || true
    
    log "Dependencies installed successfully"
}

# Step 3: Run warmup routine
warmup_routine() {
    log "Running worker warmup routine..."
    
    if [ -f "/infra/warmup.sh" ]; then
        bash /infra/warmup.sh
    else
        log "Creating basic warmup routine..."
        
        # Test basic functionality
        python3 -c "import requests, redis, json; print('Python libraries OK')"
        
        # Test Redis connection
        if redis-cli -u "$REDIS_URL" ping >/dev/null 2>&1; then
            log "Redis connection: OK"
        else
            log "Redis connection: FAILED"
        fi
        
        # Configure proxy chains
        cat > /etc/proxychains4.conf << EOF
strict_chain
proxy_dns 
remote_dns_subnet 224
tcp_read_time_out 15000
tcp_connect_time_out 8000
localnet 127.0.0.0/255.0.0.0
localnet 10.0.0.0/255.0.0.0
localnet 172.16.0.0/255.240.0.0
localnet 192.168.0.0/255.255.0.0

[ProxyList]
socks5 ${SMARTPROXY_HOST} ${SMARTPROXY_PORT} ${SMARTPROXY_USER} ${SMARTPROXY_PASS}
EOF
        
        # Test orchestrator connection through proxy
        if curl_proxy -f "$ORCHESTRATOR_URL/health" >/dev/null 2>&1; then
            log "Orchestrator connection: OK (via proxy)"
        else
            log "Orchestrator connection: FAILED (via proxy)"
        fi
        
        # Test proxy connectivity
        if curl_proxy -s --connect-timeout 10 https://httpbin.org/ip > /tmp/proxy_test.json 2>/dev/null; then
            PROXY_IP=$(jq -r '.origin' /tmp/proxy_test.json 2>/dev/null || echo "unknown")
            log "Proxy connectivity: OK - External IP: $PROXY_IP"
        else
            log "Proxy connectivity: FAILED"
        fi
        
        # Set up ADB proxy
        cat > /usr/local/bin/adb-proxy << 'ADBEOF'
#!/bin/bash
exec proxychains4 adb "$@"
ADBEOF
        chmod +x /usr/local/bin/adb-proxy
        echo "alias adb='proxychains4 adb'" >> /root/.bashrc
        
        # Create worker directories
        mkdir -p /opt/qa-worker/{scripts,data,logs,temp}
        
        # Set up basic Android emulator if needed
        if command -v adb >/dev/null 2>&1; then
            adb start-server || true
            log "ADB server started"
        fi
    fi
    
    log "Warmup routine completed"
}

# Step 4: Register with orchestrator
register_worker() {
    log "Registering worker with orchestrator..."
    
    if [ -f "/infra/register.sh" ]; then
        bash /infra/register.sh
    else
        log "Creating basic registration..."
        
        # Prepare registration data
        REGISTRATION_DATA=$(cat <<EOF
{
    "worker_id": "$WORKER_ID",
    "hostname": "$(hostname)",
    "ip_address": "$(curl_proxy -s ifconfig.me || echo 'unknown')",
    "capabilities": ["touch_test", "network_test", "image_test"],
    "max_concurrent_jobs": 3,
    "status": "ready",
    "registered_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
)
        
        # Register with orchestrator through proxy
        if curl_proxy -X POST "$ORCHESTRATOR_URL/workers/register" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer ${CHAT_API_TOKEN:-default}" \
            -d "$REGISTRATION_DATA" >/dev/null 2>&1; then
            log "Successfully registered with orchestrator (via proxy)"
        else
            log "Failed to register with orchestrator via proxy, will retry later"
        fi
        
        # Store registration info in Redis
        if redis-cli -u "$REDIS_URL" hset "worker:$WORKER_ID" \
            status "ready" \
            registered_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
            hostname "$(hostname)" >/dev/null 2>&1; then
            log "Worker info stored in Redis"
        fi
    fi
}

# Step 5: Start worker processes
start_worker_processes() {
    log "Starting worker processes..."
    
    # Create worker process script
    cat > /opt/qa-worker/worker_process.py << 'EOF'
#!/usr/bin/env python3
import redis
import json
import time
import logging
import subprocess
import os
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WorkerProcess:
    def __init__(self):
        self.worker_id = os.environ.get('WORKER_ID', 'unknown')
        self.redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
        self.running = True
    
    def process_job(self, job_data):
        """Process a single job"""
        job_id = job_data.get('id', 'unknown')
        job_type = job_data.get('type', 'unknown')
        
        logger.info(f"Processing job {job_id} of type {job_type}")
        
        # Update job status
        self.redis_client.hset(f"job:{job_id}", "status", "running")
        self.redis_client.hset(f"job:{job_id}", "worker_id", self.worker_id)
        self.redis_client.hset(f"job:{job_id}", "started_at", datetime.now().isoformat())
        
        try:
            if job_type == "touch_test":
                result = subprocess.run([
                    "python3", "/automation/scripts/touch_simulator.py", 
                    "--test-count", "5"
                ], capture_output=True, text=True, timeout=300)
                
            elif job_type == "network_test":
                result = subprocess.run([
                    "python3", "/automation/scripts/network_test.py",
                    "--condition", "wifi"
                ], capture_output=True, text=True, timeout=300)
                
            elif job_type == "image_test":
                result = subprocess.run([
                    "bash", "/automation/scripts/image_setup.sh"
                ], capture_output=True, text=True, timeout=300)
                
            else:
                logger.warning(f"Unknown job type: {job_type}")
                result = subprocess.CompletedProcess([], 1, "Unknown job type", "")
            
            # Update job with results
            if result.returncode == 0:
                self.redis_client.hset(f"job:{job_id}", "status", "completed")
                self.redis_client.hset(f"job:{job_id}", "results", result.stdout)
            else:
                self.redis_client.hset(f"job:{job_id}", "status", "failed")
                self.redis_client.hset(f"job:{job_id}", "error", result.stderr)
            
            self.redis_client.hset(f"job:{job_id}", "completed_at", datetime.now().isoformat())
            logger.info(f"Job {job_id} completed with status: {result.returncode}")
            
        except Exception as e:
            logger.error(f"Job {job_id} failed with exception: {e}")
            self.redis_client.hset(f"job:{job_id}", "status", "failed")
            self.redis_client.hset(f"job:{job_id}", "error", str(e))
    
    def run(self):
        """Main worker loop"""
        logger.info(f"Worker {self.worker_id} starting...")
        
        while self.running:
            try:
                # Check for jobs in the queue
                job_json = self.redis_client.lpop('test_queue')
                
                if job_json:
                    job_data = json.loads(job_json)
                    self.process_job(job_data)
                else:
                    # No jobs available, sleep briefly
                    time.sleep(10)
                    
                # Update worker heartbeat
                self.redis_client.hset(f"worker:{self.worker_id}", 
                                     "last_seen", datetime.now().isoformat())
                
            except KeyboardInterrupt:
                logger.info("Worker stopping...")
                self.running = False
            except Exception as e:
                logger.error(f"Worker error: {e}")
                time.sleep(30)

if __name__ == "__main__":
    worker = WorkerProcess()
    worker.run()
EOF
    
    chmod +x /opt/qa-worker/worker_process.py
    
    # Start worker process in background
    nohup python3 /opt/qa-worker/worker_process.py > /var/log/qa-worker-process.log 2>&1 &
    WORKER_PID=$!
    
    log "Worker process started with PID: $WORKER_PID"
    
    # Create systemd service for worker persistence
    cat > /etc/systemd/system/qa-worker.service << EOF
[Unit]
Description=QA Framework Worker Process
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/qa-worker
ExecStart=/usr/bin/python3 /opt/qa-worker/worker_process.py
Restart=always
RestartSec=10
Environment=WORKER_ID=$WORKER_ID
Environment=REDIS_URL=$REDIS_URL
Environment=ORCHESTRATOR_URL=$ORCHESTRATOR_URL

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable qa-worker.service
    systemctl start qa-worker.service
    
    log "Worker service configured and started"
}

# Step 6: Health monitoring setup
setup_monitoring() {
    log "Setting up worker monitoring..."
    
    # Create health check script
    cat > /opt/qa-worker/health_check.sh << 'EOF'
#!/bin/bash
# Worker health check script

WORKER_ID="${WORKER_ID:-$(hostname)}"
REDIS_URL="${REDIS_URL:-redis://localhost:6379}"

# Check if worker process is running
if ! pgrep -f "worker_process.py" > /dev/null; then
    echo "Worker process not running, restarting..."
    systemctl restart qa-worker.service
fi

# Update health status in Redis
redis-cli -u "$REDIS_URL" hset "worker:$WORKER_ID" \
    health_check "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    status "healthy" >/dev/null 2>&1 || echo "Redis health update failed"

echo "Health check completed"
EOF
    
    chmod +x /opt/qa-worker/health_check.sh
    
    # Schedule health checks
    (crontab -l 2>/dev/null; echo "*/5 * * * * /opt/qa-worker/health_check.sh") | crontab -
    
    log "Health monitoring configured"
}

# Main execution
main() {
    log "Worker entrypoint starting..."
    
    # Execute all initialization steps
    load_secrets
    install_dependencies
    warmup_routine
    register_worker
    start_worker_processes
    setup_monitoring
    
    log "Worker initialization completed successfully"
    log "Worker $WORKER_ID is now ready and running"
    
    # Keep the script running for Docker containers
    if [ "${CONTAINER_MODE:-false}" = "true" ]; then
        log "Running in container mode, keeping process alive..."
        while true; do
            sleep 3600  # Sleep for 1 hour
            log "Worker heartbeat: $(date)"
        done
    fi
}

# Handle signals for graceful shutdown
cleanup() {
    log "Received shutdown signal, cleaning up..."
    
    # Stop worker service
    systemctl stop qa-worker.service 2>/dev/null || true
    
    # Update worker status
    redis-cli -u "$REDIS_URL" hset "worker:$WORKER_ID" \
        status "offline" \
        stopped_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" 2>/dev/null || true
    
    log "Worker cleanup completed"
    exit 0
}

trap cleanup SIGTERM SIGINT

# Run main function
main "$@"