#!/usr/bin/env python3
"""
Test Bulk Account Creation - Verify 50 accounts can be created
"""

import asyncio
import time
import json
from simple_account_creator_test import SimpleAccountCreator

async def test_bulk_creation():
    creator = SimpleAccountCreator()
    
    print("🔥 TESTING BULK ACCOUNT CREATION - 50 ACCOUNTS")
    print("=" * 60)
    
    start_time = time.time()
    
    # Create 50 accounts
    print("📊 Creating 50 accounts...")
    accounts = await creator.create_multiple_accounts(50)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Verify all accounts were created
    print(f"\n✅ BULK CREATION TEST RESULTS:")
    print("=" * 60)
    print(f"📈 Accounts requested: 50")
    print(f"📈 Accounts created: {len(accounts)}")
    print(f"⏱️ Total time: {total_time:.1f} seconds")
    print(f"⚡ Average time per account: {total_time / len(accounts):.2f} seconds")
    print(f"🔥 Success rate: {len(accounts)/50*100:.1f}%")
    
    # Show first 5 accounts as sample
    print(f"\n🎯 SAMPLE ACCOUNTS (first 5):")
    print("-" * 60)
    for i, account in enumerate(accounts[:5], 1):
        print(f"#{i}. {account['first_name']} {account['last_name']}")
        print(f"   Username: {account['username']}")
        print(f"   Password: {account['password']}")
        print(f"   Email: {account['email']}")
        print(f"   Phone: {account['phone_number']}")
        print(f"   Status: {account['status']}")
        print()
    
    # Save to file
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"bulk_test_50_accounts_{timestamp}.json"
    with open(filename, 'w') as f:
        json.dump(accounts, f, indent=2)
    
    print(f"💾 All 50 accounts saved to: {filename}")
    
    # Verify uniqueness
    usernames = [acc['username'] for acc in accounts]
    passwords = [acc['password'] for acc in accounts]
    emails = [acc['email'] for acc in accounts]
    
    print(f"\n🔍 UNIQUENESS CHECK:")
    print(f"   Unique usernames: {len(set(usernames))}/50")
    print(f"   Unique passwords: {len(set(passwords))}/50")
    print(f"   Unique emails: {len(set(emails))}/50")
    
    if len(set(usernames)) == 50 and len(set(passwords)) == 50:
        print("✅ ALL ACCOUNTS ARE UNIQUE!")
    else:
        print("⚠️ Some duplicates found")
    
    return len(accounts) == 50

if __name__ == "__main__":
    success = asyncio.run(test_bulk_creation())
    if success:
        print("\n🎉 BULK CREATION TEST PASSED! 50 accounts created successfully.")
    else:
        print("\n❌ BULK CREATION TEST FAILED!")