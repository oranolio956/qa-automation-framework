#!/usr/bin/env python3
"""
Tinder Account Creation Pipeline
Automates full Tinder account registration with anti-detection measures
"""

import os
import sys
import time
import random
import logging
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, date
from pathlib import Path
import subprocess
import uuid

# Import automation components
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from android.emulator_manager import get_emulator_manager, EmulatorInstance
from core.anti_detection import get_anti_detection_system

# Import existing utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../utils'))
from sms_verifier import send_verification_sms, verify_sms_code
from brightdata_proxy import get_brightdata_session, verify_proxy

# UI automation imports
try:
    from appium import webdriver
    from appium.webdriver.common.appiumby import AppiumBy
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.action_chains import ActionChains
    APPIUM_AVAILABLE = True
except ImportError:
    APPIUM_AVAILABLE = False

try:
    import uiautomator2 as u2
    U2_AVAILABLE = True
except ImportError:
    U2_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AccountProfile:
    """Tinder account profile data"""
    first_name: str
    birth_date: date
    gender: str  # "man", "woman", "other"
    interested_in: str  # "men", "women", "everyone"
    phone_number: str
    email: str
    bio: str
    photos: List[str]  # File paths to photos
    location: Tuple[float, float]  # (latitude, longitude)
    distance_preference: int = 50  # km
    age_min: int = 18
    age_max: int = 50
    snapchat_username: Optional[str] = None

@dataclass
class AccountCreationResult:
    """Result of account creation attempt"""
    success: bool
    account_id: Optional[str] = None
    profile: Optional[AccountProfile] = None
    device_id: Optional[str] = None
    creation_time: Optional[datetime] = None
    error: Optional[str] = None
    verification_status: str = "pending"  # pending, verified, failed
    tinder_account_id: Optional[str] = None

class TinderAppAutomator:
    """Automates Tinder app interactions"""
    
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.driver = None
        self.u2_device = None
        self._setup_automation()
        
    def _setup_automation(self):
        """Set up automation driver"""
        if APPIUM_AVAILABLE:
            self._setup_appium()
        elif U2_AVAILABLE:
            self._setup_u2()
        else:
            raise RuntimeError("No automation framework available. Install appium-python-client or uiautomator2")
    
    def _setup_appium(self):
        """Set up Appium WebDriver"""
        desired_caps = {
            'platformName': 'Android',
            'deviceName': self.device_id,
            'automationName': 'UiAutomator2',
            'appPackage': 'com.tinder',
            'appActivity': '.activity.MainActivity',
            'noReset': False,
            'fullReset': True,
            'newCommandTimeout': 300,
            'adbExecTimeout': 60000
        }
        
        try:
            self.driver = webdriver.Remote('http://localhost:4723/wd/hub', desired_caps)
            logger.info(f"Appium driver connected for device: {self.device_id}")
        except Exception as e:
            logger.error(f"Failed to connect Appium driver: {e}")
            raise
    
    def _setup_u2(self):
        """Set up UIAutomator2 device"""
        try:
            self.u2_device = u2.connect(self.device_id)
            logger.info(f"UIAutomator2 connected for device: {self.device_id}")
        except Exception as e:
            logger.error(f"Failed to connect UIAutomator2: {e}")
            raise
    
    def install_tinder(self) -> bool:
        """Install Tinder app on device"""
        try:
            # Download Tinder APK (would need to be provided)
            apk_path = "/path/to/tinder.apk"  # This would be configured
            
            if not os.path.exists(apk_path):
                logger.error(f"Tinder APK not found: {apk_path}")
                return False
            
            # Install APK
            cmd = ["adb", "-s", self.device_id, "install", "-r", apk_path]
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            if "Success" in result.stdout:
                logger.info(f"Tinder installed successfully on {self.device_id}")
                return True
            else:
                logger.error(f"Tinder installation failed: {result.stdout}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to install Tinder: {e}")
            return False
    
    def launch_tinder(self) -> bool:
        """Launch Tinder app"""
        try:
            if self.u2_device:
                self.u2_device.app_start("com.tinder")
                time.sleep(3)
                return True
            elif self.driver:
                self.driver.activate_app("com.tinder")
                time.sleep(3)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to launch Tinder: {e}")
            return False
    
    def wait_for_element(self, locator: str, timeout: int = 30) -> bool:
        """Wait for UI element to appear"""
        try:
            if self.u2_device:
                return self.u2_device(text=locator).wait(timeout=timeout)
            elif self.driver:
                wait = WebDriverWait(self.driver, timeout)
                wait.until(EC.presence_of_element_located((AppiumBy.XPATH, f"//*[contains(@text, '{locator}')]")))
                return True
            return False
        except Exception:
            return False
    
    def tap_element(self, locator: str) -> bool:
        """Tap UI element"""
        try:
            if self.u2_device:
                if self.u2_device(text=locator).exists:
                    self.u2_device(text=locator).click()
                    return True
                return False
            elif self.driver:
                element = self.driver.find_element(AppiumBy.XPATH, f"//*[contains(@text, '{locator}')]")
                element.click()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to tap element {locator}: {e}")
            return False
    
    def enter_text(self, locator: str, text: str) -> bool:
        """Enter text in input field"""
        try:
            if self.u2_device:
                if self.u2_device(text=locator).exists:
                    self.u2_device(text=locator).clear_text()
                    self.u2_device(text=locator).send_keys(text)
                    return True
                return False
            elif self.driver:
                element = self.driver.find_element(AppiumBy.XPATH, f"//*[contains(@text, '{locator}')]")
                element.clear()
                element.send_keys(text)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to enter text in {locator}: {e}")
            return False

