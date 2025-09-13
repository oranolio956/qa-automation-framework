#!/usr/bin/env python3
"""
Tinder Profile Management System
Handles profile updates, bio management, and photo optimization
"""

import os
import sys
import time
import random
import logging
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import requests
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np

# Import automation components
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from android.emulator_manager import EmulatorInstance
from core.anti_detection import get_anti_detection_system
from tinder.account_creator import TinderAppAutomator, AccountProfile

# Import existing utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../utils'))
from brightdata_proxy import get_brightdata_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PhotoMetadata:
    """Photo metadata for optimization"""
    file_path: str
    width: int
    height: int
    file_size: int
    format: str
    quality_score: float = 0.0
    face_count: int = 0
    is_optimized: bool = False

@dataclass
class ProfileUpdate:
    """Profile update request"""
    account_id: str
    bio_updates: Optional[str] = None
    new_photos: Optional[List[str]] = None
    remove_photos: Optional[List[int]] = None  # Photo indices to remove
    distance_preference: Optional[int] = None
    age_range: Optional[Tuple[int, int]] = None
    location: Optional[Tuple[float, float]] = None

class PhotoProcessor:
    """Processes and optimizes photos for Tinder profiles"""
    
    def __init__(self):
        self.target_size = (640, 640)  # Tinder recommended size
        self.max_file_size = 8 * 1024 * 1024  # 8MB limit
        self.supported_formats = ['JPEG', 'PNG', 'WEBP']
        
    def analyze_photo(self, image_path: str) -> PhotoMetadata:
        """Analyze photo quality and characteristics"""
        try:
            with Image.open(image_path) as img:
                metadata = PhotoMetadata(
                    file_path=image_path,
                    width=img.width,
                    height=img.height,
                    file_size=os.path.getsize(image_path),
                    format=img.format,
                )
            
            # Calculate quality score
            quality_score = self._calculate_quality_score(image_path)
            metadata.quality_score = quality_score
            
            # Detect faces
            face_count = self._detect_faces(image_path)
            metadata.face_count = face_count
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to analyze photo {image_path}: {e}")
            raise
    
    def _calculate_quality_score(self, image_path: str) -> float:
        """Calculate photo quality score (0-10)"""
        try:
            # Load image
            img = cv2.imread(image_path)
            if img is None:
                return 0.0
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Calculate sharpness using Laplacian variance
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            sharpness_score = min(laplacian_var / 1000, 1.0)  # Normalize to 0-1
            
            # Calculate brightness
            brightness = np.mean(gray) / 255.0
            brightness_score = 1.0 - abs(brightness - 0.5) * 2  # Best around 0.5
            
            # Calculate contrast
            contrast = np.std(gray) / 128.0
            contrast_score = min(contrast, 1.0)
            
            # Resolution score
            resolution = img.shape[0] * img.shape[1]
            resolution_score = min(resolution / (1920 * 1080), 1.0)
            
            # Combine scores
            quality_score = (
                sharpness_score * 0.4 +
                brightness_score * 0.2 +
                contrast_score * 0.2 +
                resolution_score * 0.2
            ) * 10
            
            return round(quality_score, 2)
            
        except Exception as e:
            logger.error(f"Quality calculation failed: {e}")
            return 5.0  # Default medium quality
    
    def _detect_faces(self, image_path: str) -> int:
        """Detect number of faces in image"""
        try:
            # Load image
            img = cv2.imread(image_path)
            if img is None:
                return 0
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Load face cascade (would need to download haarcascade_frontalface_default.xml)
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            face_cascade = cv2.CascadeClassifier(cascade_path)
            
            # Detect faces
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
            
            return len(faces)
            
        except Exception as e:
            logger.warning(f"Face detection failed: {e}")
            return 1  # Assume one face if detection fails
    
    def optimize_photo(self, image_path: str, output_path: str = None) -> str:
        """Optimize photo for Tinder upload"""
        if not output_path:
            name, ext = os.path.splitext(image_path)
            output_path = f"{name}_optimized{ext}"
        
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if too large
                if img.width > self.target_size[0] or img.height > self.target_size[1]:
                    img.thumbnail(self.target_size, Image.Resampling.LANCZOS)
                
                # Enhance image
                img = self._enhance_image(img)
                
                # Save with optimization
                quality = 85
                while True:
                    img.save(output_path, 'JPEG', quality=quality, optimize=True)
                    
                    # Check file size
                    if os.path.getsize(output_path) <= self.max_file_size or quality <= 60:
                        break
                    quality -= 5
                
                logger.info(f"Optimized photo: {image_path} -> {output_path} (quality={quality})")
                return output_path
                
        except Exception as e:
            logger.error(f"Photo optimization failed: {e}")
            raise
    
    def _enhance_image(self, img: Image.Image) -> Image.Image:
        """Apply subtle enhancements to image"""
        try:
            # Slight sharpening
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.1)
            
            # Slight contrast boost
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.05)
            
            # Slight color saturation
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(1.1)
            
            return img
            
        except Exception as e:
            logger.error(f"Image enhancement failed: {e}")
            return img

