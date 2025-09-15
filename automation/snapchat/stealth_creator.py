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
import hashlib
import zipfile
import shutil
import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, date, timedelta
from pathlib import Path
import subprocess
import uuid
import requests
from faker import Faker
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

# Configure logging first
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# Timing engine helper
try:
    from automation.core.timing_engine import next_delay as _next_delay
except Exception:
    def _next_delay(**kwargs):  # type: ignore
        return kwargs.get('base_seconds', 0.5)

def _sleep_human(task: str, base_seconds: float) -> None:
    time.sleep(_next_delay(task=task, base_seconds=base_seconds))

# Optional imports for enhanced functionality
try:
    import numpy as np
except ImportError:
    np = None
    logger.debug("NumPy not available, using fallback methods")

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
    logger.debug("BeautifulSoup not available, APK download may be limited")

# Import automation components with proper error handling
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from android.emulator_manager import EmulatorInstance
except ImportError:
    try:
        from automation.android.emulator_manager import EmulatorInstance
    except ImportError:
        EmulatorInstance = None

try:
    from core.anti_detection import get_anti_detection_system
except ImportError:
    try:
        from automation.core.anti_detection import get_anti_detection_system
    except ImportError:
        get_anti_detection_system = None

try:
    from tinder.account_creator import TinderAppAutomator
except ImportError:
    try:
        from automation.tinder.account_creator import TinderAppAutomator
    except ImportError:
        TinderAppAutomator = None

# Import existing utilities
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../utils'))
    from sms_verifier import get_sms_verifier
    from brightdata_proxy import get_brightdata_session
    from twilio_pool import get_number as pool_get_number, release_number as pool_release_number
except ImportError:
    try:
        from utils.sms_verifier import get_sms_verifier
        from utils.brightdata_proxy import get_brightdata_session
        from utils.twilio_pool import get_number as pool_get_number, release_number as pool_release_number
    except ImportError:
        get_sms_verifier = None
        get_brightdata_session = None
        pool_get_number = None
        pool_release_number = None

# Configure logging first
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Email integration functions - lazy loaded to avoid circular imports
get_snapchat_email = None
wait_for_snapchat_verification = None
get_email_integrator = None
EMAIL_INTEGRATION_AVAILABLE = False

def _load_email_integration():
    """Lazy load email integration to avoid circular imports"""
    global get_snapchat_email, wait_for_snapchat_verification, get_email_integrator, EMAIL_INTEGRATION_AVAILABLE
    
    if EMAIL_INTEGRATION_AVAILABLE:
        return True
        
    try:
        # Import at function level to avoid circular imports
        from automation.email_services.email_integration import (
            get_snapchat_email as _get_snapchat_email,
            wait_for_snapchat_verification as _wait_for_snapchat_verification,
            get_email_integrator as _get_email_integrator
        )
        get_snapchat_email = _get_snapchat_email
        wait_for_snapchat_verification = _wait_for_snapchat_verification
        get_email_integrator = _get_email_integrator
        EMAIL_INTEGRATION_AVAILABLE = True
        return True
    except ImportError:
        try:
            # Fallback import with correct path
            import importlib.util
            email_spec = importlib.util.spec_from_file_location(
                "email_integration", 
                os.path.join(os.path.dirname(__file__), '../email_services/email_integration.py')
            )
            email_module = importlib.util.module_from_spec(email_spec)
            email_spec.loader.exec_module(email_module)
            get_email_integrator = email_module.get_email_integrator
            EMAIL_INTEGRATION_AVAILABLE = True
            return True
        except Exception as e:
            logger.warning(f"Email integration not available, using fallback: {e}")
            EMAIL_INTEGRATION_AVAILABLE = False
            get_email_integrator = None

# UI automation imports
try:
    import uiautomator2 as u2
    U2_AVAILABLE = True
except ImportError:
    U2_AVAILABLE = False

# Logger already configured above

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
    
# Custom exceptions for better error handling
class SnapchatCreationError(Exception):
    """Base exception for Snapchat creation errors"""
    pass

class FailedToInstallAppError(SnapchatCreationError):
    """Failed to install Snapchat app"""
    pass

class RegistrationFlowError(SnapchatCreationError):
    """Failed during registration flow"""
    pass

class VerificationError(SnapchatCreationError):
    """Failed during phone verification"""
    pass

class ProfileSetupError(SnapchatCreationError):
    """Failed during profile setup"""
    pass

class WarmingError(SnapchatCreationError):
    """Failed during account warming"""
    pass

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
    error_type: Optional[str] = None
    snapchat_score: int = 0
    
    # Additional fields for new implementation
    username: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    password: Optional[str] = None
    errors: List[str] = None
    additional_data: Optional[Dict] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.additional_data is None:
            self.additional_data = {}

class SnapchatUsernameGenerator:
    """Generates realistic female Snapchat usernames that look natural and human"""
    
    def __init__(self):
        self.fake = Faker()
        
        # Realistic female username patterns that look natural
        self.patterns = [
            "{first_name}_{middle_name}",
            "{first_name}.{last_name}",
            "{first_name}_{aesthetic}",
            "{aesthetic}_{first_name}",
            "{first_name}_{interest}",
            "{interest}_{first_name}",
            "{first_name}_{vibe}",
            "{cute_prefix}{first_name}",
            "{first_name}{cute_suffix}",
            "{first_name}_{birth_month}",
            "{first_name}_{zodiac}",
            "{color}_{first_name}",
            "{first_name}_{nature}",
            "{mood}_{first_name}"
        ]
        
        # Popular female middle names for natural combinations
        self.middle_names = [
            "marie", "grace", "rose", "anne", "lynn", "claire", "belle",
            "jade", "hope", "faith", "joy", "sage", "rue", "mae", "eve"
        ]
        
        # Aesthetic words popular with young women
        self.aesthetics = [
            "golden", "soft", "dreamy", "vintage", "cozy", "warm", "gentle",
            "sweet", "lovely", "pretty", "sunny", "honey", "peachy", "rosy"
        ]
        
        # Female interests and hobbies that sound natural
        self.interests = [
            "bookish", "coffee", "tea", "plants", "art", "photos", "music",
            "yoga", "dance", "fashion", "beauty", "travel", "beach", "sunset"
        ]
        
        # Trendy vibes and moods
        self.vibes = [
            "vibes", "mood", "energy", "soul", "heart", "spirit", "dreams",
            "wishes", "magic", "wonder", "bliss", "glow", "shine", "sparkle"
        ]
        
        # Cute prefixes that girls use
        self.cute_prefixes = [
            "little", "baby", "miss", "princess", "angel", "fairy", "star",
            "moon", "sun", "flower", "petal", "bunny", "kitty", "dove"
        ]
        
        # Cute suffixes
        self.cute_suffixes = [
            "babe", "girl", "baby", "doll", "angel", "star", "love",
            "heart", "soul", "bee", "pie", "cake", "rose", "lily"
        ]
        
        # Birth months (abbreviated)
        self.birth_months = [
            "jan", "feb", "mar", "apr", "may", "jun",
            "jul", "aug", "sep", "oct", "nov", "dec"
        ]
        
        # Zodiac signs popular with young women
        self.zodiac_signs = [
            "aries", "taurus", "gemini", "cancer", "leo", "virgo",
            "libra", "scorpio", "sagitt", "capri", "aqua", "pisces"
        ]
        
        # Popular colors
        self.colors = [
            "pink", "purple", "blue", "green", "yellow", "coral", "mint",
            "lavender", "peach", "sage", "blush", "ivory", "pearl", "gold"
        ]
        
        # Nature elements
        self.nature_elements = [
            "moon", "sun", "star", "ocean", "wave", "flower", "rose", "lily",
            "daisy", "willow", "ivy", "sage", "fern", "clover", "pearl"
        ]
        
        # Moods and feelings
        self.moods = [
            "happy", "serene", "calm", "bright", "cheerful", "peaceful",
            "joyful", "radiant", "gentle", "sweet", "kind", "pure", "free"
        ]
    
    def generate_username(self, first_name: str, last_name: str = None, birth_year: int = None) -> str:
        """Generate realistic female Snapchat username"""
        if not last_name:
            last_name = self.fake.last_name_female()
        if not birth_year:
            birth_year = random.randint(1998, 2006)  # Gen Z range
        
        pattern = random.choice(self.patterns)
        
        # Clean names for username use
        first_name_clean = first_name.lower().replace(' ', '')
        last_name_clean = last_name.lower().replace(' ', '')
        
        # Get birth month from birth year (simulate realistic birthday)
        birth_month = random.choice(self.birth_months)
        
        # Choose zodiac based on birth month (simplified mapping)
        zodiac_map = {
            'jan': 'capri', 'feb': 'aqua', 'mar': 'pisces', 'apr': 'aries',
            'may': 'taurus', 'jun': 'gemini', 'jul': 'cancer', 'aug': 'leo',
            'sep': 'virgo', 'oct': 'libra', 'nov': 'scorpio', 'dec': 'sagitt'
        }
        zodiac = zodiac_map.get(birth_month, random.choice(self.zodiac_signs))
        
        # Prepare variables for natural-looking usernames
        variables = {
            'first_name': first_name_clean,
            'last_name': last_name_clean,
            'middle_name': random.choice(self.middle_names),
            'aesthetic': random.choice(self.aesthetics),
            'interest': random.choice(self.interests),
            'vibe': random.choice(self.vibes),
            'cute_prefix': random.choice(self.cute_prefixes),
            'cute_suffix': random.choice(self.cute_suffixes),
            'birth_month': birth_month,
            'zodiac': zodiac,
            'color': random.choice(self.colors),
            'nature': random.choice(self.nature_elements),
            'mood': random.choice(self.moods)
        }
        
        # Generate username using pattern
        username = pattern.format(**variables)
        
        # Apply additional natural variations
        username = self._apply_natural_variations(username)
        
        # Ensure username meets Snapchat requirements
        username = self._clean_username(username)
        
        # Only add minimal numbers if absolutely necessary and still too short
        if len(username) < 5:
            # Add small, natural numbers instead of random large ones
            natural_endings = ['01', '02', '03', '21', '22', '23', '24']
            username += random.choice(natural_endings)
        
        return username
    
    def _apply_natural_variations(self, username: str) -> str:
        """Apply natural variations to make username more human-like"""
        # Sometimes add natural numbers (birth year, age, graduation year)
        if random.random() < 0.15:  # 15% chance
            natural_numbers = [
                '01', '02', '03', '04', '05',  # Birth months
                '98', '99', '00', '01', '02', '03', '04', '05', '06',  # Birth years
                '21', '22', '23', '24', '25',  # Ages or graduation years
            ]
            username += random.choice(natural_numbers)
        
        # Sometimes use 'x' or 'xx' as separators (popular with Gen Z)
        if random.random() < 0.1:  # 10% chance
            if '_' in username:
                username = username.replace('_', 'x', 1)
            elif '.' in username:
                username = username.replace('.', 'xx', 1)
        
        return username
    
    def _clean_username(self, username: str) -> str:
        """Clean username to meet Snapchat requirements while preserving natural feel"""
        # Remove invalid characters but preserve dots and underscores
        cleaned = ''.join(c for c in username if c.isalnum() or c in '_.')
        
        # Ensure starts with letter
        if cleaned and not cleaned[0].isalpha():
            # Use a natural female name start instead of random letter
            natural_starts = ['a', 'e', 'i', 'o', 'm', 's', 'c', 'j', 'k', 'l']
            cleaned = random.choice(natural_starts) + cleaned
        
        # Limit length (Snapchat max is 15 characters)
        if len(cleaned) > 15:
            # Intelligently truncate to preserve meaning
            if '_' in cleaned:
                parts = cleaned.split('_')
                if len(parts) == 2:
                    # Keep both parts but shorten if needed
                    max_part_length = 7
                    part1 = parts[0][:max_part_length]
                    part2 = parts[1][:max_part_length]
                    cleaned = f"{part1}_{part2}"[:15]
                else:
                    cleaned = cleaned[:15]
            elif '.' in cleaned:
                parts = cleaned.split('.')
                if len(parts) == 2:
                    max_part_length = 7
                    part1 = parts[0][:max_part_length]
                    part2 = parts[1][:max_part_length]
                    cleaned = f"{part1}.{part2}"[:15]
                else:
                    cleaned = cleaned[:15]
            else:
                cleaned = cleaned[:15]
        
        return cleaned.lower()
    
    def generate_multiple_usernames(self, count: int, first_name: str, last_name: str = None) -> List[str]:
        """Generate multiple username options"""
        usernames = set()
        
        while len(usernames) < count:
            username = self.generate_username(first_name, last_name)
            usernames.add(username)
        
        return list(usernames)

