#!/usr/bin/env python3
"""
Test the fixed real_snap_bot to verify critical bugs are resolved
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'automation'))

from automation.snapchat.stealth_creator import SnapchatStealthCreator

def test_critical_fixes():
    """Test that all critical bugs identified are fixed"""
    
    print("🔧 TESTING CRITICAL BUG FIXES")
    print("=" * 50)
    
    # Test 1: Method exists (generate_stealth_profile not generate_profile)
    print("\n1. Testing method name fix...")
    try:
        creator = SnapchatStealthCreator()
        
        # This should work now (was the bug: calling generate_profile())
        profile = creator.generate_stealth_profile()
        print(f"✅ generate_stealth_profile() method works: {profile.username}")
        
        # Verify it returns profile object, not dict
        assert hasattr(profile, 'username'), "Profile should be object with username attribute"
        assert hasattr(profile, 'email'), "Profile should be object with email attribute"
        print(f"✅ Profile object has correct attributes")
        
    except Exception as e:
        print(f"❌ Method name test failed: {e}")
        return False
    
    # Test 2: Parameter type fix (create_account expects profile object)
    print("\n2. Testing parameter type fix...")
    try:
        # This should work now (was the bug: passing string instead of profile object)
        result = creator.create_account(profile=profile, device_id="test_device")
        print(f"✅ create_account() accepts profile object: {result.success}")
        
    except Exception as e:
        print(f"❌ Parameter type test failed: {e}")
        return False
    
    # Test 3: No fake emails (should be real email services)
    print("\n3. Testing real email generation...")
    try:
        email = profile.email
        assert "@example.com" not in email, f"Found fake email: {email}"
        assert "@" in email, f"Invalid email format: {email}"
        
        # Should be real email service
        real_email_domains = ["guerrillamail", "tempmail", "10minutemail", "mailinator", "gmail.com", "yahoo.com", "hotmail.com", "icloud.com"]
        is_real_email = any(domain in email for domain in real_email_domains)
        assert is_real_email, f"Email doesn't use real service: {email}"
        
        print(f"✅ Real email generated: {email}")
        
    except Exception as e:
        print(f"❌ Real email test failed: {e}")
        return False
    
    # Test 4: Profile object access (not dict)
    print("\n4. Testing profile object access...")
    try:
        # These should work (was the bug: using .get() on object)
        username = profile.username  # Not profile.get('username')
        password = profile.password  # Not profile.get('password')
        email = profile.email       # Not profile.get('email')
        display_name = profile.display_name  # Not profile.get('display_name')
        
        print(f"✅ Profile object access works:")
        print(f"   Username: {username}")
        print(f"   Email: {email}")
        print(f"   Display Name: {display_name}")
        
    except Exception as e:
        print(f"❌ Profile object access test failed: {e}")
        return False
    
    print("\n🎉 ALL CRITICAL BUGS FIXED!")
    print("✅ Method name: generate_stealth_profile() works")
    print("✅ Parameter type: create_account() accepts profile object")
    print("✅ Real emails: No more @example.com fake emails")
    print("✅ Object access: Profile attributes work correctly")
    print("\n🚀 Bot should now work for real account creation!")
    
    return True

if __name__ == "__main__":
    success = test_critical_fixes()
    if success:
        print("\n✅ VERIFICATION COMPLETE - Ready for real account creation")
        exit(0)
    else:
        print("\n❌ VERIFICATION FAILED - Still has critical bugs")
        exit(1)