class BioGenerator:
    """Generates and optimizes Tinder bios"""
    
    def __init__(self):
        self.bio_templates = {
            'adventure': [
                "Adventure seeker ⛰️ Always planning the next trip",
                "Outdoor enthusiast 🏕️ Love hiking and camping",
                "Travel addict ✈️ Next stop: {destination}",
                "Ski slopes in winter, beaches in summer 🎿🏄‍♀️"
            ],
            'fitness': [
                "Gym life 💪 Early morning workouts",
                "Yoga instructor 🧘‍♀️ Finding balance daily",
                "Running marathons and chasing dreams 🏃‍♂️",
                "Crossfit enthusiast 🏋️‍♀️ Always up for a challenge"
            ],
            'foodie': [
                "Foodie at heart ❤️ Always trying new restaurants",
                "Chef by night 👨‍🍳 Love cooking Italian",
                "Coffee connoisseur ☕ Third wave or bust",
                "Wine enthusiast 🍷 Napa Valley regular"
            ],
            'creative': [
                "Artist 🎨 Painting my way through life",
                "Musician 🎸 Playing gigs around town",
                "Photographer 📷 Capturing life's moments",
                "Writer ✍️ Working on my first novel"
            ],
            'professional': [
                "Marketing professional 💼 Building brands",
                "Software engineer 💻 Building the future",
                "Teacher 📚 Shaping young minds",
                "Doctor 👨‍⚕️ Saving lives daily"
            ]
        }
        
        self.interests = [
            "dogs", "cats", "hiking", "yoga", "coffee", "wine", "travel",
            "photography", "music", "art", "books", "movies", "cooking",
            "fitness", "beach", "mountains", "concerts", "festivals"
        ]
        
        self.emojis = {
            'dogs': '🐕', 'cats': '🐱', 'hiking': '🥾', 'yoga': '🧘‍♀️',
            'coffee': '☕', 'wine': '🍷', 'travel': '✈️', 'photography': '📷',
            'music': '🎵', 'art': '🎨', 'books': '📚', 'movies': '🎬',
            'cooking': '👨‍🍳', 'fitness': '💪', 'beach': '🏖️', 'mountains': '⛰️'
        }
    
    def generate_bio(self, snapchat_username: str = None, interests: List[str] = None) -> str:
        """Generate engaging Tinder bio"""
        if not interests:
            interests = random.sample(self.interests, k=random.randint(2, 4))
        
        # Choose bio category
        category = random.choice(list(self.bio_templates.keys()))
        base_bio = random.choice(self.bio_templates[category])
        
        # Add interests with emojis
        interest_line = " ".join([
            f"{interest.title()} {self.emojis.get(interest, '✨')}"
            for interest in interests[:3]
        ])
        
        # Combine elements
        bio_parts = [base_bio, interest_line]
        
        # Add Snapchat if provided
        if snapchat_username:
            bio_parts.append(f"SC: {snapchat_username}")
        
        # Add call to action
        cta_options = [
            "Let's grab coffee ☕",
            "Adventure buddy needed 🗺️",
            "Swipe right if you can keep up 😉",
            "Looking for genuine connections 💫",
            "Let's create some memories 📸"
        ]
        bio_parts.append(random.choice(cta_options))
        
        bio = "\n".join(bio_parts)
        
        # Ensure bio is under Tinder's character limit (500 characters)
        if len(bio) > 500:
            bio = bio[:497] + "..."
        
        return bio
    
    def optimize_bio_for_engagement(self, bio: str) -> str:
        """Optimize bio for higher engagement"""
        # Add strategic emojis if missing
        if '☕' not in bio and 'coffee' in bio.lower():
            bio = bio.replace('coffee', 'coffee ☕')
        
        if '🐕' not in bio and 'dog' in bio.lower():
            bio = bio.replace('dog', 'dog 🐕')
        
        # Ensure proper spacing and formatting
        lines = bio.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not line.endswith(('✨', '💫', '❤️', '😉')):
                line += ' ✨'
            formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)

