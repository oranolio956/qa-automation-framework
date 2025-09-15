#!/usr/bin/env python3
"""
Configuration Setup and Validation Script
Comprehensive setup tool for the Tinder automation system configuration

This script:
1. Validates current configuration
2. Sets up missing configuration files  
3. Initializes secure credential storage
4. Tests all service connections
5. Generates environment templates
"""

import os
import sys
import json
import logging
import argparse
import getpass
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv(project_root / '.env')
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️  python-dotenv not available, environment variables must be set manually")
    pass
except Exception as e:
    print(f"⚠️  Failed to load .env file: {e}")

try:
    from automation.config import (
        validate_configuration, 
        setup_configuration,
        health_check,
        export_env_template,
        get_config,
        get_credentials,
        ConfigurationValidator
    )
except ImportError as e:
    print(f"❌ Failed to import configuration modules: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('setup_configuration.log')
    ]
)
logger = logging.getLogger(__name__)

class ConfigurationSetup:
    """Main configuration setup coordinator"""
    
    def __init__(self, environment: str = 'development', interactive: bool = True):
        self.environment = environment
        self.interactive = interactive
        self.project_root = project_root
        self.setup_results = {
            'validation': None,
            'credentials': None,
            'services': None,
            'files_created': [],
            'errors': [],
            'warnings': []
        }
    
    def run_complete_setup(self) -> Dict[str, Any]:
        """Run complete configuration setup process"""
        print("🚀 Starting Tinder Automation Configuration Setup")
        print("=" * 60)
        print(f"Environment: {self.environment.upper()}")
        print(f"Project Root: {self.project_root}")
        print("")
        
        try:
            # Step 1: Initial validation
            self._step_validate_current_config()
            
            # Step 2: Setup environment files
            self._step_setup_environment_files()
            
            # Step 3: Initialize credentials system
            self._step_setup_credentials()
            
            # Step 4: Test service connections
            self._step_test_services()
            
            # Step 5: Final validation
            self._step_final_validation()
            
            # Step 6: Generate summary
            self._generate_setup_summary()
            
        except KeyboardInterrupt:
            print("\\n❌ Setup cancelled by user")
            return self.setup_results
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            self.setup_results['errors'].append(f"Setup failed: {str(e)}")
            print(f"❌ Setup failed: {e}")
        
        return self.setup_results
    
    def _step_validate_current_config(self):
        """Step 1: Validate current configuration"""
        print("🔍 Step 1: Validating Current Configuration")
        print("-" * 40)
        
        try:
            # Run validation
            if ConfigurationValidator:
                validator = ConfigurationValidator(self.environment)
                report = validator.validate_all()
                self.setup_results['validation'] = report
                
                # Show summary
                print(f"   Overall Status: {report.overall_status.upper()}")
                print(f"   Valid: {report.summary.get('valid', 0)}")
                print(f"   Warnings: {report.summary.get('warning', 0)}")
                print(f"   Errors: {report.summary.get('error', 0)}")
                
                if report.summary.get('error', 0) > 0:
                    print("   ⚠️  Configuration has errors that need fixing")
                
            else:
                print("   ❌ Configuration validator not available")
                self.setup_results['errors'].append("Configuration validator not available")
            
        except Exception as e:
            error_msg = f"Validation failed: {str(e)}"
            self.setup_results['errors'].append(error_msg)
            print(f"   ❌ {error_msg}")
        
        print()
    
    def _step_setup_environment_files(self):
        """Step 2: Setup environment configuration files"""
        print("📁 Step 2: Setting Up Environment Files")
        print("-" * 40)
        
        # Check if .env exists
        env_file = self.project_root / '.env'
        env_example_file = self.project_root / '.env.example'
        
        # Create .env.example if it doesn't exist
        if not env_example_file.exists():
            try:
                template = export_env_template(include_secrets=False)
                with open(env_example_file, 'w') as f:
                    f.write(template)
                print(f"   ✅ Created {env_example_file}")
                self.setup_results['files_created'].append(str(env_example_file))
            except Exception as e:
                error_msg = f"Failed to create .env.example: {str(e)}"
                self.setup_results['errors'].append(error_msg)
                print(f"   ❌ {error_msg}")
        else:
            print(f"   ✅ {env_example_file} already exists")
        
        # Handle .env file
        if not env_file.exists():
            if self.interactive:
                create_env = input("   📝 .env file doesn't exist. Create it? (y/N): ").lower().strip()
                if create_env in ('y', 'yes'):
                    try:
                        # Copy from example with secure secrets
                        template = export_env_template(include_secrets=True)
                        with open(env_file, 'w') as f:
                            f.write(template)
                        print(f"   ✅ Created {env_file} with secure defaults")
                        self.setup_results['files_created'].append(str(env_file))
                        
                        print("   ⚠️  IMPORTANT: Update the credentials in .env with your actual values")
                    except Exception as e:
                        error_msg = f"Failed to create .env: {str(e)}"
                        self.setup_results['errors'].append(error_msg)
                        print(f"   ❌ {error_msg}")
                else:
                    print("   ℹ️  .env file not created. You'll need to set environment variables manually")
            else:
                print("   ⚠️  .env file doesn't exist (non-interactive mode)")
        else:
            print(f"   ✅ {env_file} exists")
        
        # Create config directory structure
        config_dirs = [
            self.project_root / 'automation' / 'config',
            self.project_root / 'logs'
        ]
        
        for config_dir in config_dirs:
            if not config_dir.exists():
                try:
                    config_dir.mkdir(parents=True, exist_ok=True)
                    print(f"   ✅ Created directory {config_dir}")
                    self.setup_results['files_created'].append(str(config_dir))
                except Exception as e:
                    error_msg = f"Failed to create {config_dir}: {str(e)}"
                    self.setup_results['errors'].append(error_msg)
                    print(f"   ❌ {error_msg}")
        
        print()
    
    def _step_setup_credentials(self):
        """Step 3: Initialize credentials system"""
        print("🔐 Step 3: Setting Up Secure Credentials System")
        print("-" * 40)
        
        try:
            # Ask for master password if interactive
            master_password = None
            if self.interactive:
                use_encryption = input("   🔒 Use encrypted credential storage? (Y/n): ").lower().strip()
                if use_encryption not in ('n', 'no'):
                    master_password = getpass.getpass("   Enter master password for credential encryption: ").strip()
                    if not master_password:
                        print("   ℹ️  No master password provided, credentials will be stored unencrypted")
            
            # Initialize credentials manager
            setup_status = setup_configuration(
                environment=self.environment,
                master_password=master_password
            )
            
            self.setup_results['credentials'] = setup_status
            
            # Report setup status
            for component, status in setup_status.items():
                if component != 'errors':
                    status_icon = "✅" if status else "❌"
                    component_name = component.replace('_', ' ').title()
                    print(f"   {status_icon} {component_name}: {'Ready' if status else 'Failed'}")
            
            if setup_status['errors']:
                for error in setup_status['errors']:
                    print(f"   ❌ {error}")
                    self.setup_results['errors'].extend(setup_status['errors'])
            
            # Test credentials system
            if setup_status.get('credentials_manager'):
                creds = get_credentials(master_password)
                health = creds.health_check()
                
                if health['healthy']:
                    print("   ✅ Credentials system health check passed")
                else:
                    for error in health.get('errors', []):
                        print(f"   ⚠️  Credentials health issue: {error}")
                        self.setup_results['warnings'].append(f"Credentials: {error}")
        
        except Exception as e:
            error_msg = f"Credentials setup failed: {str(e)}"
            self.setup_results['errors'].append(error_msg)
            print(f"   ❌ {error_msg}")
        
        print()
    
    def _step_test_services(self):
        """Step 4: Test service connections"""
        print("🔌 Step 4: Testing Service Connections")
        print("-" * 40)
        
        try:
            # Get configuration
            config = get_config(self.environment)
            
            # Test database connection
            self._test_database_connection(config)
            
            # Test Redis connection  
            self._test_redis_connection(config)
            
            # Test Twilio if configured
            self._test_twilio_connection(config)
            
            # Test proxy if configured
            self._test_proxy_connection(config)
            
            # Overall service health check
            health = health_check()
            self.setup_results['services'] = health
            
            if health['healthy']:
                print("   ✅ Overall service health: HEALTHY")
            else:
                print("   ⚠️  Overall service health: ISSUES FOUND")
                for error in health.get('errors', []):
                    print(f"      - {error}")
                    self.setup_results['warnings'].append(f"Service health: {error}")
        
        except Exception as e:
            error_msg = f"Service testing failed: {str(e)}"
            self.setup_results['errors'].append(error_msg)
            print(f"   ❌ {error_msg}")
        
        print()
    
    def _test_database_connection(self, config):
        """Test database connection"""
        try:
            db_config = config.get_database_config()
            print(f"   🗄️  Database: {db_config.url[:30]}...")
            
            # Basic URL validation
            if 'localhost' in db_config.url and self.environment == 'production':
                print("      ⚠️  Using localhost database in production")
                self.setup_results['warnings'].append("Database: localhost in production")
            
            print("      ✅ Database configuration loaded")
            
        except Exception as e:
            print(f"      ❌ Database test failed: {e}")
            self.setup_results['errors'].append(f"Database: {str(e)}")
    
    def _test_redis_connection(self, config):
        """Test Redis connection"""
        try:
            redis_config = config.get_redis_config()
            print(f"   📦 Redis: {redis_config.url}")
            
            # Try actual connection
            try:
                import redis
                redis_client = redis.from_url(
                    redis_config.url,
                    password=redis_config.password,
                    socket_timeout=2,
                    decode_responses=True
                )
                redis_client.ping()
                print("      ✅ Redis connection successful")
            except ImportError:
                print("      ⚠️  Redis package not installed")
                self.setup_results['warnings'].append("Redis: package not installed")
            except Exception as e:
                print(f"      ❌ Redis connection failed: {e}")
                self.setup_results['warnings'].append(f"Redis: connection failed - {str(e)}")
            
        except Exception as e:
            print(f"      ❌ Redis test failed: {e}")
            self.setup_results['errors'].append(f"Redis: {str(e)}")
    
    def _test_twilio_connection(self, config):
        """Test Twilio connection"""
        try:
            twilio_config = config.get_twilio_config()
            
            if twilio_config.enabled:
                print("   📱 Twilio: Enabled")
                
                try:
                    from twilio.rest import Client
                    client = Client(
                        twilio_config.credentials['account_sid'],
                        twilio_config.credentials['auth_token']
                    )
                    account = client.api.accounts(twilio_config.credentials['account_sid']).fetch()
                    print(f"      ✅ Twilio connection successful (Account: {account.friendly_name})")
                    
                    if account.status != 'active':
                        print(f"      ⚠️  Account status: {account.status}")
                        self.setup_results['warnings'].append(f"Twilio: account status {account.status}")
                
                except ImportError:
                    print("      ⚠️  Twilio package not installed")
                    self.setup_results['warnings'].append("Twilio: package not installed")
                except Exception as e:
                    print(f"      ❌ Twilio connection failed: {e}")
                    self.setup_results['warnings'].append(f"Twilio: connection failed - {str(e)}")
            else:
                print("   📱 Twilio: Disabled (no credentials)")
        
        except Exception as e:
            print(f"      ❌ Twilio test failed: {e}")
            self.setup_results['warnings'].append(f"Twilio: {str(e)}")
    
    def _test_proxy_connection(self, config):
        """Test proxy connection"""
        try:
            proxy_config = config.get_proxy_config()
            
            if proxy_config.enabled:
                print("   🌐 Proxy: Enabled")
                
                try:
                    import requests
                    response = requests.get(
                        'http://httpbin.org/ip',
                        proxies={'http': proxy_config.endpoint, 'https': proxy_config.endpoint},
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        print("      ✅ Proxy connection successful")
                    else:
                        print(f"      ⚠️  Proxy returned status {response.status_code}")
                        self.setup_results['warnings'].append(f"Proxy: status {response.status_code}")
                
                except ImportError:
                    print("      ⚠️  Requests package not installed")
                    self.setup_results['warnings'].append("Proxy: requests package not installed")
                except Exception as e:
                    print(f"      ❌ Proxy connection failed: {e}")
                    self.setup_results['warnings'].append(f"Proxy: connection failed - {str(e)}")
            else:
                print("   🌐 Proxy: Disabled (no configuration)")
        
        except Exception as e:
            print(f"      ❌ Proxy test failed: {e}")
            self.setup_results['warnings'].append(f"Proxy: {str(e)}")
    
    def _step_final_validation(self):
        """Step 5: Final validation"""
        print("✅ Step 5: Final Configuration Validation")
        print("-" * 40)
        
        try:
            if ConfigurationValidator:
                validator = ConfigurationValidator(self.environment)
                final_report = validator.validate_all()
                
                print(f"   Overall Status: {final_report.overall_status.upper()}")
                print(f"   Valid: {final_report.summary.get('valid', 0)}")
                print(f"   Warnings: {final_report.summary.get('warning', 0)}")
                print(f"   Errors: {final_report.summary.get('error', 0)}")
                
                # Save report
                report_file = f"config_validation_{self.environment}_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                validator.save_report(final_report, report_file)
                print(f"   📄 Validation report saved: {report_file}")
                self.setup_results['files_created'].append(report_file)
                
            else:
                print("   ❌ Final validation skipped (validator not available)")
        
        except Exception as e:
            error_msg = f"Final validation failed: {str(e)}"
            self.setup_results['errors'].append(error_msg)
            print(f"   ❌ {error_msg}")
        
        print()
    
    def _generate_setup_summary(self):
        """Generate setup summary"""
        print("📋 Setup Summary")
        print("=" * 60)
        
        # Overall status
        error_count = len(self.setup_results['errors'])
        warning_count = len(self.setup_results['warnings'])
        
        if error_count == 0 and warning_count == 0:
            print("🎉 SETUP COMPLETED SUCCESSFULLY!")
            print("✅ Configuration is ready for use")
        elif error_count == 0:
            print("⚠️  SETUP COMPLETED WITH WARNINGS")
            print("✅ Configuration is functional but needs attention")
        else:
            print("❌ SETUP COMPLETED WITH ERRORS")  
            print("🔧 Configuration has issues that need fixing")
        
        print(f"\\nResults:")
        print(f"   ✅ Files created: {len(self.setup_results['files_created'])}")
        print(f"   ⚠️  Warnings: {warning_count}")
        print(f"   ❌ Errors: {error_count}")
        
        # Show files created
        if self.setup_results['files_created']:
            print(f"\\n📁 Files Created:")
            for file_path in self.setup_results['files_created']:
                print(f"   - {file_path}")
        
        # Show errors
        if self.setup_results['errors']:
            print(f"\\n❌ Errors:")
            for error in self.setup_results['errors']:
                print(f"   - {error}")
        
        # Show warnings  
        if self.setup_results['warnings']:
            print(f"\\n⚠️  Warnings:")
            for warning in self.setup_results['warnings']:
                print(f"   - {warning}")
        
        # Next steps
        print(f"\\n🎯 Next Steps:")
        if error_count > 0:
            print("   1. Fix the errors listed above")
            print("   2. Update credentials in .env file")
            print("   3. Re-run setup: python setup_configuration.py")
        elif warning_count > 0:
            print("   1. Review and address warnings")
            print("   2. Update credentials in .env file")
            print("   3. Test application functionality")
        else:
            print("   1. Update credentials in .env file with your actual values")
            print("   2. Test the application: python -m automation.tests.test_config")
            print("   3. Start the services!")
        
        print("\\n🔧 Configuration Tools:")
        print("   - Validate: python -m automation.config.validation")
        print("   - Test credentials: python -m automation.config.credentials_manager")
        print("   - Export template: python -c \"from automation.config import export_env_template; print(export_env_template())\" > .env.new")
        
        print("\\n📚 Documentation:")
        print("   - Configuration guide: ./automation/config/README.md")
        print("   - Environment variables: ./.env.example")
        print("   - Setup log: ./setup_configuration.log")

def main():
    """Main setup script entry point"""
    # Load environment variables at startup
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    parser = argparse.ArgumentParser(
        description='Setup and validate Tinder automation configuration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python setup_configuration.py                    # Interactive setup for development
  python setup_configuration.py --env production  # Production environment setup
  python setup_configuration.py --non-interactive # Non-interactive mode
  python setup_configuration.py --validate-only   # Just validate current config
        """
    )
    
    parser.add_argument(
        '--environment', '--env', '-e',
        choices=['development', 'staging', 'production', 'testing', 'local'],
        default='development',
        help='Environment to set up (default: development)'
    )
    
    parser.add_argument(
        '--non-interactive', '--batch', '-b',
        action='store_true',
        help='Run in non-interactive mode'
    )
    
    parser.add_argument(
        '--validate-only', '-v',
        action='store_true', 
        help='Only validate current configuration'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Save setup results to JSON file'
    )
    
    args = parser.parse_args()
    
    try:
        if args.validate_only:
            # Just run validation
            print("🔍 Configuration Validation Only")
            print("=" * 40)
            
            if ConfigurationValidator:
                validator = ConfigurationValidator(args.environment)
                report = validator.validate_all()
                
                if args.output:
                    validator.save_report(report, args.output)
                    print(f"\\n📄 Report saved to: {args.output}")
                
                sys.exit(0 if report.overall_status == 'valid' else 1)
            else:
                print("❌ Configuration validator not available")
                sys.exit(1)
        else:
            # Full setup
            setup = ConfigurationSetup(
                environment=args.environment,
                interactive=not args.non_interactive
            )
            
            results = setup.run_complete_setup()
            
            # Save results if requested
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(results, f, indent=2, default=str)
                print(f"\\n📄 Setup results saved to: {args.output}")
            
            # Exit with appropriate code
            if len(results.get('errors', [])) > 0:
                sys.exit(1)  # Errors found
            elif len(results.get('warnings', [])) > 0:
                sys.exit(2)  # Warnings found  
            else:
                sys.exit(0)  # Success
    
    except KeyboardInterrupt:
        print("\\n❌ Setup cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Setup script failed: {e}")
        print(f"❌ Setup script failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()