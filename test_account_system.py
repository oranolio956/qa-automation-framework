#!/usr/bin/env python3
"""
Quick test of the account creation system
"""

import asyncio
from real_snapchat_registration import RealSnapchatAccountCreator

async def test_creation():
    creator = RealSnapchatAccountCreator()
    
    print("TESTING REAL SNAPCHAT ACCOUNT SYSTEM")
    print("=" * 50)
    
    # Test creating 2 accounts
    accounts_created, failed_accounts = await creator.create_multiple_accounts(2)
    
    print(f"\nRESULTS:")
    print(f"Created: {len(accounts_created)}")
    print(f"Failed: {len(failed_accounts)}")
    
    if accounts_created:
        print("\nFIRST ACCOUNT DETAILS:")
        account = accounts_created[0]
        print(f"Username: {account['username']}")
        print(f"Password: {account['password']}")
        print(f"Email: {account.get('email', 'N/A')}")
        print(f"Phone: {account.get('phone_number', 'N/A')}")
        print(f"Status: {account.get('status', 'Unknown')}")
        print(f"Login Verified: {account.get('login_verified', False)}")
        
        creator.save_accounts_to_file(accounts_created, "test_accounts.json")

if __name__ == "__main__":
    asyncio.run(test_creation())