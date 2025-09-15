#!/usr/bin/env python3
"""
Email Integration Module
Integrates email automation with existing Snapchat/Tinder automation systems
"""

import os
import sys
import asyncio
import logging
import json
import httpx
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# Import email services
from .temp_email_services import EmailAccount, EmailProviderType, get_email_service_manager
from .email_pool_manager import get_email_pool_manager

from typing import TYPE_CHECKING

# Import only lightweight runtime deps to avoid circular imports
try:
    from utils.sms_verifier import get_sms_verifier
except ImportError as e:
    logging.warning(f"Could not import sms_verifier: {e}")

# Heavy imports only for typing to prevent runtime circular imports
if TYPE_CHECKING:
    from automation.snapchat.stealth_creator import SnapchatStealthCreator
    from automation.tinder.account_creator import TinderAppAutomator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class EmailVerificationResult:
    """Email verification result"""
    success: bool
    email: str
    verification_code: Optional[str] = None
    message_count: int = 0
    time_taken: float = 0.0
    error_message: Optional[str] = None

class EmailAutomationIntegrator:
    """Integrates email automation with existing systems"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Email service URLs (if running as microservices)
        self.email_service_url = self.config.get('email_service_url', 'http://localhost:8003')
        self.inbox_service_url = self.config.get('inbox_service_url', 'http://localhost:8004')
        
        # Initialize services
        self.email_manager = get_email_service_manager()
        self.pool_manager = get_email_pool_manager()
        
        # HTTP client for service communication
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        logger.info("Email Automation Integrator initialized")
    
    async def get_email_for_registration(self, service: str, purpose: str = "registration") -> Optional[EmailAccount]:
        """Get email account for service registration"""
        try:
            # Try to get from pool first (fastest)
            account = await self.pool_manager.get_email_account(service, purpose)
            
            if account:
                logger.info(f"Got email from pool: {account.email} for {service}")
                return account
            
            # Fallback to direct creation
            account = await self.email_manager.create_email_account()
            
            if account:
                logger.info(f"Created new email: {account.email} for {service}")
                return account
            
            logger.error(f"Failed to get email account for {service}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting email for {service}: {e}")
            return None
    
    async def wait_for_verification_email(self, email: str, service: str, 
                                        timeout: int = 300, 
                                        service_specific_patterns: List[str] = None) -> EmailVerificationResult:
        """Wait for verification email with service-specific patterns"""
        start_time = datetime.now()
        
        try:
            # Service-specific configuration
            service_config = self._get_service_config(service)
            actual_timeout = min(timeout, service_config.get('max_timeout', 300))
            poll_interval = service_config.get('poll_interval', 10)
            
            logger.info(f"Waiting for verification email for {email} (service: {service}, timeout: {actual_timeout}s)")
            
            last_message_count = 0
            
            while (datetime.now() - start_time).total_seconds() < actual_timeout:
                try:
                    # Get inbox messages
                    messages = await self.email_manager.get_inbox_messages(email)
                    
                    if len(messages) > last_message_count:
                        # New messages found
                        new_messages = messages[last_message_count:]
                        
                        for message in new_messages:
                            # Extract verification codes
                            codes = self._extract_verification_codes(
                                message, service, service_specific_patterns
                            )
                            
                            if codes:
                                time_taken = (datetime.now() - start_time).total_seconds()
                                
                                logger.info(f"Verification code found for {email}: {codes[0]}")
                                
                                return EmailVerificationResult(
                                    success=True,
                                    email=email,
                                    verification_code=codes[0],
                                    message_count=len(messages),
                                    time_taken=time_taken
                                )
                        
                        last_message_count = len(messages)
                    
                    # Wait before next poll
                    await asyncio.sleep(poll_interval)
                    
                except Exception as poll_error:
                    logger.warning(f"Error polling inbox: {poll_error}")
                    await asyncio.sleep(5)  # Brief pause on error
            
            # Timeout reached
            time_taken = (datetime.now() - start_time).total_seconds()
            
            return EmailVerificationResult(
                success=False,
                email=email,
                message_count=last_message_count,
                time_taken=time_taken,
                error_message=f"Timeout after {actual_timeout} seconds"
            )
            
        except Exception as e:
            time_taken = (datetime.now() - start_time).total_seconds()
            
            logger.error(f"Error waiting for verification email: {e}")
            
            return EmailVerificationResult(
                success=False,
                email=email,
                time_taken=time_taken,
                error_message=str(e)
            )
    
    def _extract_verification_codes(self, message, service: str, 
                                  custom_patterns: List[str] = None) -> List[str]:
        """Extract verification codes with service-specific logic"""
        import re
        
        codes = set()
        content = f"{message.subject} {message.body}".lower()
        
        # Service-specific patterns
        service_patterns = {
            'snapchat': [
                r'snapchat.*?(\d{6})',
                r'snap.*?verification.*?(\d{6})',
                r'your\s+snapchat\s+code\s+is[:\s]*(\d{6})',
                r'confirm\s+your\s+snapchat\s+account[:\s]*(\d{6})'
            ],
            'tinder': [
                r'tinder.*?(\d{4,6})',
                r'your\s+tinder\s+code\s+is[:\s]*(\d{4,6})',
                r'tinder\s+verification[:\s]*(\d{4,6})',
                r'confirm\s+your\s+phone\s+number[:\s]*(\d{4,6})'
            ],
            'instagram': [
                r'instagram.*?(\d{6})',
                r'your\s+instagram\s+code\s+is[:\s]*(\d{6})',
                r'confirmation\s+code[:\s]*(\d{6})'
            ],
            'facebook': [
                r'facebook.*?(\d{6,8})',
                r'your\s+facebook\s+code\s+is[:\s]*(\d{6,8})',
                r'fb.*?code[:\s]*(\d{6,8})'
            ]
        }
        
        # Use custom patterns first
        if custom_patterns:
            for pattern in custom_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                codes.update(matches)
        
        # Use service-specific patterns
        if service.lower() in service_patterns:
            patterns = service_patterns[service.lower()]
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                codes.update(matches)
        
        # General patterns as fallback
        general_patterns = [
            r'\b(\d{4,8})\b',                    # 4-8 digit codes
            r'code[:\s]*(\d{4,8})',              # "Code: 123456"
            r'verification[:\s]*(\d{4,8})',       # "Verification: 123456"
            r'pin[:\s]*(\d{4,6})',               # "PIN: 1234"
            r'otp[:\s]*(\d{4,8})',               # "OTP: 123456"
        ]
        
        for pattern in general_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            codes.update(matches)
        
        # Filter and validate codes
        valid_codes = []
        for code in codes:
            if self._is_valid_verification_code(code):
                valid_codes.append(code)
        
        return list(set(valid_codes))
    
    def _is_valid_verification_code(self, code: str) -> bool:
        """Validate verification code"""
        if not code or len(code) < 4 or len(code) > 8:
            return False
        
        # Must be numeric or alphanumeric
        if not (code.isdigit() or code.isalnum()):
            return False
        
        # Avoid common false positives
        false_positives = [
            '1234', '0000', '9999', '1111', '2222', '3333', 
            '4444', '5555', '6666', '7777', '8888', '1000', '2000'
        ]
        
        return code not in false_positives
    
    def _get_service_config(self, service: str) -> Dict:
        """Get service-specific configuration"""
        configs = {
            'snapchat': {
                'max_timeout': 180,  # Snapchat usually sends codes quickly
                'poll_interval': 8,
                'expected_code_length': 6,
            },
            'tinder': {
                'max_timeout': 120,  # Tinder is very fast
                'poll_interval': 5,
                'expected_code_length': 6,
            },
            'instagram': {
                'max_timeout': 240,
                'poll_interval': 10,
                'expected_code_length': 6,
            },
            'facebook': {
                'max_timeout': 300,
                'poll_interval': 15,
                'expected_code_length': 8,
            },
            'default': {
                'max_timeout': 300,
                'poll_interval': 10,
                'expected_code_length': 6,
            }
        }
        
        return configs.get(service.lower(), configs['default'])
    
    async def complete_email_registration_flow(self, service: str, 
                                             registration_data: Dict = None) -> Tuple[EmailAccount, EmailVerificationResult]:
        """Complete full email registration flow"""
        try:
            # Get email account
            email_account = await self.get_email_for_registration(service, "registration")
            
            if not email_account:
                return None, EmailVerificationResult(
                    success=False,
                    email="",
                    error_message="Failed to get email account"
                )
            
            # Submit email for registration (would integrate with automation)
            # This is where the automation system would use the email
            logger.info(f"Email {email_account.email} ready for {service} registration")
            
            # Wait for verification email
            verification_result = await self.wait_for_verification_email(
                email_account.email, 
                service,
                timeout=self._get_service_config(service).get('max_timeout', 300)
            )
            
            return email_account, verification_result
            
        except Exception as e:
            logger.error(f"Error in email registration flow: {e}")
            return None, EmailVerificationResult(
                success=False,
                email="",
                error_message=str(e)
            )
    
    async def return_email_to_pool(self, email: str, success: bool = True, 
                                 spam_reported: bool = False, bounced: bool = False):
        """Return email to pool after use"""
        try:
            returned = await self.pool_manager.return_email_account(
                email, success, spam_reported, bounced
            )
            
            if returned:
                logger.info(f"Returned email {email} to pool (success: {success})")
            else:
                logger.warning(f"Failed to return email {email} to pool")
            
            return returned
            
        except Exception as e:
            logger.error(f"Error returning email to pool: {e}")
            return False
    
    async def get_pool_statistics(self) -> Dict:
        """Get email pool statistics"""
        try:
            return await self.pool_manager.get_pool_statistics()
        except Exception as e:
            logger.error(f"Error getting pool statistics: {e}")
            return {}
    
    async def cleanup_expired_emails(self) -> int:
        """Clean up expired emails from pool"""
        try:
            return await self.pool_manager.cleanup_expired_accounts()
        except Exception as e:
            logger.error(f"Error cleaning up expired emails: {e}")
            return 0
    
    async def start_inbox_monitoring(self, email: str, service: str, 
                                   webhook_url: str = None) -> Optional[str]:
        """Start real-time inbox monitoring"""
        try:
            # Use inbox monitoring service if available
            monitor_request = {
                'email': email,
                'service': service,
                'webhook_url': webhook_url,
                'poll_interval': self._get_service_config(service).get('poll_interval', 10)
            }
            
            async with self.http_client as client:
                response = await client.post(
                    f"{self.inbox_service_url}/monitor/start",
                    json=monitor_request
                )
                
                if response.status_code == 200:
                    result = response.json()
                    monitor_id = result.get('monitor_id')
                    logger.info(f"Started inbox monitoring for {email}: {monitor_id}")
                    return monitor_id
                else:
                    logger.error(f"Failed to start inbox monitoring: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error starting inbox monitoring: {e}")
            return None
    
    async def stop_inbox_monitoring(self, monitor_id: str) -> bool:
        """Stop inbox monitoring"""
        try:
            async with self.http_client as client:
                response = await client.post(
                    f"{self.inbox_service_url}/monitor/{monitor_id}/stop"
                )
                
                return response.status_code == 200
                
        except Exception as e:
            logger.error(f"Error stopping inbox monitoring: {e}")
            return False
    
    def create_snapchat_email(self, username: str) -> str:
        """Create email address for Snapchat registration"""
        try:
            # Use async function synchronously
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                email_account = loop.run_until_complete(self.get_email_for_registration("snapchat", "registration"))
                
                if email_account:
                    return getattr(email_account, 'email', None) or getattr(email_account, 'email_address', None) or ""
                else:
                    # Fallback to generated email
                    domain = None
                    try:
                        domain = self.pool_manager.get_random_domain()
                    except Exception:
                        domain = "tempmail.com"
                    return f"{username}@{domain}"
                    
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"Error creating Snapchat email: {e}")
            # Return fallback email
            return f"{username}@tempmail.com"

# Global integrator instance
_email_integrator = None

def get_email_integrator(config: Dict = None) -> EmailAutomationIntegrator:
    """Get global email integrator instance"""
    global _email_integrator
    if _email_integrator is None:
        _email_integrator = EmailAutomationIntegrator(config)
    return _email_integrator

# Convenience functions for existing automation systems
async def get_snapchat_email() -> Optional[EmailAccount]:
    """Get email account for Snapchat registration"""
    integrator = get_email_integrator()
    return await integrator.get_email_for_registration("snapchat", "registration")

async def get_tinder_email() -> Optional[EmailAccount]:
    """Get email account for Tinder registration"""
    integrator = get_email_integrator()
    return await integrator.get_email_for_registration("tinder", "registration")

async def wait_for_snapchat_verification(email: str, timeout: int = 180) -> EmailVerificationResult:
    """Wait for Snapchat verification email"""
    integrator = get_email_integrator()
    return await integrator.wait_for_verification_email(email, "snapchat", timeout)

async def wait_for_tinder_verification(email: str, timeout: int = 120) -> EmailVerificationResult:
    """Wait for Tinder verification email"""  
    integrator = get_email_integrator()
    return await integrator.wait_for_verification_email(email, "tinder", timeout)

if __name__ == "__main__":
    async def test_email_integration():
        """Test email integration functionality"""
        print("Testing Email Integration...")
        
        integrator = EmailAutomationIntegrator()
        
        # Test getting email
        print("1. Getting email for Snapchat...")
        email_account = await get_snapchat_email()
        
        if email_account:
            print(f"   Got email: {email_account.email}")
            
            # Test waiting for verification (with timeout)
            print("2. Waiting for verification email (30s timeout)...")
            result = await wait_for_snapchat_verification(email_account.email, timeout=30)
            
            print(f"   Verification result: success={result.success}, code={result.verification_code}")
            
            # Return email to pool
            print("3. Returning email to pool...")
            returned = await integrator.return_email_to_pool(email_account.email, success=True)
            print(f"   Returned: {returned}")
        
        # Get pool statistics
        print("4. Pool statistics...")
        stats = await integrator.get_pool_statistics()
        print(f"   Available: {stats.get('available', 0)}")
        print(f"   Total: {stats.get('total_accounts', 0)}")
        
        print("Email integration test complete!")
    
    # Run test
    asyncio.run(test_email_integration())