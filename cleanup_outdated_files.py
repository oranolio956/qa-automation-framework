#!/usr/bin/env python3
"""
Cleanup Script - Remove outdated/conflicting bot and integration files
Keep only the essential production files
"""

import os
import shutil

def cleanup_files():
    """Remove outdated and conflicting files"""
    
    # Files to KEEP (production essentials)
    keep_files = {
        # Main production bot
        '/Users/daltonmetzler/Desktop/Tinder/final_production_bot.py',
        
        # Core automation system
        '/Users/daltonmetzler/Desktop/Tinder/automation/telegram_bot/snap_command_orchestrator.py',
        '/Users/daltonmetzler/Desktop/Tinder/automation/snapchat/stealth_creator.py',
        '/Users/daltonmetzler/Desktop/Tinder/automation/telegram_bot/main_bot.py',  # Original main bot
        
        # Core integrations (keep the main ones)
        '/Users/daltonmetzler/Desktop/Tinder/automation/core/bot_integration_interface.py',
        '/Users/daltonmetzler/Desktop/Tinder/automation/core/database_integration.py',
        '/Users/daltonmetzler/Desktop/Tinder/automation/email/email_integration.py',
    }
    
    # Files to REMOVE (outdated/conflicting)
    remove_files = [
        # Duplicate/test bots
        '/Users/daltonmetzler/Desktop/Tinder/telegram_bot/bot.py',
        '/Users/daltonmetzler/Desktop/Tinder/telegram_bot/simple_bot.py',
        '/Users/daltonmetzler/Desktop/Tinder/run_snap_bot.py',
        '/Users/daltonmetzler/Desktop/Tinder/automation/telegram_bot/enhanced_main_bot.py',
        '/Users/daltonmetzler/Desktop/Tinder/automation/telegram_bot/run_bot.py',
        '/Users/daltonmetzler/Desktop/Tinder/automation/telegram_bot/test_bot.py',
        '/Users/daltonmetzler/Desktop/Tinder/live_snap_bot.py',
        '/Users/daltonmetzler/Desktop/Tinder/production_snap_bot.py',
        '/Users/daltonmetzler/Desktop/Tinder/clean_bot_responses.py',
        '/Users/daltonmetzler/Desktop/Tinder/emergency_clean_bot.py',
        '/Users/daltonmetzler/Desktop/Tinder/minimal_progress_bot.py',
        '/Users/daltonmetzler/Desktop/Tinder/final_clean_bot.py',
        '/Users/daltonmetzler/Desktop/Tinder/live_progress_bot.py',
        '/Users/daltonmetzler/Desktop/Tinder/webhook_bot.py',
        '/Users/daltonmetzler/Desktop/Tinder/simple_bot_launcher.py',
        '/Users/daltonmetzler/Desktop/Tinder/perfectly_clean_bot.py',
        '/Users/daltonmetzler/Desktop/Tinder/real_account_bot.py',
        '/Users/daltonmetzler/Desktop/Tinder/production_real_bot.py',
        
        # Duplicate/test integrations
        '/Users/daltonmetzler/Desktop/Tinder/automation/core/integration_utilities.py',
        '/Users/daltonmetzler/Desktop/Tinder/automation/core/integration_examples.py',
        '/Users/daltonmetzler/Desktop/Tinder/automation/core/comprehensive_integration_test.py',
        '/Users/daltonmetzler/Desktop/Tinder/simple_integration_test.py',
        '/Users/daltonmetzler/Desktop/Tinder/test_basic_integration.py',
        '/Users/daltonmetzler/Desktop/Tinder/automation/test_live_integration.py',
        '/Users/daltonmetzler/Desktop/Tinder/test_complete_integration.py',
        '/Users/daltonmetzler/Desktop/Tinder/test_enhanced_integration.py',
        '/Users/daltonmetzler/Desktop/Tinder/test_core_integration.py',
        '/Users/daltonmetzler/Desktop/Tinder/automation/telegram_bot/complete_snap_integration.py',
        '/Users/daltonmetzler/Desktop/Tinder/clean_snap_integration.py',
        
        # Test files
        '/Users/daltonmetzler/Desktop/Tinder/test_deployment_fix.py',
        '/Users/daltonmetzler/Desktop/Tinder/test_flyctl_fix.py',
        '/Users/daltonmetzler/Desktop/Tinder/fix_all_formatting.py',
        '/Users/daltonmetzler/Desktop/Tinder/simple_progress_callback.py',
    ]
    
    removed_count = 0
    kept_count = 0
    
    print("🧹 Cleaning up outdated and conflicting files...")
    
    for file_path in remove_files:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"✅ Removed: {os.path.basename(file_path)}")
                removed_count += 1
            else:
                print(f"⚠️ Not found: {os.path.basename(file_path)}")
        except Exception as e:
            print(f"❌ Failed to remove {os.path.basename(file_path)}: {e}")
    
    print(f"\n📊 Cleanup Summary:")
    print(f"Files removed: {removed_count}")
    print(f"Essential files kept: {len(keep_files)}")
    
    print(f"\n✅ Essential files remaining:")
    for file_path in keep_files:
        if os.path.exists(file_path):
            print(f"  ✓ {os.path.basename(file_path)}")
            kept_count += 1
        else:
            print(f"  ❌ Missing: {os.path.basename(file_path)}")
    
    print(f"\n🎯 Production bot ready: final_production_bot.py")
    print(f"🔧 Core system: snap_command_orchestrator.py")
    print(f"🤖 Snapchat creator: stealth_creator.py")

if __name__ == "__main__":
    cleanup_files()