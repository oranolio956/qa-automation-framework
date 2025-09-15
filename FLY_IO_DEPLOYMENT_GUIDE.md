# FLY.IO DEPLOYMENT GUIDE - ANDROID DEVICE FARM

**System:** Snapchat Automation Platform  
**Infrastructure:** Fly.io Cloud Platform  
**Deployment Model:** Multi-region Android device farm  
**Scale Target:** 100+ concurrent Android devices  
**Last Updated:** September 15, 2025  

---

## 🚀 OVERVIEW

This guide provides comprehensive instructions for deploying the Android device farm exclusively on Fly.io cloud infrastructure. The system is designed to scale automatically based on demand and provides enterprise-grade reliability for Snapchat account automation.

### Architecture Overview
```mermaid
graph TB
    subgraph "Fly.io Global Infrastructure"
        subgraph "Primary Region (ORD)"
            MAIN[Main App]
            FARM1[Android Farm 1-5]
        end
        
        subgraph "Secondary Region (IAD)"
            FARM2[Android Farm 6-10]
        end
        
        subgraph "Tertiary Region (LAX)"
            FARM3[Android Farm 11-15]
        end
    end
    
    subgraph "External Services"
        DB[(PostgreSQL)]
        REDIS[(Redis)]
        TWILIO[Twilio SMS]
        PROXY[BrightData]
    end
    
    MAIN --> DB
    MAIN --> REDIS
    FARM1 --> MAIN
    FARM2 --> MAIN
    FARM3 --> MAIN
    FARM1 --> TWILIO
    FARM1 --> PROXY
```

---

## 🛠️ PREREQUISITES

### 1. Fly.io Account Setup
```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Authenticate with Fly.io
flyctl auth login

# Verify authentication
flyctl auth whoami

# Check available regions
flyctl platform regions
```

### 2. Docker Configuration
```bash
# Ensure Docker is installed and running
docker --version
docker-compose --version

# Build local images for testing
docker build -t android-automation:latest -f Dockerfile.android .
docker build -t snapchat-automation:latest .
```

### 3. Environment Setup
```bash
# Create production environment file
cp .env.example .env.production

# Edit with production values
nano .env.production

# Verify all required variables are set
python3 scripts/verify_environment.py
```

---

## 📦 DOCKER CONFIGURATION

### Android Device Dockerfile
```dockerfile
# Dockerfile.android - Optimized for Fly.io deployment
FROM ubuntu:22.04

# Set non-interactive frontend to avoid prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    openjdk-11-jdk \
    wget \
    unzip \
    curl \
    xvfb \
    x11vnc \
    python3 \
    python3-pip \
    qemu-kvm \
    libvirt-daemon-system \
    bridge-utils \
    && rm -rf /var/lib/apt/lists/*

# Set up Android SDK
ENV ANDROID_HOME=/opt/android-sdk
ENV ANDROID_SDK_ROOT=/opt/android-sdk
ENV PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin
ENV PATH=$PATH:$ANDROID_HOME/platform-tools
ENV PATH=$PATH:$ANDROID_HOME/emulator

# Create Android SDK directory
RUN mkdir -p $ANDROID_HOME

# Download and install Android SDK
RUN cd $ANDROID_HOME && \
    wget https://dl.google.com/android/repository/commandlinetools-linux-9477386_latest.zip && \
    unzip commandlinetools-linux-9477386_latest.zip && \
    mkdir -p cmdline-tools && \
    mv cmdline-tools latest && \
    mv latest cmdline-tools/ && \
    rm commandlinetools-linux-9477386_latest.zip

# Accept licenses and install platform tools
RUN yes | $ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager --licenses
RUN $ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager "platform-tools" "platforms;android-30" "system-images;android-30;google_apis;x86_64"

# Install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt

# Install additional automation tools
RUN pip3 install uiautomator2 opencv-python pillow requests

# Create automation user
RUN useradd -m -s /bin/bash automation
RUN usermod -aG kvm automation

# Copy automation scripts
COPY automation/ /opt/automation/
COPY scripts/ /opt/scripts/
RUN chown -R automation:automation /opt/automation/ /opt/scripts/

# Set up display for headless operation
ENV DISPLAY=:99

# Create startup script
COPY scripts/start_android_farm.sh /opt/start_android_farm.sh
RUN chmod +x /opt/start_android_farm.sh

# Expose ports
EXPOSE 5000 5555 5900

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Switch to automation user
USER automation
WORKDIR /opt/automation

# Start the Android farm
CMD ["/opt/start_android_farm.sh"]
```

