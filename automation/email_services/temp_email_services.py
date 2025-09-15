#!/usr/bin/env python3
"""
Temporary Email Services Integration
Production-ready temporary email service with multiple providers and failover
"""

import os
import time
import random
import logging
import hashlib
import requests
import json
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
import aiohttp
from urllib.parse import urlparse

# Handle missing email modules with fallbacks
try:
    import email.utils
    EMAIL_UTILS_AVAILABLE = True
except ImportError:
    EMAIL_UTILS_AVAILABLE = False
    logging.warning("email.utils not available, using fallbacks")

try:
    import email.parser
    EMAIL_PARSER_AVAILABLE = True
except ImportError:
    EMAIL_PARSER_AVAILABLE = False
    logging.warning("email.parser not available, using fallbacks")

try:
    from google_auth_oauthlib.flow import Flow
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False
    logging.warning("google_auth_oauthlib not available, using fallbacks")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmailProviderType(Enum):
    TEMPMAIL_ORG = "tempmail_org"
    GUERRILLA_MAIL = "guerrilla_mail"
    RAPIDAPI_TEMPMAIL = "rapidapi_tempmail"
    MAIL_TM = "mail_tm"
    TEMP_MAIL_PLUS = "temp_mail_plus"

@dataclass
class EmailAccount:
    """Temporary email account data structure"""
    email: str
    password: Optional[str] = None
    provider: EmailProviderType = EmailProviderType.TEMPMAIL_ORG
    created_at: datetime = None
    expires_at: datetime = None
    inbox_id: Optional[str] = None
    auth_token: Optional[str] = None
    last_checked: datetime = None
    message_count: int = 0
    is_active: bool = True
    provider_data: Dict = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.expires_at is None:
            # Default 60-minute expiry
            self.expires_at = self.created_at + timedelta(minutes=60)
        if self.provider_data is None:
            self.provider_data = {}

@dataclass
class EmailMessage:
    """Email message data structure"""
    id: str
    from_address: str
    to_address: str
    subject: str
    body: str
    html_body: Optional[str] = None
    received_at: datetime = None
    attachments: List[Dict] = None
    verification_codes: List[str] = None
    
    def __post_init__(self):
        if self.received_at is None:
            self.received_at = datetime.now()
        if self.attachments is None:
            self.attachments = []
        if self.verification_codes is None:
            self.verification_codes = self.extract_verification_codes()
    
    def extract_verification_codes(self) -> List[str]:
        """Extract verification codes from email content"""
        import re
        codes = []
        
        # Common verification code patterns
        patterns = [
            r'\b(\d{4,8})\b',           # 4-8 digit codes
            r'\b([A-Z0-9]{6,8})\b',     # Alphanumeric codes  
            r'code[:\s]*(\d{4,8})',     # "Code: 123456"
            r'verification[:\s]*(\d{4,8})', # "Verification: 123456"
            r'pin[:\s]*(\d{4,6})',      # "PIN: 1234"
            r'otp[:\s]*(\d{4,8})',      # "OTP: 123456"
        ]
        
        content = f"{self.subject} {self.body}".lower()
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            codes.extend(matches)
        
        # Remove duplicates and filter reasonable codes
        unique_codes = list(set(codes))
        filtered_codes = [code for code in unique_codes if 4 <= len(code) <= 8]
        
        return filtered_codes