class TinderAccountCreator:
    """Main Tinder account creation system"""
    
    def __init__(self, aggressiveness: float = 0.3):
        self.emulator_manager = get_emulator_manager()
        self.anti_detection = get_anti_detection_system(aggressiveness)
        self.created_accounts: List[AccountCreationResult] = []
        
    def generate_random_profile(self, snapchat_username: str = None) -> AccountProfile:
        """Generate random but realistic profile data"""
        first_names_male = [
            "Alex", "Brad", "Chris", "David", "Eric", "Frank", "Greg", "Henry",
            "Ian", "Jake", "Kyle", "Luke", "Matt", "Nick", "Owen", "Paul"
        ]
        
        first_names_female = [
            "Amy", "Beth", "Chloe", "Diana", "Emma", "Faith", "Grace", "Hannah", 
            "Iris", "Jen", "Kate", "Lisa", "Maya", "Nina", "Olivia", "Paige"
        ]
        
        genders = ["man", "woman"]
        gender = random.choice(genders)
        
        if gender == "man":
            first_name = random.choice(first_names_male)
        else:
            first_name = random.choice(first_names_female)
        
        # Generate realistic age (18-35 for dating apps)
        age = random.randint(18, 35)
        birth_year = 2024 - age
        birth_date = date(birth_year, random.randint(1, 12), random.randint(1, 28))
        
        # Generate phone number (US format)
        area_codes = ["555", "216", "312", "415", "713", "202", "305", "404", "617", "206"]
        area_code = random.choice(area_codes)
        phone_number = f"+1{area_code}{random.randint(1000000, 9999999)}"
        
        # Generate email
        email_domains = ["gmail.com", "yahoo.com", "hotmail.com", "icloud.com", "outlook.com"]
        email = f"{first_name.lower()}.{random.randint(1000, 9999)}@{random.choice(email_domains)}"
        
        # Generate bio with Snapchat
        bio_templates = [
            "Love hiking and coffee ☕ {snapchat}",
            "Dog lover 🐕 Always up for adventures {snapchat}",
            "Yoga instructor and foodie 🧘‍♀️ {snapchat}",
            "Travel enthusiast ✈️ Let's explore together {snapchat}",
            "Gym rat and Netflix addict 💪 {snapchat}",
            "Artist at heart 🎨 Looking for genuine connections {snapchat}",
            "Outdoor adventures and good vibes ⛰️ {snapchat}",
            "Coffee connoisseur ☕ Swipe right if you can keep up {snapchat}"
        ]
        
        bio = random.choice(bio_templates)
        if snapchat_username:
            bio = bio.format(snapchat=f"SC: {snapchat_username}")
        else:
            bio = bio.replace(" {snapchat}", "")
        
        # Generate location (US cities)
        locations = [
            (40.7128, -74.0060),  # New York
            (34.0522, -118.2437), # Los Angeles  
            (41.8781, -87.6298),  # Chicago
            (29.7604, -95.3698),  # Houston
            (33.4484, -112.0740), # Phoenix
            (39.7392, -104.9903), # Denver
            (25.7617, -80.1918),  # Miami
            (47.6062, -122.3321), # Seattle
            (37.7749, -122.4194), # San Francisco
            (32.7767, -96.7970)   # Dallas
        ]
        location = random.choice(locations)
        
        return AccountProfile(
            first_name=first_name,
            birth_date=birth_date,
            gender=gender,
            interested_in="everyone" if random.random() < 0.3 else ("men" if gender == "woman" else "women"),
            phone_number=phone_number,
            email=email,
            bio=bio,
            photos=[],  # Would be populated with generated/downloaded photos
            location=location,
            snapchat_username=snapchat_username
        )
    
    def create_account(self, profile: AccountProfile, emulator_instance: EmulatorInstance) -> AccountCreationResult:
        """Create single Tinder account"""
        account_id = str(uuid.uuid4())
        creation_start = datetime.now()
        
        logger.info(f"Creating Tinder account: {profile.first_name} on {emulator_instance.device_id}")
        
        try:
            # Set up device fingerprint
            fingerprint = self.anti_detection.create_device_fingerprint(emulator_instance.device_id)
            
            # Initialize app automator
            automator = TinderAppAutomator(emulator_instance.device_id)
            
            # Install and launch Tinder
            if not automator.install_tinder():
                raise RuntimeError("Failed to install Tinder app")
            
            if not automator.launch_tinder():
                raise RuntimeError("Failed to launch Tinder app")
            
            # Handle onboarding flow
            success = self._complete_registration_flow(automator, profile)
            if not success:
                raise RuntimeError("Failed to complete registration flow")
            
            # Verify phone number
            verification_result = self._verify_phone_number(automator, profile.phone_number)
            if not verification_result:
                raise RuntimeError("Failed to verify phone number")
            
            # Complete profile setup
            profile_result = self._setup_profile(automator, profile)
            if not profile_result:
                raise RuntimeError("Failed to set up profile")
            
            # Create successful result
            result = AccountCreationResult(
                success=True,
                account_id=account_id,
                profile=profile,
                device_id=emulator_instance.device_id,
                creation_time=creation_start,
                verification_status="verified"
            )
            
            self.created_accounts.append(result)
            logger.info(f"Successfully created Tinder account: {account_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to create Tinder account: {e}")
            return AccountCreationResult(
                success=False,
                account_id=account_id,
                profile=profile,
                device_id=emulator_instance.device_id,
                creation_time=creation_start,
                error=str(e),
                verification_status="failed"
            )
    
    def _complete_registration_flow(self, automator: TinderAppAutomator, profile: AccountProfile) -> bool:
        """Complete Tinder registration flow"""
        try:
            # Wait for welcome screen
            if not automator.wait_for_element("Create Account", timeout=30):
                return False
            
            # Tap "Create Account"
            if not automator.tap_element("Create Account"):
                return False
            
            time.sleep(2)
            
            # Enter phone number
            if not automator.wait_for_element("Phone number", timeout=10):
                return False
            
            if not automator.enter_text("Phone number", profile.phone_number):
                return False
            
            # Continue
            if not automator.tap_element("Continue"):
                return False
            
            # Handle potential phone verification step
            time.sleep(3)
            
            return True
            
        except Exception as e:
            logger.error(f"Registration flow failed: {e}")
            return False
    
    def _verify_phone_number(self, automator: TinderAppAutomator, phone_number: str) -> bool:
        """Handle phone number verification"""
        try:
            # Send SMS verification
            sms_result = send_verification_sms(phone_number, "Tinder")
            if not sms_result['success']:
                logger.error(f"Failed to send verification SMS: {sms_result.get('error')}")
                return False
            
            logger.info(f"Verification SMS sent to {phone_number}")
            
            # Wait for verification code input field
            if not automator.wait_for_element("Verification code", timeout=60):
                logger.error("Verification code input not found")
                return False
            
            # In real implementation, would need to retrieve SMS from provider
            # For now, simulate manual verification
            logger.warning("Manual SMS verification required - implement SMS retrieval")
            
            # Simulate entering verification code
            verification_code = "123456"  # Would get from SMS
            if not automator.enter_text("Verification code", verification_code):
                return False
            
            # Continue
            if not automator.tap_element("Continue"):
                return False
            
            time.sleep(3)
            return True
            
        except Exception as e:
            logger.error(f"Phone verification failed: {e}")
            return False
    
    def _setup_profile(self, automator: TinderAppAutomator, profile: AccountProfile) -> bool:
        """Set up Tinder profile"""
        try:
            # Enter first name
            if automator.wait_for_element("First name", timeout=30):
                if not automator.enter_text("First name", profile.first_name):
                    return False
                
                if not automator.tap_element("Continue"):
                    return False
            
            # Enter birth date
            if automator.wait_for_element("Birthday", timeout=10):
                # Would implement date picker interaction
                logger.info("Setting birth date - implementation needed")
                if not automator.tap_element("Continue"):
                    return False
            
            # Select gender
            if automator.wait_for_element("Gender", timeout=10):
                if not automator.tap_element(profile.gender.title()):
                    return False
                
                if not automator.tap_element("Continue"):
                    return False
            
            # Select interested in
            if automator.wait_for_element("Show me", timeout=10):
                interested_text = profile.interested_in.title()
                if interested_text == "Everyone":
                    interested_text = "Everyone"
                elif interested_text == "Men":
                    interested_text = "Men"
                else:
                    interested_text = "Women"
                
                if not automator.tap_element(interested_text):
                    return False
                
                if not automator.tap_element("Continue"):
                    return False
            
            # Add photos (would implement photo upload)
            if automator.wait_for_element("Add Photos", timeout=10):
                logger.info("Photo upload - implementation needed")
                # Skip for now
                if not automator.tap_element("Continue"):
                    return False
            
            # Add bio
            if automator.wait_for_element("Bio", timeout=10):
                if not automator.enter_text("Bio", profile.bio):
                    return False
                
                if not automator.tap_element("Continue"):
                    return False
            
            # Complete setup
            if automator.wait_for_element("Start Swiping", timeout=10):
                if not automator.tap_element("Start Swiping"):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Profile setup failed: {e}")
            return False
    
    def create_multiple_accounts(self, count: int, snapchat_usernames: List[str] = None) -> List[AccountCreationResult]:
        """Create multiple Tinder accounts in parallel"""
        logger.info(f"Creating {count} Tinder accounts...")
        
        # Create emulator pool
        emulator_instances = self.emulator_manager.create_emulator_pool(count, headless=True)
        
        if len(emulator_instances) < count:
            logger.warning(f"Only {len(emulator_instances)} emulators available for {count} accounts")
        
        results = []
        
        for i, instance in enumerate(emulator_instances):
            try:
                # Generate profile
                snapchat_username = None
                if snapchat_usernames and i < len(snapchat_usernames):
                    snapchat_username = snapchat_usernames[i]
                
                profile = self.generate_random_profile(snapchat_username)
                
                # Create account
                result = self.create_account(profile, instance)
                results.append(result)
                
                # Delay between account creations
                if i < len(emulator_instances) - 1:
                    delay = random.uniform(30, 120)  # 30s to 2min between accounts
                    logger.info(f"Waiting {delay:.1f}s before next account creation...")
                    time.sleep(delay)
                
            except Exception as e:
                logger.error(f"Failed to create account {i+1}: {e}")
                results.append(AccountCreationResult(
                    success=False,
                    error=str(e),
                    device_id=instance.device_id
                ))
        
        # Summary
        successful = sum(1 for r in results if r.success)
        logger.info(f"Account creation complete: {successful}/{len(results)} successful")
        
        return results
    
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
_account_creator = None

