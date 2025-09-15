#!/usr/bin/env python3
"""
Snapchat Registration Flow Module

Handles the core registration process with state management and error recovery.
Extracted from stealth_creator.py for better maintainability.
"""

import os
import time
import random
import logging
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class RegistrationState(Enum):
    """Registration flow states for state machine"""
    INITIAL = "initial"
    WELCOME_SCREEN = "welcome_screen"
    SIGN_UP_CLICKED = "sign_up_clicked"
    NAME_ENTRY = "name_entry"
    USERNAME_ENTRY = "username_entry"
    PASSWORD_ENTRY = "password_entry"
    BIRTHDAY_ENTRY = "birthday_entry"
    PHONE_ENTRY = "phone_entry"
    PHONE_VERIFICATION = "phone_verification"
    EMAIL_VERIFICATION = "email_verification"
    PROFILE_SETUP = "profile_setup"
    COMPLETED = "completed"
    FAILED = "failed"
    CAPTCHA_DETECTED = "captcha_detected"


@dataclass
class RegistrationProgress:
    """Track registration progress and state"""
    current_state: RegistrationState = RegistrationState.INITIAL
    start_time: datetime = None
    last_action_time: datetime = None
    retry_count: int = 0
    error_history: List[str] = None
    captcha_count: int = 0
    
    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.now()
        if self.last_action_time is None:
            self.last_action_time = datetime.now()
        if self.error_history is None:
            self.error_history = []


