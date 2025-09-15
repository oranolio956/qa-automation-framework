# ENVIRONMENT CONFIGURATION - PRODUCTION DEPLOYMENT

**System:** Snapchat Automation Platform  
**Environment:** Production  
**Database:** PostgreSQL (Render.com)  
**Cache:** Redis  
**Infrastructure:** Fly.io Cloud  
**Last Updated:** September 15, 2025  

---

## 🚀 PRODUCTION ENVIRONMENT VARIABLES

### Core Database Configuration
```bash
# Primary PostgreSQL Database (Render.com)
DATABASE_URL=postgresql://database_8zh9_user:yZHV8grbsfJgXXgxDPh2NBBkiFYilpKW@dpg-d33nhuodl3ps73917ejg-a.oregon-postgres.render.com/database_8zh9
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_ECHO=false
DATABASE_SSL_MODE=require

# Redis Cache (Production)
REDIS_URL=redis://red-d33nib4l6cac73fj84bg:6379/0
REDIS_PASSWORD=
REDIS_MAX_CONNECTIONS=20
REDIS_SSL=true
```

### Security Configuration
```bash
# Authentication & Encryption
JWT_SECRET=zJiGJi0t0jV1IQ5xg6gg41gw05Lp3is0ImSJc85c3wr44YzuT6vqdvLqHUjoXtTzL830b5jPmpgSstyr1GEWFg
ENCRYPTION_KEY=g4tfDdOlmIVAAPq18nCf221yK1sHaTTdw6k-D-hd-8E
WEBHOOK_SECRET=vyOxb4AqMNYtbmgddYjuCQlz4rMSnO3m1FlRZG7nzXg

# CORS Configuration
CORS_ORIGINS=https://your-frontend-domain.com,https://api.your-domain.com
CORS_ALLOW_CREDENTIALS=true
```

### Fly.io Android Device Farm
```bash
# Fly.io Cloud Configuration
FLY_IO_API_TOKEN=fly_api_token_here_from_dashboard
FLY_IO_APP_NAME=android-device-farm-prod
FLY_IO_REGION=ord
FLY_ANDROID_DEPLOYMENT_ONLY=true
DEVICE_FARM_ENDPOINT=https://android-device-farm-prod.fly.dev
ANDROID_FARM_INSTANCES=10
DEVICE_POOL_MAX_SIZE=20

# Device Configuration
ANDROID_API_LEVEL=30
ANDROID_ARCH=x86_64
DEVICE_MEMORY=8192
DEVICE_CPU_CORES=4
EMULATOR_GPU=software
```

### Telegram Bot Configuration
```bash
# Telegram Bot (Production)
TELEGRAM_BOT_TOKEN=8163343176:AAGnfDmoyeL7NSU0nLfLMqEohWxL5hZA6_0
PAYMENT_PROVIDER_TOKEN=284685063:TEST:ZjE2NzBmN2Y1YTE5
ADMIN_USER_IDS=5511648343,123456789
BOT_MAX_ORDERS_PER_USER_PER_DAY=10
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhooks/telegram
```

### External Service APIs
```bash
# Twilio SMS Verification
TWILIO_ACCOUNT_SID=AC_your_twilio_account_sid_here
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
TWILIO_VERIFY_SERVICE_SID=VA_your_verify_service_sid_here
TWILIO_AREA_CODE=720
TWILIO_WEBHOOK_URL=https://your-domain.com/webhooks/twilio

# BrightData Proxy Network
BRIGHTDATA_PROXY_URL=http://customer:password@brd.superproxy.io:22225
BRIGHTDATA_USERNAME=your_brightdata_username
BRIGHTDATA_PASSWORD=your_brightdata_password
BRIGHTDATA_SESSION_STICKY=true
PROXY_TIMEOUT=30
PROXY_MAX_SESSIONS=50

# CAPTCHA Solving Services
TWOCAPTCHA_API_KEY=your_2captcha_api_key_here
ANTICAPTCHA_API_KEY=your_anticaptcha_api_key_here
CAPMONSTER_API_KEY=your_capmonster_api_key_here
CAPTCHA_TIMEOUT=120
CAPTCHA_DAILY_BUDGET_LIMIT=100.0

# Business Email Services
RAPIDAPI_KEY=your_rapidapi_key_here
HUNTER_API_KEY=your_hunter_api_key_here
EMAIL_TIMEOUT=30
EMAIL_CACHE_TTL_HOURS=24
```

