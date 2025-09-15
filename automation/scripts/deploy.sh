#!/bin/bash
# QA Framework Deployment Script
# Deploys the complete Phase 14A QA emulation framework

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="/var/log/qa-framework/deploy.log"

mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_prerequisites() {
    log "Checking prerequisites..."
    
    local required_commands=("python3" "docker" "docker-compose")
    local missing_commands=()
    
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            missing_commands+=("$cmd")
        fi
    done
    
    if [ ${#missing_commands[@]} -gt 0 ]; then
        log "ERROR: Missing required commands: ${missing_commands[*]}"
        log "Please run the installation script first: sudo $SCRIPT_DIR/install_dependencies.sh"
        exit 1
    fi
    
    log "Prerequisites check passed"
}

create_docker_compose() {
    log "Creating Docker Compose configuration..."
    
    cat > "$PROJECT_ROOT/docker-compose-qa.yml" << 'EOF'
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - qa_redis_data:/data
    networks:
      - qa_network
    restart: unless-stopped

  qa-test-agent:
    build:
      context: .
      dockerfile: automation/Dockerfile.agent
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - LOG_LEVEL=INFO
    volumes:
      - ./automation/scripts:/app/scripts:ro
      - qa_logs:/var/log/qa-framework
    depends_on:
      - redis
    networks:
      - qa_network
    restart: unless-stopped
    deploy:
      replicas: 2

  qa-monitor:
    build:
      context: .
      dockerfile: automation/Dockerfile.monitor
    ports:
      - "8080:8080"
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    volumes:
      - qa_logs:/var/log/qa-framework:ro
    depends_on:
      - redis
    networks:
      - qa_network
    restart: unless-stopped

  autoscaler:
    build:
      context: .
      dockerfile: automation/Dockerfile.autoscaler
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    volumes:
      - ./automation/config:/app/config:ro
      - /var/run/docker.sock:/var/run/docker.sock
    depends_on:
      - redis
      - qa-test-agent
    networks:
      - qa_network
    restart: unless-stopped

volumes:
  qa_redis_data:
  qa_logs:

networks:
  qa_network:
    driver: bridge
EOF
    
    log "Docker Compose configuration created"
}

create_dockerfiles() {
    log "Creating Dockerfiles..."
    
    # Test Agent Dockerfile
    cat > "$PROJECT_ROOT/automation/Dockerfile.agent" << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    android-tools-adb \
    imagemagick \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY automation/scripts/ ./scripts/
COPY automation/config/ ./config/

# Create log directory
RUN mkdir -p /var/log/qa-framework

# Make scripts executable
RUN chmod +x ./scripts/*.sh ./scripts/*.py

# Run the test agent
CMD ["./scripts/start_test_agent.sh"]
EOF

    # Monitor Dockerfile
    cat > "$PROJECT_ROOT/automation/Dockerfile.monitor" << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install flask redis prometheus_client

# Copy monitoring script
COPY automation/scripts/monitor.py ./

# Create log directory
RUN mkdir -p /var/log/qa-framework

EXPOSE 8080

CMD ["python", "monitor.py"]
EOF

    # Autoscaler Dockerfile
    cat > "$PROJECT_ROOT/automation/Dockerfile.autoscaler" << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    docker.io \
    curl \
    bc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install redis docker

# Copy scripts
COPY automation/scripts/autoscale.sh ./
COPY automation/config/ ./config/

# Make executable
RUN chmod +x ./autoscale.sh

CMD ["./autoscale.sh", "monitor"]
EOF
    
    log "Dockerfiles created"
}

create_requirements_file() {
    log "Creating requirements.txt..."
    
    cat > "$PROJECT_ROOT/requirements.txt" << 'EOF'
# QA Framework Python Dependencies
redis==4.6.0
requests==2.31.0
numpy==1.24.3
pillow==10.0.0
opencv-python-headless==4.8.0.74
bezier==2023.7.28
flask==2.3.2
prometheus-client==0.17.1
psutil==5.9.5
pyyaml==6.0.1
pytest==7.4.0
pytest-asyncio==0.21.1
aiohttp==3.8.5
docker==6.1.3
EOF
    
    log "Requirements file created"
}

create_systemd_services() {
    if ! command -v systemctl >/dev/null 2>&1; then
        log "Systemd not available, skipping service creation"
        return
    fi
    
    log "Creating systemd services..."
    
    # QA Framework service
    cat > "/tmp/qa-framework.service" << EOF
[Unit]
Description=QA Framework Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$PROJECT_ROOT
ExecStart=/usr/bin/docker-compose -f docker-compose-qa.yml up -d
ExecStop=/usr/bin/docker-compose -f docker-compose-qa.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF
    
    # Autoscaler service
    cat > "/tmp/qa-autoscaler.service" << EOF
[Unit]
Description=QA Framework Autoscaler
After=network.target

[Service]
Type=simple
User=root
ExecStart=$SCRIPT_DIR/autoscale.sh monitor
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF
    
    if [[ $EUID -eq 0 ]] || groups | grep -q sudo; then
        # Install services if we have sudo access
        sudo mv /tmp/qa-framework.service /etc/systemd/system/
        sudo mv /tmp/qa-autoscaler.service /etc/systemd/system/
        sudo systemctl daemon-reload
        log "Systemd services created and installed"
    else
        log "Systemd services created in /tmp (requires sudo to install)"
    fi
}

create_kubernetes_manifests() {
    log "Creating Kubernetes manifests..."
    
    mkdir -p "$PROJECT_ROOT/k8s"
    
    cat > "$PROJECT_ROOT/k8s/namespace.yaml" << 'EOF'
apiVersion: v1
kind: Namespace
metadata:
  name: qa-framework
  labels:
    name: qa-framework
EOF

    cat > "$PROJECT_ROOT/k8s/redis.yaml" << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: qa-framework
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        command: ["redis-server", "--appendonly", "yes"]
        volumeMounts:
        - name: redis-data
          mountPath: /data
      volumes:
      - name: redis-data
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: qa-framework
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
EOF

    cat > "$PROJECT_ROOT/k8s/test-agent.yaml" << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-agent
  namespace: qa-framework
spec:
  replicas: 2
  selector:
    matchLabels:
      app: test-agent
  template:
    metadata:
      labels:
        app: test-agent
    spec:
      containers:
      - name: test-agent
        image: qa-test-agent:latest
        env:
        - name: REDIS_HOST
          value: "redis"
        - name: REDIS_PORT
          value: "6379"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
EOF
    
    log "Kubernetes manifests created"
}

setup_monitoring() {
    log "Setting up monitoring dashboard..."
    
    # Create monitoring script
    cat > "$PROJECT_ROOT/automation/scripts/monitor.py" << 'EOF'
#!/usr/bin/env python3
"""
QA Framework Monitoring Dashboard
Provides web interface for monitoring test execution and system metrics
"""

from flask import Flask, render_template_string, jsonify
import redis
import json
import time
from datetime import datetime
import psutil
import logging
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
TEST_COUNTER = Counter('qa_tests_total', 'Total number of tests executed', ['test_type', 'status'])
TEST_DURATION = Histogram('qa_test_duration_seconds', 'Test execution time', ['test_type'])
SYSTEM_CPU = Gauge('qa_system_cpu_percent', 'System CPU usage percentage')
SYSTEM_MEMORY = Gauge('qa_system_memory_percent', 'System memory usage percentage')
QUEUE_SIZE = Gauge('qa_queue_size', 'Number of pending tasks in queue')

# Redis connection
try:
    r = redis.Redis(host='redis', port=6379, decode_responses=True)
except:
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)

@app.route('/')
def dashboard():
    template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>QA Framework Dashboard</title>
        <meta http-equiv="refresh" content="30">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .metric { margin: 10px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
            .status-good { background-color: #d4edda; }
            .status-warning { background-color: #fff3cd; }
            .status-error { background-color: #f8d7da; }
            table { width: 100%; border-collapse: collapse; }
            th, td { text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }
        </style>
    </head>
    <body>
        <h1>QA Framework Dashboard</h1>
        <div class="metric status-good">
            <h3>System Status</h3>
            <p>CPU Usage: {{ cpu_usage }}%</p>
            <p>Memory Usage: {{ memory_usage }}%</p>
            <p>Queue Size: {{ queue_size }}</p>
            <p>Active Agents: {{ active_agents }}</p>
            <p>Last Updated: {{ timestamp }}</p>
        </div>
        
        <div class="metric">
            <h3>Recent Tests</h3>
            <table>
                <tr>
                    <th>Time</th>
                    <th>Test Type</th>
                    <th>Status</th>
                    <th>Duration</th>
                </tr>
                {% for test in recent_tests %}
                <tr>
                    <td>{{ test.time }}</td>
                    <td>{{ test.type }}</td>
                    <td>{{ test.status }}</td>
                    <td>{{ test.duration }}s</td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </body>
    </html>
    '''
    
    # Get current metrics
    cpu_usage = psutil.cpu_percent()
    memory_usage = psutil.virtual_memory().percent
    queue_size = r.llen('test_queue') if r else 0
    active_agents = len(r.keys('agent:*')) if r else 0
    
    # Get recent tests (mock data for now)
    recent_tests = [
        {
            'time': datetime.now().strftime('%H:%M:%S'),
            'type': 'Touch Test',
            'status': 'Passed',
            'duration': '2.3'
        }
    ]
    
    # Update Prometheus metrics
    SYSTEM_CPU.set(cpu_usage)
    SYSTEM_MEMORY.set(memory_usage)
    QUEUE_SIZE.set(queue_size)
    
    return render_template_string(template,
                                cpu_usage=cpu_usage,
                                memory_usage=memory_usage,
                                queue_size=queue_size,
                                active_agents=active_agents,
                                timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                recent_tests=recent_tests)

@app.route('/api/metrics')
def api_metrics():
    return jsonify({
        'cpu_usage': psutil.cpu_percent(),
        'memory_usage': psutil.virtual_memory().percent,
        'queue_size': r.llen('test_queue') if r else 0,
        'timestamp': time.time()
    })

@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': time.time()})

if __name__ == '__main__':
    logger.info("Starting QA Framework monitoring dashboard...")
    app.run(host='0.0.0.0', port=8080, debug=False)
EOF
    
    chmod +x "$PROJECT_ROOT/automation/scripts/monitor.py"
    log "Monitoring dashboard created"
}

run_tests() {
    log "Running deployment tests..."
    
    # Test Python scripts
    if python3 -c "import sys; print('Python version:', sys.version)"; then
        log "Python environment: OK"
    else
        log "Python environment: FAILED"
        return 1
    fi
    
    # Test touch simulator
    if [ -f "$SCRIPT_DIR/touch_simulator.py" ]; then
        if python3 "$SCRIPT_DIR/touch_simulator.py" --help >/dev/null 2>&1; then
            log "Touch simulator: OK"
        else
            log "Touch simulator: FAILED"
        fi
    fi
    
    # Test network tester
    if [ -f "$SCRIPT_DIR/network_test.py" ]; then
        if python3 "$SCRIPT_DIR/network_test.py" --help >/dev/null 2>&1; then
            log "Network tester: OK"
        else
            log "Network tester: FAILED"
        fi
    fi
    
    log "Deployment tests completed"
}

main() {
    log "Starting QA Framework deployment..."
    
    # Check prerequisites
    check_prerequisites
    
    # Create configuration files
    create_requirements_file
    create_docker_compose
    create_dockerfiles
    create_kubernetes_manifests
    
    # Setup monitoring
    setup_monitoring
    
    # Create system services
    create_systemd_services
    
    # Run tests
    run_tests
    
    # Create startup script
    cat > "$PROJECT_ROOT/start-qa-framework.sh" << 'EOF'
#!/bin/bash
# QA Framework Startup Script

echo "Starting QA Framework..."

# Option 1: Docker Compose
if command -v docker-compose >/dev/null 2>&1; then
    echo "Starting with Docker Compose..."
    docker-compose -f docker-compose-qa.yml up -d
    echo "QA Framework started. Dashboard available at http://localhost:8080"
    exit 0
fi

# Option 2: Kubernetes
if command -v kubectl >/dev/null 2>&1; then
    echo "Starting with Kubernetes..."
    kubectl apply -f k8s/
    echo "QA Framework deployed to Kubernetes"
    exit 0
fi

# Option 3: Manual startup
echo "Starting manually..."
bash automation/scripts/autoscale.sh monitor &
python3 automation/scripts/monitor.py &
echo "QA Framework components started"
EOF
    
    chmod +x "$PROJECT_ROOT/start-qa-framework.sh"
    
    log "=== QA Framework Deployment Completed ==="
    log "Files created:"
    log "  - Docker Compose: docker-compose-qa.yml"
    log "  - Kubernetes manifests: k8s/"
    log "  - Startup script: start-qa-framework.sh"
    log "  - Requirements: requirements.txt"
    log ""
    log "To start the framework:"
    log "  ./start-qa-framework.sh"
    log ""
    log "Dashboard will be available at: http://localhost:8080"
    log "Metrics endpoint: http://localhost:8080/metrics"
    log ""
    log "For manual autoscaling: ./automation/scripts/autoscale.sh check"
}

main "$@"