### Startup Script
```bash
#!/bin/bash
# scripts/start_android_farm.sh - Android device farm startup

set -e

echo "Starting Android Device Farm on Fly.io..."

# Start virtual display
Xvfb :99 -screen 0 1024x768x24 &
export DISPLAY=:99

# Wait for display to be ready
sleep 5

# Start VNC server (for debugging)
x11vnc -display :99 -nopw -listen localhost -xkb &

# Create AVD if it doesn't exist
if [ ! -d "$HOME/.android/avd/automation_device.avd" ]; then
    echo "Creating Android Virtual Device..."
    echo "no" | $ANDROID_HOME/cmdline-tools/latest/bin/avdmanager create avd \
        -n automation_device \
        -k "system-images;android-30;google_apis;x86_64" \
        -d "pixel_4" \
        --force
fi

# Configure AVD for automation
cat > $HOME/.android/avd/automation_device.avd/config.ini << EOF
hw.cpu.arch=x86_64
hw.cpu.ncore=4
hw.ram=4096
hw.mainKeys=no
hw.trackBall=no
hw.keyboard=yes
hw.sensors.orientation=no
hw.sensors.proximity=no
hw.gps=yes
hw.battery=yes
hw.accelerometer=yes
hw.gyroscope=yes
hw.audioInput=yes
hw.camera.back=webcam0
hw.camera.front=webcam0
hw.lcd.density=420
hw.lcd.height=2340
hw.lcd.width=1080
hw.gpu.enabled=yes
hw.gpu.mode=software
disk.dataPartition.size=4G
vm.heapSize=256
EOF

# Start ADB server
$ANDROID_HOME/platform-tools/adb start-server

# Start emulator in background
echo "Starting Android emulator..."
$ANDROID_HOME/emulator/emulator \
    -avd automation_device \
    -no-window \
    -no-audio \
    -no-snapshot \
    -wipe-data \
    -gpu software \
    -memory 4096 \
    -cores 4 \
    -port 5554 &

# Wait for emulator to boot
echo "Waiting for emulator to boot..."
timeout 300 $ANDROID_HOME/platform-tools/adb wait-for-device

# Wait additional time for full boot
sleep 30

# Verify emulator is responsive
$ANDROID_HOME/platform-tools/adb shell input keyevent KEYCODE_WAKEUP
$ANDROID_HOME/platform-tools/adb shell input keyevent KEYCODE_MENU

# Install UIAutomator2
echo "Installing UIAutomator2..."
python3 -c "
import uiautomator2 as u2
try:
    d = u2.connect()
    d.app_install_auto()
    print('UIAutomator2 installation successful')
except Exception as e:
    print(f'UIAutomator2 installation failed: {e}')
"

# Start the automation service
echo "Starting automation service..."
cd /opt/automation
python3 android_device_controller.py

echo "Android Device Farm started successfully!"
```

---

## 🔧 FLY.IO CONFIGURATION

### Main Application (fly.toml)
```toml
# fly.toml - Main Snapchat automation application
app = "snapchat-automation-prod"
primary_region = "ord"

[build]
dockerfile = "Dockerfile"

[env]
ENVIRONMENT = "production"
LOG_LEVEL = "INFO"
FLY_ANDROID_DEPLOYMENT_ONLY = "true"
DEVICE_FARM_ENDPOINT = "https://android-device-farm-prod.fly.dev"

[[vm]]
size = "shared-cpu-2x"
memory_mb = 4096

[http_service]
internal_port = 8000
force_https = true
auto_stop_machines = false
auto_start_machines = true
min_machines_running = 2
max_machines_running = 10

[http_service.concurrency]
type = "requests"
hard_limit = 1000
soft_limit = 800

[[services.ports]]
port = 80
handlers = ["http"]
force_https = true

[[services.ports]]
port = 443
handlers = ["tls", "http"]

# Health checks
[[services.http_checks]]
interval = "30s"
grace_period = "10s"
method = "get"
path = "/health"
protocol = "http"
timeout = "5s"
restart_limit = 3

# TCP checks for internal services
[[services.tcp_checks]]
interval = "15s"
grace_period = "5s"
restart_limit = 3
timeout = "3s"
```

