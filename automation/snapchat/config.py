#!/usr/bin/env python3
"""
Configuration Management for Snapchat Automation

Centralized configuration with environment variable validation and fallbacks.
"""

import os
import tempfile
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SnapchatConfig:
    """Configuration for Snapchat automation"""
    
    # APK Management
    apk_artifacts_dir: str
    apk_cache_dir: str
    
    # Device Farm
    farm_devices_config: Optional[str]
    farm_host: str
    farm_port_range: tuple
    
    # Twilio Configuration
    twilio_account_sid: Optional[str]
    twilio_auth_token: Optional[str]
    
    # Paths and Directories
    temp_dir: str
    screenshot_dir: str
    logs_dir: str
    
    # UI Automation
    max_retries: int
    base_delay: float
    max_delay: float
    
    # Security
    enable_apk_verification: bool
    enable_captcha_detection: bool
    
    # Performance
    max_concurrent_devices: int
    connection_timeout: int


class ConfigurationManager:
    """Manages configuration with validation and fallbacks"""
    
    def __init__(self):
        self.config = self._load_configuration()
        self._validate_configuration()
        self._ensure_directories()
    
    def _load_configuration(self) -> SnapchatConfig:
        """Load configuration from environment variables with fallbacks"""
        
        # Get base directories
        base_dir = Path.cwd()
        temp_base = Path(tempfile.gettempdir())
        
        # APK Management
        apk_artifacts_dir = os.environ.get(
            'SNAPCHAT_APK_ARTIFACTS_DIR',
            str(base_dir / 'artifacts' / 'apks')
        )
        apk_cache_dir = os.environ.get(
            'SNAPCHAT_APK_CACHE_DIR',
            str(base_dir / 'cache' / 'apks')
        )
        
        # Device Farm
        farm_devices_config = os.environ.get('FARM_DEVICES_CONFIG')
        farm_host = os.environ.get('FARM_HOST', 'localhost')
        farm_port_start = int(os.environ.get('FARM_PORT_START', '5555'))
        farm_port_end = int(os.environ.get('FARM_PORT_END', '5565'))
        
        # Twilio
        twilio_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        twilio_token = os.environ.get('TWILIO_AUTH_TOKEN')
        
        # Paths
        temp_dir = os.environ.get(
            'SNAPCHAT_TEMP_DIR',
            str(temp_base / 'snapchat_automation')
        )
        screenshot_dir = os.environ.get(
            'SNAPCHAT_SCREENSHOT_DIR',
            str(temp_base / 'snapchat_screenshots')
        )
        logs_dir = os.environ.get(
            'SNAPCHAT_LOGS_DIR',
            str(base_dir / 'logs')
        )
        
        # UI Automation
        max_retries = int(os.environ.get('SNAPCHAT_MAX_RETRIES', '3'))
        base_delay = float(os.environ.get('SNAPCHAT_BASE_DELAY', '1.0'))
        max_delay = float(os.environ.get('SNAPCHAT_MAX_DELAY', '10.0'))
        
        # Security
        enable_apk_verification = os.environ.get('ENABLE_APK_VERIFICATION', 'true').lower() == 'true'
        enable_captcha_detection = os.environ.get('ENABLE_CAPTCHA_DETECTION', 'true').lower() == 'true'
        
        # Performance
        max_concurrent_devices = int(os.environ.get('MAX_CONCURRENT_DEVICES', '10'))
        connection_timeout = int(os.environ.get('CONNECTION_TIMEOUT', '30'))
        
        return SnapchatConfig(
            apk_artifacts_dir=apk_artifacts_dir,
            apk_cache_dir=apk_cache_dir,
            farm_devices_config=farm_devices_config,
            farm_host=farm_host,
            farm_port_range=(farm_port_start, farm_port_end),
            twilio_account_sid=twilio_sid,
            twilio_auth_token=twilio_token,
            temp_dir=temp_dir,
            screenshot_dir=screenshot_dir,
            logs_dir=logs_dir,
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
            enable_apk_verification=enable_apk_verification,
            enable_captcha_detection=enable_captcha_detection,
            max_concurrent_devices=max_concurrent_devices,
            connection_timeout=connection_timeout
        )
    
    def _validate_configuration(self):
        """Validate configuration and log warnings for missing optional components"""
        warnings = []
        errors = []
        
        # Validate Twilio configuration
        if not self.config.twilio_account_sid or not self.config.twilio_auth_token:
            warnings.append("Twilio credentials not configured - SMS verification will be disabled")
        
        # Validate farm configuration
        if not self.config.farm_devices_config:
            warnings.append("Farm devices config not provided - using localhost discovery")
        
        # Validate directory paths
        try:
            Path(self.config.apk_artifacts_dir).parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create APK artifacts directory: {e}")
        
        # Log validation results
        if warnings:
            for warning in warnings:
                logger.warning(f"Configuration warning: {warning}")
        
        if errors:
            for error in errors:
                logger.error(f"Configuration error: {error}")
            raise RuntimeError(f"Configuration validation failed: {errors}")
        
        logger.info("Configuration validation completed successfully")
    
    def _ensure_directories(self):
        """Ensure all required directories exist"""
        directories = [
            self.config.apk_artifacts_dir,
            self.config.apk_cache_dir,
            self.config.temp_dir,
            self.config.screenshot_dir,
            self.config.logs_dir
        ]
        
        for directory in directories:
            try:
                Path(directory).mkdir(parents=True, exist_ok=True)
                logger.debug(f"Ensured directory exists: {directory}")
            except Exception as e:
                logger.error(f"Failed to create directory {directory}: {e}")
    
    def get_screenshot_path(self, device_id: str, timestamp: str = None) -> str:
        """Generate screenshot path with proper naming"""
        if timestamp is None:
            import time
            timestamp = str(int(time.time()))
        
        filename = f"snapchat_{device_id}_{timestamp}.png"
        return str(Path(self.config.screenshot_dir) / filename)
    
    def get_temp_file_path(self, filename: str) -> str:
        """Generate temporary file path"""
        return str(Path(self.config.temp_dir) / filename)
    
    def is_twilio_enabled(self) -> bool:
        """Check if Twilio is properly configured"""
        return bool(self.config.twilio_account_sid and self.config.twilio_auth_token)
    
    def is_farm_configured(self) -> bool:
        """Check if device farm is configured"""
        return bool(self.config.farm_devices_config)
    
    def get_farm_device_addresses(self) -> List[str]:
        """Get list of farm device addresses"""
        addresses = []
        start_port, end_port = self.config.farm_port_range
        
        for port in range(start_port, end_port + 1):
            addresses.append(f"{self.config.farm_host}:{port}")
        
        return addresses
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for logging"""
        config_dict = {}
        
        for field_name in self.config.__dataclass_fields__:
            value = getattr(self.config, field_name)
            
            # Mask sensitive values
            if 'token' in field_name.lower() or 'sid' in field_name.lower():
                if value:
                    config_dict[field_name] = f"***{value[-4:]}" if len(value) > 4 else "***"
                else:
                    config_dict[field_name] = None
            else:
                config_dict[field_name] = value
        
        return config_dict


# Global configuration instance
_config_manager = None


def get_config() -> ConfigurationManager:
    """Get global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager()
    return _config_manager


def reload_config() -> ConfigurationManager:
    """Reload configuration (useful for testing)"""
    global _config_manager
    _config_manager = ConfigurationManager()
    return _config_manager


if __name__ == "__main__":
    # Configuration testing and validation
    import json
    
    try:
        config_manager = get_config()
        config_dict = config_manager.to_dict()
        
        print("Configuration loaded successfully:")
        print(json.dumps(config_dict, indent=2))
        
        print(f"\nTwilio enabled: {config_manager.is_twilio_enabled()}")
        print(f"Farm configured: {config_manager.is_farm_configured()}")
        print(f"Farm addresses: {config_manager.get_farm_device_addresses()[:3]}...")  # Show first 3
        
        # Test path generation
        screenshot_path = config_manager.get_screenshot_path("test_device")
        temp_path = config_manager.get_temp_file_path("test.tmp")
        
        print(f"\nPath generation:")
        print(f"Screenshot: {screenshot_path}")
        print(f"Temp file: {temp_path}")
        
    except Exception as e:
        print(f"Configuration failed: {e}")
        exit(1)