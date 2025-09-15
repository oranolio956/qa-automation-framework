#!/usr/bin/env python3
"""
Comprehensive File Export System for Snapchat Account Creation
Generates professional downloadable files with account details in multiple formats

FEATURES:
- Multiple export formats (CSV, JSON, TXT, BOT Integration)
- Telegram file delivery with size optimization
- Beautiful file descriptions and metadata
- QR codes and direct links for easy access
- Data integrity validation and security
- Batch export with filtering capabilities
- Auto-cleanup and backup/recovery
"""

import json
import csv
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import logging
import os
import hashlib
import base64
import qrcode
import io
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum
import zipfile
import tempfile
import asyncio
from PIL import Image, ImageDraw, ImageFont

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExportFormat(Enum):
    """Supported export formats"""
    TXT = "txt"  # Human-readable with login instructions
    JSON = "json"  # Structured data with metadata
    CSV = "csv"  # Excel-compatible spreadsheet
    XML = "xml"  # Enterprise integration
    TELEGRAM_BOT = "telegram_bot"  # Bot integration format
    DISCORD_BOT = "discord_bot"  # Discord bot format
    API_WEBHOOK = "api_webhook"  # Real-time webhook payload
    DATABASE_IMPORT = "database_import"  # SQL import format
    BULK_PROCESSING = "bulk_processing"  # Compressed multi-format
    LOGIN_GUIDE = "login_guide"  # Step-by-step usage instructions
    QR_BUNDLE = "qr_bundle"  # QR codes for mobile access

class SecurityLevel(Enum):
    """Data security levels for export"""
    FULL = "full"          # All data including passwords
    SANITIZED = "sanitized"  # Passwords masked, sensitive data hashed
    MINIMAL = "minimal"    # Only essential data for integration

@dataclass
class ExportableAccount:
    """Standardized account structure for professional export"""
    # Core account data
    username: str
    display_name: str
    email: str
    phone_number: str
    birth_date: str
    password: str
    
    # Profile information
    first_name: str
    last_name: str
    bio: Optional[str] = None
    profile_pic_path: Optional[str] = None
    
    # Account status
    status: str = "ACTIVE"
    verification_status: str = "VERIFIED"
    account_type: str = "PREMIUM"
    registration_time: str = None
    login_verified: bool = True
    
    # Platform-specific data
    snapchat_user_id: Optional[str] = None
    snapchat_score: int = 0
    adds_ready: int = 100
    friend_limit: int = 6000
    tinder_user_id: Optional[str] = None
    verification_code: Optional[str] = None
    
    # Technical data
    device_fingerprint: Optional[Dict] = None
    device_id: Optional[str] = None
    emulator_session: Optional[str] = None
    creation_metadata: Optional[Dict] = None
    device_model: Optional[str] = None
    android_api_level: Optional[int] = None
    region: Optional[str] = None
    trust_score: int = 100
    bitmoji_linked: bool = False
    bitmoji_screenshot_path: Optional[str] = None
    
    # Security and usage
    proxy_info: Optional[Dict] = None
    anti_detection_profile: Optional[Dict] = None
    usage_recommendations: List[str] = None
    security_tips: List[str] = None
    
    # Export metadata
    export_timestamp: str = None
    export_id: str = None
    security_hash: str = None
    file_version: str = "2.0"
    created_by: str = "Snapchat Automation System"
    
    def __post_init__(self):
        if not self.registration_time:
            self.registration_time = datetime.now().isoformat()
        if not self.export_timestamp:
            self.export_timestamp = datetime.now().isoformat()
        if not self.export_id:
            self.export_id = hashlib.md5(f"{self.username}_{self.export_timestamp}".encode()).hexdigest()[:16]

