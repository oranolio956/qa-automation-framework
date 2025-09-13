#!/usr/bin/env python3
"""
Twilio SMS Phone Number Pool Management
Dynamically manages Twilio phone numbers with 24-hour cooldown and auto-provisioning
"""

import os
import redis
import json
import time
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from twilio.rest import Client
from twilio.base.exceptions import TwilioException

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load Twilio configuration from environment
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_AREA_CODE = os.environ.get('TWILIO_AREA_CODE', '720')
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')

class TwilioPhonePool:
    """Manages a pool of Twilio phone numbers with automatic provisioning and cooldown"""
    
    def __init__(self):
        self.client = None
        self.redis_client = None
        self._initialize_clients()
        self.pool_key = 'twilio_phone_pool'
        self.cooldown_key = 'twilio_phone_cooldown'
        self.cooldown_hours = 24
        
    def _initialize_clients(self):
        """Initialize Twilio and Redis clients"""
        try:
            if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
                raise ValueError("TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set")
            
            self.client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            logger.info("Twilio client initialized successfully")
            
            self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            self.redis_client.ping()
            logger.info(f"Redis client connected: {REDIS_URL}")
            
        except Exception as e:
            logger.error(f"Failed to initialize clients: {e}")
            raise
    
    def get_available_numbers(self) -> List[Dict]:
        """Get list of available phone numbers from pool"""
        try:
            pool_data = self.redis_client.get(self.pool_key)
            if pool_data:
                return json.loads(pool_data)
            return []
        except Exception as e:
            logger.error(f"Error getting available numbers: {e}")
            return []
    
    def get_cooldown_numbers(self) -> Dict:
        """Get numbers currently in cooldown period"""
        try:
            cooldown_data = self.redis_client.get(self.cooldown_key)
            if cooldown_data:
                return json.loads(cooldown_data)
            return {}
        except Exception as e:
            logger.error(f"Error getting cooldown numbers: {e}")
            return {}
    
    def purchase_new_number(self) -> Optional[str]:
        """Purchase a new Twilio phone number in the specified area code"""
        try:
            logger.info(f"Purchasing new phone number in area code {TWILIO_AREA_CODE}")
            
            # Search for available numbers
            available_numbers = self.client.available_phone_numbers('US').local.list(
                area_code=TWILIO_AREA_CODE,
                limit=5
            )
            
            if not available_numbers:
                logger.error(f"No available numbers in area code {TWILIO_AREA_CODE}")
                return None
            
            # Purchase the first available number
            phone_number = available_numbers[0].phone_number
            incoming_number = self.client.incoming_phone_numbers.create(
                phone_number=phone_number,
                voice_url='https://demo.twilio.com/welcome/voice/',  # Default voice handler
                sms_url='https://demo.twilio.com/welcome/sms/'        # Default SMS handler
            )
            
            logger.info(f"Successfully purchased phone number: {phone_number}")
            
            # Add to available pool
            self._add_to_pool(phone_number, incoming_number.sid)
            
            return phone_number
            
        except TwilioException as e:
            logger.error(f"Twilio error purchasing number: {e}")
            return None
        except Exception as e:
            logger.error(f"Error purchasing new number: {e}")
            return None
    
    def _add_to_pool(self, phone_number: str, number_sid: str):
        """Add a phone number to the available pool"""
        try:
            available_numbers = self.get_available_numbers()
            
            # Check if number already exists
            for num_data in available_numbers:
                if num_data['phone_number'] == phone_number:
                    logger.info(f"Number {phone_number} already in pool")
                    return
            
            # Add new number to pool
            number_data = {
                'phone_number': phone_number,
                'number_sid': number_sid,
                'added_at': datetime.now().isoformat(),
                'usage_count': 0
            }
            
            available_numbers.append(number_data)
            
            # Save updated pool
            self.redis_client.set(self.pool_key, json.dumps(available_numbers))
            logger.info(f"Added {phone_number} to available pool")
            
        except Exception as e:
            logger.error(f"Error adding number to pool: {e}")
    
    def get_number(self) -> Optional[str]:
        """Get an available phone number from the pool"""
        try:
            available_numbers = self.get_available_numbers()
            
            # If pool is empty, try to purchase a new number
            if not available_numbers:
                logger.info("Phone pool is empty, purchasing new number")
                new_number = self.purchase_new_number()
                if new_number:
                    return new_number
                else:
                    logger.error("Failed to purchase new number and pool is empty")
                    return None
            
            # Get the first available number
            number_data = available_numbers.pop(0)
            phone_number = number_data['phone_number']
            
            # Update usage count
            number_data['usage_count'] += 1
            number_data['last_used'] = datetime.now().isoformat()
            
            # Save updated pool (without the number we just took)
            self.redis_client.set(self.pool_key, json.dumps(available_numbers))
            
            logger.info(f"Allocated phone number: {phone_number} (usage: {number_data['usage_count']})")
            return phone_number
            
        except Exception as e:
            logger.error(f"Error getting phone number: {e}")
            return None
    
    def release_number(self, phone_number: str):
        """Release a phone number back to the pool with cooldown"""
        try:
            logger.info(f"Releasing phone number: {phone_number}")
            
            # Add to cooldown
            cooldown_numbers = self.get_cooldown_numbers()
            cooldown_until = (datetime.now() + timedelta(hours=self.cooldown_hours)).isoformat()
            
            cooldown_numbers[phone_number] = {
                'released_at': datetime.now().isoformat(),
                'cooldown_until': cooldown_until,
                'phone_number': phone_number
            }
            
            # Save cooldown data
            self.redis_client.set(self.cooldown_key, json.dumps(cooldown_numbers))
            
            # Set Redis expiration for automatic cleanup
            self.redis_client.expire(self.cooldown_key, self.cooldown_hours * 3600)
            
            logger.info(f"Number {phone_number} in cooldown until {cooldown_until}")
            
        except Exception as e:
            logger.error(f"Error releasing number {phone_number}: {e}")
    
    def cleanup_cooldown(self):
        """Clean up expired cooldown numbers and return them to available pool"""
        try:
            cooldown_numbers = self.get_cooldown_numbers()
            current_time = datetime.now()
            
            expired_numbers = []
            active_cooldowns = {}
            
            for phone_number, cooldown_data in cooldown_numbers.items():
                cooldown_until = datetime.fromisoformat(cooldown_data['cooldown_until'])
                
                if current_time >= cooldown_until:
                    expired_numbers.append(phone_number)
                    logger.info(f"Number {phone_number} cooldown expired, returning to pool")
                else:
                    active_cooldowns[phone_number] = cooldown_data
            
            # Update cooldown data (remove expired)
            self.redis_client.set(self.cooldown_key, json.dumps(active_cooldowns))
            
            # Add expired numbers back to available pool
            available_numbers = self.get_available_numbers()
            for phone_number in expired_numbers:
                # Find the number data (we need the SID)
                number_data = {
                    'phone_number': phone_number,
                    'number_sid': f"PN{phone_number.replace('+', '').replace('-', '')}",  # Reconstructed SID
                    'added_at': datetime.now().isoformat(),
                    'usage_count': 0,
                    'returned_from_cooldown': True
                }
                available_numbers.append(number_data)
            
            if expired_numbers:
                self.redis_client.set(self.pool_key, json.dumps(available_numbers))
                logger.info(f"Returned {len(expired_numbers)} numbers to available pool")
            
        except Exception as e:
            logger.error(f"Error during cooldown cleanup: {e}")
    
    def get_pool_status(self) -> Dict:
        """Get current pool status and statistics"""
        try:
            available_numbers = self.get_available_numbers()
            cooldown_numbers = self.get_cooldown_numbers()
            
            # Calculate total usage
            total_usage = sum(num.get('usage_count', 0) for num in available_numbers)
            
            return {
                'available_count': len(available_numbers),
                'cooldown_count': len(cooldown_numbers),
                'total_numbers': len(available_numbers) + len(cooldown_numbers),
                'total_usage': total_usage,
                'area_code': TWILIO_AREA_CODE,
                'cooldown_hours': self.cooldown_hours,
                'available_numbers': [num['phone_number'] for num in available_numbers],
                'cooldown_numbers': list(cooldown_numbers.keys())
            }
            
        except Exception as e:
            logger.error(f"Error getting pool status: {e}")
            return {}
    
    def send_sms(self, to_number: str, message: str, from_number: Optional[str] = None) -> bool:
        """Send SMS using a number from the pool"""
        try:
            if not from_number:
                from_number = self.get_number()
                if not from_number:
                    logger.error("No available phone numbers to send SMS")
                    return False
            
            message_instance = self.client.messages.create(
                body=message,
                from_=from_number,
                to=to_number
            )
            
            logger.info(f"SMS sent successfully: {message_instance.sid}")
            logger.info(f"From: {from_number}, To: {to_number}")
            
            # Release the number back to cooldown
            self.release_number(from_number)
            
            return True
            
        except TwilioException as e:
            logger.error(f"Twilio error sending SMS: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending SMS: {e}")
            return False

