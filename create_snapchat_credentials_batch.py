#!/usr/bin/env python3
"""
Snapchat Credential Batch Generator
This script demonstrates what ACTUALLY works - generating complete account credentials
for manual or future automated account creation.
"""

import os
import sys
import json
import csv
import time
from pathlib import Path
from datetime import datetime

# Add automation modules to path
sys.path.insert(0, 'automation')
sys.path.insert(0, 'utils')

def create_snapchat_credentials_batch(count=10, names=None):
    """Generate a batch of Snapchat account credentials"""
    print(f"🚀 GENERATING {count} SNAPCHAT ACCOUNT CREDENTIALS")
    print("="*60)
    
    try:
        from automation.snapchat.stealth_creator import SnapchatStealthCreator
        creator = SnapchatStealthCreator()
        
        if not names:
            # Default names for generation
            names = [
                "Emma", "Sarah", "Ashley", "Jessica", "Madison", 
                "Taylor", "Hannah", "Samantha", "Alexis", "Rachel",
                "Lauren", "Alyssa", "Kayla", "Abigail", "Megan",
                "Sydney", "Kaitlyn", "Paige", "Jenna", "Chloe"
            ]
        
        accounts = []
        success_count = 0
        
        for i in range(count):
            try:
                name = names[i % len(names)]
                print(f"Generating account {i+1}/{count} for {name}...")
                
                profile = creator.generate_stealth_profile(name)
                
                account_data = {
                    'id': i + 1,
                    'username': profile.username,
                    'email': profile.email,
                    'password': profile.password,
                    'phone_number': profile.phone_number,
                    'display_name': profile.display_name,
                    'birth_date': str(profile.birth_date),
                    'bio': profile.bio if profile.bio else f"Hey, I'm {profile.display_name}!",
                    'generated_at': datetime.now().isoformat(),
                    'status': 'credentials_ready',
                    'platform': 'snapchat',
                    'creation_method': 'automated_generation'
                }
                
                accounts.append(account_data)
                success_count += 1
                
                print(f"  ✅ {profile.username} - {profile.email}")
                
            except Exception as e:
                print(f"  ❌ Failed to generate account {i+1}: {e}")
        
        return accounts, success_count
        
    except Exception as e:
        print(f"❌ Failed to initialize account generator: {e}")
        return [], 0

def save_accounts_multiple_formats(accounts, batch_name="snapchat_batch"):
    """Save accounts in multiple formats for different use cases"""
    timestamp = int(time.time())
    output_dir = Path(f'snapchat_credentials_{timestamp}')
    output_dir.mkdir(exist_ok=True)
    
    formats_saved = []
    
    # 1. JSON format (for APIs and automation)
    json_file = output_dir / f'{batch_name}.json'
    batch_data = {
        'batch_info': {
            'name': batch_name,
            'created_at': datetime.now().isoformat(),
            'total_accounts': len(accounts),
            'generation_method': 'snapchat_stealth_creator',
            'status': 'ready_for_manual_creation'
        },
        'accounts': accounts
    }
    
    with open(json_file, 'w') as f:
        json.dump(batch_data, f, indent=2)
    formats_saved.append(('JSON', str(json_file)))
    
    # 2. TXT format (human readable)
    txt_file = output_dir / f'{batch_name}.txt'
    with open(txt_file, 'w') as f:
        f.write(f"SNAPCHAT ACCOUNT CREDENTIALS - {batch_name.upper()}\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Accounts: {len(accounts)}\n")
        f.write(f"Status: Ready for manual creation on Snapchat\n\n")
        f.write("NOTE: These are generated credentials. Accounts must be\n")
        f.write("manually created on Snapchat due to missing automation.\n")
        f.write("="*60 + "\n\n")
        
        for account in accounts:
            f.write(f"Account #{account['id']}:\n")
            f.write(f"Username: {account['username']}\n")
            f.write(f"Email: {account['email']}\n")
            f.write(f"Password: {account['password']}\n")
            f.write(f"Phone: {account['phone_number']}\n")
            f.write(f"Display Name: {account['display_name']}\n")
            f.write(f"Birth Date: {account['birth_date']}\n")
            f.write(f"Bio: {account['bio']}\n")
            f.write("-" * 40 + "\n")
    
    formats_saved.append(('TXT', str(txt_file)))
    
    # 3. CSV format (for spreadsheets)
    csv_file = output_dir / f'{batch_name}.csv'
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'ID', 'Username', 'Email', 'Password', 'Phone', 'Display_Name', 
            'Birth_Date', 'Bio', 'Status', 'Generated_At'
        ])
        
        for account in accounts:
            writer.writerow([
                account['id'],
                account['username'], 
                account['email'],
                account['password'],
                account['phone_number'],
                account['display_name'],
                account['birth_date'],
                account['bio'],
                account['status'],
                account['generated_at']
            ])
    
    formats_saved.append(('CSV', str(csv_file)))
    
    # 4. Bot integration format (for Telegram delivery)
    bot_file = output_dir / f'{batch_name}_bot_format.json'
    bot_data = {
        'delivery_ready': True,
        'batch_id': timestamp,
        'total_accounts': len(accounts),
        'accounts_for_delivery': [
            {
                'account_id': acc['id'],
                'username': acc['username'],
                'credentials': {
                    'email': acc['email'],
                    'password': acc['password'],
                    'phone': acc['phone_number']
                },
                'profile_info': {
                    'display_name': acc['display_name'],
                    'birth_date': acc['birth_date'],
                    'bio': acc['bio']
                },
                'status': 'ready_for_manual_creation',
                'platform': 'snapchat'
            }
            for acc in accounts
        ],
        'delivery_instructions': {
            'manual_creation_required': True,
            'automation_status': 'not_available',
            'estimated_manual_time_per_account': '5-10 minutes'
        }
    }
    
    with open(bot_file, 'w') as f:
        json.dump(bot_data, f, indent=2)
    formats_saved.append(('Bot Format', str(bot_file)))
    
    return formats_saved, output_dir

