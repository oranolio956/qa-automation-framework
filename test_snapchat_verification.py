#!/usr/bin/env python3
"""
CRITICAL VERIFICATION SCRIPT - Test actual Snapchat account creation blockers
"""

import sys
import os
import traceback
from pathlib import Path

# Add automation directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'automation'))

# Store results for comprehensive analysis
verification_results = {
    "blockers": [],
    "warnings": [],
    "missing_configs": [],
    "critical_errors": [],
    "environment_issues": []
}

def test_component(name, test_func):
    """Test a component and capture real errors"""
    print(f"\n{'='*50}")
    print(f"TESTING: {name}")
    print(f"{'='*50}")
    
    try:
        result = test_func()
        if result.get('status') == 'ERROR':
            verification_results['blockers'].append({
                'component': name,
                'error': result.get('error'),
                'details': result.get('details')
            })
            print(f"❌ BLOCKER FOUND: {result.get('error')}")
        elif result.get('status') == 'WARNING':
            verification_results['warnings'].append({
                'component': name,
                'warning': result.get('warning'),
                'details': result.get('details')
            })
            print(f"⚠️  WARNING: {result.get('warning')}")
        else:
            print(f"✅ {name}: PASSED")
        
        return result
    except Exception as e:
        error_msg = f"Exception in {name}: {str(e)}"
        verification_results['critical_errors'].append({
            'component': name,
            'error': error_msg,
            'traceback': traceback.format_exc()
        })
        print(f"💥 CRITICAL ERROR in {name}: {str(e)}")
        return {'status': 'CRITICAL_ERROR', 'error': str(e)}

def test_snapchat_stealth_creator():
    """Test SnapchatStealthCreator initialization"""
    try:
        from snapchat.stealth_creator import SnapchatStealthCreator
        creator = SnapchatStealthCreator()
        return {'status': 'SUCCESS', 'message': 'SnapchatStealthCreator initialized successfully'}
    except ImportError as e:
        return {'status': 'ERROR', 'error': 'Import failed', 'details': str(e)}
    except Exception as e:
        return {'status': 'ERROR', 'error': 'Initialization failed', 'details': str(e)}

def test_android_connectivity():
    """Test Android device connectivity"""
    try:
        import uiautomator2 as u2
        import adbutils
        # Try to list devices using adbutils
        devices = adbutils.adb.list()
        if not devices:
            return {'status': 'ERROR', 'error': 'No Android devices detected', 'details': 'adb cannot find any connected devices. Connect an Android device with USB debugging enabled.'}
        
        # Try to connect to the first device
        device = u2.connect(devices[0].serial)
        info = device.info
        return {'status': 'SUCCESS', 'message': f'Connected to device: {info.get("model", "Unknown")} - {devices[0].serial}'}
    except ImportError as e:
        return {'status': 'ERROR', 'error': 'UIAutomator2 or adbutils not available', 'details': f'Missing packages: {str(e)}'}
    except Exception as e:
        return {'status': 'ERROR', 'error': 'Device connection failed', 'details': str(e)}

def test_sms_services():
    """Test SMS verification services"""
    try:
        # Check Twilio configuration with correct class name
        from utils.twilio_pool import TwilioPhonePool
        pool = TwilioPhonePool()
        
        # Check if Twilio is configured
        if not pool.credentials_available:
            return {'status': 'ERROR', 'error': 'Twilio credentials not configured', 'details': 'TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN environment variables not set'}
        
        if not pool.client:
            return {'status': 'ERROR', 'error': 'Twilio client not initialized', 'details': 'Twilio client failed to initialize'}
        
        return {'status': 'SUCCESS', 'message': 'Twilio phone pool is properly configured'}
    except ImportError as e:
        return {'status': 'ERROR', 'error': 'SMS service import failed', 'details': str(e)}
    except Exception as e:
        return {'status': 'ERROR', 'error': 'SMS service configuration error', 'details': str(e)}

def test_email_services():
    """Test email verification services"""
    try:
        # Use correct import path
        from automation.email_services.business_email_service import BusinessEmailService
        email_service = BusinessEmailService()
        
        # Test if email service can be initialized
        if not hasattr(email_service, 'providers') or not email_service.providers:
            return {'status': 'WARNING', 'warning': 'No email providers configured', 'details': 'BusinessEmailService has no active providers but can work in fallback mode'}
        
        return {'status': 'SUCCESS', 'message': f'Email service has {len(email_service.providers)} providers'}
    except ImportError as e:
        return {'status': 'ERROR', 'error': 'Email service import failed', 'details': str(e)}
    except Exception as e:
        return {'status': 'ERROR', 'error': 'Email service configuration error', 'details': str(e)}