class EmailProviderInterface:
    """Base interface for email providers"""
    
    def __init__(self, api_key: str = None, config: Dict = None):
        self.api_key = api_key
        self.config = config or {}
        self.session = requests.Session()
        self.rate_limits = {}
        
    async def create_email_account(self) -> EmailAccount:
        """Create new temporary email account"""
        # Base implementation - should be overridden by specific providers
        import uuid
        random_id = str(uuid.uuid4())[:8]
        fake_email = f"temp_{random_id}@example.com"
        
        return EmailAccount(
            email=fake_email,
            provider=EmailProviderType.TEMPMAIL_ORG,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=60),
            is_active=False  # Mark as inactive since this is just a placeholder
        )
        
    async def get_inbox_messages(self, account: EmailAccount) -> List[EmailMessage]:
        """Get messages from inbox"""
        # Base implementation - should be overridden by specific providers
        logger.warning(f"Get inbox messages not implemented for provider: {self.__class__.__name__}")
        return []
        
    async def delete_email_account(self, account: EmailAccount) -> bool:
        """Delete email account"""
        # Base implementation - most temp email providers auto-delete
        try:
            account.is_active = False
            account.expires_at = datetime.now()  # Mark as expired
            logger.info(f"Marked temp email account {account.email} as deleted/expired")
            return True
        except Exception as e:
            logger.error(f"Failed to delete temp email account: {e}")
            return False
        
    def _check_rate_limit(self, endpoint: str) -> bool:
        """Check if rate limit allows request"""
        now = time.time()
        key = f"{self.__class__.__name__}_{endpoint}"
        
        if key not in self.rate_limits:
            self.rate_limits[key] = {'count': 0, 'reset_time': now + 60}
            
        rate_limit = self.rate_limits[key]
        
        if now > rate_limit['reset_time']:
            rate_limit['count'] = 0
            rate_limit['reset_time'] = now + 60
            
        if rate_limit['count'] >= 30:  # 30 requests per minute
            return False
            
        rate_limit['count'] += 1
        return True
        
    async def _make_request(self, method: str, url: str, **kwargs) -> Dict:
        """Make HTTP request with retry logic"""
        max_retries = 3
        backoff = 1
        
        for attempt in range(max_retries):
            try:
                if not self._check_rate_limit(url):
                    await asyncio.sleep(60)  # Wait for rate limit reset
                    
                async with aiohttp.ClientSession() as session:
                    async with session.request(method, url, **kwargs) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 429:  # Rate limited
                            await asyncio.sleep(backoff * 2)
                            backoff *= 2
                            continue
                        else:
                            response.raise_for_status()
                            
            except Exception as e:
                logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(backoff)
                backoff *= 2
                
        raise Exception(f"Failed to make request after {max_retries} attempts")

class TempMailOrgProvider(EmailProviderInterface):
    """Temp-Mail.org API integration"""
    
    BASE_URL = "https://api.temp-mail.org/request"
    
    async def create_email_account(self) -> EmailAccount:
        """Create temp-mail.org email account"""
        try:
            # Generate random email
            url = f"{self.BASE_URL}/mail/id/{self._generate_random_string()}/format/json/"
            
            response = await self._make_request('GET', url)
            
            if response and 'mail' in response:
                email = response['mail']
                
                return EmailAccount(
                    email=email,
                    provider=EmailProviderType.TEMPMAIL_ORG,
                    inbox_id=email,
                    expires_at=datetime.now() + timedelta(minutes=60),
                    provider_data={'api_url': url}
                )
                
        except Exception as e:
            logger.error(f"Failed to create temp-mail.org account: {e}")
            raise
    
    async def get_inbox_messages(self, account: EmailAccount) -> List[EmailMessage]:
        """Get messages from temp-mail.org inbox"""
        try:
            hash_email = hashlib.md5(account.email.encode()).hexdigest()
            url = f"{self.BASE_URL}/mail/id/{hash_email}/format/json/"
            
            response = await self._make_request('GET', url)
            
            messages = []
            if response and isinstance(response, list):
                for msg_data in response:
                    message = EmailMessage(
                        id=msg_data.get('mail_id', ''),
                        from_address=msg_data.get('mail_from', ''),
                        to_address=account.email,
                        subject=msg_data.get('mail_subject', ''),
                        body=msg_data.get('mail_text', ''),
                        html_body=msg_data.get('mail_html', ''),
                        received_at=datetime.fromisoformat(msg_data.get('mail_timestamp', '').replace('Z', '+00:00'))
                    )
                    messages.append(message)
                    
            account.last_checked = datetime.now()
            account.message_count = len(messages)
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get temp-mail.org messages: {e}")
            return []
    
    def _generate_random_string(self, length: int = 10) -> str:
        """Generate random string for email"""
        import string
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

