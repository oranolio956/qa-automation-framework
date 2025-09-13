#!/usr/bin/env python3
"""
Anti-Detection System for Tinder Account Automation
Implements advanced stealth measures to avoid bans and detection
"""

import random
import time
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from scipy import interpolate
import hashlib
import os
import sys

# Import existing utils
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../utils'))
from brightdata_proxy import get_brightdata_session, verify_proxy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DeviceFingerprint:
    """Device fingerprint for consistent identity"""
    device_id: str
    model: str
    android_version: str
    brand: str
    display_resolution: Tuple[int, int]
    dpi: int
    build_id: str
    timezone: str
    language: str
    carrier: str
    ip_address: str
    
class BehaviorPattern:
    """Human-like behavior pattern generator"""
    
    def __init__(self, aggressiveness: float = 0.3):
        """
        Initialize behavior patterns
        Args:
            aggressiveness: 0.1 (very conservative) to 1.0 (aggressive)
        """
        self.aggressiveness = aggressiveness
        self.session_data = {}
        self.activity_history = []
        
    def get_swipe_timing(self) -> float:
        """Generate human-like swipe timing intervals"""
        base_delay = 2.0  # Base 2 seconds between swipes
        
        # Add variability based on aggressiveness
        if self.aggressiveness < 0.2:  # Ultra conservative
            min_delay = 4.0
            max_delay = 12.0
        elif self.aggressiveness < 0.4:  # Conservative
            min_delay = 2.5
            max_delay = 8.0
        elif self.aggressiveness < 0.7:  # Moderate
            min_delay = 1.5
            max_delay = 5.0
        else:  # Aggressive
            min_delay = 0.8
            max_delay = 3.0
            
        # Use log-normal distribution for realistic timing
        mu = np.log(base_delay)
        sigma = 0.5
        delay = np.random.lognormal(mu, sigma)
        
        return np.clip(delay, min_delay, max_delay)
    
    def get_session_duration(self) -> float:
        """Generate realistic session duration (minutes)"""
        if self.aggressiveness < 0.3:
            # Short sessions, 2-8 minutes
            return random.uniform(2, 8)
        elif self.aggressiveness < 0.6:
            # Medium sessions, 5-15 minutes
            return random.uniform(5, 15)
        else:
            # Longer sessions, 8-25 minutes
            return random.uniform(8, 25)
    
    def get_daily_session_count(self) -> int:
        """Get number of sessions per day"""
        if self.aggressiveness < 0.3:
            return random.randint(1, 3)
        elif self.aggressiveness < 0.6:
            return random.randint(2, 5)
        else:
            return random.randint(3, 8)
    
    def should_take_break(self, current_session_time: float) -> bool:
        """Determine if account should take a break"""
        session_duration = self.get_session_duration()
        
        # Add random micro-breaks
        if current_session_time > 3 and random.random() < 0.15:
            return True
            
        return current_session_time >= session_duration
    
    def get_break_duration(self) -> float:
        """Get break duration between sessions (minutes)"""
        if self.aggressiveness < 0.3:
            # Long breaks: 30 minutes to 4 hours
            return random.uniform(30, 240)
        elif self.aggressiveness < 0.6:
            # Medium breaks: 15 minutes to 2 hours
            return random.uniform(15, 120)
        else:
            # Short breaks: 5 minutes to 1 hour
            return random.uniform(5, 60)

