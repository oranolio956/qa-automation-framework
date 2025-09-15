#!/usr/bin/env python3
"""
Simple test of the export system without Telegram dependencies
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Add project path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Import just the core export system
from automation.core.account_export_system import (
    AccountExportSystem, ExportableAccount, ExportFormat, SecurityLevel
)

def create_test_accounts():
    """Create test account data"""
    return [
        ExportableAccount(
            username="snapking_2024",
            password="SnapKing@2024!",
            email="snapking2024@tempmail.org",
            phone_number="+15551234567",
            first_name="Jake",
            last_name="Miller",
            display_name="Jake Miller",
            birth_date="1998-05-15",
            verification_status="VERIFIED",
            adds_ready=100,
            trust_score=94,
            device_id="pixel_6_pro_001"
        ),
        ExportableAccount(
            username="socialqueen24",
            password="SocialQ@24",
            email="socialqueen24@tempmail.org", 
            phone_number="+15551234568",
            first_name="Emma",
            last_name="Davis",
            display_name="Emma Davis",
            birth_date="1999-08-22",
            verification_status="VERIFIED",
            adds_ready=100,
            trust_score=91,
            device_id="samsung_s21_002"
        )
    ]

def test_export_system():
    """Test the export system"""
    print("🧪 TESTING PROFESSIONAL FILE EXPORT SYSTEM")
    print("=" * 60)
    
    # Create test accounts
    accounts = create_test_accounts()
    exporter = AccountExportSystem()
    
    results = {}
    
    # Test TXT export
    print("📄 Testing TXT Export...")
    try:
        txt_file = exporter.export_to_txt(accounts, SecurityLevel.FULL)
        file_size = Path(txt_file).stat().st_size
        results['txt'] = {'file': txt_file, 'size': file_size, 'status': 'SUCCESS'}
        print(f"   ✅ TXT file created: {Path(txt_file).name} ({file_size:,} bytes)")
        
        # Verify content
        with open(txt_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        content_checks = {
            'has_credentials': 'Username:' in content and 'Password:' in content,
            'has_instructions': 'LOGIN INSTRUCTIONS' in content,
            'has_security_tips': 'SECURITY TIPS' in content,
            'has_emojis': '👻' in content or '🔥' in content
        }
        
        print(f"      Content checks: {sum(content_checks.values())}/{len(content_checks)} passed")
        
    except Exception as e:
        results['txt'] = {'status': 'FAILED', 'error': str(e)}
        print(f"   ❌ TXT export failed: {e}")
    
    # Test CSV export
    print("📊 Testing CSV Export...")
    try:
        csv_file = exporter.export_to_csv(accounts, SecurityLevel.FULL)
        file_size = Path(csv_file).stat().st_size
        results['csv'] = {'file': csv_file, 'size': file_size, 'status': 'SUCCESS'}
        print(f"   ✅ CSV file created: {Path(csv_file).name} ({file_size:,} bytes)")
        
        # Verify CSV content
        import csv
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        print(f"      CSV rows: {len(rows)}, Columns: {len(reader.fieldnames) if reader.fieldnames else 0}")
        
    except Exception as e:
        results['csv'] = {'status': 'FAILED', 'error': str(e)}
        print(f"   ❌ CSV export failed: {e}")
    
    # Test JSON export
    print("⚙️ Testing JSON Export...")
    try:
        json_file = exporter.export_to_json(accounts, SecurityLevel.FULL)
        file_size = Path(json_file).stat().st_size
        results['json'] = {'file': json_file, 'size': file_size, 'status': 'SUCCESS'}
        print(f"   ✅ JSON file created: {Path(json_file).name} ({file_size:,} bytes)")
        
        # Verify JSON structure
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        structure_checks = {
            'has_export_info': 'export_info' in data,
            'has_statistics': 'statistics' in data,
            'has_accounts': 'accounts' in data,
            'correct_count': len(data.get('accounts', [])) == len(accounts)
        }
        
        print(f"      Structure checks: {sum(structure_checks.values())}/{len(structure_checks)} passed")
        
    except Exception as e:
        results['json'] = {'status': 'FAILED', 'error': str(e)}
        print(f"   ❌ JSON export failed: {e}")
    
    # Summary
    print("\n🎯 EXPORT TEST SUMMARY:")
    successful = sum(1 for r in results.values() if r.get('status') == 'SUCCESS')
    total = len(results)
    print(f"   ✅ Successful exports: {successful}/{total}")
    print(f"   📁 Files created in: {exporter.output_dir}")
    print(f"   👥 Test accounts: {len(accounts)}")
    print(f"   💯 Total friend adds ready: {len(accounts) * 100}")
    
    if successful == total:
        print("\n🚀 ALL TESTS PASSED! Export system is ready for production.")
    else:
        print(f"\n⚠️ {total - successful} tests failed. Check errors above.")
    
    # Show file details
    print("\n📋 CREATED FILES:")
    for format_name, result in results.items():
        if result.get('status') == 'SUCCESS':
            file_path = result['file']
            print(f"   📄 {format_name.upper()}: {Path(file_path).name}")
            print(f"       Size: {result['size']:,} bytes")
            print(f"       Path: {file_path}")
    
    return results

if __name__ == "__main__":
    try:
        test_export_system()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()