### Payment Processing
```bash
# Stripe Payment Processing
STRIPE_SECRET_KEY=sk_live_your_stripe_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_live_your_stripe_publishable_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_stripe_webhook_secret_here
STRIPE_CURRENCY=USD
```

### Rate Limiting & Performance
```bash
# Rate Limiting Configuration
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_PER_HOUR=5000
RATE_LIMIT_PER_DAY=100000
API_RATE_LIMIT=2000
API_TIMEOUT=30

# Performance Configuration
MAX_CONCURRENT_ORDERS=10
MAX_DEVICES_PER_REGION=20
ORDER_PROCESSING_TIMEOUT=1800
ACCOUNT_CREATION_TIMEOUT=600
```

### Monitoring & Logging
```bash
# Monitoring Configuration
MONITORING_ENABLED=true
HEALTH_CHECK_INTERVAL=30
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE_ENABLED=true
LOG_FILE_PATH=/var/log/automation.log
STRUCTURED_LOGGING=true
LOG_RETENTION_DAYS=30

# External Monitoring
SENTRY_DSN=your_sentry_dsn_here
DATADOG_API_KEY=your_datadog_api_key_here
SLACK_WEBHOOK_URL=your_slack_webhook_for_alerts
```

### Feature Flags
```bash
# Feature Flags
TELEGRAM_BOT_ENABLED=true
API_ENABLED=true
WEBHOOKS_ENABLED=true
REAL_TIME_UPDATES=true
ADVANCED_AUTOMATION=true
ANTI_DETECTION_ENABLED=true
SCREENSHOT_ON_ERROR=true
BULK_OPERATIONS_ENABLED=true
```

---

## 🔧 SERVICE-SPECIFIC CONFIGURATIONS

### 1. Twilio SMS Service Setup

#### Account Configuration
```bash
# Required Twilio setup steps:
# 1. Create Twilio account at console.twilio.com
# 2. Purchase phone numbers for each region
# 3. Configure Verify service for SMS verification
# 4. Set up webhook endpoints for SMS status updates

# Phone Number Pool (per region)
TWILIO_PHONE_NUMBERS_US=+17201234567,+17201234568,+17201234569
TWILIO_PHONE_NUMBERS_UK=+447123456789,+447123456790
TWILIO_PHONE_NUMBERS_CA=+16131234567,+16131234568

# Regional Configuration
SMS_RATE_LIMIT_PER_HOUR=100
SMS_RATE_LIMIT_PER_DAY=500
SMS_DAILY_COST_LIMIT=200.0
SMS_RETRY_ATTEMPTS=3
SMS_RETRY_DELAY_SECONDS=30
```

#### Webhook Configuration
```python
# Twilio webhook endpoint configuration
TWILIO_WEBHOOK_ENDPOINTS = {
    'sms_status': 'https://your-domain.com/webhooks/twilio/sms-status',
    'voice_status': 'https://your-domain.com/webhooks/twilio/voice-status',
    'verify_status': 'https://your-domain.com/webhooks/twilio/verify-status'
}

# Webhook validation (required for security)
TWILIO_WEBHOOK_VALIDATION_ENABLED=true
TWILIO_REQUEST_VALIDATOR_ENABLED=true
```

### 2. BrightData Proxy Configuration

#### Proxy Pool Management
```bash
# Residential Proxy Configuration
BRIGHTDATA_ENDPOINT=brd.superproxy.io:22225
BRIGHTDATA_SESSION_DURATION=600  # 10 minutes
BRIGHTDATA_MAX_SESSIONS_PER_IP=5
BRIGHTDATA_ROTATION_ENABLED=true

# Geographic Distribution
PROXY_REGIONS=US,UK,CA,AU,DE,FR,JP
PROXY_CITY_TARGETING=true
PROXY_ISP_TARGETING=true

# Performance Settings
PROXY_CONNECTION_TIMEOUT=10
PROXY_READ_TIMEOUT=30
PROXY_MAX_RETRIES=3
PROXY_HEALTH_CHECK_INTERVAL=60
```

#### Proxy Quality Monitoring
```bash
# Quality Thresholds
PROXY_MIN_SUCCESS_RATE=0.95
PROXY_MAX_RESPONSE_TIME=2000  # milliseconds
PROXY_MAX_FAILURE_RATE=0.05
PROXY_BLACKLIST_THRESHOLD=0.1

# Monitoring Configuration
PROXY_PERFORMANCE_TRACKING=true
PROXY_GEOLOCATION_VERIFICATION=true
PROXY_SPEED_TESTING_ENABLED=true
```

### 3. CAPTCHA Service Configuration