def get_account_creator(aggressiveness: float = 0.3) -> TinderAccountCreator:
    """Get global account creator instance"""
    global _account_creator
    if _account_creator is None:
        _account_creator = TinderAccountCreator(aggressiveness)
    return _account_creator

if __name__ == "__main__":
    # Test account creation
    import argparse
    
    parser = argparse.ArgumentParser(description='Tinder Account Creator')
    parser.add_argument('--count', '-c', type=int, default=1, help='Number of accounts to create')
    parser.add_argument('--aggressiveness', '-a', type=float, default=0.3, help='Aggressiveness level (0.1-1.0)')
    parser.add_argument('--output', '-o', help='JSON output file for results')
    
    args = parser.parse_args()
    
    try:
        # Verify proxy setup
        verify_proxy()
        logger.info("✅ Proxy verification successful")
        
        # Create accounts
        creator = TinderAccountCreator(args.aggressiveness)
        results = creator.create_multiple_accounts(args.count)
        
        # Output results
        stats = creator.get_creation_statistics()
        print(f"✅ Account creation completed: {stats['successful_creations']}/{stats['total_attempts']} successful")
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(stats, f, indent=2, default=str)
            print(f"Results saved to {args.output}")
        
    except KeyboardInterrupt:
        logger.info("Account creation interrupted by user")
    except Exception as e:
        logger.error(f"Account creation failed: {e}")
        sys.exit(1)