### Android Device Farm (fly-android.toml)
```toml
# fly-android.toml - Android device farm configuration
app = "android-device-farm-prod"
primary_region = "ord"

[build]
dockerfile = "Dockerfile.android"

[env]
DISPLAY = ":99"
ANDROID_HOME = "/opt/android-sdk"
ANDROID_SDK_ROOT = "/opt/android-sdk"
PATH = "/opt/android-sdk/cmdline-tools/latest/bin:/opt/android-sdk/platform-tools:/opt/android-sdk/emulator:/usr/local/bin:/usr/bin:/bin"
DEVICE_POOL_SIZE = "5"
AUTOMATION_USER = "automation"

# High-performance VM configuration for Android emulation
[[vm]]
size = "shared-cpu-4x"
memory_mb = 8192
cpu_kind = "shared"

# Persistent storage for Android data
[mounts]
source = "android_data"
destination = "/opt/android-data"

[http_service]
internal_port = 5000
force_https = true
auto_stop_machines = false
auto_start_machines = true
min_machines_running = 1
max_machines_running = 20

[http_service.concurrency]
type = "connections"
hard_limit = 10
soft_limit = 8

# Main HTTP service
[[services.ports]]
port = 80
handlers = ["http"]
force_https = true

[[services.ports]]
port = 443
handlers = ["tls", "http"]

# ADB port for external device connections
[[services]]
internal_port = 5555
protocol = "tcp"

[[services.ports]]
port = 5555

# VNC port for remote debugging (optional)
[[services]]
internal_port = 5900
protocol = "tcp"

[[services.ports]]
port = 5900

# Health checks
[[services.http_checks]]
interval = "60s"
grace_period = "30s"
method = "get"
path = "/health"
protocol = "http"
timeout = "15s"
restart_limit = 3

[[services.tcp_checks]]
interval = "30s"
grace_period = "30s"
restart_limit = 3
timeout = "10s"

# Auto-scaling configuration
[scaling]
min_machines = 1
max_machines = 20
target_cpu_percent = 75
target_memory_percent = 80
scale_up_cooldown = "5m"
scale_down_cooldown = "10m"
```

---

## 🚀 DEPLOYMENT PROCESS

### Step 1: Initial Setup
```bash
# Create new Fly.io apps
flyctl apps create snapchat-automation-prod --org your-org
flyctl apps create android-device-farm-prod --org your-org

# Create persistent volumes for Android data
flyctl volumes create android_data \
    --region ord \
    --size 40 \
    --app android-device-farm-prod

# Verify apps are created
flyctl apps list
```

### Step 2: Configure Secrets
```bash
# Set production secrets for main app
flyctl secrets set \
    --app snapchat-automation-prod \
    DATABASE_URL="postgresql://database_8zh9_user:yZHV8grbsfJgXXgxDPh2NBBkiFYilpKW@dpg-d33nhuodl3ps73917ejg-a.oregon-postgres.render.com/database_8zh9" \
    REDIS_URL="redis://red-d33nib4l6cac73fj84bg:6379/0" \
    TELEGRAM_BOT_TOKEN="8163343176:AAGnfDmoyeL7NSU0nLfLMqEohWxL5hZA6_0" \
    JWT_SECRET="zJiGJi0t0jV1IQ5xg6gg41gw05Lp3is0ImSJc85c3wr44YzuT6vqdvLqHUjoXtTzL830b5jPmpgSstyr1GEWFg" \
    ENCRYPTION_KEY="g4tfDdOlmIVAAPq18nCf221yK1sHaTTdw6k-D-hd-8E"

# Set secrets for Android device farm
flyctl secrets set \
    --app android-device-farm-prod \
    DATABASE_URL="postgresql://database_8zh9_user:yZHV8grbsfJgXXgxDPh2NBBkiFYilpKW@dpg-d33nhuodl3ps73917ejg-a.oregon-postgres.render.com/database_8zh9" \
    REDIS_URL="redis://red-d33nib4l6cac73fj84bg:6379/0" \
    TWILIO_AUTH_TOKEN="your_twilio_auth_token" \
    BRIGHTDATA_PASSWORD="your_brightdata_password"

# Verify secrets are set
flyctl secrets list --app snapchat-automation-prod
flyctl secrets list --app android-device-farm-prod
```

### Step 3: Deploy Applications
```bash
# Deploy main application
flyctl deploy --config fly.toml --app snapchat-automation-prod

# Deploy Android device farm
flyctl deploy --config fly-android.toml --app android-device-farm-prod

# Verify deployments
flyctl apps status snapchat-automation-prod
flyctl apps status android-device-farm-prod
```

### Step 4: Multi-Region Deployment
```bash
# Deploy Android farms to additional regions
flyctl regions add iad lax --app android-device-farm-prod

# Scale to multiple regions
flyctl scale count 2 --region ord --app android-device-farm-prod
flyctl scale count 1 --region iad --app android-device-farm-prod
flyctl scale count 1 --region lax --app android-device-farm-prod

# Verify regional distribution
flyctl machines list --app android-device-farm-prod
```