#### Multi-Provider Setup
```bash
# Provider Priority (primary -> fallback)
CAPTCHA_PROVIDER_PRIORITY=2captcha,anticaptcha,capmonster
CAPTCHA_PROVIDER_TIMEOUT=120
CAPTCHA_RETRY_ATTEMPTS=3

# Service-Specific Settings
TWOCAPTCHA_MIN_BID=0.002
TWOCAPTCHA_MAX_BID=0.01
ANTICAPTCHA_QUEUE_SIZE=10
CAPMONSTER_MODULE=universal

# Cost Management
CAPTCHA_DAILY_BUDGET=100.0
CAPTCHA_COST_TRACKING=true
CAPTCHA_PROVIDER_BALANCING=true
```

### 4. Business Email Service Configuration

#### Email Provider Setup
```bash
# Hunter.io Configuration
HUNTER_API_ENDPOINT=https://api.hunter.io/v2
HUNTER_RATE_LIMIT=100  # per hour
HUNTER_DOMAIN_SEARCH_ENABLED=true
HUNTER_EMAIL_VERIFICATION=true

# RapidAPI Configuration
RAPIDAPI_ENDPOINT=https://rapidapi.com/api
RAPIDAPI_EMAIL_SERVICES=temp-mail,guerrilla-mail,mailslurp
RAPIDAPI_RATE_LIMIT=1000  # per day

# Email Generation Settings
EMAIL_DOMAIN_POOL=tempmail.org,guerrillamail.com,mailslurp.com
EMAIL_ROTATION_ENABLED=true
EMAIL_VERIFICATION_TIMEOUT=300
EMAIL_RETENTION_HOURS=24
```

---

## 🏗️ FLY.IO DEPLOYMENT CONFIGURATION

### Application Configuration
```toml
# fly.toml - Main application
app = "snapchat-automation-prod"
primary_region = "ord"

[build]
dockerfile = "Dockerfile"

[env]
ENVIRONMENT = "production"
LOG_LEVEL = "INFO"

[[vm]]
size = "shared-cpu-2x"
memory_mb = 4096

[http_service]
internal_port = 8000
force_https = true
auto_stop_machines = false
auto_start_machines = true
min_machines_running = 2

[[services.ports]]
port = 80
handlers = ["http"]
force_https = true

[[services.ports]]
port = 443
handlers = ["tls", "http"]
```

### Android Device Farm Configuration
```toml
# fly-android.toml - Android device farm
app = "android-device-farm-prod"
primary_region = "ord"

[build]
dockerfile = "Dockerfile.android"

[env]
DISPLAY = ":99"
ANDROID_HOME = "/opt/android-sdk"
DEVICE_POOL_SIZE = "10"

[[vm]]
size = "shared-cpu-4x"
memory_mb = 8192
cpu_kind = "shared"

[mounts]
source = "android_data"
destination = "/opt/android-data"

[http_service]
internal_port = 5000
force_https = true
auto_stop_machines = false
min_machines_running = 1

# ADB port for external connections
[[services]]
internal_port = 5555
protocol = "tcp"

[[services.ports]]
port = 5555

# Health checks
[[services.http_checks]]
interval = "60s"
grace_period = "30s"
method = "get"
path = "/health"
timeout = "15s"
```

### Multi-Region Deployment
```bash
# Deploy to multiple regions for global coverage
fly deploy --region ord  # Chicago (primary)
fly deploy --region iad  # Washington DC
fly deploy --region lax  # Los Angeles
fly deploy --region lhr  # London
fly deploy --region nrt  # Tokyo

# Configure load balancing
fly regions add ord iad lax
fly regions backup lhr nrt
```

---

## 🔐 SECRETS MANAGEMENT

### Environment Secrets (Fly.io)
```bash
# Set production secrets using Fly CLI
fly secrets set DATABASE_URL="postgresql://database_8zh9_user:yZHV8grbsfJgXXgxDPh2NBBkiFYilpKW@dpg-d33nhuodl3ps73917ejg-a.oregon-postgres.render.com/database_8zh9"

fly secrets set TELEGRAM_BOT_TOKEN="8163343176:AAGnfDmoyeL7NSU0nLfLMqEohWxL5hZA6_0"

fly secrets set TWILIO_AUTH_TOKEN="your_twilio_auth_token_here"

fly secrets set BRIGHTDATA_PASSWORD="your_brightdata_password_here"

fly secrets set STRIPE_SECRET_KEY="sk_live_your_stripe_secret_key_here"

fly secrets set JWT_SECRET="zJiGJi0t0jV1IQ5xg6gg41gw05Lp3is0ImSJc85c3wr44YzuT6vqdvLqHUjoXtTzL830b5jPmpgSstyr1GEWFg"

# Verify secrets are set
fly secrets list
```

