#!/usr/bin/env python3
"""
Test Script for Real Automation Integration
Verifies that the Telegram bot is properly integrated with REAL automation systems
"""

import os
import sys
import asyncio
import logging

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'automation'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'automation/telegram_bot'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_real_automation_config():
    """Test real automation configuration"""
    print("🧪 Testing Real Automation Configuration...")
    
    try:
        from automation.telegram_bot.real_automation_config import get_real_automation_config, validate_real_automation_ready
        
        config = get_real_automation_config()
        config.log_configuration_status()
        
        ready, message = validate_real_automation_ready()
        print(f"\n✅ Configuration Test: {message}")
        return ready
        
    except ImportError as e:
        print(f"❌ Configuration Test Failed: {e}")
        return False

def test_automation_components():
    """Test individual automation components"""
    print("\n🧪 Testing Automation Components...")
    
    results = {}
    
    # Test Snapchat Creator
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'automation'))
        from snapchat.stealth_creator import SnapchatStealthCreator
        creator = SnapchatStealthCreator()
        results['snapchat_creator'] = True
        print("✅ SnapchatStealthCreator: Loaded")
    except Exception as e:
        results['snapchat_creator'] = False
        print(f"❌ SnapchatStealthCreator: Failed - {e}")
    
    # Test Android Orchestrator
    try:
        from android.automation_orchestrator_fixed import AndroidAutomationOrchestratorFixed
        orchestrator = AndroidAutomationOrchestratorFixed()
        results['android_orchestrator'] = True
        print("✅ AndroidAutomationOrchestratorFixed: Loaded")
    except Exception as e:
        results['android_orchestrator'] = False
        print(f"❌ AndroidAutomationOrchestratorFixed: Failed - {e}")
    
    # Test SMS Verifier
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))
        from sms_verifier import SMSVerifier
        sms_verifier = SMSVerifier()
        results['sms_verifier'] = True
        print("✅ SMSVerifier: Loaded")
    except Exception as e:
        results['sms_verifier'] = False
        print(f"❌ SMSVerifier: Failed - {e}")
    
    # Test Email Integration
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'automation/email'))
        from email_integration import EmailAutomationIntegrator
        email_integrator = EmailAutomationIntegrator()
        results['email_integrator'] = True
        print("✅ EmailAutomationIntegrator: Loaded")
    except Exception as e:
        results['email_integrator'] = False
        print(f"❌ EmailAutomationIntegrator: Failed - {e}")
    
    return results

def test_progress_tracker():
    """Test real-time progress tracker"""
    print("\n🧪 Testing Progress Tracker...")
    
    try:
        from automation.telegram_bot.real_time_progress_tracker import RealTimeProgressTracker
        
        # Mock telegram app for testing
        class MockTelegramApp:
            pass
        
        tracker = RealTimeProgressTracker(MockTelegramApp())
        print("✅ RealTimeProgressTracker: Loaded")
        
        # Test batch creation
        batch_id = tracker.create_batch(
            user_id=12345,
            account_count=1,
            total_price=0.0,
            crypto_type="TEST"
        )
        print(f"✅ Batch created: {batch_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Progress Tracker Test Failed: {e}")
        return False

def test_bot_integration():
    """Test bot integration with real automation"""
    print("\n🧪 Testing Bot Integration...")
    
    try:
        from automation.telegram_bot.main_bot import TelegramBot
        
        # Test validation function
        bot = TelegramBot()
        if hasattr(bot, '_validate_real_automation_available'):
            is_available, message = bot._validate_real_automation_available()
            print(f"Bot Validation: {message}")
            return is_available
        else:
            print("❌ Validation method not found in bot")
            return False
            
    except Exception as e:
        print(f"❌ Bot Integration Test Failed: {e}")
        return False

async def run_complete_test():
    """Run complete integration test"""
    print("🚀 REAL AUTOMATION INTEGRATION TEST")
    print("=" * 50)
    
    test_results = {
        'config': test_real_automation_config(),
        'components': test_automation_components(),
        'progress_tracker': test_progress_tracker(),
        'bot_integration': test_bot_integration()
    }
    
    print("\n📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    for test_name, result in test_results.items():
        if isinstance(result, dict):
            # Components test returns dict
            success_count = sum(1 for v in result.values() if v)
            total_count = len(result)
            status = "✅ PASS" if success_count == total_count else f"⚠️ PARTIAL ({success_count}/{total_count})"
            print(f"{test_name.upper()}: {status}")
            
            if success_count < total_count:
                for comp, success in result.items():
                    if not success:
                        print(f"  ❌ {comp}")
        else:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.upper()}: {status}")
    
    # Overall assessment
    all_components_loaded = all(test_results['components'].values()) if isinstance(test_results['components'], dict) else test_results['components']
    overall_success = (
        test_results['config'] and
        all_components_loaded and
        test_results['progress_tracker'] and
        test_results['bot_integration']
    )
    
    print("\n🎯 OVERALL RESULT")
    print("=" * 50)
    
    if overall_success:
        print("🎉 ALL TESTS PASSED - REAL AUTOMATION READY!")
        print("✅ Bot will create REAL Snapchat accounts")
        print("🚫 NO fake/demo accounts will be created")
    else:
        print("❌ TESTS FAILED - Real automation not ready")
        print("⚠️ Bot may fall back to error messages")
        print("🔧 Please fix failing components before deployment")
    
    return overall_success

if __name__ == "__main__":
    result = asyncio.run(run_complete_test())
    sys.exit(0 if result else 1)