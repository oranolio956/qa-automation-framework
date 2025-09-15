#!/usr/bin/env python3
"""
Test Telegram bot integration end-to-end
"""

import asyncio
import sys
import os
sys.path.append('/Users/daltonmetzler/Desktop/Tinder')

from real_snapchat_registration import RealSnapchatAccountCreator

async def test_telegram_integration():
    """Test the same flow that Telegram bot would use"""
    print("TESTING TELEGRAM BOT INTEGRATION FLOW")
    print("=" * 50)
    
    # Simulate Telegram bot requesting 3 accounts in batch processing
    creator = RealSnapchatAccountCreator()
    
    num_accounts = 3
    batches_needed = (num_accounts + 49) // 50  # Same calculation as Telegram bot
    
    print(f"User requested: {num_accounts} accounts")
    print(f"Batches needed: {batches_needed}")
    
    # Process the same way as Telegram bot
    all_accounts_created = []
    all_failed_accounts = []
    
    for batch_num in range(batches_needed):
        batch_start = batch_num * 50
        batch_size = min(50, num_accounts - batch_start)
        
        print(f"\nProcessing batch {batch_num + 1}/{batches_needed}")
        print(f"Creating {batch_size} accounts...")
        
        # Create this batch (same as Telegram bot logic)
        batch_accounts, batch_failed = await creator.create_multiple_accounts(batch_size)
        all_accounts_created.extend(batch_accounts)
        all_failed_accounts.extend(batch_failed)
        
        print(f"Batch {batch_num + 1} complete")
        print(f"Created: {len(batch_accounts)}, Failed: {len(batch_failed)}")
        print(f"Total created so far: {len(all_accounts_created)}/{num_accounts}")
    
    # Display results same as Telegram bot
    if all_accounts_created:
        print(f"\nACCOUNT CREATION COMPLETE")
        print(f"Successfully Created: {len(all_accounts_created)}")
        print(f"Failed: {len(all_failed_accounts)}")
        
        login_verified_count = sum(1 for acc in all_accounts_created if acc.get('login_verified', False))
        print(f"\nLOGIN VERIFICATION RESULTS:")
        print(f"Accounts with verified login: {login_verified_count}/{len(all_accounts_created)}")
        print(f"Login success rate: {login_verified_count/len(all_accounts_created)*100:.1f}%")
        
        print(f"\nSAMPLE ACCOUNT:")
        account = all_accounts_created[0]
        print(f"Username: {account['username']}")
        print(f"Password: {account['password']}")
        print(f"Email: {account.get('email', 'N/A')}")
        print(f"Phone: {account.get('phone_number', 'N/A')}")
        print(f"Login Test: {'LOGIN VERIFIED' if account.get('login_verified', False) else 'LOGIN FAILED'}")
        print(f"Device: {account.get('device_fingerprint', {}).get('device_model', 'N/A')}")
        
        # Save just like Telegram bot
        import json
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"telegram_test_accounts_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(all_accounts_created, f, indent=2)
        
        print(f"\nAll credentials saved to: {filename}")
        print("\n✅ TELEGRAM BOT INTEGRATION TEST PASSED!")
        
        return True
    else:
        print("❌ TELEGRAM BOT INTEGRATION TEST FAILED!")
        return False

if __name__ == "__main__":
    asyncio.run(test_telegram_integration())