class SnapchatRegistrationFlow:
    """State machine-based registration flow for reliability and recovery"""
    
    def __init__(self, automator, anti_detection, captcha_handler=None):
        self.automator = automator
        self.anti_detection = anti_detection
        self.captcha_handler = captcha_handler
        self.progress = RegistrationProgress()
        
        # State machine configuration
        self.max_retries_per_state = 3
        self.max_total_retries = 10
        self.captcha_detection_enabled = captcha_handler is not None
        
        # State transition map
        self.state_transitions = {
            RegistrationState.INITIAL: self._handle_initial,
            RegistrationState.WELCOME_SCREEN: self._handle_welcome_screen,
            RegistrationState.SIGN_UP_CLICKED: self._handle_sign_up_clicked,
            RegistrationState.NAME_ENTRY: self._handle_name_entry,
            RegistrationState.USERNAME_ENTRY: self._handle_username_entry,
            RegistrationState.PASSWORD_ENTRY: self._handle_password_entry,
            RegistrationState.BIRTHDAY_ENTRY: self._handle_birthday_entry,
            RegistrationState.PHONE_ENTRY: self._handle_phone_entry,
            RegistrationState.PHONE_VERIFICATION: self._handle_phone_verification,
            RegistrationState.EMAIL_VERIFICATION: self._handle_email_verification,
            RegistrationState.PROFILE_SETUP: self._handle_profile_setup,
        }
    
    def execute_registration(self, profile) -> Dict[str, any]:
        """Execute the complete registration flow with state management"""
        logger.info(f"Starting registration flow for {profile.username}")
        self.profile = profile
        
        try:
            while (self.progress.current_state not in [RegistrationState.COMPLETED, RegistrationState.FAILED] 
                   and self.progress.retry_count < self.max_total_retries):
                
                # Check for CAPTCHA before each major state transition
                if self.captcha_detection_enabled and self._should_check_captcha():
                    captcha_result = self._check_for_captcha()
                    if captcha_result.get('detected'):
                        return self._handle_captcha_detection(captcha_result)
                
                # Execute current state handler
                try:
                    state_handler = self.state_transitions.get(self.progress.current_state)
                    if state_handler:
                        result = state_handler()
                        if result.get('success'):
                            self._advance_state(result.get('next_state'))
                        else:
                            self._handle_state_failure(result)
                    else:
                        logger.error(f"No handler for state: {self.progress.current_state}")
                        self.progress.current_state = RegistrationState.FAILED
                        
                except Exception as e:
                    logger.error(f"Error in state {self.progress.current_state}: {e}")
                    self._handle_state_failure({'error': str(e)})
                
                # Update timing
                self.progress.last_action_time = datetime.now()
            
            # Final result
            if self.progress.current_state == RegistrationState.COMPLETED:
                return {
                    'success': True,
                    'profile': profile,
                    'duration': (datetime.now() - self.progress.start_time).total_seconds(),
                    'retry_count': self.progress.retry_count
                }
            else:
                return {
                    'success': False,
                    'error': f"Registration failed in state: {self.progress.current_state}",
                    'retry_count': self.progress.retry_count,
                    'error_history': self.progress.error_history
                }
                
        except Exception as e:
            logger.error(f"Critical registration error: {e}")
            return {
                'success': False,
                'error': f"Critical error: {str(e)}",
                'state': self.progress.current_state.value
            }
    
    def _advance_state(self, next_state: RegistrationState):
        """Advance to next state with logging"""
        if next_state:
            logger.info(f"Advancing: {self.progress.current_state.value} → {next_state.value}")
            self.progress.current_state = next_state
            self.progress.retry_count = 0  # Reset retry count for new state
    
    def _handle_state_failure(self, result: Dict):
        """Handle failure in current state with retry logic"""
        error_msg = result.get('error', 'Unknown error')
        self.progress.error_history.append(f"{self.progress.current_state.value}: {error_msg}")
        self.progress.retry_count += 1
        
        logger.warning(f"State {self.progress.current_state.value} failed (retry {self.progress.retry_count}): {error_msg}")
        
        if self.progress.retry_count >= self.max_retries_per_state:
            logger.error(f"Max retries exceeded for state {self.progress.current_state.value}")
            self.progress.current_state = RegistrationState.FAILED
        else:
            # Add delay before retry with exponential backoff
            delay = min(2 ** self.progress.retry_count, 10)
            time.sleep(delay + random.uniform(0, 2))
    
    def _should_check_captcha(self) -> bool:
        """Determine if CAPTCHA check is needed based on current state"""
        captcha_check_states = [
            RegistrationState.SIGN_UP_CLICKED,
            RegistrationState.USERNAME_ENTRY,
            RegistrationState.PHONE_ENTRY,
            RegistrationState.PHONE_VERIFICATION
        ]
        return self.progress.current_state in captcha_check_states
    
    def _check_for_captcha(self) -> Dict[str, any]:
        """Check for CAPTCHA using the handler"""
        try:
            # Use configuration manager for proper path generation
            try:
                from .config import get_config
                config = get_config()
                screenshot_path = config.get_temp_file_path(f"snapchat_captcha_{int(time.time())}.png")
            except ImportError:
                # Fallback to temp directory
                import tempfile
                screenshot_path = f"{tempfile.gettempdir()}/snapchat_captcha_{int(time.time())}.png"
            if self.automator.take_screenshot(screenshot_path):
                
                # Check regular CAPTCHA
                captcha_result = self.captcha_handler.detect_captcha(screenshot_path)
                if captcha_result.get('detected'):
                    self.progress.captcha_count += 1
                    return {
                        'detected': True,
                        'type': 'captcha',
                        'requires_manual': True,
                        'details': captcha_result
                    }
                
                # Check Arkose challenge
                arkose_result = self.captcha_handler.detect_arkose_challenge(screenshot_path)
                if arkose_result.get('detected'):
                    self.progress.captcha_count += 1
                    return {
                        'detected': True,
                        'type': 'arkose',
                        'requires_manual': True,
                        'details': arkose_result
                    }
                
                # Clean up
                try:
                    os.remove(screenshot_path)
                except:
                    pass
                    
            return {'detected': False}
            
        except Exception as e:
            logger.error(f"CAPTCHA detection error: {e}")
            return {'detected': False, 'error': str(e)}
    
    def _handle_captcha_detection(self, captcha_result: Dict) -> Dict[str, any]:
        """Handle detected CAPTCHA"""
        self.progress.current_state = RegistrationState.CAPTCHA_DETECTED
        logger.warning(f"CAPTCHA detected: {captcha_result}")
        
        return {
            'success': False,
            'error': 'CAPTCHA detected - manual intervention required',
            'captcha_info': captcha_result,
            'state': RegistrationState.CAPTCHA_DETECTED.value
        }
    
    # State handlers
    def _handle_initial(self) -> Dict[str, any]:
        """Handle initial state - wait for app to load"""
        try:
            # Wait for app to fully load
            time.sleep(random.uniform(2, 4))
            
            # Check if we're already past welcome screen
            if self.automator.wait_for_element("Sign Up", timeout=10):
                return {'success': True, 'next_state': RegistrationState.WELCOME_SCREEN}
            elif self.automator.wait_for_element("Username", timeout=5):
                return {'success': True, 'next_state': RegistrationState.USERNAME_ENTRY}
            else:
                return {'success': False, 'error': 'App not loaded properly'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_welcome_screen(self) -> Dict[str, any]:
        """Handle welcome screen - click Sign Up"""
        try:
            if not self.automator.wait_for_element("Sign Up", timeout=30):
                return {'success': False, 'error': 'Sign Up button not found'}
            
            if not self.automator.tap_element("Sign Up"):
                return {'success': False, 'error': 'Failed to tap Sign Up'}
            
            # Add realistic delay
            delay = self.anti_detection.get_next_action_delay(self.automator.device_id)
            time.sleep(delay)
            
            return {'success': True, 'next_state': RegistrationState.SIGN_UP_CLICKED}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_sign_up_clicked(self) -> Dict[str, any]:
        """Handle post sign-up click - wait for name entry"""
        try:
            # Wait for name entry fields to appear
            if self.automator.wait_for_element("First name", timeout=15):
                return {'success': True, 'next_state': RegistrationState.NAME_ENTRY}
            elif self.automator.wait_for_element("Username", timeout=5):
                # Skip directly to username if name already handled
                return {'success': True, 'next_state': RegistrationState.USERNAME_ENTRY}
            else:
                return {'success': False, 'error': 'Name entry fields not found'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_name_entry(self) -> Dict[str, any]:
        """Handle name entry"""
        try:
            # Enter first name
            first_name = self.profile.display_name.split()[0]
            if not self.automator.enter_text(first_name, "First name"):
                return {'success': False, 'error': 'Failed to enter first name'}
            
            # Enter last name if available
            if len(self.profile.display_name.split()) > 1:
                last_name = self.profile.display_name.split()[-1]
                if not self.automator.enter_text(last_name, "Last name"):
                    return {'success': False, 'error': 'Failed to enter last name'}
            
            # Continue
            if not self.automator.tap_element("Continue"):
                return {'success': False, 'error': 'Failed to tap Continue after name entry'}
            
            delay = self.anti_detection.get_next_action_delay(self.automator.device_id)
            time.sleep(delay)
            
            return {'success': True, 'next_state': RegistrationState.USERNAME_ENTRY}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_username_entry(self) -> Dict[str, any]:
        """Handle username entry"""
        try:
            if not self.automator.wait_for_element("Username", timeout=15):
                return {'success': False, 'error': 'Username field not found'}
            
            if not self.automator.enter_text(self.profile.username, "Username"):
                return {'success': False, 'error': 'Failed to enter username'}
            
            if not self.automator.tap_element("Continue"):
                return {'success': False, 'error': 'Failed to continue after username'}
            
            delay = self.anti_detection.get_next_action_delay(self.automator.device_id)
            time.sleep(delay)
            
            return {'success': True, 'next_state': RegistrationState.PASSWORD_ENTRY}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_password_entry(self) -> Dict[str, any]:
        """Handle password entry"""
        try:
            if not self.automator.wait_for_element("Password", timeout=15):
                return {'success': False, 'error': 'Password field not found'}
            
            if not self.automator.enter_text(self.profile.password, "Password"):
                return {'success': False, 'error': 'Failed to enter password'}
            
            if not self.automator.tap_element("Continue"):
                return {'success': False, 'error': 'Failed to continue after password'}
            
            delay = self.anti_detection.get_next_action_delay(self.automator.device_id)
            time.sleep(delay)
            
            return {'success': True, 'next_state': RegistrationState.BIRTHDAY_ENTRY}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_birthday_entry(self) -> Dict[str, any]:
        """Handle birthday entry"""
        try:
            # Implementation would handle birthday picker UI
            # This is a simplified version
            if not self.automator.wait_for_element("Birthday", timeout=15):
                return {'success': False, 'error': 'Birthday picker not found'}
            
            # Enter birthday (implementation depends on UI format)
            # ... birthday entry logic ...
            
            if not self.automator.tap_element("Continue"):
                return {'success': False, 'error': 'Failed to continue after birthday'}
            
            delay = self.anti_detection.get_next_action_delay(self.automator.device_id)
            time.sleep(delay)
            
            return {'success': True, 'next_state': RegistrationState.PHONE_ENTRY}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_phone_entry(self) -> Dict[str, any]:
        """Handle phone number entry"""
        try:
            if not self.automator.wait_for_element("Phone", timeout=15):
                return {'success': False, 'error': 'Phone field not found'}
            
            if not self.automator.enter_text(self.profile.phone_number, "Phone"):
                return {'success': False, 'error': 'Failed to enter phone number'}
            
            if not self.automator.tap_element("Continue"):
                return {'success': False, 'error': 'Failed to continue after phone'}
            
            delay = self.anti_detection.get_next_action_delay(self.automator.device_id)
            time.sleep(delay)
            
            return {'success': True, 'next_state': RegistrationState.PHONE_VERIFICATION}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_phone_verification(self) -> Dict[str, any]:
        """Handle phone verification"""
        try:
            # Wait for verification code input
            if not self.automator.wait_for_element("Verification code", timeout=30):
                return {'success': False, 'error': 'Verification code input not found'}
            
            # Poll for SMS verification code (implementation from original)
            # This would include the Twilio SMS polling logic
            verification_code = self._poll_for_verification_code()
            
            if not verification_code:
                return {'success': False, 'error': 'Verification code not received'}
            
            if not self.automator.enter_text(verification_code, "Verification code"):
                return {'success': False, 'error': 'Failed to enter verification code'}
            
            if not self.automator.tap_element("Continue"):
                return {'success': False, 'error': 'Failed to continue after verification'}
            
            delay = self.anti_detection.get_next_action_delay(self.automator.device_id)
            time.sleep(delay)
            
            return {'success': True, 'next_state': RegistrationState.PROFILE_SETUP}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_email_verification(self) -> Dict[str, any]:
        """Handle email verification if required"""
        # Implementation would handle email verification
        return {'success': True, 'next_state': RegistrationState.PROFILE_SETUP}
    
    def _handle_profile_setup(self) -> Dict[str, any]:
        """Handle final profile setup"""
        try:
            # Skip optional profile steps or handle them
            # This would include avatar setup, friend finding, etc.
            
            # For now, assume we've reached the main screen
            if self.automator.wait_for_element("Camera", timeout=30):
                return {'success': True, 'next_state': RegistrationState.COMPLETED}
            else:
                return {'success': False, 'error': 'Failed to reach main screen'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _poll_for_verification_code(self) -> Optional[str]:
        """Poll for SMS verification code"""
        # This would implement the SMS polling logic from the original
        # Placeholder for now
        return None