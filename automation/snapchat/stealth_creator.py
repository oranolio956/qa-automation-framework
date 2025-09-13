#!/usr/bin/env python3
"""
Snapchat Stealth Account Creator
Creates hidden Snapchat accounts for embedding in Tinder bios
"""

import os
import sys
import time
import random
import logging
import json
import string
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, date, timedelta
from pathlib import Path
import subprocess
import uuid
import requests
from faker import Faker

# Import automation components
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from android.emulator_manager import EmulatorInstance
from core.anti_detection import get_anti_detection_system
from tinder.account_creator import TinderAppAutomator  # Reuse automation framework

# Import existing utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../utils'))
from sms_verifier import send_verification_sms, verify_sms_code
from brightdata_proxy import get_brightdata_session

# UI automation imports
try:
    import uiautomator2 as u2
    U2_AVAILABLE = True
except ImportError:
    U2_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SnapchatProfile:
    """Snapchat account profile data"""
    username: str
    display_name: str
    email: str
    phone_number: str
    birth_date: date
    password: str
    bio: Optional[str] = None
    profile_pic_path: Optional[str] = None
    
@dataclass
class SnapchatCreationResult:
    """Result of Snapchat account creation"""
    success: bool
    profile: Optional[SnapchatProfile] = None
    account_id: Optional[str] = None
    device_id: Optional[str] = None
    creation_time: Optional[datetime] = None
    verification_status: str = "pending"
    error: Optional[str] = None
    snapchat_score: int = 0

class SnapchatUsernameGenerator:
    """Generates realistic but unique Snapchat usernames"""
    
    def __init__(self):
        self.fake = Faker()
        
        # Common username patterns on Snapchat
        self.patterns = [
            "{first_name}{numbers}",
            "{first_name}_{last_initial}{numbers}",
            "{first_name}{last_name}{numbers}",
            "{first_initial}{last_name}{numbers}",
            "{adjective}{first_name}",
            "{first_name}_{adjective}",
            "{hobby}{first_name}",
            "{first_name}{hobby}",
            "{city}{first_name}",
            "{first_name}_{birth_year}"
        ]
        
        self.adjectives = [
            "cool", "fun", "wild", "rad", "epic", "lit", "fire", "dope",
            "fresh", "real", "true", "young", "bright", "fast", "smooth"
        ]
        
        self.hobbies = [
            "travel", "music", "art", "photo", "dance", "sport", "game",
            "surf", "skate", "bike", "run", "gym", "yoga", "chef", "style"
        ]
        
        self.cities = [
            "miami", "nyc", "la", "vegas", "chi", "atl", "sea", "den", "pdx", "nash"
        ]
    
    def generate_username(self, first_name: str, last_name: str = None, birth_year: int = None) -> str:
        """Generate realistic Snapchat username"""
        if not last_name:
            last_name = self.fake.last_name()
        if not birth_year:
            birth_year = random.randint(1995, 2005)
        
        pattern = random.choice(self.patterns)
        
        # Prepare variables
        first_name_clean = first_name.lower().replace(' ', '')
        last_name_clean = last_name.lower().replace(' ', '')
        
        variables = {
            'first_name': first_name_clean,
            'last_name': last_name_clean,
            'first_initial': first_name_clean[0],
            'last_initial': last_name_clean[0],
            'numbers': str(random.randint(10, 9999)),
            'adjective': random.choice(self.adjectives),
            'hobby': random.choice(self.hobbies),
            'city': random.choice(self.cities),
            'birth_year': str(birth_year)[-2:]  # Last 2 digits
        }
        
        # Generate username
        username = pattern.format(**variables)
        
        # Ensure username meets Snapchat requirements
        username = self._clean_username(username)
        
        # Add randomization if too short
        if len(username) < 6:
            username += str(random.randint(10, 999))
        
        return username
    
    def _clean_username(self, username: str) -> str:
        """Clean username to meet Snapchat requirements"""
        # Remove invalid characters
        cleaned = ''.join(c for c in username if c.isalnum() or c in '_.-')
        
        # Ensure starts with letter
        if cleaned and not cleaned[0].isalpha():
            cleaned = random.choice(string.ascii_lowercase) + cleaned
        
        # Limit length (Snapchat max is 15 characters)
        if len(cleaned) > 15:
            cleaned = cleaned[:15]
        
        return cleaned.lower()
    
    def generate_multiple_usernames(self, count: int, first_name: str, last_name: str = None) -> List[str]:
        """Generate multiple username options"""
        usernames = set()
        
        while len(usernames) < count:
            username = self.generate_username(first_name, last_name)
            usernames.add(username)
        
        return list(usernames)

