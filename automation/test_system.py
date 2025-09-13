#!/usr/bin/env python3
"""
Tinder Automation System Test Runner
Comprehensive testing and validation of all automation components
"""

import os
import sys
import time
import logging
import json
from typing import Dict, List, Tuple, Optional
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, date

# Import all automation components
from android.emulator_manager import get_emulator_manager, AndroidSDKManager
from core.anti_detection import get_anti_detection_system, BehaviorPattern, TouchPatternGenerator
from tinder.account_creator import get_account_creator, AccountProfile
from tinder.profile_manager import get_profile_manager, BioGenerator, PhotoProcessor
from tinder.warming_scheduler import get_warming_manager, WarmingSchedules
from snapchat.stealth_creator import get_snapchat_creator, SnapchatUsernameGenerator

# Import utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../utils'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestAntiDetection(unittest.TestCase):
    """Test anti-detection system components"""
    
    def setUp(self):
        self.anti_detection = get_anti_detection_system(aggressiveness=0.3)
    
    def test_device_fingerprint_creation(self):
        """Test device fingerprint generation"""
        device_id = "test_device_001"
        fingerprint = self.anti_detection.create_device_fingerprint(device_id)
        
        self.assertIsNotNone(fingerprint.device_id)
        self.assertIsNotNone(fingerprint.model)
        self.assertIsNotNone(fingerprint.android_version)
        self.assertIsInstance(fingerprint.display_resolution, tuple)
        self.assertEqual(len(fingerprint.display_resolution), 2)
        
        # Test consistency - same device_id should generate same fingerprint
        fingerprint2 = self.anti_detection.create_device_fingerprint(device_id)
        self.assertEqual(fingerprint.model, fingerprint2.model)
        self.assertEqual(fingerprint.android_version, fingerprint2.android_version)
    
    def test_behavior_patterns(self):
        """Test behavior pattern generation"""
        behavior = BehaviorPattern(aggressiveness=0.3)
        
        # Test swipe timing
        timing = behavior.get_swipe_timing()
        self.assertIsInstance(timing, float)
        self.assertGreater(timing, 0.5)  # Minimum reasonable delay
        self.assertLess(timing, 15.0)    # Maximum reasonable delay
        
        # Test session duration
        duration = behavior.get_session_duration()
        self.assertIsInstance(duration, float)
        self.assertGreater(duration, 1.0)   # At least 1 minute
        self.assertLess(duration, 30.0)     # At most 30 minutes
        
        # Test daily session count
        sessions = behavior.get_daily_session_count()
        self.assertIsInstance(sessions, int)
        self.assertGreaterEqual(sessions, 1)
        self.assertLessEqual(sessions, 10)
    
    def test_touch_pattern_generation(self):
        """Test touch pattern generation"""
        generator = TouchPatternGenerator()
        
        start_point = (100, 100)
        end_point = (500, 800)
        
        points = generator.generate_bezier_swipe(start_point, end_point)
        
        self.assertIsInstance(points, list)
        self.assertGreater(len(points), 10)  # Should have multiple points
        self.assertLess(len(points), 50)     # But not too many
        
        # First and last points should be close to start/end
        self.assertLess(abs(points[0][0] - start_point[0]), 10)
        self.assertLess(abs(points[-1][0] - end_point[0]), 10)

class TestAccountCreation(unittest.TestCase):
    """Test account creation components"""
    
    def setUp(self):
        self.account_creator = get_account_creator(aggressiveness=0.3)
    
    def test_profile_generation(self):
        """Test random profile generation"""
        profile = self.account_creator.generate_random_profile()
        
        self.assertIsInstance(profile, AccountProfile)
        self.assertIsNotNone(profile.first_name)
        self.assertIsNotNone(profile.birth_date)
        self.assertIn(profile.gender, ["man", "woman"])
        self.assertIn(profile.interested_in, ["men", "women", "everyone"])
        self.assertTrue(profile.phone_number.startswith("+1"))
        self.assertIn("@", profile.email)
        self.assertIsInstance(profile.location, tuple)
        
        # Test with Snapchat username
        snapchat_username = "test_user123"
        profile_with_snap = self.account_creator.generate_random_profile(snapchat_username)
        self.assertEqual(profile_with_snap.snapchat_username, snapchat_username)
        self.assertIn("SC: test_user123", profile_with_snap.bio)

