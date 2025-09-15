#!/usr/bin/env python3
"""
Comprehensive System Implementation Test
Tests all critical components to identify exactly what needs to be implemented
"""

import sys
import os
import asyncio
import json
import traceback
from datetime import datetime

# Add automation to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class SystemImplementationTest:
    def __init__(self):
        self.test_results = {}
        self.missing_implementations = []
        self.working_components = []
        
    def log_result(self, component: str, status: str, details: str = ""):
        """Log test result"""
        self.test_results[component] = {
            'status': status,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        
        symbol = "✅" if status == "WORKING" else "❌" if status == "MISSING" else "⚠️"
        print(f"{symbol} {component}: {status}")
        if details:
            print(f"   Details: {details}")
    
    def test_sms_system(self):
        """Test SMS verification system"""
        try:
            from utils.sms_verifier import get_sms_verifier, SMSVerifier
            verifier = get_sms_verifier()
            
            # Test if pool is available
            if hasattr(verifier, 'pool_available') and verifier.pool_available:
                self.log_result("SMS System", "WORKING", "Twilio pool available")
            else:
                self.log_result("SMS System", "MISSING", "Twilio credentials not configured")
            
            # Test if new methods exist
            missing_methods = []
            required_methods = ['get_number', 'get_verification_code', 'get_number_info', 'release_number']
            
            for method in required_methods:
                if not hasattr(verifier, method):
                    missing_methods.append(method)
            
            if missing_methods:
                self.log_result("SMS Methods", "MISSING", f"Missing methods: {missing_methods}")
            else:
                self.log_result("SMS Methods", "WORKING", "All required methods available")
                
        except Exception as e:
            self.log_result("SMS System", "ERROR", str(e))
    
    def test_email_system(self):
        """Test email verification system"""
        try:
            from automation.email.business_email_service import get_email_service
            email_service = get_email_service()
            self.log_result("Email System", "WORKING", "Email service imports successfully")
            
            # Test email creation method
            if hasattr(email_service, 'create_email'):
                self.log_result("Email Creation", "WORKING", "create_email method available")
            else:
                self.log_result("Email Creation", "MISSING", "create_email method not found")
                
        except ImportError as e:
            self.log_result("Email System", "MISSING", f"Import error: {e}")
        except Exception as e:
            self.log_result("Email System", "ERROR", str(e))
    
    def test_anti_detection(self):
        """Test anti-detection system"""
        try:
            from automation.core.anti_detection import get_anti_detection_system, BehaviorPattern
            
            # Test anti-detection system creation
            ad_system = get_anti_detection_system()
            self.log_result("Anti-Detection System", "WORKING", "System creates successfully")
            
            # Test behavior pattern
            behavior = BehaviorPattern()
            
            # Test if generate_behavior_profile method exists
            if hasattr(behavior, 'generate_behavior_profile'):
                try:
                    profile = behavior.generate_behavior_profile()
                    if isinstance(profile, dict) and 'personality_type' in profile:
                        self.log_result("Behavior Profile Generation", "WORKING", "Method works and returns valid profile")
                    else:
                        self.log_result("Behavior Profile Generation", "PARTIAL", "Method exists but returns invalid data")
                except Exception as e:
                    self.log_result("Behavior Profile Generation", "ERROR", f"Method exists but fails: {e}")
            else:
                self.log_result("Behavior Profile Generation", "MISSING", "generate_behavior_profile method not found")
                
        except Exception as e:
            self.log_result("Anti-Detection System", "ERROR", str(e))
    
    def test_android_system(self):
        """Test Android automation system"""
        try:
            from automation.android.emulator_manager import get_emulator_manager
            emulator_manager = get_emulator_manager()
            self.log_result("Android Emulator Manager", "WORKING", "Manager imports successfully")
            
            # Test UIAutomator2 integration
            try:
                from automation.android.ui_automator_manager import get_ui_automator_manager
                ui_manager = get_ui_automator_manager()
                if ui_manager:
                    self.log_result("UIAutomator2 Integration", "WORKING", "UI Automator manager available")
                else:
                    self.log_result("UIAutomator2 Integration", "MISSING", "UI Automator manager returns None")
            except ImportError:
                self.log_result("UIAutomator2 Integration", "MISSING", "ui_automator_manager module not found")
            except Exception as e:
                self.log_result("UIAutomator2 Integration", "ERROR", str(e))
                
        except Exception as e:
            self.log_result("Android System", "ERROR", str(e))
    
    def test_snapchat_automation(self):
        """Test Snapchat automation core"""
        try:
            from automation.snapchat.stealth_creator import get_snapchat_creator
            snapchat_creator = get_snapchat_creator()
            self.log_result("Snapchat Creator", "WORKING", "Creator imports successfully")
            
            # Test if create_multiple_accounts is real implementation
            if hasattr(snapchat_creator, 'create_multiple_accounts'):
                # Check if it's a real implementation or simulation
                import inspect
                source = inspect.getsource(snapchat_creator.create_multiple_accounts)
                if 'simulation' in source.lower() or 'mock' in source.lower() or 'placeholder' in source.lower():
                    self.log_result("Snapchat Account Creation", "SIMULATION", "Method exists but is simulation only")
                else:
                    self.log_result("Snapchat Account Creation", "IMPLEMENTATION", "Method appears to be real implementation")
            else:
                self.log_result("Snapchat Account Creation", "MISSING", "create_multiple_accounts method not found")
                
        except Exception as e:
            self.log_result("Snapchat Automation", "ERROR", str(e))
    
    def test_telegram_bot(self):
        """Test Telegram bot integration"""
        try:
            from automation.telegram_bot.main_bot import TinderBotApplication
            bot_app = TinderBotApplication()
            self.log_result("Telegram Bot", "WORKING", "Bot application imports successfully")
            
            # Test /snap command implementation
            try:
                # Check if handle_snap_command exists and is implemented
                if hasattr(bot_app, 'handle_snap_command'):
                    import inspect
                    source = inspect.getsource(bot_app.handle_snap_command)
                    if len(source.strip()) > 100:  # Basic check for substantial implementation
                        self.log_result("Snap Command", "IMPLEMENTED", "/snap command has substantial implementation")
                    else:
                        self.log_result("Snap Command", "STUB", "/snap command exists but is minimal")
                else:
                    self.log_result("Snap Command", "MISSING", "handle_snap_command method not found")
            except Exception as e:
                self.log_result("Snap Command", "ERROR", f"Error checking /snap command: {e}")
                
        except Exception as e:
            self.log_result("Telegram Bot", "ERROR", str(e))
    
    def test_fly_io_integration(self):
        """Test Fly.io cloud deployment"""
        try:
            from automation.telegram_bot.fly_deployment_orchestrator import get_fly_orchestrator
            fly_orchestrator = get_fly_orchestrator()
            self.log_result("Fly.io Integration", "WORKING", "Fly orchestrator imports successfully")
            
            # Test if it's real implementation
            if hasattr(fly_orchestrator, 'deploy_android_emulator'):
                import inspect
                source = inspect.getsource(fly_orchestrator.deploy_android_emulator)
                if 'flyctl' in source or 'fly.io' in source:
                    self.log_result("Fly.io Deployment", "IMPLEMENTED", "Contains actual flyctl integration")
                else:
                    self.log_result("Fly.io Deployment", "STUB", "Method exists but no flyctl integration")
            else:
                self.log_result("Fly.io Deployment", "MISSING", "deploy_android_emulator method not found")
                
        except Exception as e:
            self.log_result("Fly.io Integration", "ERROR", str(e))
    
    def test_database_integration(self):
        """Test database and session management"""
        try:
            from automation.telegram_bot.database import get_database
            database = get_database()
            self.log_result("Database System", "WORKING", "Database imports successfully")
            
            # Test Redis integration
            try:
                import redis
                # Try to connect to Redis
                r = redis.Redis(host='localhost', port=6379, decode_responses=True)
                r.ping()
                self.log_result("Redis Integration", "WORKING", "Redis server is running and accessible")
            except redis.ConnectionError:
                self.log_result("Redis Integration", "MISSING", "Redis server not running or not accessible")
            except ImportError:
                self.log_result("Redis Integration", "MISSING", "Redis Python package not installed")
            except Exception as e:
                self.log_result("Redis Integration", "ERROR", str(e))
                
        except Exception as e:
            self.log_result("Database System", "ERROR", str(e))
    
    def test_environment_setup(self):
        """Test environment and configuration"""
        required_env_vars = [
            'REDIS_URL',
            'TWILIO_ACCOUNT_SID', 
            'TWILIO_AUTH_TOKEN',
            'FLY_API_TOKEN',
            'SMARTPROXY_ENDPOINT',
            'SMARTPROXY_USERNAME',
            'SMARTPROXY_PASSWORD'
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            self.log_result("Environment Variables", "MISSING", f"Missing: {missing_vars}")
        else:
            self.log_result("Environment Variables", "WORKING", "All required environment variables set")
    
    async def run_all_tests(self):
        """Run all system tests"""
        print("🔍 COMPREHENSIVE SYSTEM IMPLEMENTATION TEST")
        print("=" * 60)
        
        # Test each component
        self.test_environment_setup()
        self.test_sms_system()
        self.test_email_system()
        self.test_anti_detection()
        self.test_android_system()
        self.test_snapchat_automation()
        self.test_telegram_bot()
        self.test_fly_io_integration()
        self.test_database_integration()
        
        # Generate summary
        print("\n" + "=" * 60)
        print("📊 IMPLEMENTATION STATUS SUMMARY")
        print("=" * 60)
        
        working_count = sum(1 for r in self.test_results.values() if r['status'] == 'WORKING')
        implemented_count = sum(1 for r in self.test_results.values() if r['status'] == 'IMPLEMENTED')
        missing_count = sum(1 for r in self.test_results.values() if r['status'] == 'MISSING')
        error_count = sum(1 for r in self.test_results.values() if r['status'] == 'ERROR')
        stub_count = sum(1 for r in self.test_results.values() if r['status'] in ['STUB', 'SIMULATION', 'PARTIAL'])
        
        total_components = len(self.test_results)
        fully_working = working_count + implemented_count
        
        print(f"✅ Fully Working: {fully_working}/{total_components} ({fully_working/total_components*100:.1f}%)")
        print(f"⚠️  Partial/Stub: {stub_count}/{total_components} ({stub_count/total_components*100:.1f}%)")
        print(f"❌ Missing: {missing_count}/{total_components} ({missing_count/total_components*100:.1f}%)")
        print(f"🔥 Errors: {error_count}/{total_components} ({error_count/total_components*100:.1f}%)")
        
        print("\n🔧 CRITICAL COMPONENTS TO IMPLEMENT:")
        for component, result in self.test_results.items():
            if result['status'] in ['MISSING', 'ERROR', 'STUB', 'SIMULATION']:
                print(f"   - {component}: {result['status']} - {result['details']}")
        
        # Save detailed results
        with open('system_implementation_status.json', 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: system_implementation_status.json")
        
        return self.test_results

def main():
    """Main test runner"""
    test_runner = SystemImplementationTest()
    
    # Run tests
    try:
        results = asyncio.run(test_runner.run_all_tests())
        
        # Determine next steps
        missing_critical = [
            component for component, result in results.items() 
            if result['status'] in ['MISSING', 'ERROR'] and 
            any(critical in component.lower() for critical in ['sms', 'email', 'snapchat', 'android'])
        ]
        
        if missing_critical:
            print(f"\n🚨 NEXT STEPS: Implement these critical components first:")
            for component in missing_critical[:3]:  # Top 3 priorities
                print(f"   1. {component}")
        else:
            print(f"\n🎉 SYSTEM STATUS: Ready for production testing!")
            
    except Exception as e:
        print(f"\n🔥 FATAL ERROR: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()