class SnapchatAppAutomator:
    """Automates Snapchat app interactions"""
    
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.u2_device = None
        self.anti_detection = get_anti_detection_system()
        self._setup_automation()
    
    def _setup_automation(self):
        """Set up UIAutomator2 device connection"""
        if not U2_AVAILABLE:
            raise RuntimeError("UIAutomator2 not available. Install uiautomator2")
        
        try:
            self.u2_device = u2.connect(self.device_id)
            logger.info(f"UIAutomator2 connected for Snapchat on device: {self.device_id}")
        except Exception as e:
            logger.error(f"Failed to connect UIAutomator2: {e}")
            raise
    
    def install_snapchat(self) -> bool:
        """Install Snapchat app on device"""
        try:
            # Download Snapchat APK (would need to be provided)
            apk_path = "/path/to/snapchat.apk"  # Configure this path
            
            if not os.path.exists(apk_path):
                # Try to download from APK source
                logger.warning(f"Snapchat APK not found: {apk_path}")
                return False
            
            # Install APK
            cmd = ["adb", "-s", self.device_id, "install", "-r", apk_path]
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            if "Success" in result.stdout:
                logger.info(f"Snapchat installed successfully on {self.device_id}")
                return True
            else:
                logger.error(f"Snapchat installation failed: {result.stdout}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to install Snapchat: {e}")
            return False
    
    def launch_snapchat(self) -> bool:
        """Launch Snapchat app"""
        try:
            self.u2_device.app_start("com.snapchat.android")
            time.sleep(5)  # Wait for app to load
            return True
        except Exception as e:
            logger.error(f"Failed to launch Snapchat: {e}")
            return False
    
    def wait_for_element(self, text: str = None, resource_id: str = None, timeout: int = 30) -> bool:
        """Wait for UI element to appear"""
        try:
            if text:
                return self.u2_device(text=text).wait(timeout=timeout)
            elif resource_id:
                return self.u2_device(resourceId=resource_id).wait(timeout=timeout)
            return False
        except Exception:
            return False
    
    def tap_element(self, text: str = None, resource_id: str = None) -> bool:
        """Tap UI element"""
        try:
            if text and self.u2_device(text=text).exists:
                self.u2_device(text=text).click()
                return True
            elif resource_id and self.u2_device(resourceId=resource_id).exists:
                self.u2_device(resourceId=resource_id).click()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to tap element: {e}")
            return False
    
    def enter_text(self, text: str, field_text: str = None, resource_id: str = None) -> bool:
        """Enter text in input field"""
        try:
            if field_text and self.u2_device(text=field_text).exists:
                self.u2_device(text=field_text).clear_text()
                self.u2_device(text=field_text).send_keys(text)
                return True
            elif resource_id and self.u2_device(resourceId=resource_id).exists:
                self.u2_device(resourceId=resource_id).clear_text()
                self.u2_device(resourceId=resource_id).send_keys(text)
                return True
            
            # Fallback: find any input field and enter text
            if self.u2_device(className="android.widget.EditText").exists:
                self.u2_device(className="android.widget.EditText").clear_text()
                self.u2_device(className="android.widget.EditText").send_keys(text)
                return True
            
            return False
        except Exception as e:
            logger.error(f"Failed to enter text: {e}")
            return False

