#!/usr/bin/env python3
"""
Real Automation Configuration
Ensures all automation components are properly configured for REAL account creation
"""

import os
import sys
import logging
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealAutomationConfig:
    """Configuration manager for real automation components"""
    
    def __init__(self):
        self.config = self._load_configuration()
        
    def _load_configuration(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        return {
            # Snapchat Configuration
            'snapchat': {
                'enabled': True,
                'girl_usernames_only': True,
                'verification_required': True,
                'warming_enabled': True,
                'add_farming_enabled': True
            },
            
            # Android Configuration  
            'android': {
                'enabled': True,
                'max_concurrent_emulators': 5,
                'emulator_config': 'snapchat_pixel_6_api_30',
                'headless_mode': True,
                'ui_automator_enabled': True
            },
            
            # SMS Configuration
            'sms': {
                'enabled': True,
                'service': 'twilio_pool',
                'verification_timeout': 60,
                'max_retries': 3
            },
            
            # Email Configuration
            'email': {
                'enabled': True,
                'service': 'temp_email_automation',
                'verification_timeout': 120,
                'disposable_emails': True
            },
            
            # Anti-Detection Configuration
            'anti_detection': {
                'enabled': True,
                'behavior_randomization': True,
                'device_fingerprinting': True,
                'timing_randomization': True
            },
            
            # Quality Assurance
            'quality': {
                'test_accounts_before_delivery': True,
                'verify_login_works': True,
                'verify_add_functionality': True,
                'minimum_trust_score': 85
            }
        }
    
    def validate_configuration(self) -> tuple[bool, list[str]]:
        """Validate that all required components are enabled"""
        issues = []
        
        # Check critical components
        critical_components = ['snapchat', 'android', 'sms', 'email']
        for component in critical_components:
            if not self.config.get(component, {}).get('enabled', False):
                issues.append(f"{component.title()} automation is disabled")
        
        # Check environment variables for sensitive data
        required_env_vars = [
            'TWILIO_ACCOUNT_SID',
            'TWILIO_AUTH_TOKEN',
            'TELEGRAM_BOT_TOKEN'
        ]
        
for env_var in required_env_vars:
            try:
                from utils.vault_client import get_secret
                if not get_secret(env_var):
                    issues.append(f"Missing secret: {env_var}")
            except Exception:
                if not os.getenv(env_var):
                    issues.append(f"Missing environment variable: {env_var}")
        
        return len(issues) == 0, issues
    
    def get_snapchat_config(self) -> Dict[str, Any]:
        """Get Snapchat-specific configuration"""
        return self.config.get('snapchat', {})
    
    def get_android_config(self) -> Dict[str, Any]:
        """Get Android automation configuration"""
        return self.config.get('android', {})
    
    def get_sms_config(self) -> Dict[str, Any]:
        """Get SMS verification configuration"""
        return self.config.get('sms', {})
    
    def get_email_config(self) -> Dict[str, Any]:
        """Get email automation configuration"""
        return self.config.get('email', {})
    
    def is_real_automation_enabled(self) -> bool:
        """Check if real automation is fully enabled"""
        valid, issues = self.validate_configuration()
        if not valid:
            logger.warning(f"Real automation not fully enabled: {issues}")
            return False
        return True
    
    def log_configuration_status(self):
        """Log the current configuration status"""
        logger.info("=== REAL AUTOMATION CONFIGURATION ===")
        
        for component, config in self.config.items():
            enabled = config.get('enabled', False)
            status = "✅ ENABLED" if enabled else "❌ DISABLED"
            logger.info(f"{component.upper()}: {status}")
        
        valid, issues = self.validate_configuration()
        if valid:
            logger.info("🚀 ALL SYSTEMS READY FOR REAL AUTOMATION")
        else:
            logger.error("❌ CONFIGURATION ISSUES DETECTED:")
            for issue in issues:
                logger.error(f"  • {issue}")
        
        logger.info("=====================================")

# Global configuration instance
_real_automation_config = None

def get_real_automation_config() -> RealAutomationConfig:
    """Get global real automation configuration"""
    global _real_automation_config
    if _real_automation_config is None:
        _real_automation_config = RealAutomationConfig()
    return _real_automation_config

def validate_real_automation_ready() -> tuple[bool, str]:
    """Validate that real automation is ready to operate"""
    config = get_real_automation_config()
    
    if not config.is_real_automation_enabled():
        valid, issues = config.validate_configuration()
        error_msg = (
            "❌ **REAL AUTOMATION NOT READY**\n\n"
            "Issues detected:\n" + 
            "\n".join(f"• {issue}" for issue in issues) +
            "\n\n🚫 **NO ACCOUNTS WILL BE CREATED**\n"
            "⚙️ Please fix configuration issues first."
        )
        return False, error_msg
    
    return True, "✅ Real automation validated and ready"

if __name__ == "__main__":
    # Test configuration
    config = get_real_automation_config()
    config.log_configuration_status()
    
    ready, message = validate_real_automation_ready()
    print(f"\nValidation Result: {message}")