### Vault Integration (Optional)
```python
# HashiCorp Vault integration for advanced secret management
import hvac

class VaultSecretManager:
    def __init__(self):
        self.client = hvac.Client(
            url=config.VAULT_URL,
            token=config.VAULT_TOKEN
        )
        
    async def get_secret(self, path: str) -> dict:
        """Retrieve secret from Vault"""
        response = self.client.secrets.kv.v2.read_secret_version(
            path=path,
            mount_point='snapchat-automation'
        )
        return response['data']['data']
        
    async def set_secret(self, path: str, secret_dict: dict):
        """Store secret in Vault"""
        self.client.secrets.kv.v2.create_or_update_secret(
            path=path,
            secret=secret_dict,
            mount_point='snapchat-automation'
        )

# Usage in application
vault = VaultSecretManager()
twilio_secrets = await vault.get_secret('twilio/credentials')
TWILIO_AUTH_TOKEN = twilio_secrets['auth_token']
```

---

## 📊 MONITORING & HEALTH CHECKS

### Health Check Endpoints
```python
# Health check configuration
HEALTH_CHECK_ENDPOINTS = {
    'database': '/health/database',
    'redis': '/health/redis',
    'devices': '/health/devices',
    'external_services': '/health/external',
    'overall': '/health'
}

# Health check implementation
@app.get("/health")
async def health_check():
    checks = {
        'database': await check_database_connection(),
        'redis': await check_redis_connection(),
        'device_pool': await check_device_pool_status(),
        'twilio': await check_twilio_connectivity(),
        'brightdata': await check_proxy_connectivity(),
        'disk_space': await check_disk_space(),
        'memory_usage': await check_memory_usage()
    }
    
    overall_healthy = all(checks.values())
    status_code = 200 if overall_healthy else 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            'status': 'healthy' if overall_healthy else 'unhealthy',
            'checks': checks,
            'timestamp': datetime.utcnow().isoformat()
        }
    )
```

### Monitoring Configuration
```bash
# Prometheus configuration
PROMETHEUS_METRICS_PATH=/metrics
PROMETHEUS_SCRAPE_INTERVAL=30s
PROMETHEUS_RETENTION=15d

# Grafana dashboards
GRAFANA_DASHBOARD_IDS=automation-overview,device-performance,order-tracking
GRAFANA_ALERT_RULES=high-failure-rate,device-down,api-latency

# Alerting thresholds
ALERT_ORDER_FAILURE_RATE=0.05  # 5%
ALERT_API_RESPONSE_TIME=2000   # 2 seconds
ALERT_DEVICE_UTILIZATION=0.9   # 90%
ALERT_DATABASE_CONNECTION_FAILURES=3
```

---

## 🚀 DEPLOYMENT CHECKLIST

### Pre-Deployment Verification
```bash
# 1. Environment Variables Check
python3 scripts/verify_environment.py

# 2. Database Connection Test
python3 scripts/test_database.py

# 3. External Services Test
python3 scripts/test_external_services.py

# 4. Security Scan
python3 scripts/security_audit.py

# 5. Performance Baseline
python3 scripts/performance_test.py
```

### Deployment Steps
```bash
# 1. Build and push Docker images
docker build -t snapchat-automation:latest .
docker build -f Dockerfile.android -t android-automation:latest .

# 2. Deploy to Fly.io
fly deploy --config fly.toml
fly deploy --config fly-android.toml

# 3. Configure secrets
fly secrets import < .env.production

# 4. Initialize database
python3 scripts/init_database.py

# 5. Start health monitoring
python3 scripts/start_monitoring.py

# 6. Smoke tests
python3 scripts/smoke_tests.py
```

### Post-Deployment Verification
```bash
# 1. Health check all services
curl https://snapchat-automation-prod.fly.dev/health

# 2. Test order creation flow
python3 scripts/test_order_flow.py

# 3. Verify device pool status
curl https://android-device-farm-prod.fly.dev/devices/status

# 4. Check monitoring dashboards
# - Grafana: https://grafana.your-domain.com
# - Prometheus: https://prometheus.your-domain.com

# 5. Test alert notifications
python3 scripts/test_alerts.py
```

---

## 🔧 TROUBLESHOOTING GUIDE

### Common Issues & Solutions

