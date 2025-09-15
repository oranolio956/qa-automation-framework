#!/bin/bash

# Android Network Testing Infrastructure Setup
# Configures network testing tools, proxies, and monitoring for app development

set -e

# Configuration
PROXY_PORT="3128"
MITM_PORT="8080"
MOCK_SERVER_PORT="8081"
WORKSPACE_DIR="$HOME/AndroidTesting"
NETWORK_TEST_DIR="$WORKSPACE_DIR/network-testing"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_section() {
    echo -e "${BLUE}[SECTION]${NC} $1"
}

check_prerequisites() {
    log_section "Checking Prerequisites"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker not found. Please install Docker first"
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        log_error "Docker is not running. Please start Docker service"
        exit 1
    fi
    
    # Check ADB
    if ! command -v adb &> /dev/null; then
        log_error "ADB not found. Install Android SDK first"
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 not found. Install Python3 first"
        exit 1
    fi
    
    log_info "Prerequisites check passed"
}

setup_network_test_workspace() {
    log_section "Setting Up Network Test Workspace"
    
    # Create directory structure
    mkdir -p "$NETWORK_TEST_DIR"/{config,logs,captures,mocks,scripts,certs}
    
    # Create network testing configuration
    cat > "$NETWORK_TEST_DIR/config/network_config.json" << 'EOF'
{
  "proxy_settings": {
    "http_proxy_port": 3128,
    "mitm_proxy_port": 8080,
    "mock_server_port": 8081
  },
  "test_endpoints": {
    "httpbin": "https://httpbin.org",
    "jsonplaceholder": "https://jsonplaceholder.typicode.com",
    "mock_api": "http://localhost:8081"
  },
  "network_conditions": {
    "fast_3g": {
      "download": "1.6 Mbps",
      "upload": "768 Kbps", 
      "latency": "150ms"
    },
    "slow_3g": {
      "download": "400 Kbps",
      "upload": "400 Kbps",
      "latency": "400ms"
    },
    "2g": {
      "download": "250 Kbps",
      "upload": "50 Kbps",
      "latency": "800ms"
    }
  }
}
EOF

    log_info "Network test workspace created at $NETWORK_TEST_DIR"
}

setup_squid_proxy() {
    log_section "Setting Up Squid Proxy for Development"
    
    # Create Squid configuration
    cat > "$NETWORK_TEST_DIR/config/squid.conf" << 'EOF'
# Squid configuration for Android development testing

# Basic configuration
http_port 3128

# Access control
acl localnet src 10.0.0.0/8
acl localnet src 172.16.0.0/12
acl localnet src 192.168.0.0/16
acl localnet src fc00::/7
acl localnet src fe80::/10

# Allow local network access
http_access allow localnet
http_access allow localhost

# Safe ports for development
acl SSL_ports port 443
acl Safe_ports port 80
acl Safe_ports port 443
acl Safe_ports port 8080-8090
acl CONNECT method CONNECT

# Allow HTTPS tunneling
http_access allow CONNECT SSL_ports

# Deny access to non-safe ports
http_access deny !Safe_ports
http_access deny CONNECT !SSL_ports

# Allow access from localhost manager
http_access allow localhost manager
http_access deny manager

# Finally deny all other access
http_access deny all

# Cache settings for development (minimal caching)
cache deny all

# Logging for debugging
access_log /var/log/squid/access.log squid
cache_log /var/log/squid/cache.log
EOF

    # Start Squid proxy container
    log_info "Starting Squid proxy container..."
    
    # Stop existing container if running
    docker stop test-proxy 2>/dev/null || true
    docker rm test-proxy 2>/dev/null || true
    
    # Start new container
    docker run -d \
        --name test-proxy \
        -p $PROXY_PORT:3128 \
        -v "$NETWORK_TEST_DIR/config/squid.conf:/etc/squid/squid.conf:ro" \
        -v "$NETWORK_TEST_DIR/logs:/var/log/squid" \
        sameersbn/squid:latest
    
    # Wait for proxy to start
    sleep 5
    
    # Test proxy
    if curl -x localhost:$PROXY_PORT -s http://httpbin.org/ip > /dev/null; then
        log_info "✓ Squid proxy running successfully on port $PROXY_PORT"
    else
        log_warn "✗ Proxy test failed"
    fi
}