class TestProfileManagement(unittest.TestCase):
    """Test profile management components"""
    
    def setUp(self):
        self.profile_manager = get_profile_manager()
    
    def test_bio_generation(self):
        """Test bio generation"""
        bio_generator = BioGenerator()
        
        # Test basic bio generation
        bio = bio_generator.generate_bio()
        self.assertIsInstance(bio, str)
        self.assertGreater(len(bio), 20)  # Should be substantial
        self.assertLess(len(bio), 500)    # Under Tinder limit
        
        # Test with Snapchat username
        bio_with_snap = bio_generator.generate_bio(snapchat_username="testuser123")
        self.assertIn("SC: testuser123", bio_with_snap)
        
        # Test with custom interests
        interests = ['travel', 'coffee', 'dogs']
        bio_with_interests = bio_generator.generate_bio(interests=interests)
        # Should contain some emojis related to interests
        self.assertTrue(any(emoji in bio_with_interests for emoji in ['✈️', '☕', '🐕']))
    
    def test_bio_optimization(self):
        """Test bio optimization"""
        bio_generator = BioGenerator()
        
        original_bio = "I love coffee and dogs"
        optimized_bio = bio_generator.optimize_bio_for_engagement(original_bio)
        
        # Should add emojis
        self.assertIn("☕", optimized_bio)
        self.assertIn("🐕", optimized_bio)

class TestWarmingSystem(unittest.TestCase):
    """Test account warming system"""
    
    def setUp(self):
        self.warming_manager = get_warming_manager()
    
    def test_warming_schedules(self):
        """Test warming schedule generation"""
        schedules = [
            WarmingSchedules.day_1_schedule(),
            WarmingSchedules.week_1_schedule(),
            WarmingSchedules.week_2_schedule(),
            WarmingSchedules.active_schedule()
        ]
        
        # Verify progression of aggressiveness
        for i in range(len(schedules) - 1):
            current = schedules[i]
            next_schedule = schedules[i + 1]
            
            # Each phase should be more aggressive
            self.assertLessEqual(current.daily_sessions, next_schedule.daily_sessions)
            self.assertLessEqual(current.activities_per_session, next_schedule.activities_per_session)
            self.assertLessEqual(current.swipe_ratio_right, next_schedule.swipe_ratio_right)
    
    def test_schedule_validation(self):
        """Test schedule parameter validation"""
        day_1 = WarmingSchedules.day_1_schedule()
        
        # Day 1 should be very conservative
        self.assertLessEqual(day_1.daily_sessions, 3)
        self.assertLessEqual(day_1.swipe_ratio_right, 0.2)
        self.assertEqual(day_1.super_like_frequency, 0.0)
        self.assertEqual(day_1.messaging_probability, 0.0)
        
        # Active should be most aggressive
        active = WarmingSchedules.active_schedule()
        self.assertGreaterEqual(active.daily_sessions, 5)
        self.assertGreaterEqual(active.swipe_ratio_right, 0.4)
        self.assertGreaterEqual(active.super_like_frequency, 0.5)

class TestSnapchatCreation(unittest.TestCase):
    """Test Snapchat creation system"""
    
    def setUp(self):
        self.snapchat_creator = get_snapchat_creator()
    
    def test_username_generation(self):
        """Test Snapchat username generation"""
        generator = SnapchatUsernameGenerator()
        
        # Test single username
        username = generator.generate_username("John", "Smith", 1995)
        self.assertIsInstance(username, str)
        self.assertGreaterEqual(len(username), 6)   # Minimum length
        self.assertLessEqual(len(username), 15)     # Maximum length
        self.assertTrue(username[0].isalpha())      # Should start with letter
        
        # Test multiple usernames
        usernames = generator.generate_multiple_usernames(5, "Jane", "Doe")
        self.assertEqual(len(usernames), 5)
        self.assertEqual(len(set(usernames)), 5)    # Should all be unique
    
    def test_profile_generation(self):
        """Test Snapchat profile generation"""
        profile = self.snapchat_creator.generate_stealth_profile("Alex")
        
        self.assertEqual(profile.display_name.split()[0], "Alex")
        self.assertIsInstance(profile.username, str)
        self.assertIn("@", profile.email)
        self.assertTrue(profile.phone_number.startswith("+1"))
        self.assertIsInstance(profile.birth_date, date)
        self.assertGreaterEqual(len(profile.password), 8)

