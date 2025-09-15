#!/usr/bin/env python3
"""
Automation Configuration Package
Centralized configuration management for all automation services

This package provides:
- ConfigManager: Main configuration management with validation
- CredentialsManager: Secure credential storage with encryption  
- EnvironmentConfig: Environment-specific configuration
- Validation: Comprehensive configuration validation

Usage:
    from automation.config import get_config, get_credentials
    
    config = get_config()
    db_config = config.get_database_config()
    
    creds = get_credentials()
    twilio_creds = creds.get_twilio_credentials()
"""

__version__ = "2.0.0"

import os
import sys
import logging
from typing import Dict, Any, Optional

# Import main components
try:
    from .config_manager import ConfigManager, get_config, reset_config
    from .credentials_manager import CredentialsManager, get_credentials, reset_credentials
    from .environment_config import EnvironmentConfig, get_env_config, reset_env_config
    from .validation import ConfigurationValidator
except ImportError as e:
    logging.error(f"Failed to import configuration components: {e}")
    # Fallback to basic configuration
    ConfigManager = None
    CredentialsManager = None
    EnvironmentConfig = None
    ConfigurationValidator = None

# Backward compatibility - legacy configuration defaults
DEFAULT_CONFIG = {
    'automation': {
        'aggressiveness': 0.3,
        'session_duration_minutes': 15,
        'break_duration_minutes': 60,
        'max_concurrent_sessions': 3,
        'anti_detection_enabled': True
    },
    'proxy': {
        'verification_interval': 300,
        'timeout': 30,
        'max_sessions': 10
    },
    'captcha': {
        'daily_limit': 50.0,
        'timeout': 120,
        'max_retry_attempts': 3
    },
    'database': {
        'pool_size': 10,
        'max_overflow': 20,
        'pool_timeout': 30,
        'echo': False
    },
    'redis': {
        'max_connections': 20,
        'socket_timeout': 5,
        'decode_responses': True
    },
    'security': {
        'jwt_expiry_hours': 24,
        'max_login_attempts': 5,
        'session_timeout_minutes': 30,
        'rate_limit_per_minute': 60
    }
}

def get_legacy_config() -> Dict[str, Any]:
    """Get legacy configuration with environment overrides (backward compatibility)"""
    config = DEFAULT_CONFIG.copy()
    
    # Override with environment variables
    if os.environ.get('AUTOMATION_AGGRESSIVENESS'):
        try:
            config['automation']['aggressiveness'] = float(os.environ.get('AUTOMATION_AGGRESSIVENESS'))
        except ValueError:
            pass
    
    if os.environ.get('CAPTCHA_DAILY_LIMIT'):
        try:
            config['captcha']['daily_limit'] = float(os.environ.get('CAPTCHA_DAILY_LIMIT'))
        except ValueError:
            pass
    
    if os.environ.get('DATABASE_POOL_SIZE'):
        try:
            config['database']['pool_size'] = int(os.environ.get('DATABASE_POOL_SIZE'))
        except ValueError:
            pass
    
    if os.environ.get('REDIS_MAX_CONNECTIONS'):
        try:
            config['redis']['max_connections'] = int(os.environ.get('REDIS_MAX_CONNECTIONS'))
        except ValueError:
            pass
    
    return config

def validate_configuration(environment: str = 'development') -> Dict[str, Any]:
    """Validate current configuration and return report"""
    if ConfigurationValidator:
        validator = ConfigurationValidator(environment)
        report = validator.validate_all()
        return {
            'valid': report.overall_status == 'valid',
            'status': report.overall_status,
            'summary': report.summary,
            'errors': [r for r in report.results if r.status == 'error'],
            'warnings': [r for r in report.results if r.status == 'warning']
        }
    else:
        return {
            'valid': False,
            'status': 'error',
            'summary': {'error': 1},
            'errors': [{'message': 'Configuration validation system not available'}],
            'warnings': []
        }

def setup_configuration(environment: Optional[str] = None, 
                       master_password: Optional[str] = None) -> Dict[str, Any]:
    """Set up complete configuration system"""
    setup_status = {
        'config_manager': False,
        'credentials_manager': False,
        'environment_config': False,
        'errors': []
    }
    
    try:
        # Initialize configuration manager
        if ConfigManager:
            config = get_config(environment)
            setup_status['config_manager'] = True
        else:
            setup_status['errors'].append('ConfigManager not available')
        
        # Initialize credentials manager
        if CredentialsManager:
            creds = get_credentials(master_password)
            setup_status['credentials_manager'] = True
        else:
            setup_status['errors'].append('CredentialsManager not available')
        
        # Initialize environment config
        if EnvironmentConfig:
            env_config = get_env_config(environment)
            setup_status['environment_config'] = True
        else:
            setup_status['errors'].append('EnvironmentConfig not available')
        
    except Exception as e:
        setup_status['errors'].append(f'Setup error: {str(e)}')
    
    return setup_status

def health_check() -> Dict[str, Any]:
    """Perform health check on configuration system"""
    health = {
        'healthy': True,
        'components': {},
        'errors': []
    }
    
    try:
        # Check config manager
        if ConfigManager:
            config = get_config()
            config_health = config.health_check()
            health['components']['config_manager'] = config_health['healthy']
            if not config_health['healthy']:
                health['healthy'] = False
        
        # Check credentials manager  
        if CredentialsManager:
            creds = get_credentials()
            creds_health = creds.health_check()
            health['components']['credentials_manager'] = creds_health['healthy']
            if not creds_health['healthy']:
                health['healthy'] = False
        
        # Basic environment checks
        required_env_vars = ['DATABASE_URL', 'REDIS_URL', 'JWT_SECRET']
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_vars:
            health['healthy'] = False
            health['errors'].append(f'Missing environment variables: {missing_vars}')
        
    except Exception as e:
        health['healthy'] = False
        health['errors'].append(f'Health check error: {str(e)}')
    
    return health

def export_env_template(include_secrets: bool = False) -> str:
    """Export environment template for configuration"""
    if ConfigManager:
        config = get_config()
        return config.export_config_template(include_secrets)
    elif EnvironmentConfig:
        env_config = get_env_config()
        return env_config.export_env_template()
    else:
        # Basic template fallback
        return """# Basic Configuration Template
# DATABASE_URL=postgresql://user:password@localhost/automation
# REDIS_URL=redis://localhost:6379
# JWT_SECRET=your_jwt_secret_here
# ENCRYPTION_KEY=your_encryption_key_here
"""

# Public API
__all__ = [
    # Main classes
    'ConfigManager',
    'CredentialsManager', 
    'EnvironmentConfig',
    'ConfigurationValidator',
    
    # Factory functions
    'get_config',
    'get_credentials',
    'get_env_config',
    
    # Utility functions
    'validate_configuration',
    'setup_configuration',
    'health_check',
    'export_env_template',
    
    # Legacy support
    'get_legacy_config',
    'DEFAULT_CONFIG',
    
    # Reset functions (for testing)
    'reset_config',
    'reset_credentials', 
    'reset_env_config'
]

# Initialize logging for the configuration package
logging.getLogger(__name__).addHandler(logging.NullHandler())