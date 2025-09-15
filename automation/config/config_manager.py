#!/usr/bin/env python3
"""
Comprehensive Configuration Management System
Handles all configuration needs with proper validation and security
"""

import os
import sys
import json
import logging
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import redis
import hashlib
import secrets

logger = logging.getLogger(__name__)

class Environment(Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging" 
    PRODUCTION = "production"
    TESTING = "testing"

@dataclass
class ServiceConfig:
    """Service-specific configuration"""
    name: str
    enabled: bool = True
    endpoint: Optional[str] = None
    timeout: int = 30
    retry_count: int = 3
    rate_limit: int = 100
    credentials: Dict[str, Any] = field(default_factory=dict)

@dataclass 
class DatabaseConfig:
    """Database configuration"""
    url: str
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False

@dataclass
class RedisConfig:
    """Redis configuration"""
    url: str
    password: Optional[str] = None
    database: int = 0
    max_connections: int = 20
    socket_timeout: int = 5
    decode_responses: bool = True

class ConfigManager:
    """Comprehensive configuration manager with validation and security"""
    
    def __init__(self, environment: Optional[str] = None):
        # Load environment variables from .env file if available
        self._load_env_file()
        
        self.environment = Environment(environment or os.getenv('ENVIRONMENT', 'development'))
        self.config_dir = Path(__file__).parent
        self.root_dir = self.config_dir.parent.parent
        self._config_cache = {}
        self._load_base_config()
    
    def _load_env_file(self):
        """Load environment variables from .env file if available"""
        try:
            from dotenv import load_dotenv
            
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
        
    def _load_base_config(self):
        """Load base configuration from multiple sources"""
        # Load from environment-specific file first
        env_config_file = self.config_dir / f"config.{self.environment.value}.json"
        if env_config_file.exists():
            with open(env_config_file) as f:
                self._config_cache.update(json.load(f))
        
        # Load default config
        default_config_file = self.config_dir / "config.default.json"
        if default_config_file.exists():
            with open(default_config_file) as f:
                default_config = json.load(f)
                # Merge defaults with existing config (existing takes precedence)
                for key, value in default_config.items():
                    if key not in self._config_cache:
                        self._config_cache[key] = value
        
        # Override with environment variables
        self._load_env_overrides()
        
    def _load_env_overrides(self):
        """Load configuration overrides from environment variables"""
        env_mappings = {
            # Database configuration
            'DATABASE_URL': ('database', 'url'),
            'DATABASE_POOL_SIZE': ('database', 'pool_size', int),
            'DATABASE_MAX_OVERFLOW': ('database', 'max_overflow', int),
            'DATABASE_ECHO': ('database', 'echo', bool),
            
            # Redis configuration  
            'REDIS_URL': ('redis', 'url'),
            'REDIS_PASSWORD': ('redis', 'password'),
            'REDIS_DATABASE': ('redis', 'database', int),
            'REDIS_MAX_CONNECTIONS': ('redis', 'max_connections', int),
            
            # Twilio configuration
            'TWILIO_ACCOUNT_SID': ('twilio', 'account_sid'),
            'TWILIO_AUTH_TOKEN': ('twilio', 'auth_token'),
            'TWILIO_AREA_CODE': ('twilio', 'area_code'),
            
            # BrightData proxy configuration
            'BRIGHTDATA_PROXY_URL': ('proxy', 'brightdata_url'),
            'BRIGHTDATA_USERNAME': ('proxy', 'username'),
            'BRIGHTDATA_PASSWORD': ('proxy', 'password'),
            
            # Webhook configuration
            'WEBHOOK_SECRET': ('webhooks', 'secret'),
            'WEBHOOK_URL': ('webhooks', 'url'),
            
            # CAPTCHA services
            'TWOCAPTCHA_API_KEY': ('captcha', 'twocaptcha_key'),
            'ANTICAPTCHA_API_KEY': ('captcha', 'anticaptcha_key'),
            'CAPMONSTER_API_KEY': ('captcha', 'capmonster_key'),
            
            # Business email services
            'RAPIDAPI_KEY': ('business_email', 'rapidapi_key'),
            'HUNTER_API_KEY': ('business_email', 'hunter_api_key'),
            
            # Rate limiting
            'RATE_LIMIT_PER_MINUTE': ('rate_limiting', 'per_minute', int),
            'RATE_LIMIT_PER_HOUR': ('rate_limiting', 'per_hour', int),
            'RATE_LIMIT_PER_DAY': ('rate_limiting', 'per_day', int),
            
            # Security
            'JWT_SECRET': ('security', 'jwt_secret'),
            'ENCRYPTION_KEY': ('security', 'encryption_key'),
            
            # API Configuration
            'API_BASE_URL': ('api', 'base_url'),
            'API_TIMEOUT': ('api', 'timeout', int),
            'API_RATE_LIMIT': ('api', 'rate_limit', int),
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Handle type conversion
                if len(config_path) > 2:
                    converter = config_path[2]
                    if converter == int:
                        try:
                            value = int(value)
                        except ValueError:
                            logger.warning(f"Invalid integer value for {env_var}: {value}")
                            continue
                    elif converter == bool:
                        value = value.lower() in ('true', '1', 'yes', 'on')
                
                # Set nested configuration
                self._set_nested_config(config_path[0], config_path[1], value)
    
    def _set_nested_config(self, section: str, key: str, value: Any):
        """Set nested configuration value"""
        if section not in self._config_cache:
            self._config_cache[section] = {}
        self._config_cache[section][key] = value
    
    # Service Configuration Methods
    
    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration"""
        db_config = self._config_cache.get('database', {})
        return DatabaseConfig(
            url=db_config.get('url', 'postgresql://user:password@localhost/automation'),
            pool_size=db_config.get('pool_size', 10),
            max_overflow=db_config.get('max_overflow', 20),
            pool_timeout=db_config.get('pool_timeout', 30),
            pool_recycle=db_config.get('pool_recycle', 3600),
            echo=db_config.get('echo', False)
        )
    
    def get_redis_config(self) -> RedisConfig:
        """Get Redis configuration"""
        redis_config = self._config_cache.get('redis', {})
        redis_url = redis_config.get('url', 'redis://localhost:6379')
        
        # Extract password from URL if present
        password = redis_config.get('password')
        if not password and '://:' in redis_url:
            # Extract password from redis://:password@host:port format
            try:
                password = redis_url.split('://')[1].split('@')[0].split(':')[1]
            except (IndexError, ValueError):
                pass
        
        return RedisConfig(
            url=redis_url,
            password=password,
            database=redis_config.get('database', 0),
            max_connections=redis_config.get('max_connections', 20),
            socket_timeout=redis_config.get('socket_timeout', 5),
            decode_responses=redis_config.get('decode_responses', True)
        )
    
    def get_twilio_config(self) -> ServiceConfig:
        """Get Twilio service configuration"""
        twilio_config = self._config_cache.get('twilio', {})
        return ServiceConfig(
            name='twilio',
            enabled=bool(twilio_config.get('account_sid') and twilio_config.get('auth_token')),
            credentials={
                'account_sid': twilio_config.get('account_sid', ''),
                'auth_token': twilio_config.get('auth_token', ''),
                'area_code': twilio_config.get('area_code', '720')
            },
            timeout=twilio_config.get('timeout', 30),
            retry_count=twilio_config.get('retry_count', 3)
        )
    
    def get_proxy_config(self) -> ServiceConfig:
        """Get proxy service configuration"""
        proxy_config = self._config_cache.get('proxy', {})
        return ServiceConfig(
            name='brightdata_proxy',
            enabled=bool(proxy_config.get('brightdata_url')),
            endpoint=proxy_config.get('brightdata_url', ''),
            credentials={
                'username': proxy_config.get('username', ''),
                'password': proxy_config.get('password', ''),
                'proxy_url': proxy_config.get('brightdata_url', '')
            },
            timeout=proxy_config.get('timeout', 30),
            retry_count=proxy_config.get('retry_count', 3)
        )
    
    def get_captcha_config(self) -> ServiceConfig:
        """Get CAPTCHA solving service configuration"""
        captcha_config = self._config_cache.get('captcha', {})
        
        # Determine which service is available
        enabled_services = []
        credentials = {}
        
        if captcha_config.get('twocaptcha_key'):
            enabled_services.append('2captcha')
            credentials['twocaptcha_key'] = captcha_config['twocaptcha_key']
            
        if captcha_config.get('anticaptcha_key'):
            enabled_services.append('anticaptcha')
            credentials['anticaptcha_key'] = captcha_config['anticaptcha_key']
            
        if captcha_config.get('capmonster_key'):
            enabled_services.append('capmonster')
            credentials['capmonster_key'] = captcha_config['capmonster_key']
        
        return ServiceConfig(
            name='captcha_solver',
            enabled=len(enabled_services) > 0,
            credentials=credentials,
            timeout=captcha_config.get('timeout', 120),
            retry_count=captcha_config.get('retry_count', 3),
            rate_limit=captcha_config.get('daily_limit', 50)
        )
    
    def get_business_email_config(self) -> ServiceConfig:
        """Get business email service configuration"""
        email_config = self._config_cache.get('business_email', {})
        
        credentials = {}
        enabled = False
        
        if email_config.get('rapidapi_key'):
            credentials['rapidapi_key'] = email_config['rapidapi_key']
            enabled = True
            
        if email_config.get('hunter_api_key'):
            credentials['hunter_api_key'] = email_config['hunter_api_key']
            enabled = True
        
        return ServiceConfig(
            name='business_email',
            enabled=enabled,
            credentials=credentials,
            timeout=email_config.get('timeout', 30),
            retry_count=email_config.get('retry_count', 3),
            rate_limit=email_config.get('rate_limit', 100)
        )
    
    def get_webhook_config(self) -> Dict[str, Any]:
        """Get webhook configuration"""
        webhook_config = self._config_cache.get('webhooks', {})
        
        # Generate secret if not provided
        secret = webhook_config.get('secret')
        if not secret or secret in ('your-webhook-secret-here', 'changeme'):
            secret = secrets.token_urlsafe(32)
            logger.warning(f"Generated new webhook secret. Please save: {secret}")
        
        return {
            'secret': secret,
            'url': webhook_config.get('url', 'https://your-domain.com/webhook'),
            'enabled': bool(webhook_config.get('url'))
        }
    
    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration"""
        security_config = self._config_cache.get('security', {})
        
        # Generate JWT secret if not provided
        jwt_secret = security_config.get('jwt_secret')
        if not jwt_secret or jwt_secret in ('your-jwt-secret-here', 'changeme'):
            jwt_secret = secrets.token_urlsafe(64)
            logger.warning(f"Generated new JWT secret. Please save: {jwt_secret}")
        
        # Generate encryption key if not provided
        encryption_key = security_config.get('encryption_key')
        if not encryption_key or encryption_key in ('your-encryption-key-here', 'changeme'):
            encryption_key = secrets.token_urlsafe(32)
            logger.warning(f"Generated new encryption key. Please save: {encryption_key}")
        
        return {
            'jwt_secret': jwt_secret,
            'encryption_key': encryption_key,
            'session_timeout': security_config.get('session_timeout', 3600),
            'password_min_length': security_config.get('password_min_length', 8),
            'max_login_attempts': security_config.get('max_login_attempts', 5)
        }
    
    def get_rate_limiting_config(self) -> Dict[str, int]:
        """Get rate limiting configuration"""
        rate_config = self._config_cache.get('rate_limiting', {})
        return {
            'per_minute': rate_config.get('per_minute', 60),
            'per_hour': rate_config.get('per_hour', 1000),
            'per_day': rate_config.get('per_day', 10000),
            'burst_size': rate_config.get('burst_size', 10)
        }
    
    def get_api_config(self) -> Dict[str, Any]:
        """Get API configuration"""
        api_config = self._config_cache.get('api', {})
        return {
            'base_url': api_config.get('base_url', 'http://localhost:8000'),
            'timeout': api_config.get('timeout', 30),
            'rate_limit': api_config.get('rate_limit', 1000),
            'max_retries': api_config.get('max_retries', 3),
            'backoff_factor': api_config.get('backoff_factor', 0.5)
        }
    
    # Validation Methods
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate all configuration and return status"""
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'services': {}
        }
        
        # Validate database configuration
        db_config = self.get_database_config()
        if not db_config.url or db_config.url.startswith('your-'):
            validation_results['errors'].append('Invalid database URL')
            validation_results['valid'] = False
        validation_results['services']['database'] = db_config.url != 'postgresql://user:password@localhost/automation'
        
        # Validate Redis configuration
        redis_config = self.get_redis_config()
        try:
            # Test Redis connection
            redis_client = redis.from_url(
                redis_config.url,
                password=redis_config.password,
                socket_timeout=2,
                decode_responses=True
            )
            redis_client.ping()
            validation_results['services']['redis'] = True
        except Exception as e:
            validation_results['warnings'].append(f'Redis connection failed: {str(e)}')
            validation_results['services']['redis'] = False
        
        # Validate Twilio configuration
        twilio_config = self.get_twilio_config()
        validation_results['services']['twilio'] = twilio_config.enabled
        if not twilio_config.enabled:
            validation_results['warnings'].append('Twilio credentials not configured')
        
        # Validate proxy configuration
        proxy_config = self.get_proxy_config()
        validation_results['services']['proxy'] = proxy_config.enabled
        if not proxy_config.enabled:
            validation_results['warnings'].append('Proxy service not configured')
        
        # Validate CAPTCHA configuration
        captcha_config = self.get_captcha_config()
        validation_results['services']['captcha'] = captcha_config.enabled
        if not captcha_config.enabled:
            validation_results['warnings'].append('No CAPTCHA solving services configured')
        
        # Validate security configuration
        security_config = self.get_security_config()
        if len(security_config['jwt_secret']) < 32:
            validation_results['errors'].append('JWT secret too short (minimum 32 characters)')
            validation_results['valid'] = False
        
        return validation_results
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on all configured services"""
        health_status = {
            'healthy': True,
            'services': {},
            'timestamp': int(__import__('time').time())
        }
        
        # Check Redis
        try:
            redis_config = self.get_redis_config()
            redis_client = redis.from_url(
                redis_config.url,
                password=redis_config.password,
                socket_timeout=2
            )
            redis_client.ping()
            health_status['services']['redis'] = {'status': 'healthy', 'response_time_ms': 0}
        except Exception as e:
            health_status['services']['redis'] = {'status': 'unhealthy', 'error': str(e)}
            health_status['healthy'] = False
        
        # Check Twilio (if configured)
        twilio_config = self.get_twilio_config()
        if twilio_config.enabled:
            try:
                from twilio.rest import Client
                client = Client(
                    twilio_config.credentials['account_sid'],
                    twilio_config.credentials['auth_token']
                )
                # Test with a simple account fetch
                account = client.api.accounts(twilio_config.credentials['account_sid']).fetch()
                health_status['services']['twilio'] = {
                    'status': 'healthy',
                    'account_status': account.status
                }
            except Exception as e:
                health_status['services']['twilio'] = {'status': 'unhealthy', 'error': str(e)}
                health_status['healthy'] = False
        else:
            health_status['services']['twilio'] = {'status': 'disabled'}
        
        return health_status
    
    def export_config_template(self, include_secrets: bool = False) -> str:
        """Export configuration template for .env file"""
        template = """# Automation System Configuration
# Copy this to .env and update with your actual values

# Environment
ENVIRONMENT=development

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost/automation
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_ECHO=false

# Redis Configuration
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your_redis_password_here
REDIS_DATABASE=0
REDIS_MAX_CONNECTIONS=20

# Twilio SMS Configuration
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
TWILIO_AREA_CODE=720

# BrightData Proxy Configuration
BRIGHTDATA_PROXY_URL=http://brd-customer-hl_12345678-zone-datacenter_proxy1:password@brd.superproxy.io:22225
BRIGHTDATA_USERNAME=brd-customer-hl_12345678-zone-datacenter_proxy1
BRIGHTDATA_PASSWORD=your_brightdata_password

# Webhook Configuration
WEBHOOK_SECRET=your_webhook_secret_here_min_32_chars
WEBHOOK_URL=https://your-domain.com/webhook

# CAPTCHA Solving Services (at least one required)
TWOCAPTCHA_API_KEY=your_2captcha_api_key_here
ANTICAPTCHA_API_KEY=your_anticaptcha_api_key_here
CAPMONSTER_API_KEY=your_capmonster_api_key_here

# Business Email Services
RAPIDAPI_KEY=your_rapidapi_key_here
HUNTER_API_KEY=your_hunter_api_key_here

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
RATE_LIMIT_PER_DAY=10000

# Security Configuration
JWT_SECRET=your_jwt_secret_here_min_64_chars_for_security
ENCRYPTION_KEY=your_encryption_key_here_min_32_chars

# API Configuration
API_BASE_URL=http://localhost:8000
API_TIMEOUT=30
API_RATE_LIMIT=1000
"""
        
        if include_secrets:
            # Generate actual secure values for template
            template = template.replace(
                'your_webhook_secret_here_min_32_chars',
                secrets.token_urlsafe(32)
            ).replace(
                'your_jwt_secret_here_min_64_chars_for_security',
                secrets.token_urlsafe(64)
            ).replace(
                'your_encryption_key_here_min_32_chars',
                secrets.token_urlsafe(32)
            )
        
        return template
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get complete configuration (without sensitive data)"""
        config_copy = self._config_cache.copy()
        
        # Remove sensitive information
        sensitive_keys = ['password', 'secret', 'key', 'token', 'auth']
        self._redact_sensitive_data(config_copy, sensitive_keys)
        
        return config_copy
    
    def _redact_sensitive_data(self, data: Dict[str, Any], sensitive_keys: list):
        """Recursively redact sensitive data from configuration"""
        if isinstance(data, dict):
            for key, value in data.items():
                if any(sensitive in key.lower() for sensitive in sensitive_keys):
                    if isinstance(value, str) and value:
                        data[key] = f"{value[:4]}****{value[-4:]}" if len(value) > 8 else "****"
                elif isinstance(value, dict):
                    self._redact_sensitive_data(value, sensitive_keys)

# Global configuration manager instance
_config_manager = None

def get_config(environment: Optional[str] = None) -> ConfigManager:
    """Get global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(environment)
    return _config_manager

def reset_config():
    """Reset global configuration manager (useful for testing)"""
    global _config_manager
    _config_manager = None

if __name__ == "__main__":
    # Test configuration manager
    config = ConfigManager()
    
    print("🔧 Configuration Manager Test")
    print("=" * 50)
    
    # Test database config
    db_config = config.get_database_config()
    print(f"📊 Database: {db_config.url[:30]}...")
    
    # Test Redis config
    redis_config = config.get_redis_config()
    print(f"📦 Redis: {redis_config.url}")
    
    # Test service configurations
    twilio_config = config.get_twilio_config()
    print(f"📱 Twilio: {'✅ Enabled' if twilio_config.enabled else '❌ Disabled'}")
    
    proxy_config = config.get_proxy_config()
    print(f"🔗 Proxy: {'✅ Enabled' if proxy_config.enabled else '❌ Disabled'}")
    
    captcha_config = config.get_captcha_config()
    print(f"🤖 CAPTCHA: {'✅ Enabled' if captcha_config.enabled else '❌ Disabled'}")
    
    # Validation test
    print(f"\n🔍 Configuration Validation:")
    validation = config.validate_configuration()
    print(f"   Valid: {'✅' if validation['valid'] else '❌'}")
    print(f"   Errors: {len(validation['errors'])}")
    print(f"   Warnings: {len(validation['warnings'])}")
    
    if validation['errors']:
        print("   Errors found:")
        for error in validation['errors']:
            print(f"   - {error}")
    
    # Health check test
    print(f"\n💗 Health Check:")
    health = config.health_check()
    print(f"   Overall: {'✅ Healthy' if health['healthy'] else '❌ Unhealthy'}")
    for service, status in health['services'].items():
        print(f"   {service}: {status.get('status', 'unknown')}")
    
    print(f"\n📋 Export .env template:")
    print("   Run: python -c \"from automation.config.config_manager import ConfigManager; print(ConfigManager().export_config_template())\" > .env.example")