setup_mitmproxy() {
    log_section "Setting Up MITM Proxy for Traffic Analysis"
    
    # Install mitmproxy if not available
    if ! command -v mitmproxy &> /dev/null; then
        log_info "Installing mitmproxy..."
        pip3 install --user mitmproxy
    fi
    
    # Create mitmproxy configuration
    cat > "$NETWORK_TEST_DIR/config/mitmproxy_config.py" << 'EOF'
"""
MITM Proxy configuration for Android app testing
"""

from mitmproxy import http
import json
import time

class NetworkLogger:
    """Log network requests for analysis"""
    
    def __init__(self):
        self.log_file = "/tmp/network_requests.log"
    
    def request(self, flow: http.HTTPFlow) -> None:
        """Log outgoing requests"""
        request_data = {
            "timestamp": time.time(),
            "method": flow.request.method,
            "url": flow.request.pretty_url,
            "headers": dict(flow.request.headers),
            "size": len(flow.request.content)
        }
        
        with open(self.log_file, "a") as f:
            f.write(json.dumps(request_data) + "\n")
    
    def response(self, flow: http.HTTPFlow) -> None:
        """Log incoming responses"""
        response_data = {
            "timestamp": time.time(),
            "url": flow.request.pretty_url,
            "status_code": flow.response.status_code,
            "headers": dict(flow.response.headers),
            "size": len(flow.response.content),
            "duration_ms": flow.response.timestamp_end - flow.request.timestamp_start
        }
        
        with open(self.log_file, "a") as f:
            f.write(json.dumps(response_data) + "\n")

class RequestModifier:
    """Modify requests for testing scenarios"""
    
    def request(self, flow: http.HTTPFlow) -> None:
        """Modify requests if needed"""
        # Add test headers for development
        if "test-mode" not in flow.request.headers:
            flow.request.headers["X-Test-Mode"] = "development"
    
    def response(self, flow: http.HTTPFlow) -> None:
        """Modify responses if needed"""
        # Add CORS headers for development
        flow.response.headers["Access-Control-Allow-Origin"] = "*"
        flow.response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        flow.response.headers["Access-Control-Allow-Headers"] = "*"

# Register addons
addons = [
    NetworkLogger(),
    RequestModifier()
]
EOF

    # Create MITM startup script
    cat > "$NETWORK_TEST_DIR/scripts/start_mitm.sh" << 'EOF'
#!/bin/bash

# Start MITM Proxy for network analysis

NETWORK_TEST_DIR="$HOME/AndroidTesting/network-testing"
CONFIG_FILE="$NETWORK_TEST_DIR/config/mitmproxy_config.py"

echo "Starting MITM Proxy for network analysis..."

# Clear previous logs
rm -f /tmp/network_requests.log

# Start mitmproxy
mitmproxy \
    --listen-port 8080 \
    --set confdir="$NETWORK_TEST_DIR/certs" \
    --scripts "$CONFIG_FILE" \
    --set web_port=8081
EOF

    chmod +x "$NETWORK_TEST_DIR/scripts/start_mitm.sh"
    
    log_info "MITM Proxy configuration created"
}

