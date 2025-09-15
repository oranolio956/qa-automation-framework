#!/usr/bin/env python3
"""
Business Email Service
Legitimate business email service with Gmail API, Outlook API, and SMTP integrations
"""

import os
import time
import logging
import json
import asyncio
import aiohttp
import smtplib
import imaplib

# Import standard library email modules with proper path management
import sys
import importlib

# Temporarily remove current directory from path to avoid conflicts
original_path = sys.path[:]
try:
    # Remove paths that could conflict with standard library
    paths_to_remove = ['.', '', os.getcwd(), os.path.dirname(__file__)]
    for path in paths_to_remove:
        while path in sys.path:
            sys.path.remove(path)
    
    # Force reimport of email modules from standard library
    import email
    import email.mime.text
    import email.mime.multipart
    import email.mime.base
    import email.utils
    import email.parser
    from email import encoders
    
    # Store references to avoid conflicts
    MIMEText = email.mime.text.MIMEText
    MIMEMultipart = email.mime.multipart.MIMEMultipart
    MIMEBase = email.mime.base.MIMEBase
    email_utils = email.utils
    email_parser = email.parser
    
    EMAIL_MODULES_AVAILABLE = True
    
finally:
    # Restore original path
    sys.path = original_path

if 'MIMEText' not in locals():
    print("Warning: Email modules not available, using fallbacks")
    EMAIL_MODULES_AVAILABLE = False
    
    # Minimal fallback classes
    class MIMEText:
        def __init__(self, text, subtype='plain'):
            self.text = text
            self.subtype = subtype
    
    class MIMEMultipart:
        def __init__(self, subtype='mixed'):
            self.subtype = subtype
            self.parts = []
    
    class MIMEBase:
        def __init__(self, maintype, subtype):
            self.maintype = maintype
            self.subtype = subtype
    
    class encoders:
        @staticmethod
        def encode_base64(msg):
            pass
    
    class email_utils:
        @staticmethod
        def formataddr(pair):
            return f"{pair[0]} <{pair[1]}>"
    
    class email_parser:
        @staticmethod
        def Parser():
            return None
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import base64
import uuid
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from microsoft.graph import GraphServiceClient
from microsoft.graph.generated.models.message import Message
from microsoft.graph.generated.models.email_address import EmailAddress
from microsoft.graph.generated.models.recipient import Recipient
from microsoft.graph.generated.models.item_body import ItemBody
from microsoft.graph.generated.models.body_type import BodyType
from azure.identity import ClientSecretCredential

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmailProviderType(Enum):
    GMAIL_API = "gmail_api"
    OUTLOOK_API = "outlook_api"
    CUSTOM_SMTP = "custom_smtp"
    SENDGRID = "sendgrid"
    MAILGUN = "mailgun"
    SES = "ses"

class EmailAccountType(Enum):
    BUSINESS = "business"
    PERSONAL = "personal"
    TRANSACTIONAL = "transactional"
    MARKETING = "marketing"

@dataclass
class BusinessEmailAccount:
    """Business email account data structure"""
    email: str
    provider: EmailProviderType
    account_type: EmailAccountType
    display_name: Optional[str] = None
    created_at: datetime = None
    last_accessed: datetime = None
    is_verified: bool = False
    is_active: bool = True
    credentials: Dict = None
    settings: Dict = None
    usage_stats: Dict = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.credentials is None:
            self.credentials = {}
        if self.settings is None:
            self.settings = {}
        if self.usage_stats is None:
            self.usage_stats = {
                'emails_sent': 0,
                'emails_received': 0,
                'last_activity': None
            }