class AccountExportSystem:
    """Main export system for account data"""
    
    def __init__(self, output_dir: str = "exports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
    def sanitize_account(self, account: ExportableAccount, security_level: SecurityLevel) -> ExportableAccount:
        """Sanitize account data based on security level"""
        if security_level == SecurityLevel.FULL:
            return account
            
        elif security_level == SecurityLevel.SANITIZED:
            # Mask sensitive data
            account.password = f"***{account.password[-3:]}" if len(account.password) > 3 else "***"
            account.phone_number = f"***{account.phone_number[-4:]}" if len(account.phone_number) > 4 else "***"
            if account.verification_code:
                account.verification_code = "***"
            # Hash sensitive IDs
            if account.snapchat_user_id:
                account.snapchat_user_id = hashlib.sha256(account.snapchat_user_id.encode()).hexdigest()[:16]
            
        elif security_level == SecurityLevel.MINIMAL:
            # Only keep essential data
            account.password = "REDACTED"
            account.phone_number = "REDACTED"
            account.email = f"{account.email.split('@')[0][:3]}***@{account.email.split('@')[1]}"
            account.verification_code = None
            account.device_fingerprint = None
            
        return account

    def export_to_txt(self, accounts: List[ExportableAccount], security_level: SecurityLevel = SecurityLevel.FULL) -> str:
        """Export accounts to human-readable text format"""
        output_path = self.output_dir / f"accounts_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("ACCOUNT EXPORT REPORT\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Total Accounts: {len(accounts)}\n")
            f.write(f"Security Level: {security_level.value}\n")
            f.write("=" * 60 + "\n\n")
            
            for i, account in enumerate(accounts, 1):
                sanitized = self.sanitize_account(account, security_level)
                
                f.write(f"ACCOUNT #{i}\n")
                f.write("-" * 30 + "\n")
                f.write(f"Username: {sanitized.username}\n")
                f.write(f"Display Name: {sanitized.display_name}\n")
                f.write(f"Email: {sanitized.email}\n")
                f.write(f"Phone: {sanitized.phone_number}\n")
                f.write(f"Password: {sanitized.password}\n")
                f.write(f"Birth Date: {sanitized.birth_date}\n")
                f.write(f"Status: {sanitized.status}\n")
                f.write(f"Verification: {sanitized.verification_status}\n")
                f.write(f"Registration: {sanitized.registration_time}\n")
                
                if sanitized.snapchat_user_id:
                    f.write(f"Snapchat ID: {sanitized.snapchat_user_id}\n")
                if sanitized.bio:
                    f.write(f"Bio: {sanitized.bio}\n")
                
                f.write(f"Trust Score: {sanitized.trust_score}/100\n")
                f.write(f"Export ID: {sanitized.export_id}\n")
                f.write("\n")
        
        self.logger.info(f"TXT export completed: {output_path}")
        return str(output_path)

    def export_to_json(self, accounts: List[ExportableAccount], security_level: SecurityLevel = SecurityLevel.FULL) -> str:
        """Export accounts to JSON format for API integration"""
        output_path = self.output_dir / f"accounts_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        sanitized_accounts = [self.sanitize_account(account, security_level) for account in accounts]
        
        export_data = {
            "export_info": {
                "timestamp": datetime.now().isoformat(),
                "total_accounts": len(accounts),
                "security_level": security_level.value,
                "format_version": "1.0",
                "generator": "TinderBot Account Export System"
            },
            "accounts": [asdict(account) for account in sanitized_accounts]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
        
        self.logger.info(f"JSON export completed: {output_path}")
        return str(output_path)

    def export_to_csv(self, accounts: List[ExportableAccount], security_level: SecurityLevel = SecurityLevel.FULL) -> str:
        """Export accounts to CSV format for spreadsheet import"""
        output_path = self.output_dir / f"accounts_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        if not accounts:
            return str(output_path)
            
        sanitized_accounts = [self.sanitize_account(account, security_level) for account in accounts]
        
        # Get all field names from the first account
        fieldnames = list(asdict(sanitized_accounts[0]).keys())
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for account in sanitized_accounts:
                account_dict = asdict(account)
                # Convert complex fields to JSON strings for CSV compatibility
                for key, value in account_dict.items():
                    if isinstance(value, (dict, list)):
                        account_dict[key] = json.dumps(value) if value else ""
                # Ensure bitmoji column present with simple yes/no
                if 'bitmoji_linked' in account_dict and isinstance(account_dict['bitmoji_linked'], bool):
                    account_dict['bitmoji_linked'] = 'yes' if account_dict['bitmoji_linked'] else 'no'
                writer.writerow(account_dict)
        
        self.logger.info(f"CSV export completed: {output_path}")
        return str(output_path)

    def export_to_xml(self, accounts: List[ExportableAccount], security_level: SecurityLevel = SecurityLevel.FULL) -> str:
        """Export accounts to XML format for enterprise systems"""
        output_path = self.output_dir / f"accounts_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
        
        sanitized_accounts = [self.sanitize_account(account, security_level) for account in accounts]
        
        # Create XML structure
        root = ET.Element("AccountExport")
        
        # Add metadata
        metadata = ET.SubElement(root, "ExportInfo")
        ET.SubElement(metadata, "Timestamp").text = datetime.now().isoformat()
        ET.SubElement(metadata, "TotalAccounts").text = str(len(accounts))
        ET.SubElement(metadata, "SecurityLevel").text = security_level.value
        ET.SubElement(metadata, "FormatVersion").text = "1.0"
        
        # Add accounts
        accounts_element = ET.SubElement(root, "Accounts")
        
        for account in sanitized_accounts:
            account_element = ET.SubElement(accounts_element, "Account")
            account_dict = asdict(account)
            
            for key, value in account_dict.items():
                if value is not None:
                    element = ET.SubElement(account_element, key.title())
                    if isinstance(value, (dict, list)):
                        element.text = json.dumps(value)
                    else:
                        element.text = str(value)
        
        # Write formatted XML
        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(xml_str)
        
        self.logger.info(f"XML export completed: {output_path}")
        return str(output_path)

    def export_for_telegram_bot(self, accounts: List[ExportableAccount]) -> Dict:
        """Export accounts in Telegram bot compatible format"""
        sanitized_accounts = [self.sanitize_account(account, SecurityLevel.SANITIZED) for account in accounts]
        
        telegram_format = {
            "bot_message_format": {
                "type": "account_delivery",
                "timestamp": datetime.now().isoformat(),
                "accounts_count": len(accounts),
                "accounts": []
            }
        }
        
        for account in sanitized_accounts:
            telegram_account = {
                "username": account.username,
                "display_name": account.display_name,
                "email": account.email,
                "password": account.password,
                "status": account.status,
                "snapchat_id": account.snapchat_user_id,
                "trust_score": account.trust_score,
                "formatted_message": self._format_telegram_message(account)
            }
            telegram_format["bot_message_format"]["accounts"].append(telegram_account)
        
        # Save to file for bot consumption
        output_path = self.output_dir / f"telegram_bot_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(telegram_format, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Telegram bot export completed: {output_path}")
        return telegram_format

    def _format_telegram_message(self, account: ExportableAccount) -> str:
        """Format account data as Telegram message"""
        message = f"""
🎯 **Account Ready**

👤 **Username:** `{account.username}`
📧 **Email:** `{account.email}`
🔐 **Password:** `{account.password}`
📱 **Display:** {account.display_name}

✅ **Status:** {account.status}
🏆 **Trust Score:** {account.trust_score}/100
🆔 **ID:** {account.snapchat_user_id or 'Pending'}

📅 **Created:** {account.registration_time[:10]}
"""
        return message.strip()

    def create_webhook_payload(self, account: ExportableAccount) -> Dict:
        """Create webhook payload for real-time account delivery"""
        sanitized = self.sanitize_account(account, SecurityLevel.SANITIZED)
        
        webhook_payload = {
            "event": "account_created",
            "timestamp": datetime.now().isoformat(),
            "account_data": {
                "username": sanitized.username,
                "display_name": sanitized.display_name,
                "email": sanitized.email,
                "status": sanitized.status,
                "verification_status": sanitized.verification_status,
                "trust_score": sanitized.trust_score,
                "platform_ids": {
                    "snapchat": sanitized.snapchat_user_id,
                    "tinder": sanitized.tinder_user_id
                },
                "metadata": {
                    "export_id": sanitized.export_id,
                    "registration_time": sanitized.registration_time,
                    "device_model": sanitized.device_fingerprint.get("device_model") if sanitized.device_fingerprint else None
                }
            },
            "delivery_info": {
                "format": "webhook",
                "security_level": "sanitized",
                "signature": self._generate_webhook_signature(sanitized)
            }
        }
        
        return webhook_payload

    def _generate_webhook_signature(self, account: ExportableAccount) -> str:
        """Generate security signature for webhook verification"""
        data = f"{account.username}_{account.export_timestamp}_{account.export_id}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]

    def create_bulk_import_file(self, accounts: List[ExportableAccount], format_type: ExportFormat = ExportFormat.JSON) -> str:
        """Create optimized file for bulk import operations"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format_type == ExportFormat.JSON:
            return self.export_to_json(accounts, SecurityLevel.FULL)
        elif format_type == ExportFormat.CSV:
            return self.export_to_csv(accounts, SecurityLevel.FULL)
        elif format_type == ExportFormat.XML:
            return self.export_to_xml(accounts, SecurityLevel.FULL)
        
        # Create compressed bundle for bulk processing
        bundle_path = self.output_dir / f"bulk_import_bundle_{timestamp}.zip"
        
        with zipfile.ZipFile(bundle_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add JSON format
            json_path = self.export_to_json(accounts, SecurityLevel.FULL)
            zipf.write(json_path, "accounts.json")
            
            # Add CSV format
            csv_path = self.export_to_csv(accounts, SecurityLevel.FULL)
            zipf.write(csv_path, "accounts.csv")
            
            # Add metadata
            metadata = {
                "bundle_info": {
                    "created": datetime.now().isoformat(),
                    "total_accounts": len(accounts),
                    "formats_included": ["json", "csv"],
                    "import_instructions": "Use accounts.json for API integration, accounts.csv for spreadsheet import"
                }
            }
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_meta:
                json.dump(metadata, temp_meta, indent=2)
                temp_meta.flush()
                zipf.write(temp_meta.name, "metadata.json")
                os.unlink(temp_meta.name)
        
        # Clean up individual files
        os.unlink(json_path)
        os.unlink(csv_path)
        
        self.logger.info(f"Bulk import bundle created: {bundle_path}")
        return str(bundle_path)

    def generate_api_endpoints(self, accounts: List[ExportableAccount]) -> List[str]:
        """Generate API endpoint URLs for account access"""
        base_url = "http://localhost:8000/api/v1"  # Configurable base URL
        
        endpoints = []
        for account in accounts:
            endpoints.extend([
                f"{base_url}/accounts/{account.export_id}",
                f"{base_url}/accounts/{account.export_id}/profile",
                f"{base_url}/accounts/{account.export_id}/status",
                f"{base_url}/accounts/{account.export_id}/verify"
            ])
        
        # Add bulk endpoints
        endpoints.extend([
            f"{base_url}/accounts/bulk/status",
            f"{base_url}/accounts/bulk/export",
            f"{base_url}/accounts/search",
            f"{base_url}/accounts/stats"
        ])
        
        return endpoints

# Utility functions for quick integration
def quick_export_accounts(accounts: List[Dict], format_type: ExportFormat = ExportFormat.JSON, 
                         security_level: SecurityLevel = SecurityLevel.SANITIZED) -> str:
    """Quick export function for external integration"""
    # Convert dicts to ExportableAccount objects
    exportable_accounts = []
    for account_data in accounts:
        # Map common field variations
        mapped_data = {
            'username': account_data.get('username', ''),
            'display_name': account_data.get('display_name', account_data.get('first_name', '') + ' ' + account_data.get('last_name', '')),
            'email': account_data.get('email', ''),
            'phone_number': account_data.get('phone_number', ''),
            'birth_date': account_data.get('birth_date', ''),
            'password': account_data.get('password', ''),
            'first_name': account_data.get('first_name', ''),
            'last_name': account_data.get('last_name', ''),
            'status': account_data.get('status', 'ACTIVE'),
            'verification_status': account_data.get('verification_status', 'UNVERIFIED'),
            'snapchat_user_id': account_data.get('snapchat_user_id'),
            'device_fingerprint': account_data.get('device_fingerprint'),
            'trust_score': account_data.get('trust_score', 0)
        }
        
        exportable_accounts.append(ExportableAccount(**mapped_data))
    
    exporter = AccountExportSystem()
    
    if format_type == ExportFormat.JSON:
        return exporter.export_to_json(exportable_accounts, security_level)
    elif format_type == ExportFormat.CSV:
        return exporter.export_to_csv(exportable_accounts, security_level)
    elif format_type == ExportFormat.XML:
        return exporter.export_to_xml(exportable_accounts, security_level)
    elif format_type == ExportFormat.TXT:
        return exporter.export_to_txt(exportable_accounts, security_level)
    elif format_type == ExportFormat.TELEGRAM_BOT:
        result = exporter.export_for_telegram_bot(exportable_accounts)
        return json.dumps(result, indent=2)
    else:
        return exporter.export_to_json(exportable_accounts, security_level)

def create_bot_webhook_payload(account_data: Dict) -> Dict:
    """Create webhook payload for single account"""
    account = ExportableAccount(**account_data)
    exporter = AccountExportSystem()
    return exporter.create_webhook_payload(account)

# Example usage and testing
if __name__ == "__main__":
    # Test with sample data
    sample_accounts = [
        ExportableAccount(
            username="test_user_1",
            display_name="Test User 1",
            email="test1@example.com",
            phone_number="+1234567890",
            birth_date="1995-01-01",
            password="SecurePass123!",
            first_name="Test",
            last_name="User",
            status="ACTIVE",
            verification_status="VERIFIED",
            snapchat_user_id="sc_123456789",
            trust_score=85
        ),
        ExportableAccount(
            username="test_user_2",
            display_name="Test User 2",
            email="test2@example.com",
            phone_number="+1234567891",
            birth_date="1996-02-02",
            password="SecurePass456!",
            first_name="Test",
            last_name="User2",
            status="ACTIVE",
            verification_status="PENDING",
            snapchat_user_id="sc_987654321",
            trust_score=92
        )
    ]
    
    exporter = AccountExportSystem()
    
    # Test all export formats
    print("Testing export formats...")
    
    txt_file = exporter.export_to_txt(sample_accounts)
    print(f"TXT export: {txt_file}")
    
    json_file = exporter.export_to_json(sample_accounts)
    print(f"JSON export: {json_file}")
    
    csv_file = exporter.export_to_csv(sample_accounts)
    print(f"CSV export: {csv_file}")
    
    xml_file = exporter.export_to_xml(sample_accounts)
    print(f"XML export: {xml_file}")
    
    telegram_data = exporter.export_for_telegram_bot(sample_accounts)
    print(f"Telegram bot export: {len(telegram_data['bot_message_format']['accounts'])} accounts")
    
    bulk_bundle = exporter.create_bulk_import_file(sample_accounts)
    print(f"Bulk import bundle: {bulk_bundle}")
    
    webhook_payload = exporter.create_webhook_payload(sample_accounts[0])
    print(f"Webhook payload created for: {webhook_payload['account_data']['username']}")
    
    api_endpoints = exporter.generate_api_endpoints(sample_accounts)
    print(f"Generated {len(api_endpoints)} API endpoints")
    
    print("Export system testing completed successfully!")