class GuerrillaMailProvider(EmailProviderInterface):
    """Guerrilla Mail API integration"""
    
    BASE_URL = "https://api.guerrillamail.com/ajax.php"
    
    async def create_email_account(self) -> EmailAccount:
        """Create Guerrilla Mail email account"""
        try:
            params = {
                'f': 'get_email_address',
                'ip': '127.0.0.1',
                'agent': 'Mozilla/5.0'
            }
            
            response = await self._make_request('GET', self.BASE_URL, params=params)
            
            if response and 'email_addr' in response:
                return EmailAccount(
                    email=response['email_addr'],
                    provider=EmailProviderType.GUERRILLA_MAIL,
                    inbox_id=response.get('sid_token', ''),
                    auth_token=response.get('sid_token', ''),
                    expires_at=datetime.now() + timedelta(minutes=60),
                    provider_data=response
                )
                
        except Exception as e:
            logger.error(f"Failed to create Guerrilla Mail account: {e}")
            raise
    
    async def get_inbox_messages(self, account: EmailAccount) -> List[EmailMessage]:
        """Get messages from Guerrilla Mail inbox"""
        try:
            params = {
                'f': 'get_email_list',
                'sid_token': account.auth_token,
                'offset': 0
            }
            
            response = await self._make_request('GET', self.BASE_URL, params=params)
            
            messages = []
            if response and 'list' in response:
                for msg_data in response['list']:
                    # Get full message content
                    msg_params = {
                        'f': 'fetch_email',
                        'sid_token': account.auth_token,
                        'email_id': msg_data['mail_id']
                    }
                    
                    msg_response = await self._make_request('GET', self.BASE_URL, params=msg_params)
                    
                    if msg_response:
                        message = EmailMessage(
                            id=str(msg_data['mail_id']),
                            from_address=msg_data.get('mail_from', ''),
                            to_address=account.email,
                            subject=msg_data.get('mail_subject', ''),
                            body=msg_response.get('mail_body', ''),
                            html_body=msg_response.get('mail_body', ''),
                            received_at=datetime.fromtimestamp(int(msg_data.get('mail_timestamp', 0)))
                        )
                        messages.append(message)
                        
            account.last_checked = datetime.now()
            account.message_count = len(messages)
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get Guerrilla Mail messages: {e}")
            return []

class RapidAPITempMailProvider(EmailProviderInterface):
    """RapidAPI Temp Mail integration"""
    
    BASE_URL = "https://temp-mail44.p.rapidapi.com"
    
    def __init__(self, api_key: str, config: Dict = None):
        super().__init__(api_key, config)
        self.headers = {
            'X-RapidAPI-Key': api_key,
            'X-RapidAPI-Host': 'temp-mail44.p.rapidapi.com'
        }
    
    async def create_email_account(self) -> EmailAccount:
        """Create RapidAPI temp mail account"""
        try:
            url = f"{self.BASE_URL}/api/v3/email/new"
            
            response = await self._make_request('GET', url, headers=self.headers)
            
            if response and 'email' in response:
                return EmailAccount(
                    email=response['email'],
                    provider=EmailProviderType.RAPIDAPI_TEMPMAIL,
                    inbox_id=response.get('id', ''),
                    expires_at=datetime.now() + timedelta(minutes=60),
                    provider_data=response
                )
                
        except Exception as e:
            logger.error(f"Failed to create RapidAPI temp mail account: {e}")
            raise
    
    async def get_inbox_messages(self, account: EmailAccount) -> List[EmailMessage]:
        """Get messages from RapidAPI temp mail inbox"""
        try:
            url = f"{self.BASE_URL}/api/v3/email/{account.email}/messages"
            
            response = await self._make_request('GET', url, headers=self.headers)
            
            messages = []
            if response and isinstance(response, list):
                for msg_data in response:
                    message = EmailMessage(
                        id=msg_data.get('id', ''),
                        from_address=msg_data.get('from', ''),
                        to_address=account.email,
                        subject=msg_data.get('subject', ''),
                        body=msg_data.get('body', ''),
                        html_body=msg_data.get('html', ''),
                        received_at=datetime.fromisoformat(msg_data.get('date', '').replace('Z', '+00:00'))
                    )
                    messages.append(message)
                    
            account.last_checked = datetime.now()
            account.message_count = len(messages)
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get RapidAPI temp mail messages: {e}")
            return []

