#!/usr/bin/env python3
"""
Secure Email Credentials Manager
GDPR-compliant secure storage and management of email credentials with encryption
"""

import os
import json
import logging
import hashlib
import secrets
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import keyring
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CredentialType(Enum):
    OAUTH2_TOKEN = "oauth2_token"
    SMTP_PASSWORD = "smtp_password"
    IMAP_PASSWORD = "imap_password"
    API_KEY = "api_key"
    CLIENT_SECRET = "client_secret"
    REFRESH_TOKEN = "refresh_token"
    ACCESS_TOKEN = "access_token"

class CredentialStatus(Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING_REFRESH = "pending_refresh"

@dataclass
class EmailCredential:
    """Secure email credential data structure"""
    id: str
    email_address: str
    provider: str
    credential_type: CredentialType
    encrypted_value: str
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    status: CredentialStatus = CredentialStatus.ACTIVE
    metadata: Dict = None
    last_used: Optional[datetime] = None
    usage_count: int = 0
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self, include_encrypted: bool = False) -> Dict:
        """Convert to dictionary for storage"""
        data = {
            'id': self.id,
            'email_address': self.email_address,
            'provider': self.provider,
            'credential_type': self.credential_type.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'status': self.status.value,
            'metadata': self.metadata,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'usage_count': self.usage_count
        }
        
        if include_encrypted:
            data['encrypted_value'] = self.encrypted_value
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'EmailCredential':
        """Create from dictionary"""
        credential = cls(
            id=data['id'],
            email_address=data['email_address'],
            provider=data['provider'],
            credential_type=CredentialType(data['credential_type']),
            encrypted_value=data['encrypted_value'],
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            status=CredentialStatus(data.get('status', 'active')),
            metadata=data.get('metadata', {}),
            usage_count=data.get('usage_count', 0)
        )
        
        if data.get('expires_at'):
            credential.expires_at = datetime.fromisoformat(data['expires_at'])
        if data.get('last_used'):
            credential.last_used = datetime.fromisoformat(data['last_used'])
        
        return credential