class TouchPatternGenerator:
    """Generates natural touch patterns with Bezier curves"""
    
    def __init__(self):
        self.screen_width = 1080
        self.screen_height = 1920
        
    def generate_bezier_swipe(self, start: Tuple[int, int], end: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Generate natural swipe path using Bezier curves"""
        # Create control points for natural curve
        control_points = self._create_control_points(start, end)
        
        # Generate points along curve
        num_points = random.randint(15, 30)
        t_values = np.linspace(0, 1, num_points)
        
        points = []
        for t in t_values:
            point = self._bezier_point(control_points, t)
            # Add micro-jitter for realism
            jitter_x = random.uniform(-2, 2)
            jitter_y = random.uniform(-2, 2)
            points.append((
                int(point[0] + jitter_x),
                int(point[1] + jitter_y)
            ))
            
        return points
    
    def _create_control_points(self, start: Tuple[int, int], end: Tuple[int, int]) -> List[Tuple[float, float]]:
        """Create control points for natural swipe curve"""
        # Add control points for natural arc
        distance = ((end[0] - start[0])**2 + (end[1] - start[1])**2)**0.5
        
        # Create slight arc in swipe
        mid_x = (start[0] + end[0]) / 2
        mid_y = (start[1] + end[1]) / 2
        
        # Add perpendicular offset for natural curve
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        
        # Perpendicular vector
        perp_x = -dy
        perp_y = dx
        
        # Normalize and scale
        perp_length = (perp_x**2 + perp_y**2)**0.5
        if perp_length > 0:
            perp_x = perp_x / perp_length * random.uniform(10, 30)
            perp_y = perp_y / perp_length * random.uniform(10, 30)
        
        control_point = (mid_x + perp_x, mid_y + perp_y)
        
        return [start, control_point, end]
    
    def _bezier_point(self, control_points: List[Tuple[float, float]], t: float) -> Tuple[float, float]:
        """Calculate point on Bezier curve at parameter t"""
        n = len(control_points) - 1
        x = y = 0
        
        for i, (px, py) in enumerate(control_points):
            # Bernstein polynomial
            coeff = self._binomial_coeff(n, i) * (t**i) * ((1-t)**(n-i))
            x += coeff * px
            y += coeff * py
            
        return (x, y)
    
    def _binomial_coeff(self, n: int, k: int) -> int:
        """Calculate binomial coefficient"""
        if k > n - k:
            k = n - k
        result = 1
        for i in range(k):
            result = result * (n - i) // (i + 1)
        return result

class CaptchaHandler:
    """Handle Tinder puzzle/CAPTCHA detection and solving"""
    
    def __init__(self):
        self.detection_templates = []
        self.solve_strategies = []
        
    def detect_captcha(self, screenshot_path: str) -> Dict[str, any]:
        """Detect if CAPTCHA is present in screenshot"""
        try:
            import cv2
            
            image = cv2.imread(screenshot_path)
            if image is None:
                return {'detected': False, 'error': 'Could not load screenshot'}
            
            # Convert to grayscale for template matching
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Look for common CAPTCHA indicators
            captcha_indicators = [
                'verify you are human',
                'puzzle',
                'security check',
                'complete the challenge'
            ]
            
            # Use OCR to extract text
            try:
                import pytesseract
                text = pytesseract.image_to_string(gray).lower()
                
                for indicator in captcha_indicators:
                    if indicator in text:
                        return {
                            'detected': True,
                            'type': 'text_challenge',
                            'text': text,
                            'confidence': 0.8
                        }
            except Exception as e:
                logger.warning(f"OCR detection failed: {e}")
            
            # Template matching for visual CAPTCHAs
            # (Would implement with actual Tinder CAPTCHA templates)
            
            return {'detected': False}
            
        except Exception as e:
            logger.error(f"CAPTCHA detection failed: {e}")
            return {'detected': False, 'error': str(e)}
    
    def solve_captcha(self, captcha_data: Dict[str, any]) -> Dict[str, any]:
        """Attempt to solve detected CAPTCHA"""
        if not captcha_data.get('detected'):
            return {'solved': False, 'reason': 'No CAPTCHA detected'}
        
        captcha_type = captcha_data.get('type')
        
        if captcha_type == 'text_challenge':
            # For now, flag for manual intervention
            logger.warning("Text CAPTCHA detected - requires manual intervention")
            return {
                'solved': False,
                'requires_manual': True,
                'type': captcha_type
            }
        
        # Would implement specific solving strategies here
        return {'solved': False, 'reason': 'No solver available for this type'}

class AntiDetectionSystem:
    """Main anti-detection system coordinator"""
    
    def __init__(self, aggressiveness: float = 0.3):
        self.behavior_pattern = BehaviorPattern(aggressiveness)
        self.touch_generator = TouchPatternGenerator()
        self.captcha_handler = CaptchaHandler()
        self.device_fingerprints = {}
        self.session_states = {}
        
    def create_device_fingerprint(self, device_id: str) -> DeviceFingerprint:
        """Create consistent device fingerprint"""
        if device_id in self.device_fingerprints:
            return self.device_fingerprints[device_id]
        
        # Generate consistent fingerprint based on device_id
        random.seed(hash(device_id))
        
        models = [
            "Samsung Galaxy S21", "Samsung Galaxy S22", "Samsung Galaxy A52",
            "Google Pixel 6", "Google Pixel 7", "OnePlus 9", "OnePlus 10",
            "Xiaomi Mi 11", "Xiaomi Redmi Note 11"
        ]
        
        android_versions = ["11", "12", "13", "14"]
        carriers = ["Verizon", "AT&T", "T-Mobile", "Sprint"]
        timezones = ["America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles"]
        
        fingerprint = DeviceFingerprint(
            device_id=device_id,
            model=random.choice(models),
            android_version=random.choice(android_versions),
            brand=random.choice(models).split()[0],
            display_resolution=random.choice([(1080, 1920), (1440, 2560), (1080, 2340)]),
            dpi=random.choice([400, 420, 480, 560]),
            build_id=f"Build_{random.randint(100000, 999999)}",
            timezone=random.choice(timezones),
            language="en-US",
            carrier=random.choice(carriers),
            ip_address=""  # Will be set by proxy
        )
        
        # Reset random seed
        random.seed()
        
        self.device_fingerprints[device_id] = fingerprint
        return fingerprint
    
    def should_continue_session(self, device_id: str) -> bool:
        """Check if session should continue or take break"""
        if device_id not in self.session_states:
            self.session_states[device_id] = {
                'session_start': datetime.now(),
                'total_swipes': 0,
                'last_action': datetime.now()
            }
            return True
        
        session_state = self.session_states[device_id]
        session_duration = (datetime.now() - session_state['session_start']).total_seconds() / 60
        
        return not self.behavior_pattern.should_take_break(session_duration)
    
    def get_next_action_delay(self, device_id: str) -> float:
        """Get delay before next action"""
        return self.behavior_pattern.get_swipe_timing()
    
    def record_action(self, device_id: str, action_type: str):
        """Record action for behavior tracking"""
        if device_id not in self.session_states:
            self.session_states[device_id] = {
                'session_start': datetime.now(),
                'total_swipes': 0,
                'last_action': datetime.now()
            }
        
        self.session_states[device_id]['last_action'] = datetime.now()
        if action_type == 'swipe':
            self.session_states[device_id]['total_swipes'] += 1
    
    def end_session(self, device_id: str) -> float:
        """End current session and return break duration"""
        if device_id in self.session_states:
            del self.session_states[device_id]
        
        return self.behavior_pattern.get_break_duration()
    
    def verify_stealth_setup(self) -> Dict[str, bool]:
        """Verify all stealth systems are working"""
        results = {}
        
        # Check proxy
        try:
            verify_proxy()
            results['proxy'] = True
        except Exception as e:
            logger.error(f"Proxy verification failed: {e}")
            results['proxy'] = False
        
        # Check touch simulation
        try:
            points = self.touch_generator.generate_bezier_swipe((100, 100), (200, 200))
            results['touch_generation'] = len(points) > 10
        except Exception as e:
            logger.error(f"Touch generation failed: {e}")
            results['touch_generation'] = False
        
        # Check behavior patterns
        try:
            delay = self.behavior_pattern.get_swipe_timing()
            results['behavior_patterns'] = 0.5 <= delay <= 15.0
        except Exception as e:
            logger.error(f"Behavior pattern generation failed: {e}")
            results['behavior_patterns'] = False
        
        return results

# Global instance
_anti_detection_system = None

def get_anti_detection_system(aggressiveness: float = 0.3) -> AntiDetectionSystem:
    """Get global anti-detection system instance"""
    global _anti_detection_system
    if _anti_detection_system is None:
        _anti_detection_system = AntiDetectionSystem(aggressiveness)
    return _anti_detection_system

if __name__ == "__main__":
    # Test anti-detection system
    system = AntiDetectionSystem(aggressiveness=0.3)
    
    # Test device fingerprint
    device_id = "test_device_001"
    fingerprint = system.create_device_fingerprint(device_id)
    print(f"Device fingerprint: {fingerprint.model} - {fingerprint.android_version}")
    
    # Test behavior patterns
    for i in range(5):
        delay = system.get_next_action_delay(device_id)
        should_continue = system.should_continue_session(device_id)
        print(f"Action {i+1}: delay={delay:.1f}s, continue={should_continue}")
        system.record_action(device_id, 'swipe')
        time.sleep(0.1)
    
    # Test stealth verification
    stealth_results = system.verify_stealth_setup()
    print(f"Stealth verification: {stealth_results}")