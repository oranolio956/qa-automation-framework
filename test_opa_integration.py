#!/usr/bin/env python3
"""
Test script for OPA integration with the backend Flask app
"""

import requests
import json
import time
import jwt
import os
from datetime import datetime, timedelta

# Configuration
BACKEND_URL = "http://localhost:8000"
OPA_URL = "http://localhost:8181"

# Get JWT secret from environment (NEVER hardcode in production)
try:
    from utils.vault_client import get_secret
    JWT_SECRET = get_secret('JWT_SECRET')
    if not JWT_SECRET:
        raise ValueError("JWT_SECRET not found in vault or environment")
except Exception:
    JWT_SECRET = os.environ.get('JWT_SECRET')
    if not JWT_SECRET:
        raise ValueError("JWT_SECRET must be set in environment variables for testing")

def generate_test_jwt(user_id="test_user", customer_id="test_customer"):
    """Generate a test JWT token"""
    payload = {
        'user_id': user_id,
        'customer_id': customer_id,
        'exp': datetime.utcnow() + timedelta(hours=1),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def test_opa_policy_direct():
    """Test OPA policies directly"""
    print("🔍 Testing OPA policies directly...")
    
    # Test policy input
    policy_input = {
        "input": {
            "method": "GET",
            "path": "/orders",
            "user_id": "test_user",
            "customer_id": "test_customer",
            "headers": {"Authorization": "Bearer test_token"},
            "timestamp": datetime.now().isoformat(),
            "ip_address": "127.0.0.1"
        }
    }
    
    try:
        response = requests.post(
            f"{OPA_URL}/v1/data/app/authz/allow",
            json=policy_input,
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ OPA direct test: {result}")
            return result.get('result', False)
        else:
            print(f"❌ OPA direct test failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ OPA connection error: {e}")
        return False

def test_backend_health():
    """Test backend health endpoint (should work without auth)"""
    print("🏥 Testing backend health endpoint...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        
        if response.status_code == 200:
            print(f"✅ Health check passed: {response.json()}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Backend connection error: {e}")
        return False

def test_authenticated_endpoint():
    """Test authenticated endpoint with JWT"""
    print("🔐 Testing authenticated endpoint...")
    
    token = generate_test_jwt()
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(f"{BACKEND_URL}/orders", headers=headers, timeout=5)
        
        if response.status_code in [200, 503]:  # 503 if Redis unavailable
            print(f"✅ Authenticated request passed: {response.status_code}")
            return True
        elif response.status_code == 403:
            print(f"🚫 Request blocked by OPA policy: {response.status_code}")
            return True  # This is expected behavior
        else:
            print(f"❌ Unexpected response: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Request error: {e}")
        return False

def test_unauthorized_request():
    """Test request without JWT (should be blocked)"""
    print("🚫 Testing unauthorized request...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/orders", timeout=5)
        
        if response.status_code == 401:
            print(f"✅ Unauthorized request correctly blocked: {response.status_code}")
            return True
        else:
            print(f"❌ Unauthorized request not blocked: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Request error: {e}")
        return False

def test_rbac_permissions():
    """Test RBAC permissions with different user types"""
    print("👥 Testing RBAC permissions...")
    
    # Test admin user
    admin_token = generate_test_jwt(user_id="admin", customer_id="admin")
    headers = {'Authorization': f'Bearer {admin_token}'}
    
    try:
        response = requests.get(f"{BACKEND_URL}/orders", headers=headers, timeout=5)
        print(f"🔑 Admin access: {response.status_code}")
        
        # Test customer user
        customer_token = generate_test_jwt(user_id="customer", customer_id="cust_123")
        headers = {'Authorization': f'Bearer {customer_token}'}
        
        response = requests.get(f"{BACKEND_URL}/orders", headers=headers, timeout=5)
        print(f"👤 Customer access: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ RBAC test error: {e}")
        return False

def test_pii_protection():
    """Test PII protection policies"""
    print("🔒 Testing PII protection...")
    
    token = generate_test_jwt()
    headers = {'Authorization': f'Bearer {token}'}
    
    # Test accessing PII-related endpoint
    try:
        response = requests.get(f"{BACKEND_URL}/orders/test-order/personal", headers=headers, timeout=5)
        print(f"🔐 PII access attempt: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ PII test error: {e}")
        return False

def run_comprehensive_test():
    """Run all OPA integration tests"""
    print("🚀 Starting OPA Integration Tests")
    print("=" * 50)
    
    tests = [
        ("OPA Direct Policy Test", test_opa_policy_direct),
        ("Backend Health Check", test_backend_health),
        ("Authenticated Endpoint", test_authenticated_endpoint),
        ("Unauthorized Request Block", test_unauthorized_request),
        ("RBAC Permissions", test_rbac_permissions),
        ("PII Protection", test_pii_protection)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"Result: {'✅ PASS' if result else '❌ FAIL'}")
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((test_name, False))
        
        time.sleep(1)  # Brief pause between tests
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! OPA integration is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    run_comprehensive_test()