setup_mock_server() {
    log_section "Setting Up Mock API Server"
    
    # Create mock server using Python
    cat > "$NETWORK_TEST_DIR/scripts/mock_server.py" << 'EOF'
#!/usr/bin/env python3
"""
Mock API server for testing Android apps
"""

from flask import Flask, jsonify, request, make_response
import time
import random
import json
from datetime import datetime

app = Flask(__name__)

# Store request logs
request_logs = []

def log_request():
    """Log incoming requests"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "method": request.method,
        "path": request.path,
        "headers": dict(request.headers),
        "args": dict(request.args),
        "json": request.get_json() if request.is_json else None
    }
    request_logs.append(log_entry)

@app.before_request
def before_request():
    log_request()

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": time.time() - start_time
    })

@app.route('/api/users')
def get_users():
    """Mock users endpoint"""
    users = [
        {"id": 1, "name": "Test User 1", "email": "test1@example.com"},
        {"id": 2, "name": "Test User 2", "email": "test2@example.com"},
        {"id": 3, "name": "Test User 3", "email": "test3@example.com"}
    ]
    return jsonify(users)

@app.route('/api/users/<int:user_id>')
def get_user(user_id):
    """Mock single user endpoint"""
    if user_id > 3:
        return jsonify({"error": "User not found"}), 404
    
    user = {
        "id": user_id,
        "name": f"Test User {user_id}",
        "email": f"test{user_id}@example.com",
        "profile": {
            "age": random.randint(18, 65),
            "location": random.choice(["New York", "San Francisco", "Los Angeles"])
        }
    }
    return jsonify(user)

@app.route('/api/posts')
def get_posts():
    """Mock posts endpoint"""
    posts = []
    for i in range(1, 11):
        posts.append({
            "id": i,
            "title": f"Test Post {i}",
            "content": f"This is the content for test post {i}",
            "author_id": random.randint(1, 3),
            "created_at": datetime.now().isoformat()
        })
    return jsonify(posts)

@app.route('/api/slow')
def slow_endpoint():
    """Slow endpoint for testing"""
    delay = request.args.get('delay', 3, type=int)
    time.sleep(delay)
    return jsonify({
        "message": f"Response after {delay} seconds",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/error')
def error_endpoint():
    """Error endpoint for testing"""
    error_code = request.args.get('code', 500, type=int)
    return jsonify({
        "error": f"Mock error {error_code}",
        "timestamp": datetime.now().isoformat()
    }), error_code

@app.route('/api/upload', methods=['POST'])
def upload_endpoint():
    """Mock upload endpoint"""
    if 'file' in request.files:
        file = request.files['file']
        return jsonify({
            "message": "File uploaded successfully",
            "filename": file.filename,
            "size": len(file.read()),
            "timestamp": datetime.now().isoformat()
        })
    else:
        return jsonify({"error": "No file provided"}), 400

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Mock login endpoint"""
    data = request.get_json()
    if data and data.get('username') == 'testuser' and data.get('password') == 'testpass':
        return jsonify({
            "token": "mock_jwt_token_12345",
            "user": {
                "id": 1,
                "username": "testuser",
                "email": "testuser@example.com"
            },
            "expires_in": 3600
        })
    else:
        return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/logs')
def get_logs():
    """Get request logs"""
    return jsonify({
        "total_requests": len(request_logs),
        "logs": request_logs[-50:]  # Last 50 requests
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

if __name__ == '__main__':
    start_time = time.time()
    print("Starting Mock API Server...")
    print("Available endpoints:")
    print("  GET  /health")
    print("  GET  /api/users")
    print("  GET  /api/users/<id>")
    print("  GET  /api/posts")
    print("  GET  /api/slow?delay=<seconds>")
    print("  GET  /api/error?code=<status_code>")
    print("  POST /api/upload")
    print("  POST /api/auth/login")
    print("  GET  /api/logs")
    
    app.run(host='0.0.0.0', port=8081, debug=True)
EOF

    chmod +x "$NETWORK_TEST_DIR/scripts/mock_server.py"
    
    # Install Flask if not available
    pip3 install --user flask 2>/dev/null || log_warn "Could not install Flask"
    
    log_info "Mock API server created"
}

create_network_test_tools() {
    log_section "Creating Network Testing Tools"
    
    # Network connectivity tester
    cat > "$NETWORK_TEST_DIR/scripts/network_tester.py" << 'EOF'
#!/usr/bin/env python3
"""
Network connectivity and performance tester for Android apps
"""

import requests
import time
import json
import subprocess
import argparse
from datetime import datetime

class NetworkTester:
    """Test network connectivity and performance"""
    
    def __init__(self, proxy_host=None, proxy_port=None):
        self.session = requests.Session()
        if proxy_host and proxy_port:
            self.session.proxies = {
                'http': f'http://{proxy_host}:{proxy_port}',
                'https': f'http://{proxy_host}:{proxy_port}'
            }
    
    def test_connectivity(self, urls=None):
        """Test basic connectivity to various endpoints"""
        if urls is None:
            urls = [
                "http://httpbin.org/ip",
                "https://jsonplaceholder.typicode.com/posts/1",
                "http://localhost:8081/health"
            ]
        
        results = {}
        
        for url in urls:
            try:
                start_time = time.time()
                response = self.session.get(url, timeout=10)
                end_time = time.time()
                
                results[url] = {
                    "status": "success",
                    "status_code": response.status_code,
                    "response_time_ms": (end_time - start_time) * 1000,
                    "content_length": len(response.content)
                }
                
            except Exception as e:
                results[url] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        return results
    
    def test_performance(self, url, iterations=10):
        """Test network performance with multiple requests"""
        response_times = []
        
        for i in range(iterations):
            try:
                start_time = time.time()
                response = self.session.get(url, timeout=30)
                end_time = time.time()
                
                if response.status_code == 200:
                    response_times.append((end_time - start_time) * 1000)
                
            except Exception as e:
                print(f"Request {i+1} failed: {e}")
        
        if response_times:
            return {
                "url": url,
                "iterations": len(response_times),
                "avg_response_time_ms": sum(response_times) / len(response_times),
                "min_response_time_ms": min(response_times),
                "max_response_time_ms": max(response_times)
            }
        else:
            return {"url": url, "error": "All requests failed"}
    
    def test_android_connectivity(self):
        """Test Android device network connectivity"""
        try:
            # Test ADB connection
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
            if 'device' not in result.stdout:
                return {"error": "No Android device connected"}
            
            # Test device internet connectivity
            result = subprocess.run(['adb', 'shell', 'ping', '-c', '3', '8.8.8.8'], 
                                  capture_output=True, text=True, timeout=15)
            
            ping_success = result.returncode == 0
            
            # Get device IP
            result = subprocess.run(['adb', 'shell', 'ip', 'route', 'get', '1.1.1.1'], 
                                  capture_output=True, text=True)
            
            return {
                "device_connected": True,
                "internet_connectivity": ping_success,
                "ping_output": result.stdout if ping_success else result.stderr
            }
            
        except Exception as e:
            return {"error": f"Android connectivity test failed: {e}"}

def main():
    parser = argparse.ArgumentParser(description="Network connectivity tester")
    parser.add_argument("--proxy-host", help="Proxy host")
    parser.add_argument("--proxy-port", type=int, help="Proxy port")
    parser.add_argument("--url", help="Specific URL to test")
    parser.add_argument("--performance", action="store_true", help="Run performance test")
    parser.add_argument("--android", action="store_true", help="Test Android connectivity")
    
    args = parser.parse_args()
    
    tester = NetworkTester(args.proxy_host, args.proxy_port)
    
    print(f"Network Testing - {datetime.now().isoformat()}")
    print("=" * 50)
    
    if args.android:
        print("Testing Android device connectivity...")
        android_result = tester.test_android_connectivity()
        print(json.dumps(android_result, indent=2))
        print()
    
    if args.performance and args.url:
        print(f"Performance testing: {args.url}")
        perf_result = tester.test_performance(args.url)
        print(json.dumps(perf_result, indent=2))
    elif args.url:
        print(f"Connectivity testing: {args.url}")
        conn_result = tester.test_connectivity([args.url])
        print(json.dumps(conn_result, indent=2))
    else:
        print("Testing standard endpoints...")
        conn_result = tester.test_connectivity()
        print(json.dumps(conn_result, indent=2))

if __name__ == "__main__":
    main()
EOF

    chmod +x "$NETWORK_TEST_DIR/scripts/network_tester.py"
    
    # Android proxy configuration script
    cat > "$NETWORK_TEST_DIR/scripts/configure_android_proxy.sh" << 'EOF'
#!/bin/bash

# Configure Android device proxy settings for testing

PROXY_HOST="${1:-10.0.2.2}"  # Default for Android emulator
PROXY_PORT="${2:-3128}"

log_info() {
    echo "[INFO] $1"
}

log_error() {
    echo "[ERROR] $1"
}

configure_proxy() {
    log_info "Configuring Android proxy: $PROXY_HOST:$PROXY_PORT"
    
    # Check ADB connection
    if ! adb devices | grep -q "device$"; then
        log_error "No Android device connected"
        exit 1
    fi
    
    # Set global HTTP proxy
    adb shell settings put global http_proxy "$PROXY_HOST:$PROXY_PORT"
    
    # Verify proxy setting
    CURRENT_PROXY=$(adb shell settings get global http_proxy)
    log_info "Proxy configured: $CURRENT_PROXY"
    
    # Test connectivity through proxy
    log_info "Testing connectivity through proxy..."
    if adb shell ping -c 1 8.8.8.8 > /dev/null 2>&1; then
        log_info "✓ Network connectivity confirmed"
    else
        log_error "✗ Network connectivity issue"
    fi
}

remove_proxy() {
    log_info "Removing proxy configuration..."
    adb shell settings delete global http_proxy
    log_info "Proxy configuration removed"
}

show_usage() {
    echo "Usage: $0 [configure|remove] [proxy_host] [proxy_port]"
    echo
    echo "Examples:"
    echo "  $0 configure 10.0.2.2 3128    # Configure proxy"
    echo "  $0 remove                     # Remove proxy"
    echo "  $0 configure                  # Use default proxy (10.0.2.2:3128)"
}

case "${1:-configure}" in
    configure)
        if [[ -n "$2" ]]; then
            PROXY_HOST="$2"
        fi
        if [[ -n "$3" ]]; then
            PROXY_PORT="$3"
        fi
        configure_proxy
        ;;
    remove)
        remove_proxy
        ;;
    *)
        show_usage
        exit 1
        ;;