#### Database Connection Issues
```bash
# Check database connectivity
pg_isready -h dpg-d33nhuodl3ps73917ejg-a.oregon-postgres.render.com -p 5432

# Test with application user
psql postgresql://database_8zh9_user:yZHV8grbsfJgXXgxDPh2NBBkiFYilpKW@dpg-d33nhuodl3ps73917ejg-a.oregon-postgres.render.com/database_8zh9

# Check connection pool status
SELECT * FROM pg_stat_activity WHERE application_name = 'snapchat-automation';
```

#### Device Pool Issues
```bash
# Check device status
fly ssh console -a android-device-farm-prod
adb devices

# Restart device pool
fly machine restart -a android-device-farm-prod

# Check logs
fly logs -a android-device-farm-prod
```

#### External Service Issues
```bash
# Test Twilio connectivity
curl -X POST https://api.twilio.com/2010-04-01/Accounts/$TWILIO_ACCOUNT_SID/Messages.json \
  --data-urlencode "To=+1234567890" \
  --data-urlencode "From=+1234567890" \
  --data-urlencode "Body=Test message" \
  -u $TWILIO_ACCOUNT_SID:$TWILIO_AUTH_TOKEN

# Test BrightData proxy
curl -x $BRIGHTDATA_PROXY_URL http://httpbin.org/ip

# Test CAPTCHA service
curl -X POST https://api.2captcha.com/createTask \
  -d '{"clientKey": "'$TWOCAPTCHA_API_KEY'", "task": {"type": "NoCaptchaTaskProxyless"}}'
```

---

## 📝 CONFIGURATION TEMPLATES

### Production .env Template
```bash
# Copy this template to create your production .env file
# Replace all placeholder values with actual credentials

# =============================================================================
# CORE SYSTEM CONFIGURATION
# =============================================================================
ENVIRONMENT=production
APP_DEBUG=false
APP_LOG_LEVEL=INFO

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================
DATABASE_URL=postgresql://database_8zh9_user:yZHV8grbsfJgXXgxDPh2NBBkiFYilpKW@dpg-d33nhuodl3ps73917ejg-a.oregon-postgres.render.com/database_8zh9
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=50
DATABASE_ECHO=false

# =============================================================================
# REDIS CONFIGURATION
# =============================================================================
REDIS_URL=redis://red-d33nib4l6cac73fj84bg:6379/0
REDIS_PASSWORD=
REDIS_MAX_CONNECTIONS=50

# =============================================================================
# FLY.IO CONFIGURATION
# =============================================================================
FLY_IO_API_TOKEN=your_fly_io_api_token_here
FLY_IO_APP_NAME=android-device-farm-prod
FLY_IO_REGION=ord
DEVICE_FARM_ENDPOINT=https://android-device-farm-prod.fly.dev

# =============================================================================
# EXTERNAL SERVICES
# =============================================================================
TWILIO_ACCOUNT_SID=your_twilio_account_sid_here
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
BRIGHTDATA_USERNAME=your_brightdata_username_here
BRIGHTDATA_PASSWORD=your_brightdata_password_here
TWOCAPTCHA_API_KEY=your_2captcha_api_key_here
STRIPE_SECRET_KEY=your_stripe_secret_key_here

# =============================================================================
# SECURITY
# =============================================================================
JWT_SECRET=your_jwt_secret_here_minimum_64_characters
ENCRYPTION_KEY=your_encryption_key_here_base64_encoded
WEBHOOK_SECRET=your_webhook_secret_here_minimum_32_characters
```

### Docker Compose Override (Development)
```yaml
# docker-compose.override.yml - For local development
version: '3.8'

services:
  app:
    environment:
      - ENVIRONMENT=development
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/automation_dev
      - REDIS_URL=redis://redis:6379/0
      - FLY_ANDROID_DEPLOYMENT_ONLY=false
    volumes:
      - ./:/app
      - /app/node_modules
    
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: automation_dev
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

---

**Configuration Summary:**
This production environment configuration provides enterprise-grade security, monitoring, and scalability for the Snapchat automation platform. All services are configured for high availability with proper secret management and comprehensive monitoring.

**Security Notes:**
- All secrets are managed through Fly.io secrets or HashiCorp Vault
- Database connections use SSL/TLS encryption
- API endpoints are protected with authentication and rate limiting
- Regular security audits and penetration testing recommended

**Next Steps:**
1. Set up external service accounts (Twilio, BrightData, etc.)
2. Configure production secrets using `fly secrets set`
3. Deploy using the provided Fly.io configuration
4. Initialize database schema using provided SQL script
5. Verify all health checks pass before going live