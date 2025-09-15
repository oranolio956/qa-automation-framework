#!/usr/bin/env python3
"""
Environment Setup and Validation for Snapchat Automation

Loads and validates all required environment variables and credentials.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional

def load_env_file(env_path: str = None) -> Dict[str, str]:
    """Load environment variables from .env file"""
    if env_path is None:
        # Look for .env file in parent directories
        current_dir = Path(__file__).parent
        for _ in range(3):  # Check up to 3 levels up
            env_file = current_dir / '.env'
            if env_file.exists():
                env_path = str(env_file)
                break
            current_dir = current_dir.parent
    
    if not env_path or not os.path.exists(env_path):
        raise FileNotFoundError(f"Environment file not found: {env_path}")
    
    env_vars = {}
    with open(env_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                try:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip('"\'')
                    os.environ[key] = value
                    env_vars[key] = value
                except Exception as e:
                    print(f"Warning: Could not parse line {line_num}: {line} ({e})")
    
    return env_vars

def setup_fly_device_farm() -> bool:
    """Setup Fly.io device farm configuration"""
    try:
        # Check if FARM_DEVICES_CONFIG is already set
        if os.getenv('FARM_DEVICES_CONFIG'):
            return True
        
        # Create default Fly.io device configuration
        fly_devices_config = {
            'devices': []
        }
        
        # Get device farm endpoint
        farm_endpoint = os.getenv('DEVICE_FARM_ENDPOINT')
        if farm_endpoint:
            # Extract host from endpoint
            if '://' in farm_endpoint:
                host = farm_endpoint.split('://')[1]
            else:
                host = farm_endpoint
            
            # Create device configurations for standard ports
            for i, port in enumerate([5555, 5556, 5557, 5558], 1):
                device_config = {
                    'device_id': f'fly_android_{i}',
                    'host': host,
                    'port': port,
                    'api_level': 30,
                    'architecture': 'x86_64',
                    'screen_resolution': '1080x1920',
                    'metadata': {
                        'provider': 'fly.io',
                        'region': os.getenv('FLY_IO_REGION', 'ord')
                    }
                }
                fly_devices_config['devices'].append(device_config)
        
        # Set the environment variable
        os.environ['FARM_DEVICES_CONFIG'] = json.dumps(fly_devices_config)
        return True
        
    except Exception as e:
        print(f"Warning: Could not setup Fly.io device farm: {e}")
        return False

def validate_credentials() -> Dict[str, Any]:
    """Validate all required credentials and configurations"""
    validation_results = {
        'twilio': {'status': 'unknown', 'details': {}},
        'fly_io': {'status': 'unknown', 'details': {}},
        'brightdata': {'status': 'unknown', 'details': {}},
        'captcha': {'status': 'unknown', 'details': {}},
        'database': {'status': 'unknown', 'details': {}},
        'overall': {'status': 'unknown', 'issues': []}
    }
    
    issues = []
    
    # Validate Twilio
    twilio_sid = os.getenv('TWILIO_ACCOUNT_SID')
    twilio_token = os.getenv('TWILIO_AUTH_TOKEN')
    
    if twilio_sid and twilio_token:
        try:
            from twilio.rest import Client
            client = Client(twilio_sid, twilio_token)
            account = client.api.accounts(twilio_sid).fetch()
            validation_results['twilio'] = {
                'status': 'valid',
                'details': {
                    'account_sid': twilio_sid,
                    'account_name': account.friendly_name,
                    'status': account.status
                }
            }
        except ImportError:
            validation_results['twilio'] = {
                'status': 'missing_dependency',
                'details': {'error': 'Twilio SDK not installed'}
            }
            issues.append('Install Twilio SDK: pip install twilio')
        except Exception as e:
            validation_results['twilio'] = {
                'status': 'invalid',
                'details': {'error': str(e)}
            }
            issues.append(f'Twilio credentials invalid: {e}')
    else:
        validation_results['twilio'] = {
            'status': 'missing',
            'details': {'missing': [k for k in ['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN'] if not os.getenv(k)]}
        }
        issues.append('Twilio credentials missing')
    
    # Validate Fly.io
    fly_token = os.getenv('FLY_IO_API_TOKEN')
    fly_endpoint = os.getenv('DEVICE_FARM_ENDPOINT')
    
    if fly_token and fly_endpoint:
        validation_results['fly_io'] = {
            'status': 'configured',
            'details': {
                'endpoint': fly_endpoint,
                'token_present': bool(fly_token),
                'app_name': os.getenv('FLY_IO_APP_NAME'),
                'region': os.getenv('FLY_IO_REGION')
            }
        }
    else:
        validation_results['fly_io'] = {
            'status': 'missing',
            'details': {'missing': [k for k in ['FLY_IO_API_TOKEN', 'DEVICE_FARM_ENDPOINT'] if not os.getenv(k)]}
        }
        issues.append('Fly.io configuration missing')
    
    # Validate BrightData
    brightdata_url = os.getenv('BRIGHTDATA_PROXY_URL')
    if brightdata_url:
        validation_results['brightdata'] = {
            'status': 'configured',
            'details': {'proxy_url_present': True}
        }
    else:
        validation_results['brightdata'] = {
            'status': 'missing',
            'details': {'missing': ['BRIGHTDATA_PROXY_URL']}
        }
        issues.append('BrightData proxy configuration missing')
    
    # Validate CAPTCHA service
    captcha_key = os.getenv('TWOCAPTCHA_API_KEY')
    if captcha_key:
        validation_results['captcha'] = {
            'status': 'configured',
            'details': {'api_key_present': True}
        }
    else:
        validation_results['captcha'] = {
            'status': 'missing',
            'details': {'missing': ['TWOCAPTCHA_API_KEY']}
        }
        issues.append('CAPTCHA service API key missing')
    
    # Validate Database
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        validation_results['database'] = {
            'status': 'configured',
            'details': {'url_present': True}
        }
    else:
        validation_results['database'] = {
            'status': 'missing',
            'details': {'missing': ['DATABASE_URL']}
        }
        issues.append('Database URL missing')
    
    # Overall status
    valid_services = sum(1 for service in validation_results.values() 
                        if isinstance(service, dict) and service.get('status') in ['valid', 'configured'])
    
    if valid_services >= 4:  # Twilio + Fly.io + 2 others minimum
        validation_results['overall']['status'] = 'ready'
    elif valid_services >= 2:
        validation_results['overall']['status'] = 'partial'
    else:
        validation_results['overall']['status'] = 'insufficient'
    
    validation_results['overall']['issues'] = issues
    validation_results['overall']['services_configured'] = valid_services
    
    return validation_results

def setup_environment() -> bool:
    """Complete environment setup and validation"""
    try:
        print("=== Snapchat Automation Environment Setup ===")
        print()
        
        # Load environment variables
        print("1. Loading environment variables...")
        env_vars = load_env_file()
        print(f"   ✅ Loaded {len(env_vars)} environment variables")
        
        # Setup Fly.io device farm
        print("2. Setting up Fly.io device farm...")
        fly_setup = setup_fly_device_farm()
        if fly_setup:
            print("   ✅ Fly.io device farm configured")
        else:
            print("   ⚠️ Fly.io device farm setup failed")
        
        # Validate credentials
        print("3. Validating credentials...")
        results = validate_credentials()
        
        # Print validation results
        print()
        print("=== Credential Validation Results ===")
        
        for service, result in results.items():
            if service == 'overall':
                continue
                
            status = result['status']
            if status == 'valid':
                print(f"✅ {service.upper()}: Valid")
                if 'details' in result:
                    for key, value in result['details'].items():
                        if 'token' not in key.lower() and 'key' not in key.lower():
                            print(f"   {key}: {value}")
            elif status == 'configured':
                print(f"🔧 {service.upper()}: Configured")
            elif status == 'missing':
                print(f"❌ {service.upper()}: Missing")
                if 'missing' in result['details']:
                    print(f"   Missing: {', '.join(result['details']['missing'])}")
            elif status == 'invalid':
                print(f"⚠️ {service.upper()}: Invalid")
                if 'error' in result['details']:
                    print(f"   Error: {result['details']['error']}")
            elif status == 'missing_dependency':
                print(f"📦 {service.upper()}: Missing dependency")
                if 'error' in result['details']:
                    print(f"   {result['details']['error']}")
        
        # Overall status
        overall = results['overall']
        print()
        print(f"=== Overall Status: {overall['status'].upper()} ===")
        print(f"Services configured: {overall['services_configured']}/5")
        
        if overall['issues']:
            print()
            print("Issues to resolve:")
            for issue in overall['issues']:
                print(f"  - {issue}")
        
        return overall['status'] in ['ready', 'partial']
        
    except Exception as e:
        print(f"❌ Environment setup failed: {e}")
        return False

if __name__ == "__main__":
    success = setup_environment()
    if success:
        print()
        print("🎉 Environment setup completed successfully!")
        print("The automation system is ready to use.")
    else:
        print()
        print("⚠️ Environment setup completed with issues.")
        print("Some features may not work correctly.")
    
    sys.exit(0 if success else 1)