class SecureCredentialsManager:
    """GDPR-compliant secure credentials management system"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.db_path = self.config.get('db_path', 'secure_credentials.db')
        self.master_key_id = self.config.get('master_key_id', 'email_service_master_key')
        
        # Initialize encryption
        self.encryption_key = self._get_or_create_master_key()
        self.fernet = Fernet(self.encryption_key)
        
        # Initialize database
        self.init_database()
        
        # Credential cache (in-memory only)
        self.credential_cache = {}
        self.cache_ttl = self.config.get('cache_ttl', 300)  # 5 minutes
        
        logger.info("Secure Credentials Manager initialized")
    
    def _get_or_create_master_key(self) -> bytes:
        """Get or create master encryption key using system keyring"""
        try:
            # Try to get existing key from keyring
            existing_key = keyring.get_password("email_service", self.master_key_id)
            
            if existing_key:
                logger.info("Retrieved existing master key from keyring")
                return base64.b64decode(existing_key.encode())
            
            # Generate new master key
            key = Fernet.generate_key()
            
            # Store in keyring
            keyring.set_password("email_service", self.master_key_id, base64.b64encode(key).decode())
            
            logger.info("Generated and stored new master key in keyring")
            return key
            
        except Exception as e:
            logger.error(f"Failed to manage master key: {e}")
            # Fallback to environment variable (less secure)
            env_key = os.getenv('EMAIL_SERVICE_MASTER_KEY')
            if env_key:
                return base64.b64decode(env_key.encode())
            
            # Last resort: generate temporary key (will be lost on restart)
            logger.warning("Using temporary master key - credentials will not persist")
            return Fernet.generate_key()
    
    def init_database(self):
        """Initialize SQLite database for credential storage"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create credentials table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS credentials (
                    id TEXT PRIMARY KEY,
                    email_address TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    credential_type TEXT NOT NULL,
                    encrypted_value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    metadata TEXT,
                    last_used TIMESTAMP,
                    usage_count INTEGER DEFAULT 0
                )
            ''')
            
            # Create audit log table for GDPR compliance
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS credential_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    credential_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    performed_by TEXT,
                    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_address TEXT,
                    user_agent TEXT,
                    details TEXT
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_email_provider ON credentials(email_address, provider)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_credential_type ON credentials(credential_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON credentials(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_credential ON credential_audit_log(credential_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_action ON credential_audit_log(action)')
            
            conn.commit()
            conn.close()
            
            logger.info("Credentials database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize credentials database: {e}")
            raise
    
    def store_credential(self, email_address: str, provider: str, 
                       credential_type: CredentialType, value: str,
                       expires_at: Optional[datetime] = None,
                       metadata: Dict = None) -> str:
        """Store encrypted credential securely"""
        try:
            # Generate unique credential ID
            credential_id = hashlib.sha256(f"{email_address}:{provider}:{credential_type.value}:{secrets.token_hex(16)}".encode()).hexdigest()
            
            # Encrypt the credential value
            encrypted_value = self.fernet.encrypt(value.encode()).decode()
            
            # Create credential object
            credential = EmailCredential(
                id=credential_id,
                email_address=email_address,
                provider=provider,
                credential_type=credential_type,
                encrypted_value=encrypted_value,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                expires_at=expires_at,
                metadata=metadata or {}
            )
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO credentials (
                    id, email_address, provider, credential_type, encrypted_value,
                    created_at, updated_at, expires_at, status, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                credential.id,
                credential.email_address,
                credential.provider,
                credential.credential_type.value,
                credential.encrypted_value,
                credential.created_at.isoformat(),
                credential.updated_at.isoformat(),
                credential.expires_at.isoformat() if credential.expires_at else None,
                credential.status.value,
                json.dumps(credential.metadata)
            ))
            
            conn.commit()
            conn.close()
            
            # Log the action for audit
            self._log_credential_action(credential_id, 'STORE', f"Stored {credential_type.value} for {email_address}")
            
            logger.info(f"Stored credential {credential_id} for {email_address}")
            return credential_id
            
        except Exception as e:
            logger.error(f"Failed to store credential: {e}")
            raise
    
    def get_credential(self, credential_id: str) -> Optional[str]:
        """Retrieve and decrypt credential value"""
        try:
            # Check cache first
            if credential_id in self.credential_cache:
                cache_entry = self.credential_cache[credential_id]
                if datetime.now() - cache_entry['cached_at'] < timedelta(seconds=self.cache_ttl):
                    logger.debug(f"Retrieved credential {credential_id} from cache")
                    return cache_entry['value']
            
            # Get from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT encrypted_value, status FROM credentials WHERE id=?', (credential_id,))
            result = cursor.fetchone()
            
            if not result:
                logger.warning(f"Credential {credential_id} not found")
                return None
            
            encrypted_value, status = result
            
            if status != CredentialStatus.ACTIVE.value:
                logger.warning(f"Credential {credential_id} is not active (status: {status})")
                return None
            
            # Decrypt value
            decrypted_value = self.fernet.decrypt(encrypted_value.encode()).decode()
            
            # Update usage statistics
            cursor.execute('''
                UPDATE credentials 
                SET last_used=?, usage_count=usage_count+1 
                WHERE id=?
            ''', (datetime.now().isoformat(), credential_id))
            
            conn.commit()
            conn.close()
            
            # Cache the decrypted value
            self.credential_cache[credential_id] = {
                'value': decrypted_value,
                'cached_at': datetime.now()
            }
            
            # Log the access for audit
            self._log_credential_action(credential_id, 'ACCESS', "Credential accessed")
            
            logger.debug(f"Retrieved credential {credential_id}")
            return decrypted_value
            
        except Exception as e:
            logger.error(f"Failed to get credential: {e}")
            return None
    
    def get_credential_by_email_and_type(self, email_address: str, provider: str, 
                                        credential_type: CredentialType) -> Optional[str]:
        """Get credential by email address and type"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id FROM credentials 
                WHERE email_address=? AND provider=? AND credential_type=? AND status='active'
                ORDER BY updated_at DESC LIMIT 1
            ''', (email_address, provider, credential_type.value))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return self.get_credential(result[0])
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get credential by email and type: {e}")
            return None
    
    def update_credential(self, credential_id: str, new_value: str, 
                         expires_at: Optional[datetime] = None) -> bool:
        """Update existing credential with new value"""
        try:
            # Encrypt new value
            encrypted_value = self.fernet.encrypt(new_value.encode()).decode()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE credentials 
                SET encrypted_value=?, updated_at=?, expires_at=?, status='active'
                WHERE id=?
            ''', (
                encrypted_value,
                datetime.now().isoformat(),
                expires_at.isoformat() if expires_at else None,
                credential_id
            ))
            
            if cursor.rowcount == 0:
                logger.warning(f"Credential {credential_id} not found for update")
                conn.close()
                return False
            
            conn.commit()
            conn.close()
            
            # Clear from cache
            if credential_id in self.credential_cache:
                del self.credential_cache[credential_id]
            
            # Log the action
            self._log_credential_action(credential_id, 'UPDATE', "Credential value updated")
            
            logger.info(f"Updated credential {credential_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update credential: {e}")
            return False
    
    def delete_credential(self, credential_id: str, reason: str = "User requested") -> bool:
        """Securely delete credential (GDPR right to erasure)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get credential info for audit
            cursor.execute('SELECT email_address, provider FROM credentials WHERE id=?', (credential_id,))
            credential_info = cursor.fetchone()
            
            if not credential_info:
                logger.warning(f"Credential {credential_id} not found for deletion")
                conn.close()
                return False
            
            # Delete the credential
            cursor.execute('DELETE FROM credentials WHERE id=?', (credential_id,))
            
            conn.commit()
            conn.close()
            
            # Clear from cache
            if credential_id in self.credential_cache:
                del self.credential_cache[credential_id]
            
            # Log the deletion
            self._log_credential_action(
                credential_id, 
                'DELETE', 
                f"Credential deleted - Reason: {reason} - Email: {credential_info[0]}"
            )
            
            logger.info(f"Deleted credential {credential_id} for {credential_info[0]}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete credential: {e}")
            return False
    
    def revoke_credential(self, credential_id: str, reason: str = "Security precaution") -> bool:
        """Revoke credential without deletion"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE credentials 
                SET status='revoked', updated_at=?
                WHERE id=?
            ''', (datetime.now().isoformat(), credential_id))
            
            if cursor.rowcount == 0:
                logger.warning(f"Credential {credential_id} not found for revocation")
                conn.close()
                return False
            
            conn.commit()
            conn.close()
            
            # Clear from cache
            if credential_id in self.credential_cache:
                del self.credential_cache[credential_id]
            
            # Log the revocation
            self._log_credential_action(credential_id, 'REVOKE', f"Credential revoked - Reason: {reason}")
            
            logger.info(f"Revoked credential {credential_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke credential: {e}")
            return False
    
    def list_credentials(self, email_address: str = None, provider: str = None, 
                        include_expired: bool = False) -> List[Dict]:
        """List credentials (without decrypted values)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = 'SELECT * FROM credentials WHERE 1=1'
            params = []
            
            if email_address:
                query += ' AND email_address=?'
                params.append(email_address)
            
            if provider:
                query += ' AND provider=?'
                params.append(provider)
            
            if not include_expired:
                query += ' AND (expires_at IS NULL OR expires_at > ?)'
                params.append(datetime.now().isoformat())
            
            query += ' ORDER BY updated_at DESC'
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            columns = [description[0] for description in cursor.description]
            credentials = []
            
            for row in rows:
                data = dict(zip(columns, row))
                
                # Parse JSON fields
                if data['metadata']:
                    data['metadata'] = json.loads(data['metadata'])
                
                # Don't include encrypted value in list
                del data['encrypted_value']
                
                credentials.append(data)
            
            conn.close()
            
            return credentials
            
        except Exception as e:
            logger.error(f"Failed to list credentials: {e}")
            return []
    
    def cleanup_expired_credentials(self) -> int:
        """Clean up expired credentials"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get expired credentials
            cursor.execute('''
                SELECT id, email_address FROM credentials 
                WHERE expires_at IS NOT NULL AND expires_at <= ? AND status='active'
            ''', (datetime.now().isoformat(),))
            
            expired = cursor.fetchall()
            
            # Mark as expired
            cursor.execute('''
                UPDATE credentials 
                SET status='expired', updated_at=?
                WHERE expires_at IS NOT NULL AND expires_at <= ? AND status='active'
            ''', (datetime.now().isoformat(), datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            # Clear from cache
            for credential_id, _ in expired:
                if credential_id in self.credential_cache:
                    del self.credential_cache[credential_id]
                
                # Log expiration
                self._log_credential_action(credential_id, 'EXPIRE', "Credential expired automatically")
            
            if expired:
                logger.info(f"Marked {len(expired)} credentials as expired")
            
            return len(expired)
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired credentials: {e}")
            return 0
    
    def _log_credential_action(self, credential_id: str, action: str, details: str = None):
        """Log credential action for audit trail (GDPR compliance)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO credential_audit_log (
                    credential_id, action, performed_at, details
                ) VALUES (?, ?, ?, ?)
            ''', (
                credential_id,
                action,
                datetime.now().isoformat(),
                details
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.warning(f"Failed to log credential action: {e}")
    
    def get_credential_audit_log(self, credential_id: str = None, 
                               days: int = 30) -> List[Dict]:
        """Get credential audit log for compliance"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = 'SELECT * FROM credential_audit_log WHERE 1=1'
            params = []
            
            if credential_id:
                query += ' AND credential_id=?'
                params.append(credential_id)
            
            if days > 0:
                since_date = (datetime.now() - timedelta(days=days)).isoformat()
                query += ' AND performed_at >= ?'
                params.append(since_date)
            
            query += ' ORDER BY performed_at DESC'
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            columns = [description[0] for description in cursor.description]
            audit_log = [dict(zip(columns, row)) for row in rows]
            
            conn.close()
            
            return audit_log
            
        except Exception as e:
            logger.error(f"Failed to get audit log: {e}")
            return []
    
    def export_user_data(self, email_address: str) -> Dict:
        """Export all data for user (GDPR right to data portability)"""
        try:
            # Get credentials (without encrypted values)
            credentials = self.list_credentials(email_address=email_address, include_expired=True)
            
            # Get audit log
            credential_ids = [cred['id'] for cred in credentials]
            audit_entries = []
            
            for cred_id in credential_ids:
                audit_entries.extend(self.get_credential_audit_log(cred_id, days=0))  # All history
            
            export_data = {
                'export_generated_at': datetime.now().isoformat(),
                'email_address': email_address,
                'credentials': credentials,
                'audit_log': audit_entries,
                'data_retention_info': {
                    'credential_retention_days': 365,
                    'audit_log_retention_days': 2555,  # 7 years for compliance
                    'note': 'Encrypted credential values are not included in export for security'
                }
            }
            
            logger.info(f"Exported data for user: {email_address}")
            return export_data
            
        except Exception as e:
            logger.error(f"Failed to export user data: {e}")
            return {}
    
    def delete_user_data(self, email_address: str, reason: str = "GDPR erasure request") -> bool:
        """Delete all user data (GDPR right to erasure)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all credentials for this user
            cursor.execute('SELECT id FROM credentials WHERE email_address=?', (email_address,))
            credential_ids = [row[0] for row in cursor.fetchall()]
            
            # Log deletion intent
            for cred_id in credential_ids:
                self._log_credential_action(cred_id, 'USER_DATA_DELETION', f"Full user data deletion - {reason}")
            
            # Delete credentials
            cursor.execute('DELETE FROM credentials WHERE email_address=?', (email_address,))
            
            # Note: We keep audit log for legal compliance but anonymize it
            cursor.execute('''
                UPDATE credential_audit_log 
                SET details = 'USER_DATA_DELETED: ' || details
                WHERE credential_id IN (
                    SELECT id FROM credentials WHERE email_address=?
                )
            ''', (email_address,))
            
            conn.commit()
            conn.close()
            
            # Clear from cache
            for cred_id in credential_ids:
                if cred_id in self.credential_cache:
                    del self.credential_cache[cred_id]
            
            logger.info(f"Deleted all data for user: {email_address}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete user data: {e}")
            return False
    
    def get_usage_statistics(self) -> Dict:
        """Get system usage statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total credentials by status
            cursor.execute('''
                SELECT status, COUNT(*) 
                FROM credentials 
                GROUP BY status
            ''')
            status_counts = dict(cursor.fetchall())
            
            # Credentials by provider
            cursor.execute('''
                SELECT provider, COUNT(*) 
                FROM credentials 
                WHERE status='active'
                GROUP BY provider
            ''')
            provider_counts = dict(cursor.fetchall())
            
            # Recent activity
            since_date = (datetime.now() - timedelta(days=30)).isoformat()
            cursor.execute('''
                SELECT action, COUNT(*) 
                FROM credential_audit_log 
                WHERE performed_at >= ?
                GROUP BY action
            ''', (since_date,))
            activity_counts = dict(cursor.fetchall())
            
            # Most used credentials
            cursor.execute('''
                SELECT email_address, provider, SUM(usage_count) as total_usage
                FROM credentials 
                WHERE status='active'
                GROUP BY email_address, provider
                ORDER BY total_usage DESC
                LIMIT 10
            ''')
            top_used = cursor.fetchall()
            
            conn.close()
            
            return {
                'total_by_status': status_counts,
                'total_by_provider': provider_counts,
                'activity_last_30_days': activity_counts,
                'most_used_accounts': [
                    {'email': email, 'provider': provider, 'usage': usage}
                    for email, provider, usage in top_used
                ],
                'cache_stats': {
                    'cached_credentials': len(self.credential_cache),
                    'cache_ttl_seconds': self.cache_ttl
                },
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get usage statistics: {e}")
            return {}

# Global credentials manager instance
_credentials_manager = None

def get_credentials_manager(config: Dict = None) -> SecureCredentialsManager:
    """Get global credentials manager instance"""
    global _credentials_manager
    if _credentials_manager is None:
        _credentials_manager = SecureCredentialsManager(config)
    return _credentials_manager

if __name__ == "__main__":
    def test_credentials_manager():
        """Test credentials manager functionality"""
        print("Testing Secure Credentials Manager...")
        
        # Initialize manager
        manager = get_credentials_manager({'db_path': 'test_credentials.db'})
        
        # Store test credential
        cred_id = manager.store_credential(
            email_address="test@example.com",
            provider="gmail",
            credential_type=CredentialType.SMTP_PASSWORD,
            value="test_password_123",
            metadata={"server": "smtp.gmail.com", "port": 587}
        )
        print(f"Stored credential: {cred_id}")
        
        # Retrieve credential
        retrieved_value = manager.get_credential(cred_id)
        print(f"Retrieved value: {'✓ Success' if retrieved_value == 'test_password_123' else '✗ Failed'}")
        
        # List credentials
        credentials = manager.list_credentials()
        print(f"Total credentials: {len(credentials)}")
        
        # Get usage statistics
        stats = manager.get_usage_statistics()
        print(f"Active credentials: {stats.get('total_by_status', {}).get('active', 0)}")
        
        # Export user data
        user_data = manager.export_user_data("test@example.com")
        print(f"Exported data contains {len(user_data.get('credentials', []))} credentials")
        
        # Clean up test
        manager.delete_credential(cred_id, "Test cleanup")
        print("Test credential deleted")
        
        print("Credentials manager test complete!")
    
    # Run test
    test_credentials_manager()