class SnapchatStealthCreator:
    """Main Snapchat stealth account creation system"""
    
    def __init__(self):
        self.username_generator = SnapchatUsernameGenerator()
        self.anti_detection = get_anti_detection_system()
        self.created_accounts: List[SnapchatCreationResult] = []
        
    def generate_stealth_profile(self, first_name: str = None) -> SnapchatProfile:
        """Generate stealth Snapchat profile"""
        fake = Faker()
        
        if not first_name:
            first_name = fake.first_name()
        
        last_name = fake.last_name()
        
        # Generate username variations and pick one
        usernames = self.username_generator.generate_multiple_usernames(5, first_name, last_name)
        username = random.choice(usernames)
        
        # Generate realistic display name
        display_names = [
            first_name,
            f"{first_name} {last_name[0]}",  # "John D"
            f"{first_name} {last_name}",
            f"{first_name[0]} {last_name}",  # "J Smith"
        ]
        display_name = random.choice(display_names)
        
        # Generate email
        email_domains = ["gmail.com", "yahoo.com", "hotmail.com", "icloud.com"]
        email_username = f"{first_name.lower()}.{last_name.lower()}.{random.randint(100, 999)}"
        email = f"{email_username}@{random.choice(email_domains)}"
        
        # Generate phone number (US format)
        area_codes = ["555", "216", "312", "415", "713", "202", "305", "404"]
        phone_number = f"+1{random.choice(area_codes)}{random.randint(1000000, 9999999)}"
        
        # Generate birth date (18-25 years old for dating context)
        age = random.randint(18, 25)
        birth_year = datetime.now().year - age
        birth_date = fake.date_between(
            start_date=date(birth_year, 1, 1),
            end_date=date(birth_year, 12, 31)
        )
        
        # Generate secure password
        password = self._generate_secure_password()
        
        return SnapchatProfile(
            username=username,
            display_name=display_name,
            email=email,
            phone_number=phone_number,
            birth_date=birth_date,
            password=password
        )
    
    def _generate_secure_password(self) -> str:
        """Generate secure password for Snapchat"""
        # Snapchat requires 8+ characters with letters and numbers
        words = ["snap", "photo", "fun", "life", "cool", "wild", "free"]
        word = random.choice(words)
        numbers = str(random.randint(100, 999))
        symbols = random.choice(["!", "@", "#", "$"])
        
        password = word.capitalize() + numbers + symbols
        return password
    
    def create_account(self, profile: SnapchatProfile, device_id: str) -> SnapchatCreationResult:
        """Create single Snapchat account"""
        account_id = str(uuid.uuid4())
        creation_start = datetime.now()
        
        logger.info(f"Creating Snapchat account: {profile.username} on {device_id}")
        
        try:
            # Set up device fingerprint for consistency
            fingerprint = self.anti_detection.create_device_fingerprint(device_id)
            
            # Initialize app automator
            automator = SnapchatAppAutomator(device_id)
            
            # Install and launch Snapchat
            if not automator.install_snapchat():
                raise RuntimeError("Failed to install Snapchat app")
            
            if not automator.launch_snapchat():
                raise RuntimeError("Failed to launch Snapchat app")
            
            # Complete registration flow
            if not self._complete_registration_flow(automator, profile):
                raise RuntimeError("Failed to complete registration flow")
            
            # Verify phone number
            if not self._verify_phone_number(automator, profile.phone_number):
                raise RuntimeError("Failed to verify phone number")
            
            # Complete profile setup
            if not self._setup_profile(automator, profile):
                raise RuntimeError("Failed to set up profile")
            
            # Perform initial warming activities
            self._perform_warming_activities(automator)
            
            # Create successful result
            result = SnapchatCreationResult(
                success=True,
                profile=profile,
                account_id=account_id,
                device_id=device_id,
                creation_time=creation_start,
                verification_status="verified",
                snapchat_score=0  # New accounts start at 0
            )
            
            self.created_accounts.append(result)
            logger.info(f"Successfully created Snapchat account: {profile.username}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to create Snapchat account: {e}")
            return SnapchatCreationResult(
                success=False,
                profile=profile,
                account_id=account_id,
                device_id=device_id,
                creation_time=creation_start,
                error=str(e),
                verification_status="failed"
            )
    
    def _complete_registration_flow(self, automator: SnapchatAppAutomator, profile: SnapchatProfile) -> bool:
        """Complete Snapchat registration flow"""
        try:
            # Wait for welcome screen
            if not automator.wait_for_element("Sign Up", timeout=30):
                logger.error("Sign Up button not found")
                return False
            
            # Tap Sign Up
            if not automator.tap_element("Sign Up"):
                return False
            
            time.sleep(2)
            
            # Enter first and last name
            if automator.wait_for_element("First name", timeout=10):
                if not automator.enter_text(profile.display_name.split()[0], "First name"):
                    return False
                
                if len(profile.display_name.split()) > 1:
                    last_name = profile.display_name.split()[-1]
                    if not automator.enter_text(last_name, "Last name"):
                        return False
                
                # Continue
                if not automator.tap_element("Continue"):
                    return False
            
            time.sleep(2)
            
            # Enter username
            if automator.wait_for_element("Username", timeout=10):
                if not automator.enter_text(profile.username, "Username"):
                    return False
                
                # Check availability (might take a moment)
                time.sleep(3)
                
                # Continue
                if not automator.tap_element("Continue"):
                    return False
            
            time.sleep(2)
            
            # Enter password
            if automator.wait_for_element("Password", timeout=10):
                if not automator.enter_text(profile.password, "Password"):
                    return False
                
                # Continue
                if not automator.tap_element("Continue"):
                    return False
            
            time.sleep(2)
            
            # Enter phone number
            if automator.wait_for_element("Mobile Number", timeout=10):
                if not automator.enter_text(profile.phone_number, "Mobile Number"):
                    return False
                
                # Continue
                if not automator.tap_element("Continue"):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Registration flow failed: {e}")
            return False
    
    def _verify_phone_number(self, automator: SnapchatAppAutomator, phone_number: str) -> bool:
        """Handle phone number verification"""
        try:
            # Send SMS verification
            sms_result = send_verification_sms(phone_number, "Snapchat")
            if not sms_result['success']:
                logger.error(f"Failed to send verification SMS: {sms_result.get('error')}")
                return False
            
            logger.info(f"Verification SMS sent to {phone_number}")
            
            # Wait for verification code input
            if not automator.wait_for_element("Verification code", timeout=60):
                logger.error("Verification code input not found")
                return False
            
            # In real implementation, would retrieve SMS code
            # For now, simulate verification
            logger.warning("Manual SMS verification required - implement SMS retrieval")
            
            # Simulate entering verification code
            verification_code = "123456"  # Would get from SMS service
            if not automator.enter_text(verification_code, "Verification code"):
                return False
            
            # Continue
            if not automator.tap_element("Continue"):
                return False
            
            time.sleep(3)
            return True
            
        except Exception as e:
            logger.error(f"Phone verification failed: {e}")
            return False
    
    def _setup_profile(self, automator: SnapchatAppAutomator, profile: SnapchatProfile) -> bool:
        """Set up Snapchat profile"""
        try:
            # Set birth date
            if automator.wait_for_element("Birthday", timeout=30):
                # Would implement date picker interaction
                logger.info("Setting birthday - date picker interaction needed")
                if not automator.tap_element("Continue"):
                    return False
            
            # Add profile picture (optional)
            if automator.wait_for_element("Add Profile Picture", timeout=10):
                # Skip for now - can add later
                if automator.tap_element("Skip"):
                    pass  # Skipped successfully
                elif automator.tap_element("Continue"):
                    pass  # Continued without photo
            
            # Privacy settings
            if automator.wait_for_element("Privacy", timeout=10):
                # Set to private/friends only for stealth
                if automator.tap_element("Friends Only"):
                    pass
                
                if not automator.tap_element("Continue"):
                    return False
            
            # Complete setup
            if automator.wait_for_element("Get Started", timeout=10):
                if not automator.tap_element("Get Started"):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Profile setup failed: {e}")
            return False
    
    def _perform_warming_activities(self, automator: SnapchatAppAutomator):
        """Perform initial warming activities for new account"""
        try:
            logger.info("Performing warming activities...")
            
            # Take a snap (without sending)
            if automator.u2_device:
                # Tap camera button (center of screen)
                automator.u2_device.click(540, 960)
                time.sleep(2)
                
                # Take photo
                automator.u2_device.click(540, 1700)  # Camera shutter button
                time.sleep(2)
                
                # Discard it
                if automator.tap_element("Discard"):
                    pass
                elif automator.u2_device.press("back"):
                    pass
            
            # Check Discover section briefly
            if automator.tap_element("Discover"):
                time.sleep(random.uniform(5, 10))
                automator.u2_device.press("back")
            
            # Check Chat section
            if automator.tap_element("Chat"):
                time.sleep(random.uniform(3, 7))
                automator.u2_device.press("back")
            
            # Check profile/settings
            if automator.u2_device:
                # Swipe down from top to access profile
                automator.u2_device.swipe(540, 200, 540, 800, duration=0.5)
                time.sleep(random.uniform(2, 5))
                
                # Go back to camera
                automator.u2_device.swipe(540, 800, 540, 200, duration=0.5)
            
            logger.info("Warming activities completed")
            
        except Exception as e:
            logger.error(f"Warming activities failed: {e}")
    
    def create_multiple_accounts(self, count: int, device_ids: List[str]) -> List[SnapchatCreationResult]:
        """Create multiple Snapchat accounts"""
        logger.info(f"Creating {count} Snapchat accounts...")
        
        results = []
        
        for i in range(min(count, len(device_ids))):
            try:
                device_id = device_ids[i]
                
                # Generate profile
                profile = self.generate_stealth_profile()
                
                # Create account
                result = self.create_account(profile, device_id)
                results.append(result)
                
                # Delay between account creations
                if i < count - 1:
                    delay = random.uniform(60, 180)  # 1-3 minutes between accounts
                    logger.info(f"Waiting {delay:.1f}s before next account creation...")
                    time.sleep(delay)
                
            except Exception as e:
                logger.error(f"Failed to create Snapchat account {i+1}: {e}")
                results.append(SnapchatCreationResult(
                    success=False,
                    error=str(e)
                ))
        
        # Summary
        successful = sum(1 for r in results if r.success)
        logger.info(f"Snapchat account creation complete: {successful}/{len(results)} successful")
        
        return results
    
    def get_usernames_for_tinder(self, count: int) -> List[str]:
        """Get Snapchat usernames for use in Tinder bios"""
        successful_accounts = [acc for acc in self.created_accounts if acc.success and acc.profile]
        return [acc.profile.username for acc in successful_accounts[:count]]
    
    def get_creation_statistics(self) -> Dict[str, any]:
        """Get account creation statistics"""
        total = len(self.created_accounts)
        successful = sum(1 for acc in self.created_accounts if acc.success)
        verified = sum(1 for acc in self.created_accounts if acc.verification_status == "verified")
        
        return {
            'total_attempts': total,
            'successful_creations': successful,
            'verified_accounts': verified,
            'success_rate': successful / total if total > 0 else 0,
            'verification_rate': verified / total if total > 0 else 0,
            'created_accounts': [asdict(acc) for acc in self.created_accounts]
        }

