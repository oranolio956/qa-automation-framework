#!/usr/bin/env python3
"""
Twilio SMS Phone Number Pool Management
Dynamically manages Twilio phone numbers with 24-hour cooldown and auto-provisioning
"""

import os
try:
    from redis import asyncio as aioredis  # for type hints if needed later
except Exception:
    aioredis = None
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
# Optional API Key auth (preferred for production). Requires account SID as well.
TWILIO_API_KEY_SID = os.environ.get('TWILIO_API_KEY_SID')  # e.g., SKXXXXXXXX
TWILIO_API_KEY_SECRET = os.environ.get('TWILIO_API_KEY_SECRET')
TWILIO_AREA_CODE = os.environ.get('TWILIO_AREA_CODE', '720')
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')

class TwilioPhonePool:
    """Manages a pool of Twilio phone numbers with automatic provisioning and cooldown"""
    
    def __init__(self):
        self.client = None
        self.redis_client = None
        self.credentials_available = False
        
        # Initialize clients with proper error handling
        try:
            self._initialize_clients()
        except Exception as init_error:
            logger.error(f"❌ Failed to initialize TwilioPhonePool: {init_error}")
            # Don't raise - allow system to continue in degraded mode
            
        self.pool_key = 'twilio_phone_pool'
        self.cooldown_key = 'twilio_phone_cooldown'
        self.cooldown_hours = 24
        
        # Log initialization status
        if self.credentials_available and self.client:
            logger.info("🚀 TwilioPhonePool fully operational")
        else:
            logger.info("⚠️  TwilioPhonePool operating in degraded mode (SMS disabled)")
        
    def _initialize_clients(self):
        """Initialize Twilio and Redis clients with graceful credential handling"""
        # Initialize Redis first (always needed)
        self._initialize_redis()
        
        # Initialize Twilio with proper error handling
        self._initialize_twilio()
    
    def _initialize_redis(self):
        """Initialize Redis client with error handling"""
        try:
            # Use TLS if URL scheme is rediss
            tls_required = REDIS_URL.startswith('rediss://')
            client_kwargs = dict(
                decode_responses=True,
                max_connections=20,
                socket_keepalive=True,
                retry_on_timeout=True,
            )
            # Do not pass custom ssl args; redis.from_url handles rediss natively across platforms
            self.redis_client = redis.from_url(
                REDIS_URL,
                **client_kwargs
            )
            self.redis_client.ping()
            logger.info(f"✅ Redis client connected with connection pooling: {REDIS_URL.split('@')[0]}@***")
        except Exception as e:
            logger.error(f"❌ Redis initialization failed: {e}")
            self.redis_client = None
            # Do not raise to allow degraded mode
    
    def _initialize_twilio(self):
        """Initialize Twilio client with graceful credential handling"""
        try:
            # Require account SID always
            if not TWILIO_ACCOUNT_SID or not TWILIO_ACCOUNT_SID.startswith('AC'):
                logger.warning("⚠️  TWILIO_ACCOUNT_SID not configured or invalid")
                self.client = None
                self.credentials_available = False
                return

            # Prefer API Key if provided; else fall back to Account SID/Auth Token
            if TWILIO_API_KEY_SID and TWILIO_API_KEY_SECRET:
                logger.info("Initializing Twilio client with API Key credentials")
                self.client = Client(TWILIO_API_KEY_SID, TWILIO_API_KEY_SECRET, TWILIO_ACCOUNT_SID)
            else:
                if not TWILIO_AUTH_TOKEN:
                    logger.warning("⚠️  TWILIO_AUTH_TOKEN not set; SMS disabled")
                    self.client = None
                    self.credentials_available = False
                    return
                self.client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            
            # Test connection
            try:
                # Validate credentials by fetching account info
                account = self.client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
                logger.info(f"✅ Twilio client initialized successfully for account: {account.friendly_name}")
                logger.info(f"📊 Account status: {account.status}")
                logger.info(f"🏷️  Account type: {account.type}")
                self.credentials_available = True
            except Exception as test_e:
                logger.error(f"❌ Twilio credential validation failed: {test_e}")
                logger.info("🔍 Check your TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN")
                self.client = None
                self.credentials_available = False
                
        except Exception as e:
            logger.error(f"❌ Twilio initialization failed: {e}")
            self.client = None
            self.credentials_available = False
    
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
    
    def purchase_new_number(self, sms_webhook_url: Optional[str] = None) -> Optional[str]:
        """Purchase a new Twilio phone number with proper webhook configuration"""
        try:
            logger.info(f"Purchasing new phone number in area code {TWILIO_AREA_CODE}")
            
            # Search for available numbers with SMS capability
            available_numbers = self.client.available_phone_numbers('US').local.list(
                area_code=TWILIO_AREA_CODE,
                sms_enabled=True,
                voice_enabled=True,
                limit=10
            )
            
            if not available_numbers:
                logger.error(f"No available SMS-enabled numbers in area code {TWILIO_AREA_CODE}")
                return None
            
            # Purchase the first available number
            phone_number = available_numbers[0].phone_number
            
            # Configure webhooks for SMS service integration
            webhook_config = {
                'phone_number': phone_number,
                'voice_url': 'https://demo.twilio.com/welcome/voice/',  # Default voice handler
            }
            
            # Set SMS webhook if provided (for status updates)
            if sms_webhook_url:
                webhook_config['sms_url'] = sms_webhook_url
                webhook_config['sms_method'] = 'POST'
            else:
                webhook_config['sms_url'] = 'https://demo.twilio.com/welcome/sms/'
            
            incoming_number = self.client.incoming_phone_numbers.create(**webhook_config)
            
            logger.info(f"Successfully purchased phone number: {phone_number} with SID: {incoming_number.sid}")
            
            # Add to available pool with enhanced metadata
            self._add_to_pool(phone_number, incoming_number.sid, {
                'purchased_at': datetime.now().isoformat(),
                'area_code': TWILIO_AREA_CODE,
                'capabilities': {
                    'sms': True,
                    'voice': True
                },
                'webhook_configured': sms_webhook_url is not None
            })
            
            return phone_number
            
        except TwilioException as e:
            logger.error(f"Twilio error purchasing number: {e}")
            return None
        except Exception as e:
            logger.error(f"Error purchasing new number: {e}")
            return None
    
    def _add_to_pool(self, phone_number: str, number_sid: str, metadata: dict = None):
        """Add a phone number to the available pool with enhanced metadata"""
        try:
            available_numbers = self.get_available_numbers()
            
            # Check if number already exists
            for num_data in available_numbers:
                if num_data['phone_number'] == phone_number:
                    logger.info(f"Number {phone_number} already in pool")
                    return
            
            # Add new number to pool with enhanced data
            number_data = {
                'phone_number': phone_number,
                'number_sid': number_sid,
                'added_at': datetime.now().isoformat(),
                'usage_count': 0,
                'last_used': None,
                'status': 'active',
                'metadata': metadata or {}
            }
            
            available_numbers.append(number_data)
            
            # Save updated pool with transaction for consistency
            pipe = self.redis_client.pipeline()
            pipe.set(self.pool_key, json.dumps(available_numbers))
            pipe.expire(self.pool_key, 86400 * 30)  # 30 days expiration
            pipe.execute()
            
            logger.info(f"Added {phone_number} to available pool with metadata", 
                       metadata=metadata)
            
        except Exception as e:
            logger.error(f"Error adding number to pool: {e}")
    
    def get_number(self) -> Optional[str]:
        """Get an available phone number from the pool with credential checking"""
        try:
            # Check if Twilio credentials are available
            if not self.credentials_available:
                logger.error("❌ Cannot get phone number - Twilio credentials not configured")
                return None
                
            if not self.redis_client:
                logger.error("❌ Cannot get phone number - Redis not available")
                return None
            
            available_numbers = self.get_available_numbers()
            
            # If pool is empty, try to purchase a new number
            if not available_numbers:
                logger.info("📞 Phone pool is empty, attempting to purchase new number")
                new_number = self.purchase_new_number()
                if new_number:
                    return new_number
                else:
                    logger.error("❌ Failed to purchase new number and pool is empty")
                    return None
            
            # Get the first available number
            number_data = available_numbers.pop(0)
            phone_number = number_data['phone_number']
            
            # Update usage count
            number_data['usage_count'] += 1
            number_data['last_used'] = datetime.now().isoformat()
            
            # Save updated pool (without the number we just taken)
            self.redis_client.set(self.pool_key, json.dumps(available_numbers))
            
            logger.info(f"📱 Allocated phone number: {phone_number[-4:]} (usage: {number_data['usage_count']})")
            return phone_number
            
        except Exception as e:
            logger.error(f"❌ Error getting phone number: {e}")
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
        """Get comprehensive pool status and health metrics"""
        try:
            available_numbers = self.get_available_numbers()
            cooldown_numbers = self.get_cooldown_numbers()
            
            # Calculate usage statistics
            total_usage = sum(num.get('usage_count', 0) for num in available_numbers)
            avg_usage = total_usage / len(available_numbers) if available_numbers else 0
            
            # Calculate cooldown status
            current_time = datetime.now()
            cooldown_ready_soon = 0
            
            for cooldown_data in cooldown_numbers.values():
                cooldown_until = datetime.fromisoformat(cooldown_data['cooldown_until'])
                time_remaining = (cooldown_until - current_time).total_seconds()
                if 0 < time_remaining <= 3600:  # Ready within 1 hour
                    cooldown_ready_soon += 1
            
            # Health metrics
            health_score = min(100, (len(available_numbers) / max(1, len(available_numbers) + len(cooldown_numbers))) * 100)
            
            status = {
                'timestamp': current_time.isoformat(),
                'pool_health': {
                    'available_count': len(available_numbers),
                    'cooldown_count': len(cooldown_numbers),
                    'total_numbers': len(available_numbers) + len(cooldown_numbers),
                    'health_score': round(health_score, 1),
                    'ready_soon_count': cooldown_ready_soon
                },
                'usage_stats': {
                    'total_usage': total_usage,
                    'average_usage': round(avg_usage, 2),
                    'most_used': max([num.get('usage_count', 0) for num in available_numbers], default=0)
                },
                'configuration': {
                    'area_code': TWILIO_AREA_CODE,
                    'cooldown_hours': self.cooldown_hours,
                    'redis_connected': self.redis_client is not None
                },
                'numbers': {
                    'available': [{
                        'phone_number': num['phone_number'],
                        'usage_count': num.get('usage_count', 0),
                        'added_at': num.get('added_at'),
                        'status': num.get('status', 'active')
                    } for num in available_numbers],
                    'cooldown': [{
                        'phone_number': phone,
                        'cooldown_until': data['cooldown_until'],
                        'released_at': data['released_at']
                    } for phone, data in cooldown_numbers.items()]
                }
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting pool status: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'pool_health': {'available_count': 0, 'health_score': 0}
            }
    
    def send_sms(self, to_number: str, message: str, from_number: Optional[str] = None, 
                 webhook_url: Optional[str] = None) -> dict:
        """Send SMS using a number from the pool with enhanced tracking and credential validation"""
        try:
            # Validate system readiness
            if not self.credentials_available:
                return {
                    'success': False, 
                    'error': 'SMS functionality disabled - Twilio credentials not configured',
                    'error_code': 'CREDENTIALS_MISSING',
                    'instructions': 'Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN environment variables'
                }
                
            if not self.client:
                return {
                    'success': False, 
                    'error': 'SMS functionality disabled - Twilio client not initialized',
                    'error_code': 'CLIENT_UNAVAILABLE'
                }
                
            if not self.redis_client:
                return {
                    'success': False, 
                    'error': 'SMS tracking disabled - Redis not available',
                    'error_code': 'REDIS_UNAVAILABLE'
                }
            
            # Get phone number if not provided
            if not from_number:
                from_number = self.get_number()
                if not from_number:
                    return {
                        'success': False, 
                        'error': 'No available phone numbers to send SMS',
                        'error_code': 'NO_NUMBERS_AVAILABLE',
                        'suggestion': 'Check Twilio account balance and number pool'
                    }
            
            # Prepare message parameters
            message_params = {
                'body': message,
                'from_': from_number,
                'to': to_number
            }
            
            # Add status callback if webhook provided
            if webhook_url:
                message_params['status_callback'] = webhook_url
                message_params['provide_feedback'] = True
            
            # Send the message
            message_instance = self.client.messages.create(**message_params)
            
            logger.info(f"📤 SMS sent successfully: {message_instance.sid}")
            logger.info(f"📞 From: {from_number}, To: ***{to_number[-4:]}")
            
            # Store message tracking info in Redis
            message_info = {
                'message_id': message_instance.sid,
                'from_number': from_number,
                'to_number': to_number,
                'status': message_instance.status,
                'sent_at': datetime.now().isoformat(),
                'provider': 'twilio_pool',
                'webhook_configured': webhook_url is not None
            }
            
            # Store in Redis for tracking
            try:
                if self.redis_client:
                    self.redis_client.hset(
                        f"sms_pool:{message_instance.sid}",
                        mapping=message_info
                    )
                    self.redis_client.expire(f"sms_pool:{message_instance.sid}", 86400 * 7)  # 7 days
            except Exception as e:
                logger.warning(f"⚠️  Failed to store SMS tracking info: {e}")
            
            # Release the number back to cooldown
            self.release_number(from_number)
            
            return {
                'success': True,
                'message_id': message_instance.sid,
                'status': message_instance.status,
                'from_number': from_number,
                'credentials_status': 'active'
            }
            
        except TwilioException as e:
            logger.error(f"❌ Twilio error sending SMS: {e}")
            return {
                'success': False, 
                'error': f'Twilio API error: {str(e)}',
                'error_code': 'TWILIO_API_ERROR',
                'from_number': from_number
            }
        except Exception as e:
            logger.error(f"❌ Error sending SMS: {e}")
            return {
                'success': False, 
                'error': str(e),
                'error_code': 'GENERAL_ERROR',
                'from_number': from_number
            }

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