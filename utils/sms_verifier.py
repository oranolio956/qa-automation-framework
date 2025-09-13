#!/usr/bin/env python3
"""
SMS Verification Service with Dynamic Twilio Phone Number Pool
Handles SMS verification using dynamically managed Twilio phone numbers
"""

import os
import re
import time
import logging
import json
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
from twilio.rest import Client
from twilio.base.exceptions import TwilioException

# Import our Twilio phone pool
try:
    from .twilio_pool import get_twilio_pool, send_sms, get_number, release_number
except ImportError:
    # Fallback for direct execution
    import sys
    sys.path.append(os.path.dirname(__file__))
    from twilio_pool import get_twilio_pool, send_sms, get_number, release_number

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SMSVerifier:
    """SMS verification service using dynamic Twilio phone number pool"""
    
    def __init__(self):
        self.pool = get_twilio_pool()
        self.verification_codes = {}  # In-memory storage for codes (use Redis in production)
        self.code_length = 6
        self.code_expiry_minutes = 10
    
    def generate_verification_code(self) -> str:
        """Generate a 6-digit verification code"""
        import random
        return ''.join([str(random.randint(0, 9)) for _ in range(self.code_length)])
    
    def send_verification_sms(self, to_number: str, app_name: str = "TinderQA") -> Dict[str, any]:
        """Send SMS verification code using dynamic phone number from pool"""
        try:
            # Clean phone number format
            clean_number = self.clean_phone_number(to_number)
            if not clean_number:
                return {
                    'success': False,
                    'error': 'Invalid phone number format',
                    'phone_number': to_number
                }
            
            # Generate verification code
            code = self.generate_verification_code()
            
            # Create message
            message = f"Your {app_name} verification code is: {code}. This code expires in {self.code_expiry_minutes} minutes."
            
            # Get phone number from pool
            from_number = get_number()
            if not from_number:
                return {
                    'success': False,
                    'error': 'No available phone numbers in pool',
                    'phone_number': clean_number
                }
            
            # Send SMS using pool
            success = send_sms(clean_number, message, from_number)
            
            if success:
                # Store verification code with expiration
                self.verification_codes[clean_number] = {
                    'code': code,
                    'created_at': datetime.now(),
                    'expires_at': datetime.now() + timedelta(minutes=self.code_expiry_minutes),
                    'from_number': from_number,
                    'attempts': 0
                }
                
                logger.info(f"Verification SMS sent to {clean_number} from {from_number}")
                
                return {
                    'success': True,
                    'phone_number': clean_number,
                    'from_number': from_number,
                    'code_length': self.code_length,
                    'expires_in_minutes': self.code_expiry_minutes,
                    'message_sent': True
                }
            else:
                # Release number back to pool if sending failed
                release_number(from_number)
                return {
                    'success': False,
                    'error': 'Failed to send SMS',
                    'phone_number': clean_number,
                    'from_number': from_number
                }
            
        except Exception as e:
            logger.error(f"Error sending verification SMS: {e}")
            return {
                'success': False,
                'error': str(e),
                'phone_number': to_number
            }
    
    def verify_sms_code(self, phone_number: str, submitted_code: str) -> Dict[str, any]:
        """Verify SMS code against stored verification"""
        try:
            clean_number = self.clean_phone_number(phone_number)
            if not clean_number:
                return {
                    'success': False,
                    'error': 'Invalid phone number format'
                }
            
            # Check if verification exists
            if clean_number not in self.verification_codes:
                return {
                    'success': False,
                    'error': 'No verification code found for this number'
                }
            
            verification_data = self.verification_codes[clean_number]
            
            # Check if code has expired
            if datetime.now() > verification_data['expires_at']:
                del self.verification_codes[clean_number]
                return {
                    'success': False,
                    'error': 'Verification code has expired'
                }
            
            # Increment attempt counter
            verification_data['attempts'] += 1
            
            # Check attempt limit
            if verification_data['attempts'] > 3:
                del self.verification_codes[clean_number]
                return {
                    'success': False,
                    'error': 'Too many failed attempts'
                }
            
            # Verify code
            if submitted_code == verification_data['code']:
                # Success - clean up
                del self.verification_codes[clean_number]
                logger.info(f"SMS verification successful for {clean_number}")
                
                return {
                    'success': True,
                    'phone_number': clean_number,
                    'verified_at': datetime.now().isoformat(),
                    'attempts_used': verification_data['attempts']
                }
            else:
                # Wrong code
                logger.warning(f"Wrong verification code for {clean_number}. Attempt {verification_data['attempts']}/3")
                return {
                    'success': False,
                    'error': 'Invalid verification code',
                    'attempts_remaining': 3 - verification_data['attempts']
                }
                
        except Exception as e:
            logger.error(f"Error verifying SMS code: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def clean_phone_number(self, phone_number: str) -> Optional[str]:
        """Clean and validate phone number format"""
        try:
            # Remove all non-digit characters except +
            cleaned = re.sub(r'[^\d+]', '', phone_number)
            
            # Add +1 if no country code
            if not cleaned.startswith('+'):
                if len(cleaned) == 10:  # US number without country code
                    cleaned = '+1' + cleaned
                elif len(cleaned) == 11 and cleaned.startswith('1'):
                    cleaned = '+' + cleaned
                else:
                    return None
            
            # Validate US phone number format
            if len(cleaned) == 12 and cleaned.startswith('+1'):
                return cleaned
            
            return None
            
        except Exception:
            return None
    
    def get_verification_status(self, phone_number: str) -> Dict[str, any]:
        """Get current verification status for a phone number"""
        try:
            clean_number = self.clean_phone_number(phone_number)
            if not clean_number or clean_number not in self.verification_codes:
                return {
                    'has_pending_verification': False,
                    'phone_number': clean_number or phone_number
                }
            
            verification_data = self.verification_codes[clean_number]
            is_expired = datetime.now() > verification_data['expires_at']
            
            if is_expired:
                del self.verification_codes[clean_number]
                return {
                    'has_pending_verification': False,
                    'phone_number': clean_number,
                    'was_expired': True
                }
            
            time_remaining = verification_data['expires_at'] - datetime.now()
            
            return {
                'has_pending_verification': True,
                'phone_number': clean_number,
                'created_at': verification_data['created_at'].isoformat(),
                'expires_at': verification_data['expires_at'].isoformat(),
                'minutes_remaining': int(time_remaining.total_seconds() / 60),
                'attempts_used': verification_data['attempts'],
                'attempts_remaining': 3 - verification_data['attempts']
            }
            
        except Exception as e:
            logger.error(f"Error getting verification status: {e}")
            return {
                'has_pending_verification': False,
                'error': str(e)
            }
    
    def resend_verification(self, phone_number: str) -> Dict[str, any]:
        """Resend verification SMS (if not too recent)"""
        try:
            clean_number = self.clean_phone_number(phone_number)
            if not clean_number:
                return {
                    'success': False,
                    'error': 'Invalid phone number format'
                }
            
            # Check if there's a recent verification
            if clean_number in self.verification_codes:
                last_sent = self.verification_codes[clean_number]['created_at']
                time_since_last = datetime.now() - last_sent
                
                # Require at least 1 minute between resends
                if time_since_last < timedelta(minutes=1):
                    seconds_remaining = 60 - int(time_since_last.total_seconds())
                    return {
                        'success': False,
                        'error': f'Please wait {seconds_remaining} seconds before requesting another code'
                    }
            
            # Send new verification
            return self.send_verification_sms(clean_number)
            
        except Exception as e:
            logger.error(f"Error resending verification: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def cleanup_expired_codes(self):
        """Clean up expired verification codes"""
        try:
            current_time = datetime.now()
            expired_numbers = []
            
            for phone_number, verification_data in self.verification_codes.items():
                if current_time > verification_data['expires_at']:
                    expired_numbers.append(phone_number)
            
            for phone_number in expired_numbers:
                del self.verification_codes[phone_number]
                logger.info(f"Cleaned up expired verification for {phone_number}")
            
            return len(expired_numbers)
            
        except Exception as e:
            logger.error(f"Error cleaning up expired codes: {e}")
            return 0
    
    def get_statistics(self) -> Dict[str, any]:
        """Get SMS verification statistics"""
        try:
            active_verifications = len(self.verification_codes)
            
            # Get pool statistics
            pool_status = self.pool.get_pool_status()
            
            return {
                'active_verifications': active_verifications,
                'code_length': self.code_length,
                'code_expiry_minutes': self.code_expiry_minutes,
                'pool_status': pool_status,
                'current_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {'error': str(e)}

# Global instance
_sms_verifier = None

def get_sms_verifier() -> SMSVerifier:
    """Get global SMS verifier instance"""
    global _sms_verifier
    if _sms_verifier is None:
        _sms_verifier = SMSVerifier()
    return _sms_verifier

# Convenience functions
def send_verification_sms(phone_number: str, app_name: str = "TinderQA") -> Dict[str, any]:
    """Send verification SMS using dynamic phone pool"""
    return get_sms_verifier().send_verification_sms(phone_number, app_name)

def verify_sms_code(phone_number: str, code: str) -> Dict[str, any]:
    """Verify SMS code"""
    return get_sms_verifier().verify_sms_code(phone_number, code)

def get_verification_status(phone_number: str) -> Dict[str, any]:
    """Get verification status"""
    return get_sms_verifier().get_verification_status(phone_number)

def resend_verification(phone_number: str) -> Dict[str, any]:
    """Resend verification SMS"""
    return get_sms_verifier().resend_verification(phone_number)

if __name__ == "__main__":
    # Test SMS verification functionality
    verifier = SMSVerifier()
    
    print("Testing SMS Verifier...")
    
    # Test phone number cleaning
    test_numbers = [
        "+1234567890",
        "1234567890", 
        "(123) 456-7890",
        "123-456-7890"
    ]
    
    for number in test_numbers:
        cleaned = verifier.clean_phone_number(number)
        print(f"Original: {number} -> Cleaned: {cleaned}")
    
    # Test verification workflow (uncomment to test with real number)
    # test_number = "+1234567890"  # Replace with actual number for testing
    # 
    # # Send verification
    # result = verifier.send_verification_sms(test_number)
    # print(f"Send result: {json.dumps(result, indent=2)}")
    # 
    # if result['success']:
    #     # Test verification status
    #     status = verifier.get_verification_status(test_number)
    #     print(f"Status: {json.dumps(status, indent=2)}")
    #     
    #     # Test code verification (would need actual code from SMS)
    #     # verify_result = verifier.verify_sms_code(test_number, "123456")
    #     # print(f"Verify result: {json.dumps(verify_result, indent=2)}")
    
    # Get statistics
    stats = verifier.get_statistics()
    print(f"Statistics: {json.dumps(stats, indent=2)}")