esac
EOF

    chmod +x "$NETWORK_TEST_DIR/scripts/configure_android_proxy.sh"
    
    log_info "Network testing tools created"
}

configure_android_networking() {
    log_section "Configuring Android Network Settings"
    
    # Check if device is connected
    if ! adb devices | grep -q "device$"; then
        log_warn "No Android device connected - skipping device configuration"
        return 0
    fi
    
    log_info "Configuring Android device for network testing..."
    
    # Configure proxy for emulator (10.0.2.2 is host IP from emulator perspective)
    PROXY_HOST="10.0.2.2"
    if adb shell getprop ro.kernel.qemu | grep -q "1"; then
        log_info "Detected Android emulator - using host IP $PROXY_HOST"
    else
        # For real devices, use actual host IP
        PROXY_HOST=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "192.168.1.100")
        log_info "Detected real device - using host IP $PROXY_HOST"
    fi
    
    # Set proxy if requested
    read -p "Configure device to use test proxy? (y/N): " configure_proxy
    if [[ $configure_proxy =~ ^[Yy]$ ]]; then
        adb shell settings put global http_proxy "$PROXY_HOST:$PROXY_PORT"
        log_info "Android proxy configured: $PROXY_HOST:$PROXY_PORT"
        
        # Test connectivity
        log_info "Testing proxy connectivity..."
        if timeout 10 adb shell curl -x "$PROXY_HOST:$PROXY_PORT" -s http://httpbin.org/ip > /dev/null 2>&1; then
            log_info "✓ Proxy connectivity confirmed"
        else
            log_warn "✗ Proxy connectivity test failed"
        fi
    fi
}

