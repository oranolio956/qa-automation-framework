#!/usr/bin/env python3
"""
Configuration Validation System
Comprehensive validation for all configuration settings with detailed reporting
"""

import os
import sys
import json
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse
import secrets

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Single validation result"""
    category: str
    name: str
    status: str  # 'valid', 'warning', 'error', 'missing'
    message: str
    suggestion: Optional[str] = None
    critical: bool = False

@dataclass
class ValidationReport:
    """Complete validation report"""
    timestamp: datetime
    environment: str
    overall_status: str  # 'valid', 'warnings', 'errors'
    results: List[ValidationResult] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)

class ConfigurationValidator:
    """Comprehensive configuration validator"""
    
    def __init__(self, environment: str = 'development'):
        # Load environment variables from .env file if available
        self._load_env_file()
        
        self.environment = environment
        self.results = []
    
    def _load_env_file(self):
        """Load environment variables from .env file if available"""
        try:
            from dotenv import load_dotenv
            from pathlib import Path
            
            # Try to find .env file in common locations
            possible_env_files = [
                Path.cwd() / '.env',
                Path(__file__).parent.parent.parent / '.env',
                Path.home() / '.env'
            ]
            
            for env_file in possible_env_files:
                if env_file.exists():
                    load_dotenv(env_file)
                    logger.debug(f"Loaded environment variables from {env_file}")
                    break
        except ImportError:
            logger.debug("python-dotenv not available, skipping .env file loading")
        except Exception as e:
            logger.debug(f"Failed to load .env file: {e}")
        
        # Security patterns for validation
        self.security_patterns = {
            'twilio_sid': r'^AC[a-f0-9]{32}$',
            'jwt_token': r'^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$',
            'api_key': r'^[a-zA-Z0-9_-]{16,}$',
            'webhook_secret': r'^[a-zA-Z0-9_-]{32,}$',
            'database_url': r'^postgresql://[^:]+:[^@]+@[^:]+:\d+/[^/]+$',
            'redis_url': r'^redis://([^:]+:[^@]+@)?[^:]+:\d+(/\d+)?$',
            'proxy_url': r'^https?://[^:]+:[^@]+@[^:]+:\d+$'
        }
        
        # Required environment variables by category
        self.required_vars = {
            'database': ['DATABASE_URL'],
            'redis': ['REDIS_URL'],
            'security': ['JWT_SECRET', 'ENCRYPTION_KEY', 'WEBHOOK_SECRET'],
            'twilio': ['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN'],
            'proxy': ['BRIGHTDATA_PROXY_URL'],
            'captcha': [],  # At least one captcha service
            'monitoring': []  # Optional in development
        }
        
        # Critical settings for production
        self.production_critical = [
            'JWT_SECRET', 'ENCRYPTION_KEY', 'DATABASE_URL', 
            'REDIS_URL', 'WEBHOOK_SECRET'
        ]
    
    def validate_all(self) -> ValidationReport:
        """Run comprehensive validation on all configuration"""
        logger.info(f"🔍 Starting configuration validation for {self.environment}")
        
        self.results.clear()
        
        # Run all validation categories
        self._validate_environment_setup()
        self._validate_security_configuration()
        self._validate_database_configuration()
        self._validate_redis_configuration()
        self._validate_twilio_configuration()
        self._validate_proxy_configuration()
        self._validate_captcha_configuration()
        self._validate_business_email_configuration()
        self._validate_webhook_configuration()
        self._validate_rate_limiting_configuration()
        self._validate_monitoring_configuration()
        self._validate_telegram_bot_configuration()
        
        # Generate report
        report = self._generate_report()
        self._display_report(report)
        
        return report
    
    def _add_result(self, category: str, name: str, status: str, 
                   message: str, suggestion: str = None, critical: bool = False):
        """Add validation result"""
        result = ValidationResult(
            category=category,
            name=name,
            status=status,
            message=message,
            suggestion=suggestion,
            critical=critical
        )
        self.results.append(result)
    
    def _validate_environment_setup(self):
        """Validate basic environment setup"""
        # Check environment type
        env = os.getenv('ENVIRONMENT', 'development')
        if env not in ['development', 'staging', 'production', 'testing', 'local']:
            self._add_result('environment', 'ENVIRONMENT', 'warning',
                           f'Unknown environment: {env}',
                           'Use: development, staging, production, testing, or local')
        else:
            self._add_result('environment', 'ENVIRONMENT', 'valid',
                           f'Environment set to {env}')
        
        # Check Python version
        python_version = sys.version_info
        if python_version < (3, 8):
            self._add_result('environment', 'python_version', 'error',
                           f'Python {python_version.major}.{python_version.minor} is too old',
                           'Upgrade to Python 3.8 or higher', critical=True)
        else:
            self._add_result('environment', 'python_version', 'valid',
                           f'Python {python_version.major}.{python_version.minor} is supported')
    
    def _validate_security_configuration(self):
        """Validate security settings"""
        # JWT Secret
        jwt_secret = os.getenv('JWT_SECRET')
        if not jwt_secret:
            self._add_result('security', 'JWT_SECRET', 'error',
                           'JWT secret is not set', 
                           'Generate secure secret: python -c "import secrets; print(secrets.token_urlsafe(64))"',
                           critical=True)
        elif len(jwt_secret) < 32:
            self._add_result('security', 'JWT_SECRET', 'warning',
                           'JWT secret is too short (< 32 chars)',
                           'Use at least 32 characters for security')
        elif jwt_secret.startswith('your-') or jwt_secret == 'changeme':
            self._add_result('security', 'JWT_SECRET', 'error',
                           'JWT secret is using default placeholder value',
                           'Set a secure secret value', critical=True)
        else:
            self._add_result('security', 'JWT_SECRET', 'valid',
                           f'JWT secret configured ({len(jwt_secret)} chars)')
        
        # Encryption Key
        enc_key = os.getenv('ENCRYPTION_KEY')
        if not enc_key:
            self._add_result('security', 'ENCRYPTION_KEY', 'error',
                           'Encryption key is not set',
                           'Generate secure key: python -c "import secrets; print(secrets.token_urlsafe(32))"',
                           critical=True)
        elif len(enc_key) < 32:
            self._add_result('security', 'ENCRYPTION_KEY', 'warning',
                           'Encryption key is too short (< 32 chars)',
                           'Use at least 32 characters for security')
        elif enc_key.startswith('your-') or enc_key == 'changeme':
            self._add_result('security', 'ENCRYPTION_KEY', 'error',
                           'Encryption key is using default placeholder',
                           'Set a secure key value', critical=True)
        else:
            self._add_result('security', 'ENCRYPTION_KEY', 'valid',
                           f'Encryption key configured ({len(enc_key)} chars)')
        
        # Webhook Secret
        webhook_secret = os.getenv('WEBHOOK_SECRET')
        if not webhook_secret:
            self._add_result('security', 'WEBHOOK_SECRET', 'warning',
                           'Webhook secret is not set',
                           'Generate secure secret for webhook validation')
        elif len(webhook_secret) < 32:
            self._add_result('security', 'WEBHOOK_SECRET', 'warning',
                           'Webhook secret is too short (< 32 chars)',
                           'Use at least 32 characters')
        else:
            self._add_result('security', 'WEBHOOK_SECRET', 'valid',
                           f'Webhook secret configured ({len(webhook_secret)} chars)')
        
        # CORS Origins
        cors_origins = os.getenv('CORS_ORIGINS', '')
        if not cors_origins and self.environment == 'production':
            self._add_result('security', 'CORS_ORIGINS', 'warning',
                           'CORS origins not configured for production',
                           'Set allowed origins for security')
        elif cors_origins:
            origins = [origin.strip() for origin in cors_origins.split(',')]
            if '*' in origins and self.environment == 'production':
                self._add_result('security', 'CORS_ORIGINS', 'error',
                               'Wildcard CORS origin in production is insecure',
                               'Specify exact allowed origins', critical=True)
            else:
                self._add_result('security', 'CORS_ORIGINS', 'valid',
                               f'CORS origins configured ({len(origins)} origins)')
    
    def _validate_database_configuration(self):
        """Validate database configuration"""
        db_url = os.getenv('DATABASE_URL')
        
        if not db_url:
            self._add_result('database', 'DATABASE_URL', 'error',
                           'Database URL is not set',
                           'Set PostgreSQL connection string', critical=True)
            return
        
        # Validate URL format
        if not re.match(self.security_patterns['database_url'], db_url):
            self._add_result('database', 'DATABASE_URL', 'error',
                           'Invalid database URL format',
                           'Use format: postgresql://user:pass@host:port/database',
                           critical=True)
            return
        
        # Parse URL for additional validation
        try:
            parsed = urlparse(db_url)
            
            # Check for default/weak credentials
            if 'password' in parsed.password or 'changeme' in parsed.password:
                self._add_result('database', 'DATABASE_URL', 'error',
                               'Database using default/weak password',
                               'Set strong database password', critical=True)
            
            # Production-specific checks
            if self.environment == 'production':
                if parsed.hostname == 'localhost' or parsed.hostname == '127.0.0.1':
                    self._add_result('database', 'DATABASE_URL', 'warning',
                                   'Production using localhost database',
                                   'Use external database service for production')
            
            self._add_result('database', 'DATABASE_URL', 'valid',
                           f'Database configured ({parsed.hostname}:{parsed.port})')
            
        except Exception as e:
            self._add_result('database', 'DATABASE_URL', 'error',
                           f'Error parsing database URL: {str(e)}',
                           'Check database URL format', critical=True)
        
        # Validate pool settings
        pool_size = os.getenv('DATABASE_POOL_SIZE', '10')
        try:
            pool_size_int = int(pool_size)
            if pool_size_int < 5:
                self._add_result('database', 'DATABASE_POOL_SIZE', 'warning',
                               'Database pool size is very small',
                               'Consider increasing for better performance')
            elif pool_size_int > 50:
                self._add_result('database', 'DATABASE_POOL_SIZE', 'warning',
                               'Database pool size is very large',
                               'Monitor connection usage and adjust as needed')
            else:
                self._add_result('database', 'DATABASE_POOL_SIZE', 'valid',
                               f'Pool size set to {pool_size_int}')
        except ValueError:
            self._add_result('database', 'DATABASE_POOL_SIZE', 'error',
                           'Invalid pool size value',
                           'Set numeric value for DATABASE_POOL_SIZE')
    
    def _validate_redis_configuration(self):
        """Validate Redis configuration"""
        redis_url = os.getenv('REDIS_URL')
        
        if not redis_url:
            self._add_result('redis', 'REDIS_URL', 'error',
                           'Redis URL is not set',
                           'Set Redis connection string', critical=True)
            return
        
        # Validate URL format
        if not re.match(self.security_patterns['redis_url'], redis_url):
            self._add_result('redis', 'REDIS_URL', 'error',
                           'Invalid Redis URL format',
                           'Use format: redis://[password@]host:port[/database]')
            return
        
        # Test Redis connection if possible
        try:
            import redis
            redis_client = redis.from_url(redis_url, socket_timeout=2, decode_responses=True)
            redis_client.ping()
            self._add_result('redis', 'REDIS_URL', 'valid',
                           'Redis connection successful')
        except ImportError:
            self._add_result('redis', 'REDIS_URL', 'warning',
                           'Redis package not installed',
                           'Install with: pip install redis')
        except Exception as e:
            self._add_result('redis', 'REDIS_URL', 'warning',
                           f'Redis connection failed: {str(e)}',
                           'Check Redis server status and credentials')
        
        # Validate Redis password
        redis_password = os.getenv('REDIS_PASSWORD')
        if self.environment == 'production' and not redis_password:
            self._add_result('redis', 'REDIS_PASSWORD', 'warning',
                           'No Redis password set for production',
                           'Set Redis password for security')
    
    def _validate_twilio_configuration(self):
        """Validate Twilio configuration"""
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        
        if not account_sid and not auth_token:
            self._add_result('twilio', 'credentials', 'warning',
                           'Twilio credentials not configured',
                           'SMS functionality will be disabled')
            return
        
        # Validate Account SID format
        if account_sid:
            if not re.match(self.security_patterns['twilio_sid'], account_sid):
                self._add_result('twilio', 'TWILIO_ACCOUNT_SID', 'error',
                               'Invalid Twilio Account SID format',
                               'SID should start with "AC" and be 34 characters long')
            else:
                self._add_result('twilio', 'TWILIO_ACCOUNT_SID', 'valid',
                               'Account SID format is valid')
        else:
            self._add_result('twilio', 'TWILIO_ACCOUNT_SID', 'error',
                           'Twilio Account SID is not set',
                           'Get from Twilio Console')
        
        # Validate Auth Token
        if auth_token:
            if len(auth_token) < 32:
                self._add_result('twilio', 'TWILIO_AUTH_TOKEN', 'error',
                               'Twilio Auth Token is too short',
                               'Check token from Twilio Console')
            elif auth_token.startswith('your-') or auth_token == 'changeme':
                self._add_result('twilio', 'TWILIO_AUTH_TOKEN', 'error',
                               'Twilio Auth Token is placeholder value',
                               'Set actual token from Twilio Console')
            else:
                self._add_result('twilio', 'TWILIO_AUTH_TOKEN', 'valid',
                               f'Auth Token configured ({len(auth_token)} chars)')
        else:
            self._add_result('twilio', 'TWILIO_AUTH_TOKEN', 'error',
                           'Twilio Auth Token is not set',
                           'Get from Twilio Console')
        
        # Test Twilio credentials if both are present
        if account_sid and auth_token and re.match(self.security_patterns['twilio_sid'], account_sid):
            try:
                from twilio.rest import Client
                client = Client(account_sid, auth_token)
                account = client.api.accounts(account_sid).fetch()
                
                self._add_result('twilio', 'connection', 'valid',
                               f'Twilio connection successful (Account: {account.friendly_name})')
                
                if account.status != 'active':
                    self._add_result('twilio', 'account_status', 'warning',
                                   f'Account status: {account.status}',
                                   'Check account standing in Twilio Console')
                
            except ImportError:
                self._add_result('twilio', 'connection', 'warning',
                               'Twilio package not installed',
                               'Install with: pip install twilio')
            except Exception as e:
                self._add_result('twilio', 'connection', 'error',
                               f'Twilio connection failed: {str(e)}',
                               'Check credentials and account status')
        
        # Validate area code
        area_code = os.getenv('TWILIO_AREA_CODE', '720')
        if not area_code.isdigit() or len(area_code) != 3:
            self._add_result('twilio', 'TWILIO_AREA_CODE', 'warning',
                           'Invalid area code format',
                           'Use 3-digit area code (e.g., 720)')
    
    def _validate_proxy_configuration(self):
        """Validate proxy configuration"""
        proxy_url = os.getenv('BRIGHTDATA_PROXY_URL')
        
        if not proxy_url:
            self._add_result('proxy', 'BRIGHTDATA_PROXY_URL', 'warning',
                           'BrightData proxy not configured',
                           'Proxy functionality will be disabled')
            return
        
        # Validate proxy URL format
        if not re.match(self.security_patterns['proxy_url'], proxy_url):
            self._add_result('proxy', 'BRIGHTDATA_PROXY_URL', 'error',
                           'Invalid proxy URL format',
                           'Use format: http://username:password@host:port')
            return
        
        # Validate separate credentials if provided
        username = os.getenv('BRIGHTDATA_USERNAME')
        password = os.getenv('BRIGHTDATA_PASSWORD')
        
        if username and password:
            self._add_result('proxy', 'brightdata_credentials', 'valid',
                           'BrightData credentials configured')
        
        # Test proxy if possible (basic connectivity)
        try:
            import requests
            response = requests.get('http://httpbin.org/ip', 
                                  proxies={'http': proxy_url, 'https': proxy_url},
                                  timeout=10)
            if response.status_code == 200:
                self._add_result('proxy', 'connection', 'valid',
                               'Proxy connection test successful')
            else:
                self._add_result('proxy', 'connection', 'warning',
                               f'Proxy test returned status {response.status_code}',
                               'Check proxy credentials and configuration')
        except ImportError:
            self._add_result('proxy', 'connection', 'warning',
                           'Requests package not installed',
                           'Install with: pip install requests')
        except Exception as e:
            self._add_result('proxy', 'connection', 'warning',
                           f'Proxy connection test failed: {str(e)}',
                           'Check proxy URL and credentials')
    
    def _validate_captcha_configuration(self):
        """Validate CAPTCHA solving services"""
        captcha_services = [
            ('twocaptcha', 'TWOCAPTCHA_API_KEY'),
            ('anticaptcha', 'ANTICAPTCHA_API_KEY'),
            ('capmonster', 'CAPMONSTER_API_KEY')
        ]
        
        configured_services = []
        
        for service_name, env_var in captcha_services:
            api_key = os.getenv(env_var)
            if api_key and not api_key.startswith('your-'):
                configured_services.append(service_name)
                self._add_result('captcha', env_var, 'valid',
                               f'{service_name} API key configured')
            elif api_key and api_key.startswith('your-'):
                self._add_result('captcha', env_var, 'error',
                               f'{service_name} API key is placeholder value',
                               'Set actual API key from service')
        
        if not configured_services:
            self._add_result('captcha', 'services', 'warning',
                           'No CAPTCHA solving services configured',
                           'Configure at least one service for CAPTCHA handling')
        else:
            self._add_result('captcha', 'services', 'valid',
                           f'{len(configured_services)} CAPTCHA service(s) configured: {", ".join(configured_services)}')
        
        # Validate budget limit
        budget_limit = os.getenv('CAPTCHA_DAILY_BUDGET_LIMIT', '50.0')
        try:
            budget = float(budget_limit)
            if budget <= 0:
                self._add_result('captcha', 'budget_limit', 'warning',
                               'CAPTCHA budget limit is zero or negative',
                               'Set positive budget limit')
            else:
                self._add_result('captcha', 'budget_limit', 'valid',
                               f'Daily budget limit: ${budget}')
        except ValueError:
            self._add_result('captcha', 'budget_limit', 'error',
                           'Invalid CAPTCHA budget limit value',
                           'Set numeric value for budget limit')
    
    def _validate_business_email_configuration(self):
        """Validate business email services"""
        rapidapi_key = os.getenv('RAPIDAPI_KEY')
        hunter_key = os.getenv('HUNTER_API_KEY')
        
        configured_services = []
        
        if rapidapi_key and not rapidapi_key.startswith('your-'):
            configured_services.append('RapidAPI')
            self._add_result('business_email', 'RAPIDAPI_KEY', 'valid',
                           'RapidAPI key configured')
        elif rapidapi_key and rapidapi_key.startswith('your-'):
            self._add_result('business_email', 'RAPIDAPI_KEY', 'error',
                           'RapidAPI key is placeholder value',
                           'Set actual API key from RapidAPI')
        
        if hunter_key and not hunter_key.startswith('your-'):
            configured_services.append('Hunter.io')
            self._add_result('business_email', 'HUNTER_API_KEY', 'valid',
                           'Hunter.io API key configured')
        elif hunter_key and hunter_key.startswith('your-'):
            self._add_result('business_email', 'HUNTER_API_KEY', 'error',
                           'Hunter.io API key is placeholder value',
                           'Set actual API key from Hunter.io')
        
        if not configured_services:
            self._add_result('business_email', 'services', 'warning',
                           'No business email services configured',
                           'Business email lookup will be disabled')
        else:
            self._add_result('business_email', 'services', 'valid',
                           f'{len(configured_services)} email service(s) configured: {", ".join(configured_services)}')
    
    def _validate_webhook_configuration(self):
        """Validate webhook configuration"""
        webhook_url = os.getenv('WEBHOOK_BASE_URL')
        
        if not webhook_url:
            self._add_result('webhooks', 'WEBHOOK_BASE_URL', 'warning',
                           'Webhook base URL not set',
                           'External services cannot send webhooks')
        elif webhook_url.startswith('https://your-domain'):
            self._add_result('webhooks', 'WEBHOOK_BASE_URL', 'error',
                           'Webhook URL is placeholder value',
                           'Set actual domain for webhook endpoints')
        elif not webhook_url.startswith('https://') and self.environment == 'production':
            self._add_result('webhooks', 'WEBHOOK_BASE_URL', 'warning',
                           'Webhook URL not using HTTPS in production',
                           'Use HTTPS for security in production')
        else:
            self._add_result('webhooks', 'WEBHOOK_BASE_URL', 'valid',
                           f'Webhook base URL configured: {webhook_url}')
        
        # Validate webhook timeout
        timeout = os.getenv('WEBHOOK_TIMEOUT', '30')
        try:
            timeout_int = int(timeout)
            if timeout_int < 5:
                self._add_result('webhooks', 'WEBHOOK_TIMEOUT', 'warning',
                               'Webhook timeout is very short',
                               'Consider increasing timeout for reliability')
            elif timeout_int > 120:
                self._add_result('webhooks', 'WEBHOOK_TIMEOUT', 'warning',
                               'Webhook timeout is very long',
                               'Long timeouts may cause issues')
            else:
                self._add_result('webhooks', 'WEBHOOK_TIMEOUT', 'valid',
                               f'Webhook timeout: {timeout_int} seconds')
        except ValueError:
            self._add_result('webhooks', 'WEBHOOK_TIMEOUT', 'error',
                           'Invalid webhook timeout value',
                           'Set numeric timeout value in seconds')
    
    def _validate_rate_limiting_configuration(self):
        """Validate rate limiting settings"""
        rate_limits = [
            ('RATE_LIMIT_PER_MINUTE', 60),
            ('RATE_LIMIT_PER_HOUR', 1000),
            ('RATE_LIMIT_PER_DAY', 10000)
        ]
        
        for env_var, default in rate_limits:
            value = os.getenv(env_var, str(default))
            try:
                limit = int(value)
                if limit <= 0:
                    self._add_result('rate_limiting', env_var, 'error',
                                   f'{env_var} must be positive',
                                   'Set positive rate limit value')
                else:
                    self._add_result('rate_limiting', env_var, 'valid',
                                   f'{env_var.lower().replace("_", " ")}: {limit}')
            except ValueError:
                self._add_result('rate_limiting', env_var, 'error',
                               f'Invalid {env_var} value: {value}',
                               'Set numeric rate limit value')
        
        # Validate rate limit hierarchy
        try:
            per_minute = int(os.getenv('RATE_LIMIT_PER_MINUTE', '60'))
            per_hour = int(os.getenv('RATE_LIMIT_PER_HOUR', '1000'))
            per_day = int(os.getenv('RATE_LIMIT_PER_DAY', '10000'))
            
            if per_minute * 60 > per_hour:
                self._add_result('rate_limiting', 'hierarchy', 'warning',
                               'Per-minute limit * 60 exceeds hourly limit',
                               'Adjust limits to maintain hierarchy')
            
            if per_hour * 24 > per_day:
                self._add_result('rate_limiting', 'hierarchy', 'warning',
                               'Hourly limit * 24 exceeds daily limit',
                               'Adjust limits to maintain hierarchy')
        except ValueError:
            pass  # Already handled in individual validations
    
    def _validate_monitoring_configuration(self):
        """Validate monitoring configuration"""
        monitoring_enabled = os.getenv('MONITORING_ENABLED', 'true').lower()
        
        if monitoring_enabled in ('true', '1', 'yes'):
            self._add_result('monitoring', 'MONITORING_ENABLED', 'valid',
                           'Monitoring is enabled')
            
            # Check optional monitoring services
            sentry_dsn = os.getenv('SENTRY_DSN')
            if sentry_dsn and not sentry_dsn.startswith('your-'):
                self._add_result('monitoring', 'SENTRY_DSN', 'valid',
                               'Sentry error tracking configured')
            elif sentry_dsn and sentry_dsn.startswith('your-'):
                self._add_result('monitoring', 'SENTRY_DSN', 'warning',
                               'Sentry DSN is placeholder value',
                               'Set actual Sentry DSN for error tracking')
            
            alert_email = os.getenv('ALERT_EMAIL')
            if alert_email and '@' in alert_email:
                self._add_result('monitoring', 'ALERT_EMAIL', 'valid',
                               'Alert email configured')
            elif not alert_email and self.environment == 'production':
                self._add_result('monitoring', 'ALERT_EMAIL', 'warning',
                               'No alert email configured for production',
                               'Set email for critical alerts')
            
        else:
            self._add_result('monitoring', 'MONITORING_ENABLED', 'warning',
                           'Monitoring is disabled',
                           'Enable monitoring for production use')
    
    def _validate_telegram_bot_configuration(self):
        """Validate Telegram bot configuration"""
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        
        if not bot_token:
            self._add_result('telegram', 'TELEGRAM_BOT_TOKEN', 'warning',
                           'Telegram bot token not set',
                           'Bot functionality will be disabled')
            return
        
        # Validate bot token format
        if ':' in bot_token and len(bot_token.split(':')) == 2:
            bot_id, token_part = bot_token.split(':', 1)
            if bot_id.isdigit() and len(token_part) >= 35:
                self._add_result('telegram', 'TELEGRAM_BOT_TOKEN', 'valid',
                               f'Bot token format is valid (Bot ID: {bot_id})')
            else:
                self._add_result('telegram', 'TELEGRAM_BOT_TOKEN', 'error',
                               'Invalid bot token format',
                               'Get valid token from @BotFather')
        else:
            self._add_result('telegram', 'TELEGRAM_BOT_TOKEN', 'error',
                           'Invalid bot token format',
                           'Token should be in format: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11')
        
        # Validate admin user IDs
        admin_ids = os.getenv('ADMIN_USER_IDS', '')
        if admin_ids:
            try:
                ids = [int(uid.strip()) for uid in admin_ids.split(',') if uid.strip()]
                self._add_result('telegram', 'ADMIN_USER_IDS', 'valid',
                               f'{len(ids)} admin user(s) configured')
            except ValueError:
                self._add_result('telegram', 'ADMIN_USER_IDS', 'error',
                               'Invalid admin user ID format',
                               'Use comma-separated numeric user IDs')
        else:
            self._add_result('telegram', 'ADMIN_USER_IDS', 'warning',
                           'No admin users configured',
                           'Set admin user IDs for bot management')
        
        # Validate payment configuration
        payment_token = os.getenv('PAYMENT_PROVIDER_TOKEN')
        if payment_token and not payment_token.startswith('your-'):
            self._add_result('telegram', 'PAYMENT_PROVIDER_TOKEN', 'valid',
                           'Payment provider token configured')
        elif bot_token and not payment_token:
            self._add_result('telegram', 'PAYMENT_PROVIDER_TOKEN', 'warning',
                           'Payment provider not configured',
                           'Bot payments will not work')
    
    def _generate_report(self) -> ValidationReport:
        """Generate validation report"""
        # Count results by status
        summary = {'valid': 0, 'warning': 0, 'error': 0, 'missing': 0, 'critical': 0}
        
        for result in self.results:
            summary[result.status] = summary.get(result.status, 0) + 1
            if result.critical:
                summary['critical'] += 1
        
        # Determine overall status
        if summary['error'] > 0 or summary['critical'] > 0:
            overall_status = 'errors'
        elif summary['warning'] > 0:
            overall_status = 'warnings'
        else:
            overall_status = 'valid'
        
        return ValidationReport(
            timestamp=datetime.now(),
            environment=self.environment,
            overall_status=overall_status,
            results=self.results,
            summary=summary
        )
    
    def _display_report(self, report: ValidationReport):
        """Display validation report"""
        print("\n" + "="*80)
        print("🔍 CONFIGURATION VALIDATION REPORT")
        print("="*80)
        print(f"Environment: {report.environment.upper()}")
        print(f"Timestamp: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Overall status
        if report.overall_status == 'valid':
            print("🎉 STATUS: ALL VALID")
            print("✅ Configuration is ready for use")
        elif report.overall_status == 'warnings':
            print("⚠️  STATUS: WARNINGS FOUND")
            print("✅ Configuration is functional but needs attention")
        else:
            print("❌ STATUS: ERRORS FOUND")
            print("🔧 Configuration has issues that need fixing")
        
        # Summary
        print(f"\n📊 Summary:")
        print(f"   ✅ Valid: {report.summary['valid']}")
        print(f"   ⚠️  Warnings: {report.summary['warning']}")
        print(f"   ❌ Errors: {report.summary['error']}")
        if report.summary['critical'] > 0:
            print(f"   🚨 Critical: {report.summary['critical']}")
        
        # Group results by category
        categories = {}
        for result in report.results:
            if result.category not in categories:
                categories[result.category] = []
            categories[result.category].append(result)
        
        # Display results by category
        for category, results in categories.items():
            print(f"\n📋 {category.upper()}:")
            for result in results:
                status_icon = {
                    'valid': '✅',
                    'warning': '⚠️ ',
                    'error': '❌',
                    'missing': '❓'
                }.get(result.status, '❓')
                
                critical_marker = " 🚨" if result.critical else ""
                print(f"   {status_icon} {result.name}: {result.message}{critical_marker}")
                
                if result.suggestion:
                    print(f"      💡 {result.suggestion}")
        
        # Next steps
        print(f"\n🎯 NEXT STEPS:")
        if report.overall_status == 'errors':
            critical_errors = [r for r in report.results if r.status == 'error' and r.critical]
            if critical_errors:
                print("   1. Fix critical errors first:")
                for error in critical_errors[:3]:
                    print(f"      - {error.name}: {error.suggestion}")
            print("   2. Fix all remaining errors")
            print("   3. Re-run validation")
        elif report.overall_status == 'warnings':
            print("   1. Review and address warnings")
            print("   2. Consider security improvements")
            print("   3. Test functionality")
        else:
            print("   1. Configuration is ready!")
            print("   2. Run application tests")
            print("   3. Deploy with confidence")
        
        print("\n" + "="*80)
    
    def save_report(self, report: ValidationReport, filename: str = None):
        """Save validation report to file"""
        if not filename:
            timestamp = report.timestamp.strftime('%Y%m%d_%H%M%S')
            filename = f"config_validation_{report.environment}_{timestamp}.json"
        
        # Convert report to serializable format
        report_data = {
            'timestamp': report.timestamp.isoformat(),
            'environment': report.environment,
            'overall_status': report.overall_status,
            'summary': report.summary,
            'results': [
                {
                    'category': r.category,
                    'name': r.name,
                    'status': r.status,
                    'message': r.message,
                    'suggestion': r.suggestion,
                    'critical': r.critical
                }
                for r in report.results
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"📄 Validation report saved to: {filename}")

def main():
    """Run configuration validation"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate system configuration')
    parser.add_argument('--environment', '-e', default='development',
                       choices=['development', 'staging', 'production', 'testing'],
                       help='Environment to validate for')
    parser.add_argument('--save', '-s', action='store_true',
                       help='Save validation report to file')
    parser.add_argument('--output', '-o', help='Output filename for report')
    
    args = parser.parse_args()
    
    try:
        validator = ConfigurationValidator(args.environment)
        report = validator.validate_all()
        
        if args.save:
            validator.save_report(report, args.output)
        
        # Exit with appropriate code
        if report.overall_status == 'errors':
            sys.exit(1)  # Errors found
        elif report.overall_status == 'warnings':
            sys.exit(2)  # Warnings found
        else:
            sys.exit(0)  # All valid
            
    except KeyboardInterrupt:
        print("\n❌ Validation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Validation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()