# Global instance
_twilio_pool = None

def get_twilio_pool() -> TwilioPhonePool:
    """Get global Twilio phone pool instance"""
    global _twilio_pool
    if _twilio_pool is None:
        _twilio_pool = TwilioPhonePool()
    return _twilio_pool

def get_number() -> Optional[str]:
    """Get an available phone number from the pool"""
    return get_twilio_pool().get_number()

def release_number(phone_number: str):
    """Release a phone number back to the pool"""
    get_twilio_pool().release_number(phone_number)

def send_sms(to_number: str, message: str, from_number: Optional[str] = None) -> bool:
    """Send SMS using pool management"""
    return get_twilio_pool().send_sms(to_number, message, from_number)

def get_pool_status() -> Dict:
    """Get current pool status"""
    return get_twilio_pool().get_pool_status()

def cleanup_cooldown():
    """Clean up expired numbers in cooldown"""
    get_twilio_pool().cleanup_cooldown()

if __name__ == "__main__":
    # Test the pool functionality
    pool = TwilioPhonePool()
    
    print("Testing Twilio Phone Pool...")
    
    # Get pool status
    status = pool.get_pool_status()
    print(f"Pool Status: {json.dumps(status, indent=2)}")
    
    # Test getting a number
    number = pool.get_number()
    if number:
        print(f"Got number: {number}")
        
        # Test sending SMS (uncomment to test with real number)
        # success = pool.send_sms("+1234567890", "Test message from Twilio Pool", number)
        # print(f"SMS sent: {success}")
        
        # Release number
        pool.release_number(number)
        print(f"Released number: {number}")
    
    # Final status
    status = pool.get_pool_status()
    print(f"Final Status: {json.dumps(status, indent=2)}")