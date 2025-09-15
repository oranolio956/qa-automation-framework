# Configuration Setup Guide

## Overview

This document provides a comprehensive guide for setting up and managing the Tinder Automation System configuration. The system includes secure credential management, environment-specific configurations, and comprehensive validation.

## 🚀 Quick Start

### 1. Initial Setup

```bash
# Run the automated setup
python3 setup_configuration.py

# Or validate existing configuration only
python3 setup_configuration.py --validate-only

# Non-interactive setup for CI/CD
python3 setup_configuration.py --non-interactive
```

### 2. Environment Configuration

The system uses a `.env` file for configuration. Copy and customize the template:

```bash
# Template is already created - just update with your values
cp .env.example .env
# Edit .env with your actual credentials
```

### 3. Validate Configuration

```bash
# Comprehensive validation
python3 -m automation.config.validation

# Quick health check
python3 -c "
from automation.config import health_check
import json
print(json.dumps(health_check(), indent=2))
"
```

## 🔧 Configuration Components

### 1. ConfigManager
- **Purpose**: Main configuration management with validation
- **Features**: Environment-specific settings, service configurations, health checks
- **Usage**: `from automation.config import get_config`

### 2. CredentialsManager  
- **Purpose**: Secure credential storage with encryption
- **Features**: Encrypted storage, credential rotation, audit logging
- **Usage**: `from automation.config import get_credentials`

### 3. EnvironmentConfig
- **Purpose**: Environment-specific configuration management
- **Features**: Development/staging/production settings, feature flags
- **Usage**: `from automation.config import get_env_config`

### 4. ConfigurationValidator
- **Purpose**: Comprehensive configuration validation
- **Features**: Security checks, service connectivity, format validation
- **Usage**: `from automation.config import validate_configuration`

## 📋 Configuration Categories

### Core Settings
```bash
# Environment
ENVIRONMENT=development
APP_DEBUG=true
APP_LOG_LEVEL=INFO

# Security (GENERATE SECURE VALUES!)
JWT_SECRET=<64+ character secure string>
ENCRYPTION_KEY=<32+ character secure string>
WEBHOOK_SECRET=<32+ character secure string>
```

### Database & Cache
```bash
# PostgreSQL
DATABASE_URL=postgresql://user:password@host:port/database
DATABASE_POOL_SIZE=10

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=20
```

### External Services
```bash
# Twilio SMS
TWILIO_ACCOUNT_SID=ACxxxxx...
TWILIO_AUTH_TOKEN=xxxxx...

# BrightData Proxy
BRIGHTDATA_PROXY_URL=http://user:pass@host:port

# CAPTCHA Services
TWOCAPTCHA_API_KEY=xxxxx...
ANTICAPTCHA_API_KEY=xxxxx...

# Business Email
RAPIDAPI_KEY=xxxxx...
HUNTER_API_KEY=xxxxx...
```

### Telegram Bot
```bash
# Bot Configuration
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMN...
PAYMENT_PROVIDER_TOKEN=xxxxx...
ADMIN_USER_IDS=123456789,987654321
```

## 🔒 Security Best Practices

### 1. Secret Generation
```bash
# Generate secure secrets
python3 -c "import secrets; print('JWT_SECRET=' + secrets.token_urlsafe(64))"
python3 -c "import secrets; print('ENCRYPTION_KEY=' + secrets.token_urlsafe(32))"
python3 -c "import secrets; print('WEBHOOK_SECRET=' + secrets.token_urlsafe(32))"
```

### 2. Credential Storage
- **Development**: Use `.env` file (never commit to git)
- **Production**: Use environment variables or secret management service
- **Encryption**: Enable credential encryption with master password

### 3. Access Control
```bash
# Set proper file permissions
chmod 600 .env
chmod 600 automation/config/credentials.enc
```

## 🧪 Testing & Validation

### Validation Levels

1. **Format Validation**: Check configuration format and syntax
2. **Security Validation**: Verify secrets are secure and properly set
3. **Service Validation**: Test connectivity to external services
4. **Integration Validation**: End-to-end configuration testing

### Running Tests
```bash
# Full validation suite
python3 setup_configuration.py --validate-only

# Specific validation categories
python3 -c "
from automation.config.validation import ConfigurationValidator
validator = ConfigurationValidator('development')
report = validator.validate_all()
"

# Health check
python3 -c "
from automation.config import health_check
status = health_check()
print('Healthy:', status['healthy'])
"
```

## 🛠️ Troubleshooting

### Common Issues

1. **Environment Variables Not Loaded**
   ```bash
   # Install python-dotenv
   pip install python-dotenv
   
   # Verify .env file exists and has correct format
   python3 -c "
   from dotenv import load_dotenv
   import os
   load_dotenv()
   print('JWT_SECRET loaded:', bool(os.getenv('JWT_SECRET')))
   "
   ```