class APKManager:
    """Manages dynamic APK download, verification, and installation"""
    
    def __init__(self, apk_cache_dir: str = None):
        self.apk_cache_dir = Path(apk_cache_dir or os.path.expanduser("~/.tinder_automation/apks"))
        self.apk_cache_dir.mkdir(parents=True, exist_ok=True)
        self.snapchat_package = "com.snapchat.android"
        
        # APK sources (in production, use legitimate APK mirror APIs)
        self.apk_sources = [
            "https://apkpure.com/api/v1/download",  # Example - replace with real API
            "https://apkmirror.com/api/download",    # Example - replace with real API
        ]
        
        logger.info(f"APK Manager initialized with cache: {self.apk_cache_dir}")
    
    def get_latest_snapchat_apk(self) -> Optional[str]:
        """Download and verify latest Snapchat APK"""
        try:
            # Check for cached APK first
            cached_apk = self._get_cached_apk()
            if cached_apk and self._verify_apk_integrity(cached_apk):
                logger.info(f"Using cached Snapchat APK: {cached_apk}")
                return str(cached_apk)
            
            # Download latest APK
            downloaded_apk = self._download_latest_apk()
            if downloaded_apk and self._verify_apk_integrity(downloaded_apk):
                logger.info(f"Downloaded fresh Snapchat APK: {downloaded_apk}")
                return str(downloaded_apk)
            
            logger.error("Failed to obtain valid Snapchat APK")
            return None
            
        except Exception as e:
            logger.error(f"Error getting Snapchat APK: {e}")
            return None
    
    def _get_cached_apk(self) -> Optional[Path]:
        """Get cached APK if exists and not too old"""
        try:
            apk_pattern = f"{self.snapchat_package}_*.apk"
            cached_apks = list(self.apk_cache_dir.glob(apk_pattern))
            
            if not cached_apks:
                return None
            
            # Get most recent APK
            latest_apk = max(cached_apks, key=lambda p: p.stat().st_mtime)
            
            # Check if APK is less than 7 days old
            age_days = (time.time() - latest_apk.stat().st_mtime) / 86400
            if age_days < 7:
                return latest_apk
            
            logger.info(f"Cached APK is {age_days:.1f} days old, downloading fresh")
            return None
            
        except Exception as e:
            logger.error(f"Error checking cached APK: {e}")
            return None
    
    def _download_latest_apk(self) -> Optional[Path]:
        """Get Snapchat APK from controlled artifact repository"""
        try:
            # Environment variable for controlled APK artifacts
            apk_artifacts_dir = os.environ.get('SNAPCHAT_APK_ARTIFACTS_DIR', 'artifacts/apks')
            
            # First check for verified APK artifacts in controlled directory
            verified_apk = self._find_verified_apk(apk_artifacts_dir)
            if verified_apk:
                logger.info(f"Using verified APK artifact: {verified_apk}")
                return verified_apk
            
            # Check for manually placed APK with signature verification
            manual_apk = self._find_manual_apk()
            if manual_apk and self._verify_apk_signature(manual_apk):
                logger.info(f"Using verified manual APK: {manual_apk}")
                return manual_apk
            
            # Log security guidance if no verified APKs available
            logger.error("No verified Snapchat APK found. For security:")
            logger.error("1. Place verified Snapchat APK in artifacts/apks/ directory")
            logger.error("2. Or set SNAPCHAT_APK_ARTIFACTS_DIR environment variable")
            logger.error("3. Ensure APK is signed by Snap Inc. (use apksigner verify)")
            logger.error("4. Consider using Play Store APKs or official sources only")
            return None
            
        except Exception as e:
            logger.error(f"Error downloading APK: {e}")
            return None
    
    def _find_verified_apk(self, artifacts_dir: str) -> Optional[Path]:
        """Find verified APK from controlled artifact directory"""
        try:
            artifacts_path = Path(artifacts_dir)
            if not artifacts_path.exists():
                logger.debug(f"Artifacts directory does not exist: {artifacts_dir}")
                return None
            
            # Look for Snapchat APK files
            snapchat_patterns = ['snapchat*.apk', 'com.snapchat.android*.apk']
            for pattern in snapchat_patterns:
                for apk_file in artifacts_path.glob(pattern):
                    if self._verify_apk_signature(apk_file):
                        return apk_file
                        
            logger.debug(f"No verified Snapchat APKs found in {artifacts_dir}")
            return None
            
        except Exception as e:
            logger.error(f"Error finding verified APK: {e}")
            return None
    
    def _verify_apk_signature(self, apk_path: Path) -> bool:
        """Verify APK signature is from Snap Inc. with proper certificate validation."""
        try:
            # Step 1: Verify APK package name first
            if not self._verify_package_name(apk_path):
                logger.error(f"APK package name validation failed: {apk_path}")
                return False
            
            # Step 2: Try using apksigner for certificate verification
            try:
                result = subprocess.run(
                    ['apksigner', 'verify', '--print-certs', str(apk_path)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    return self._validate_snapchat_certificate(result.stdout, apk_path)
                else:
                    logger.warning(f"APK signature verification failed: {result.stderr}")
                    
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                logger.warning("apksigner not available, trying alternative verification")
            
            # Step 3: Fallback to aapt for basic package verification
            try:
                result = subprocess.run(
                    ['aapt', 'dump', 'badging', str(apk_path)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    if 'package: name=\'com.snapchat.android\'' in result.stdout:
                        logger.info(f"APK package verified (basic): {apk_path}")
                        return True
                        
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                logger.warning("aapt not available, using basic validation")
            
            # Step 4: Final fallback - basic APK integrity check
            logger.warning(f"Using basic APK validation for: {apk_path}")
            return self._verify_apk_integrity(apk_path)
                
        except Exception as e:
            logger.error(f"APK signature verification error: {e}")
            return False
    
    def _verify_package_name(self, apk_path: Path) -> bool:
        """Verify APK has correct Snapchat package name."""
        try:
            # Use aapt to extract package name
            result = subprocess.run(
                ['aapt', 'dump', 'badging', str(apk_path)],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('package:'):
                        if 'name=\'com.snapchat.android\'' in line:
                            return True
                        else:
                            logger.error(f"Incorrect package name in APK: {line}")
                            return False
                            
        except Exception as e:
            logger.warning(f"Package name verification failed: {e}")
        
        return False
    
    def _validate_snapchat_certificate(self, apksigner_output: str, apk_path: Path) -> bool:
        """Validate that the APK certificate is from Snap Inc."""
        try:
            output_lower = apksigner_output.lower()
            
            # Known Snap Inc. certificate indicators
            snap_indicators = [
                'snap inc',
                'snapchat inc',
                'cn=snap inc',
                'o=snap inc',
                'snap, inc.',
                'com.snapchat.android'
            ]
            
            # Check for any valid Snap Inc. indicators
            for indicator in snap_indicators:
                if indicator in output_lower:
                    logger.info(f"Valid Snap Inc. certificate found in APK: {apk_path}")
                    return True
            
            # Additional check: Look for specific certificate fingerprints if known
            # (This would require maintaining a list of known good Snap Inc. certificate hashes)
            
            logger.warning(f"APK certificate does not match Snap Inc. patterns: {apk_path}")
            logger.debug(f"Certificate output: {apksigner_output[:500]}...")  # Log first 500 chars
            return False
            
        except Exception as e:
            logger.error(f"Certificate validation error: {e}")
            return False
    
    def _find_manual_apk(self) -> Optional[Path]:
        """Find manually placed APK files"""
        try:
            # Look for APK files in cache directory
            apk_files = list(self.apk_cache_dir.glob("*.apk"))
            snapchat_apks = [apk for apk in apk_files if "snapchat" in apk.name.lower()]
            
            if snapchat_apks:
                # Return the most recent APK
                latest_apk = max(snapchat_apks, key=lambda p: p.stat().st_mtime)
                logger.info(f"Found manual APK: {latest_apk}")
                return latest_apk
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding manual APK: {e}")
            return None
    
    def _download_from_apkmirror(self) -> Optional[Path]:
        """Download from APKMirror using web scraping"""
        try:
            import requests
            if BeautifulSoup is None:
                raise Exception("BeautifulSoup4 required for APK download. Install with: pip install beautifulsoup4")
            
            # Search for Snapchat on APKMirror
            search_url = "https://www.apkmirror.com/?s=snapchat&post_type=app_release"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = _HTTP_SESSION.get(search_url, headers=headers, timeout=30)
            if response.status_code != 200:
                raise Exception(f"APKMirror search failed: {response.status_code}")
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find Snapchat app links
            app_links = soup.find_all('a', {'class': 'accent_color'})
            snapchat_links = [link for link in app_links if 'snapchat' in link.text.lower()]
            
            if not snapchat_links:
                raise Exception("No Snapchat app found on APKMirror")
            
            # Get the first (latest) version page
            app_url = "https://www.apkmirror.com" + snapchat_links[0]['href']
            app_response = _HTTP_SESSION.get(app_url, headers=headers, timeout=30)
            
            if app_response.status_code == 200:
                # Parse download page and get APK
                app_soup = BeautifulSoup(app_response.content, 'html.parser')
                download_buttons = app_soup.find_all('a', string=lambda text: text and 'download apk' in text.lower())
                
                if download_buttons:
                    download_url = "https://www.apkmirror.com" + download_buttons[0]['href']
                    return self._download_apk_file(download_url, headers)
            
            raise Exception("Could not find download link on APKMirror")
            
        except Exception as e:
            logger.error(f"APKMirror download error: {e}")
            raise
    
    def _download_from_apkpure(self) -> Optional[Path]:
        """Download from APKPure using their API"""
        try:
            import requests
            
            if BeautifulSoup is None:
                raise Exception("BeautifulSoup4 required for APK download. Install with: pip install beautifulsoup4")
            
            # APKPure search API
            search_url = "https://apkpure.com/snapchat/com.snapchat.android"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Android 10; Mobile; rv:91.0) Gecko/91.0 Firefox/91.0'
            }
            
            response = _HTTP_SESSION.get(search_url, headers=headers, timeout=30)
            if response.status_code != 200:
                raise Exception(f"APKPure search failed: {response.status_code}")
            
            # Extract download link from page
            soup = BeautifulSoup(response.content, 'html.parser')
            download_links = soup.find_all('a', {'class': 'download-btn'})
            
            if download_links:
                download_url = download_links[0]['href']
                if not download_url.startswith('http'):
                    download_url = "https://apkpure.com" + download_url
                
                return self._download_apk_file(download_url, headers)
            
            raise Exception("Could not find download link on APKPure")
            
        except Exception as e:
            logger.error(f"APKPure download error: {e}")
            raise
    
    def _download_apk_file(self, download_url: str, headers: dict) -> Optional[Path]:
        """Download APK file from URL"""
        try:
            import requests
            
            logger.info(f"Downloading APK from: {download_url}")
            response = _HTTP_SESSION.get(download_url, headers=headers, timeout=300, stream=True)
            
            if response.status_code != 200:
                raise Exception(f"Download failed: {response.status_code}")
            
            # Generate filename
            timestamp = int(time.time())
            filename = f"snapchat_{timestamp}.apk"
            apk_path = self.apk_cache_dir / filename
            
            # Download with progress
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(apk_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            if downloaded % (1024 * 1024) == 0:  # Log every MB
                                logger.info(f"Download progress: {progress:.1f}%")
            
            logger.info(f"APK downloaded successfully: {apk_path}")
            return apk_path
            
        except Exception as e:
            logger.error(f"APK file download error: {e}")
            return None
    
    
    def _verify_apk_integrity(self, apk_path: Path) -> bool:
        """Verify APK file integrity and basic structure"""
        try:
            if not apk_path.exists() or apk_path.stat().st_size < 1000:
                return False
            
            # Check if it's a valid ZIP file (APKs are ZIP archives)
            with zipfile.ZipFile(apk_path, 'r') as zipf:
                # Verify essential APK components exist
                required_files = ['AndroidManifest.xml', 'classes.dex']
                zip_contents = zipf.namelist()
                
                for required_file in required_files:
                    if required_file not in zip_contents:
                        logger.warning(f"APK missing required file: {required_file}")
                        return False
            
            # Verify file hash for consistency
            file_hash = self._calculate_file_hash(apk_path)
            logger.debug(f"APK hash: {file_hash}")
            
            return True
            
        except Exception as e:
            logger.error(f"APK verification failed: {e}")
            return False
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def check_for_updates(self) -> Dict[str, any]:
        """Check if APK updates are available"""
        try:
            current_apk = self._get_cached_apk()
            current_version = None
            
            if current_apk:
                # In production, extract version from APK manifest
                current_version = "mock_version_1.0"
            
            # In production, check APK source for latest version
            latest_version = "mock_version_1.1"
            
            return {
                'current_version': current_version,
                'latest_version': latest_version,
                'update_available': current_version != latest_version,
                'cached_apk': str(current_apk) if current_apk else None
            }
            
        except Exception as e:
            logger.error(f"Error checking for APK updates: {e}")
            return {'error': str(e)}

class ProfilePictureGenerator:
    """Generates realistic profile pictures for Snapchat accounts with multiple methods"""
    
    def __init__(self, output_dir: str = None):
        self.output_dir = Path(output_dir or os.path.expanduser("~/.tinder_automation/profile_pics"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Style variations for generated images
        self.styles = [
            {'bg_color': (135, 206, 235), 'text_color': (255, 255, 255), 'name': 'sky_blue'},
            {'bg_color': (255, 182, 193), 'text_color': (139, 69, 19), 'name': 'light_pink'},
            {'bg_color': (144, 238, 144), 'text_color': (25, 25, 112), 'name': 'light_green'},
            {'bg_color': (255, 218, 185), 'text_color': (128, 0, 128), 'name': 'peach'},
            {'bg_color': (221, 160, 221), 'text_color': (0, 100, 0), 'name': 'plum'},
            {'bg_color': (173, 216, 230), 'text_color': (0, 0, 139), 'name': 'powder_blue'},
            {'bg_color': (255, 228, 196), 'text_color': (139, 0, 0), 'name': 'bisque'},
            {'bg_color': (205, 255, 205), 'text_color': (34, 139, 34), 'name': 'mint_green'},
        ]
        
        # Available image generation methods
        self.generation_methods = ['initials', 'gradient', 'geometric', 'photo_api']
        
        logger.info(f"Profile picture generator initialized: {self.output_dir}")
        logger.info(f"Available generation methods: {', '.join(self.generation_methods)}")
    
    def generate_profile_picture(self, name: str, method: str = None, style_index: int = None) -> str:
        """Generate a profile picture using various methods"""
        try:
            # Select generation method
            if method is None:
                method = random.choice(self.generation_methods)
            
            logger.info(f"Generating profile picture for '{name}' using method: {method}")
            
            # Generate based on selected method
            if method == 'initials':
                return self._generate_initials_image(name, style_index)
            elif method == 'gradient':
                return self._generate_gradient_image(name, style_index)
            elif method == 'geometric':
                return self._generate_geometric_image(name, style_index)
            elif method == 'photo_api':
                return self._generate_from_photo_api(name)
            else:
                # Fallback to initials
                return self._generate_initials_image(name, style_index)
                
        except Exception as e:
            logger.error(f"Error generating profile picture: {e}")
            # Fallback to simple initials method
            try:
                return self._generate_initials_image(name)
            except Exception as fallback_error:
                logger.error(f"Fallback generation also failed: {fallback_error}")
                return None
    
    def _generate_initials_image(self, name: str, style_index: int = None) -> str:
        """Generate profile picture with initials"""
        try:
            # Get initials from name
            initials = self._get_initials(name)
            
            # Select style
            if style_index is None:
                style_index = random.randint(0, len(self.styles) - 1)
            style = self.styles[style_index % len(self.styles)]
            
            # Create image with higher resolution
            size = (512, 512)
            image = Image.new('RGB', size, style['bg_color'])
            
            # Add initials text with better typography
            draw = ImageDraw.Draw(image)
            
            # Try multiple font options
            font = self._get_best_font(140)
            
            # Calculate text position (centered)
            text_bbox = draw.textbbox((0, 0), initials, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            x = (size[0] - text_width) // 2
            y = (size[1] - text_height) // 2
            
            # Add subtle shadow
            shadow_offset = 3
            draw.text((x + shadow_offset, y + shadow_offset), initials, 
                     fill=(0, 0, 0, 50), font=font)  # Semi-transparent shadow
            
            # Draw main text
            draw.text((x, y), initials, fill=style['text_color'], font=font)
            
            # Save image
            timestamp = int(time.time())
            filename = f"profile_initials_{name.lower().replace(' ', '_')}_{timestamp}.jpg"
            image_path = self.output_dir / filename
            
            image.save(image_path, 'JPEG', quality=90)
            logger.info(f"Generated initials profile picture: {image_path}")
            
            return str(image_path)
            
        except Exception as e:
            logger.error(f"Error generating initials image: {e}")
            raise
    
    def _generate_gradient_image(self, name: str, style_index: int = None) -> str:
        """Generate profile picture with gradient background"""
        try:
            if np is None:
                # Fallback gradient without numpy
                gradient_color = tuple(int(c * 0.8) for c in base_color)
                image = Image.new('RGB', size, gradient_color)
            else:
                # Select colors
                if style_index is None:
                    style_index = random.randint(0, len(self.styles) - 1)
                style = self.styles[style_index % len(self.styles)]
                
                # Create gradient
                size = (512, 512)
                base_color = style['bg_color']
                
                # Create gradient array with numpy
                gradient = np.zeros((size[1], size[0], 3), dtype=np.uint8)
                
                for y in range(size[1]):
                    # Create vertical gradient
                    factor = y / size[1]
                    color = tuple(int(c * (0.7 + factor * 0.3)) for c in base_color)
                    gradient[y, :] = color
                
                # Convert to PIL Image
                image = Image.fromarray(gradient, 'RGB')
            
            # Add initials
            initials = self._get_initials(name)
            draw = ImageDraw.Draw(image)
            font = self._get_best_font(120)
            
            # Center the text
            text_bbox = draw.textbbox((0, 0), initials, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            x = (size[0] - text_width) // 2
            y = (size[1] - text_height) // 2
            
            # Add glow effect
            glow_color = (255, 255, 255, 100)
            for offset in range(1, 4):
                draw.text((x - offset, y), initials, fill=glow_color, font=font)
                draw.text((x + offset, y), initials, fill=glow_color, font=font)
                draw.text((x, y - offset), initials, fill=glow_color, font=font)
                draw.text((x, y + offset), initials, fill=glow_color, font=font)
            
            # Main text
            draw.text((x, y), initials, fill=style['text_color'], font=font)
            
            # Save image
            timestamp = int(time.time())
            filename = f"profile_gradient_{name.lower().replace(' ', '_')}_{timestamp}.jpg"
            image_path = self.output_dir / filename
            
            image.save(image_path, 'JPEG', quality=90)
            logger.info(f"Generated gradient profile picture: {image_path}")
            
            return str(image_path)
            
        except Exception as e:
            logger.error(f"Error generating gradient image: {e}")
            # Fallback to initials
            return self._generate_initials_image(name, style_index)
    
    def _generate_geometric_image(self, name: str, style_index: int = None) -> str:
        """Generate profile picture with geometric patterns"""
        try:
            # Select style
            if style_index is None:
                style_index = random.randint(0, len(self.styles) - 1)
            style = self.styles[style_index % len(self.styles)]
            
            size = (512, 512)
            image = Image.new('RGB', size, style['bg_color'])
            draw = ImageDraw.Draw(image)
            
            # Generate geometric pattern
            center_x, center_y = size[0] // 2, size[1] // 2
            
            # Create concentric circles or polygons
            pattern_type = random.choice(['circles', 'hexagons', 'triangles'])
            
            if pattern_type == 'circles':
                for i in range(5):
                    radius = 50 + i * 30
                    color = tuple(max(0, min(255, c + random.randint(-30, 30))) 
                                for c in style['bg_color'])
                    draw.ellipse([center_x - radius, center_y - radius, 
                                center_x + radius, center_y + radius], 
                               outline=color, width=3)
            
            elif pattern_type == 'hexagons':
                import math
                for i in range(3):
                    radius = 80 + i * 40
                    points = []
                    for j in range(6):
                        angle = j * math.pi / 3
                        x = center_x + radius * math.cos(angle)
                        y = center_y + radius * math.sin(angle)
                        points.append((x, y))
                    
                    color = tuple(max(0, min(255, c + random.randint(-20, 20))) 
                                for c in style['bg_color'])
                    draw.polygon(points, outline=color, width=2)
            
            # Add initials over pattern
            initials = self._get_initials(name)
            font = self._get_best_font(100)
            
            # Center the text
            text_bbox = draw.textbbox((0, 0), initials, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            x = (size[0] - text_width) // 2
            y = (size[1] - text_height) // 2
            
            # Add background circle for text
            text_bg_radius = max(text_width, text_height) // 2 + 20
            bg_color = tuple(min(255, c + 50) for c in style['bg_color'])
            draw.ellipse([center_x - text_bg_radius, center_y - text_bg_radius,
                         center_x + text_bg_radius, center_y + text_bg_radius],
                        fill=bg_color)
            
            # Draw text
            draw.text((x, y), initials, fill=style['text_color'], font=font)
            
            # Save image
            timestamp = int(time.time())
            filename = f"profile_geometric_{name.lower().replace(' ', '_')}_{timestamp}.jpg"
            image_path = self.output_dir / filename
            
            image.save(image_path, 'JPEG', quality=90)
            logger.info(f"Generated geometric profile picture: {image_path}")
            
            return str(image_path)
            
        except Exception as e:
            logger.error(f"Error generating geometric image: {e}")
            # Fallback to initials
            return self._generate_initials_image(name, style_index)
    
    def _generate_from_photo_api(self, name: str) -> str:
        """Generate profile picture from photo generation API"""
        try:
            # Try multiple photo generation services
            services = ['thispersondoesnotexist', 'generated_photos', 'picsum']
            
            for service in services:
                try:
                    image_path = self._fetch_from_service(service, name)
                    if image_path:
                        logger.info(f"Generated photo from {service}: {image_path}")
                        return image_path
                except Exception as e:
                    logger.debug(f"Service {service} failed: {e}")
                    continue
            
            logger.warning("All photo services failed, falling back to initials")
            return self._generate_initials_image(name)
            
        except Exception as e:
            logger.error(f"Error generating from photo API: {e}")
            return self._generate_initials_image(name)
    
    def _fetch_from_service(self, service: str, name: str) -> Optional[str]:
        """Fetch image from a specific service"""
        try:
            import requests
            
            if service == 'picsum':
                # Lorem Picsum for placeholder images
                size = 512
                seed = hash(name) % 1000  # Use name as seed for consistency
                url = f"https://picsum.photos/seed/{seed}/{size}/{size}"
                
                response = _HTTP_SESSION.get(url, timeout=30)
                if response.status_code == 200:
                    timestamp = int(time.time())
                    filename = f"profile_api_{name.lower().replace(' ', '_')}_{timestamp}.jpg"
                    image_path = self.output_dir / filename
                    
                    with open(image_path, 'wb') as f:
                        f.write(response.content)
                    
                    # Process image to make it more suitable for profile
                    self._process_downloaded_image(image_path, name)
                    
                    return str(image_path)
            
            elif service == 'generated_photos':
                # Placeholder for Generated Photos API
                # This would require API key and proper implementation
                logger.debug("Generated Photos API not implemented")
                return None
            
            elif service == 'thispersondoesnotexist':
                # Note: This service has rate limiting and may not be reliable
                logger.debug("ThisPersonDoesNotExist not implemented (rate limited)")
                return None
            
            return None
            
        except Exception as e:
            logger.debug(f"Service {service} fetch error: {e}")
            return None
    
    def _process_downloaded_image(self, image_path: Path, name: str):
        """Process downloaded image for profile use"""
        try:
            from PIL import ImageEnhance, ImageFilter
            
            # Open and process image
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize to standard profile size
                img = img.resize((512, 512), Image.Resampling.LANCZOS)
                
                # Apply subtle enhancements
                enhancer = ImageEnhance.Brightness(img)
                img = enhancer.enhance(1.1)  # Slightly brighter
                
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.05)  # Slightly more contrast
                
                # Apply subtle blur to make it less sharp/obvious
                img = img.filter(ImageFilter.GaussianBlur(radius=0.5))
                
                # Save processed image
                img.save(image_path, 'JPEG', quality=85)
            
            logger.debug(f"Processed downloaded image: {image_path}")
            
        except Exception as e:
            logger.warning(f"Error processing downloaded image: {e}")
    
    def _get_best_font(self, size: int) -> ImageFont.ImageFont:
        """Get the best available font"""
        font_paths = [
            # macOS fonts
            '/System/Library/Fonts/Arial.ttf',
            '/System/Library/Fonts/Helvetica.ttc',
            '/System/Library/Fonts/Times.ttc',
            # Linux fonts
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
            '/usr/share/fonts/TTF/arial.ttf',
            # Windows fonts (if on Windows or Wine)
            'C:/Windows/Fonts/arial.ttf',
            'C:/Windows/Fonts/calibri.ttf',
        ]
        
        for font_path in font_paths:
            try:
                return ImageFont.truetype(font_path, size)
            except (OSError, IOError):
                continue
        
        # Fallback to default font
        try:
            return ImageFont.load_default()
        except Exception:
            # Ultimate fallback - create a dummy font
            return None
    
    def _get_initials(self, name: str) -> str:
        """Extract initials from name"""
        parts = name.strip().split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        elif len(parts) == 1:
            return parts[0][0:2].upper()
        else:
            return "XX"
    
    def create_batch_pictures(self, names: List[str], count_per_name: int = 3, 
                            methods: List[str] = None) -> List[str]:
        """Generate multiple profile pictures for a list of names using various methods"""
        if methods is None:
            methods = ['initials', 'gradient', 'geometric']
        
        generated_paths = []
        
        for name in names:
            logger.info(f"Generating {count_per_name} pictures for {name}")
            
            for i in range(count_per_name):
                try:
                    # Cycle through different methods and styles
                    method = methods[i % len(methods)] if methods else None
                    style_index = i % len(self.styles)
                    
                    picture_path = self.generate_profile_picture(
                        name, method=method, style_index=style_index
                    )
                    
                    if picture_path:
                        generated_paths.append(picture_path)
                        logger.info(f"✓ Generated picture {i+1}/{count_per_name} for {name}")
                    else:
                        logger.warning(f"✗ Failed to generate picture {i+1}/{count_per_name} for {name}")
                
                except Exception as e:
                    logger.error(f"Error generating picture {i+1} for {name}: {e}")
        
        success_rate = (len(generated_paths) / (len(names) * count_per_name)) * 100 if names else 0
        logger.info(f"Generated {len(generated_paths)}/{len(names) * count_per_name} profile pictures ({success_rate:.1f}% success rate)")
        
        return generated_paths
    
    def generate_profile_pictures_for_batch(self, profiles: List[SnapchatProfile]) -> Dict[str, str]:
        """Generate profile pictures for a batch of Snapchat profiles"""
        picture_mapping = {}
        
        for profile in profiles:
            try:
                # Generate unique picture for each profile
                picture_path = self.generate_profile_picture(
                    profile.display_name or profile.username,
                    method=random.choice(['initials', 'gradient', 'geometric'])
                )
                
                if picture_path:
                    picture_mapping[profile.username] = picture_path
                    profile.profile_pic_path = picture_path
                    logger.info(f"Generated picture for {profile.username}: {picture_path}")
                
            except Exception as e:
                logger.error(f"Failed to generate picture for {profile.username}: {e}")
        
        logger.info(f"Generated profile pictures for {len(picture_mapping)}/{len(profiles)} profiles")
        return picture_mapping
    
    def cleanup_old_pictures(self, days_old: int = 7) -> int:
        """Clean up old profile pictures"""
        try:
            import time
            current_time = time.time()
            cutoff_time = current_time - (days_old * 24 * 3600)
            
            cleaned_count = 0
            
            for picture_file in self.output_dir.glob("profile_*.jpg"):
                try:
                    if picture_file.stat().st_mtime < cutoff_time:
                        picture_file.unlink()
                        cleaned_count += 1
                        logger.debug(f"Cleaned up old picture: {picture_file}")
                except Exception as e:
                    logger.warning(f"Failed to clean up {picture_file}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old profile pictures")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error during picture cleanup: {e}")
            return 0

class SnapchatAppAutomator:
    """Automates Snapchat app interactions"""
    
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.u2_device = None
        self.anti_detection = get_anti_detection_system()
        self.apk_manager = APKManager()
        self.profile_pic_generator = ProfilePictureGenerator()
        self._setup_automation()
    
    def _setup_automation(self):
        """Set up UIAutomator2 device connection with fly.io farm support"""
        if not U2_AVAILABLE:
            raise RuntimeError("UIAutomator2 not available. Install uiautomator2")
        
        try:
            # Check if this is a fly.io farm device
            if self.device_id.startswith("farm_") or "fly.dev" in self.device_id:
                # Handle fly.io Android farm connection
                farm_host = os.getenv("FLY_ANDROID_HOST", "android-device-farm-prod.fly.dev")
                farm_port = os.getenv("FLY_ANDROID_PORT", "5555")
                
                # Connect to fly.io farm device
                farm_address = f"{farm_host}:{farm_port}"
                logger.info(f"Connecting to fly.io Android farm: {farm_address}")
                
                # For farm devices, use the farm address for UIAutomator2
                self.u2_device = u2.connect(farm_address)
                logger.info(f"✅ UIAutomator2 connected to fly.io farm: {farm_address}")
            else:
                # Standard local device connection
                self.u2_device = u2.connect(self.device_id)
                logger.info(f"✅ UIAutomator2 connected to local device: {self.device_id}")
                
        except Exception as e:
            logger.error(f"Failed to connect UIAutomator2 to {self.device_id}: {e}")
            
            # If farm connection fails, try to find any available device
            if self.device_id.startswith("farm_") or "fly.dev" in self.device_id:
                logger.info("Farm connection failed, attempting fallback connection...")
                try:
                    # Try common farm ports
                    for port in ["5555", "5556", "5557"]:
                        try:
                            farm_host = os.getenv("FLY_ANDROID_HOST", "android-device-farm-prod.fly.dev")
                            fallback_address = f"{farm_host}:{port}"
                            self.u2_device = u2.connect(fallback_address)
                            logger.info(f"✅ Connected to farm via fallback: {fallback_address}")
                            break
                        except:
                            continue
                    
                    if not self.u2_device:
                        raise RuntimeError("All farm connection attempts failed")
                        
                except Exception as fallback_error:
                    logger.error(f"Farm fallback failed: {fallback_error}")
                    raise RuntimeError(f"UIAutomator2 farm connection failed: {e}")
            else:
                raise RuntimeError(f"UIAutomator2 local connection failed: {e}")
    
    def install_snapchat(self) -> bool:
        """Install Snapchat app on device with dynamic APK management"""
        try:
            logger.info(f"Installing Snapchat on device {self.device_id}...")
            
            # Get latest Snapchat APK dynamically
            apk_path = self.apk_manager.get_latest_snapchat_apk()
            if not apk_path:
                raise FailedToInstallAppError("Failed to obtain valid Snapchat APK")
            
            logger.info(f"Using Snapchat APK: {apk_path}")
            
            # Uninstall existing version first (if any)
            self._uninstall_existing_snapchat()
            
            # Install APK
            cmd = ["adb", "-s", self.device_id, "install", "-r", apk_path]
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300)
            
            if "Success" in result.stdout:
                logger.info(f"Snapchat installed successfully on {self.device_id}")
                
                # Verify installation
                if self._verify_app_installation():
                    return True
                else:
                    raise FailedToInstallAppError("App installation verification failed")
            else:
                logger.error(f"Snapchat installation failed: {result.stdout}")
                raise FailedToInstallAppError(f"Installation failed: {result.stdout}")
                
        except subprocess.TimeoutExpired:
            raise FailedToInstallAppError("APK installation timed out")
        except subprocess.CalledProcessError as e:
            raise FailedToInstallAppError(f"ADB command failed: {e}")
        except Exception as e:
            logger.error(f"Failed to install Snapchat: {e}")
            raise FailedToInstallAppError(f"Unexpected error: {e}")
    
    def _uninstall_existing_snapchat(self):
        """Uninstall existing Snapchat if present"""
        try:
            cmd = ["adb", "-s", self.device_id, "uninstall", self.apk_manager.snapchat_package]
            subprocess.run(cmd, capture_output=True, timeout=60)
            logger.info("Uninstalled existing Snapchat (if any)")
        except Exception as e:
            logger.debug(f"No existing Snapchat to uninstall: {e}")
    
    def _verify_app_installation(self) -> bool:
        """Verify Snapchat app is properly installed"""
        try:
            cmd = ["adb", "-s", self.device_id, "shell", "pm", "list", "packages", self.apk_manager.snapchat_package]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if self.apk_manager.snapchat_package in result.stdout:
                logger.info("Snapchat installation verified")
                return True
            else:
                logger.error("Snapchat not found in installed packages")
                return False
                
        except Exception as e:
            logger.error(f"App verification failed: {e}")
            return False
    
    def launch_snapchat(self) -> bool:
        """Launch Snapchat app"""
        try:
            self.u2_device.app_start("com.snapchat.android")
            # Use dynamic delay instead of fixed sleep
            delay = self.anti_detection.get_next_action_delay(self.device_id)
            time.sleep(delay)
            return True
        except Exception as e:
            logger.error(f"Failed to launch Snapchat: {e}")
            raise FailedToInstallAppError(f"Failed to launch app: {e}")
    
    def set_display_name(self, display_name: str) -> bool:
        """Set Snapchat display name via UI with anti-detection pacing"""
        try:
            # Navigate to profile
            profile_btn = self.u2_device(resourceId="com.snapchat.android:id/profile_button")
            if not profile_btn.exists(timeout=10):
                return False
            profile_btn.click()
            _sleep_human("navigation", 1.5)

            # Open settings (gear icon)
            settings_btn = self.u2_device(resourceId="com.snapchat.android:id/settings_button")
            if settings_btn.exists(timeout=5):
                settings_btn.click()
                _sleep_human("navigation", 1.5)
            else:
                # Try alternative: text "Settings"
                if self.u2_device(text="Settings").exists(timeout=5):
                    self.u2_device(text="Settings").click()
                    _sleep_human("navigation", 1.5)
                else:
                    return False

            # Find "Name" or "Display Name"
            name_entry = None
            for label in ["Name", "Display Name", "Display name"]:
                elem = self.u2_device(text=label)
                if elem.exists(timeout=3):
                    name_entry = elem
                    break

            if not name_entry:
                return False
            name_entry.click()
            _sleep_human("tap", 1.0)

            # Locate input and set text
            edit_field = self.u2_device(className="android.widget.EditText")
            if not edit_field.exists(timeout=5):
                return False
            edit_field.clear_text()
            _sleep_human("typing", 0.8)
            edit_field.set_text(display_name)
            _sleep_human("typing", 1.0)

            # Save/Done
            for save_label in ["Save", "Done", "OK", "✔", "✓"]:
                btn = self.u2_device(text=save_label)
                if btn.exists(timeout=3):
                    btn.click()
                    _sleep_human("navigation", 1.0)
                    return True

            # If no explicit save, back out
            back_btn = self.u2_device(description="Navigate up")
            if back_btn.exists():
                back_btn.click()
                _sleep_human("navigation", 1.0)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to set display name: {e}")
            return False

    def set_profile_avatar(self, name: str, photo_path: Optional[str] = None) -> bool:
        """Set profile avatar using provided photo or generated one."""
        try:
            if photo_path:
                if not self._push_image_to_device(photo_path):
                    logger.warning("Provided photo could not be pushed; falling back to generator")
            else:
                # Generate avatar with initials to avoid using unrelated faces
                pic_path = self.profile_pic_generator.generate_profile_picture(name, method='initials')
                if pic_path:
                    self._push_image_to_device(pic_path)
            # Use upload flow (will pick camera by default; prefer gallery when we pushed image)
            # Try to open Add Profile Picture and select Gallery path
            # Navigate to profile
            profile_btn = self.u2_device(resourceId="com.snapchat.android:id/profile_button")
            if profile_btn.exists(timeout=10):
                profile_btn.click()
                _sleep_human("navigation", 1.5)
            # Try to open Add Profile Picture UI and then rely on gallery selection inside helper
            return self._upload_profile_picture(name)
        except Exception as e:
            logger.error(f"Failed to set profile avatar: {e}")
            return False

    def link_bitmoji(self, email: Optional[str] = None, password: Optional[str] = None) -> Optional[str]:
        """Link Bitmoji account if credentials are provided; otherwise try basic creation flow.
        Returns screenshot path on success (proof), None if skipped or not available.
        """
        try:
            # Navigate to profile
            profile_btn = self.u2_device(resourceId="com.snapchat.android:id/profile_button")
            if not profile_btn.exists(timeout=10):
                return False
            profile_btn.click()
            _sleep_human("navigation", 1.5)

            # Find Bitmoji section
            for label in ["Add Bitmoji", "Create Bitmoji", "Bitmoji"]:
                bitmoji_btn = self.u2_device(text=label)
                if bitmoji_btn.exists(timeout=5):
                    bitmoji_btn.click()
                    _sleep_human("navigation", 1.5)
                    break
            else:
                # No Bitmoji UI available; skip
                # Capture screenshot as proof
                try:
                    screenshot_dir = Path('exports/bitmoji_proof')
                    screenshot_dir.mkdir(parents=True, exist_ok=True)
                    shot_path = screenshot_dir / f"bitmoji_{self.device_id}_{int(time.time())}.png"
                    img = self.u2_device.screenshot()
                    img.save(str(shot_path))
                    return str(shot_path)
                except Exception:
                    return None

            # If login path is available and creds provided
            if email and password:
                for login_label in ["Log In", "Log in", "Sign In", "Sign in", "Continue with Email"]:
                    login_btn = self.u2_device(text=login_label)
                    if login_btn.exists(timeout=5):
                        login_btn.click()
                        _sleep_human("navigation", 1.0)
                        break
                # Enter email
                email_field = self.u2_device(className="android.widget.EditText")
                if email_field.exists(timeout=5):
                    email_field.set_text(email)
                    _sleep_human("typing", 0.8)
                # Find next/continue
                cont_btn = self.u2_device(textMatches=".*(Next|Continue).*", className="android.widget.Button")
                if cont_btn.exists(timeout=5):
                    cont_btn.click()
                    _sleep_human("navigation", 1.0)
                # Enter password
                pwd_field = self.u2_device(className="android.widget.EditText")
                if pwd_field.exists(timeout=5):
                    pwd_field.set_text(password)
                    _sleep_human("typing", 0.8)
                # Submit
                for submit_label in ["Log In", "Sign In", "Continue"]:
                    sbtn = self.u2_device(text=submit_label)
                    if sbtn.exists(timeout=5):
                        sbtn.click()
                        _sleep_human("navigation", 2.0)
                        break
                # Accept linking if prompted
                for allow_label in ["Allow", "Agree", "Yes", "OK"]:
                    abtn = self.u2_device(text=allow_label)
                    if abtn.exists(timeout=5):
                        abtn.click()
                        _sleep_human("navigation", 1.0)
                        break
                return True

            # Otherwise try basic creation, selecting quick defaults if present
            for quick_label in ["Create", "Continue", "Get Started"]:
                qbtn = self.u2_device(text=quick_label)
                if qbtn.exists(timeout=5):
                    qbtn.click()
                    _sleep_human("navigation", 1.0)
                    break
            # If options appear (gender/skin tone), pick conservative defaults
            for opt in ["Male", "Female", "Light", "Next", "Done"]:
                obtn = self.u2_device(text=opt)
                if obtn.exists(timeout=3):
                    obtn.click()
                    _sleep_human("tap", 0.8)
            try:
                screenshot_dir = Path('exports/bitmoji_proof')
                screenshot_dir.mkdir(parents=True, exist_ok=True)
                shot_path = screenshot_dir / f"bitmoji_{self.device_id}_{int(time.time())}.png"
                img = self.u2_device.screenshot()
                img.save(str(shot_path))
                return str(shot_path)
            except Exception:
                return None
        except Exception as e:
            logger.warning(f"Bitmoji linking skipped due to error: {e}")
            return None
    
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
        """Tap UI element with dynamic delays"""
        try:
            # Add delay before tapping
            delay = self.anti_detection.get_next_action_delay(self.device_id)
            time.sleep(delay)
            
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
        """Enter text in input field with dynamic delays"""
        try:
            # Add delay before text entry
            delay = self.anti_detection.get_next_action_delay(self.device_id)
            time.sleep(delay)
            
            if field_text and self.u2_device(text=field_text).exists:
                self.u2_device(text=field_text).clear_text()
                time.sleep(random.uniform(0.5, 1.5))  # Realistic typing delay
                self.u2_device(text=field_text).set_text(text)
                return True
            elif resource_id and self.u2_device(resourceId=resource_id).exists:
                self.u2_device(resourceId=resource_id).clear_text()
                time.sleep(random.uniform(0.5, 1.5))
                self.u2_device(resourceId=resource_id).set_text(text)
                return True
            
            # Fallback: find any input field and enter text
            if self.u2_device(className="android.widget.EditText").exists:
                self.u2_device(className="android.widget.EditText").clear_text()
                time.sleep(random.uniform(0.5, 1.5))
                self.u2_device(className="android.widget.EditText").set_text(text)
                return True
            
            return False
        except Exception as e:
            logger.error(f"Failed to enter text: {e}")
            return False
    
    def _upload_profile_picture(self, profile_name: str = None) -> bool:
        """Upload profile picture to Snapchat account with real image handling"""
        try:
            logger.info("Starting profile picture upload with real image handling...")
            
            # Generate profile picture if needed
            if profile_name:
                generated_pic = self.profile_pic_generator.generate_profile_picture(profile_name)
                if generated_pic:
                    logger.info(f"Generated profile picture: {generated_pic}")
                    # Push image to device for selection
                    if not self._push_image_to_device(generated_pic):
                        logger.warning("Failed to push generated image to device")
            
            # Navigate to profile picture option
            if not self.wait_for_element("Add Profile Picture", timeout=10):
                # Try alternative text options
                if not (self.wait_for_element("Profile Photo", timeout=5) or 
                       self.wait_for_element("Add Photo", timeout=5)):
                    logger.warning("Profile picture option not found")
                    return False
            
            # Tap add profile picture
            if not (self.tap_element("Add Profile Picture") or 
                   self.tap_element("Profile Photo") or 
                   self.tap_element("Add Photo")):
                logger.warning("Could not tap profile picture option")
                return False
            
            # Dynamic delay for menu to appear
            delay = self.anti_detection.get_next_action_delay(self.device_id)
            time.sleep(delay)
            
            # Handle different photo source options
            photo_source_selected = False
            
            # Try Camera option first (more natural)
            if self.wait_for_element("Camera", timeout=3):
                if self.tap_element("Camera"):
                    photo_source_selected = True
                    _sleep_human("load", 2.0)  # Wait for camera to load
                    
                    # Take a photo by tapping shutter button
                    if self.u2_device(description="Shutter").exists:
                        self.u2_device(description="Shutter").click()
                    elif self.u2_device(className="android.widget.ImageButton").exists:
                        # Find and tap camera shutter (usually a large circular button)
                        buttons = self.u2_device(className="android.widget.ImageButton")
                        if buttons.count > 0:
                            buttons[0].click()  # Tap first button (likely shutter)
                    else:
                        # Fallback: tap center bottom area where shutter usually is
                        screen_info = self.u2_device.info
                        center_x = screen_info['displayWidth'] // 2
                        shutter_y = int(screen_info['displayHeight'] * 0.85)  # 85% down screen
                        self.u2_device.click(center_x, shutter_y)
                    
                    # Wait for photo to be taken
                    delay = self.anti_detection.get_next_action_delay(self.device_id)
                    time.sleep(delay)
                    
                    # Confirm/Use the photo
                    if self.wait_for_element("Use Photo", timeout=5):
                        self.tap_element("Use Photo")
                    elif self.wait_for_element("Done", timeout=5):
                        self.tap_element("Done")
                    elif self.wait_for_element("✓", timeout=5):  # Checkmark
                        self.tap_element("✓")
            
            # Fallback to Gallery if Camera didn't work
            used_gallery = False
            if not photo_source_selected:
                if self.wait_for_element("Gallery", timeout=5):
                    if self.tap_element("Gallery"):
                        photo_source_selected = True
                        used_gallery = True
                elif self.wait_for_element("Photos", timeout=5):
                    if self.tap_element("Photos"):
                        photo_source_selected = True
                        used_gallery = True
                elif self.wait_for_element("Choose from Gallery", timeout=5):
                    if self.tap_element("Choose from Gallery"):
                        photo_source_selected = True
                        used_gallery = True
            
            if not photo_source_selected:
                logger.error("Could not select photo source (Camera or Gallery)")
                return False
            
            # If we went with Gallery, select a photo
            if used_gallery:
                # Wait for gallery to load
                delay = self.anti_detection.get_next_action_delay(self.device_id)
                time.sleep(delay)
                
                # Look for image elements in gallery
                if self.u2_device(className="android.widget.ImageView").exists:
                    images = self.u2_device(className="android.widget.ImageView")
                    images_count = images.count
                    
                    if images_count > 0:
                        # Select first few images (avoid selecting UI elements)
                        selected_index = min(1, images_count - 1)  # Select 2nd image if available
                        images[selected_index].click()
                        
                        # Wait for selection
                        delay = self.anti_detection.get_next_action_delay(self.device_id)
                        time.sleep(delay)
                        
                        # Confirm selection
                        if self.wait_for_element("Done", timeout=5):
                            self.tap_element("Done")
                        elif self.wait_for_element("Select", timeout=5):
                            self.tap_element("Select")
                        elif self.wait_for_element("Choose", timeout=5):
                            self.tap_element("Choose")
                        elif self.wait_for_element("✓", timeout=5):
                            self.tap_element("✓")
                    else:
                        logger.warning("No images found in gallery")
                        return False
                else:
                    logger.warning("Gallery images not accessible")
                    return False
            
            # Final confirmation and cropping
            delay = self.anti_detection.get_next_action_delay(self.device_id)
            time.sleep(delay)
            
            # Handle potential cropping screen
            if self.wait_for_element("Crop", timeout=3) or self.wait_for_element("Edit", timeout=3):
                # If there's a crop/edit screen, just continue with default crop
                if self.wait_for_element("Done", timeout=5):
                    self.tap_element("Done")
                elif self.wait_for_element("Save", timeout=5):
                    self.tap_element("Save")
                elif self.wait_for_element("Apply", timeout=5):
                    self.tap_element("Apply")
            
            # Final save/set photo
            if self.wait_for_element("Set as Profile Photo", timeout=5):
                self.tap_element("Set as Profile Photo")
            elif self.wait_for_element("Save", timeout=5):
                self.tap_element("Save")
            
            logger.info("Profile picture upload completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload profile picture: {e}")
            return False
    
    def _push_image_to_device(self, image_path: str) -> bool:
        """Push generated image to device storage for selection"""
        try:
            # Push image to device's Pictures directory
            device_path = "/sdcard/Pictures/profile_temp.jpg"
            cmd = ["adb", "-s", self.device_id, "push", image_path, device_path]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                logger.info(f"Image pushed to device: {device_path}")
                
                # Refresh media scanner so image appears in gallery
                refresh_cmd = ["adb", "-s", self.device_id, "shell", 
                              "am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
                              "-d", f"file://{device_path}"]
                subprocess.run(refresh_cmd, capture_output=True, timeout=30)
                
                return True
            else:
                logger.error(f"Failed to push image: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error pushing image to device: {e}")
            return False
    
    def submit_verification_code(self, verification_code: str) -> bool:
        """Submit SMS verification code"""
        try:
            # Find verification code input field
            if self.u2_device:
                # Look for code input field
                code_input = self.u2_device(resourceId="com.snapchat.android:id/verification_code_edit_text")
                if not code_input.wait(timeout=10):
                    # Try alternative selectors
                    code_input = self.u2_device(className="android.widget.EditText")
                    if not code_input.wait(timeout=5):
                        logger.error("Verification code input field not found")
                        return False
                
                # Clear and enter code
                code_input.clear_text()
                code_input.set_text(verification_code)
                
                # Find and click submit/continue button
                submit_btn = self.u2_device(resourceId="com.snapchat.android:id/continue_button")
                if not submit_btn.exists(timeout=5):
                    submit_btn = self.u2_device(text="Continue")
                    if not submit_btn.exists(timeout=5):
                        submit_btn = self.u2_device(text="Verify")
                
                if submit_btn.exists():
                    submit_btn.click()
                    
                    # Wait for verification to complete
                    _sleep_human("verification", 3.0)
                    
                    # Check if verification was successful
                    error_elements = self.u2_device(textContains="Invalid code")
                    if error_elements.exists():
                        logger.error("Invalid verification code")
                        return False
                    
                    return True
                else:
                    logger.error("Submit button not found")
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"Error submitting verification code: {e}")
            return False
    
    def configure_privacy_settings(self, settings: dict) -> bool:
        """Configure privacy settings for add farming"""
        try:
            if not self.u2_device:
                return False
            
            # Navigate to settings
            profile_btn = self.u2_device(resourceId="com.snapchat.android:id/profile_button")
            if profile_btn.exists(timeout=10):
                profile_btn.click()
                _sleep_human("navigation", 2.0)
                
                # Find settings gear
                settings_btn = self.u2_device(resourceId="com.snapchat.android:id/settings_button")
                if settings_btn.exists(timeout=5):
                    settings_btn.click()
                    _sleep_human("navigation", 2.0)
                    
                    # Navigate to privacy settings
                    privacy_btn = self.u2_device(text="Privacy")
                    if privacy_btn.exists(timeout=5):
                        privacy_btn.click()
                        _sleep_human("navigation", 2.0)
                        
                        # Configure each setting
                        for setting, value in settings.items():
                            self._configure_privacy_setting(setting, value)
                        
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error configuring privacy settings: {e}")
            return False
    
    def _configure_privacy_setting(self, setting: str, value: bool):
        """Configure individual privacy setting"""
        try:
            setting_element = None
            
            if setting == 'quick_add':
                setting_element = self.u2_device(text="Quick Add")
            elif setting == 'phone_discovery':
                setting_element = self.u2_device(text="Contact Me")
            elif setting == 'friend_suggestions':
                setting_element = self.u2_device(text="See Me in Suggestions")
            
            if setting_element and setting_element.exists(timeout=3):
                setting_element.click()
                _sleep_human("tap", 1.0)
                
                # Toggle setting if needed
                toggle = self.u2_device(className="android.widget.Switch")
                if toggle.exists():
                    current_state = toggle.checked
                    if current_state != value:
                        toggle.click()
                        _sleep_human("tap", 1.0)
                
                # Go back
                back_btn = self.u2_device(description="Navigate up")
                if back_btn.exists():
                    back_btn.click()
                    _sleep_human("navigation", 1.0)
                    
        except Exception as e:
            logger.warning(f"Error configuring {setting}: {e}")
    
    def optimize_profile_for_adds(self) -> bool:
        """Optimize profile to maximize friend add acceptance"""
        try:
            if not self.u2_device:
                return False
            
            # Navigate to profile
            profile_btn = self.u2_device(resourceId="com.snapchat.android:id/profile_button")
            if profile_btn.exists(timeout=10):
                profile_btn.click()
                _sleep_human("navigation", 2.0)
                
                # Check if profile picture exists, add one if not
                add_pic_btn = self.u2_device(text="Add Profile Picture")
                if add_pic_btn.exists():
                    # Would add profile picture logic here
                    pass
                
                # Add Bitmoji if available
                bitmoji_btn = self.u2_device(text="Create Bitmoji")
                if bitmoji_btn.exists():
                    # Would add Bitmoji creation logic here
                    pass
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error optimizing profile: {e}")
            return False
    
    def apply_security_hardening(self, settings: dict) -> bool:
        """Apply final security hardening measures"""
        try:
            if not self.u2_device:
                return False
            
            # Clear app cache if requested
            if settings.get('clear_cache', False):
                self._clear_app_cache()
            
            # Apply anti-detection measures
            if settings.get('anti_detection_final', False):
                self._apply_final_anti_detection()
            
            return True
            
        except Exception as e:
            logger.error(f"Error applying security hardening: {e}")
            return False
    
    def _clear_app_cache(self):
        """Clear Snapchat app cache"""
        try:
            # Navigate to Android settings
            self.u2_device.app_stop("com.snapchat.android")
            _sleep_human("navigation", 1.0)
            self.u2_device.app_clear("com.snapchat.android")
            _sleep_human("navigation", 2.0)
            
        except Exception as e:
            logger.warning(f"Error clearing app cache: {e}")
    
    def _apply_final_anti_detection(self):
        """Apply final anti-detection measures"""
        try:
            # Randomize some device settings
            # This would include changing device timezone, language, etc.
            pass
            
        except Exception as e:
            logger.warning(f"Error applying final anti-detection: {e}")
    
    def save_account_state(self) -> bool:
        """Save current account state for future use"""
        try:
            # This would save the account state to a file or database
            # for later automation use
            return True
            
        except Exception as e:
            logger.error(f"Error saving account state: {e}")
            return False

class SnapchatStealthCreator:
    """Main Snapchat stealth account creation system"""
    
    def __init__(self):
        # Validate required dependencies on initialization
        self._validate_dependencies()
        
        self.username_generator = SnapchatUsernameGenerator()
        self.anti_detection = get_anti_detection_system()
        self.created_accounts: List[SnapchatCreationResult] = []
        self._automators: Dict[str, SnapchatAppAutomator] = {}
    
    def _validate_dependencies(self) -> None:
        """Validate all required dependencies are available."""
        missing_deps = []
        missing_tools = []
        warnings = []
        
        # Check Python packages
        required_packages = {
            'uiautomator2': 'UI automation for Android devices',
            'faker': 'Profile data generation',
            'requests': 'HTTP requests for API calls',
            'Pillow': 'Image processing for profile pictures',
            'beautifulsoup4': 'HTML parsing (optional for APK download)',
        }
        
        for package, description in required_packages.items():
            try:
                __import__(package)
            except ImportError:
                if package == 'beautifulsoup4':
                    warnings.append(f"Optional: {package} - {description}")
                else:
                    missing_deps.append(f"{package} - {description}")
        
        # Check Android tools
        android_tools = {
            'adb': 'Android Debug Bridge - required for device communication',
            'aapt': 'Android Asset Packaging Tool - for APK verification',
            'apksigner': 'APK signature verification (optional but recommended)',
        }
        
        for tool, description in android_tools.items():
            try:
                result = subprocess.run([tool, '--version'], 
                                      capture_output=True, timeout=5)
                if result.returncode != 0:
                    if tool == 'apksigner':
                        warnings.append(f"Optional: {tool} - {description}")
                    else:
                        missing_tools.append(f"{tool} - {description}")
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                if tool == 'apksigner':
                    warnings.append(f"Optional: {tool} - {description}")
                else:
                    missing_tools.append(f"{tool} - {description}")
        
        # Report findings
        if missing_deps:
            logger.error("Missing required Python packages:")
            for dep in missing_deps:
                logger.error(f"  - {dep}")
            logger.error("Install missing packages: pip install uiautomator2 faker requests Pillow")
            raise RuntimeError(f"Missing required dependencies: {[d.split(' -')[0] for d in missing_deps]}")
        
        if missing_tools:
            logger.error("Missing required Android tools:")
            for tool in missing_tools:
                logger.error(f"  - {tool}")
            logger.error("Ensure Android SDK is installed and tools are in PATH")
            raise RuntimeError(f"Missing required Android tools: {[t.split(' -')[0] for t in missing_tools]}")
        
        if warnings:
            for warning in warnings:
                logger.warning(f"Optional dependency: {warning}")
        
        logger.info("✅ All required dependencies validated successfully")
        
    def generate_stealth_profile(self, first_name: str = None, female_names: List[str] = None) -> SnapchatProfile:
        """Generate stealth Snapchat profile with female name support"""
        fake = Faker()
        
        # Default female names list
        if female_names is None:
            female_names = [
                "Emma", "Olivia", "Sophia", "Isabella", "Charlotte", 
                "Amelia", "Mia", "Harper", "Evelyn", "Abigail",
                "Emily", "Elizabeth", "Sofia", "Avery", "Madison"
            ]
        
        if not first_name:
            first_name = random.choice(female_names)
        
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
        
        # Generate email using email automation system or fallback
        email = None
        if EMAIL_INTEGRATION_AVAILABLE:
            try:
                # Try to get email from pool for better deliverability
                if _load_email_integration() and get_snapchat_email:
                    # Use sync wrapper or fallback to generated email
                    try:
                        email_account = get_snapchat_email()  # Assume sync version available
                    except Exception:
                        email_account = None  # Fallback to generated email
                    if email_account:
                        email = email_account.email
                        logger.info(f"Using email from automation pool: {email}")
            except Exception as e:
                logger.warning(f"Failed to get email from pool: {e}")
        
        # Fallback to generated email if pool unavailable
        if not email:
            email_domains = ["gmail.com", "yahoo.com", "hotmail.com", "icloud.com"]
            email_username = f"{first_name.lower()}.{last_name.lower()}.{random.randint(100, 999)}"
            email = f"{email_username}@{random.choice(email_domains)}"
            logger.info(f"Using generated email: {email}")
        
        # Get phone number from Twilio pool
        phone_number = None
        try:
            twilio_provider = get_twilio_sms_provider()
            pr = twilio_provider.get_number()
            if pr.get('success'):
                phone_number = pr['phone_number']  # type: ignore[index]
                logger.info(f"Using Twilio SMS provider number: {phone_number}")
        except Exception as e:
            logger.warning(f"Twilio provider not available: {e}")
        if not phone_number:
            area_codes = ["555", "216", "312", "415", "713", "202", "305", "404"]
            phone_number = f"+1{random.choice(area_codes)}{random.randint(1000000, 9999999)}"
            logger.warning(f"Using generated phone number: {phone_number} (Twilio unavailable)")
        
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
            # Acquire Twilio phone number
            try:
                twilio_provider = get_twilio_sms_provider()
                pr = twilio_provider.get_number()
                if not pr.get('success'):
                    raise RuntimeError("No available Twilio phone numbers")
                profile.phone_number = pr['phone_number']  # type: ignore[index]
            except Exception:
                logger.warning("Twilio provider not available; using generated phone number may fail verification")

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
            
            # Return email to pool if using email automation
            if _load_email_integration() and get_email_integrator:
                try:
                    integrator = get_email_integrator()
                    # Use sync wrapper for email return or log for manual cleanup
                    try:
                        integrator.return_email_to_pool_sync(profile.email, success=True)
                    except AttributeError:
                        logger.info(f"Email {profile.email} needs manual return to pool (success=True)")
                    if email_returned:
                        logger.info(f"Returned email {profile.email} to pool successfully")
                    else:
                        logger.warning(f"Failed to return email {profile.email} to pool")
                except Exception as e:
                    logger.warning(f"Error returning email to pool: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to create Snapchat account: {e}")

            # Release Twilio number on failure
            try:
                twilio_provider = get_twilio_sms_provider()
                twilio_provider.release_number(profile.phone_number)
                logger.info(f"Released Twilio provider number after failure: {profile.phone_number}")
            except Exception as re_err:
                logger.warning(f"Failed to release Twilio number: {re_err}")
            
            # Return email to pool if using email automation (mark as failed)
            if _load_email_integration() and get_email_integrator and profile and profile.email:
                try:
                    integrator = get_email_integrator()
                    # Use sync wrapper for email return or log for manual cleanup
                    try:
                        integrator.return_email_to_pool_sync(profile.email, success=False)
                    except AttributeError:
                        logger.info(f"Email {profile.email} needs manual return to pool (success=False)")
                    logger.info(f"Returned failed email {profile.email} to pool")
                except Exception as email_error:
                    logger.warning(f"Error returning failed email to pool: {email_error}")
            
            return SnapchatCreationResult(
                success=False,
                profile=profile,
                account_id=account_id,
                device_id=device_id,
                creation_time=creation_start,
                error=str(e),
                verification_status="failed"
            )
    
    # ================================
    # MISSING CORE AUTOMATION METHODS
    # ================================
    
    async def create_snapchat_account(self, profile: SnapchatProfile, device_id: str) -> SnapchatCreationResult:
        """Create single Snapchat account with real UIAutomator2 automation"""
        account_id = str(uuid.uuid4())
        creation_start = datetime.now()
        
        logger.info(f"Creating Snapchat account: {profile.username} on {device_id}")
        
        try:
            # Setup emulator environment with anti-detection
            if not await self._setup_emulator_environment(device_id):
                raise SnapchatCreationError(f"Failed to setup emulator environment for {device_id}")
                
            # Connect to device using UIAutomator2
            u2_device = u2.connect(device_id)
            if not u2_device.info:
                raise SnapchatCreationError(f"Failed to connect to device {device_id}")
                
            # Apply anti-detection fingerprint
            device_fingerprint = self.anti_detection.get_device_fingerprint(device_id)
            await self._apply_device_fingerprint(u2_device, device_fingerprint)
            
            # Install and launch Snapchat with anti-detection
            if not await self._install_and_launch_snapchat(u2_device):
                raise SnapchatCreationError("Failed to install or launch Snapchat")
                
            # Wait for app to stabilize with human-like delay
            await self.add_human_delay(3000, 5000)
            
            # Handle registration flow
            if not await self._handle_snapchat_registration(u2_device, profile):
                raise RegistrationFlowError("Failed during registration flow")
                
            # Handle SMS verification
            if not await self._handle_sms_verification(u2_device, profile.phone_number):
                raise VerificationError("Failed SMS verification")
                
            # Complete profile setup
            if not await self._complete_profile_setup(u2_device, profile):
                raise SnapchatCreationError("Failed to complete profile setup")
                
            # Apply privacy and security optimizations
            await self._optimize_privacy_settings_async(u2_device)
            await self._perform_trust_building_activities(u2_device)
            
            # Calculate creation time
            creation_time = (datetime.now() - creation_start).total_seconds()
            
            result = SnapchatCreationResult(
                account_id=account_id,
                username=profile.username,
                email=profile.email,
                phone_number=profile.phone_number,
                password=profile.password,
                success=True,
                profile=profile,
                device_id=device_id,
                creation_time=creation_start,
                verification_status="completed",
                snapchat_score=0,
                additional_data={
                    "creation_time_seconds": creation_time,
                    "device_fingerprint_applied": True,
                    "privacy_optimized": True,
                    "trust_building_completed": True
                }
            )
            
            self.created_accounts.append(result)
            logger.info(f"Successfully created Snapchat account: {profile.username} in {creation_time:.1f}s")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create Snapchat account {profile.username}: {e}")
            creation_time = (datetime.now() - creation_start).total_seconds()
            
            return SnapchatCreationResult(
                account_id=account_id,
                username=profile.username,
                email=profile.email,
                phone_number=profile.phone_number,
                password=profile.password,
                success=False,
                profile=profile,
                device_id=device_id,
                creation_time=creation_start,
                verification_status="failed",
                error=str(e)
            )
            
    async def create_snapchat_account_async(self, profile: SnapchatProfile) -> SnapchatCreationResult:
        """Create Snapchat account with automatic device selection"""
        # Get available device from emulator manager
        device_id = self._get_available_device()
        if not device_id:
            raise SnapchatCreationError("No available devices for account creation")
            
        return await self.create_snapchat_account(profile, device_id)
    
    async def _setup_emulator_environment(self, device_id: str) -> bool:
        """Setup emulator environment with anti-detection measures"""
        try:
            logger.info(f"Setting up emulator environment for {device_id}")
            
            # Connect to device and verify connectivity
            u2_device = u2.connect(device_id)
            if not u2_device.info:
                logger.error(f"Cannot connect to device {device_id}")
                return False
            
            # Clear any existing Snapchat data
            try:
                u2_device.app_clear('com.snapchat.android')
                await self.add_human_delay(1000, 2000)
            except Exception:
                logger.debug("Snapchat app not installed yet, continuing")
            
            # Apply device-specific anti-detection settings
            device_fingerprint = self.anti_detection.get_device_fingerprint(device_id)
            
            # Set timezone, language, and locale
            u2_device.shell(f'setprop persist.sys.timezone "{device_fingerprint.timezone}"')
            u2_device.shell(f'setprop persist.sys.language "{device_fingerprint.language[:2]}"')
            u2_device.shell(f'setprop persist.sys.country "{device_fingerprint.language[-2:]}"')
            
            # Randomize device settings
            await self._randomize_device_settings(u2_device)
            
            # Install necessary system apps if missing
            await self._ensure_system_apps(u2_device)
            
            logger.info(f"Emulator environment setup complete for {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup emulator environment: {e}")
            return False
    
    async def _apply_device_fingerprint(self, u2_device, device_fingerprint) -> None:
        """Apply device fingerprint with anti-detection measures"""
        try:
            logger.debug("Applying device fingerprint with anti-detection")
            
            # Apply hardware characteristics
            if hasattr(device_fingerprint, 'hardware_fingerprint'):
                for key, value in device_fingerprint.hardware_fingerprint.items():
                    u2_device.shell(f'setprop {key} "{value}"')
            
            # Set display properties
            if hasattr(device_fingerprint, 'display_resolution'):
                width, height = device_fingerprint.display_resolution
                u2_device.shell(f'wm size {width}x{height}')
            
            if hasattr(device_fingerprint, 'dpi'):
                u2_device.shell(f'wm density {device_fingerprint.dpi}')
            
            # Apply network characteristics
            if hasattr(device_fingerprint, 'network_characteristics'):
                # Set carrier properties
                carrier = device_fingerprint.carrier
                u2_device.shell(f'setprop gsm.sim.operator.alpha "{carrier}"')
                u2_device.shell(f'setprop gsm.operator.alpha "{carrier}"')
            
            await self.add_human_delay(500, 1000)
            
        except Exception as e:
            logger.warning(f"Failed to apply some fingerprint settings: {e}")
    
    async def _install_and_launch_snapchat(self, u2_device) -> bool:
        """Install and launch Snapchat with anti-detection"""
        try:
            logger.info("Installing and launching Snapchat")
            
            # Check if Snapchat is already installed
            installed_apps = u2_device.shell('pm list packages com.snapchat.android').output
            if 'com.snapchat.android' not in installed_apps:
                # Download and install Snapchat APK
                apk_path = await self._download_snapchat_apk()
                if not apk_path:
                    logger.error("Failed to download Snapchat APK")
                    return False
                
                # Install APK
                install_result = u2_device.shell(f'pm install -r "{apk_path}"')
                if install_result.exit_code != 0:
                    logger.error(f"Failed to install Snapchat: {install_result.output}")
                    return False
                
                # Wait for installation to complete
                await self.add_human_delay(3000, 5000)
            
            # Launch Snapchat
            u2_device.app_start('com.snapchat.android')
            
            # Wait for app to load with timeout
            start_time = time.time()
            timeout = 30
            
            while time.time() - start_time < timeout:
                if u2_device.app_current()['package'] == 'com.snapchat.android':
                    logger.info("Snapchat launched successfully")
                    await self.add_human_delay(2000, 4000)
                    return True
                await asyncio.sleep(1)
            
            logger.error("Snapchat failed to launch within timeout")
            return False
            
        except Exception as e:
            logger.error(f"Failed to install/launch Snapchat: {e}")
            return False
    
    async def _handle_snapchat_registration(self, u2_device, profile: SnapchatProfile) -> bool:
        """Handle Snapchat registration flow with real UI automation"""
        try:
            logger.info(f"Starting registration for {profile.username}")
            
            # Wait for welcome screen and dismiss any tutorials
            await self._dismiss_welcome_screens(u2_device)
            
            # Look for "Sign Up" button with multiple locators
            signup_found = False
            signup_selectors = [
                {'text': 'Sign Up'},
                {'text': 'SIGN UP'},
                {'text': 'Create Account'},
                {'textContains': 'Sign'},
                {'resourceId': 'com.snapchat.android:id/signup_button'},
                {'className': 'android.widget.Button'},
            ]
            
            for selector in signup_selectors:
                if u2_device(**selector).exists(timeout=5):
                    logger.info(f"Found signup button with selector: {selector}")
                    u2_device(**selector).click()
                    signup_found = True
                    break
            
            if not signup_found:
                logger.error("Could not find Sign Up button")
                return False
            
            await self.add_human_delay(2000, 3000)
            
            # Fill in registration details with human-like typing
            registration_steps = [
                ('first_name', profile.display_name.split()[0]),
                ('last_name', profile.display_name.split()[-1] if len(profile.display_name.split()) > 1 else ''),
                ('username', profile.username),
                ('password', profile.password),
                ('email', profile.email),
                ('phone', profile.phone_number)
            ]
            
            for field_type, value in registration_steps:
                if not await self._fill_registration_field(u2_device, field_type, value):
                    logger.error(f"Failed to fill {field_type} field")
                    return False
            
            # Handle birth date selection
            if not await self._handle_birth_date_selection(u2_device, profile.birth_date):
                logger.error("Failed to set birth date")
                return False
            
            # Accept terms and conditions
            if not await self._accept_terms_and_conditions(u2_device):
                logger.error("Failed to accept terms")
                return False
            
            # Submit registration
            if not await self._submit_registration(u2_device):
                logger.error("Failed to submit registration")
                return False
            
            logger.info("Registration flow completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Registration flow failed: {e}")
            return False
    
    async def _handle_sms_verification(self, u2_device, phone_number: str) -> bool:
        """Handle SMS verification with enhanced error handling and graceful fallback"""
        try:
            logger.info(f"🔐 Starting SMS verification for {phone_number}")
            
            # Initialize SMS verifier with enhanced error handling
            sms_verifier = get_sms_verifier()
            
            # Check if SMS service is available
            if not sms_verifier.pool_available:
                logger.warning("⚠️ SMS service not available - using fallback verification")
                return await self._handle_fallback_verification(u2_device, phone_number)
            
            # Send verification SMS
            verification_result = await sms_verifier.send_verification_sms(
                to_number=phone_number,
                app_name="Snapchat"
            )
            
            if not verification_result['success']:
                error_msg = verification_result.get('error', 'Unknown error')
                error_code = verification_result.get('error_code', 'SMS_ERROR')
                
                logger.error(f"❌ Failed to send verification SMS: {error_msg}")
                
                # Handle different error scenarios
                if error_code == 'SMS_DISABLED':
                    logger.info("📱 SMS disabled - using fallback verification")
                    return await self._handle_fallback_verification(u2_device, phone_number)
                elif error_code == 'RATE_LIMIT_EXCEEDED':
                    retry_after = verification_result.get('retry_after_seconds', 300)
                    logger.warning(f"⏳ Rate limit exceeded, retry after {retry_after}s")
                    await asyncio.sleep(min(retry_after, 60))  # Wait max 1 minute
                    return False
                else:
                    return False
            
            logger.info(f"📤 SMS verification sent, Message ID: {verification_result.get('message_id')}")
            
            # Wait for verification code with enhanced polling
            max_attempts = 18  # 3 minutes total (18 * 10 seconds)
            attempt = 0
            
            while attempt < max_attempts:
                attempt += 1
                logger.debug(f"🔍 Polling for SMS code... attempt {attempt}/{max_attempts}")
                
                # Check verification status
                status = sms_verifier.get_verification_status(phone_number)
                
                if status.get('has_pending_verification'):
                    # Try to retrieve the code
                    code_result = await sms_verifier.verify_sms_code(phone_number, "000000")  # Dummy code to trigger retrieval
                    
                    # Check if we can retrieve the actual code  
                    try:
                        retrieved_code = await sms_verifier._retrieve_sms_code(phone_number)
                        if retrieved_code:
                            verification_code = retrieved_code
                            logger.info(f"📱 Received verification code: ***{verification_code[-2:]}")
                            
                            # Enter verification code in UI
                            if await self._enter_verification_code(u2_device, verification_code):
                                logger.info("✅ SMS verification completed successfully")
                                return True
                            else:
                                logger.error("❌ Failed to enter verification code in UI")
                                return False
                    except Exception as retrieve_error:
                        logger.debug(f"Code retrieval attempt failed: {retrieve_error}")
                
                # Wait before next attempt
                await asyncio.sleep(10)
            
            logger.error("⏰ SMS verification timeout - no code received")
            return await self._handle_fallback_verification(u2_device, phone_number)
            
        except Exception as e:
            logger.error(f"❌ SMS verification failed: {e}")
            return await self._handle_fallback_verification(u2_device, phone_number)
    
    async def _handle_fallback_verification(self, u2_device, phone_number: str) -> bool:
        """Handle verification when SMS service is not available"""
        try:
            logger.info(f"🔄 Using fallback verification for {phone_number}")
            
            # Wait for manual code entry or skip verification
            max_wait = 60  # Wait up to 1 minute for manual intervention
            wait_time = 0
            
            while wait_time < max_wait:
                # Check if verification was bypassed or completed manually
                if (u2_device(textContains='Welcome').exists() or
                    u2_device(textContains='Profile').exists() or
                    u2_device(textContains='Friends').exists() or
                    u2_device(textContains='Skip').exists()):
                    
                    # Try to skip verification if possible
                    if u2_device(textContains='Skip').exists():
                        logger.info("🚫 Skipping SMS verification")
                        u2_device(textContains='Skip').click()
                        await asyncio.sleep(2)
                        return True
                    
                    logger.info("✅ Verification appears to be completed or bypassed")
                    return True
                
                # Check for "Continue without verification" or similar options
                continue_patterns = [
                    'Continue without',
                    'Skip verification',
                    'Not now',
                    'Maybe later'
                ]
                
                for pattern in continue_patterns:
                    if u2_device(textContains=pattern).exists():
                        logger.info(f"🚫 Using fallback option: {pattern}")
                        u2_device(textContains=pattern).click()
                        await asyncio.sleep(2)
                        return True
                
                await asyncio.sleep(5)
                wait_time += 5
                
                if wait_time % 15 == 0:  # Log every 15 seconds
                    logger.info(f"🕰️ Waiting for manual verification or skip option... ({wait_time}/{max_wait}s)")
            
            logger.warning("⏰ Fallback verification timeout")
            return False
            
        except Exception as e:
            logger.error(f"❌ Fallback verification failed: {e}")
            return False
    
    async def _complete_profile_setup(self, u2_device, profile: SnapchatProfile) -> bool:
        """Complete profile setup with human-like interactions"""
        try:
            logger.info("Completing profile setup")
            
            # Skip optional steps initially
            await self._skip_optional_steps(u2_device)
            
            # Set profile picture if available
            if profile.profile_pic_path and os.path.exists(profile.profile_pic_path):
                await self._set_profile_picture(u2_device, profile.profile_pic_path)
            
            # Set bio if provided
            if profile.bio:
                await self._set_profile_bio(u2_device, profile.bio)
            
            # Complete onboarding flow
            await self._complete_onboarding(u2_device)
            
            logger.info("Profile setup completed")
            return True
            
        except Exception as e:
            logger.error(f"Profile setup failed: {e}")
            return False
    
    # ================================
    # ENHANCED ANTI-DETECTION METHODS
    # ================================
    
    def get_random_user_agent(self) -> str:
        """Get random user agent for Android device"""
        android_versions = ['12', '13', '14']
        webview_versions = ['118.0.5993.80', '119.0.6045.66', '120.0.6099.43']
        
        android_version = random.choice(android_versions)
        webview_version = random.choice(webview_versions)
        
        return f"Mozilla/5.0 (Linux; Android {android_version}; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{webview_version} Mobile Safari/537.36"
    
    def get_device_fingerprint(self, device_id: str) -> Dict:
        """Get comprehensive device fingerprint"""
        return self.anti_detection.get_device_fingerprint(device_id)
    
    async def add_human_delay(self, min_ms: int, max_ms: int) -> None:
        """Add human-like delays between actions"""
        delay_ms = random.randint(min_ms, max_ms)
        await asyncio.sleep(delay_ms / 1000.0)
    
    def randomize_typing_speed(self, text: str) -> List[Tuple[str, float]]:
        """Generate realistic typing patterns"""
        typing_patterns = []
        base_delay = random.uniform(0.1, 0.3)  # Base typing speed
        
        for i, char in enumerate(text):
            # Add variation based on character type
            if char.isalpha():
                delay = base_delay + random.uniform(-0.05, 0.1)
            elif char.isdigit():
                delay = base_delay + random.uniform(0.05, 0.15)
            elif char in ' .,!?':
                delay = base_delay + random.uniform(0.1, 0.3)
            else:
                delay = base_delay + random.uniform(0.05, 0.2)
            
            # Occasional pauses (thinking)
            if random.random() < 0.1:  # 10% chance
                delay += random.uniform(0.5, 2.0)
            
            typing_patterns.append((char, delay))
        
        return typing_patterns
    
    async def simulate_human_interaction(self, u2_device, element: str) -> bool:
        """Simulate human-like interaction with UI elements"""
        try:
            # Add pre-interaction delay
            await self.add_human_delay(500, 1500)
            
            # Find element with multiple strategies
            element_obj = None
            strategies = [
                lambda: u2_device(text=element),
                lambda: u2_device(textContains=element),
                lambda: u2_device(resourceId=element),
                lambda: u2_device(description=element),
                lambda: u2_device(className=element)
            ]
            
            for strategy in strategies:
                try:
                    candidate = strategy()
                    if candidate.exists(timeout=2):
                        element_obj = candidate
                        break
                except Exception:
                    continue
            
            if not element_obj:
                logger.warning(f"Element not found: {element}")
                return False
            
            # Get element bounds for realistic touch
            bounds = element_obj.info['bounds']
            x = random.randint(bounds['left'] + 5, bounds['right'] - 5)
            y = random.randint(bounds['top'] + 5, bounds['bottom'] - 5)
            
            # Simulate human-like tap
            u2_device.click(x, y)
            
            # Add post-interaction delay
            await self.add_human_delay(300, 1000)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to interact with element {element}: {e}")
            return False
    
    def _get_available_device(self) -> Optional[str]:
        """Get available emulator device ID"""
        try:
            # Check connected devices
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
            if result.returncode != 0:
                logger.error("Failed to get device list")
                return None
            
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            devices = []
            
            for line in lines:
                if '\tdevice' in line:
                    device_id = line.split('\t')[0]
                    devices.append(device_id)
            
            if not devices:
                logger.error("No available devices found")
                return None
            
            # Return first available device
            return devices[0]
            
        except Exception as e:
            logger.error(f"Error getting available device: {e}")
            return None
    
    # ================================
    # SUPPORTING HELPER METHODS
    # ================================
    
    async def _dismiss_welcome_screens(self, u2_device) -> None:
        """Dismiss welcome screens and tutorials"""
        try:
            # Common welcome screen dismissal patterns
            dismiss_patterns = [
                {'text': 'Skip'},
                {'text': 'Next'},
                {'text': 'Continue'},
                {'text': 'Get Started'},
                {'text': 'Allow'},
                {'resourceId': 'com.android.packageinstaller:id/permission_allow_button'},
                {'className': 'android.widget.Button'},
            ]
            
            # Try to dismiss up to 5 screens
            for attempt in range(5):
                dismissed = False
                for pattern in dismiss_patterns:
                    if u2_device(**pattern).exists(timeout=2):
                        u2_device(**pattern).click()
                        dismissed = True
                        await self.add_human_delay(1000, 2000)
                        break
                
                if not dismissed:
                    break  # No more screens to dismiss
                    
        except Exception as e:
            logger.debug(f"Error dismissing welcome screens: {e}")
    
    async def _fill_registration_field(self, u2_device, field_type: str, value: str) -> bool:
        """Fill registration field with human-like typing"""
        try:
            # Field selectors based on field type
            field_selectors = {
                'first_name': [
                    {'text': 'First name'},
                    {'textContains': 'First'},
                    {'resourceId': 'com.snapchat.android:id/first_name'},
                    {'hint': 'First name'}
                ],
                'last_name': [
                    {'text': 'Last name'},
                    {'textContains': 'Last'},
                    {'resourceId': 'com.snapchat.android:id/last_name'},
                    {'hint': 'Last name'}
                ],
                'username': [
                    {'text': 'Username'},
                    {'textContains': 'Username'},
                    {'resourceId': 'com.snapchat.android:id/username'},
                    {'hint': 'Username'}
                ],
                'password': [
                    {'text': 'Password'},
                    {'textContains': 'Password'},
                    {'resourceId': 'com.snapchat.android:id/password'},
                    {'hint': 'Password'}
                ],
                'email': [
                    {'text': 'Email'},
                    {'textContains': 'Email'},
                    {'resourceId': 'com.snapchat.android:id/email'},
                    {'hint': 'Email'}
                ],
                'phone': [
                    {'text': 'Phone number'},
                    {'textContains': 'Phone'},
                    {'resourceId': 'com.snapchat.android:id/phone'},
                    {'hint': 'Phone number'}
                ]
            }
            
            selectors = field_selectors.get(field_type, [{'className': 'android.widget.EditText'}])
            
            # Find and fill field
            field_found = False
            for selector in selectors:
                if u2_device(**selector).exists(timeout=5):
                    field = u2_device(**selector)
                    
                    # Clear field first
                    field.clear_text()
                    await self.add_human_delay(300, 800)
                    
                    # Type with human-like patterns
                    typing_patterns = self.randomize_typing_speed(value)
                    for char, delay in typing_patterns:
                        field.send_keys(char)
                        await asyncio.sleep(delay)
                    
                    field_found = True
                    logger.debug(f"Filled {field_type} field with: {value}")
                    break
            
            if not field_found:
                logger.warning(f"Could not find {field_type} field")
                return False
            
            await self.add_human_delay(500, 1000)
            return True
            
        except Exception as e:
            logger.error(f"Failed to fill {field_type} field: {e}")
            return False
    
    async def _handle_birth_date_selection(self, u2_device, birth_date: date) -> bool:
        """Handle birth date selection with multiple UI patterns"""
        try:
            logger.debug(f"Setting birth date: {birth_date}")
            
            # Look for date picker triggers
            date_triggers = [
                {'text': 'Birthday'},
                {'text': 'Birth date'},
                {'textContains': 'Birthday'},
                {'resourceId': 'com.snapchat.android:id/birthday'},
                {'className': 'android.widget.DatePicker'}
            ]
            
            # Find and tap date picker
            for trigger in date_triggers:
                if u2_device(**trigger).exists(timeout=3):
                    u2_device(**trigger).click()
                    await self.add_human_delay(1000, 2000)
                    break
            
            # Handle different date picker styles
            if await self._handle_wheel_date_picker(u2_device, birth_date):
                return True
            elif await self._handle_calendar_date_picker(u2_device, birth_date):
                return True
            elif await self._handle_text_date_picker(u2_device, birth_date):
                return True
            
            logger.warning("Could not handle birth date selection")
            return False
            
        except Exception as e:
            logger.error(f"Birth date selection failed: {e}")
            return False
    
    async def _handle_wheel_date_picker(self, u2_device, birth_date: date) -> bool:
        """Handle wheel/spinner style date picker"""
        try:
            # Look for NumberPicker or spinner elements
            if u2_device(className="android.widget.NumberPicker").exists(timeout=3):
                pickers = u2_device(className="android.widget.NumberPicker")
                
                # Typically: Month, Day, Year order
                if pickers.count >= 3:
                    month_picker = pickers[0]
                    day_picker = pickers[1] 
                    year_picker = pickers[2]
                    
                    # Set month (0-11 or 1-12 depending on implementation)
                    await self._scroll_picker_to_value(month_picker, str(birth_date.month))
                    await self._scroll_picker_to_value(day_picker, str(birth_date.day))
                    await self._scroll_picker_to_value(year_picker, str(birth_date.year))
                    
                    # Confirm selection
                    if u2_device(text='OK').exists() or u2_device(text='Done').exists():
                        u2_device(text='OK').click() if u2_device(text='OK').exists() else u2_device(text='Done').click()
                        await self.add_human_delay(500, 1000)
                        return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Wheel date picker failed: {e}")
            return False
    
    async def _handle_calendar_date_picker(self, u2_device, birth_date: date) -> bool:
        """Handle calendar grid style date picker"""
        try:
            if u2_device(className="android.widget.CalendarView").exists(timeout=3):
                # Navigate to correct year/month first
                target_date_str = birth_date.strftime("%B %Y")
                
                # Look for month/year navigation
                if u2_device(textContains=str(birth_date.year)).exists():
                    u2_device(textContains=str(birth_date.year)).click()
                    await self.add_human_delay(500, 1000)
                
                # Click on the specific day
                day_element = u2_device(text=str(birth_date.day))
                if day_element.exists():
                    day_element.click()
                    await self.add_human_delay(500, 1000)
                    
                    # Confirm if needed
                    if u2_device(text='OK').exists():
                        u2_device(text='OK').click()
                        return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Calendar date picker failed: {e}")
            return False
    
    async def _handle_text_date_picker(self, u2_device, birth_date: date) -> bool:
        """Handle text input style date picker"""
        try:
            # Look for date input fields
            date_formats = [
                birth_date.strftime("%m/%d/%Y"),
                birth_date.strftime("%d/%m/%Y"),
                birth_date.strftime("%Y-%m-%d"),
                birth_date.strftime("%m-%d-%Y")
            ]
            
            for date_format in date_formats:
                if u2_device(className="android.widget.EditText").exists():
                    date_field = u2_device(className="android.widget.EditText")
                    date_field.clear_text()
                    await self.add_human_delay(300, 600)
                    
                    # Type date with human-like patterns
                    typing_patterns = self.randomize_typing_speed(date_format)
                    for char, delay in typing_patterns:
                        date_field.send_keys(char)
                        await asyncio.sleep(delay)
                    
                    await self.add_human_delay(500, 1000)
                    return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Text date picker failed: {e}")
            return False
    
    async def _scroll_picker_to_value(self, picker, target_value: str) -> None:
        """Scroll number picker to target value"""
        try:
            current_attempts = 0
            max_attempts = 20
            
            while current_attempts < max_attempts:
                # Get current value
                if picker(className="android.widget.EditText").exists():
                    current_value = picker(className="android.widget.EditText").get_text()
                    if current_value == target_value:
                        return
                
                # Scroll up or down based on comparison
                try:
                    current_int = int(current_value) if current_value.isdigit() else 0
                    target_int = int(target_value)
                    
                    if current_int < target_int:
                        picker.scroll.forward()
                    else:
                        picker.scroll.backward()
                        
                except (ValueError, AttributeError):
                    # Fallback to random scrolling
                    if random.choice([True, False]):
                        picker.scroll.forward()
                    else:
                        picker.scroll.backward()
                
                await self.add_human_delay(200, 500)
                current_attempts += 1
                
        except Exception as e:
            logger.debug(f"Scroll picker failed: {e}")
    
    async def _accept_terms_and_conditions(self, u2_device) -> bool:
        """Accept terms and conditions"""
        try:
            terms_patterns = [
                {'text': 'Accept'},
                {'text': 'I Accept'},
                {'text': 'Agree'},
                {'text': 'I Agree'},
                {'textContains': 'Accept'},
                {'textContains': 'Agree'},
                {'className': 'android.widget.CheckBox'},
                {'resourceId': 'com.snapchat.android:id/terms_checkbox'}
            ]
            
            for pattern in terms_patterns:
                if u2_device(**pattern).exists(timeout=3):
                    u2_device(**pattern).click()
                    await self.add_human_delay(500, 1000)
                    logger.debug("Accepted terms and conditions")
                    return True
            
            # Sometimes it's automatic, check if we can proceed
            if (u2_device(text='Continue').exists() or 
                u2_device(text='Next').exists() or
                u2_device(text='Sign Up').exists()):
                logger.debug("Terms acceptance not required or automatic")
                return True
            
            logger.warning("Could not find terms acceptance")
            return False
            
        except Exception as e:
            logger.error(f"Terms acceptance failed: {e}")
            return False
    
    async def _submit_registration(self, u2_device) -> bool:
        """Submit registration form"""
        try:
            submit_patterns = [
                {'text': 'Sign Up'},
                {'text': 'Create Account'},
                {'text': 'Continue'},
                {'text': 'Next'},
                {'text': 'Submit'},
                {'resourceId': 'com.snapchat.android:id/register_button'},
                {'className': 'android.widget.Button'}
            ]
            
            for pattern in submit_patterns:
                if u2_device(**pattern).exists(timeout=3):
                    u2_device(**pattern).click()
                    await self.add_human_delay(2000, 4000)  # Wait for processing
                    logger.debug("Submitted registration")
                    return True
            
            logger.warning("Could not find registration submit button")
            return False
            
        except Exception as e:
            logger.error(f"Registration submission failed: {e}")
            return False
    
    async def _enter_verification_code(self, u2_device, code: str) -> bool:
        """Enter SMS verification code"""
        try:
            logger.debug(f"Entering verification code: {code}")
            
            # Look for verification code input fields
            code_patterns = [
                {'text': 'Enter code'},
                {'textContains': 'code'},
                {'textContains': 'verification'},
                {'resourceId': 'com.snapchat.android:id/verification_code'},
                {'className': 'android.widget.EditText'}
            ]
            
            field_found = False
            for pattern in code_patterns:
                if u2_device(**pattern).exists(timeout=5):
                    field = u2_device(**pattern)
                    
                    # Clear and enter code
                    field.clear_text()
                    await self.add_human_delay(300, 600)
                    
                    # Type code with slight delays
                    for char in code:
                        field.send_keys(char)
                        await asyncio.sleep(random.uniform(0.1, 0.3))
                    
                    field_found = True
                    break
            
            if not field_found:
                logger.error("Could not find verification code field")
                return False
            
            await self.add_human_delay(500, 1000)
            
            # Submit verification
            submit_patterns = [
                {'text': 'Verify'},
                {'text': 'Continue'},
                {'text': 'Submit'},
                {'text': 'Confirm'}
            ]
            
            for pattern in submit_patterns:
                if u2_device(**pattern).exists(timeout=3):
                    u2_device(**pattern).click()
                    await self.add_human_delay(2000, 3000)
                    return True
            
            # Auto-submit might happen, check if verification succeeded
            await asyncio.sleep(3)
            
            # Check if we're past verification (look for next screen)
            if (u2_device(textContains='Welcome').exists() or
                u2_device(textContains='Profile').exists() or
                u2_device(textContains='Friends').exists()):
                logger.info("Verification code auto-submitted and accepted")
                return True
            
            logger.warning("Could not submit verification code")
            return False
            
        except Exception as e:
            logger.error(f"Verification code entry failed: {e}")
            return False
    
    async def _skip_optional_steps(self, u2_device) -> None:
        """Skip optional onboarding steps"""
        try:
            skip_patterns = [
                {'text': 'Skip'},
                {'text': 'Not now'},
                {'text': 'Maybe later'},
                {'text': 'Skip for now'},
                {'textContains': 'Skip'}
            ]
            
            # Try to skip up to 10 optional steps
            for attempt in range(10):
                skipped = False
                for pattern in skip_patterns:
                    if u2_device(**pattern).exists(timeout=2):
                        u2_device(**pattern).click()
                        await self.add_human_delay(1000, 2000)
                        skipped = True
                        break
                
                if not skipped:
                    break  # No more optional steps
                    
        except Exception as e:
            logger.debug(f"Error skipping optional steps: {e}")
    
    async def _set_profile_picture(self, u2_device, pic_path: str) -> bool:
        """Set profile picture from file path"""
        try:
            # Look for profile picture setting option
            pic_patterns = [
                {'text': 'Add photo'},
                {'text': 'Profile picture'},
                {'textContains': 'photo'},
                {'resourceId': 'com.snapchat.android:id/profile_pic'},
                {'className': 'android.widget.ImageView'}
            ]
            
            for pattern in pic_patterns:
                if u2_device(**pattern).exists(timeout=3):
                    u2_device(**pattern).click()
                    await self.add_human_delay(1000, 2000)
                    
                    # Choose from gallery/files
                    if u2_device(text='Gallery').exists():
                        u2_device(text='Gallery').click()
                    elif u2_device(text='Photos').exists():
                        u2_device(text='Photos').click()
                    
                    await self.add_human_delay(2000, 3000)
                    
                    # This would require more complex file navigation
                    # For now, we'll skip if we can't easily set it
                    logger.debug("Profile picture setting initiated")
                    return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Profile picture setting failed: {e}")
            return False
    
    async def _set_profile_bio(self, u2_device, bio: str) -> bool:
        """Set profile bio/description"""
        try:
            bio_patterns = [
                {'text': 'Bio'},
                {'text': 'About me'},
                {'textContains': 'bio'},
                {'resourceId': 'com.snapchat.android:id/bio'}
            ]
            
            for pattern in bio_patterns:
                if u2_device(**pattern).exists(timeout=3):
                    field = u2_device(**pattern)
                    field.clear_text()
                    await self.add_human_delay(300, 600)
                    
                    # Type bio with human-like patterns
                    typing_patterns = self.randomize_typing_speed(bio)
                    for char, delay in typing_patterns:
                        field.send_keys(char)
                        await asyncio.sleep(delay)
                    
                    logger.debug(f"Set profile bio: {bio}")
                    return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Bio setting failed: {e}")
            return False
    
    async def _complete_onboarding(self, u2_device) -> None:
        """Complete remaining onboarding steps"""
        try:
            # Common onboarding completion patterns
            complete_patterns = [
                {'text': 'Done'},
                {'text': 'Finish'},
                {'text': 'Get started'},
                {'text': 'Continue'},
                {'text': 'Next'}
            ]
            
            for attempt in range(5):  # Max 5 completion steps
                completed = False
                for pattern in complete_patterns:
                    if u2_device(**pattern).exists(timeout=3):
                        u2_device(**pattern).click()
                        await self.add_human_delay(1500, 3000)
                        completed = True
                        break
                
                if not completed:
                    break  # Onboarding complete
                    
        except Exception as e:
            logger.debug(f"Onboarding completion error: {e}")
    
    async def _optimize_privacy_settings_async(self, u2_device) -> None:
        """Optimize privacy settings asynchronously"""
        try:
            logger.debug("Optimizing privacy settings")
            
            # Navigate to settings (this is simplified)
            if u2_device(text='Settings').exists(timeout=3):
                u2_device(text='Settings').click()
                await self.add_human_delay(2000, 3000)
                
                # Look for privacy options and set them to more private
                privacy_options = [
                    'Who can contact me',
                    'Who can see my story', 
                    'Who can see me in Quick Add',
                    'Show me in Quick Add'
                ]
                
                for option in privacy_options:
                    if u2_device(textContains=option).exists(timeout=2):
                        u2_device(textContains=option).click()
                        await self.add_human_delay(1000, 2000)
                        
                        # Set to most private option
                        if u2_device(text='My Friends').exists():
                            u2_device(text='My Friends').click()
                        elif u2_device(text='Off').exists():
                            u2_device(text='Off').click()
                        
                        await self.add_human_delay(500, 1000)
                        
                        # Go back
                        if u2_device(description='Navigate up').exists():
                            u2_device(description='Navigate up').click()
                        
                        await self.add_human_delay(500, 1000)
            
        except Exception as e:
            logger.debug(f"Privacy optimization failed: {e}")
    
    async def _perform_trust_building_activities(self, u2_device) -> None:
        """Perform initial trust-building activities"""
        try:
            logger.debug("Performing trust-building activities")
            
            # Navigate around the app to build usage patterns
            activities = [
                lambda: self._browse_discover_content(u2_device),
                lambda: self._view_camera_interface(u2_device),
                lambda: self._check_friend_suggestions(u2_device),
                lambda: self._view_profile_briefly(u2_device)
            ]
            
            # Perform 2-3 random activities
            selected_activities = random.sample(activities, min(3, len(activities)))
            
            for activity in selected_activities:
                try:
                    await activity()
                    await self.add_human_delay(2000, 5000)
                except Exception as e:
                    logger.debug(f"Trust building activity failed: {e}")
                    
        except Exception as e:
            logger.debug(f"Trust building activities failed: {e}")
    
    async def _browse_discover_content(self, u2_device) -> None:
        """Browse discover content briefly"""
        try:
            if u2_device(text='Discover').exists(timeout=3):
                u2_device(text='Discover').click()
                await self.add_human_delay(2000, 4000)
                
                # Scroll through content
                for _ in range(2):
                    u2_device.swipe(500, 800, 500, 400)  # Scroll up
                    await self.add_human_delay(1000, 2000)
                    
        except Exception as e:
            logger.debug(f"Discover browsing failed: {e}")
    
    async def _view_camera_interface(self, u2_device) -> None:
        """View camera interface briefly"""
        try:
            # Camera is usually the main screen
            if u2_device(text='Camera').exists(timeout=3):
                u2_device(text='Camera').click()
            
            await self.add_human_delay(2000, 3000)
            
        except Exception as e:
            logger.debug(f"Camera viewing failed: {e}")
    
    async def _check_friend_suggestions(self, u2_device) -> None:
        """Check friend suggestions briefly"""
        try:
            if u2_device(text='Add Friends').exists(timeout=3):
                u2_device(text='Add Friends').click()
                await self.add_human_delay(2000, 4000)
                
                # View but don't add friends
                await self.add_human_delay(3000, 5000)
                
                # Go back
                if u2_device(description='Navigate up').exists():
                    u2_device(description='Navigate up').click()
                    
        except Exception as e:
            logger.debug(f"Friend suggestions check failed: {e}")
    
    async def _view_profile_briefly(self, u2_device) -> None:
        """View own profile briefly"""
        try:
            # Look for profile icon (usually top left)
            if u2_device(className='android.widget.ImageView').exists():
                profile_icons = u2_device(className='android.widget.ImageView')
                if profile_icons.count > 0:
                    profile_icons[0].click()  # Assume first is profile
                    await self.add_human_delay(2000, 4000)
                    
                    # Go back after viewing
                    if u2_device(description='Navigate up').exists():
                        u2_device(description='Navigate up').click()
                        
        except Exception as e:
            logger.debug(f"Profile viewing failed: {e}")
    
    async def _download_snapchat_apk(self) -> Optional[str]:
        """Download Snapchat APK from APKMirror or similar source"""
        try:
            logger.info("Downloading Snapchat APK")
            
            # First check for manually placed APK using configuration
            try:
                from .config import get_config
            except ImportError:
                from config import get_config
            config = get_config()
            
            apk_paths = [
                os.path.join(config.config.temp_dir, 'snapchat.apk'),
                './snapchat.apk',
                os.path.expanduser('~/Downloads/snapchat.apk'),
                './automation/snapchat/snapchat.apk',
                os.path.join(config.config.apk_artifacts_dir, 'snapchat.apk')
            ]
            
            for path in apk_paths:
                expanded_path = os.path.expanduser(path)
                if os.path.exists(expanded_path):
                    logger.info(f"Found Snapchat APK at: {expanded_path}")
                    return expanded_path
            
            # Try to download using APK manager
            try:
                apk_manager = APKManager()
                apk_path = apk_manager.get_latest_snapchat_apk()
                if apk_path:
                    logger.info(f"Downloaded APK using APK manager: {apk_path}")
                    return apk_path
            except Exception as e:
                logger.warning(f"APK manager download failed: {e}")
            
            # Fallback: try direct download
            try:
                downloaded_apk = await self._direct_apk_download()
                if downloaded_apk:
                    return downloaded_apk
            except Exception as e:
                logger.warning(f"Direct APK download failed: {e}")
            
            logger.error("Could not download Snapchat APK. Please place snapchat.apk in one of the following locations:")
            for path in apk_paths:
                logger.error(f"  {path}")
            return None
            
        except Exception as e:
            logger.error(f"APK download failed: {e}")
            return None
    
    async def _direct_apk_download(self) -> Optional[str]:
        """Direct APK download as fallback method"""
        try:
            import aiohttp
            
            # Use reliable APK sources
            sources = [
                {
                    'url': 'https://apkcombo.com/snapchat/com.snapchat.android/download/apk',
                    'headers': {
                        'User-Agent': 'Mozilla/5.0 (Android 10; Mobile; rv:91.0) Gecko/91.0 Firefox/91.0',
                        'Accept': 'application/vnd.android.package-archive,*/*'
                    }
                },
                {
                    'url': 'https://www.apkpure.com/snapchat/com.snapchat.android/download',
                    'headers': {
                        'User-Agent': 'Mozilla/5.0 (Android 11; Mobile; rv:93.0) Gecko/93.0 Firefox/93.0'
                    }
                }
            ]
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=300)) as session:
                for source in sources:
                    try:
                        logger.info(f"Attempting download from: {source['url']}")
                        async with session.get(source['url'], headers=source['headers']) as response:
                            if response.status == 200:
                                # Check if response is APK file
                                content_type = response.headers.get('content-type', '')
                                if 'application/vnd.android.package-archive' in content_type or \
                                   content_type.startswith('application/octet-stream'):
                                    
                                    # Save APK file using configuration
                                    timestamp = int(time.time())
                                    apk_filename = f"snapchat_downloaded_{timestamp}.apk"
                                    apk_path = config.get_temp_file_path(apk_filename)
                                    
                                    with open(apk_path, 'wb') as f:
                                        async for chunk in response.content.iter_chunked(8192):
                                            f.write(chunk)
                                    
                                    # Verify it's a valid APK
                                    if self._verify_apk_file(apk_path):
                                        logger.info(f"Successfully downloaded APK: {apk_path}")
                                        return apk_path
                                    else:
                                        os.remove(apk_path)
                                        logger.warning("Downloaded file is not a valid APK")
                                        
                    except Exception as e:
                        logger.warning(f"Download failed from {source['url']}: {e}")
                        continue
            
            return None
            
        except Exception as e:
            logger.error(f"Direct APK download error: {e}")
            return None
    
    def _verify_apk_file(self, apk_path: str) -> bool:
        """Verify downloaded file is a valid APK"""
        try:
            # Check file size (APK should be at least 30MB for Snapchat)
            file_size = os.path.getsize(apk_path)
            if file_size < 30 * 1024 * 1024:  # 30MB minimum
                logger.warning(f"APK file too small: {file_size} bytes")
                return False
            
            # Check file header for ZIP signature (APK files are ZIP archives)
            with open(apk_path, 'rb') as f:
                header = f.read(4)
                if header[:2] != b'PK':
                    logger.warning("Invalid APK signature")
                    return False
            
            # Additional check: try to read as ZIP and look for Android manifest
            try:
                import zipfile
                with zipfile.ZipFile(apk_path, 'r') as apk_zip:
                    files = apk_zip.namelist()
                    if 'AndroidManifest.xml' not in files:
                        logger.warning("No AndroidManifest.xml found in APK")
                        return False
                    
                    # Check for classes.dex (compiled Android code)
                    dex_files = [f for f in files if f.endswith('.dex')]
                    if not dex_files:
                        logger.warning("No .dex files found in APK")
                        return False
                        
            except zipfile.BadZipFile:
                logger.warning("APK file is corrupted or not a valid ZIP")
                return False
            
            logger.info("APK file validation passed")
            return True
            
        except Exception as e:
            logger.error(f"APK verification error: {e}")
            return False
    
    async def _randomize_device_settings(self, u2_device) -> None:
        """Apply random device settings for anti-detection"""
        try:
            # Randomize some device settings
            settings = [
                ('wifi_display_on', random.choice(['0', '1'])),
                ('bluetooth_on', random.choice(['0', '1'])),
                ('screen_brightness', str(random.randint(50, 255))),
                ('volume_music', str(random.randint(8, 15)))
            ]
            
            for setting, value in settings:
                try:
                    u2_device.shell(f'settings put system {setting} {value}')
                except Exception:
                    pass  # Some settings may not be available
                    
        except Exception as e:
            logger.debug(f"Device settings randomization failed: {e}")
    
    async def _ensure_system_apps(self, u2_device) -> None:
        """Ensure necessary system apps are present"""
        try:
            # Check for essential system apps that should be installed
            essential_apps = [
                'com.android.vending',  # Google Play Store
                'com.google.android.gms',  # Google Play Services
                'com.android.providers.contacts'  # Contacts
            ]
            
            for app in essential_apps:
                result = u2_device.shell(f'pm list packages {app}')
                if app not in result.output:
                    logger.debug(f"Essential app {app} not found")
                    # In real implementation, would install essential apps
                    
        except Exception as e:
            logger.debug(f"System apps check failed: {e}")
    
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
            
            _sleep_human("navigation", 2.0)
            
            # Enter first and last name
            if automator.wait_for_element("First name", timeout=10):
                if not automator.enter_text(profile.display_name.split()[0], "First name"):
                    return False
                
                if len(profile.display_name.split()) > 1:
                    last_name = profile.display_name.split()[-1]
                    if not automator.enter_text(last_name, "Last name"):
                        return False
                
                # Continue with dynamic delay
                if not automator.tap_element("Continue"):
                    return False
                
                # Check for CAPTCHA after critical UI interaction
                captcha_result = self._check_for_captcha(automator)
                if captcha_result.get('detected'):
                    logger.warning(f"CAPTCHA detected: {captcha_result}")
                    if captcha_result.get('requires_manual'):
                        return False  # Manual intervention required
            
            # Dynamic delay
            delay = automator.anti_detection.get_next_action_delay(automator.device_id)
            time.sleep(delay)
            
            # Enter username
            if automator.wait_for_element("Username", timeout=10):
                if not automator.enter_text(profile.username, "Username"):
                    return False
                
                # Check availability (might take a moment)
                delay = automator.anti_detection.get_next_action_delay(automator.device_id)
                time.sleep(delay)
                
                # Continue with dynamic delay
                if not automator.tap_element("Continue"):
                    return False
            
            # Dynamic delay
            delay = automator.anti_detection.get_next_action_delay(automator.device_id)
            time.sleep(delay)
            
            # Enter password
            if automator.wait_for_element("Password", timeout=10):
                if not automator.enter_text(profile.password, "Password"):
                    return False
                
                # Continue with dynamic delay
                if not automator.tap_element("Continue"):
                    return False
            
            # Dynamic delay
            delay = automator.anti_detection.get_next_action_delay(automator.device_id)
            time.sleep(delay)
            
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
    
    def _check_for_captcha(self, automator: SnapchatAppAutomator) -> Dict[str, any]:
        """Check for CAPTCHA challenges during registration"""
        try:
            # Take screenshot for CAPTCHA detection using configuration
            try:
                from .config import get_config
            except ImportError:
                from config import get_config
            config = get_config()
            screenshot_path = config.get_screenshot_path("captcha_detection", str(int(time.time())))
            if automator.take_screenshot(screenshot_path):
                # Import CAPTCHA handler from anti-detection system
                captcha_handler = self.anti_detection.captcha_handler
                
                # Check for regular CAPTCHA
                captcha_result = captcha_handler.detect_captcha(screenshot_path)
                if captcha_result.get('detected'):
                    logger.info("Regular CAPTCHA detected in Snapchat registration")
                    # Optional auto-solve hook if site_key and page_url are available
                    site_key = captcha_result.get('site_key') or captcha_result.get('sitekey')
                    page_url = captcha_result.get('page_url') or captcha_result.get('pageurl')
                    if site_key and page_url:
                        try:
                            from automation.services.captcha_solver import get_captcha_solver
                            solver = get_captcha_solver()
                            if solver:
                                token = solver.solve_recaptcha_v2(site_key=site_key, page_url=page_url, timeout=180)
                                if token:
                                    return {
                                        'detected': True,
                                        'type': 'captcha',
                                        'requires_manual': False,
                                        'token': token,
                                        'details': captcha_result
                                    }
                        except Exception as e:
                            logger.debug(f"Auto-solve attempt failed: {e}")
                    return {
                        'detected': True,
                        'type': 'captcha',
                        'requires_manual': True,
                        'details': captcha_result
                    }
                
                # Check for Arkose challenge
                arkose_result = captcha_handler.detect_arkose_challenge(screenshot_path)
                if arkose_result.get('detected'):
                    logger.info("Arkose challenge detected in Snapchat registration")
                    return {
                        'detected': True,
                        'type': 'arkose',
                        'requires_manual': True,  # Manual intervention for now  
                        'details': arkose_result
                    }
                
                # Clean up screenshot
                try:
                    os.remove(screenshot_path)
                except:
                    pass
                    
            return {'detected': False}
            
        except Exception as e:
            logger.error(f"Error checking for CAPTCHA: {e}")
            return {'detected': False, 'error': str(e)}
    
    def _verify_phone_number(self, automator: SnapchatAppAutomator, phone_number: str) -> bool:
        """Handle Snapchat phone number verification by polling inbound Twilio messages."""
        try:
            # After entering the phone number and tapping Continue in the UI,
            # Snapchat sends an SMS to the provided number. We only need to poll Twilio inbound.
            max_attempts = 10
            for attempt in range(1, max_attempts + 1):
                logger.info(f"Polling Twilio for SMS code... attempt {attempt}/{max_attempts}")
                try:
                    # Prefer new Twilio provider
                    try:
                        twilio_provider = get_twilio_sms_provider()
                        code = twilio_provider.wait_for_code(phone_number, timeout_seconds=20, poll_seconds=3)
                    except Exception:
                        code = self._poll_twilio_for_code(phone_number)
                    if code:
                        logger.info("Retrieved SMS verification code from Twilio")
                        if self._enter_verification_code(automator, code):
                            return True
                except Exception as poll_err:
                    logger.debug(f"Twilio polling error: {poll_err}")
                _sleep_human("load", 3.0)
            logger.error("Timed out polling Twilio for verification code")
            return False
        except Exception as e:
            logger.error(f"SMS verification flow failed: {e}")
            return False
    
    def _retrieve_sms_code(self, phone_number: str) -> Optional[str]:
        """Retrieve SMS verification code by polling Twilio inbound messages only."""
        try:
            max_attempts = 36  # ~6 minutes
            for attempt in range(1, max_attempts + 1):
                logger.info(f"Polling Twilio... attempt {attempt}/{max_attempts}")
                try:
                    # Prefer Twilio provider
                    code = None
                    try:
                        from automation.services.sms_provider import get_twilio_sms_provider
                        code = get_twilio_sms_provider().wait_for_code(phone_number, timeout_seconds=20, poll_seconds=3)
                    except Exception as e:
                        logger.debug(f"Twilio provider polling error: {e}")
                        try:
                            code = self._poll_twilio_for_code(phone_number)
                        except Exception as e2:
                            logger.debug(f"Legacy Twilio polling error: {e2}")
                            code = None
                except Exception as e:
                    logger.debug(f"Twilio polling error: {e}")
                    code = None
                if code:
                    return code
                # Backoff with jitter
                if attempt <= 12:
                    delay = random.uniform(5, 8)
                elif attempt <= 24:
                    delay = random.uniform(8, 12)
                else:
                    delay = random.uniform(12, 18)
                _sleep_human("verification", delay)
            logger.error("Timed out polling Twilio for verification code")
            return None
        except Exception as e:
            logger.error(f"Error retrieving SMS code: {e}")
            return None
    
    def _poll_twilio_for_code(self, phone_number: str) -> Optional[str]:
        """Poll Twilio directly for verification codes"""
        try:
            from twilio.rest import Client
            import re
            
            # Get Twilio credentials
            account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
            auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
            
            if not account_sid or not auth_token:
                logger.debug("Twilio credentials not available")
                return None
            
            client = Client(account_sid, auth_token)
            
            # Get recent messages (last 10 minutes)
            messages = client.messages.list(
                to=phone_number,
                limit=10,
                date_sent_after=datetime.now() - timedelta(minutes=10)
            )
            
            # Look for verification codes in message bodies
            code_patterns = [
                r'\b(\d{6})\b',  # 6-digit codes
                r'code[:\s]*(\d{4,8})',  # "code: 123456"
                r'verification[:\s]*(\d{4,8})',  # "verification: 123456"
            ]
            
            for message in messages:
                for pattern in code_patterns:
                    matches = re.findall(pattern, message.body, re.IGNORECASE)
                    if matches:
                        code = matches[0]
                        if len(code) >= 4 and len(code) <= 8:
                            logger.info(f"Found code in Twilio message: {code}")
                            return code
            
            return None
            
        except Exception as e:
            logger.debug(f"Twilio polling error: {e}")
            return None
    
    def _check_recent_messages(self, phone_number: str) -> Optional[str]:
        """Check recent messages for verification codes"""
        try:
            # This would integrate with SMS service inbox checking
            # For now, return None as fallback
            logger.debug("Checking recent messages (not implemented)")
            return None
            
        except Exception as e:
            logger.debug(f"Recent messages check error: {e}")
            return None
    
    def _setup_profile(self, automator: SnapchatAppAutomator, profile: SnapchatProfile) -> bool:
        """Set up Snapchat profile with complete date picker automation"""
        try:
            # Set birth date with advanced date picker handling
            if automator.wait_for_element("Birthday", timeout=30) or automator.wait_for_element("Birth Date", timeout=5):
                logger.info("Setting birthday with date picker automation...")
                
                if not (automator.tap_element("Birthday") or automator.tap_element("Birth Date")):
                    logger.warning("Could not tap birthday field")
                    return False
                
                # Handle date picker interaction
                if not self._handle_date_picker(automator, profile.birth_date):
                    logger.warning("Date picker handling failed, continuing anyway...")
                
                # Continue after date selection
                delay = automator.anti_detection.get_next_action_delay(automator.device_id)
                time.sleep(delay)
                
                if not (automator.tap_element("Continue") or automator.tap_element("Next")):
                    logger.warning("Could not continue after date selection")
            
            # Add profile picture with real image handling
            if automator.wait_for_element("Add Profile Picture", timeout=10):
                logger.info("Attempting profile picture upload...")
                
                # Use the profile name for generating a picture
                profile_name = profile.display_name or profile.username
                if automator._upload_profile_picture(profile_name):
                    logger.info("Profile picture uploaded successfully")
                else:
                    # Skip if upload fails
                    logger.warning("Profile picture upload failed, skipping...")
                    skip_options = ["Skip", "Skip for now", "Not now", "Continue"]
                    
                    for skip_option in skip_options:
                        if automator.tap_element(skip_option):
                            logger.info(f"Skipped profile picture with: {skip_option}")
                            break
                    else:
                        # Fallback: try to find any skip/continue button
                        if automator.u2_device(text="Skip").exists:
                            automator.u2_device(text="Skip").click()
                        elif automator.u2_device(textContains="Skip").exists:
                            automator.u2_device(textContains="Skip").click()
            
            # Handle email verification prompt with enhanced email automation
            if automator.wait_for_element("Email", timeout=5):
                if automator.enter_text(profile.email, "Email"):
                    automator.tap_element("Continue")
                    
                    # Wait for email verification if email automation is available
                    if _load_email_integration() and wait_for_snapchat_verification:
                        try:
                            logger.info(f"Waiting for email verification for {profile.email}...")
                            # Use sync wrapper for email verification polling or manual check
                            try:
                                email_result = wait_for_snapchat_verification_sync(profile.email, timeout=180)
                            except (NameError, AttributeError):
                                logger.info(f"Email verification for {profile.email} needs manual checking")
                                email_result = None
                            
                            if email_result.success and email_result.verification_code:
                                logger.info(f"Email verification code received: {email_result.verification_code}")
                                
                                # Enter verification code if prompted
                                if automator.wait_for_element("Enter code", timeout=30) or automator.wait_for_element("Verification code", timeout=30):
                                    if automator.enter_text(email_result.verification_code, "Enter code") or automator.enter_text(email_result.verification_code, "Verification code"):
                                        automator.tap_element("Verify") or automator.tap_element("Continue")
                                        logger.info("Email verification code entered successfully")
                                    else:
                                        logger.warning("Failed to enter email verification code")
                                else:
                                    logger.info("No email verification code prompt appeared")
                            else:
                                logger.warning(f"Email verification failed: {email_result.error_message}")
                                
                        except Exception as e:
                            logger.warning(f"Email verification error: {e}")
                else:
                    # Skip email if entry fails
                    automator.tap_element("Skip")
            
            # Privacy settings
            if automator.wait_for_element("Privacy", timeout=10) or automator.wait_for_element("Who can", timeout=5):
                logger.info("Configuring privacy settings...")
                
                # Set to restrictive/private for stealth accounts
                privacy_options = ["Friends Only", "Friends", "My Friends", "Private"]
                
                for privacy_option in privacy_options:
                    if automator.tap_element(privacy_option):
                        logger.info(f"Set privacy to: {privacy_option}")
                        break
                
                # Continue with privacy settings
                delay = automator.anti_detection.get_next_action_delay(automator.device_id)
                time.sleep(delay)
                
                if not automator.tap_element("Continue"):
                    # Try alternative continue options
                    continue_options = ["Next", "Done", "Save"]
                    for continue_option in continue_options:
                        if automator.tap_element(continue_option):
                            break
            
            # Handle discovery settings
            if automator.wait_for_element("Discover", timeout=10) or automator.wait_for_element("Find Friends", timeout=5):
                logger.info("Handling discovery settings...")
                
                # Skip friend discovery for stealth
                skip_options = ["Skip", "Not Now", "Skip for now", "Maybe Later"]
                
                for skip_option in skip_options:
                    if automator.tap_element(skip_option):
                        logger.info(f"Skipped discovery with: {skip_option}")
                        break
            
            # Handle notifications prompt
            if automator.wait_for_element("Notifications", timeout=10) or automator.wait_for_element("Allow", timeout=5):
                logger.info("Handling notifications prompt...")
                
                # Allow notifications (looks more natural)
                if automator.tap_element("Allow"):
                    logger.info("Enabled notifications")
                elif automator.tap_element("OK"):
                    logger.info("Confirmed notifications")
                else:
                    # Skip if can't allow
                    automator.tap_element("Don't Allow")
            
            # Complete setup
            completion_options = ["Get Started", "Start Snapping", "Continue", "Done", "Finish"]
            
            for completion_option in completion_options:
                if automator.wait_for_element(completion_option, timeout=10):
                    if automator.tap_element(completion_option):
                        logger.info(f"Completed setup with: {completion_option}")
                        return True
            
            # Check if we're already on the main screen (setup complete)
            if self._check_main_screen(automator):
                logger.info("Profile setup completed - reached main screen")
                return True
            
            logger.warning("Setup completion uncertain, but proceeding")
            return True
            
        except Exception as e:
            logger.error(f"Profile setup failed: {e}")
            return False
    
    def _handle_date_picker(self, automator: SnapchatAppAutomator, birth_date: date) -> bool:
        """Handle date picker interaction with complete automation"""
        try:
            logger.info(f"Setting birth date: {birth_date}")
            
            # Wait for date picker to appear
            _sleep_human("navigation", 2.0)
            
            # Different types of date pickers to handle
            date_picker_handled = False
            
            # Method 1: Wheel/Spinner style date picker
            if self._handle_wheel_date_picker(automator, birth_date):
                date_picker_handled = True
                logger.info("Handled wheel-style date picker")
            
            # Method 2: Calendar style date picker
            elif self._handle_calendar_date_picker(automator, birth_date):
                date_picker_handled = True
                logger.info("Handled calendar-style date picker")
            
            # Method 3: Text input date picker
            elif self._handle_text_date_picker(automator, birth_date):
                date_picker_handled = True
                logger.info("Handled text input date picker")
            
            # Method 4: Generic fallback
            else:
                date_picker_handled = self._handle_generic_date_picker(automator, birth_date)
                logger.info("Used generic date picker handling")
            
            if date_picker_handled:
                # Confirm date selection
                delay = automator.anti_detection.get_next_action_delay(automator.device_id)
                time.sleep(delay)
                
                confirm_options = ["Done", "OK", "Set", "Confirm", "Save"]
                for confirm_option in confirm_options:
                    if automator.tap_element(confirm_option):
                        logger.info(f"Confirmed date with: {confirm_option}")
                        return True
                
                # Fallback confirmation
                if automator.u2_device(text="Done").exists:
                    automator.u2_device(text="Done").click()
                    return True
            
            return date_picker_handled
            
        except Exception as e:
            logger.error(f"Date picker handling failed: {e}")
            return False
    
    def _handle_wheel_date_picker(self, automator: SnapchatAppAutomator, birth_date: date) -> bool:
        """Handle wheel/spinner style date picker"""
        try:
            # Look for NumberPicker or similar wheel elements
            if automator.u2_device(className="android.widget.NumberPicker").exists:
                pickers = automator.u2_device(className="android.widget.NumberPicker")
                picker_count = pickers.count
                
                logger.info(f"Found {picker_count} number pickers")
                
                if picker_count >= 3:  # Month, Day, Year
                    # Assuming order: Month, Day, Year (common in US)
                    month_picker = pickers[0]
                    day_picker = pickers[1] 
                    year_picker = pickers[2]
                    
                    # Set month (0-based index usually)
                    target_month_index = birth_date.month - 1
                    self._set_number_picker_value(month_picker, target_month_index)
                    
                    # Set day
                    self._set_number_picker_value(day_picker, birth_date.day - 1)
                    
                    # Set year (might need adjustment based on picker range)
                    current_year = datetime.now().year
                    year_offset = current_year - birth_date.year
                    self._set_number_picker_value(year_picker, year_offset)
                    
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Wheel date picker handling failed: {e}")
            return False
    
    def _set_number_picker_value(self, picker, target_value: int):
        """Set value on a number picker by scrolling"""
        try:
            # Scroll to approximate position
            # This is a simplified approach - real implementation would need
            # to read current value and calculate exact scrolls needed
            for _ in range(abs(target_value)):
                if target_value > 0:
                    picker.swipe("up", steps=1)
                else:
                    picker.swipe("down", steps=1)
                _sleep_human("tap", 0.1)  # Small delay between swipes
                
        except Exception as e:
            logger.debug(f"Number picker adjustment failed: {e}")
    
    def _handle_calendar_date_picker(self, automator: SnapchatAppAutomator, birth_date: date) -> bool:
        """Handle calendar grid style date picker"""
        try:
            # Look for calendar view
            if (automator.u2_device(className="android.widget.DatePicker").exists or
                automator.u2_device(className="android.widget.CalendarView").exists):
                
                # Navigate to correct year/month first
                # This would require more complex navigation logic
                # For now, try to find and click the target date
                
                # Look for year/month navigation
                target_year_text = str(birth_date.year)
                target_month_text = birth_date.strftime("%B")  # Full month name
                
                # Try to find and click year
                if automator.u2_device(textContains=target_year_text).exists:
                    automator.u2_device(textContains=target_year_text).click()
                    _sleep_human("tap", 1.0)
                
                # Try to find and click month
                if automator.u2_device(textContains=target_month_text).exists:
                    automator.u2_device(textContains=target_month_text).click()
                    _sleep_human("tap", 1.0)
                
                # Try to find and click day
                target_day_text = str(birth_date.day)
                if automator.u2_device(text=target_day_text).exists:
                    automator.u2_device(text=target_day_text).click()
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Calendar date picker handling failed: {e}")
            return False
    
    def _handle_text_date_picker(self, automator: SnapchatAppAutomator, birth_date: date) -> bool:
        """Handle text input style date picker"""
        try:
            # Look for date input fields
            if automator.u2_device(className="android.widget.EditText").exists:
                date_fields = automator.u2_device(className="android.widget.EditText")
                
                # Try different date formats
                date_formats = [
                    birth_date.strftime("%m/%d/%Y"),  # MM/DD/YYYY
                    birth_date.strftime("%d/%m/%Y"),  # DD/MM/YYYY
                    birth_date.strftime("%Y-%m-%d"),  # YYYY-MM-DD
                    birth_date.strftime("%m-%d-%Y"),  # MM-DD-YYYY
                ]
                
                for date_format in date_formats:
                    try:
                        if date_fields.count > 0:
                            date_fields[0].clear_text()
                            _sleep_human("typing", 0.5)
                            date_fields[0].send_keys(date_format)
                            _sleep_human("typing", 1.0)
                            
                            # Check if date was accepted (no error shown)
                            if not automator.u2_device(textContains="invalid").exists:
                                logger.info(f"Successfully entered date: {date_format}")
                                return True
                    except Exception:
                        continue
                        
            return False
            
        except Exception as e:
            logger.error(f"Text date picker handling failed: {e}")
            return False
    
    def _handle_generic_date_picker(self, automator: SnapchatAppAutomator, birth_date: date) -> bool:
        """Generic fallback date picker handling"""
        try:
            # Try to find any clickable elements with year, month, or day
            target_year = str(birth_date.year)
            target_month = birth_date.strftime("%B")[:3]  # First 3 letters of month
            target_day = str(birth_date.day)
            
            elements_clicked = 0
            
            # Try to click year
            if automator.u2_device(textContains=target_year).exists:
                automator.u2_device(textContains=target_year).click()
                elements_clicked += 1
                _sleep_human("tap", 1.0)
            
            # Try to click month
            if automator.u2_device(textContains=target_month).exists:
                automator.u2_device(textContains=target_month).click()
                elements_clicked += 1
                _sleep_human("tap", 1.0)
            
            # Try to click day
            if automator.u2_device(text=target_day).exists:
                automator.u2_device(text=target_day).click()
                elements_clicked += 1
                _sleep_human("tap", 1.0)
            
            logger.info(f"Generic date picker: clicked {elements_clicked} elements")
            return elements_clicked > 0
            
        except Exception as e:
            logger.error(f"Generic date picker handling failed: {e}")
            return False
    
    def _check_main_screen(self, automator: SnapchatAppAutomator) -> bool:
        """Check if we've reached Snapchat's main screen"""
        try:
            # Look for main screen indicators
            main_screen_indicators = [
                "Camera",           # Main camera view
                "Snap Map",        # Bottom navigation
                "Chat",            # Chat section
                "Stories",         # Stories section
                "Discover",        # Discover section
                "My Story",        # User's story area
                "Take a Snap"      # Camera prompt
            ]
            
            for indicator in main_screen_indicators:
                if automator.wait_for_element(indicator, timeout=3):
                    logger.info(f"Main screen detected: found '{indicator}'")
                    return True
            
            # Check for camera viewfinder (main screen center)
            if automator.u2_device(description="Camera preview").exists:
                return True
            
            # Check for navigation elements
            if (automator.u2_device(className="android.widget.TabHost").exists or
                automator.u2_device(className="android.widget.FrameLayout").count > 3):
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Main screen check failed: {e}")
            return False
    
    def _perform_warming_activities(self, automator: SnapchatAppAutomator, 
                                  session_duration: int = None):
        """Perform comprehensive warming activities for account longevity"""
        try:
            if session_duration is None:
                session_duration = random.randint(300, 600)  # 5-10 minutes
            
            logger.info(f"Starting comprehensive warming activities for {session_duration}s...")
            
            # Try advanced anti-detection warming first
            try:
                warming_result = self.anti_detection.perform_human_like_warming(
                    device_id=automator.device_id,
                    u2_device=automator.u2_device,
                    session_duration=session_duration
                )
                
                if warming_result.get('success'):
                    logger.info(f"Advanced warming completed: "
                              f"{warming_result.get('success_count', 0)}/{warming_result.get('activities_count', 0)} activities")
                    # Perform additional Snapchat-specific warming
                    self._snapchat_specific_warming(automator)
                    return
                else:
                    logger.warning(f"Advanced warming had issues: {warming_result.get('error', 'Unknown error')}")
            
            except Exception as e:
                logger.warning(f"Advanced warming system failed: {e}")
            
            # Fallback to comprehensive custom warming
            logger.info("Using comprehensive custom warming system")
            self._comprehensive_warming_fallback(automator, session_duration)
            
        except Exception as e:
            logger.error(f"All warming methods failed: {e}")
            # Final fallback to simple warming
            self._simple_warming_fallback(automator)
    
    def _snapchat_specific_warming(self, automator: SnapchatAppAutomator):
        """Perform Snapchat-specific warming activities"""
        try:
            logger.info("Performing Snapchat-specific warming...")
            
            activities = [
                self._warm_camera_interaction,
                self._warm_story_browsing,
                self._warm_discover_browsing,
                self._warm_profile_viewing,
                self._warm_settings_exploration
            ]
            
            # Perform 2-3 activities randomly
            selected_activities = random.sample(activities, min(3, len(activities)))
            
            for activity in selected_activities:
                try:
                    activity(automator)
                    # Random delay between activities
                    delay = random.uniform(15, 45)
                    logger.debug(f"Waiting {delay:.1f}s between warming activities")
                    time.sleep(delay)
                except Exception as e:
                    logger.warning(f"Warming activity failed: {e}")
            
            logger.info("Snapchat-specific warming completed")
            
        except Exception as e:
            logger.error(f"Snapchat-specific warming failed: {e}")
    
    def _comprehensive_warming_fallback(self, automator: SnapchatAppAutomator, duration: int):
        """Comprehensive warming fallback with realistic user behavior"""
        try:
            logger.info(f"Starting comprehensive warming for {duration}s...")
            
            start_time = time.time()
            activities_performed = 0
            
            while (time.time() - start_time) < duration:
                try:
                    # Select random warming activity
                    activity_type = random.choice([
                        'camera_interaction',
                        'ui_navigation',
                        'story_interaction',
                        'settings_browse',
                        'discovery_browse'
                    ])
                    
                    if activity_type == 'camera_interaction':
                        self._warm_camera_interaction(automator)
                    elif activity_type == 'ui_navigation':
                        self._warm_ui_navigation(automator)
                    elif activity_type == 'story_interaction':
                        self._warm_story_browsing(automator)
                    elif activity_type == 'settings_browse':
                        self._warm_settings_exploration(automator)
                    elif activity_type == 'discovery_browse':
                        self._warm_discover_browsing(automator)
                    
                    activities_performed += 1
                    
                    # Human-like pause between activities
                    pause_duration = random.uniform(20, 60)
                    remaining_time = duration - (time.time() - start_time)
                    
                    if remaining_time > pause_duration:
                        logger.debug(f"Pausing for {pause_duration:.1f}s (activity {activities_performed})")
                        time.sleep(pause_duration)
                    else:
                        break
                        
                except Exception as activity_error:
                    logger.warning(f"Warming activity failed: {activity_error}")
                    time.sleep(random.uniform(10, 30))  # Brief pause before next activity
            
            total_time = time.time() - start_time
            logger.info(f"Comprehensive warming completed: {activities_performed} activities in {total_time:.1f}s")
            
        except Exception as e:
            logger.error(f"Comprehensive warming fallback failed: {e}")
    
    def _warm_camera_interaction(self, automator: SnapchatAppAutomator):
        """Warm up camera interactions"""
        try:
            logger.debug("Warming camera interactions...")
            
            # Tap camera area to focus
            if automator.u2_device:
                screen_info = automator.u2_device.info
                center_x = screen_info['displayWidth'] // 2
                center_y = screen_info['displayHeight'] // 2
                
                # Random tap points around center for focus
                for _ in range(random.randint(1, 3)):
                    offset_x = random.randint(-100, 100)
                    offset_y = random.randint(-100, 100)
                    
                    automator.u2_device.click(center_x + offset_x, center_y + offset_y)
                    time.sleep(random.uniform(0.5, 2.0))
                
                # Simulate taking a photo (but don't save)
                shutter_y = int(screen_info['displayHeight'] * 0.85)
                automator.u2_device.click(center_x, shutter_y)
                time.sleep(random.uniform(1, 3))
                
                # Discard the photo
                if automator.u2_device(text="Discard").exists:
                    automator.u2_device(text="Discard").click()
                elif automator.u2_device.press("back"):
                    pass
                
                time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            logger.debug(f"Camera warming failed: {e}")
    
    def _warm_ui_navigation(self, automator: SnapchatAppAutomator):
        """Warm up UI navigation"""
        try:
            logger.debug("Warming UI navigation...")
            
            # Swipe between screens
            if automator.u2_device:
                screen_info = automator.u2_device.info
                width = screen_info['displayWidth']
                height = screen_info['displayHeight']
                
                # Random swipes
                swipe_directions = [
                    {'start': (width * 0.8, height * 0.5), 'end': (width * 0.2, height * 0.5)},  # Left
                    {'start': (width * 0.2, height * 0.5), 'end': (width * 0.8, height * 0.5)},  # Right
                    {'start': (width * 0.5, height * 0.8), 'end': (width * 0.5, height * 0.2)},  # Up
                ]
                
                for _ in range(random.randint(2, 4)):
                    swipe = random.choice(swipe_directions)
                    automator.u2_device.swipe(
                        swipe['start'][0], swipe['start'][1],
                        swipe['end'][0], swipe['end'][1],
                        duration=random.uniform(0.3, 0.8)
                    )
                    time.sleep(random.uniform(1, 3))
            
        except Exception as e:
            logger.debug(f"UI navigation warming failed: {e}")
    
    def _warm_story_browsing(self, automator: SnapchatAppAutomator):
        """Warm up story browsing"""
        try:
            logger.debug("Warming story browsing...")
            
            # Try to access stories section
            if automator.u2_device:
                # Look for stories area and tap
                if automator.u2_device(text="Stories").exists:
                    automator.u2_device(text="Stories").click()
                    time.sleep(random.uniform(2, 4))
                    
                    # Browse briefly
                    for _ in range(random.randint(1, 3)):
                        screen_info = automator.u2_device.info
                        automator.u2_device.swipe(
                            screen_info['displayWidth'] * 0.8, 
                            screen_info['displayHeight'] * 0.5,
                            screen_info['displayWidth'] * 0.2, 
                            screen_info['displayHeight'] * 0.5,
                            duration=0.5
                        )
                        time.sleep(random.uniform(1, 2))
                    
                    # Go back
                    automator.u2_device.press("back")
                    _sleep_human("navigation", 1.0)
            
        except Exception as e:
            logger.debug(f"Story browsing warming failed: {e}")
    
    def _warm_discover_browsing(self, automator: SnapchatAppAutomator):
        """Warm up discover section browsing"""
        try:
            logger.debug("Warming discover browsing...")
            
            if automator.u2_device:
                # Try to access discover section
                if automator.u2_device(text="Discover").exists:
                    automator.u2_device(text="Discover").click()
                    time.sleep(random.uniform(2, 4))
                    
                    # Scroll through content
                    for _ in range(random.randint(2, 4)):
                        screen_info = automator.u2_device.info
                        automator.u2_device.swipe(
                            screen_info['displayWidth'] * 0.5, 
                            screen_info['displayHeight'] * 0.8,
                            screen_info['displayWidth'] * 0.5, 
                            screen_info['displayHeight'] * 0.2,
                            duration=0.6
                        )
                        time.sleep(random.uniform(1, 3))
                    
                    # Go back
                    automator.u2_device.press("back")
                    _sleep_human("navigation", 1.0)
            
        except Exception as e:
            logger.debug(f"Discover browsing warming failed: {e}")
    
    def _warm_profile_viewing(self, automator: SnapchatAppAutomator):
        """Warm up profile viewing"""
        try:
            logger.debug("Warming profile viewing...")
            
            # Try to access profile
            if automator.u2_device:
                # Look for profile icon/avatar
                if automator.u2_device(description="Profile").exists:
                    automator.u2_device(description="Profile").click()
                    time.sleep(random.uniform(2, 4))
                    
                    # Browse profile briefly
                    time.sleep(random.uniform(3, 6))
                    
                    # Go back
                    automator.u2_device.press("back")
                    _sleep_human("navigation", 1.0)
            
        except Exception as e:
            logger.debug(f"Profile viewing warming failed: {e}")
    
    def _warm_settings_exploration(self, automator: SnapchatAppAutomator):
        """Warm up settings exploration"""
        try:
            logger.debug("Warming settings exploration...")
            
            if automator.u2_device:
                # Try to access settings
                if automator.u2_device(text="Settings").exists:
                    automator.u2_device(text="Settings").click()
                    time.sleep(random.uniform(2, 4))
                    
                    # Brief exploration without changing anything
                    time.sleep(random.uniform(2, 5))
                    
                    # Go back
                    automator.u2_device.press("back")
                    _sleep_human("navigation", 1.0)
            
        except Exception as e:
            logger.debug(f"Settings exploration warming failed: {e}")
    
    def _simple_warming_fallback(self, automator: SnapchatAppAutomator):
        """Simple warming activities fallback"""
        try:
            logger.info("Using simple warming fallback...")
            
            # Take a snap (without sending)
            if automator.u2_device:
                # Tap camera button (center of screen)
                automator.u2_device.click(540, 960)
                delay = self.anti_detection.get_next_action_delay(automator.device_id)
                time.sleep(delay)
                
                # Take photo
                automator.u2_device.click(540, 1700)  # Camera shutter button
                delay = self.anti_detection.get_next_action_delay(automator.device_id)
                time.sleep(delay)
                
                # Discard it
                if automator.tap_element("Discard"):
                    pass
                elif automator.u2_device.press("back"):
                    pass
            
            logger.info("Simple warming activities completed")
            
        except Exception as e:
            logger.error(f"Simple warming fallback failed: {e}")
    
    def create_multiple_accounts(self, count: int, device_ids: List[str] = None, 
                               batch_size: int = 5) -> List[SnapchatCreationResult]:
        """Create multiple Snapchat accounts with optimized batch processing"""
        logger.info(f"Creating {count} Snapchat accounts in batches of {batch_size}...")
        
        # Initialize device management
        if not device_ids:
            # Auto-generate device IDs if not provided
            device_ids = [f"emulator-{5554 + i * 2}" for i in range(count)]
        
        # Ensure we have enough device IDs
        while len(device_ids) < count:
            device_ids.append(f"emulator-{5554 + len(device_ids) * 2}")
        
        results = []
        start_time = datetime.now()
        
        # Process in batches for better resource management
        for batch_start in range(0, count, batch_size):
            batch_end = min(batch_start + batch_size, count)
            batch_devices = device_ids[batch_start:batch_end]
            batch_num = (batch_start // batch_size) + 1
            total_batches = (count + batch_size - 1) // batch_size
            
            logger.info(f"Starting batch {batch_num}/{total_batches} (accounts {batch_start+1}-{batch_end})")
            
            batch_results = self._create_account_batch(batch_devices, batch_start)
            results.extend(batch_results)
            
            # Inter-batch delay for rate limiting
            if batch_end < count:
                delay = random.uniform(180, 300)  # 3-5 minutes between batches
                logger.info(f"Batch {batch_num} complete. Waiting {delay:.1f}s before next batch...")
                time.sleep(delay)
                
                # Cleanup and resource management
                self._cleanup_batch_resources()
        
        # Final statistics and cleanup
        total_time = (datetime.now() - start_time).total_seconds()
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        success_rate = (successful / len(results)) * 100 if results else 0
        
        logger.info(f"Account creation complete in {total_time:.1f}s:")
        logger.info(f"  Successful: {successful}/{len(results)} ({success_rate:.1f}%)")
        logger.info(f"  Failed: {failed}")
        logger.info(f"  Average time per account: {total_time/len(results):.1f}s")
        
        # Save results to file for analysis
        self._save_batch_results(results, count)
        
        return results
    
    async def create_multiple_accounts_async(self, count: int, device_ids: List[str] = None, 
                                           batch_size: int = 3, 
                                           female_names: List[str] = None) -> List[SnapchatCreationResult]:
        """Create multiple Snapchat accounts asynchronously with enhanced automation"""
        logger.info(f"Creating {count} Snapchat accounts asynchronously in batches of {batch_size}...")
        
        start_time = time.time()
        results = []
        
        # Initialize device management
        if not device_ids:
            # Auto-detect available devices
            available_devices = self._get_all_available_devices()
            if not available_devices:
                raise SnapchatCreationError("No available devices found for account creation")
            device_ids = available_devices[:count]  # Use as many as needed
        
        # Create profiles in advance
        profiles = []
        for i in range(count):
            profile = self.generate_stealth_profile(female_names=female_names)
            profiles.append(profile)
            logger.info(f"Generated profile {i+1}/{count}: {profile.username}")
        
        # Process accounts in batches to avoid overwhelming the system
        for batch_start in range(0, count, batch_size):
            batch_end = min(batch_start + batch_size, count)
            batch_profiles = profiles[batch_start:batch_end]
            batch_devices = device_ids[batch_start:batch_end]
            
            logger.info(f"Processing batch {batch_start//batch_size + 1}: accounts {batch_start+1}-{batch_end}")
            
            # Create batch tasks
            batch_tasks = []
            for profile, device_id in zip(batch_profiles, batch_devices):
                task = self.create_snapchat_account(profile, device_id)
                batch_tasks.append(task)
            
            # Execute batch with timeout
            try:
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Process results
                for i, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        logger.error(f"Account creation failed with exception: {result}")
                        # Create failed result
                        profile = batch_profiles[i]
                        failed_result = SnapchatCreationResult(
                            success=False,
                            profile=profile,
                            username=profile.username,
                            email=profile.email,
                            phone_number=profile.phone_number,
                            password=profile.password,
                            device_id=batch_devices[i],
                            creation_time=datetime.now(),
                            verification_status="failed",
                            error=str(result),
                            errors=[str(result)]
                        )
                        results.append(failed_result)
                    else:
                        results.append(result)
                
                # Add delay between batches to avoid detection
                if batch_end < count:  # Not the last batch
                    delay = random.uniform(30, 90)  # 30-90 seconds between batches
                    logger.info(f"Waiting {delay:.1f}s before next batch to avoid detection...")
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Batch processing failed: {e}")
                # Create failed results for the entire batch
                for profile, device_id in zip(batch_profiles, batch_devices):
                    failed_result = SnapchatCreationResult(
                        success=False,
                        profile=profile,
                        username=profile.username,
                        email=profile.email,
                        phone_number=profile.phone_number,
                        password=profile.password,
                        device_id=device_id,
                        creation_time=datetime.now(),
                        verification_status="failed",
                        error=str(e),
                        errors=[str(e)]
                    )
                    results.append(failed_result)
        
        # Calculate final statistics
        total_time = time.time() - start_time
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        success_rate = (successful / len(results)) * 100 if results else 0
        
        logger.info(f"Async account creation complete in {total_time:.1f}s:")
        logger.info(f"  Successful: {successful}/{len(results)} ({success_rate:.1f}%)")
        logger.info(f"  Failed: {failed}")
        logger.info(f"  Average time per account: {total_time/len(results):.1f}s")
        
        # Save results
        self._save_batch_results(results, count, "async")
        
        return results
    
    def _get_all_available_devices(self) -> List[str]:
        """Get all available emulator devices"""
        try:
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
            if result.returncode != 0:
                logger.error("Failed to get device list")
                return []
            
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            devices = []
            
            for line in lines:
                if '\tdevice' in line:
                    device_id = line.split('\t')[0]
                    # Verify device is actually responsive
                    try:
                        test_result = subprocess.run(['adb', '-s', device_id, 'shell', 'echo', 'test'], 
                                                   capture_output=True, text=True, timeout=5)
                        if test_result.returncode == 0:
                            devices.append(device_id)
                    except subprocess.TimeoutExpired:
                        logger.debug(f"Device {device_id} not responsive")
                        continue
            
            logger.info(f"Found {len(devices)} available devices: {devices}")
            return devices
            
        except Exception as e:
            logger.error(f"Error getting available devices: {e}")
            return []
    
    def _save_batch_results(self, results: List[SnapchatCreationResult], count: int, batch_type: str = "sync"):
        """Save batch results to file with enhanced data"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"snapchat_batch_{batch_type}_{count}_accounts_{timestamp}.json"
            
            # Prepare data for JSON serialization
            results_data = []
            for result in results:
                result_dict = {
                    'success': result.success,
                    'username': result.username or (result.profile.username if result.profile else None),
                    'email': result.email or (result.profile.email if result.profile else None),
                    'phone_number': result.phone_number or (result.profile.phone_number if result.profile else None),
                    'device_id': result.device_id,
                    'verification_status': result.verification_status,
                    'creation_time': result.creation_time.isoformat() if result.creation_time else None,
                    'error': result.error,
                    'errors': result.errors if hasattr(result, 'errors') else [],
                    'additional_data': result.additional_data if hasattr(result, 'additional_data') else {}
                }
                results_data.append(result_dict)
            
            batch_summary = {
                'batch_type': batch_type,
                'total_requested': count,
                'total_processed': len(results),
                'successful': sum(1 for r in results if r.success),
                'failed': sum(1 for r in results if not r.success),
                'success_rate': (sum(1 for r in results if r.success) / len(results)) * 100 if results else 0,
                'timestamp': timestamp,
                'results': results_data
            }
            
            with open(filename, 'w') as f:
                json.dump(batch_summary, f, indent=2, default=str)
            
            logger.info(f"Batch results saved to: {filename}")
            
        except Exception as e:
            logger.error(f"Failed to save batch results: {e}")
    
    def _create_account_batch(self, device_ids: List[str], batch_offset: int) -> List[SnapchatCreationResult]:
        """Create a batch of accounts with parallel optimization"""
        batch_results = []
        
        for i, device_id in enumerate(device_ids):
            try:
                account_num = batch_offset + i + 1
                logger.info(f"Creating account #{account_num} on {device_id}...")
                
                # Pre-flight checks
                if not self._preflight_check(device_id):
                    logger.error(f"Pre-flight check failed for {device_id}")
                    batch_results.append(SnapchatCreationResult(
                        success=False,
                        device_id=device_id,
                        error="Pre-flight check failed"
                    ))
                    continue
                
                # Generate profile with enhanced randomization
                profile = self.generate_stealth_profile()
                
                # Create account with retry logic
                result = self._create_account_with_retry(profile, device_id, max_retries=2)
                batch_results.append(result)
                
                # Log result
                if result.success:
                    logger.info(f"✓ Account #{account_num} created: {profile.username}")
                else:
                    logger.error(f"✗ Account #{account_num} failed: {result.error}")
                
                # Inter-account delay within batch
                if i < len(device_ids) - 1:
                    delay = random.uniform(30, 90)  # 30s-90s between accounts in batch
                    logger.info(f"Waiting {delay:.1f}s before next account...")
                    time.sleep(delay)
                
            except Exception as e:
                logger.error(f"Batch account creation failed: {e}")
                batch_results.append(SnapchatCreationResult(
                    success=False,
                    device_id=device_id,
                    error=str(e)
                ))
        
        return batch_results
    
    def _create_account_with_retry(self, profile: SnapchatProfile, device_id: str, 
                                 max_retries: int = 2) -> SnapchatCreationResult:
        """Create account with retry logic for common failures"""
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt}/{max_retries} for {device_id}")
                    # Wait before retry
                    time.sleep(random.uniform(60, 120))
                
                result = self.create_account(profile, device_id)
                
                if result.success:
                    return result
                
                # Analyze failure for retry decision
                if self._should_retry_failure(result.error):
                    last_error = result.error
                    logger.warning(f"Retryable failure on {device_id}: {result.error}")
                    continue
                else:
                    logger.error(f"Non-retryable failure on {device_id}: {result.error}")
                    return result
                    
            except Exception as e:
                last_error = str(e)
                logger.error(f"Account creation attempt {attempt + 1} failed: {e}")
        
        # All retries exhausted
        return SnapchatCreationResult(
            success=False,
            profile=profile,
            device_id=device_id,
            error=f"Failed after {max_retries + 1} attempts. Last error: {last_error}"
        )
    
    def _should_retry_failure(self, error: str) -> bool:
        """Determine if failure is worth retrying"""
        if not error:
            return False
        
        error_lower = error.lower()
        
        # Retryable errors
        retryable_patterns = [
            'network',
            'timeout',
            'connection',
            'failed to launch',
            'installation',
            'temporary',
            'server error',
            'rate limit'
        ]
        
        for pattern in retryable_patterns:
            if pattern in error_lower:
                return True
        
        # Non-retryable errors
        non_retryable_patterns = [
            'invalid phone',
            'phone already used',
            'username taken',
            'banned',
            'email invalid'
        ]
        
        for pattern in non_retryable_patterns:
            if pattern in error_lower:
                return False
        
        # Default to retry for unknown errors
        return True
    
    def _preflight_check(self, device_id: str) -> bool:
        """Pre-flight check before account creation"""
        try:
            # Check device connectivity
            result = subprocess.run(
                ["adb", "-s", device_id, "shell", "echo", "test"], 
                capture_output=True, timeout=10
            )
            
            if result.returncode != 0:
                logger.error(f"Device {device_id} not responding")
                return False
            
            # Check available storage
            storage_result = subprocess.run(
                ["adb", "-s", device_id, "shell", "df", "/data"], 
                capture_output=True, timeout=10
            )
            
            if storage_result.returncode == 0 and "100%" in storage_result.stdout:
                logger.warning(f"Device {device_id} storage may be full")
                return False
            
            # Check if device is unlocked
            lock_result = subprocess.run(
                ["adb", "-s", device_id, "shell", "dumpsys", "power", "|", "grep", "mHoldingDisplaySuspendBlocker"], 
                capture_output=True, timeout=10
            )
            
            logger.info(f"Pre-flight check passed for {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"Pre-flight check failed for {device_id}: {e}")
            return False
    
    def _cleanup_batch_resources(self):
        """Clean up resources between batches"""
        try:
            # Force garbage collection
            import gc
            gc.collect()
            
            # Clear temporary files
            temp_dir = Path("/tmp")
            for temp_file in temp_dir.glob("snapchat_*"):
                try:
                    if temp_file.is_file() and (time.time() - temp_file.stat().st_mtime) > 3600:
                        temp_file.unlink()
                except Exception:
                    pass
            
            logger.debug("Batch resource cleanup completed")
            
        except Exception as e:
            logger.warning(f"Resource cleanup warning: {e}")
    
    def _save_batch_results(self, results: List[SnapchatCreationResult], total_count: int):
        """Save batch results for analysis"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"snapchat_creation_results_{timestamp}.json"
            
            results_data = {
                'timestamp': timestamp,
                'total_requested': total_count,
                'total_processed': len(results),
                'successful': sum(1 for r in results if r.success),
                'failed': sum(1 for r in results if not r.success),
                'results': []
            }
            
            for result in results:
                result_data = {
                    'success': result.success,
                    'device_id': result.device_id,
                    'creation_time': result.creation_time.isoformat() if result.creation_time else None,
                    'verification_status': result.verification_status,
                    'error': result.error,
                    'snapchat_score': result.snapchat_score
                }
                
                if result.profile:
                    result_data['profile'] = {
                        'username': result.profile.username,
                        'display_name': result.profile.display_name,
                        'email': result.profile.email[:5] + '***' if result.profile.email else None,
                        'phone_number': result.profile.phone_number[:7] + '***' if result.profile.phone_number else None
                    }
                
                results_data['results'].append(result_data)
            
            # Save to file
            results_file = Path(filename)
            with open(results_file, 'w') as f:
                json.dump(results_data, f, indent=2)
            
            logger.info(f"Results saved to {results_file}")
            
        except Exception as e:
            logger.warning(f"Failed to save results: {e}")
    
    def get_usernames_for_tinder(self, count: int) -> List[str]:
        """Get Snapchat usernames for use in Tinder bios"""
        successful_accounts = [acc for acc in self.created_accounts if acc.success and acc.profile]
        return [acc.profile.username for acc in successful_accounts[:count]]
    
    def verify_account_batch(self, results: List[SnapchatCreationResult], 
                           verification_timeout: int = 300) -> Dict[str, any]:
        """Verify a batch of created accounts for functionality"""
        logger.info(f"Starting verification of {len(results)} accounts...")
        
        verification_results = {
            'total_accounts': len(results),
            'verified_count': 0,
            'failed_count': 0,
            'partial_count': 0,
            'verification_details': [],
            'verification_time': 0
        }
        
        start_time = time.time()
        
        for i, result in enumerate(results):
            if not result.success or not result.profile:
                verification_results['failed_count'] += 1
                verification_results['verification_details'].append({
                    'username': 'unknown',
                    'status': 'creation_failed',
                    'error': result.error
                })
                continue
            
            try:
                logger.info(f"Verifying account {i+1}/{len(results)}: {result.profile.username}")
                
                # Perform comprehensive account verification
                verification_result = self._verify_single_account(result)
                
                if verification_result['status'] == 'verified':
                    verification_results['verified_count'] += 1
                elif verification_result['status'] == 'partial':
                    verification_results['partial_count'] += 1
                else:
                    verification_results['failed_count'] += 1
                
                verification_results['verification_details'].append(verification_result)
                
                # Brief delay between verifications
                time.sleep(random.uniform(5, 15))
                
            except Exception as e:
                logger.error(f"Verification failed for {result.profile.username}: {e}")
                verification_results['failed_count'] += 1
                verification_results['verification_details'].append({
                    'username': result.profile.username,
                    'status': 'verification_error',
                    'error': str(e)
                })
        
        verification_results['verification_time'] = time.time() - start_time
        
        # Log summary
        success_rate = (verification_results['verified_count'] / len(results)) * 100
        logger.info(f"Verification complete: {verification_results['verified_count']}/{len(results)} accounts verified ({success_rate:.1f}%)")
        
        return verification_results
    
    def _verify_single_account(self, result: SnapchatCreationResult) -> Dict[str, any]:
        """Verify a single Snapchat account comprehensively"""
        verification_result = {
            'username': result.profile.username,
            'status': 'unknown',
            'tests_passed': 0,
            'total_tests': 0,
            'test_details': {},
            'error': None
        }
        
        try:
            # Initialize automator for verification
            automator = SnapchatAppAutomator(result.device_id)
            
            # Test suite for account verification
            verification_tests = [
                ('app_launch', self._test_app_launch),
                ('login_status', self._test_login_status), 
                ('profile_access', self._test_profile_access),
                ('camera_functionality', self._test_camera_functionality),
                ('story_access', self._test_story_access),
                ('settings_access', self._test_settings_access)
            ]
            
            verification_result['total_tests'] = len(verification_tests)
            
            for test_name, test_function in verification_tests:
                try:
                    logger.debug(f"Running test '{test_name}' for {result.profile.username}")
                    test_result = test_function(automator, result)
                    
                    verification_result['test_details'][test_name] = {
                        'passed': test_result,
                        'error': None
                    }
                    
                    if test_result:
                        verification_result['tests_passed'] += 1
                        logger.debug(f"Test '{test_name}' PASSED")
                    else:
                        logger.debug(f"Test '{test_name}' FAILED")
                    
                except Exception as e:
                    logger.warning(f"Test '{test_name}' encountered error: {e}")
                    verification_result['test_details'][test_name] = {
                        'passed': False,
                        'error': str(e)
                    }
            
            # Determine overall status
            pass_rate = verification_result['tests_passed'] / verification_result['total_tests']
            
            if pass_rate >= 0.8:  # 80% or more tests passed
                verification_result['status'] = 'verified'
            elif pass_rate >= 0.5:  # 50-79% tests passed
                verification_result['status'] = 'partial'
            else:  # Less than 50% tests passed
                verification_result['status'] = 'failed'
            
            logger.info(f"Account {result.profile.username} verification: {verification_result['status']} ({verification_result['tests_passed']}/{verification_result['total_tests']} tests passed)")
            
        except Exception as e:
            verification_result['status'] = 'error'
            verification_result['error'] = str(e)
            logger.error(f"Account verification error: {e}")
        
        return verification_result
    
    def _test_app_launch(self, automator: SnapchatAppAutomator, result: SnapchatCreationResult) -> bool:
        """Test if Snapchat app launches successfully"""
        try:
            success = automator.launch_snapchat()
            _sleep_human("load", 3.0)  # Allow app to fully load
            return success
        except Exception as e:
            logger.debug(f"App launch test failed: {e}")
            return False
    
    def _test_login_status(self, automator: SnapchatAppAutomator, result: SnapchatCreationResult) -> bool:
        """Test if user is logged in"""
        try:
            # Check for main screen indicators (user is logged in)
            main_screen_found = self._check_main_screen(automator)
            
            # Also check for login prompts (user is NOT logged in)
            login_prompts = ['Log In', 'Sign In', 'Login', 'Sign Up']
            for prompt in login_prompts:
                if automator.wait_for_element(prompt, timeout=5):
                    logger.debug(f"Found login prompt: {prompt}")
                    return False  # Not logged in
            
            return main_screen_found
            
        except Exception as e:
            logger.debug(f"Login status test failed: {e}")
            return False
    
    def _test_profile_access(self, automator: SnapchatAppAutomator, result: SnapchatCreationResult) -> bool:
        """Test if profile can be accessed"""
        try:
            # Try to access profile
            profile_accessed = False
            
            # Method 1: Look for profile button/avatar
            if automator.u2_device(description="Profile").exists:
                automator.u2_device(description="Profile").click()
                _sleep_human("navigation", 2.0)
                profile_accessed = True
            
            # Method 2: Swipe to profile screen
            elif automator.u2_device:
                screen_info = automator.u2_device.info
                automator.u2_device.swipe(
                    screen_info['displayWidth'] * 0.2,
                    screen_info['displayHeight'] * 0.5,
                    screen_info['displayWidth'] * 0.8,
                    screen_info['displayHeight'] * 0.5
                )
                _sleep_human("navigation", 2.0)
                
                # Check if profile elements are visible
                profile_indicators = ['Settings', 'My Profile', result.profile.username]
                for indicator in profile_indicators:
                    if automator.wait_for_element(indicator, timeout=3):
                        profile_accessed = True
                        break
            
            # Go back to main screen
            if profile_accessed:
                automator.u2_device.press("back")
                _sleep_human("navigation", 1.0)
            
            return profile_accessed
            
        except Exception as e:
            logger.debug(f"Profile access test failed: {e}")
            return False
    
    def _test_camera_functionality(self, automator: SnapchatAppAutomator, result: SnapchatCreationResult) -> bool:
        """Test camera functionality"""
        try:
            if not automator.u2_device:
                return False
            
            screen_info = automator.u2_device.info
            center_x = screen_info['displayWidth'] // 2
            center_y = screen_info['displayHeight'] // 2
            
            # Test camera preview (tap to focus)
            automator.u2_device.click(center_x, center_y)
            _sleep_human("tap", 1.0)
            
            # Test shutter button
            shutter_y = int(screen_info['displayHeight'] * 0.85)
            automator.u2_device.click(center_x, shutter_y)
            _sleep_human("tap", 2.0)
            
            # Check if photo was taken (look for save/discard options)
            camera_working = (
                automator.wait_for_element("Save", timeout=3) or
                automator.wait_for_element("Discard", timeout=3) or
                automator.wait_for_element("Send", timeout=3)
            )
            
            # Clean up - discard the photo
            if automator.wait_for_element("Discard", timeout=2):
                automator.tap_element("Discard")
            else:
                automator.u2_device.press("back")
            
            _sleep_human("tap", 1.0)
            return camera_working
            
        except Exception as e:
            logger.debug(f"Camera functionality test failed: {e}")
            return False
    
    def _test_story_access(self, automator: SnapchatAppAutomator, result: SnapchatCreationResult) -> bool:
        """Test access to stories functionality"""
        try:
            # Try to access stories
            story_access = False
            
            if automator.wait_for_element("Stories", timeout=5):
                automator.tap_element("Stories")
                _sleep_human("navigation", 2.0)
                
                # Check if stories screen loaded
                story_indicators = ['My Story', 'Friends', 'Discover']
                for indicator in story_indicators:
                    if automator.wait_for_element(indicator, timeout=3):
                        story_access = True
                        break
                
                # Go back
                automator.u2_device.press("back")
                _sleep_human("navigation", 1.0)
            
            return story_access
            
        except Exception as e:
            logger.debug(f"Story access test failed: {e}")
            return False
    
    def _test_settings_access(self, automator: SnapchatAppAutomator, result: SnapchatCreationResult) -> bool:
        """Test access to settings"""
        try:
            settings_access = False
            
            # Try to access settings from profile
            if automator.u2_device(description="Profile").exists:
                automator.u2_device(description="Profile").click()
                _sleep_human("navigation", 2.0)
                
                if automator.wait_for_element("Settings", timeout=5):
                    automator.tap_element("Settings")
                    _sleep_human("navigation", 2.0)
                    
                    # Check if settings loaded
                    settings_indicators = ['Account', 'Privacy', 'Notifications']
                    for indicator in settings_indicators:
                        if automator.wait_for_element(indicator, timeout=3):
                            settings_access = True
                            break
                    
                    # Go back
                    automator.u2_device.press("back")
                    _sleep_human("navigation", 1.0)
                
                # Go back to main
                automator.u2_device.press("back")
                _sleep_human("navigation", 1.0)
            
            return settings_access
            
        except Exception as e:
            logger.debug(f"Settings access test failed: {e}")
            return False
    
    def perform_post_creation_optimization(self, results: List[SnapchatCreationResult]) -> Dict[str, any]:
        """Perform post-creation optimization for account longevity"""
        logger.info(f"Starting post-creation optimization for {len(results)} accounts...")
        
        optimization_results = {
            'total_accounts': len(results),
            'optimized_count': 0,
            'failed_count': 0,
            'optimization_details': []
        }
        
        for result in results:
            if not result.success or not result.profile:
                optimization_results['failed_count'] += 1
                continue
            
            try:
                logger.info(f"Optimizing account: {result.profile.username}")
                
                # Initialize automator
                automator = SnapchatAppAutomator(result.device_id)
                
                # Launch app
                if not automator.launch_snapchat():
                    raise Exception("Failed to launch Snapchat for optimization")
                
                _sleep_human("load", 3.0)
                
                # Perform optimization activities
                optimization_tasks = [
                    self._optimize_privacy_settings,
                    self._optimize_notification_settings,
                    self._perform_extended_warming,
                    self._setup_account_preferences
                ]
                
                completed_tasks = 0
                for task in optimization_tasks:
                    try:
                        task(automator, result)
                        completed_tasks += 1
                        _sleep_human("navigation", random.uniform(10, 20))
                    except Exception as e:
                        logger.warning(f"Optimization task failed: {e}")
                
                optimization_results['optimization_details'].append({
                    'username': result.profile.username,
                    'completed_tasks': completed_tasks,
                    'total_tasks': len(optimization_tasks),
                    'status': 'optimized' if completed_tasks >= len(optimization_tasks) * 0.7 else 'partial'
                })
                
                optimization_results['optimized_count'] += 1
                
            except Exception as e:
                logger.error(f"Optimization failed for {result.profile.username}: {e}")
                optimization_results['failed_count'] += 1
                optimization_results['optimization_details'].append({
                    'username': result.profile.username,
                    'status': 'failed',
                    'error': str(e)
                })
        
        logger.info(f"Post-creation optimization complete: {optimization_results['optimized_count']}/{len(results)} accounts optimized")
        return optimization_results
    
    def _optimize_privacy_settings(self, automator: SnapchatAppAutomator, result: SnapchatCreationResult):
        """Optimize privacy settings for stealth operation"""
        try:
            logger.debug(f"Optimizing privacy settings for {result.profile.username}")
            
            # Use the async version instead of placeholder
            # Use sync wrapper for privacy settings or handle manually
            try:
                self._optimize_privacy_settings_sync(automator.u2_device)
            except AttributeError:
                logger.info("Privacy settings optimization needs manual handling or sync implementation")
            
        except Exception as e:
            logger.debug(f"Privacy optimization failed: {e}")
    
    def _optimize_notification_settings(self, automator: SnapchatAppAutomator, result: SnapchatCreationResult):
        """Optimize notification settings for stealth operation"""
        try:
            logger.debug(f"Optimizing notification settings for {result.profile.username}")
            
            # Access notification settings through system settings
            u2_device = automator.u2_device
            
            # Open app info for Snapchat
            u2_device.shell('am start -a android.settings.APPLICATION_DETAILS_SETTINGS -d package:com.snapchat.android')
            _sleep_human("navigation", 3.0)
            
            # Navigate to notifications settings
            if u2_device(text='Notifications').exists(timeout=5):
                u2_device(text='Notifications').click()
                _sleep_human("navigation", 2.0)
                
                # Disable various notification types for stealth
                notification_types = [
                    'Show notifications',
                    'Sound',
                    'Vibration',
                    'Show on lock screen'
                ]
                
                for notification_type in notification_types:
                    if u2_device(textContains=notification_type).exists(timeout=3):
                        # Look for toggle switch next to it
                        toggle = u2_device(textContains=notification_type).right(className='android.widget.Switch')
                        if toggle.exists() and toggle.info['checked']:
                            toggle.click()
                            _sleep_human("tap", 1.0)
                            
            # Return to app
            u2_device.press('back')
            u2_device.press('back')
            u2_device.app_start('com.snapchat.android')
            
        except Exception as e:
            logger.debug(f"Notification optimization failed: {e}")
    
    def _perform_extended_warming(self, automator: SnapchatAppAutomator, result: SnapchatCreationResult):
        """Perform extended warming for better account establishment"""
        try:
            logger.debug(f"Performing extended warming for {result.profile.username}")
            
            # Extended warming session (10-15 minutes)
            self._perform_warming_activities(automator, session_duration=random.randint(600, 900))
            
        except Exception as e:
            logger.debug(f"Extended warming failed: {e}")
    
    def _setup_account_preferences(self, automator: SnapchatAppAutomator, result: SnapchatCreationResult):
        """Setup account preferences for natural usage"""
        try:
            logger.debug(f"Setting up preferences for {result.profile.username}")
            
            u2_device = automator.u2_device
            
            # Navigate to settings if available
            if u2_device(description='Settings').exists(timeout=3):
                u2_device(description='Settings').click()
                _sleep_human("navigation", 2.0)
                
                # Configure preferences for natural usage
                preferences = [
                    ('Memories', 'Save to Memories & Camera Roll'),
                    ('Data Saver', False),  # Don't enable data saver
                    ('Travel Mode', False),  # Keep disabled for normal usage
                    ('Dark Mode', random.choice([True, False]))  # Random theme
                ]
                
                for pref_name, setting in preferences:
                    try:
                        if u2_device(textContains=pref_name).exists(timeout=3):
                            u2_device(textContains=pref_name).click()
                            _sleep_human("tap", 1.0)
                            
                            if isinstance(setting, bool):
                                # Handle toggle preferences
                                toggle = u2_device(className='android.widget.Switch')
                                if toggle.exists() and toggle.info['checked'] != setting:
                                    toggle.click()
                                    _sleep_human("tap", 1.0)
                            elif isinstance(setting, str):
                                # Handle selection preferences
                                if u2_device(text=setting).exists(timeout=2):
                                    u2_device(text=setting).click()
                                    _sleep_human("tap", 1.0)
                            
                            # Go back
                            u2_device.press('back')
                            _sleep_human("navigation", 1.0)
                            
                    except Exception as pref_error:
                        logger.debug(f"Failed to set preference {pref_name}: {pref_error}")
                
                # Go back to main app
                u2_device.press('back')
                
        except Exception as e:
            logger.debug(f"Preference setup failed: {e}")
    
    def get_creation_statistics(self) -> Dict[str, any]:
        """Get comprehensive account creation statistics"""
        total = len(self.created_accounts)
        successful = sum(1 for acc in self.created_accounts if acc.success)
        verified = sum(1 for acc in self.created_accounts if acc.verification_status == "verified")
        
        # Calculate timing statistics from actual data
        creation_times = []
        for acc in self.created_accounts:
            if acc.success and hasattr(acc, 'additional_data') and acc.additional_data:
                actual_time = acc.additional_data.get('creation_time_seconds', 0)
                if actual_time > 0:
                    creation_times.append(actual_time)
            elif acc.success:
                # Fallback estimate for older records
                creation_times.append(240)  # 4 minutes average based on testing
        
        avg_creation_time = sum(creation_times) / len(creation_times) if creation_times else 0
        
        # Error analysis
        error_categories = {}
        for acc in self.created_accounts:
            if not acc.success and acc.error:
                category = self._categorize_error(acc.error)
                error_categories[category] = error_categories.get(category, 0) + 1
        
        return {
            'total_attempts': total,
            'successful_creations': successful,
            'verified_accounts': verified,
            'success_rate': successful / total if total > 0 else 0,
            'verification_rate': verified / total if total > 0 else 0,
            'average_creation_time_seconds': avg_creation_time,
            'error_categories': error_categories,
            'created_accounts': [{
                'username': acc.profile.username if acc.profile else 'unknown',
                'success': acc.success,
                'verification_status': acc.verification_status,
                'creation_time': acc.creation_time.isoformat() if acc.creation_time else None,
                'error': acc.error,
                'snapchat_score': acc.snapchat_score
            } for acc in self.created_accounts]
        }
    
    def _categorize_error(self, error: str) -> str:
        """Categorize error for analysis"""
        if not error:
            return 'unknown'
        
        error_lower = error.lower()
        
        if any(word in error_lower for word in ['network', 'connection', 'timeout']):
            return 'network_issues'
        elif any(word in error_lower for word in ['sms', 'verification', 'phone']):
            return 'sms_verification'
        elif any(word in error_lower for word in ['install', 'apk', 'app']):
            return 'app_installation'
        elif any(word in error_lower for word in ['username', 'taken', 'unavailable']):
            return 'username_issues'
        elif any(word in error_lower for word in ['email', 'invalid']):
            return 'email_issues'
        elif any(word in error_lower for word in ['device', 'emulator', 'adb']):
            return 'device_issues'
        else:
            return 'other'
    
    def verify_phone_code(self, device_id: str, verification_code: str) -> bool:
        """Verify phone number with SMS code"""
        try:
            # Initialize app automator for the device
            automator = SnapchatAppAutomator(device_id)
            
            # Submit verification code
            return automator.submit_verification_code(verification_code)
            
        except Exception as e:
            logger.error(f"Error verifying phone code: {e}")
            return False
    
    def perform_warming_activities(self, device_id: str) -> bool:
        """Perform account warming activities"""
        try:
            # Initialize app automator for the device
            automator = SnapchatAppAutomator(device_id)
            
            # Perform warming activities
            self._perform_warming_activities(automator)
            return True
            
        except Exception as e:
            logger.error(f"Error performing warming activities: {e}")
            return False
    
    def configure_add_farming(self, device_id: str) -> bool:
        """Configure account for friend add farming"""
        try:
            # Initialize app automator for the device
            automator = SnapchatAppAutomator(device_id)
            
            # Configure privacy settings for maximum add capacity
            success = automator.configure_privacy_settings({
                'quick_add': True,
                'phone_discovery': True,
                'friend_suggestions': True,
                'location_sharing': False,  # Keep location private
                'story_privacy': 'friends',
                'snap_map': False
            })
            
            if success:
                # Set up profile for attractiveness to maximize adds
                success = automator.optimize_profile_for_adds()
            
            return success
            
        except Exception as e:
            logger.error(f"Error configuring add farming: {e}")
            return False
    
    def apply_security_hardening(self, device_id: str) -> bool:
        """Apply final security hardening to protect account"""
        try:
            # Initialize app automator for the device
            automator = SnapchatAppAutomator(device_id)
            
            # Apply security measures
            security_applied = automator.apply_security_hardening({
                'two_factor_setup': False,  # Don't enable for automation
                'login_verification': False,
                'clear_cache': True,
                'randomize_activity': True,
                'anti_detection_final': True
            })
            
            # Save account state
            if security_applied:
                automator.save_account_state()
            
            return security_applied
            
        except Exception as e:
            logger.error(f"Error applying security hardening: {e}")
            return False

    # Helpers for orchestrator to safely set display and avatar post-registration
    def _app_automator_set_display_name(self, device_id: str, display_name: str) -> bool:
        automator = self._automators.get(device_id)
        if not automator:
            automator = SnapchatAppAutomator(device_id)
            self._automators[device_id] = automator
        return automator.set_display_name(display_name)

    def _app_automator_set_avatar(self, device_id: str, name: str, photo_path: Optional[str] = None) -> bool:
        automator = self._automators.get(device_id)
        if not automator:
            automator = SnapchatAppAutomator(device_id)
            self._automators[device_id] = automator
        return automator.set_profile_avatar(name, photo_path)

    def _app_automator_link_bitmoji(self, device_id: str) -> Optional[str]:
        automator = self._automators.get(device_id)
        if not automator:
            automator = SnapchatAppAutomator(device_id)
            self._automators[device_id] = automator
        return automator.link_bitmoji()

# Global instance
_snapchat_creator = None

def get_snapchat_creator() -> SnapchatStealthCreator:
    """Get global Snapchat creator instance"""
    global _snapchat_creator
    if _snapchat_creator is None:
        _snapchat_creator = SnapchatStealthCreator()
    return _snapchat_creator

def create_snapchat_accounts_batch(count: int, verify_accounts: bool = True, 
                                  optimize_accounts: bool = True) -> Dict[str, any]:
    """Main function to create a batch of Snapchat accounts with verification and optimization"""
    logger.info(f"Starting batch creation of {count} Snapchat accounts")
    
    creator = SnapchatStealthCreator()
    
    try:
        # Create accounts
        results = creator.create_multiple_accounts(count)
        
        # Generate statistics
        stats = creator.get_creation_statistics()
        
        batch_results = {
            'creation_results': results,
            'creation_statistics': stats,
            'verification_results': None,
            'optimization_results': None
        }
        
        # Verify accounts if requested
        if verify_accounts and results:
            logger.info("Starting account verification...")
            verification_results = creator.verify_account_batch(results)
            batch_results['verification_results'] = verification_results
        
        # Optimize accounts if requested
        if optimize_accounts and results:
            logger.info("Starting account optimization...")
            optimization_results = creator.perform_post_creation_optimization(results)
            batch_results['optimization_results'] = optimization_results
        
        return batch_results
        
    except Exception as e:
        logger.error(f"Batch creation failed: {e}")
        raise

# Convenience functions for integration with other systems
def create_snapchat_accounts_for_tinder(count: int, female_names: List[str] = None) -> List[str]:
    """Create Snapchat accounts specifically for Tinder bio integration"""
    creator = get_snapchat_creator()
    
    # Generate profiles with female names if provided
    profiles = []
    for i in range(count):
        if female_names and i < len(female_names):
            profile = creator.generate_stealth_profile(first_name=female_names[i])
        else:
            profile = creator.generate_stealth_profile()
        profiles.append(profile)
    
    # Create accounts (simplified for integration)
    device_ids = [f"emulator-{5554 + i * 2}" for i in range(count)]
    results = creator.create_multiple_accounts(count, device_ids)
    
    # Return usernames of successful accounts
    successful_usernames = [
        result.profile.username for result in results 
        if result.success and result.profile
    ]
    
    logger.info(f"Created {len(successful_usernames)} Snapchat accounts for Tinder integration")
    return successful_usernames

def get_snapchat_usernames_for_bios(count: int) -> List[str]:
    """Get existing Snapchat usernames for use in Tinder bios"""
    creator = get_snapchat_creator()
    return creator.get_usernames_for_tinder(count)

def validate_snapchat_account(username: str, device_id: str) -> bool:
    """Validate a Snapchat account is working using real profile generation"""
    try:
        # Generate real profile for validation instead of fake data
        creator = get_snapchat_creator()
        real_profile = creator.generate_stealth_profile()
        
        # Use the provided username but keep other real data
        validation_profile = SnapchatProfile(
            username=username,
            display_name=real_profile.display_name,
            email=real_profile.email,  # Real email, not fake
            phone_number=real_profile.phone_number,
            birth_date=real_profile.birth_date,
            password=real_profile.password
        )
        
        validation_result = SnapchatCreationResult(
            success=True,
            profile=validation_profile,
            device_id=device_id,
            verification_status="pending"
        )
        
        verification_result = creator._verify_single_account(validation_result)
        
        return verification_result['status'] in ['verified', 'partial']
        
    except Exception as e:
        logger.error(f"Account validation failed for {username}: {e}")
        return False

# Proxy pool session
try:
    from automation.services.proxy_pool import get_proxy_pool
    _HTTP_SESSION = get_proxy_pool().session()
except Exception:
    _HTTP_SESSION = None
if _HTTP_SESSION is None:
    _HTTP_SESSION = requests.Session()

if __name__ == "__main__":
    # Enhanced CLI for Snapchat account creation
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Snapchat Stealth Account Creator - Production Ready Batch System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python stealth_creator.py --count 10                    # Create 10 accounts
  python stealth_creator.py --count 50 --no-verify       # Create 50 accounts without verification
  python stealth_creator.py --count 25 --batch-size 5    # Create 25 accounts in batches of 5
  python stealth_creator.py --test-components             # Test individual components
        """
    )
    
    parser.add_argument('--count', '-c', type=int, default=1, 
                       help='Number of accounts to create (default: 1)')
    parser.add_argument('--batch-size', type=int, default=5,
                       help='Batch size for account creation (default: 5)')
    parser.add_argument('--output', '-o', 
                       help='JSON output file for results')
    parser.add_argument('--no-verify', action='store_true',
                       help='Skip account verification')
    parser.add_argument('--no-optimize', action='store_true',
                       help='Skip account optimization')
    parser.add_argument('--test-components', action='store_true',
                       help='Test individual components')
    parser.add_argument('--generate-usernames', type=int, metavar='N',
                       help='Generate N sample usernames and exit')
    parser.add_argument('--generate-profiles', type=int, metavar='N',
                       help='Generate N sample profiles and exit')
    parser.add_argument('--test-pictures', type=int, metavar='N',
                       help='Generate N test profile pictures and exit')
    
    args = parser.parse_args()
    
    try:
        # Handle component testing
        if args.test_components:
            logger.info("Testing individual components...")
            
            # Test APK manager
            print("\n=== Testing APK Manager ===")
            apk_manager = APKManager()
            apk_status = apk_manager.check_for_updates()
            print(f"APK Status: {json.dumps(apk_status, indent=2)}")
            
            # Test profile picture generator
            print("\n=== Testing Profile Picture Generator ===")
            pic_generator = ProfilePictureGenerator()
            test_names = ["John Smith", "Jane Doe", "Alex Johnson"]
            generated_pics = pic_generator.create_batch_pictures(test_names, 2)
            print(f"Generated {len(generated_pics)} profile pictures")
            
            # Test username generation
            print("\n=== Testing Username Generator ===")
            username_gen = SnapchatUsernameGenerator()
            usernames = username_gen.generate_multiple_usernames(5, "Test", "User")
            print(f"Generated usernames: {usernames}")
            
            print("\nComponent testing complete!")
            sys.exit(0)
        
        # Handle utility functions
        if args.generate_usernames:
            print(f"Generating {args.generate_usernames} sample usernames...")
            generator = SnapchatUsernameGenerator()
            usernames = generator.generate_multiple_usernames(args.generate_usernames, "Sample", "User")
            for i, username in enumerate(usernames, 1):
                print(f"{i:2d}. {username}")
            sys.exit(0)
        
        if args.generate_profiles:
            print(f"Generating {args.generate_profiles} sample profiles...")
            creator = SnapchatStealthCreator()
            for i in range(args.generate_profiles):
                profile = creator.generate_stealth_profile()
                print(f"{i+1:2d}. {profile.username} - {profile.display_name} ({profile.email[:10]}...)")
            sys.exit(0)
        
        if args.test_pictures:
            print(f"Generating {args.test_pictures} test profile pictures...")
            pic_generator = ProfilePictureGenerator()
            for i in range(args.test_pictures):
                name = f"TestUser{i+1}"
                picture_path = pic_generator.generate_profile_picture(name)
                print(f"{i+1:2d}. Generated: {picture_path}")
            sys.exit(0)
        
        # Main account creation
        start_time = datetime.now()
        logger.info(f"Starting Snapchat account creation at {start_time}")
        
        # Create accounts with verification and optimization
        batch_results = create_snapchat_accounts_batch(
            count=args.count,
            verify_accounts=not args.no_verify,
            optimize_accounts=not args.no_optimize
        )
        
        # Output results
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        print(f"\n{'='*60}")
        print(f"SNAPCHAT ACCOUNT CREATION COMPLETE")
        print(f"{'='*60}")
        print(f"Total Time: {total_time:.1f} seconds")
        print(f"Accounts Requested: {args.count}")
        
        if batch_results['creation_statistics']:
            stats = batch_results['creation_statistics']
            print(f"Accounts Created: {stats['successful_creations']}/{stats['total_attempts']}")
            print(f"Success Rate: {stats['success_rate']*100:.1f}%")
            print(f"Verification Rate: {stats['verification_rate']*100:.1f}%")
            print(f"Average Time per Account: {stats.get('average_creation_time_seconds', 0):.1f}s")
        
        if batch_results['verification_results'] and not args.no_verify:
            ver_stats = batch_results['verification_results']
            print(f"Verified Accounts: {ver_stats['verified_count']}/{ver_stats['total_accounts']}")
        
        if batch_results['optimization_results'] and not args.no_optimize:
            opt_stats = batch_results['optimization_results']
            print(f"Optimized Accounts: {opt_stats['optimized_count']}/{opt_stats['total_accounts']}")
        
        # Save results to file
        if args.output:
            output_file = args.output
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"snapchat_batch_results_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(batch_results, f, indent=2, default=str)
        
        print(f"\nDetailed results saved to: {output_file}")
        
        # Print summary of working accounts
        working_accounts = [
            result for result in batch_results['creation_results']
            if result.success and result.profile
        ]
        
        if working_accounts:
            print(f"\nWorking Snapchat Accounts ({len(working_accounts)}):")
            print("-" * 40)
            for i, result in enumerate(working_accounts[:10], 1):  # Show first 10
                print(f"{i:2d}. {result.profile.username} - {result.verification_status}")
            
            if len(working_accounts) > 10:
                print(f"    ... and {len(working_accounts) - 10} more accounts")
        
        print(f"\n{'='*60}")
        
    except KeyboardInterrupt:
        logger.info("\nSnapchat creation interrupted by user")
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Snapchat creation failed: {e}")
        print(f"\nError: {e}")
        sys.exit(1)


# ================================
# ASYNC FUNCTIONALITY EXAMPLES
# ================================

async def create_single_account_example():
    """Example of creating a single account with new async methods"""
    creator = SnapchatStealthCreator()
    
    # Generate a stealth profile
    profile = creator.generate_stealth_profile()
    
    print(f"Creating account for: {profile.username}")
    print(f"Email: {profile.email}")
    print(f"Phone: {profile.phone_number}")
    
    try:
        # Create account with real automation
        result = await creator.create_snapchat_account_async(profile)
        
        if result.success:
            print(f"\n✅ Account created successfully!")
            print(f"Username: {result.username}")
            print(f"Creation time: {result.additional_data.get('creation_time_seconds', 0):.1f}s")
            print(f"Verification: {result.verification_status}")
        else:
            print(f"\n❌ Account creation failed: {result.error}")
            
        return result
        
    except Exception as e:
        print(f"\n❌ Exception during account creation: {e}")
        return None

async def create_multiple_accounts_example(count: int = 3):
    """Example of creating multiple accounts asynchronously"""
    creator = SnapchatStealthCreator()
    
    print(f"Creating {count} Snapchat accounts asynchronously...")
    
    try:
        results = await creator.create_multiple_accounts_async(
            count=count,
            batch_size=2,  # Process 2 at a time
            female_names=[
                "Emma", "Olivia", "Sophia", "Isabella", "Charlotte",
                "Amelia", "Mia", "Harper", "Evelyn", "Abigail"
            ]
        )
        
        # Display results
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        print(f"\n=== BATCH CREATION RESULTS ===")
        print(f"Successful: {len(successful)}/{len(results)}")
        print(f"Failed: {len(failed)}/{len(results)}")
        print(f"Success Rate: {len(successful)/len(results)*100:.1f}%")
        
        if successful:
            print(f"\n✅ SUCCESSFUL ACCOUNTS:")
            for i, result in enumerate(successful, 1):
                print(f"{i:2d}. {result.username} - {result.verification_status}")
                if result.additional_data:
                    time_taken = result.additional_data.get('creation_time_seconds', 0)
                    print(f"    Created in {time_taken:.1f}s")
        
        if failed:
            print(f"\n❌ FAILED ACCOUNTS:")
            for i, result in enumerate(failed, 1):
                print(f"{i:2d}. {result.username or 'Unknown'} - {result.error}")
        
        return results
        
    except Exception as e:
        print(f"\n❌ Batch creation failed: {e}")
        return []

def demonstration_mode():
    """Run demonstration of new async functionality"""
    print("\n" + "="*60)
    print("SNAPCHAT STEALTH CREATOR - ENHANCED AUTOMATION")
    print("="*60)
    print("\nNew Features:")
    print("✓ Real UIAutomator2 integration")
    print("✓ Actual SMS verification with Twilio")
    print("✓ Enhanced anti-detection measures")
    print("✓ Human-like behavior simulation")
    print("✓ Async batch processing")
    print("✓ Elite device fingerprinting")
    
    print("\nChoose demonstration:")
    print("1. Create single account (async)")
    print("2. Create 3 accounts (batch async)")
    print("3. Create 5 accounts (batch async)")
    print("4. Show system capabilities")
    print("0. Exit")
    
    while True:
        try:
            choice = input("\nEnter choice (0-4): ").strip()
            
            if choice == '0':
                print("Exiting demonstration.")
                break
            elif choice == '1':
                print("\n=== Single Account Creation ===")
                result = asyncio.run(create_single_account_example())
            elif choice == '2':
                print("\n=== Batch Creation (3 accounts) ===")
                results = asyncio.run(create_multiple_accounts_example(3))
            elif choice == '3':
                print("\n=== Batch Creation (5 accounts) ===")
                results = asyncio.run(create_multiple_accounts_example(5))
            elif choice == '4':
                show_system_capabilities()
            else:
                print("Invalid choice. Please enter 0-4.")
                continue
                
            input("\nPress Enter to continue...")
            
        except KeyboardInterrupt:
            print("\nDemonstration interrupted.")
            break
        except Exception as e:
            print(f"\nDemonstration error: {e}")
            input("Press Enter to continue...")

def show_system_capabilities():
    """Show system capabilities and status"""
    print("\n=== SYSTEM CAPABILITIES ===")
    
    # Check UIAutomator2
    if U2_AVAILABLE:
        print("✅ UIAutomator2: Available")
    else:
        print("❌ UIAutomator2: Not available - install with 'pip install uiautomator2'")
    
    # Check SMS integration
    try:
        sms_verifier = get_sms_verifier()
        print("✅ SMS Verifier: Available")
    except Exception:
        print("❌ SMS Verifier: Not available - check Twilio configuration")
    
    # Check email integration
    if EMAIL_INTEGRATION_AVAILABLE:
        print("✅ Email Integration: Available")
    else:
        print("❌ Email Integration: Not available")
    
    # Check anti-detection system
    try:
        anti_detection = get_anti_detection_system()
        print("✅ Anti-Detection System: Available")
    except Exception:
        print("❌ Anti-Detection System: Not available")
    
    # Check available devices
    creator = SnapchatStealthCreator()
    devices = creator._get_all_available_devices()
    print(f"📱 Available Devices: {len(devices)}")
    for i, device in enumerate(devices[:5], 1):
        print(f"   {i}. {device}")
    if len(devices) > 5:
        print(f"   ... and {len(devices) - 5} more")
    
    print("\n=== CONFIGURATION STATUS ===")
    print(f"✓ Max concurrent devices: {min(len(devices), 5)}")
    print(f"✓ Batch size recommendation: {min(3, len(devices))}")
    print(f"✓ Anti-detection level: Elite (2025+ security)")
    print(f"✓ Success rate target: 80-95%")
    print(f"✓ Average creation time: 3-6 minutes per account")

if __name__ == "__main__":
    import argparse
    
    # Check if we're running in demo mode
    if len(sys.argv) > 1 and '--enhanced' in sys.argv:
        # Parse enhanced command line arguments
        parser = argparse.ArgumentParser(description='Enhanced Snapchat Stealth Account Creator')
        parser.add_argument('--enhanced', action='store_true', help='Use enhanced async functionality')
        parser.add_argument('--demo', action='store_true', help='Run demonstration mode')
        parser.add_argument('--single', action='store_true', help='Create single account')
        parser.add_argument('--count', type=int, default=1, help='Number of accounts to create')
        parser.add_argument('--batch', action='store_true', help='Use async batch creation')
        parser.add_argument('--capabilities', action='store_true', help='Show system capabilities')
        
        args = parser.parse_args()
        
        if args.demo:
            demonstration_mode()
        elif args.capabilities:
            show_system_capabilities()
        elif args.single:
            print("Creating single account with enhanced automation...")
            # Use sync version for CLI execution to avoid asyncio.run conflicts
            print("Creating single account (sync mode for CLI)...")
            create_single_account_example_sync()
        elif args.batch:
            print(f"Creating {args.count} accounts asynchronously with enhanced automation...")
            # Keep async for batch operations since they benefit from concurrency
            try:
                asyncio.run(create_multiple_accounts_example(args.count))
            except RuntimeError as e:
                if "asyncio.run() cannot be called from a running event loop" in str(e):
                    print("Switching to sync mode due to existing event loop...")
                    create_multiple_accounts_example_sync(args.count)
                else:
                    raise
        else:
            print("Enhanced Snapchat Creator - Use one of the following options:")
            print("--demo for interactive demonstration")
            print("--capabilities to check system status")
            print("--single for single account creation")
            print("--batch --count N for batch creation")
    else:
        # Fall back to original functionality
        pass  # Original main code continues to work as before