def test_environment_variables():
    """Test critical environment variables"""
    required_vars = [
        'TWILIO_ACCOUNT_SID',
        'TWILIO_AUTH_TOKEN',
        'TELEGRAM_BOT_TOKEN',
        'DATABASE_URL'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        verification_results['missing_configs'].extend(missing_vars)
        return {'status': 'ERROR', 'error': 'Missing environment variables', 'details': f'Missing: {", ".join(missing_vars)}'}
    
    return {'status': 'SUCCESS', 'message': 'All required environment variables are set'}

def test_dependencies():
    """Test critical dependencies"""
    required_packages = [
        ('uiautomator2', 'uiautomator2'),
        ('twilio', 'twilio'),
        ('faker', 'Faker'),
        ('requests', 'requests'),
        ('beautifulsoup4', 'bs4')
    ]
    
    missing_packages = []
    for display_name, import_name in required_packages:
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(display_name)
    
    if missing_packages:
        return {'status': 'ERROR', 'error': 'Missing dependencies', 'details': f'Missing packages: {", ".join(missing_packages)}'}
    
    return {'status': 'SUCCESS', 'message': 'All required packages are available'}

def test_account_creation_flow():
    """Test the complete account creation flow logic"""
    try:
        from snapchat.stealth_creator import SnapchatStealthCreator
        creator = SnapchatStealthCreator()
        
        # Test profile generation
        profile = creator.generate_stealth_profile()
        if not profile or not hasattr(profile, 'username'):
            return {'status': 'ERROR', 'error': 'Profile generation failed', 'details': 'generate_stealth_profile() did not return valid profile'}
        
        return {'status': 'SUCCESS', 'message': f'Account creation flow logic works - generated profile for {profile.username}'}
    except Exception as e:
        return {'status': 'ERROR', 'error': 'Account creation flow failed', 'details': str(e)}

def main():
    """Run comprehensive verification"""
    print("🔍 COMPREHENSIVE SNAPCHAT ACCOUNT CREATION VERIFICATION")
    print("=" * 60)
    print("Testing REAL blockers that prevent actual account creation...")
    
    # Run all tests
    tests = [
        ("SnapchatStealthCreator Initialization", test_snapchat_stealth_creator),
        ("Android Device Connectivity", test_android_connectivity),
        ("SMS Verification Services", test_sms_services),
        ("Email Verification Services", test_email_services),
        ("Environment Variables", test_environment_variables),
        ("Critical Dependencies", test_dependencies),
        ("Account Creation Flow", test_account_creation_flow)
    ]
    
    for test_name, test_func in tests:
        test_component(test_name, test_func)
    
    # Generate comprehensive report
    print("\n" + "="*60)
    print("🚨 COMPREHENSIVE VERIFICATION RESULTS")
    print("="*60)
    
    if verification_results['critical_errors']:
        print(f"\n💥 CRITICAL ERRORS ({len(verification_results['critical_errors'])}):")
        for error in verification_results['critical_errors']:
            print(f"  - {error['component']}: {error['error']}")
    
    if verification_results['blockers']:
        print(f"\n❌ REAL BLOCKERS ({len(verification_results['blockers'])}):")
        for blocker in verification_results['blockers']:
            print(f"  - {blocker['component']}: {blocker['error']}")
            if blocker['details']:
                print(f"    Details: {blocker['details']}")
    
    if verification_results['missing_configs']:
        print(f"\n🔧 MISSING CONFIGURATIONS ({len(verification_results['missing_configs'])}):")
        for config in verification_results['missing_configs']:
            print(f"  - {config}")
    
    if verification_results['warnings']:
        print(f"\n⚠️  WARNINGS ({len(verification_results['warnings'])}):")
        for warning in verification_results['warnings']:
            print(f"  - {warning['component']}: {warning['warning']}")
    
    # Calculate readiness score
    total_issues = len(verification_results['critical_errors']) + len(verification_results['blockers'])
    if total_issues == 0:
        print(f"\n✅ PRODUCTION READINESS: READY")
        print("All critical components are working - can create real Snapchat accounts")
    else:
        print(f"\n🚫 PRODUCTION READINESS: BLOCKED")
        print(f"Found {total_issues} critical issues that prevent account creation")
    
    print(f"\nSummary: {len(verification_results['critical_errors'])} critical errors, {len(verification_results['blockers'])} blockers, {len(verification_results['warnings'])} warnings")
    
    return verification_results

if __name__ == "__main__":
    results = main()