2. **Database Connection Failed**
   ```bash
   # Check database URL format
   echo $DATABASE_URL
   # Should be: postgresql://user:password@host:port/database
   
   # Test connection
   python3 -c "
   from automation.config import get_config
   config = get_config()
   db_config = config.get_database_config()
   print('Database URL:', db_config.url)
   "
   ```

3. **Redis Connection Failed**
   ```bash
   # Check Redis service
   redis-cli ping
   
   # Test configuration
   python3 -c "
   import redis
   import os
   r = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
   print('Redis ping:', r.ping())
   "
   ```

4. **Service Authentication Failed**
   - **Twilio**: Verify Account SID and Auth Token in Twilio Console
   - **BrightData**: Check proxy URL format and credentials
   - **CAPTCHA**: Verify API keys are active and have sufficient balance

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with verbose output
python3 setup_configuration.py --validate-only
```

## 📊 Configuration Validation Report

The system generates detailed validation reports:

```json
{
  "timestamp": "2025-09-14T14:05:40",
  "environment": "development",
  "overall_status": "warnings",
  "summary": {
    "valid": 31,
    "warning": 1,
    "error": 0
  },
  "results": [
    {
      "category": "security",
      "name": "JWT_SECRET", 
      "status": "valid",
      "message": "JWT secret configured (86 chars)"
    }
  ]
}
```

### Status Levels
- **✅ Valid**: Configuration is correct and functional
- **⚠️ Warning**: Configuration works but needs attention
- **❌ Error**: Configuration is broken and needs fixing
- **🚨 Critical**: Security-critical issue requiring immediate attention

## 🔄 Maintenance

### Regular Tasks

1. **Credential Rotation** (Monthly)
   ```bash
   # Generate new secrets
   python3 -c "
   from automation.config import get_credentials
   creds = get_credentials()
   creds.rotate_credential('twilio_auth_token', 'new_token_here')
   "
   ```

2. **Health Monitoring** (Daily)
   ```bash
   # Automated health check
   python3 -c "
   from automation.config import health_check
   import sys
   status = health_check()
   sys.exit(0 if status['healthy'] else 1)
   "
   ```

3. **Configuration Backup** (Weekly)
   ```bash
   # Export configuration template
   python3 -c "
   from automation.config import export_env_template
   with open('config_backup.env', 'w') as f:
       f.write(export_env_template())
   "
   ```

### Monitoring Integration
```bash
# Add to crontab for monitoring
0 */6 * * * /usr/bin/python3 /path/to/setup_configuration.py --validate-only || echo "Config validation failed" | mail -s "Config Alert" admin@domain.com
```

## 🚀 Production Deployment

### Pre-Deployment Checklist
- [ ] All credentials are set and valid
- [ ] Security secrets are 32+ characters
- [ ] Database connections tested
- [ ] External service connectivity verified
- [ ] Rate limits configured appropriately
- [ ] Monitoring and alerting enabled
- [ ] Backup procedures in place

### Environment-Specific Settings
```bash
# Development
ENVIRONMENT=development
APP_DEBUG=true

# Staging  
ENVIRONMENT=staging
APP_DEBUG=false

# Production
ENVIRONMENT=production
APP_DEBUG=false
REQUIRE_2FA=true
```

## 📚 API Reference

### Configuration Manager
```python
from automation.config import get_config

config = get_config()

# Get specific configurations
db_config = config.get_database_config()
redis_config = config.get_redis_config()
twilio_config = config.get_twilio_config()
security_config = config.get_security_config()

# Validation and health checks
validation = config.validate_configuration()
health = config.health_check()
```

### Credentials Manager
```python
from automation.config import get_credentials

creds = get_credentials(master_password="optional")

# Set credentials
creds.set_credential('api_key', 'secret_value', encrypt=True)

# Get credentials  
api_key = creds.get_credential('api_key')

# Service-specific helpers
twilio_creds = creds.get_twilio_credentials()
proxy_creds = creds.get_brightdata_credentials()
```

### Validation
```python
from automation.config import validate_configuration

# Quick validation
result = validate_configuration('development')
print(f"Valid: {result['valid']}")
print(f"Errors: {len(result['errors'])}")

# Detailed validation
from automation.config.validation import ConfigurationValidator
validator = ConfigurationValidator('production')
report = validator.validate_all()
```

## 🆘 Getting Help

### Support Resources
- **Documentation**: Check this file and inline code comments
- **Validation**: Run `python3 setup_configuration.py --validate-only`
- **Health Check**: Run `python3 -c "from automation.config import health_check; print(health_check())"`
- **Logs**: Check `setup_configuration.log` for detailed error information

### Common Commands
```bash
# Setup and validation
python3 setup_configuration.py
python3 setup_configuration.py --validate-only
python3 -m automation.config.validation

# Testing components
python3 -m automation.config.config_manager
python3 -m automation.config.credentials_manager  
python3 -m automation.config.environment_config

# Export templates
python3 -c "from automation.config import export_env_template; print(export_env_template())" > .env.new
```

---

**Security Notice**: Never commit `.env` files or credential files to version control. Use `.env.example` for templates only.