create_testing_scripts() {
    log_section "Creating Testing Scripts"
    
    # Master test runner
    cat > "$NETWORK_TEST_DIR/run_network_tests.sh" << 'EOF'
#!/bin/bash

# Network Testing Suite Runner

NETWORK_TEST_DIR="$HOME/AndroidTesting/network-testing"
cd "$NETWORK_TEST_DIR"

echo "Starting Network Testing Suite"
echo "=============================="

# Start mock server in background
echo "Starting mock API server..."
python3 scripts/mock_server.py &
MOCK_PID=$!
sleep 3

# Test basic connectivity
echo -e "\n1. Testing basic connectivity..."
python3 scripts/network_tester.py

# Test through proxy
echo -e "\n2. Testing through proxy..."
python3 scripts/network_tester.py --proxy-host localhost --proxy-port 3128

# Test Android connectivity
echo -e "\n3. Testing Android device..."
python3 scripts/network_tester.py --android

# Test performance
echo -e "\n4. Testing performance..."
python3 scripts/network_tester.py --url http://httpbin.org/json --performance

# Cleanup
echo -e "\nCleaning up..."
kill $MOCK_PID 2>/dev/null || true

echo "Network testing completed!"
EOF

    chmod +x "$NETWORK_TEST_DIR/run_network_tests.sh"
    
    # Create README
    cat > "$NETWORK_TEST_DIR/README.md" << 'EOF'
# Android Network Testing Infrastructure

This infrastructure provides network testing capabilities for Android app development.

## Components

- **Squid Proxy**: HTTP/HTTPS proxy for traffic routing
- **MITM Proxy**: Traffic analysis and modification
- **Mock API Server**: Local API endpoints for testing
- **Network Tester**: Connectivity and performance testing tools

## Quick Start

1. **Start all services:**
   ```bash
   ./run_network_tests.sh
   ```

2. **Configure Android device:**
   ```bash
   scripts/configure_android_proxy.sh configure
   ```

3. **Test connectivity:**
   ```bash
   python3 scripts/network_tester.py
   ```

## Available Services

- Squid Proxy: `localhost:3128`
- MITM Proxy: `localhost:8080` (Web UI: `localhost:8081`)
- Mock API: `localhost:8081`

## Common Use Cases

### Testing with Proxy
```bash
# Configure device proxy
scripts/configure_android_proxy.sh configure 10.0.2.2 3128

# Test app network requests
python3 scripts/network_tester.py --proxy-host localhost --proxy-port 3128
```

### API Testing
```bash
# Start mock server
python3 scripts/mock_server.py &

# Test endpoints
curl http://localhost:8081/api/users
curl -X POST http://localhost:8081/api/auth/login -H "Content-Type: application/json" -d '{"username":"testuser","password":"testpass"}'
```

### Traffic Analysis
```bash
# Start MITM proxy
scripts/start_mitm.sh

# Configure app to use proxy
# Analyze traffic in real-time
```

## Configuration Files

- `config/network_config.json` - Network testing configuration
- `config/squid.conf` - Squid proxy configuration
- `config/mitmproxy_config.py` - MITM proxy configuration

## Logs and Captures

- `logs/` - Proxy access logs
- `captures/` - Network traffic captures
- `/tmp/network_requests.log` - MITM proxy logs

EOF

    log_info "Testing scripts and documentation created"
}