# Global instance
_snapchat_creator = None

def get_snapchat_creator() -> SnapchatStealthCreator:
    """Get global Snapchat creator instance"""
    global _snapchat_creator
    if _snapchat_creator is None:
        _snapchat_creator = SnapchatStealthCreator()
    return _snapchat_creator

if __name__ == "__main__":
    # Test Snapchat creation
    import argparse
    
    parser = argparse.ArgumentParser(description='Snapchat Stealth Account Creator')
    parser.add_argument('--count', '-c', type=int, default=1, help='Number of accounts to create')
    parser.add_argument('--output', '-o', help='JSON output file for results')
    
    args = parser.parse_args()
    
    try:
        # Test username generation
        generator = SnapchatUsernameGenerator()
        usernames = generator.generate_multiple_usernames(10, "John", "Smith")
        print("Sample usernames:", usernames[:5])
        
        # Test profile generation
        creator = SnapchatStealthCreator()
        for i in range(3):
            profile = creator.generate_stealth_profile()
            print(f"Profile {i+1}: {profile.username} - {profile.display_name}")
        
        # Output results if requested
        if args.output:
            stats = creator.get_creation_statistics()
            with open(args.output, 'w') as f:
                json.dump(stats, f, indent=2, default=str)
            print(f"Results saved to {args.output}")
        
    except KeyboardInterrupt:
        logger.info("Snapchat creation interrupted by user")
    except Exception as e:
        logger.error(f"Snapchat creation failed: {e}")
        sys.exit(1)