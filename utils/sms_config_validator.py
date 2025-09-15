#!/usr/bin/env python3
"""
SMS Configuration Validator and Setup Assistant

Validates SMS service configuration and provides detailed setup guidance.
"""

import os
import sys
import logging
import json
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SMSConfigValidator:
    """Comprehensive SMS configuration validator with setup assistance"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.recommendations = []
        self.status = {
            'twilio_credentials': False,
            'redis_connection': False,
            'configuration_valid': False,
            'ready_for_production': False
        }
        
    def validate_all(self) -> Dict[str, any]:
        """Run comprehensive SMS configuration validation"""
        logger.info("🔍 Starting SMS configuration validation...")
        
        # Clear previous results
        self.errors.clear()
        self.warnings.clear()
        self.recommendations.clear()
        
        # Run all validation checks
        self._validate_twilio_credentials()
        self._validate_redis_configuration()
        self._validate_environment_variables()
        self._validate_rate_limiting_config()
        self._validate_security_settings()
        self._test_service_connectivity()
        
        # Determine overall status
        self._calculate_overall_status()
        
        # Generate report
        report = self._generate_report()
        
        # Display results
        self._display_results()
        
        return report
    
    def _validate_twilio_credentials(self):
        """Validate Twilio credentials format and availability"""
        try:
            account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
            auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
            
            if not account_sid:
                self.errors.append({
                    'category': 'Twilio Credentials',
                    'issue': 'TWILIO_ACCOUNT_SID not set',
                    'solution': 'export TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"'
                })
                return
            
            if not auth_token:
                self.errors.append({
                    'category': 'Twilio Credentials',
                    'issue': 'TWILIO_AUTH_TOKEN not set',
                    'solution': 'export TWILIO_AUTH_TOKEN="your_auth_token_here"'
                })
                return
            
            # Validate Account SID format
            if not account_sid.startswith('AC') or len(account_sid) != 34:
                self.errors.append({
                    'category': 'Twilio Credentials',
                    'issue': f'Invalid TWILIO_ACCOUNT_SID format: {account_sid[:10]}...',
                    'solution': 'Account SID should start with "AC" and be 34 characters long'
                })
            
            # Validate Auth Token format
            if len(auth_token) < 32:
                self.errors.append({
                    'category': 'Twilio Credentials',
                    'issue': 'TWILIO_AUTH_TOKEN too short',
                    'solution': 'Auth token should be at least 32 characters long'
                })
            
            # Test credentials if format is valid
            if account_sid.startswith('AC') and len(auth_token) >= 32:
                self._test_twilio_credentials(account_sid, auth_token)
            
        except Exception as e:
            self.errors.append({
                'category': 'Twilio Credentials',
                'issue': f'Error validating credentials: {str(e)}',
                'solution': 'Check environment variables are properly set'
            })
    
    def _test_twilio_credentials(self, account_sid: str, auth_token: str):
        """Test Twilio credentials by making API call"""
        try:
            from twilio.rest import Client
            from twilio.base.exceptions import TwilioException
            
            client = Client(account_sid, auth_token)
            
            # Test credentials by fetching account info
            account = client.api.accounts(account_sid).fetch()
            
            self.status['twilio_credentials'] = True
            logger.info(f"✅ Twilio credentials valid - Account: {account.friendly_name}")
            
            # Check account status
            if account.status != 'active':
                self.warnings.append({
                    'category': 'Twilio Account',
                    'issue': f'Account status: {account.status}',
                    'solution': 'Ensure your Twilio account is active and in good standing'
                })
            
            # Check account type
            if account.type == 'Trial':
                self.warnings.append({
                    'category': 'Twilio Account',
                    'issue': 'Using Trial account - limited functionality',
                    'solution': 'Upgrade to paid account for full SMS capabilities'
                })
            
            # Test phone number availability
            try:
                available_numbers = client.available_phone_numbers('US').local.list(limit=1)
                if not available_numbers:
                    self.warnings.append({
                        'category': 'Twilio Phone Numbers',
                        'issue': 'No available phone numbers found',
                        'solution': 'Check if your account has phone number purchase capability'
                    })
                else:
                    logger.info("✅ Phone numbers available for purchase")
            except Exception as phone_error:
                self.warnings.append({
                    'category': 'Twilio Phone Numbers',
                    'issue': f'Cannot check phone availability: {phone_error}',
                    'solution': 'May need to verify account or add billing information'
                })
            
        except TwilioException as e:
            self.errors.append({
                'category': 'Twilio API',
                'issue': f'Twilio API error: {str(e)}',
                'solution': 'Check credentials are correct and account is active'
            })
        except ImportError:
            self.errors.append({
                'category': 'Dependencies',
                'issue': 'twilio package not installed',
                'solution': 'pip install twilio'
            })
        except Exception as e:
            self.errors.append({
                'category': 'Twilio Connection',
                'issue': f'Connection error: {str(e)}',
                'solution': 'Check internet connection and firewall settings'
            })
    
    def _validate_redis_configuration(self):
        """Validate Redis configuration and connectivity"""
        try:
            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
            
            try:
                import redis
                
                # Test Redis connection
                redis_client = redis.from_url(redis_url, decode_responses=True)
                redis_client.ping()
                
                self.status['redis_connection'] = True
                logger.info(f"✅ Redis connection successful: {redis_url}")
                
                # Test Redis operations
                test_key = f"sms_test_{int(datetime.now().timestamp())}"
                redis_client.set(test_key, "test_value", ex=10)
                test_value = redis_client.get(test_key)
                redis_client.delete(test_key)
                
                if test_value == "test_value":
                    logger.info("✅ Redis read/write operations working")
                else:
                    self.warnings.append({
                        'category': 'Redis Operations',
                        'issue': 'Redis read/write test failed',
                        'solution': 'Check Redis server configuration'
                    })
                
            except ImportError:
                self.errors.append({
                    'category': 'Dependencies',
                    'issue': 'redis package not installed',
                    'solution': 'pip install redis'
                })
            except redis.ConnectionError:
                self.errors.append({
                    'category': 'Redis Connection',
                    'issue': f'Cannot connect to Redis at {redis_url}',
                    'solution': 'Start Redis server: redis-server OR update REDIS_URL'
                })
            except Exception as e:
                self.errors.append({
                    'category': 'Redis',
                    'issue': f'Redis error: {str(e)}',
                    'solution': 'Check Redis server status and configuration'
                })
                
        except Exception as e:
            self.errors.append({
                'category': 'Redis Configuration',
                'issue': f'Configuration error: {str(e)}',
                'solution': 'Check REDIS_URL environment variable'
            })
    
    def _validate_environment_variables(self):
        """Validate all required environment variables"""
        required_vars = {
            'REDIS_URL': 'redis://localhost:6379',
            'TWILIO_AREA_CODE': '720'
        }
        
        optional_vars = {
            'SMS_WEBHOOK_BASE_URL': 'Webhook URL for SMS status updates',
            'SMS_RATE_LIMIT_PER_HOUR': '5',
            'SMS_RATE_LIMIT_PER_DAY': '20',
            'SMS_DAILY_COST_LIMIT': '50.0',
            'SMS_CODE_EXPIRY_MINUTES': '10'
        }
        
        # Check required variables
        for var, default in required_vars.items():
            value = os.environ.get(var)
            if not value:
                self.warnings.append({
                    'category': 'Environment Variables',
                    'issue': f'{var} not set, using default: {default}',
                    'solution': f'export {var}="{default}"'
                })
        
        # Check optional variables
        for var, description in optional_vars.items():
            value = os.environ.get(var)
            if not value:
                self.recommendations.append({
                    'category': 'Optional Configuration',
                    'suggestion': f'Consider setting {var}',
                    'benefit': description
                })
    
    def _validate_rate_limiting_config(self):
        """Validate rate limiting configuration"""
        try:
            max_hourly = int(os.environ.get('SMS_RATE_LIMIT_PER_HOUR', '5'))
            max_daily = int(os.environ.get('SMS_RATE_LIMIT_PER_DAY', '20'))
            
            if max_hourly > max_daily:
                self.warnings.append({
                    'category': 'Rate Limiting',
                    'issue': 'Hourly limit exceeds daily limit',
                    'solution': 'Ensure daily limit >= hourly limit'
                })
            
            if max_hourly > 10:
                self.warnings.append({
                    'category': 'Rate Limiting',
                    'issue': 'High hourly rate limit may trigger carrier blocking',
                    'solution': 'Consider reducing hourly limit for better deliverability'
                })
                
        except ValueError as e:
            self.errors.append({
                'category': 'Rate Limiting',
                'issue': f'Invalid rate limiting values: {e}',
                'solution': 'Ensure rate limit values are valid integers'
            })
    
    def _validate_security_settings(self):
        """Validate security configuration"""
        webhook_secret = os.environ.get('SMS_WEBHOOK_SECRET')
        
        if not webhook_secret:
            self.recommendations.append({
                'category': 'Security',
                'suggestion': 'Set SMS_WEBHOOK_SECRET for webhook validation',
                'benefit': 'Prevents unauthorized webhook calls'
            })
        elif len(webhook_secret) < 32:
            self.warnings.append({
                'category': 'Security',
                'issue': 'SMS_WEBHOOK_SECRET too short',
                'solution': 'Use at least 32 characters for webhook secret'
            })
    
    def _test_service_connectivity(self):
        """Test SMS service connectivity without sending actual messages"""
        if not self.status['twilio_credentials'] or not self.status['redis_connection']:
            return
        
        try:
            # Import and test SMS services
            from .twilio_pool import TwilioPhonePool
            
            # Test pool initialization
            pool = TwilioPhonePool()
            
            if pool.credentials_available:
                logger.info("✅ SMS service pool initialized successfully")
                
                # Get pool status
                status = pool.get_pool_status()
                logger.info(f"📊 Pool status: {status['pool_health']['available_count']} available, "
                           f"{status['pool_health']['health_score']}% health")
                
            else:
                self.errors.append({
                    'category': 'SMS Service',
                    'issue': 'SMS pool initialization failed',
                    'solution': 'Check Twilio credentials and Redis connection'
                })
                
        except ImportError as e:
            self.errors.append({
                'category': 'Dependencies',
                'issue': f'Cannot import SMS services: {e}',
                'solution': 'Ensure all SMS modules are properly installed'
            })
        except Exception as e:
            self.errors.append({
                'category': 'SMS Service',
                'issue': f'Service test failed: {e}',
                'solution': 'Check SMS service configuration and dependencies'
            })
    
    def _calculate_overall_status(self):
        """Calculate overall system status"""
        self.status['configuration_valid'] = len(self.errors) == 0
        self.status['ready_for_production'] = (
            len(self.errors) == 0 and 
            len(self.warnings) <= 2 and
            self.status['twilio_credentials'] and 
            self.status['redis_connection']
        )
    
    def _generate_report(self) -> Dict[str, any]:
        """Generate comprehensive status report"""
        return {
            'timestamp': datetime.now().isoformat(),
            'overall_status': {
                'configuration_valid': self.status['configuration_valid'],
                'ready_for_production': self.status['ready_for_production'],
                'sms_enabled': self.status['twilio_credentials'] and self.status['redis_connection']
            },
            'component_status': self.status,
            'issues': {
                'errors': self.errors,
                'warnings': self.warnings,
                'recommendations': self.recommendations
            },
            'summary': {
                'error_count': len(self.errors),
                'warning_count': len(self.warnings),
                'recommendation_count': len(self.recommendations)
            }
        }
    
    def _display_results(self):
        """Display validation results in a user-friendly format"""
        print("\n" + "="*80)
        print("📱 SMS CONFIGURATION VALIDATION REPORT")
        print("="*80)
        
        # Overall status
        if self.status['ready_for_production']:
            print("🎉 STATUS: READY FOR PRODUCTION")
            print("✅ All critical components are properly configured")
        elif self.status['configuration_valid']:
            print("⚡ STATUS: FUNCTIONAL (with warnings)")
            print("✅ SMS functionality is available but needs attention")
        else:
            print("❌ STATUS: CONFIGURATION ERRORS")
            print("🔧 SMS functionality is disabled - fix errors below")
        
        print(f"\n📊 Component Status:")
        print(f"   Twilio Credentials: {'✅ Valid' if self.status['twilio_credentials'] else '❌ Invalid'}")
        print(f"   Redis Connection:   {'✅ Connected' if self.status['redis_connection'] else '❌ Failed'}")
        print(f"   Configuration:      {'✅ Valid' if self.status['configuration_valid'] else '❌ Errors'}")
        
        # Display errors
        if self.errors:
            print(f"\n🚨 ERRORS ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                print(f"   {i}. [{error['category']}] {error['issue']}")
                print(f"      Solution: {error['solution']}")
        
        # Display warnings
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"   {i}. [{warning['category']}] {warning['issue']}")
                print(f"      Solution: {warning['solution']}")
        
        # Display recommendations
        if self.recommendations:
            print(f"\n💡 RECOMMENDATIONS ({len(self.recommendations)}):")
            for i, rec in enumerate(self.recommendations, 1):
                print(f"   {i}. [{rec['category']}] {rec['suggestion']}")
                print(f"      Benefit: {rec['benefit']}")
        
        # Next steps
        print(f"\n🎯 NEXT STEPS:")
        if self.errors:
            print("   1. Fix all errors listed above")
            print("   2. Re-run validation: python -m utils.sms_config_validator")
            print("   3. Test SMS functionality")
        elif self.warnings:
            print("   1. Address warnings for optimal performance")
            print("   2. Test SMS functionality: python -m utils.test_sms_verifier")
        else:
            print("   1. Configuration looks good!")
            print("   2. Test SMS functionality: python -m utils.test_sms_verifier")
        
        print("\n" + "="*80)

def main():
    """Run SMS configuration validation"""
    try:
        validator = SMSConfigValidator()
        report = validator.validate_all()
        
        # Save report to file
        report_file = f"sms_config_report_{int(datetime.now().timestamp())}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Full report saved to: {report_file}")
        
        # Exit with appropriate code
        if report['overall_status']['configuration_valid']:
            sys.exit(0)  # Success
        else:
            sys.exit(1)  # Errors found
            
    except KeyboardInterrupt:
        print("\n❌ Validation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Validation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()