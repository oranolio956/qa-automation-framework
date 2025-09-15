#!/usr/bin/env python3
"""
Secure Credentials Management System
Handles sensitive credentials with encryption and secure storage
"""

import os
import sys
import json
import logging
import asyncio
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import secrets
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class CredentialEntry:
    """Secure credential entry with metadata"""
    name: str
    value: str
    encrypted: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    usage_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

class CredentialsManager:
    """Secure credentials manager with encryption and rotation"""
    
    def __init__(self, master_password: Optional[str] = None):
        self.master_password = master_password or os.getenv('MASTER_PASSWORD')
        self.credentials_file = os.path.join(os.path.dirname(__file__), 'credentials.enc')
        self.encryption_key = None
        self._credentials_cache = {}
        self._salt = None
        
        # Initialize encryption if master password is provided
        if self.master_password:
            self._initialize_encryption()
        
        # Load existing credentials
        self._load_credentials()
    
    def _initialize_encryption(self):
        """Initialize encryption system with master password"""
        try:
            # Generate or load salt
            salt_file = os.path.join(os.path.dirname(__file__), 'salt.key')
            
            if os.path.exists(salt_file):
                with open(salt_file, 'rb') as f:
                    self._salt = f.read()
            else:
                self._salt = os.urandom(16)
                with open(salt_file, 'wb') as f:
                    f.write(self._salt)
                os.chmod(salt_file, 0o600)  # Read-only for owner
            
            # Derive key from master password
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self._salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.master_password.encode()))
            self.encryption_key = Fernet(key)
            
            logger.info("🔐 Encryption initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize encryption: {e}")
            self.encryption_key = None
    
    def _encrypt_value(self, value: str) -> str:
        """Encrypt a credential value"""
        if not self.encryption_key:
            logger.warning("⚠️ No encryption key available, storing as plaintext")
            return value
        
        try:
            encrypted_value = self.encryption_key.encrypt(value.encode())
            return base64.urlsafe_b64encode(encrypted_value).decode()
        except Exception as e:
            logger.error(f"❌ Failed to encrypt value: {e}")
            return value
    
    def _decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt a credential value"""
        if not self.encryption_key:
            logger.warning("⚠️ No encryption key available, returning as-is")
            return encrypted_value
        
        try:
            encrypted_data = base64.urlsafe_b64decode(encrypted_value.encode())
            decrypted_value = self.encryption_key.decrypt(encrypted_data)
            return decrypted_value.decode()
        except Exception as e:
            logger.error(f"❌ Failed to decrypt value: {e}")
            return encrypted_value
    
    def _load_credentials(self):
        """Load credentials from encrypted file"""
        if not os.path.exists(self.credentials_file):
            logger.info("📁 No existing credentials file found")
            return
        
        try:
            with open(self.credentials_file, 'r') as f:
                encrypted_data = json.load(f)
            
            for name, data in encrypted_data.items():
                credential = CredentialEntry(
                    name=name,
                    value=data['value'],
                    encrypted=data.get('encrypted', False),
                    created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
                    expires_at=datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None,
                    last_used=datetime.fromisoformat(data['last_used']) if data.get('last_used') else None,
                    usage_count=data.get('usage_count', 0),
                    metadata=data.get('metadata', {})
                )
                self._credentials_cache[name] = credential
            
            logger.info(f"📥 Loaded {len(self._credentials_cache)} credentials")
            
        except Exception as e:
            logger.error(f"❌ Failed to load credentials: {e}")
    
    def _save_credentials(self):
        """Save credentials to encrypted file"""
        try:
            # Convert credentials to serializable format
            serializable_data = {}
            for name, credential in self._credentials_cache.items():
                serializable_data[name] = {
                    'value': credential.value,
                    'encrypted': credential.encrypted,
                    'created_at': credential.created_at.isoformat(),
                    'expires_at': credential.expires_at.isoformat() if credential.expires_at else None,
                    'last_used': credential.last_used.isoformat() if credential.last_used else None,
                    'usage_count': credential.usage_count,
                    'metadata': credential.metadata
                }
            
            # Save to file with proper permissions
            with open(self.credentials_file, 'w') as f:
                json.dump(serializable_data, f, indent=2)
            
            # Set restrictive permissions
            os.chmod(self.credentials_file, 0o600)
            
            logger.info(f"💾 Saved {len(self._credentials_cache)} credentials")
            
        except Exception as e:
            logger.error(f"❌ Failed to save credentials: {e}")
    
    def set_credential(self, name: str, value: str, 
                      encrypt: bool = True, 
                      expires_days: Optional[int] = None,
                      metadata: Optional[Dict[str, Any]] = None):
        """Set a credential with optional encryption and expiration"""
        try:
            # Encrypt value if requested and encryption is available
            stored_value = self._encrypt_value(value) if encrypt and self.encryption_key else value
            encrypted = encrypt and self.encryption_key is not None
            
            # Calculate expiration date
            expires_at = None
            if expires_days:
                expires_at = datetime.now() + timedelta(days=expires_days)
            
            # Create credential entry
            credential = CredentialEntry(
                name=name,
                value=stored_value,
                encrypted=encrypted,
                expires_at=expires_at,
                metadata=metadata or {}
            )
            
            self._credentials_cache[name] = credential
            self._save_credentials()
            
            logger.info(f"✅ Set credential '{name}' {'(encrypted)' if encrypted else '(plaintext)'}")
            
        except Exception as e:
            logger.error(f"❌ Failed to set credential '{name}': {e}")
            raise
    
    def get_credential(self, name: str) -> Optional[str]:
        """Get a credential value, decrypting if necessary"""
        try:
            credential = self._credentials_cache.get(name)
            if not credential:
                logger.debug(f"🔍 Credential '{name}' not found")
                return None
            
            # Check expiration
            if credential.expires_at and datetime.now() > credential.expires_at:
                logger.warning(f"⏰ Credential '{name}' has expired")
                return None
            
            # Update usage tracking
            credential.last_used = datetime.now()
            credential.usage_count += 1
            
            # Decrypt if necessary
            value = self._decrypt_value(credential.value) if credential.encrypted else credential.value
            
            logger.debug(f"📤 Retrieved credential '{name}'")
            return value
            
        except Exception as e:
            logger.error(f"❌ Failed to get credential '{name}': {e}")
            return None
    
    def has_credential(self, name: str) -> bool:
        """Check if a credential exists and is valid"""
        credential = self._credentials_cache.get(name)
        if not credential:
            return False
        
        # Check expiration
        if credential.expires_at and datetime.now() > credential.expires_at:
            return False
        
        return True
    
    def delete_credential(self, name: str) -> bool:
        """Delete a credential"""
        try:
            if name in self._credentials_cache:
                del self._credentials_cache[name]
                self._save_credentials()
                logger.info(f"🗑️ Deleted credential '{name}'")
                return True
            else:
                logger.warning(f"⚠️ Credential '{name}' not found for deletion")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to delete credential '{name}': {e}")
            return False
    
    def list_credentials(self) -> Dict[str, Dict[str, Any]]:
        """List all credentials with metadata (without values)"""
        credentials_info = {}
        
        for name, credential in self._credentials_cache.items():
            # Check if expired
            expired = credential.expires_at and datetime.now() > credential.expires_at
            
            credentials_info[name] = {
                'created_at': credential.created_at.isoformat(),
                'expires_at': credential.expires_at.isoformat() if credential.expires_at else None,
                'last_used': credential.last_used.isoformat() if credential.last_used else None,
                'usage_count': credential.usage_count,
                'encrypted': credential.encrypted,
                'expired': expired,
                'metadata': credential.metadata
            }
        
        return credentials_info
    
    def rotate_credential(self, name: str, new_value: str) -> bool:
        """Rotate a credential to a new value"""
        try:
            if not self.has_credential(name):
                logger.error(f"❌ Cannot rotate non-existent credential '{name}'")
                return False
            
            old_credential = self._credentials_cache[name]
            
            # Create new credential with same settings but new value
            self.set_credential(
                name=name,
                value=new_value,
                encrypt=old_credential.encrypted,
                metadata={**old_credential.metadata, 'rotated_at': datetime.now().isoformat()}
            )
            
            logger.info(f"🔄 Rotated credential '{name}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to rotate credential '{name}': {e}")
            return False
    
    def cleanup_expired_credentials(self) -> int:
        """Remove all expired credentials"""
        expired_count = 0
        expired_names = []
        
        for name, credential in self._credentials_cache.items():
            if credential.expires_at and datetime.now() > credential.expires_at:
                expired_names.append(name)
        
        for name in expired_names:
            if self.delete_credential(name):
                expired_count += 1
        
        if expired_count > 0:
            logger.info(f"🧹 Cleaned up {expired_count} expired credentials")
        
        return expired_count
    
    # Convenience methods for common credentials
    
    def set_twilio_credentials(self, account_sid: str, auth_token: str, phone_numbers: list = None):
        """Set Twilio credentials"""
        self.set_credential('twilio_account_sid', account_sid, encrypt=False)
        self.set_credential('twilio_auth_token', auth_token, encrypt=True)
        if phone_numbers:
            self.set_credential('twilio_phone_numbers', json.dumps(phone_numbers), encrypt=False)
    
    def get_twilio_credentials(self) -> Optional[Dict[str, Any]]:
        """Get Twilio credentials"""
        account_sid = self.get_credential('twilio_account_sid')
        auth_token = self.get_credential('twilio_auth_token')
        
        if not account_sid or not auth_token:
            return None
        
        phone_numbers = self.get_credential('twilio_phone_numbers')
        phone_numbers = json.loads(phone_numbers) if phone_numbers else []
        
        return {
            'account_sid': account_sid,
            'auth_token': auth_token,
            'phone_numbers': phone_numbers
        }
    
    def set_brightdata_credentials(self, proxy_url: str, username: str, password: str):
        """Set BrightData proxy credentials"""
        self.set_credential('brightdata_proxy_url', proxy_url, encrypt=False)
        self.set_credential('brightdata_username', username, encrypt=False)
        self.set_credential('brightdata_password', password, encrypt=True)
    
    def get_brightdata_credentials(self) -> Optional[Dict[str, str]]:
        """Get BrightData proxy credentials"""
        proxy_url = self.get_credential('brightdata_proxy_url')
        username = self.get_credential('brightdata_username')
        password = self.get_credential('brightdata_password')
        
        if not all([proxy_url, username, password]):
            return None
        
        return {
            'proxy_url': proxy_url,
            'username': username,
            'password': password
        }
    
    def set_captcha_credentials(self, service: str, api_key: str):
        """Set CAPTCHA solving service credentials"""
        self.set_credential(f'captcha_{service}_api_key', api_key, encrypt=True)
    
    def get_captcha_credentials(self) -> Dict[str, str]:
        """Get all CAPTCHA service credentials"""
        services = ['twocaptcha', 'anticaptcha', 'capmonster']
        credentials = {}
        
        for service in services:
            api_key = self.get_credential(f'captcha_{service}_api_key')
            if api_key:
                credentials[service] = api_key
        
        return credentials
    
    def set_database_credentials(self, connection_string: str, redis_password: str = None):
        """Set database credentials"""
        self.set_credential('database_url', connection_string, encrypt=True)
        if redis_password:
            self.set_credential('redis_password', redis_password, encrypt=True)
    
    def get_database_credentials(self) -> Optional[Dict[str, str]]:
        """Get database credentials"""
        db_url = self.get_credential('database_url')
        redis_password = self.get_credential('redis_password')
        
        return {
            'database_url': db_url,
            'redis_password': redis_password
        } if db_url else None
    
    def export_env_file(self, include_encrypted: bool = False) -> str:
        """Export credentials as .env file format"""
        env_lines = [
            "# Exported credentials from secure store",
            f"# Generated at: {datetime.now().isoformat()}",
            ""
        ]
        
        for name, credential in self._credentials_cache.items():
            # Skip encrypted values unless explicitly requested
            if credential.encrypted and not include_encrypted:
                env_lines.append(f"# {name.upper()}=<encrypted_value>")
                continue
            
            # Get the actual value
            value = self.get_credential(name)
            if value:
                env_name = name.upper().replace('-', '_')
                env_lines.append(f"{env_name}={value}")
        
        return "\n".join(env_lines)
    
    def import_from_env(self, env_file_path: str = None, encrypt_by_default: bool = True):
        """Import credentials from .env file"""
        env_file_path = env_file_path or '.env'
        
        if not os.path.exists(env_file_path):
            logger.error(f"❌ Environment file not found: {env_file_path}")
            return
        
        try:
            imported_count = 0
            with open(env_file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip().lower().replace('_', '-')
                        value = value.strip()
                        
                        # Skip empty values or placeholder values
                        if not value or 'your-' in value or 'changeme' in value:
                            continue
                        
                        # Determine if should be encrypted (sensitive keys)
                        sensitive_keys = ['password', 'secret', 'key', 'token']
                        should_encrypt = encrypt_by_default and any(s in key for s in sensitive_keys)
                        
                        self.set_credential(key, value, encrypt=should_encrypt)
                        imported_count += 1
            
            logger.info(f"📥 Imported {imported_count} credentials from {env_file_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to import from {env_file_path}: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on credentials system"""
        health = {
            'healthy': True,
            'encryption_available': self.encryption_key is not None,
            'credentials_count': len(self._credentials_cache),
            'expired_count': 0,
            'errors': []
        }
        
        # Check for expired credentials
        for credential in self._credentials_cache.values():
            if credential.expires_at and datetime.now() > credential.expires_at:
                health['expired_count'] += 1
        
        # Test encryption if available
        if self.encryption_key:
            try:
                test_data = "health_check_test"
                encrypted = self._encrypt_value(test_data)
                decrypted = self._decrypt_value(encrypted)
                if decrypted != test_data:
                    health['healthy'] = False
                    health['errors'].append('Encryption test failed')
            except Exception as e:
                health['healthy'] = False
                health['errors'].append(f'Encryption error: {str(e)}')
        
        return health