@dataclass
class BusinessEmailMessage:
    """Business email message data structure"""
    id: str
    from_address: str
    to_addresses: List[str]
    subject: str
    body_text: str
    thread_id: Optional[str] = None
    cc_addresses: List[str] = None
    bcc_addresses: List[str] = None
    body_html: Optional[str] = None
    received_at: datetime = None
    sent_at: datetime = None
    attachments: List[Dict] = None
    labels: List[str] = None
    is_read: bool = False
    is_important: bool = False
    verification_codes: List[str] = None
    
    def __post_init__(self):
        if self.cc_addresses is None:
            self.cc_addresses = []
        if self.bcc_addresses is None:
            self.bcc_addresses = []
        if self.attachments is None:
            self.attachments = []
        if self.labels is None:
            self.labels = []
        if self.verification_codes is None:
            self.verification_codes = self.extract_verification_codes()
    
    def extract_verification_codes(self) -> List[str]:
        """Extract verification codes from email content"""
        import re
        codes = set()
        content = f"{self.subject} {self.body_text}".lower()
        
        # Enhanced verification code patterns for business use
        patterns = [
            r'\b(\d{4,8})\b',                    # 4-8 digit codes
            r'\b([A-Z0-9]{6,12})\b',             # Alphanumeric codes
            r'verification[:\s]*(\w{4,12})',      # "Verification: ABC123"
            r'code[:\s]*(\w{4,12})',             # "Code: 123456"
            r'token[:\s]*(\w{8,32})',            # "Token: abc123def456"
            r'otp[:\s]*(\d{4,8})',               # "OTP: 123456"
            r'pin[:\s]*(\d{4,6})',               # "PIN: 1234"
            r'confirm[:\s]*(\w{4,12})',          # "Confirm: ABC123"
            r'activate[:\s]*(\w{4,12})',         # "Activate: DEF456"
            r'security\s+code[:\s]*(\w{4,12})',  # "Security code: 789012"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            codes.update([match for match in matches if len(match) >= 4])
        
        # Filter out common false positives
        false_positives = {
            '1234', '0000', '9999', '1111', '2222', '3333', '4444',
            '5555', '6666', '7777', '8888', 'test', 'demo', 'sample'
        }
        
        return [code for code in codes if code.lower() not in false_positives]

class BusinessEmailProviderInterface:
    """Base interface for business email providers"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.rate_limits = {}
        
    async def create_email_account(self, email: str, account_type: EmailAccountType) -> BusinessEmailAccount:
        """Create or register business email account"""
        # Base implementation - should be overridden by specific providers
        return BusinessEmailAccount(
            email=email,
            provider=EmailProviderType.CUSTOM_SMTP,
            account_type=account_type,
            is_verified=False,
            settings={
                'auto_reply': False,
                'signature': f"Sent via {account_type.value.title()} Email Service"
            }
        )
        
    async def send_email(self, account: BusinessEmailAccount, message: BusinessEmailMessage) -> bool:
        """Send email via the provider"""
        # Base implementation - should be overridden by specific providers
        logger.warning(f"Send email not implemented for provider: {account.provider}")
        return False
        
    async def get_inbox_messages(self, account: BusinessEmailAccount, limit: int = 50) -> List[BusinessEmailMessage]:
        """Get inbox messages"""
        # Base implementation - should be overridden by specific providers
        logger.warning(f"Get inbox messages not implemented for provider: {account.provider}")
        return []
        
    async def search_messages(self, account: BusinessEmailAccount, query: str, limit: int = 50) -> List[BusinessEmailMessage]:
        """Search messages by query"""
        # Base implementation - get all messages and filter locally
        try:
            all_messages = await self.get_inbox_messages(account, limit * 2)  # Get more messages for better search
            
            query_lower = query.lower()
            matching_messages = []
            
            for message in all_messages:
                if len(matching_messages) >= limit:
                    break
                    
                # Search in subject, body, and from address
                if (query_lower in message.subject.lower() or 
                    query_lower in message.body_text.lower() or
                    query_lower in message.from_address.lower()):
                    matching_messages.append(message)
            
            return matching_messages
            
        except Exception as e:
            logger.error(f"Failed to search messages: {e}")
            return []
        
    async def delete_message(self, account: BusinessEmailAccount, message_id: str) -> bool:
        """Delete a message"""
        # Base implementation - should be overridden by specific providers
        logger.warning(f"Delete message not implemented for provider: {account.provider}")
        return False
        
    async def verify_account(self, account: BusinessEmailAccount) -> bool:
        """Verify email account access"""
        # Base implementation - should be overridden by specific providers
        logger.warning(f"Account verification not implemented for provider: {account.provider}")
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
            
        if rate_limit['count'] >= 100:  # 100 requests per minute
            return False
            
        rate_limit['count'] += 1
        return True

class GmailAPIProvider(BusinessEmailProviderInterface):
    """Gmail API integration for business accounts"""
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.credentials_file = self.config.get('credentials_file', 'gmail_credentials.json')
        self.token_file = self.config.get('token_file', 'gmail_token.json')
        self.scopes = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/gmail.modify'
        ]
        
    async def create_email_account(self, email: str, account_type: EmailAccountType) -> BusinessEmailAccount:
        """Register Gmail account for business use"""
        try:
            # Initiate OAuth2 flow
            if not os.path.exists(self.credentials_file):
                raise Exception(f"Gmail credentials file not found: {self.credentials_file}")
            
            flow = Flow.from_client_secrets_file(
                self.credentials_file,
                scopes=self.scopes,
                redirect_uri='http://localhost:8080/callback'
            )
            
            auth_url, _ = flow.authorization_url(prompt='consent')
            
            account = BusinessEmailAccount(
                email=email,
                provider=EmailProviderType.GMAIL_API,
                account_type=account_type,
                credentials={'auth_url': auth_url, 'flow_state': flow.state},
                settings={
                    'auto_reply': False,
                    'signature': f"Sent via {account_type.value.title()} Email Service",
                    'labels': ['INBOX', 'SENT', 'IMPORTANT']
                }
            )
            
            logger.info(f"Gmail account setup initiated for {email}")
            logger.info(f"Please complete OAuth2 flow at: {auth_url}")
            
            return account
            
        except Exception as e:
            logger.error(f"Failed to create Gmail account: {e}")
            raise
    
    async def complete_oauth(self, account: BusinessEmailAccount, authorization_code: str) -> bool:
        """Complete OAuth2 flow with authorization code"""
        try:
            flow = Flow.from_client_secrets_file(
                self.credentials_file,
                scopes=self.scopes,
                state=account.credentials.get('flow_state'),
                redirect_uri='http://localhost:8080/callback'
            )
            
            flow.fetch_token(code=authorization_code)
            
            # Save credentials
            creds = flow.credentials
            account.credentials.update({
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': creds.scopes
            })
            
            account.is_verified = True
            
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
            
            logger.info(f"Gmail OAuth2 completed for {account.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to complete Gmail OAuth2: {e}")
            return False
    
    def _get_service(self, account: BusinessEmailAccount):
        """Get authenticated Gmail service"""
        if not account.is_verified:
            raise Exception("Account not verified. Complete OAuth2 flow first.")
        
        creds = Credentials.from_authorized_user_info(account.credentials)
        
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # Update stored credentials
                account.credentials.update({
                    'token': creds.token,
                    'refresh_token': creds.refresh_token
                })
            else:
                raise Exception("Invalid credentials. Re-authentication required.")
        
        return build('gmail', 'v1', credentials=creds)
    
    async def send_email(self, account: BusinessEmailAccount, message: BusinessEmailMessage) -> bool:
        """Send email via Gmail API"""
        try:
            if not self._check_rate_limit('send_email'):
                raise Exception("Rate limit exceeded")
            
            service = self._get_service(account)
            
            # Create MIME message
            mime_message = MIMEMultipart('alternative')
            mime_message['From'] = account.email
            mime_message['To'] = ', '.join(message.to_addresses)
            mime_message['Subject'] = message.subject
            
            if message.cc_addresses:
                mime_message['Cc'] = ', '.join(message.cc_addresses)
            
            # Add text part
            text_part = MIMEText(message.body_text, 'plain', 'utf-8')
            mime_message.attach(text_part)
            
            # Add HTML part if available
            if message.body_html:
                html_part = MIMEText(message.body_html, 'html', 'utf-8')
                mime_message.attach(html_part)
            
            # Add attachments
            for attachment in message.attachments:
                with open(attachment['path'], 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {attachment["name"]}'
                    )
                    mime_message.attach(part)
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode()
            
            # Send via Gmail API
            result = service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            message.id = result.get('id')
            message.sent_at = datetime.now()
            
            # Update usage stats
            account.usage_stats['emails_sent'] += 1
            account.usage_stats['last_activity'] = datetime.now()
            
            logger.info(f"Email sent successfully via Gmail: {message.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email via Gmail: {e}")
            return False
    
    async def get_inbox_messages(self, account: BusinessEmailAccount, limit: int = 50) -> List[BusinessEmailMessage]:
        """Get inbox messages from Gmail"""
        try:
            if not self._check_rate_limit('get_messages'):
                raise Exception("Rate limit exceeded")
            
            service = self._get_service(account)
            
            # Get message list
            results = service.users().messages().list(
                userId='me',
                labelIds=['INBOX'],
                maxResults=limit
            ).execute()
            
            messages = []
            
            for msg_info in results.get('messages', []):
                # Get full message
                msg = service.users().messages().get(
                    userId='me',
                    id=msg_info['id'],
                    format='full'
                ).execute()
                
                # Parse message
                business_msg = self._parse_gmail_message(msg)
                if business_msg:
                    messages.append(business_msg)
            
            # Update usage stats
            account.usage_stats['emails_received'] = len(messages)
            account.usage_stats['last_activity'] = datetime.now()
            
            logger.info(f"Retrieved {len(messages)} messages from Gmail inbox")
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get Gmail messages: {e}")
            return []
    
    def _parse_gmail_message(self, msg: Dict) -> Optional[BusinessEmailMessage]:
        """Parse Gmail message to BusinessEmailMessage"""
        try:
            headers = {h['name']: h['value'] for h in msg['payload']['headers']}
            
            # Extract body
            body_text = self._extract_message_body(msg['payload'])
            body_html = self._extract_message_body(msg['payload'], 'text/html')
            
            # Parse addresses
            to_addresses = self._parse_email_addresses(headers.get('To', ''))
            cc_addresses = self._parse_email_addresses(headers.get('Cc', ''))
            
            message = BusinessEmailMessage(
                id=msg['id'],
                thread_id=msg.get('threadId'),
                from_address=headers.get('From', ''),
                to_addresses=to_addresses,
                cc_addresses=cc_addresses,
                subject=headers.get('Subject', ''),
                body_text=body_text or '',
                body_html=body_html,
                received_at=datetime.fromtimestamp(int(msg['internalDate']) / 1000),
                labels=msg.get('labelIds', []),
                is_read='UNREAD' not in msg.get('labelIds', [])
            )
            
            return message
            
        except Exception as e:
            logger.warning(f"Failed to parse Gmail message: {e}")
            return None
    
    def _extract_message_body(self, payload: Dict, mime_type: str = 'text/plain') -> Optional[str]:
        """Extract message body from Gmail payload"""
        try:
            if payload.get('mimeType') == mime_type:
                data = payload.get('body', {}).get('data')
                if data:
                    return base64.urlsafe_b64decode(data).decode('utf-8')
            
            for part in payload.get('parts', []):
                body = self._extract_message_body(part, mime_type)
                if body:
                    return body
            
            return None
            
        except Exception:
            return None
    
    def _parse_email_addresses(self, address_string: str) -> List[str]:
        """Parse email addresses from header string"""
        if not address_string:
            return []
        
        import re
        email_pattern = r'[\w\.-]+@[\w\.-]+\.[\w]+'
        return re.findall(email_pattern, address_string)
    
    async def verify_account(self, account: BusinessEmailAccount) -> bool:
        """Verify Gmail account access"""
        try:
            service = self._get_service(account)
            profile = service.users().getProfile(userId='me').execute()
            
            if profile.get('emailAddress') == account.email:
                account.is_verified = True
                logger.info(f"Gmail account verified: {account.email}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Gmail account verification failed: {e}")
            return False

class OutlookAPIProvider(BusinessEmailProviderInterface):
    """Microsoft Graph API integration for Outlook/Office365"""
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.tenant_id = self.config.get('tenant_id', os.getenv('AZURE_TENANT_ID'))
        self.client_id = self.config.get('client_id', os.getenv('AZURE_CLIENT_ID'))
        self.client_secret = self.config.get('client_secret', os.getenv('AZURE_CLIENT_SECRET'))
        
        if not all([self.tenant_id, self.client_id, self.client_secret]):
            raise Exception("Azure AD credentials not configured")
        
        self.credential = ClientSecretCredential(
            tenant_id=self.tenant_id,
            client_id=self.client_id,
            client_secret=self.client_secret
        )
    
    async def create_email_account(self, email: str, account_type: EmailAccountType) -> BusinessEmailAccount:
        """Register Outlook account for business use"""
        try:
            account = BusinessEmailAccount(
                email=email,
                provider=EmailProviderType.OUTLOOK_API,
                account_type=account_type,
                credentials={
                    'tenant_id': self.tenant_id,
                    'client_id': self.client_id
                },
                settings={
                    'auto_reply': False,
                    'signature': f"Sent via {account_type.value.title()} Email Service",
                    'folders': ['Inbox', 'Sent Items', 'Drafts']
                }
            )
            
            # Verify account access
            if await self.verify_account(account):
                account.is_verified = True
                logger.info(f"Outlook account registered: {email}")
            
            return account
            
        except Exception as e:
            logger.error(f"Failed to create Outlook account: {e}")
            raise
    
    def _get_client(self, account: BusinessEmailAccount) -> GraphServiceClient:
        """Get authenticated Graph API client"""
        scopes = ['https://graph.microsoft.com/.default']
        return GraphServiceClient(
            credentials=self.credential,
            scopes=scopes
        )
    
    async def send_email(self, account: BusinessEmailAccount, message: BusinessEmailMessage) -> bool:
        """Send email via Microsoft Graph API"""
        try:
            if not self._check_rate_limit('send_email'):
                raise Exception("Rate limit exceeded")
            
            client = self._get_client(account)
            
            # Create Graph message
            graph_message = Message()
            graph_message.subject = message.subject
            
            # Set recipients
            to_recipients = []
            for email_addr in message.to_addresses:
                recipient = Recipient()
                recipient.email_address = EmailAddress()
                recipient.email_address.address = email_addr
                to_recipients.append(recipient)
            graph_message.to_recipients = to_recipients
            
            # Set CC recipients
            if message.cc_addresses:
                cc_recipients = []
                for email_addr in message.cc_addresses:
                    recipient = Recipient()
                    recipient.email_address = EmailAddress()
                    recipient.email_address.address = email_addr
                    cc_recipients.append(recipient)
                graph_message.cc_recipients = cc_recipients
            
            # Set body
            graph_message.body = ItemBody()
            if message.body_html:
                graph_message.body.content_type = BodyType.Html
                graph_message.body.content = message.body_html
            else:
                graph_message.body.content_type = BodyType.Text
                graph_message.body.content = message.body_text
            
            # Send message
            result = await client.users.by_user_id(account.email).send_mail.post({
                'message': graph_message,
                'save_to_sent_items': True
            })
            
            message.sent_at = datetime.now()
            
            # Update usage stats
            account.usage_stats['emails_sent'] += 1
            account.usage_stats['last_activity'] = datetime.now()
            
            logger.info(f"Email sent successfully via Outlook")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email via Outlook: {e}")
            return False
    
    async def get_inbox_messages(self, account: BusinessEmailAccount, limit: int = 50) -> List[BusinessEmailMessage]:
        """Get inbox messages from Outlook"""
        try:
            if not self._check_rate_limit('get_messages'):
                raise Exception("Rate limit exceeded")
            
            client = self._get_client(account)
            
            # Get messages from inbox
            messages_response = await client.users.by_user_id(account.email).messages.get(
                request_configuration={
                    'query_parameters': {
                        '$top': limit,
                        '$orderby': 'receivedDateTime desc',
                        '$select': 'id,subject,bodyPreview,body,from,toRecipients,ccRecipients,receivedDateTime,isRead'
                    }
                }
            )
            
            messages = []
            
            for msg in messages_response.value:
                business_msg = self._parse_outlook_message(msg)
                if business_msg:
                    messages.append(business_msg)
            
            # Update usage stats
            account.usage_stats['emails_received'] = len(messages)
            account.usage_stats['last_activity'] = datetime.now()
            
            logger.info(f"Retrieved {len(messages)} messages from Outlook inbox")
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get Outlook messages: {e}")
            return []
    
    def _parse_outlook_message(self, msg) -> Optional[BusinessEmailMessage]:
        """Parse Outlook message to BusinessEmailMessage"""
        try:
            # Extract recipients
            to_addresses = []
            if msg.to_recipients:
                to_addresses = [recipient.email_address.address for recipient in msg.to_recipients]
            
            cc_addresses = []
            if msg.cc_recipients:
                cc_addresses = [recipient.email_address.address for recipient in msg.cc_recipients]
            
            # Extract body
            body_text = msg.body_preview or ''
            body_html = None
            if msg.body and msg.body.content_type == BodyType.Html:
                body_html = msg.body.content
            elif msg.body:
                body_text = msg.body.content
            
            message = BusinessEmailMessage(
                id=msg.id,
                from_address=msg.from_field.email_address.address if msg.from_field else '',
                to_addresses=to_addresses,
                cc_addresses=cc_addresses,
                subject=msg.subject or '',
                body_text=body_text,
                body_html=body_html,
                received_at=msg.received_date_time,
                is_read=msg.is_read or False
            )
            
            return message
            
        except Exception as e:
            logger.warning(f"Failed to parse Outlook message: {e}")
            return None
    
    async def verify_account(self, account: BusinessEmailAccount) -> bool:
        """Verify Outlook account access"""
        try:
            client = self._get_client(account)
            user_info = await client.users.by_user_id(account.email).get()
            
            if user_info and user_info.mail == account.email:
                account.is_verified = True
                logger.info(f"Outlook account verified: {account.email}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Outlook account verification failed: {e}")
            return False

class CustomSMTPProvider(BusinessEmailProviderInterface):
    """Custom SMTP/IMAP provider for business domains"""
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.smtp_config = self.config.get('smtp', {})
        self.imap_config = self.config.get('imap', {})
    
    async def create_email_account(self, email: str, account_type: EmailAccountType) -> BusinessEmailAccount:
        """Register custom SMTP/IMAP account"""
        try:
            domain = email.split('@')[1]
            
            # Auto-detect common providers if not configured
            smtp_config = self.smtp_config.copy()
            imap_config = self.imap_config.copy()
            
            if not smtp_config:
                smtp_config = self._detect_smtp_config(domain)
            
            if not imap_config:
                imap_config = self._detect_imap_config(domain)
            
            account = BusinessEmailAccount(
                email=email,
                provider=EmailProviderType.CUSTOM_SMTP,
                account_type=account_type,
                credentials={
                    'smtp': smtp_config,
                    'imap': imap_config
                },
                settings={
                    'auto_reply': False,
                    'signature': f"Sent via Custom Email Service",
                    'encryption': 'tls'
                }
            )
            
            logger.info(f"Custom SMTP account created: {email}")
            return account
            
        except Exception as e:
            logger.error(f"Failed to create custom SMTP account: {e}")
            raise
    
    def _detect_smtp_config(self, domain: str) -> Dict:
        """Auto-detect SMTP configuration for common providers"""
        common_configs = {
            'gmail.com': {'host': 'smtp.gmail.com', 'port': 587, 'tls': True},
            'outlook.com': {'host': 'smtp-mail.outlook.com', 'port': 587, 'tls': True},
            'hotmail.com': {'host': 'smtp-mail.outlook.com', 'port': 587, 'tls': True},
            'yahoo.com': {'host': 'smtp.mail.yahoo.com', 'port': 587, 'tls': True},
            'icloud.com': {'host': 'smtp.mail.me.com', 'port': 587, 'tls': True}
        }
        
        return common_configs.get(domain, {
            'host': f'smtp.{domain}',
            'port': 587,
            'tls': True
        })
    
    def _detect_imap_config(self, domain: str) -> Dict:
        """Auto-detect IMAP configuration for common providers"""
        common_configs = {
            'gmail.com': {'host': 'imap.gmail.com', 'port': 993, 'ssl': True},
            'outlook.com': {'host': 'outlook.office365.com', 'port': 993, 'ssl': True},
            'hotmail.com': {'host': 'outlook.office365.com', 'port': 993, 'ssl': True},
            'yahoo.com': {'host': 'imap.mail.yahoo.com', 'port': 993, 'ssl': True},
            'icloud.com': {'host': 'imap.mail.me.com', 'port': 993, 'ssl': True}
        }
        
        return common_configs.get(domain, {
            'host': f'imap.{domain}',
            'port': 993,
            'ssl': True
        })
    
    async def send_email(self, account: BusinessEmailAccount, message: BusinessEmailMessage) -> bool:
        """Send email via SMTP"""
        try:
            if not self._check_rate_limit('send_email'):
                raise Exception("Rate limit exceeded")
            
            smtp_config = account.credentials['smtp']
            
            # Create SMTP connection
            server = smtplib.SMTP(smtp_config['host'], smtp_config['port'])
            
            if smtp_config.get('tls'):
                server.starttls()
            
            # Login with account credentials
            password = account.credentials.get('password')
            if not password:
                raise Exception("SMTP password not configured")
            
            server.login(account.email, password)
            
            # Create message
            mime_message = MIMEMultipart('alternative')
            mime_message['From'] = account.email
            mime_message['To'] = ', '.join(message.to_addresses)
            mime_message['Subject'] = message.subject
            
            if message.cc_addresses:
                mime_message['Cc'] = ', '.join(message.cc_addresses)
            
            # Add text content
            text_part = MIMEText(message.body_text, 'plain', 'utf-8')
            mime_message.attach(text_part)
            
            # Add HTML content
            if message.body_html:
                html_part = MIMEText(message.body_html, 'html', 'utf-8')
                mime_message.attach(html_part)
            
            # Send message
            all_recipients = message.to_addresses + message.cc_addresses + message.bcc_addresses
            server.send_message(mime_message, to_addrs=all_recipients)
            server.quit()
            
            message.sent_at = datetime.now()
            
            # Update usage stats
            account.usage_stats['emails_sent'] += 1
            account.usage_stats['last_activity'] = datetime.now()
            
            logger.info(f"Email sent successfully via SMTP")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email via SMTP: {e}")
            return False
    
    async def get_inbox_messages(self, account: BusinessEmailAccount, limit: int = 50) -> List[BusinessEmailMessage]:
        """Get inbox messages via IMAP"""
        try:
            if not self._check_rate_limit('get_messages'):
                raise Exception("Rate limit exceeded")
            
            imap_config = account.credentials['imap']
            password = account.credentials.get('password')
            
            if not password:
                raise Exception("IMAP password not configured")
            
            # Create IMAP connection
            if imap_config.get('ssl'):
                mail = imaplib.IMAP4_SSL(imap_config['host'], imap_config['port'])
            else:
                mail = imaplib.IMAP4(imap_config['host'], imap_config['port'])
            
            mail.login(account.email, password)
            mail.select('INBOX')
            
            # Search for messages
            result, message_ids = mail.search(None, 'ALL')
            
            if result != 'OK':
                return []
            
            messages = []
            msg_ids = message_ids[0].split()[-limit:]  # Get latest messages
            
            for msg_id in msg_ids:
                result, msg_data = mail.fetch(msg_id, '(RFC822)')
                
                if result == 'OK':
                    raw_email = msg_data[0][1]
                    email_message = email.message_from_bytes(raw_email)
                    
                    business_msg = self._parse_imap_message(email_message, msg_id.decode())
                    if business_msg:
                        messages.append(business_msg)
            
            mail.logout()
            
            # Update usage stats
            account.usage_stats['emails_received'] = len(messages)
            account.usage_stats['last_activity'] = datetime.now()
            
            logger.info(f"Retrieved {len(messages)} messages via IMAP")
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get IMAP messages: {e}")
            return []
    
    def _parse_imap_message(self, msg, msg_id: str) -> Optional[BusinessEmailMessage]:
        """Parse IMAP message to BusinessEmailMessage"""
        try:
            # Extract headers
            subject = msg.get('Subject', '')
            from_addr = msg.get('From', '')
            to_addrs = self._parse_addresses(msg.get('To', ''))
            cc_addrs = self._parse_addresses(msg.get('Cc', ''))
            
            # Extract body
            body_text = ''
            body_html = None
            
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == 'text/plain':
                        body_text = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    elif content_type == 'text/html':
                        body_html = part.get_payload(decode=True).decode('utf-8', errors='ignore')
            else:
                body_text = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            
            # Parse date
            date_str = msg.get('Date', '')
            received_at = datetime.now()  # Fallback
            try:
                try:
                    import email.utils
                    parsedate_to_datetime = email.utils.parsedate_to_datetime
                except ImportError:
                    from datetime import datetime
                    def parsedate_to_datetime(date_str):
                        return datetime.now()
                received_at = parsedate_to_datetime(date_str)
            except Exception:
                pass
            
            message = BusinessEmailMessage(
                id=msg_id,
                from_address=from_addr,
                to_addresses=to_addrs,
                cc_addresses=cc_addrs,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                received_at=received_at
            )
            
            return message
            
        except Exception as e:
            logger.warning(f"Failed to parse IMAP message: {e}")
            return None
    
    def _parse_addresses(self, addr_string: str) -> List[str]:
        """Parse email addresses from address string"""
        if not addr_string:
            return []
        
        try:
            import email.utils
            getaddresses = email.utils.getaddresses
        except ImportError:
            def getaddresses(addresses):
                return []
        addresses = getaddresses([addr_string])
        return [addr[1] for addr in addresses if addr[1]]
    
    async def verify_account(self, account: BusinessEmailAccount) -> bool:
        """Verify SMTP/IMAP account access"""
        try:
            # Test IMAP connection
            imap_config = account.credentials['imap']
            password = account.credentials.get('password')
            
            if not password:
                return False
            
            if imap_config.get('ssl'):
                mail = imaplib.IMAP4_SSL(imap_config['host'], imap_config['port'])
            else:
                mail = imaplib.IMAP4(imap_config['host'], imap_config['port'])
            
            mail.login(account.email, password)
            mail.logout()
            
            account.is_verified = True
            logger.info(f"SMTP/IMAP account verified: {account.email}")
            return True
            
        except Exception as e:
            logger.error(f"SMTP/IMAP account verification failed: {e}")
            return False

# Global business email service manager
class BusinessEmailManager:
    """Main business email service manager"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.providers = {}
        self.accounts = {}
        self.templates = {}
        
        # Initialize providers
        self._init_providers()
    
    def _init_providers(self):
        """Initialize email providers"""
        try:
            # Gmail API
            gmail_config = self.config.get('gmail', {})
            if gmail_config.get('enabled', True):
                self.providers[EmailProviderType.GMAIL_API] = GmailAPIProvider(gmail_config)
            
            # Outlook API
            outlook_config = self.config.get('outlook', {})
            if outlook_config.get('enabled', True):
                self.providers[EmailProviderType.OUTLOOK_API] = OutlookAPIProvider(outlook_config)
            
            # Custom SMTP
            smtp_config = self.config.get('custom_smtp', {})
            if smtp_config.get('enabled', True):
                self.providers[EmailProviderType.CUSTOM_SMTP] = CustomSMTPProvider(smtp_config)
            
            logger.info(f"Initialized {len(self.providers)} business email providers")
            
        except Exception as e:
            logger.error(f"Failed to initialize providers: {e}")
    
    async def create_business_email_account(self, email: str, provider: EmailProviderType, 
                                          account_type: EmailAccountType, **kwargs) -> BusinessEmailAccount:
        """Create business email account"""
        try:
            if provider not in self.providers:
                raise Exception(f"Provider {provider.value} not available")
            
            provider_instance = self.providers[provider]
            account = await provider_instance.create_email_account(email, account_type)
            
            # Store account
            self.accounts[email] = account
            
            logger.info(f"Created business email account: {email} ({provider.value})")
            return account
            
        except Exception as e:
            logger.error(f"Failed to create business email account: {e}")
            raise
    
    async def send_business_email(self, from_email: str, to_emails: List[str], 
                                subject: str, body_text: str, body_html: str = None, 
                                cc_emails: List[str] = None, attachments: List[Dict] = None) -> bool:
        """Send business email"""
        try:
            if from_email not in self.accounts:
                raise Exception(f"Account {from_email} not found")
            
            account = self.accounts[from_email]
            provider = self.providers[account.provider]
            
            message = BusinessEmailMessage(
                id=str(uuid.uuid4()),
                from_address=from_email,
                to_addresses=to_emails,
                cc_addresses=cc_emails or [],
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                attachments=attachments or []
            )
            
            success = await provider.send_email(account, message)
            
            if success:
                logger.info(f"Business email sent from {from_email} to {len(to_emails)} recipients")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send business email: {e}")
            return False
    
    async def get_inbox_messages(self, email: str, limit: int = 50) -> List[BusinessEmailMessage]:
        """Get inbox messages for business account"""
        try:
            if email not in self.accounts:
                raise Exception(f"Account {email} not found")
            
            account = self.accounts[email]
            provider = self.providers[account.provider]
            
            messages = await provider.get_inbox_messages(account, limit)
            
            logger.info(f"Retrieved {len(messages)} messages for {email}")
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get inbox messages: {e}")
            return []
    
    async def monitor_inbox_for_verification_codes(self, email: str, timeout: int = 300) -> Optional[str]:
        """Monitor inbox for verification codes"""
        try:
            start_time = time.time()
            last_message_count = 0
            
            while time.time() - start_time < timeout:
                messages = await self.get_inbox_messages(email, limit=10)
                
                if len(messages) > last_message_count:
                    # Check new messages for verification codes
                    new_messages = messages[:len(messages) - last_message_count]
                    
                    for message in new_messages:
                        if message.verification_codes:
                            logger.info(f"Found verification code in {email}: {message.verification_codes[0]}")
                            return message.verification_codes[0]
                    
                    last_message_count = len(messages)
                
                await asyncio.sleep(10)  # Check every 10 seconds
            
            logger.warning(f"No verification code found in {email} within {timeout} seconds")
            return None
            
        except Exception as e:
            logger.error(f"Failed to monitor inbox for verification codes: {e}")
            return None
    
    def create_email_template(self, template_id: str, subject: str, body_text: str, 
                             body_html: str = None, variables: List[str] = None):
        """Create email template for reuse"""
        self.templates[template_id] = {
            'subject': subject,
            'body_text': body_text,
            'body_html': body_html,
            'variables': variables or [],
            'created_at': datetime.now()
        }
        
        logger.info(f"Created email template: {template_id}")
    
    async def send_template_email(self, template_id: str, from_email: str, to_emails: List[str], 
                                variables: Dict = None, **kwargs) -> bool:
        """Send email using template"""
        try:
            if template_id not in self.templates:
                raise Exception(f"Template {template_id} not found")
            
            template = self.templates[template_id]
            variables = variables or {}
            
            # Replace variables in template
            subject = template['subject']
            body_text = template['body_text']
            body_html = template['body_html']
            
            for var_name, var_value in variables.items():
                placeholder = f"{{{var_name}}}"
                subject = subject.replace(placeholder, str(var_value))
                body_text = body_text.replace(placeholder, str(var_value))
                if body_html:
                    body_html = body_html.replace(placeholder, str(var_value))
            
            return await self.send_business_email(
                from_email=from_email,
                to_emails=to_emails,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                **kwargs
            )
            
        except Exception as e:
            logger.error(f"Failed to send template email: {e}")
            return False
    
    def get_account_statistics(self, email: str) -> Dict:
        """Get account usage statistics"""
        if email in self.accounts:
            account = self.accounts[email]
            return {
                'email': email,
                'provider': account.provider.value,
                'account_type': account.account_type.value,
                'created_at': account.created_at.isoformat(),
                'is_verified': account.is_verified,
                'is_active': account.is_active,
                'usage_stats': account.usage_stats
            }
        return {}
    
    def get_all_accounts(self) -> List[Dict]:
        """Get all registered accounts"""
        accounts = []
        for email, account in self.accounts.items():
            accounts.append({
                'email': email,
                'provider': account.provider.value,
                'account_type': account.account_type.value,
                'is_verified': account.is_verified,
                'is_active': account.is_active,
                'created_at': account.created_at.isoformat()
            })
        return accounts

# Global instance
_business_email_manager = None

def get_business_email_manager(config: Dict = None) -> BusinessEmailManager:
    """Get global business email manager instance"""
    global _business_email_manager
    if _business_email_manager is None:
        _business_email_manager = BusinessEmailManager(config)
    return _business_email_manager

if __name__ == "__main__":
    async def test_business_email_service():
        """Test business email service functionality"""
        print("Testing Business Email Service...")
        
        # Initialize manager
        manager = get_business_email_manager({
            'gmail': {
                'enabled': True,
                'credentials_file': 'gmail_credentials.json'
            },
            'custom_smtp': {
                'enabled': True
            }
        })
        
        # Test account creation (placeholder - requires real credentials)
        try:
            account = await manager.create_business_email_account(
                email="test@yourdomain.com",
                provider=EmailProviderType.CUSTOM_SMTP,
                account_type=EmailAccountType.BUSINESS
            )
            print(f"Created account: {account.email}")
            
            # Test template creation
            manager.create_email_template(
                template_id="welcome",
                subject="Welcome {name}!",
                body_text="Hello {name}, welcome to our service!",
                body_html="<h1>Hello {name}</h1><p>Welcome to our service!</p>",
                variables=["name"]
            )
            
            print("Email template created")
            
            # Get statistics
            stats = manager.get_account_statistics(account.email)
            print(f"Account statistics: {stats}")
            
        except Exception as e:
            print(f"Test failed (expected without real credentials): {e}")
        
        print("Business email service test complete!")
    
    # Run test
    asyncio.run(test_business_email_service())