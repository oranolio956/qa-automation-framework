# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This is a sophisticated social media automation platform primarily focused on Snapchat and Tinder account creation and management. The system uses Android emulation, anti-detection techniques, SMS verification, and proxy networks to create accounts at scale.

## Technology Stack

- **Language**: Python 3.11+ (primary), TypeScript (frontend components)
- **Core Frameworks**: FastAPI (backend API), Flask (billing service), python-telegram-bot (bot interface)
- **Infrastructure**: Docker, Fly.io deployment, PostgreSQL, Redis
- **Mobile Automation**: UIAutomator2, Android emulators, ADB
- **Key Dependencies**: Selenium, OpenCV, Twilio (SMS), various proxy services

## Common Development Commands

### Environment Setup
```bash
# Set up environment variables and dependencies
./automation/setup_environment.sh
source .env

# Install Python dependencies
pip3 install -r requirements.txt

# Set up Telegram bot specifically
./setup_bot.sh
```

### Testing Commands
```bash
# Run comprehensive system tests
python3 automation/SYSTEM_IMPLEMENTATION_TEST.py

# Test specific components
python3 test_automation_system.py
python3 test_snapchat_verification.py
python3 test_database_connection.py
python3 comprehensive_system_test.py

# Run individual component tests
python3 test_android_automation_fixes.py
python3 test_missing_implementations.py
python3 test_real_time_progress.py

# Performance and load testing
python3 advanced_load_test.py
python3 comprehensive_performance_test.py
python3 network_performance_test.py

# Run single test modules
python3 -m pytest automation/tests/test_account_creation.py
python3 -m pytest automation/tests/test_anti_detection.py
```

### Infrastructure and Deployment
```bash
# Docker operations
docker-compose up -d
docker-compose -f infra/docker-compose.yml up

# Fly.io deployment
flyctl deploy
flyctl status
./deploy_android_farm.sh

# Infrastructure provisioning
./infra/deploy.sh
./infra/start-monitoring.sh
```

### Bot and Service Management
```bash
# Start Telegram bot services
./start_bot_services.sh

# Run main orchestrator
python3 automation/main_orchestrator.py

# Start backend services
cd backend && python3 app.py

# SMS infrastructure
./infra/start-sms-infrastructure.sh
python3 utils/test_sms_verifier.py
```

### Development and Validation
```bash
# Validate system components
python3 final_system_validation.py
python3 component_specific_validation.py
python3 infrastructure_validation.py

# Run automation validation
./automation-validation.sh
./advanced-testing-environment.sh
```

## Architecture Overview

### Core Components Architecture

The system follows a microservices architecture with several key modules:

1. **Automation Engine** (`automation/`):
   - `main_orchestrator.py`: Central coordination system for all automation tasks
   - `android/`: Android device and emulator management
   - `snapchat/`: Snapchat-specific account creation logic
   - `core/`: Anti-detection, API endpoints, database integration
   - `telegram_bot/`: Complete Telegram bot interface with order management

2. **Backend Services** (`backend/`):
   - `app.py`: FastAPI-based order and billing pipeline
   - Handles payment processing, order management, customer billing
   - JWT authentication, rate limiting, Redis caching

3. **Infrastructure** (`infra/`):
   - Cloud deployment configurations (Fly.io)
   - Monitoring, security, database provisioning
   - Worker management and scaling

4. **Utilities** (`utils/`):
   - `sms_verifier.py`: SMS verification system with Twilio integration
   - `brightdata_proxy.py`: Proxy management and rotation
   - Various helper modules for validation and testing

### Key Architectural Patterns

- **Orchestrator Pattern**: `main_orchestrator.py` coordinates all automation tasks
- **Anti-Detection System**: Sophisticated fingerprint spoofing and behavioral mimicry
- **Microservices**: Backend API, billing service, bot service run independently
- **Event-Driven**: Webhook-based communication between services
- **Pool Management**: Emulator pools, SMS number pools, proxy rotation
- **Retry Logic**: Extensive error handling with exponential backoff

### Data Flow

1. **Order Creation**: Telegram bot → Backend API → Database
2. **Account Creation**: Orchestrator → Android emulator → Snapchat/Tinder APIs
3. **Verification**: SMS verifier → Twilio → Account confirmation
4. **Delivery**: Export system → Customer notification → Account handoff

## Development Workflow

### Working with Android Automation
- Emulators are managed via `android/emulator_manager.py`
- UIAutomator2 handles device interaction through `android/ui_automator_manager.py`
- Touch patterns are generated to mimic human behavior

### Anti-Detection Development
- All automation includes fingerprint spoofing and behavioral randomization
- Proxy rotation is mandatory for all external requests
- Device characteristics are randomized per session

### Database Integration
- PostgreSQL schema defined in `DATABASE_SCHEMA.sql`
- All database operations go through `automation/core/database_integration.py`
- Redis used for caching and session management

### Testing Strategy
- Comprehensive test suite covering all major components
- Load testing capabilities for performance validation
- Integration tests verify end-to-end workflows
- Mock services available for development

## Environment Configuration

### Required Environment Variables
```bash
# Database
DATABASE_URL=postgresql://username:password@localhost:5432/tinder_automation
REDIS_URL=redis://localhost:6379

# SMS Services (Critical)
TWILIO_ACCOUNT_SID=your_twilio_account_sid_here
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
TWILIO_AREA_CODE=720

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Security
JWT_SECRET=your_jwt_secret_here
SECRET_KEY=your_secret_key_for_encryption_here

# Proxy Services
SMARTPROXY_ENDPOINT=your_proxy_endpoint_here
SMARTPROXY_USERNAME=your_proxy_username_here
SMARTPROXY_PASSWORD=your_proxy_password_here

# Fly.io Deployment
FLY_API_TOKEN=your_fly_api_token_here
```

### Development vs Production
- Use `.env.template` as starting point for configuration
- Development mode enables debug logging and test accounts
- Production requires all security tokens and external service credentials

## Security Considerations

- Never commit actual `.env` files with real credentials
- All external API calls use proxy rotation for anonymity
- Anti-detection measures are critical for platform compliance
- SMS verification pools require careful management to avoid blacklisting
- Rate limiting prevents abuse and maintains service stability

## Troubleshooting

### Common Issues
1. **Emulator startup failures**: Check Android SDK path and available system resources
2. **SMS verification timeouts**: Verify Twilio credentials and number pool status
3. **Proxy connection issues**: Test proxy endpoints and rotation logic
4. **Database connection errors**: Ensure PostgreSQL is running and credentials are correct
5. **Anti-detection failures**: Update user agents and device fingerprints regularly

### Debug Commands
```bash
# Check system status
python3 final_system_validation.py

# Test individual components
python3 demonstrate_working_vs_missing.py

# Validate configuration
python3 automation/config/validation.py

# Check logs
tail -f logs/snapchat_automation.log
```

This platform represents a complex automation system requiring careful attention to security, anti-detection measures, and service reliability. Always test changes thoroughly in the development environment before deploying to production.