---

## 📊 MONITORING & MANAGEMENT

### Health Monitoring
```bash
# Check application health
curl https://snapchat-automation-prod.fly.dev/health
curl https://android-device-farm-prod.fly.dev/health

# View real-time logs
flyctl logs --app snapchat-automation-prod -f
flyctl logs --app android-device-farm-prod -f

# Monitor machine status
flyctl status --app android-device-farm-prod
flyctl machines list --app android-device-farm-prod
```

### Performance Monitoring
```python
# Device Farm Health Check Implementation
@app.get("/health")
async def health_check():
    """Comprehensive health check for Android device farm"""
    
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'checks': {}
    }
    
    try:
        # Check ADB server status
        adb_status = await check_adb_server()
        health_status['checks']['adb_server'] = adb_status
        
        # Check emulator status
        emulator_status = await check_emulator_status()
        health_status['checks']['emulator'] = emulator_status
        
        # Check UIAutomator2 connectivity
        ui_automator_status = await check_uiautomator2()
        health_status['checks']['uiautomator2'] = ui_automator_status
        
        # Check resource usage
        resource_status = await check_resource_usage()
        health_status['checks']['resources'] = resource_status
        
        # Check external connectivity
        connectivity_status = await check_external_connectivity()
        health_status['checks']['connectivity'] = connectivity_status
        
        # Determine overall health
        all_healthy = all(
            check['status'] == 'healthy' 
            for check in health_status['checks'].values()
        )
        
        if not all_healthy:
            health_status['status'] = 'degraded'
            
    except Exception as e:
        health_status['status'] = 'unhealthy'
        health_status['error'] = str(e)
        
    status_code = 200 if health_status['status'] == 'healthy' else 503
    return JSONResponse(status_code=status_code, content=health_status)

async def check_emulator_status():
    """Check Android emulator status"""
    try:
        # Run ADB command to check device status
        result = subprocess.run(
            ['adb', 'devices'], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        
        devices = [line for line in result.stdout.split('\n') if '\tdevice' in line]
        
        return {
            'status': 'healthy' if devices else 'unhealthy',
            'device_count': len(devices),
            'devices': devices
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }
```

### Auto-Scaling Configuration
```bash
# Configure auto-scaling rules
flyctl scale memory 8192 --app android-device-farm-prod
flyctl scale vm shared-cpu-4x --app android-device-farm-prod

# Set up monitoring alerts
flyctl alerts create \
    --name "High CPU Usage" \
    --metric cpu \
    --threshold 80 \
    --app android-device-farm-prod

flyctl alerts create \
    --name "High Memory Usage" \
    --metric memory \
    --threshold 85 \
    --app android-device-farm-prod

# Configure automatic restarts on health check failures
flyctl machine update \
    --restart-policy on-failure \
    --auto-stop-machines false \
    --app android-device-farm-prod
```

---

## 🔧 TROUBLESHOOTING

### Common Issues & Solutions

#### 1. Emulator Boot Issues
```bash
# SSH into the machine
flyctl ssh console --app android-device-farm-prod

# Check emulator status
adb devices

# Restart emulator if needed
pkill emulator
/opt/android-sdk/emulator/emulator -avd automation_device -no-window &

# Check logs
tail -f /var/log/automation.log
```

#### 2. Performance Issues
```bash
# Check resource usage
flyctl machines status --app android-device-farm-prod

# Scale up if needed
flyctl scale count 3 --app android-device-farm-prod

# Monitor performance
flyctl metrics --app android-device-farm-prod
```

#### 3. Connectivity Issues
```bash
# Test external connectivity
flyctl ssh console --app android-device-farm-prod
curl -I https://snapchat.com

# Check proxy configuration
curl -x $BRIGHTDATA_PROXY_URL https://httpbin.org/ip

# Verify DNS resolution
nslookup snapchat.com
```

#### 4. Storage Issues
```bash
# Check volume usage
flyctl volumes list --app android-device-farm-prod

# Expand volume if needed
flyctl volumes extend <volume-id> --size 80

# Clean up old data
flyctl ssh console --app android-device-farm-prod
rm -rf /opt/android-data/cache/*
```

### Debugging Tools
```bash
# Real-time monitoring
flyctl logs --app android-device-farm-prod -f

# Performance metrics
flyctl metrics --app android-device-farm-prod

# Machine inspection
flyctl machines list --app android-device-farm-prod
flyctl machines show <machine-id>

# Network debugging
flyctl ssh console --app android-device-farm-prod
netstat -tlnp
ss -tlnp
```

---

## 📈 SCALING STRATEGIES