def generate_profile_pictures_batch(accounts, output_dir):
    """Generate profile pictures for the accounts"""
    print(f"\n🖼️ Generating profile pictures...")
    
    try:
        from automation.snapchat.stealth_creator import ProfilePictureGenerator
        pic_generator = ProfilePictureGenerator()
        
        pictures_generated = []
        
        for account in accounts[:5]:  # Generate for first 5 accounts to demo
            try:
                username = account['username']
                display_name = account['display_name']
                
                pic_path = pic_generator.generate_profile_picture(display_name)
                
                if pic_path and Path(pic_path).exists():
                    pictures_generated.append({
                        'username': username,
                        'picture_path': pic_path,
                        'file_size': Path(pic_path).stat().st_size
                    })
                    print(f"  ✅ Generated picture for {username}")
                else:
                    print(f"  ⚠️  No picture generated for {username}")
                    
            except Exception as e:
                print(f"  ❌ Picture generation failed for {username}: {e}")
        
        # Save picture info
        if pictures_generated:
            pics_file = output_dir / 'profile_pictures_info.json'
            with open(pics_file, 'w') as f:
                json.dump({
                    'generated_pictures': pictures_generated,
                    'total_generated': len(pictures_generated)
                }, f, indent=2)
        
        return pictures_generated
        
    except Exception as e:
        print(f"  ❌ Profile picture generation failed: {e}")
        return []

def create_delivery_summary(accounts, formats_saved, pictures, output_dir):
    """Create a summary of what can be delivered"""
    summary = {
        'delivery_summary': {
            'date': datetime.now().isoformat(),
            'total_accounts': len(accounts),
            'credentials_ready': len(accounts),
            'pictures_generated': len(pictures),
            'formats_available': len(formats_saved)
        },
        'what_we_can_deliver': {
            'complete_account_credentials': True,
            'profile_pictures': len(pictures) > 0,
            'multiple_formats': True,
            'bot_integration_ready': True
        },
        'what_we_cannot_deliver': {
            'active_snapchat_accounts': True,
            'sms_verified_accounts': True,
            'automated_account_creation': True,
            'reason': 'Core automation methods not implemented'
        },
        'manual_creation_required': {
            'time_per_account': '5-10 minutes',
            'success_rate_estimate': '80-90%',
            'tools_needed': ['Android device or emulator', 'SMS verification capability']
        },
        'files_generated': [{'format': fmt, 'path': path} for fmt, path in formats_saved]
    }
    
    summary_file = output_dir / 'DELIVERY_SUMMARY.json'
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    return summary, summary_file

def main():
    """Main credential generation function"""
    print("🚀 SNAPCHAT CREDENTIAL BATCH GENERATOR")
    print("="*70)
    print("This tool generates complete Snapchat account credentials")
    print("for manual account creation or future automation.")
    print("="*70)
    
    # Configuration
    account_count = 10
    batch_name = f"snapchat_batch_{int(time.time())}"
    
    # Generate accounts
    print(f"\n🎯 Generating {account_count} account credentials...")
    accounts, success_count = create_snapchat_credentials_batch(account_count)
    
    if success_count == 0:
        print("❌ No accounts generated. Check system setup.")
        return
    
    print(f"\n✅ Successfully generated {success_count}/{account_count} accounts")
    
    # Save in multiple formats
    print(f"\n💾 Saving accounts in multiple formats...")
    formats_saved, output_dir = save_accounts_multiple_formats(accounts, batch_name)
    
    for format_type, file_path in formats_saved:
        print(f"  ✅ {format_type}: {file_path}")
    
    # Generate profile pictures
    pictures = generate_profile_pictures_batch(accounts, output_dir)
    
    # Create delivery summary
    summary, summary_file = create_delivery_summary(accounts, formats_saved, pictures, output_dir)
    
    # Final output
    print(f"\n🎉 BATCH GENERATION COMPLETE")
    print("="*50)
    print(f"Accounts Generated: {success_count}")
    print(f"Formats Available: {len(formats_saved)}")
    print(f"Pictures Generated: {len(pictures)}")
    print(f"Output Directory: {output_dir}")
    
    print(f"\n📁 FILES CREATED:")
    for format_type, file_path in formats_saved:
        print(f"  - {format_type}: {Path(file_path).name}")
    if pictures:
        print(f"  - Profile Pictures: {len(pictures)} images")
    print(f"  - Delivery Summary: {summary_file.name}")
    
    print(f"\n✅ READY FOR DELIVERY:")
    print(f"  - Complete account credentials: ✅")
    print(f"  - Multiple export formats: ✅")
    print(f"  - Profile pictures: {'✅' if pictures else '⚠️  (limited)'}")
    print(f"  - Bot integration format: ✅")
    
    print(f"\n❌ NOT AVAILABLE:")
    print(f"  - Active Snapchat accounts: ❌ (automation missing)")
    print(f"  - SMS verification: ❌ (Twilio not configured)")
    print(f"  - Automated creation: ❌ (core methods missing)")
    
    print(f"\n📈 NEXT STEPS:")
    print(f"  1. Use generated credentials for manual account creation")
    print(f"  2. Implement missing automation methods for auto-creation")
    print(f"  3. Set up SMS verification service")
    print(f"  4. Add anti-detection measures before automation")
    
    return success_count > 0

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Generation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Generation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
