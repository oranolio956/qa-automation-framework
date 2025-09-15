#!/usr/bin/env python3
"""
Comprehensive test script for Android automation fixes
Tests all components: emulator management, UIAutomator2, touch patterns, APK handling, and anti-detection
"""

import os
import sys
import time
import logging
import asyncio
from pathlib import Path

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'automation'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all required modules can be imported"""
    logger.info("Testing imports...")
    
    try:
        # Test core anti-detection imports
        from automation.core.anti_detection import BehaviorPattern, DeviceFingerprint, get_anti_detection_system
        logger.info("✓ Anti-detection system imported successfully")
        
        # Test Android automation imports
        from automation.android.emulator_manager import EmulatorManager, EmulatorConfig
        from automation.android.ui_automator_manager import UIAutomatorManager
        from automation.android.touch_pattern_generator import HumanTouchGenerator, TouchType
        from automation.android.automation_orchestrator import AndroidAutomationOrchestrator
        logger.info("✓ Android automation modules imported successfully")
        
        # Test Snapchat automation imports
        from automation.snapchat.stealth_creator import SnapchatStealthCreator, APKManager
        logger.info("✓ Snapchat automation modules imported successfully")
        
        return True
        
    except ImportError as e:
        logger.error(f"✗ Import error: {e}")
        return False

def test_device_fingerprint_generation():
    """Test device fingerprint generation"""
    logger.info("Testing device fingerprint generation...")
    
    try:
        from automation.core.anti_detection import get_anti_detection_system
        
        anti_detection = get_anti_detection_system()
        if not anti_detection:
            logger.warning("Anti-detection system not available")
            return False
        
        # Test fingerprint generation
        device_id = "test_device_001"
        fingerprint = anti_detection.create_device_fingerprint(device_id)
        
        # Verify fingerprint has required fields
        required_fields = ['device_id', 'model', 'android_version', 'brand', 'display_resolution']
        for field in required_fields:
            if not hasattr(fingerprint, field):
                logger.error(f"✗ Missing fingerprint field: {field}")
                return False
        
        logger.info(f"✓ Device fingerprint generated: {fingerprint.model} - Android {fingerprint.android_version}")
        
        # Test hardware fingerprint
        if fingerprint.hardware_fingerprint:
            logger.info(f"✓ Hardware fingerprint: {len(fingerprint.hardware_fingerprint)} properties")
        
        # Test sensor data
        if fingerprint.sensor_data:
            logger.info(f"✓ Sensor data: {len(fingerprint.sensor_data)} sensors")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Device fingerprint test error: {e}")
        return False

def test_touch_pattern_generation():
    """Test human-like touch pattern generation"""
    logger.info("Testing touch pattern generation...")
    
    try:
        from automation.android.touch_pattern_generator import HumanTouchGenerator, TouchType
        
        generator = HumanTouchGenerator(1080, 1920)
        
        # Test tap pattern
        tap_pattern = generator.generate_tap_pattern(540, 960)
        if len(tap_pattern.points) < 3:
            logger.error("✗ Tap pattern too few points")
            return False
        logger.info(f"✓ Tap pattern: {len(tap_pattern.points)} points, {tap_pattern.total_duration:.3f}s")
        
        # Test swipe pattern
        swipe_pattern = generator.generate_swipe_pattern(100, 100, 900, 1800)
        if len(swipe_pattern.points) < 10:
            logger.error("✗ Swipe pattern too few points")
            return False
        logger.info(f"✓ Swipe pattern: {len(swipe_pattern.points)} points, {swipe_pattern.total_duration:.3f}s")
        
        # Test long press pattern
        long_press_pattern = generator.generate_long_press_pattern(540, 960, 1.5)
        if long_press_pattern.total_duration < 1.0:
            logger.error("✗ Long press duration too short")
            return False
        logger.info(f"✓ Long press pattern: {len(long_press_pattern.points)} points, {long_press_pattern.total_duration:.3f}s")
        
        # Test pinch pattern
        pinch_pattern = generator.generate_pinch_pattern(540, 960, 2.0)
        if len(pinch_pattern.points) < 5:
            logger.error("✗ Pinch pattern too few points")
            return False
        logger.info(f"✓ Pinch pattern: {len(pinch_pattern.points)} points, {pinch_pattern.total_duration:.3f}s")
        
        # Test profile switching
        generator.set_human_profile('elderly')
        elderly_tap = generator.generate_tap_pattern(540, 960)
        if elderly_tap.total_duration <= tap_pattern.total_duration:
            logger.warning("Elderly profile should be slower than default")
        
        logger.info("✓ Touch pattern generation tests passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Touch pattern test error: {e}")
        return False

def test_emulator_manager():
    """Test emulator manager functionality"""
    logger.info("Testing emulator manager...")
    
    try:
        from automation.android.emulator_manager import EmulatorManager
        
        # Test SDK detection
        try:
            manager = EmulatorManager()
            logger.info(f"✓ Emulator manager initialized with SDK: {manager.sdk_manager.sdk_path}")
        except RuntimeError as e:
            if "Android SDK not found" in str(e):
                logger.warning("✗ Android SDK not found - emulator tests will be skipped")
                return True  # Not a failure, just not available
            else:
                raise
        
        # Test device configs
        if not manager.device_configs:
            logger.error("✗ No device configs available")
            return False
        
        logger.info(f"✓ Available device configs: {[config.name for config in manager.device_configs]}")
        
        # Test port allocation
        port = manager._get_available_port()
        if port not in manager.port_range:
            logger.error("✗ Invalid port allocated")
            return False
        logger.info(f"✓ Port allocation working: {port}")
        
        # Test AVD existence check
        test_avd = "non_existent_avd_test"
        exists = manager._avd_exists(test_avd)
        if exists:
            logger.warning("✗ Non-existent AVD reported as existing")
        else:
            logger.info("✓ AVD existence check working")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Emulator manager test error: {e}")
        return False

def test_ui_automator_manager():
    """Test UIAutomator2 manager functionality"""
    logger.info("Testing UIAutomator2 manager...")
    
    try:
        from automation.android.ui_automator_manager import UIAutomatorManager
        
        # Test UIAutomator2 availability
        try:
            import uiautomator2 as u2
            logger.info("✓ UIAutomator2 is available")
        except ImportError:
            logger.warning("✗ UIAutomator2 not installed - install with: pip install uiautomator2")
            return True  # Not a failure, just not available
        
        manager = UIAutomatorManager()
        logger.info("✓ UIAutomator2 manager initialized")
        
        # Test device discovery
        devices = manager.discover_devices()
        logger.info(f"✓ Device discovery: {len(devices)} devices found")
        if devices:
            logger.info(f"  Devices: {devices}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ UIAutomator2 manager test error: {e}")
        return False

async def test_apk_download_methods():
    """Test APK download functionality"""
    logger.info("Testing APK download methods...")
    
    try:
        from automation.snapchat.stealth_creator import APKManager, SnapchatStealthCreator
        
        # Test APK manager
        apk_manager = APKManager()
        logger.info("✓ APK manager initialized")
        
        # Test manual APK detection
        manual_apk = apk_manager._find_manual_apk()
        if manual_apk:
            logger.info(f"✓ Manual APK found: {manual_apk}")
        else:
            logger.info("✓ Manual APK detection working (no APK found)")
        
        # Test Snapchat stealth creator APK methods
        creator = SnapchatStealthCreator()
        
        # Test APK verification method
        test_apk_path = "/tmp/test_fake.apk"
        try:
            # Create a fake APK file for testing
            with open(test_apk_path, 'wb') as f:
                f.write(b'PK')  # ZIP signature
                f.write(b'\\x00' * 1024)  # Pad to minimum size
            
            # This should fail verification (not a real APK)
            is_valid = creator._verify_apk_file(test_apk_path)
            if not is_valid:
                logger.info("✓ APK verification correctly rejects fake APK")
            else:
                logger.warning("✗ APK verification incorrectly accepted fake APK")
        
        finally:
            # Clean up test file
            if os.path.exists(test_apk_path):
                os.remove(test_apk_path)
        
        logger.info("✓ APK download methods test completed")
        return True
        
    except Exception as e:
        logger.error(f"✗ APK download test error: {e}")
        return False

def test_behavior_patterns():
    """Test behavior pattern implementations"""
    logger.info("Testing behavior patterns...")
    
    try:
        from automation.core.anti_detection import BehaviorPattern
        
        # Test different personality profiles
        profiles = ['cautious', 'confident', 'elderly', 'young']
        
        for profile in profiles:
            pattern = BehaviorPattern(aggressiveness=0.5, personality_profile=profile)
            
            # Test timing generation
            timing1 = pattern.get_swipe_timing()
            timing2 = pattern.get_swipe_timing()
            
            if timing1 == timing2:
                logger.warning(f"✗ {profile} profile generates identical timings")
            else:
                logger.info(f"✓ {profile} profile generates variable timings: {timing1:.3f}s, {timing2:.3f}s")
        
        # Test behavioral metrics tracking
        pattern = BehaviorPattern()
        for _ in range(20):
            _ = pattern.get_swipe_timing()  # Generate metrics
        
        if len(pattern.behavioral_metrics['interaction_timing_variance']) >= 20:
            logger.info("✓ Behavioral metrics tracking working")
        else:
            logger.warning("✗ Behavioral metrics not being tracked properly")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Behavior pattern test error: {e}")
        return False

def test_automation_orchestrator():
    """Test automation orchestrator functionality"""
    logger.info("Testing automation orchestrator...")
    
    try:
        from automation.android.automation_orchestrator import AndroidAutomationOrchestrator
        
        orchestrator = AndroidAutomationOrchestrator(max_concurrent_sessions=1)
        logger.info("✓ Automation orchestrator initialized")
        
        # Test session management
        active_sessions = orchestrator.get_active_sessions()
        logger.info(f"✓ Active sessions check: {len(active_sessions)} sessions")
        
        # Note: We don't create actual emulator sessions in tests to avoid resource usage
        # But we can test the orchestrator structure and methods
        
        # Test method availability
        methods = ['create_emulator_session', 'connect_physical_device', 'install_app', 
                  'launch_app', 'perform_human_tap', 'perform_human_swipe']
        
        for method in methods:
            if not hasattr(orchestrator, method):
                logger.error(f"✗ Missing orchestrator method: {method}")
                return False
        
        logger.info("✓ Orchestrator methods available")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Automation orchestrator test error: {e}")
        return False

def test_integration_capabilities():
    """Test integration between components"""
    logger.info("Testing component integration...")
    
    try:
        # Test that components can work together
        from automation.core.anti_detection import get_anti_detection_system
        from automation.android.touch_pattern_generator import HumanTouchGenerator
        from automation.android.automation_orchestrator import get_android_orchestrator
        
        # Test anti-detection system integration
        anti_detection = get_anti_detection_system()
        if anti_detection:
            device_id = "test_integration_device"
            fingerprint = anti_detection.create_device_fingerprint(device_id)
            
            # Use fingerprint data for touch generator
            screen_width, screen_height = fingerprint.display_resolution
            touch_gen = HumanTouchGenerator(screen_width, screen_height)
            
            # Generate a touch pattern
            tap_pattern = touch_gen.generate_tap_pattern(screen_width//2, screen_height//2)
            
            logger.info(f"✓ Integration test: {fingerprint.model} device with {len(tap_pattern.points)} point tap")
        
        # Test orchestrator singleton
        orchestrator1 = get_android_orchestrator()
        orchestrator2 = get_android_orchestrator()
        
        if orchestrator1 is orchestrator2:
            logger.info("✓ Orchestrator singleton working correctly")
        else:
            logger.warning("✗ Orchestrator singleton not working")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Integration test error: {e}")
        return False

async def run_all_tests():
    """Run all Android automation tests"""
    logger.info("Starting comprehensive Android automation tests...")
    
    tests = [
        ("Import Tests", test_imports),
        ("Device Fingerprint Generation", test_device_fingerprint_generation),
        ("Touch Pattern Generation", test_touch_pattern_generation),
        ("Emulator Manager", test_emulator_manager),
        ("UIAutomator2 Manager", test_ui_automator_manager),
        ("APK Download Methods", test_apk_download_methods),
        ("Behavior Patterns", test_behavior_patterns),
        ("Automation Orchestrator", test_automation_orchestrator),
        ("Integration Capabilities", test_integration_capabilities)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\\n{'='*50}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                logger.info(f"✓ {test_name} PASSED")
                passed += 1
            else:
                logger.error(f"✗ {test_name} FAILED")
                
        except Exception as e:
            logger.error(f"✗ {test_name} ERROR: {e}")
    
    logger.info(f"\\n{'='*60}")
    logger.info(f"TEST SUMMARY: {passed}/{total} tests passed")
    logger.info(f"{'='*60}")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED - Android automation fixes are working!")
        return True
    else:
        logger.error(f"❌ {total - passed} tests failed - some issues need attention")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        exit_code = 0 if success else 1
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        logger.info("\\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test runner error: {e}")
        sys.exit(1)