class TestIntegration(unittest.TestCase):
    """Integration tests for system components"""
    
    def test_system_initialization(self):
        """Test that all systems can be initialized"""
        systems = {
            'emulator_manager': get_emulator_manager,
            'anti_detection': lambda: get_anti_detection_system(0.3),
            'account_creator': lambda: get_account_creator(0.3),
            'profile_manager': get_profile_manager,
            'warming_manager': get_warming_manager,
            'snapchat_creator': get_snapchat_creator
        }
        
        for name, factory in systems.items():
            try:
                instance = factory()
                self.assertIsNotNone(instance)
                logger.info(f"✅ {name} initialized successfully")
            except Exception as e:
                self.fail(f"❌ {name} initialization failed: {e}")
    
    def test_end_to_end_flow(self):
        """Test simulated end-to-end flow"""
        # This would test the full flow in a mocked environment
        # Create mock emulator instance
        mock_emulator = MagicMock()
        mock_emulator.device_id = "emulator-5554"
        mock_emulator.is_ready = True
        
        # Test profile generation
        account_creator = get_account_creator(0.3)
        profile = account_creator.generate_random_profile("snapchat_user")
        
        # Verify profile has all required fields
        required_fields = ['first_name', 'birth_date', 'gender', 'phone_number', 'email', 'bio']
        for field in required_fields:
            self.assertIsNotNone(getattr(profile, field))
        
        # Test warming schedule assignment
        warming_manager = get_warming_manager()
        
        # Create mock account result
        from tinder.account_creator import AccountCreationResult
        mock_result = AccountCreationResult(
            success=True,
            account_id="test_account_001",
            profile=profile,
            device_id=mock_emulator.device_id,
            creation_time=datetime.now(),
            verification_status="verified"
        )
        
        # This would normally add to warming system
        # warming_manager.add_account_for_warming(mock_result, mock_emulator.device_id)
        
        logger.info("✅ End-to-end flow test completed")

def run_performance_tests():
    """Run performance tests"""
    logger.info("Running performance tests...")
    
    # Test touch pattern generation speed
    start_time = time.time()
    generator = TouchPatternGenerator()
    
    for _ in range(100):
        points = generator.generate_bezier_swipe((100, 100), (500, 800))
    
    touch_time = time.time() - start_time
    logger.info(f"Touch pattern generation: {touch_time:.3f}s for 100 patterns")
    
    # Test bio generation speed
    start_time = time.time()
    bio_generator = BioGenerator()
    
    for _ in range(100):
        bio = bio_generator.generate_bio()
    
    bio_time = time.time() - start_time
    logger.info(f"Bio generation: {bio_time:.3f}s for 100 bios")
    
    # Test username generation speed
    start_time = time.time()
    username_generator = SnapchatUsernameGenerator()
    
    for _ in range(100):
        username = username_generator.generate_username("Test", "User", 1995)
    
    username_time = time.time() - start_time
    logger.info(f"Username generation: {username_time:.3f}s for 100 usernames")

def run_system_validation():
    """Run system validation checks"""
    logger.info("Running system validation...")
    
    validation_results = {}
    
    # Check if Android SDK is available
    try:
        sdk_manager = AndroidSDKManager()
        validation_results['android_sdk'] = os.path.exists(sdk_manager.emulator)
    except Exception as e:
        validation_results['android_sdk'] = False
        logger.warning(f"Android SDK validation failed: {e}")
    
    # Check if required directories exist
    automation_dir = os.path.dirname(__file__)
    required_dirs = ['android', 'core', 'tinder', 'snapchat']
    
    for dir_name in required_dirs:
        dir_path = os.path.join(automation_dir, dir_name)
        validation_results[f'dir_{dir_name}'] = os.path.exists(dir_path)
    
    # Check if requirements can be imported
    required_imports = [
        ('numpy', 'numpy'),
        ('opencv', 'cv2'),  
        ('redis', 'redis'),
        ('pydantic', 'pydantic'),
        ('faker', 'faker')
    ]
    
    for name, import_name in required_imports:
        try:
            __import__(import_name)
            validation_results[f'import_{name}'] = True
        except ImportError:
            validation_results[f'import_{name}'] = False
            logger.warning(f"Import validation failed for {name}")
    
    # Print validation results
    logger.info("System Validation Results:")
    for check, result in validation_results.items():
        status = "✅" if result else "❌"
        logger.info(f"  {status} {check}: {'PASS' if result else 'FAIL'}")
    
    return all(validation_results.values())

def main():
    """Main test runner"""
    print("🧪 Tinder Automation System Test Suite")
    print("=" * 50)
    
    # Run system validation first
    if not run_system_validation():
        logger.error("❌ System validation failed - some tests may not run")
    
    # Run performance tests
    run_performance_tests()
    
    # Run unit tests
    logger.info("Running unit tests...")
    
    # Create test suite
    test_classes = [
        TestAntiDetection,
        TestAccountCreation, 
        TestProfileManagement,
        TestWarmingSystem,
        TestSnapchatCreation,
        TestIntegration
    ]
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            error_msg = traceback.split('AssertionError: ')[-1].split('\n')[0]
            print(f"- {test}: {error_msg}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            error_lines = traceback.split('\n')
            error_msg = error_lines[-2] if len(error_lines) > 1 else str(traceback)
            print(f"- {test}: {error_msg}")
    
    # Return success if all tests passed
    return len(result.failures) == 0 and len(result.errors) == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)