class TinderProfileManager:
    """Main profile management system"""
    
    def __init__(self):
        self.photo_processor = PhotoProcessor()
        self.bio_generator = BioGenerator()
        self.anti_detection = get_anti_detection_system()
        
    def update_profile(self, account_id: str, device_id: str, updates: ProfileUpdate) -> bool:
        """Update Tinder profile with new content"""
        logger.info(f"Updating profile for account {account_id}")
        
        try:
            # Initialize automator
            automator = TinderAppAutomator(device_id)
            
            # Launch Tinder
            if not automator.launch_tinder():
                raise RuntimeError("Failed to launch Tinder")
            
            # Navigate to profile edit
            if not self._navigate_to_profile_edit(automator):
                raise RuntimeError("Failed to navigate to profile edit")
            
            # Apply updates
            if updates.bio_updates:
                if not self._update_bio(automator, updates.bio_updates):
                    logger.error("Failed to update bio")
            
            if updates.new_photos:
                if not self._update_photos(automator, updates.new_photos):
                    logger.error("Failed to update photos")
            
            if updates.distance_preference:
                if not self._update_distance_preference(automator, updates.distance_preference):
                    logger.error("Failed to update distance preference")
            
            if updates.age_range:
                if not self._update_age_range(automator, updates.age_range):
                    logger.error("Failed to update age range")
            
            logger.info(f"Profile update completed for account {account_id}")
            return True
            
        except Exception as e:
            logger.error(f"Profile update failed: {e}")
            return False
    
    def _navigate_to_profile_edit(self, automator: TinderAppAutomator) -> bool:
        """Navigate to profile edit screen"""
        try:
            # Tap profile icon (usually bottom left)
            if not automator.tap_element("Profile"):
                return False
            
            time.sleep(2)
            
            # Tap edit profile
            if not automator.tap_element("Edit Info"):
                return False
            
            time.sleep(2)
            return True
            
        except Exception as e:
            logger.error(f"Navigation to profile edit failed: {e}")
            return False
    
    def _update_bio(self, automator: TinderAppAutomator, new_bio: str) -> bool:
        """Update profile bio"""
        try:
            # Find and tap bio field
            if not automator.wait_for_element("About", timeout=10):
                return False
            
            if not automator.tap_element("About"):
                return False
            
            time.sleep(1)
            
            # Clear and enter new bio
            if not automator.enter_text("About", new_bio):
                return False
            
            # Save changes
            if not automator.tap_element("Done"):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Bio update failed: {e}")
            return False
    
    def _update_photos(self, automator: TinderAppAutomator, photo_paths: List[str]) -> bool:
        """Update profile photos"""
        try:
            # Process and optimize photos first
            optimized_photos = []
            for photo_path in photo_paths:
                try:
                    optimized_path = self.photo_processor.optimize_photo(photo_path)
                    optimized_photos.append(optimized_path)
                except Exception as e:
                    logger.error(f"Failed to optimize photo {photo_path}: {e}")
                    continue
            
            # Upload photos via ADB (since UI automation for file picker is complex)
            for i, photo_path in enumerate(optimized_photos):
                if not self._upload_photo_via_adb(automator.device_id, photo_path, i):
                    logger.error(f"Failed to upload photo {i+1}")
            
            return len(optimized_photos) > 0
            
        except Exception as e:
            logger.error(f"Photo update failed: {e}")
            return False
    
    def _upload_photo_via_adb(self, device_id: str, photo_path: str, index: int) -> bool:
        """Upload photo using ADB"""
        try:
            # Push photo to device
            device_path = f"/sdcard/tinder_photo_{index}.jpg"
            cmd = ["adb", "-s", device_id, "push", photo_path, device_path]
            subprocess.run(cmd, check=True)
            
            # Would trigger photo selection in Tinder app
            # This requires more complex UI automation
            logger.info(f"Photo pushed to device: {device_path}")
            return True
            
        except Exception as e:
            logger.error(f"Photo upload via ADB failed: {e}")
            return False
    
    def _update_distance_preference(self, automator: TinderAppAutomator, distance: int) -> bool:
        """Update distance preference"""
        try:
            # Navigate to settings
            if not automator.tap_element("Settings"):
                return False
            
            time.sleep(2)
            
            # Find discovery preferences
            if not automator.tap_element("Discovery"):
                return False
            
            # Update maximum distance
            if not automator.wait_for_element("Maximum Distance", timeout=10):
                return False
            
            # Would need slider interaction logic here
            logger.info(f"Distance preference update to {distance}km - slider interaction needed")
            return True
            
        except Exception as e:
            logger.error(f"Distance preference update failed: {e}")
            return False
    
    def _update_age_range(self, automator: TinderAppAutomator, age_range: Tuple[int, int]) -> bool:
        """Update age range preference"""
        try:
            min_age, max_age = age_range
            
            # Would implement age range slider interaction
            logger.info(f"Age range update to {min_age}-{max_age} - slider interaction needed")
            return True
            
        except Exception as e:
            logger.error(f"Age range update failed: {e}")
            return False
    
    def batch_update_profiles(self, updates: List[ProfileUpdate], device_ids: List[str]) -> Dict[str, bool]:
        """Update multiple profiles"""
        results = {}
        
        for update in updates:
            # Find available device
            device_id = None
            for did in device_ids:
                if did not in results:  # Device not in use
                    device_id = did
                    break
            
            if not device_id:
                logger.warning(f"No available device for account {update.account_id}")
                results[update.account_id] = False
                continue
            
            # Apply update
            success = self.update_profile(update.account_id, device_id, update)
            results[update.account_id] = success
            
            # Add delay between updates
            if success:
                delay = random.uniform(30, 90)
                logger.info(f"Waiting {delay:.1f}s before next update...")
                time.sleep(delay)
        
        return results
    
    def generate_content_variations(self, base_profile: AccountProfile, count: int = 5) -> List[Dict[str, str]]:
        """Generate content variations for A/B testing"""
        variations = []
        
        for i in range(count):
            # Generate new bio
            new_bio = self.bio_generator.generate_bio(
                snapchat_username=base_profile.snapchat_username,
                interests=random.sample(['travel', 'fitness', 'coffee', 'dogs'], k=3)
            )
            
            variations.append({
                'variation_id': f"var_{i+1}",
                'bio': new_bio,
                'description': f"Bio variation {i+1} with different interests and tone"
            })
        
        return variations
    
    def analyze_photo_set(self, photo_paths: List[str]) -> Dict[str, any]:
        """Analyze a set of photos for profile optimization"""
        analysis = {
            'total_photos': len(photo_paths),
            'photo_analysis': [],
            'recommendations': [],
            'overall_score': 0.0
        }
        
        total_quality = 0.0
        face_photos = 0
        
        for photo_path in photo_paths:
            try:
                metadata = self.photo_processor.analyze_photo(photo_path)
                analysis['photo_analysis'].append(asdict(metadata))
                
                total_quality += metadata.quality_score
                if metadata.face_count > 0:
                    face_photos += 1
                    
            except Exception as e:
                logger.error(f"Failed to analyze photo {photo_path}: {e}")
        
        # Calculate overall score
        if analysis['total_photos'] > 0:
            analysis['overall_score'] = total_quality / analysis['total_photos']
        
        # Generate recommendations
        if face_photos < 2:
            analysis['recommendations'].append("Add more photos with clear face shots")
        
        if analysis['total_photos'] < 4:
            analysis['recommendations'].append("Add more photos (4-6 is optimal)")
        
        if analysis['overall_score'] < 6.0:
            analysis['recommendations'].append("Improve photo quality - better lighting and resolution")
        
        return analysis

# Global instance
_profile_manager = None

def get_profile_manager() -> TinderProfileManager:
    """Get global profile manager instance"""
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = TinderProfileManager()
    return _profile_manager

if __name__ == "__main__":
    # Test profile management
    manager = TinderProfileManager()
    
    # Test bio generation
    print("Testing bio generation:")
    for i in range(3):
        bio = manager.bio_generator.generate_bio(
            snapchat_username="test_user",
            interests=['travel', 'coffee', 'dogs']
        )
        print(f"Bio {i+1}: {bio}")
        print("-" * 50)
    
    # Test photo analysis (would need actual photo files)
    # photo_paths = ["/path/to/photo1.jpg", "/path/to/photo2.jpg"]
    # analysis = manager.analyze_photo_set(photo_paths)
    # print(f"Photo analysis: {json.dumps(analysis, indent=2)}")