class MailTmProvider(EmailProviderInterface):
    """Mail.tm API integration"""
    
    BASE_URL = "https://api.mail.tm"
    
    async def create_email_account(self) -> EmailAccount:
        """Create Mail.tm email account"""
        try:
            # First get available domains
            domains_response = await self._make_request('GET', f"{self.BASE_URL}/domains")
            
            if not domains_response or not domains_response.get('hydra:member'):
                raise Exception("No domains available")
                
            domain = domains_response['hydra:member'][0]['domain']
            
            # Create account
            username = self._generate_random_string()
            password = self._generate_random_string(16)
            email = f"{username}@{domain}"
            
            account_data = {
                'address': email,
                'password': password
            }
            
            response = await self._make_request('POST', f"{self.BASE_URL}/accounts", 
                                              json=account_data,
                                              headers={'Content-Type': 'application/json'})
            
            if response and 'id' in response:
                # Get auth token
                auth_data = {
                    'address': email,
                    'password': password
                }
                
                token_response = await self._make_request('POST', f"{self.BASE_URL}/token",
                                                        json=auth_data,
                                                        headers={'Content-Type': 'application/json'})
                
                return EmailAccount(
                    email=email,
                    password=password,
                    provider=EmailProviderType.MAIL_TM,
                    inbox_id=response['id'],
                    auth_token=token_response.get('token', ''),
                    expires_at=datetime.now() + timedelta(minutes=60),
                    provider_data={'account_id': response['id']}
                )
                
        except Exception as e:
            logger.error(f"Failed to create Mail.tm account: {e}")
            raise
    
    async def get_inbox_messages(self, account: EmailAccount) -> List[EmailMessage]:
        """Get messages from Mail.tm inbox"""
        try:
            headers = {
                'Authorization': f"Bearer {account.auth_token}",
                'Content-Type': 'application/json'
            }
            
            response = await self._make_request('GET', f"{self.BASE_URL}/messages", headers=headers)
            
            messages = []
            if response and 'hydra:member' in response:
                for msg_data in response['hydra:member']:
                    # Get full message content
                    msg_response = await self._make_request('GET', f"{self.BASE_URL}/messages/{msg_data['id']}", 
                                                          headers=headers)
                    
                    if msg_response:
                        message = EmailMessage(
                            id=msg_data['id'],
                            from_address=msg_data.get('from', {}).get('address', ''),
                            to_address=account.email,
                            subject=msg_data.get('subject', ''),
                            body=msg_response.get('text', ''),
                            html_body=msg_response.get('html', ''),
                            received_at=datetime.fromisoformat(msg_data.get('createdAt', '').replace('Z', '+00:00'))
                        )
                        messages.append(message)
                        
            account.last_checked = datetime.now()
            account.message_count = len(messages)
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get Mail.tm messages: {e}")
            return []
    
    def _generate_random_string(self, length: int = 10) -> str:
        """Generate random string"""
        import string
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

