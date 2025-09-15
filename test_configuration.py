#!/usr/bin/env python3
"""
Configuration System Test Script
Quick test to verify the configuration system is working correctly
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_configuration():
    """Test the complete configuration system"""
    print("🧪 Testing Configuration System")
    print("=" * 50)
    
    success_count = 0
    total_tests = 0
    
    # Test 1: Environment Loading
    total_tests += 1
    try:
        from dotenv import load_dotenv
        load_dotenv()
        jwt_secret = os.getenv('JWT_SECRET')
        if jwt_secret and len(jwt_secret) > 32:
            print("✅ Test 1: Environment loading - PASSED")
            success_count += 1
        else:
            print("❌ Test 1: Environment loading - FAILED (JWT_SECRET not found or too short)")
    except Exception as e:
        print(f"❌ Test 1: Environment loading - ERROR: {e}")
    
    # Test 2: Configuration Manager Import
    total_tests += 1
    try:
        from automation.config import get_config, ConfigManager
        config = get_config()
        print("✅ Test 2: Configuration manager import - PASSED")
        success_count += 1
    except Exception as e:
        print(f"❌ Test 2: Configuration manager import - ERROR: {e}")
        return
    
    # Test 3: Database Configuration
    total_tests += 1
    try:
        db_config = config.get_database_config()
        if db_config and db_config.url:
            print("✅ Test 3: Database configuration - PASSED")
            success_count += 1
        else:
            print("❌ Test 3: Database configuration - FAILED")
    except Exception as e:
        print(f"❌ Test 3: Database configuration - ERROR: {e}")
    
    # Test 4: Redis Configuration
    total_tests += 1
    try:
        redis_config = config.get_redis_config()
        if redis_config and redis_config.url:
            print("✅ Test 4: Redis configuration - PASSED")
            success_count += 1
        else:
            print("❌ Test 4: Redis configuration - FAILED")
    except Exception as e:
        print(f"❌ Test 4: Redis configuration - ERROR: {e}")
    
    # Test 5: Security Configuration
    total_tests += 1
    try:
        security_config = config.get_security_config()
        if security_config and len(security_config['jwt_secret']) > 32:
            print("✅ Test 5: Security configuration - PASSED")
            success_count += 1
        else:
            print("❌ Test 5: Security configuration - FAILED")
    except Exception as e:
        print(f"❌ Test 5: Security configuration - ERROR: {e}")
    
    # Test 6: Service Configurations
    total_tests += 1
    try:
        twilio_config = config.get_twilio_config()
        proxy_config = config.get_proxy_config()
        captcha_config = config.get_captcha_config()
        print("✅ Test 6: Service configurations - PASSED")
        success_count += 1
    except Exception as e:
        print(f"❌ Test 6: Service configurations - ERROR: {e}")
    
    # Test 7: Validation System
    total_tests += 1
    try:
        validation = config.validate_configuration()
        if validation and 'valid' in validation:
            print("✅ Test 7: Validation system - PASSED")
            success_count += 1
        else:
            print("❌ Test 7: Validation system - FAILED")
    except Exception as e:
        print(f"❌ Test 7: Validation system - ERROR: {e}")
    
    # Test 8: Health Check
    total_tests += 1
    try:
        from automation.config import health_check
        health = health_check()
        if health and 'healthy' in health:
            print("✅ Test 8: Health check system - PASSED")
            success_count += 1
        else:
            print("❌ Test 8: Health check system - FAILED")
    except Exception as e:
        print(f"❌ Test 8: Health check system - ERROR: {e}")
    
    # Test 9: Credentials Manager
    total_tests += 1
    try:
        from automation.config import get_credentials
        creds = get_credentials()
        if creds:
            print("✅ Test 9: Credentials manager - PASSED")
            success_count += 1
        else:
            print("❌ Test 9: Credentials manager - FAILED")
    except Exception as e:
        print(f"❌ Test 9: Credentials manager - ERROR: {e}")
    
    # Test 10: Environment Config
    total_tests += 1
    try:
        from automation.config import get_env_config
        env_config = get_env_config()
        if env_config:
            print("✅ Test 10: Environment config - PASSED")
            success_count += 1
        else:
            print("❌ Test 10: Environment config - FAILED")
    except Exception as e:
        print(f"❌ Test 10: Environment config - ERROR: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("🎉 ALL TESTS PASSED! Configuration system is working correctly.")
        return True
    elif success_count >= total_tests * 0.8:
        print("⚠️  MOSTLY WORKING with some issues. Check failed tests above.")
        return True
    else:
        print("❌ MULTIPLE FAILURES detected. Configuration system needs attention.")
        return False

def test_specific_services():
    """Test specific service configurations"""
    print("\n🔌 Testing Service Connections")
    print("-" * 30)
    
    try:
        from automation.config import get_config
        config = get_config()
        
        # Test Redis connection
        try:
            import redis
            redis_config = config.get_redis_config()
            redis_client = redis.from_url(redis_config.url, socket_timeout=2)
            redis_client.ping()
            print("✅ Redis: Connection successful")
        except ImportError:
            print("⚠️  Redis: Package not installed")
        except Exception as e:
            print(f"❌ Redis: Connection failed - {e}")
        
        # Test Twilio configuration format
        try:
            twilio_config = config.get_twilio_config()
            if twilio_config.enabled:
                account_sid = twilio_config.credentials.get('account_sid', '')
                if account_sid.startswith('AC') and len(account_sid) == 34:
                    print("✅ Twilio: Configuration format valid")
                else:
                    print("⚠️  Twilio: Invalid Account SID format")
            else:
                print("ℹ️  Twilio: Service disabled")
        except Exception as e:
            print(f"❌ Twilio: Configuration error - {e}")
        
        # Test proxy configuration
        try:
            proxy_config = config.get_proxy_config()
            if proxy_config.enabled:
                print("✅ Proxy: Configuration loaded")
            else:
                print("ℹ️  Proxy: Service disabled")
        except Exception as e:
            print(f"❌ Proxy: Configuration error - {e}")
        
        # Test CAPTCHA services
        try:
            captcha_config = config.get_captcha_config()
            if captcha_config.enabled:
                service_count = len([k for k in captcha_config.credentials.keys() if k.endswith('_key')])
                print(f"✅ CAPTCHA: {service_count} service(s) configured")
            else:
                print("ℹ️  CAPTCHA: No services configured")
        except Exception as e:
            print(f"❌ CAPTCHA: Configuration error - {e}")
            
    except Exception as e:
        print(f"❌ Service testing failed: {e}")

def show_configuration_status():
    """Show current configuration status"""
    print("\n📋 Configuration Status")
    print("-" * 30)
    
    try:
        from automation.config import get_config
        config = get_config()
        
        print(f"Environment: {config.environment.value}")
        
        # Show service status
        services = {
            'Database': config.get_database_config(),
            'Redis': config.get_redis_config(), 
            'Twilio': config.get_twilio_config(),
            'Proxy': config.get_proxy_config(),
            'CAPTCHA': config.get_captcha_config()
        }
        
        for service_name, service_config in services.items():
            if hasattr(service_config, 'enabled'):
                status = "✅ Enabled" if service_config.enabled else "❌ Disabled"
            else:
                status = "✅ Configured"
            print(f"{service_name}: {status}")
            
    except Exception as e:
        print(f"❌ Status check failed: {e}")

def main():
    """Main test function"""
    try:
        # Load environment variables
        try:
            from dotenv import load_dotenv
            load_dotenv()
            print("✅ Environment variables loaded from .env file\n")
        except ImportError:
            print("⚠️  python-dotenv not available, using system environment\n")
        
        # Run tests
        config_working = test_configuration()
        test_specific_services()
        show_configuration_status()
        
        print(f"\n{'='*50}")
        if config_working:
            print("🎯 RESULT: Configuration system is ready for use!")
            print("\n🚀 Next steps:")
            print("   1. Update .env with your actual service credentials")
            print("   2. Run: python3 setup_configuration.py --validate-only")
            print("   3. Start your application services")
            return 0
        else:
            print("🔧 RESULT: Configuration system needs attention.")
            print("\n🛠️  Troubleshooting:")
            print("   1. Check .env file exists and has proper values")
            print("   2. Run: python3 setup_configuration.py")
            print("   3. Review error messages above")
            return 1
            
    except KeyboardInterrupt:
        print("\n❌ Test cancelled by user")
        return 130
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())