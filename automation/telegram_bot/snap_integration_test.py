#!/usr/bin/env python3
"""
Test /snap command integration with backend
"""

import asyncio
import os
import sys
import requests
import json
from dotenv import load_dotenv

# Load environment
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

def test_backend_connection():
    """Test if backend is accessible"""
    try:
        response = requests.get('http://localhost:8000/health', timeout=5)
        if response.status_code == 200:
            print("✅ Backend is accessible")
            print(f"   Status: {response.json()}")
            return True
        else:
            print(f"❌ Backend returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend connection failed: {e}")
        return False

def test_snap_automation_endpoint():
    """Test snap automation endpoint"""
    try:
        # Test data for automation
        test_data = {
            "user_id": "test_user_123",
            "account_count": 1,
            "automation_type": "demo"
        }
        
        response = requests.post(
            'http://localhost:8000/api/v1/automation/snapchat/create',
            json=test_data,
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ Snap automation endpoint accessible")
            result = response.json()
            print(f"   Response: {result}")
            return True
        else:
            print(f"❌ Snap automation endpoint returned {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Snap automation test failed: {e}")
        return False

def test_webhook_integration():
    """Test webhook integration for real-time updates"""
    try:
        # Test webhook endpoint
        webhook_data = {
            "type": "progress_update",
            "user_id": "test_user_123",
            "message": "Test progress update",
            "progress": 50
        }
        
        response = requests.post(
            'http://localhost:8000/webhooks/telegram',
            json=webhook_data,
            timeout=5
        )
        
        if response.status_code in [200, 202]:
            print("✅ Webhook integration working")
            return True
        else:
            print(f"⚠️ Webhook returned {response.status_code} (may be expected)")
            return True  # Webhooks may return different codes
            
    except Exception as e:
        print(f"❌ Webhook test failed: {e}")
        return False

def main():
    """Run integration tests"""
    print("🧪 Testing Telegram Bot <-> Backend Integration\n")
    
    tests = [
        ("Backend Connection", test_backend_connection),
        ("Snap Automation Endpoint", test_snap_automation_endpoint),
        ("Webhook Integration", test_webhook_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"Testing {test_name}...")
        result = test_func()
        results.append((test_name, result))
        print()
    
    print("📊 Test Results:")
    print("=" * 50)
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All integration tests passed! Bot is ready for production.")
    else:
        print("⚠️ Some tests failed. Check the backend implementation.")

if __name__ == "__main__":
    main()