class EmailServiceManager:
    """Main email service manager with provider failover"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.providers = {}
        self.active_accounts = {}
        self.provider_stats = {}
        self._message_cache = {}  # Cache for retrieved messages
        
        # Initialize providers
        self._init_providers()
        
    def _init_providers(self):
        """Initialize email providers"""
        try:
            # Temp-Mail.org (no API key needed)
            self.providers[EmailProviderType.TEMPMAIL_ORG] = TempMailOrgProvider()
            
            # Guerrilla Mail (no API key needed)  
            self.providers[EmailProviderType.GUERRILLA_MAIL] = GuerrillaMailProvider()
            
            # RapidAPI Temp Mail (API key required)
            rapidapi_key = self.config.get('rapidapi_key', os.getenv('RAPIDAPI_KEY'))
            if rapidapi_key:
                self.providers[EmailProviderType.RAPIDAPI_TEMPMAIL] = RapidAPITempMailProvider(rapidapi_key)
            
            # Mail.tm (no API key needed)
            self.providers[EmailProviderType.MAIL_TM] = MailTmProvider()
            
            # Initialize stats
            for provider_type in self.providers:
                self.provider_stats[provider_type] = {
                    'total_requests': 0,
                    'successful_requests': 0,
                    'failed_requests': 0,
                    'last_success': None,
                    'last_failure': None,
                    'avg_response_time': 0
                }
                
            logger.info(f"Initialized {len(self.providers)} email providers")
            
        except Exception as e:
            logger.error(f"Failed to initialize providers: {e}")
    
    async def create_email_account(self, preferred_provider: EmailProviderType = None) -> EmailAccount:
        """Create email account with provider failover"""
        providers_to_try = []
        
        if preferred_provider and preferred_provider in self.providers:
            providers_to_try.append(preferred_provider)
        
        # Add remaining providers in order of reliability
        reliable_order = [
            EmailProviderType.MAIL_TM,
            EmailProviderType.TEMPMAIL_ORG,  
            EmailProviderType.GUERRILLA_MAIL,
            EmailProviderType.RAPIDAPI_TEMPMAIL
        ]
        
        for provider_type in reliable_order:
            if provider_type not in providers_to_try and provider_type in self.providers:
                providers_to_try.append(provider_type)
        
        last_error = None
        
        for provider_type in providers_to_try:
            try:
                provider = self.providers[provider_type]
                start_time = time.time()
                
                account = await provider.create_email_account()
                
                # Update stats
                response_time = time.time() - start_time
                stats = self.provider_stats[provider_type]
                stats['total_requests'] += 1
                stats['successful_requests'] += 1
                stats['last_success'] = datetime.now()
                stats['avg_response_time'] = (stats['avg_response_time'] + response_time) / 2
                
                # Store active account
                self.active_accounts[account.email] = account
                
                logger.info(f"Created email account {account.email} via {provider_type.value}")
                return account
                
            except Exception as e:
                # Update failure stats
                stats = self.provider_stats[provider_type]
                stats['total_requests'] += 1
                stats['failed_requests'] += 1
                stats['last_failure'] = datetime.now()
                
                logger.warning(f"Provider {provider_type.value} failed: {e}")
                last_error = e
                continue
        
        raise Exception(f"All email providers failed. Last error: {last_error}")
    
    async def get_inbox_messages(self, email: str) -> List[EmailMessage]:
        """Get inbox messages for email account"""
        if email not in self.active_accounts:
            raise ValueError(f"Email account {email} not found")
            
        account = self.active_accounts[email]
        
        if datetime.now() > account.expires_at:
            logger.warning(f"Email account {email} has expired")
            account.is_active = False
            return []
        
        try:
            provider = self.providers[account.provider]
            messages = await provider.get_inbox_messages(account)
            
            logger.info(f"Retrieved {len(messages)} messages for {email}")
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get messages for {email}: {e}")
            return []
    
    async def delete_email_account(self, email: str) -> bool:
        """Delete email account and clean up resources"""
        if email not in self.active_accounts:
            logger.warning(f"Email account {email} not found for deletion")
            return False
            
        account = self.active_accounts[email]
        
        try:
            provider = self.providers[account.provider]
            success = True  # Default to success for providers without explicit delete
            
            if hasattr(provider, 'delete_email_account'):
                success = await provider.delete_email_account(account)
                logger.info(f"Provider delete result for {email}: {success}")
            
            # Clean up local resources regardless of provider result
            if email in self.active_accounts:
                del self.active_accounts[email]
                
            # Clear message cache for this account
            if email in self._message_cache:
                del self._message_cache[email]
                
            # Mark account as inactive
            account.is_active = False
            account.expires_at = datetime.now()  # Force expiry
            
            logger.info(f"Successfully cleaned up email account: {email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete email account {email}: {e}")
            # Still try to clean up locally
            try:
                if email in self.active_accounts:
                    del self.active_accounts[email]
                if email in self._message_cache:
                    del self._message_cache[email]
                logger.info(f"Performed local cleanup for {email} despite provider error")
            except:
                pass
            return False
    
    async def get_message_content(self, email: str, message_id: str, include_html: bool = True) -> Optional[EmailMessage]:
        """Get detailed content for a specific message"""
        try:
            if email not in self.active_accounts:
                logger.error(f"Email account {email} not found")
                return None
                
            account = self.active_accounts[email]
            
            # Check cache first
            cache_key = f"{email}:{message_id}"
            if cache_key in self._message_cache:
                cached_msg = self._message_cache[cache_key]
                # Check if cache is still fresh (5 minutes)
                if datetime.now() - cached_msg.get('cached_at', datetime.min) < timedelta(minutes=5):
                    return cached_msg['message']
            
            # Get all messages and find the specific one
            messages = await self.get_inbox_messages(email)
            
            for message in messages:
                if message.id == message_id:
                    # Cache the message
                    self._message_cache[cache_key] = {
                        'message': message,
                        'cached_at': datetime.now()
                    }
                    
                    # Get additional content if needed
                    provider = self.providers[account.provider]
                    if hasattr(provider, 'get_message_details'):
                        try:
                            detailed_message = await provider.get_message_details(account, message_id)
                            if detailed_message:
                                message = detailed_message
                        except Exception as e:
                            logger.warning(f"Failed to get detailed message content: {e}")
                    
                    return message
            
            logger.warning(f"Message {message_id} not found in {email}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get message content: {e}")
            return None
    
    async def delete_message(self, email: str, message_id: str) -> bool:
        """Delete a specific message"""
        try:
            if email not in self.active_accounts:
                return False
                
            account = self.active_accounts[email]
            provider = self.providers[account.provider]
            
            # Try provider-specific delete if available
            if hasattr(provider, 'delete_message'):
                success = await provider.delete_message(account, message_id)
                logger.info(f"Provider delete message result: {success}")
                return success
            else:
                # For providers without delete, just remove from cache
                cache_key = f"{email}:{message_id}"
                if cache_key in self._message_cache:
                    del self._message_cache[cache_key]
                logger.info(f"Removed message {message_id} from cache (provider doesn't support delete)")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete message {message_id} from {email}: {e}")
            return False
    
    async def mark_message_as_read(self, email: str, message_id: str) -> bool:
        """Mark a message as read"""
        try:
            message = await self.get_message_content(email, message_id)
            if message:
                message.is_read = True
                # Update cache
                cache_key = f"{email}:{message_id}"
                if cache_key in self._message_cache:
                    self._message_cache[cache_key]['message'].is_read = True
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to mark message as read: {e}")
            return False
    
    async def search_messages(self, email: str, query: str, limit: int = 20) -> List[EmailMessage]:
        """Search messages by content, subject, or sender"""
        try:
            messages = await self.get_inbox_messages(email)
            
            query_lower = query.lower()
            matching_messages = []
            
            for message in messages:
                if len(matching_messages) >= limit:
                    break
                    
                # Search in subject, body, from address, and verification codes
                search_text = f"{message.subject} {message.body} {message.from_address}".lower()
                
                if query_lower in search_text:
                    matching_messages.append(message)
                elif message.verification_codes and any(query_lower in code.lower() for code in message.verification_codes):
                    matching_messages.append(message)
            
            logger.info(f"Found {len(matching_messages)} messages matching '{query}' in {email}")
            return matching_messages
            
        except Exception as e:
            logger.error(f"Failed to search messages in {email}: {e}")
            return []
    
    async def get_verification_codes_from_recent_messages(self, email: str, minutes_back: int = 10) -> List[str]:
        """Extract verification codes from recent messages"""
        try:
            messages = await self.get_inbox_messages(email, limit=20)
            
            recent_time = datetime.now() - timedelta(minutes=minutes_back)
            codes = []
            
            for message in messages:
                if message.received_at and message.received_at >= recent_time:
                    if message.verification_codes:
                        codes.extend(message.verification_codes)
            
            # Remove duplicates while preserving order
            unique_codes = list(dict.fromkeys(codes))
            
            logger.info(f"Found {len(unique_codes)} verification codes in recent messages from {email}")
            return unique_codes
            
        except Exception as e:
            logger.error(f"Failed to get verification codes from {email}: {e}")
            return []
    
    def get_active_accounts(self) -> List[EmailAccount]:
        """Get all active email accounts"""
        current_time = datetime.now()
        active = []
        
        for email, account in self.active_accounts.items():
            if current_time <= account.expires_at and account.is_active:
                active.append(account)
            else:
                account.is_active = False
                
        return active
    
    def cleanup_expired_accounts(self) -> int:
        """Clean up expired email accounts"""
        current_time = datetime.now()
        expired_emails = []
        
        for email, account in self.active_accounts.items():
            if current_time > account.expires_at:
                expired_emails.append(email)
        
        for email in expired_emails:
            del self.active_accounts[email]
            
        logger.info(f"Cleaned up {len(expired_emails)} expired accounts")
        return len(expired_emails)
    
    def get_provider_statistics(self) -> Dict:
        """Get provider performance statistics"""
        stats_summary = {}
        
        for provider_type, stats in self.provider_stats.items():
            success_rate = 0
            if stats['total_requests'] > 0:
                success_rate = stats['successful_requests'] / stats['total_requests']
                
            stats_summary[provider_type.value] = {
                'total_requests': stats['total_requests'],
                'successful_requests': stats['successful_requests'],
                'failed_requests': stats['failed_requests'],
                'success_rate': success_rate,
                'avg_response_time': stats['avg_response_time'],
                'last_success': stats['last_success'].isoformat() if stats['last_success'] else None,
                'last_failure': stats['last_failure'].isoformat() if stats['last_failure'] else None
            }
        
        total_active = len(self.get_active_accounts())
        total_created = len(self.active_accounts)
        
        return {
            'provider_stats': stats_summary,
            'active_accounts': total_active,
            'total_accounts_created': total_created,
            'cache_size': len(self._message_cache),
            'overall_success_rate': sum(s.get('success_rate', 0) for s in stats_summary.values()) / len(stats_summary) if stats_summary else 0,
            'total_messages_cached': len(self._message_cache)
        }
    
    def clear_message_cache(self, email: str = None) -> int:
        """Clear message cache for specific email or all emails"""
        cleared_count = 0
        
        if email:
            # Clear cache for specific email
            keys_to_remove = [k for k in self._message_cache.keys() if k.startswith(f"{email}:")]
            for key in keys_to_remove:
                del self._message_cache[key]
                cleared_count += 1
            logger.info(f"Cleared {cleared_count} cached messages for {email}")
        else:
            # Clear all cache
            cleared_count = len(self._message_cache)
            self._message_cache.clear()
            logger.info(f"Cleared all {cleared_count} cached messages")
        
        return cleared_count

# Global service manager instance
_email_service_manager = None

def get_email_service_manager(config: Dict = None) -> EmailServiceManager:
    """Get global email service manager instance"""
    global _email_service_manager
    if _email_service_manager is None:
        _email_service_manager = EmailServiceManager(config)
    return _email_service_manager

# Enhanced convenience functions
async def create_temp_email(preferred_provider: EmailProviderType = None) -> EmailAccount:
    """Create temporary email account"""
    manager = get_email_service_manager()
    return await manager.create_email_account(preferred_provider)

async def get_email_messages(email: str) -> List[EmailMessage]:
    """Get email messages"""
    manager = get_email_service_manager()
    return await manager.get_inbox_messages(email)

async def delete_temp_email(email: str) -> bool:
    """Delete temporary email account and clean up resources"""
    manager = get_email_service_manager()
    return await manager.delete_email_account(email)

async def get_message_details(email: str, message_id: str) -> Optional[EmailMessage]:
    """Get detailed message content including full body and attachments"""
    manager = get_email_service_manager()
    return await manager.get_message_content(email, message_id)

async def search_email_messages(email: str, query: str, limit: int = 20) -> List[EmailMessage]:
    """Search email messages by content"""
    manager = get_email_service_manager()
    return await manager.search_messages(email, query, limit)

async def get_recent_verification_codes(email: str, minutes_back: int = 10) -> List[str]:
    """Get verification codes from recent messages"""
    manager = get_email_service_manager()
    return await manager.get_verification_codes_from_recent_messages(email, minutes_back)

async def cleanup_expired_emails() -> int:
    """Clean up expired email accounts"""
    manager = get_email_service_manager()
    return manager.cleanup_expired_accounts()

async def wait_for_verification_email(email: str, timeout_seconds: int = 300) -> Optional[str]:
    """Wait for verification email and extract code"""
    manager = get_email_service_manager()
    start_time = time.time()
    
    while time.time() - start_time < timeout_seconds:
        try:
            messages = await manager.get_inbox_messages(email)
            
            for message in messages:
                if message.verification_codes:
                    logger.info(f"Found verification code in email from {message.from_address}")
                    return message.verification_codes[0]
                    
        except Exception as e:
            logger.warning(f"Error checking email: {e}")
            
        await asyncio.sleep(5)  # Check every 5 seconds
    
    logger.warning(f"No verification email received within {timeout_seconds} seconds")
    return None

if __name__ == "__main__":
    async def test_email_services():
        """Test email services functionality"""
        print("Testing Email Services...")
        
        # Create email account
        try:
            account = await create_temp_email()
            print(f"Created email: {account.email}")
            print(f"Provider: {account.provider.value}")
            print(f"Expires: {account.expires_at}")
            
            # Wait a bit and check for messages
            print("Waiting 30 seconds to check for messages...")
            await asyncio.sleep(30)
            
            messages = await get_email_messages(account.email)
            print(f"Found {len(messages)} messages")
            
            for msg in messages[:3]:  # Show first 3 messages
                print(f"  From: {msg.from_address}")
                print(f"  Subject: {msg.subject}")
                print(f"  Codes: {msg.verification_codes}")
            
            # Get statistics
            manager = get_email_service_manager()
            stats = manager.get_provider_statistics()
            print(f"Provider Statistics: {json.dumps(stats, indent=2)}")
            
        except Exception as e:
            print(f"Test failed: {e}")
    
    # Run test
    asyncio.run(test_email_services())