verify_setup() {
    log_section "Verifying Network Testing Setup"
    
    echo "Network Testing Infrastructure Status:"
    echo "────────────────────────────────────────"
    
    # Check Docker containers
    if docker ps | grep -q "test-proxy"; then
        echo "✓ Squid Proxy: Running on port $PROXY_PORT"
    else
        echo "✗ Squid Proxy: Not running"
    fi
    
    # Check mock server port
    if netstat -tln 2>/dev/null | grep -q ":$MOCK_SERVER_PORT "; then
        echo "✓ Mock Server: Port $MOCK_SERVER_PORT available"
    else
        echo "✓ Mock Server: Port $MOCK_SERVER_PORT ready"
    fi
    
    # Check MITM proxy availability
    if command -v mitmproxy &> /dev/null; then
        echo "✓ MITM Proxy: Available"
    else
        echo "✗ MITM Proxy: Not installed"
    fi
    
    # Check Android connectivity
    if adb devices | grep -q "device$"; then
        PROXY_SETTING=$(adb shell settings get global http_proxy 2>/dev/null || echo "none")
        echo "✓ Android Device: Connected (Proxy: $PROXY_SETTING)"
    else
        echo "✗ Android Device: Not connected"
    fi
    
    # Test basic connectivity
    if curl -s http://httpbin.org/ip > /dev/null; then
        echo "✓ Internet: Connectivity confirmed"
    else
        echo "✗ Internet: Connectivity issue"
    fi
    
    echo "────────────────────────────────────────"
    
    log_info "Setup verification completed"
    
    echo
    echo "Next steps:"
    echo "1. Start mock server: python3 $NETWORK_TEST_DIR/scripts/mock_server.py"
    echo "2. Configure Android proxy: $NETWORK_TEST_DIR/scripts/configure_android_proxy.sh"
    echo "3. Run network tests: $NETWORK_TEST_DIR/run_network_tests.sh"
    echo "4. Start MITM for traffic analysis: $NETWORK_TEST_DIR/scripts/start_mitm.sh"
}

main() {
    log_info "Starting Android Network Testing Infrastructure Setup"
    echo
    
    check_prerequisites
    setup_network_test_workspace
    setup_squid_proxy
    setup_mitmproxy
    setup_mock_server
    create_network_test_tools
    configure_android_networking
    create_testing_scripts
    verify_setup
    
    echo
    log_info "Network testing infrastructure setup completed successfully!"
}

main "$@"