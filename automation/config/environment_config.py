#!/usr/bin/env python3
"""
Environment Configuration Management
Handles environment-specific configurations with validation and defaults
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import secrets
from utils.vault_client import get_secret, get_int

logger = logging.getLogger(__name__)

class DeploymentEnvironment(Enum):
    """Deployment environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"
    LOCAL = "local"

@dataclass
class ServiceEndpoint:
    """Service endpoint configuration"""
    name: str
    url: str
    timeout: int = 30
    retries: int = 3
    health_check: str = "/health"
    enabled: bool = True

@dataclass
class SecurityConfig:
    """Security configuration settings"""
    jwt_expiry_hours: int = 24
    max_login_attempts: int = 5
    password_min_length: int = 8
    require_2fa: bool = False
    session_timeout_minutes: int = 30
    cors_origins: List[str] = field(default_factory=lambda: ["http://localhost:3000"])
    rate_limit_per_minute: int = 60

class EnvironmentConfig:
    """Environment-specific configuration manager"""
    
    def __init__(self, environment: Optional[str] = None):
        self.environment = DeploymentEnvironment(
            environment or str(get_secret('ENVIRONMENT', 'development'))
        )
        self.config_dir = Path(__file__).parent
        self._config = self._load_environment_config()
        self._validate_config()
    
    def _load_environment_config(self) -> Dict[str, Any]:
        """Load configuration based on environment"""
        base_config = self._get_base_config()
        
        # Load environment-specific overrides
        env_file = self.config_dir / f"env.{self.environment.value}.json"
        if env_file.exists():
            with open(env_file, 'r') as f:
                env_overrides = json.load(f)
                base_config.update(env_overrides)
        
        # Apply environment variable overrides
        self._apply_env_var_overrides(base_config)
        
        return base_config
    
    def _get_base_config(self) -> Dict[str, Any]:
        """Get base configuration with sensible defaults"""
        return {
            "app": {
                "name": "Tinder Automation System",
                "version": "2.0.0",
                "debug": self.environment in [DeploymentEnvironment.DEVELOPMENT, DeploymentEnvironment.LOCAL],
                "log_level": "DEBUG" if self.environment == DeploymentEnvironment.DEVELOPMENT else "INFO",
                "timezone": "UTC"
            },
            "server": {
                "host": "0.0.0.0" if self.environment == DeploymentEnvironment.PRODUCTION else "127.0.0.1",
                "port": get_int('PORT', 8000),
                "workers": 1 if self.environment == DeploymentEnvironment.DEVELOPMENT else 4,
                "reload": self.environment == DeploymentEnvironment.DEVELOPMENT,
                "access_log": True,
                "keepalive_timeout": 5
            },
            "database": {
                "url": self._get_database_url(),
                "pool_size": 5 if self.environment == DeploymentEnvironment.DEVELOPMENT else 10,
                "max_overflow": 10 if self.environment == DeploymentEnvironment.DEVELOPMENT else 20,
                "pool_timeout": 30,
                "pool_recycle": 3600,
                "echo": self.environment == DeploymentEnvironment.DEVELOPMENT,
                "migrate_on_startup": self.environment != DeploymentEnvironment.PRODUCTION
            },
            "redis": {
                "url": get_secret('REDIS_URL', 'redis://localhost:6379'),
                "max_connections": 20,
                "socket_timeout": 5,
                "socket_connect_timeout": 5,
                "decode_responses": True,
                "health_check_interval": 30
            },
            "security": {
                "jwt_secret": self._get_or_generate_secret('JWT_SECRET', 64),
                "jwt_expiry_hours": 24,
                "encryption_key": self._get_or_generate_secret('ENCRYPTION_KEY', 32),
                "webhook_secret": self._get_or_generate_secret('WEBHOOK_SECRET', 32),
                "max_login_attempts": 5,
                "password_min_length": 8,
                "session_timeout_minutes": 30,
                "require_2fa": self.environment == DeploymentEnvironment.PRODUCTION,
                "cors_origins": self._get_cors_origins(),
                "rate_limit_per_minute": 60 if self.environment == DeploymentEnvironment.DEVELOPMENT else 30
            },
            "services": {
                "twilio": {
                    "enabled": bool(get_secret('TWILIO_ACCOUNT_SID')),
                    "account_sid": get_secret('TWILIO_ACCOUNT_SID', ''),
                    "auth_token": get_secret('TWILIO_AUTH_TOKEN', ''),
                    "area_code": get_secret('TWILIO_AREA_CODE', '720'),
                    "webhook_url": get_secret('TWILIO_WEBHOOK_URL', ''),
                    "rate_limit_per_hour": 100,
                    "max_retry_attempts": 3
                },
                "brightdata": {
                    "enabled": bool(get_secret('BRIGHTDATA_PROXY_URL')),
                    "proxy_url": get_secret('BRIGHTDATA_PROXY_URL', ''),
                    "username": get_secret('BRIGHTDATA_USERNAME', ''),
                    "password": get_secret('BRIGHTDATA_PASSWORD', ''),
                    "timeout": 30,
                    "max_sessions": 10
                },
                "captcha": {
                    "enabled": bool(get_secret('TWOCAPTCHA_API_KEY') or get_secret('ANTICAPTCHA_API_KEY')),
                    "twocaptcha_key": get_secret('TWOCAPTCHA_API_KEY', ''),
                    "anticaptcha_key": get_secret('ANTICAPTCHA_API_KEY', ''),
                    "capmonster_key": get_secret('CAPMONSTER_API_KEY', ''),
                    "timeout": 120,
                    "max_retry_attempts": 3,
                    "daily_budget_limit": 50.0
                },
                "business_email": {
                    "enabled": bool(get_secret('RAPIDAPI_KEY') or get_secret('HUNTER_API_KEY')),
                    "rapidapi_key": get_secret('RAPIDAPI_KEY', ''),
                    "hunter_api_key": get_secret('HUNTER_API_KEY', ''),
                    "timeout": 30,
                    "cache_ttl_hours": 24
                }
            },
            "automation": {
                "max_concurrent_sessions": 3 if self.environment == DeploymentEnvironment.DEVELOPMENT else 10,
                "session_duration_minutes": 15,
                "break_duration_minutes": 60,
                "aggressiveness_level": 0.3,
                "anti_detection_enabled": True,
                "screenshot_on_error": self.environment != DeploymentEnvironment.PRODUCTION,
                "log_level": "DEBUG" if self.environment == DeploymentEnvironment.DEVELOPMENT else "INFO"
            },
            "monitoring": {
                "enabled": self.environment != DeploymentEnvironment.LOCAL,
                "health_check_interval": 30,
                "metrics_retention_hours": 168,  # 7 days
                "alert_email": get_secret('ALERT_EMAIL', ''),
                "sentry_dsn": get_secret('SENTRY_DSN', ''),
                "prometheus_enabled": self.environment == DeploymentEnvironment.PRODUCTION
            },
            "features": {
                "telegram_bot_enabled": True,
                "api_enabled": True,
                "webhooks_enabled": True,
                "real_time_updates": True,
                "bulk_operations": True,
                "advanced_automation": self.environment != DeploymentEnvironment.DEVELOPMENT
            }
        }
    
    def _get_database_url(self) -> str:
        """Get database URL with environment-specific defaults"""
        db_url = get_secret('DATABASE_URL')
        if db_url:
            return str(db_url)
        
        # Environment-specific defaults
        if self.environment == DeploymentEnvironment.PRODUCTION:
            return "postgresql://user:password@db:5432/automation_prod"
        elif self.environment == DeploymentEnvironment.STAGING:
            return "postgresql://user:password@db:5432/automation_staging"
        elif self.environment == DeploymentEnvironment.TESTING:
            return "postgresql://user:password@localhost:5432/automation_test"
        else:
            return "postgresql://user:password@localhost:5432/automation_dev"
    
    def _get_cors_origins(self) -> List[str]:
        """Get CORS origins based on environment"""
        cors_origins_val = get_secret('CORS_ORIGINS', '')
        cors_origins = str(cors_origins_val).split(',') if cors_origins_val else []
        cors_origins = [origin.strip() for origin in cors_origins if origin.strip()]
        
        if not cors_origins:
            if self.environment == DeploymentEnvironment.PRODUCTION:
                return ["https://your-domain.com"]
            elif self.environment == DeploymentEnvironment.STAGING:
                return ["https://staging.your-domain.com", "http://localhost:3000"]
            else:
                return ["http://localhost:3000", "http://localhost:8080", "http://127.0.0.1:3000"]
        
        return cors_origins
    
    def _get_or_generate_secret(self, env_var: str, min_length: int) -> str:
        """Get secret from environment or generate secure one"""
        secret = get_secret(env_var)
        
        # Check if secret exists and is valid
        if secret and len(str(secret)) >= min_length and not str(secret).startswith('your-'):
            return str(secret)
        
        # Generate secure secret
        generated_secret = secrets.token_urlsafe(min_length)
        
        if self.environment == DeploymentEnvironment.PRODUCTION:
            logger.error(f"❌ {env_var} not set in production environment")
            raise ValueError(f"Production environment requires {env_var} to be set")
        else:
            logger.warning(f"⚠️ Generated {env_var}: {generated_secret}")
            logger.warning(f"   Please save this to your environment: export {env_var}='{generated_secret}'")
        
        return generated_secret
    
    def _apply_env_var_overrides(self, config: Dict[str, Any]):
        """Apply environment variable overrides to configuration"""
        # Define environment variable mappings
        env_mappings = {
            'APP_DEBUG': ('app', 'debug', bool),
            'APP_LOG_LEVEL': ('app', 'log_level', str),
            'SERVER_HOST': ('server', 'host', str),
            'SERVER_PORT': ('server', 'port', int),
            'SERVER_WORKERS': ('server', 'workers', int),
            'DATABASE_POOL_SIZE': ('database', 'pool_size', int),
            'DATABASE_ECHO': ('database', 'echo', bool),
            'REDIS_MAX_CONNECTIONS': ('redis', 'max_connections', int),
            'AUTOMATION_MAX_SESSIONS': ('automation', 'max_concurrent_sessions', int),
            'AUTOMATION_AGGRESSIVENESS': ('automation', 'aggressiveness_level', float),
            'MONITORING_ENABLED': ('monitoring', 'enabled', bool),
        }
        
        for env_var, (section, key, value_type) in env_mappings.items():
            value = get_secret(env_var)
            if value is not None:
                try:
                    if value_type == bool:
                        converted_value = str(value).lower() in ('true', '1', 'yes', 'on')
                    elif value_type == int:
                        converted_value = int(value)
                    elif value_type == float:
                        converted_value = float(value)
                    else:
                        converted_value = value
                    
                    if section not in config:
                        config[section] = {}
                    config[section][key] = converted_value
                    
                except (ValueError, TypeError) as e:
                    logger.warning(f"⚠️ Invalid value for {env_var}: {value} ({e})")
    
    def _validate_config(self):
        """Validate configuration for current environment"""
        errors = []
        warnings = []
        
        # Production-specific validations
        if self.environment == DeploymentEnvironment.PRODUCTION:
            # Check required secrets
            required_secrets = ['jwt_secret', 'encryption_key', 'webhook_secret']
            for secret in required_secrets:
                value = self._config['security'][secret]
                if not value or len(value) < 32:
                    errors.append(f"Production requires secure {secret} (min 32 chars)")
            
            # Check database is not using default
            if 'localhost' in self._config['database']['url']:
                warnings.append("Production should use external database")
            
            # Check debug is disabled
            if self._config['app']['debug']:
                warnings.append("Debug mode should be disabled in production")
        
        # Check service configurations
        if self._config['services']['twilio']['enabled']:
            creds = self._config['services']['twilio']
            if not creds['account_sid'] or not creds['auth_token']:
                errors.append("Twilio enabled but credentials missing")
        
        if self._config['services']['brightdata']['enabled']:
            creds = self._config['services']['brightdata']
            if not creds['proxy_url'] or not creds['username'] or not creds['password']:
                errors.append("BrightData enabled but credentials missing")
        
        # Log validation results
        if errors:
            for error in errors:
                logger.error(f"❌ Configuration error: {error}")
            if self.environment == DeploymentEnvironment.PRODUCTION:
                raise ValueError(f"Configuration errors in production: {', '.join(errors)}")
        
        if warnings:
            for warning in warnings:
                logger.warning(f"⚠️ Configuration warning: {warning}")
    
    # Public API methods
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated path"""
        keys = key_path.split('.')
        value = self._config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_app_config(self) -> Dict[str, Any]:
        """Get application configuration"""
        return self._config['app']
    
    def get_server_config(self) -> Dict[str, Any]:
        """Get server configuration"""
        return self._config['server']
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        return self._config['database']
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration"""
        return self._config['redis']
    
    def get_security_config(self) -> SecurityConfig:
        """Get security configuration as structured object"""
        sec_config = self._config['security']
        return SecurityConfig(
            jwt_expiry_hours=sec_config['jwt_expiry_hours'],
            max_login_attempts=sec_config['max_login_attempts'],
            password_min_length=sec_config['password_min_length'],
            require_2fa=sec_config['require_2fa'],
            session_timeout_minutes=sec_config['session_timeout_minutes'],
            cors_origins=sec_config['cors_origins'],
            rate_limit_per_minute=sec_config['rate_limit_per_minute']
        )
    
    def get_service_config(self, service_name: str) -> Dict[str, Any]:
        """Get specific service configuration"""
        return self._config['services'].get(service_name, {})
    
    def get_automation_config(self) -> Dict[str, Any]:
        """Get automation configuration"""
        return self._config['automation']
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration"""
        return self._config['monitoring']
    
    def get_feature_flags(self) -> Dict[str, bool]:
        """Get feature flags configuration"""
        return self._config['features']
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment == DeploymentEnvironment.PRODUCTION
    
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment in [DeploymentEnvironment.DEVELOPMENT, DeploymentEnvironment.LOCAL]
    
    def is_debug_enabled(self) -> bool:
        """Check if debug mode is enabled"""
        return self._config['app']['debug']
    
    def get_service_endpoints(self) -> Dict[str, ServiceEndpoint]:
        """Get all configured service endpoints"""
        endpoints = {}
        
        services_config = self._config['services']
        
        # Twilio
        if services_config['twilio']['enabled']:
            endpoints['twilio'] = ServiceEndpoint(
                name='twilio',
                url='https://api.twilio.com/2010-04-01',
                timeout=30
            )
        
        # BrightData
        if services_config['brightdata']['enabled']:
            endpoints['brightdata'] = ServiceEndpoint(
                name='brightdata',
                url=services_config['brightdata']['proxy_url'],
                timeout=services_config['brightdata']['timeout']
            )
        
        # CAPTCHA services
        captcha_config = services_config['captcha']
        if captcha_config['enabled']:
            if captcha_config['twocaptcha_key']:
                endpoints['twocaptcha'] = ServiceEndpoint(
                    name='twocaptcha',
                    url='https://2captcha.com',
                    timeout=captcha_config['timeout']
                )
            
            if captcha_config['anticaptcha_key']:
                endpoints['anticaptcha'] = ServiceEndpoint(
                    name='anticaptcha',
                    url='https://api.anti-captcha.com',
                    timeout=captcha_config['timeout']
                )
        
        return endpoints
    
    def export_env_template(self) -> str:
        """Export environment template with current configuration"""
        template_lines = [
            f"# Environment Configuration for {self.environment.value.upper()}",
            f"# Generated at: {__import__('datetime').datetime.now().isoformat()}",
            "",
            "# Environment Type",
            f"ENVIRONMENT={self.environment.value}",
            "",
            "# Application Configuration",
            f"APP_DEBUG={str(self._config['app']['debug']).lower()}",
            f"APP_LOG_LEVEL={self._config['app']['log_level']}",
            "",
            "# Server Configuration",
            f"SERVER_HOST={self._config['server']['host']}",
            f"SERVER_PORT={self._config['server']['port']}",
            f"SERVER_WORKERS={self._config['server']['workers']}",
            "",
            "# Database Configuration",
            f"DATABASE_URL={self._config['database']['url']}",
            f"DATABASE_POOL_SIZE={self._config['database']['pool_size']}",
            f"DATABASE_ECHO={str(self._config['database']['echo']).lower()}",
            "",
            "# Redis Configuration",
            f"REDIS_URL={self._config['redis']['url']}",
            f"REDIS_MAX_CONNECTIONS={self._config['redis']['max_connections']}",
            "",
            "# Security Configuration (CHANGE THESE IN PRODUCTION)",
            f"JWT_SECRET={self._config['security']['jwt_secret']}",
            f"ENCRYPTION_KEY={self._config['security']['encryption_key']}",
            f"WEBHOOK_SECRET={self._config['security']['webhook_secret']}",
            "",
            "# Twilio Configuration",
            f"TWILIO_ACCOUNT_SID={self._config['services']['twilio']['account_sid']}",
            f"TWILIO_AUTH_TOKEN={self._config['services']['twilio']['auth_token']}",
            f"TWILIO_AREA_CODE={self._config['services']['twilio']['area_code']}",
            "",
            "# BrightData Proxy Configuration", 
            f"BRIGHTDATA_PROXY_URL={self._config['services']['brightdata']['proxy_url']}",
            f"BRIGHTDATA_USERNAME={self._config['services']['brightdata']['username']}",
            f"BRIGHTDATA_PASSWORD={self._config['services']['brightdata']['password']}",
            "",
            "# CAPTCHA Solving Services",
            f"TWOCAPTCHA_API_KEY={self._config['services']['captcha']['twocaptcha_key']}",
            f"ANTICAPTCHA_API_KEY={self._config['services']['captcha']['anticaptcha_key']}",
            f"CAPMONSTER_API_KEY={self._config['services']['captcha']['capmonster_key']}",
            "",
            "# Business Email Services",
            f"RAPIDAPI_KEY={self._config['services']['business_email']['rapidapi_key']}",
            f"HUNTER_API_KEY={self._config['services']['business_email']['hunter_api_key']}",
            "",
            "# Automation Configuration",
            f"AUTOMATION_MAX_SESSIONS={self._config['automation']['max_concurrent_sessions']}",
            f"AUTOMATION_AGGRESSIVENESS={self._config['automation']['aggressiveness_level']}",
            "",
            "# Monitoring Configuration",
            f"MONITORING_ENABLED={str(self._config['monitoring']['enabled']).lower()}",
            f"ALERT_EMAIL={self._config['monitoring']['alert_email']}",
            f"SENTRY_DSN={self._config['monitoring']['sentry_dsn']}",
        ]
        
        return "\n".join(template_lines)
    
    def get_health_check_config(self) -> Dict[str, Any]:
        """Get health check configuration"""
        return {
            'interval_seconds': self._config['monitoring']['health_check_interval'],
            'timeout_seconds': 10,
            'checks': {
                'database': self._config['database']['url'],
                'redis': self._config['redis']['url'],
                'services': list(self.get_service_endpoints().keys())
            }
        }

# Global environment configuration instance
_env_config = None

def get_env_config(environment: Optional[str] = None) -> EnvironmentConfig:
    """Get global environment configuration instance"""
    global _env_config
    if _env_config is None:
        _env_config = EnvironmentConfig(environment)
    return _env_config

def reset_env_config():
    """Reset global environment configuration (useful for testing)"""
    global _env_config
    _env_config = None

if __name__ == "__main__":
    # Test environment configuration
    print("Environment Configuration Test")
    print("=" * 50)
    
    # Test different environments
    for env in ['development', 'staging', 'production']:
        try:
            print(f"\nTesting {env.upper()} environment:")
            
            # Set environment and test
            os.environ['ENVIRONMENT'] = env
            config = EnvironmentConfig(env)
            
            print(f"   App debug: {config.get('app.debug')}")
            print(f"   Server workers: {config.get('server.workers')}")
            print(f"   Database pool: {config.get('database.pool_size')}")
            print(f"   Security 2FA: {config.get('security.require_2fa')}")
            
            # Test service status
            twilio_enabled = config.get('services.twilio.enabled')
            proxy_enabled = config.get('services.brightdata.enabled')
            print(f"   Twilio: {'ENABLED' if twilio_enabled else 'DISABLED'}")
            print(f"   Proxy: {'ENABLED' if proxy_enabled else 'DISABLED'}")
            
            # Test feature flags
            features = config.get_feature_flags()
            enabled_features = [k for k, v in features.items() if v]
            print(f"   Features: {len(enabled_features)}/{len(features)} enabled")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Export template
    print("\nEnvironment Template:")
    config = EnvironmentConfig('development')
    template = config.export_env_template()
    print("   Run this to generate .env.example:")
    print("   python -m automation.config.environment_config > .env.example")