# Global credentials manager
_credentials_manager = None

def get_credentials(master_password: Optional[str] = None) -> CredentialsManager:
    """Get global credentials manager instance"""
    global _credentials_manager
    if _credentials_manager is None:
        _credentials_manager = CredentialsManager(master_password)
    return _credentials_manager

def reset_credentials():
    """Reset global credentials manager (useful for testing)"""
    global _credentials_manager
    _credentials_manager = None

if __name__ == "__main__":
    # Test credentials manager
    import getpass
    
    print("🔐 Credentials Manager Test")
    print("=" * 50)
    
    # Ask for master password if not in environment
    master_password = os.getenv('MASTER_PASSWORD')
    if not master_password:
        master_password = getpass.getpass("Enter master password (or press Enter to skip encryption): ").strip()
        if not master_password:
            master_password = None
    
    # Initialize credentials manager
    creds = CredentialsManager(master_password)
    
    # Test setting and getting credentials
    print("\n📝 Testing credential operations...")
    
    # Set test credentials
    creds.set_credential('test_key', 'test_value_123', encrypt=True)
    creds.set_credential('api_key', 'sk-1234567890abcdef', encrypt=True, expires_days=30)
    
    # Get credentials
    test_value = creds.get_credential('test_key')
    api_key = creds.get_credential('api_key')
    
    print(f"✅ Test credential: {'Retrieved successfully' if test_value == 'test_value_123' else 'Failed'}")
    print(f"✅ API key: {'Retrieved successfully' if api_key == 'sk-1234567890abcdef' else 'Failed'}")
    
    # List credentials
    print(f"\n📋 Stored credentials:")
    credentials_info = creds.list_credentials()
    for name, info in credentials_info.items():
        status = "🔐" if info['encrypted'] else "📄"
        expired = "⏰" if info['expired'] else "✅"
        print(f"   {status} {expired} {name} (used {info['usage_count']} times)")
    
    # Health check
    print(f"\n💗 Health Check:")
    health = creds.health_check()
    print(f"   Healthy: {'✅' if health['healthy'] else '❌'}")
    print(f"   Encryption: {'✅' if health['encryption_available'] else '❌'}")
    print(f"   Credentials: {health['credentials_count']}")
    print(f"   Expired: {health['expired_count']}")
    
    if health['errors']:
        print("   Errors:")
        for error in health['errors']:
            print(f"   - {error}")
    
    # Cleanup test credentials
    creds.delete_credential('test_key')
    creds.delete_credential('api_key')
    
    print("\n🧹 Test credentials cleaned up")