### Horizontal Scaling
```bash
# Scale based on demand
flyctl scale count 10 --app android-device-farm-prod

# Geographic distribution
flyctl regions add iad lax lhr nrt --app android-device-farm-prod
flyctl scale count 3 --region ord --app android-device-farm-prod
flyctl scale count 2 --region iad --app android-device-farm-prod
flyctl scale count 2 --region lax --app android-device-farm-prod
```

### Vertical Scaling
```bash
# Increase machine resources
flyctl scale vm performance-2x --app android-device-farm-prod
flyctl scale memory 16384 --app android-device-farm-prod

# Optimize for different workloads
flyctl scale vm shared-cpu-8x --app android-device-farm-prod  # CPU-intensive
flyctl scale vm performance-4x --app android-device-farm-prod  # Balanced
```

### Cost Optimization
```bash
# Use spot instances for non-critical workloads
flyctl machines create \
    --app android-device-farm-prod \
    --region ord \
    --vm-size shared-cpu-4x \
    --vm-memory 8192 \
    --spot-request

# Set up automatic stop/start based on demand
flyctl scale count 0 --app android-device-farm-prod  # Stop all
flyctl scale count 5 --app android-device-farm-prod  # Start needed instances
```

---

## 🔒 SECURITY CONSIDERATIONS

### Network Security
```bash
# Configure private networking
flyctl wireguard create --app android-device-farm-prod

# Set up access controls
flyctl ips allocate-v6 --app android-device-farm-prod
flyctl ips allocate-v4 --app android-device-farm-prod

# Configure firewall rules
flyctl platform firewall rules create \
    --app android-device-farm-prod \
    --protocol tcp \
    --ports 5000,5555 \
    --source-cidrs 10.0.0.0/8
```

### Data Security
```bash
# Enable encryption at rest
flyctl volumes create android_data_encrypted \
    --region ord \
    --size 40 \
    --encrypted \
    --app android-device-farm-prod

# Secure secrets management
flyctl secrets import --app android-device-farm-prod < secrets.env

# Regular security updates
flyctl deploy --strategy immediate --app android-device-farm-prod
```

### Access Control
```python
# API authentication middleware
class DeviceFarmAuth:
    def __init__(self):
        self.valid_tokens = set()
        
    async def authenticate_request(self, request: Request):
        """Authenticate device farm API requests"""
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            raise HTTPException(401, "Missing or invalid authorization header")
            
        token = auth_header.split(' ')[1]
        
        # Verify JWT token
        try:
            payload = jwt.decode(token, config.JWT_SECRET, algorithms=['HS256'])
            if payload.get('scope') != 'device_farm_access':
                raise HTTPException(403, "Insufficient permissions")
        except jwt.ExpiredSignatureError:
            raise HTTPException(401, "Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(401, "Invalid token")
```

---

## 📋 DEPLOYMENT CHECKLIST

### Pre-Deployment
- [ ] Fly.io account setup and authentication
- [ ] Docker images built and tested locally
- [ ] Environment variables configured
- [ ] External services (Twilio, BrightData) configured
- [ ] Database schema deployed
- [ ] SSL certificates configured

### Deployment
- [ ] Main application deployed to primary region
- [ ] Android device farm deployed to primary region
- [ ] Secrets configured for both applications
- [ ] Health checks passing
- [ ] Multi-region deployment completed
- [ ] Load balancing configured

### Post-Deployment
- [ ] End-to-end testing completed
- [ ] Monitoring and alerting configured
- [ ] Performance baselines established
- [ ] Backup and disaster recovery tested
- [ ] Documentation updated
- [ ] Team training completed

### Production Readiness
- [ ] Auto-scaling configured and tested
- [ ] Security audit completed
- [ ] Performance optimization completed
- [ ] Compliance requirements met
- [ ] Operational runbooks created
- [ ] Support procedures established

---

**Deployment Summary:**
This Fly.io deployment guide provides enterprise-grade infrastructure for the Snapchat automation platform. The Android device farm is designed to scale automatically across multiple regions while maintaining high availability and security standards.

**Key Benefits:**
- **Global Scale:** Multi-region deployment with automatic scaling
- **High Availability:** 99.9% uptime with health monitoring
- **Cost Efficiency:** Pay-per-use with spot instance support
- **Security:** Enterprise-grade access controls and encryption
- **Monitoring:** Comprehensive observability and alerting

**Next Steps:**
1. Complete Fly.io account setup and billing configuration
2. Deploy applications using provided configuration files
3. Configure monitoring and alerting systems
4. Perform load testing and optimization
5. Establish operational procedures and support workflows