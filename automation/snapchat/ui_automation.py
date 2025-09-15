#!/usr/bin/env python3
"""
UI Automation Module for Snapchat

Handles UIAutomator2 interactions with proper error handling and reliability.
Extracted from stealth_creator.py for better maintainability.
"""

import os
import time
import random
import logging
from typing import Optional, Dict, List, Tuple, Any, Union
from dataclasses import dataclass
from enum import Enum
import json

try:
    import uiautomator2 as u2
except ImportError:
    u2 = None
    logging.warning("uiautomator2 not available - UI automation will be disabled")

# Import unified device management and configuration
try:
    # Try relative imports first (when used as package)
    from .device_types import get_device_manager, resolve_device_id, get_adb_address, DeviceCompatibilityAdapter
    from .config import get_config
except ImportError:
    # Fallback to absolute imports (when run directly)
    from device_types import get_device_manager, resolve_device_id, get_adb_address, DeviceCompatibilityAdapter
    from config import get_config

logger = logging.getLogger(__name__)


class UIElementState(Enum):
    """States for UI elements"""
    NOT_FOUND = "not_found"
    FOUND = "found"
    CLICKED = "clicked"
    TEXT_ENTERED = "text_entered"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class UISelector:
    """Selector configuration for UI elements"""
    text: Optional[str] = None
    resource_id: Optional[str] = None
    class_name: Optional[str] = None
    description: Optional[str] = None
    text_contains: Optional[str] = None
    description_contains: Optional[str] = None
    index: Optional[int] = None
    enabled: Optional[bool] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for u2 selector"""
        selector = {}
        if self.text is not None:
            selector['text'] = self.text
        if self.resource_id is not None:
            selector['resourceId'] = self.resource_id
        if self.class_name is not None:
            selector['className'] = self.class_name
        if self.description is not None:
            selector['description'] = self.description
        if self.text_contains is not None:
            selector['textContains'] = self.text_contains
        if self.description_contains is not None:
            selector['descriptionContains'] = self.description_contains
        if self.index is not None:
            selector['index'] = self.index
        if self.enabled is not None:
            selector['enabled'] = self.enabled
        return selector

# Human-like delay helper
try:
    from automation.core.timing_engine import next_delay as _next_delay
except Exception:
    def _next_delay(**kwargs):  # type: ignore
        return kwargs.get('base_seconds', 0.5)

def _sleep_human(task: str, base_seconds: float) -> None:
    time.sleep(_next_delay(task=task, base_seconds=base_seconds))


@dataclass
class UIActionResult:
    """Result of UI action"""
    success: bool
    state: UIElementState
    message: str
    screenshot_path: Optional[str] = None
    element_bounds: Optional[Dict] = None
    retry_count: int = 0


class SnapchatUIAutomator:
    """Reliable UI automation for Snapchat with proper error handling"""
    
    def __init__(self, device_identifier: Union[str, Any], anti_detection=None):
        # Use unified device management to resolve device ID
        self.device_identifier = device_identifier
        self.device_id = DeviceCompatibilityAdapter.ensure_string_device_id(device_identifier)
        self.adb_address = DeviceCompatibilityAdapter.ensure_adb_address(device_identifier)
        
        self.anti_detection = anti_detection
        self.u2_device = None
        self.screenshot_counter = 0
        
        # Load configuration
        self.config = get_config()
        
        # Selector configurations for common Snapchat elements
        self.selectors = self._initialize_selectors()
        
        # Retry configuration from config
        self.max_retries = self.config.config.max_retries
        self.base_delay = self.config.config.base_delay
        self.max_delay = self.config.config.max_delay
        
        # Connect to device
        self._connect_device()
    
    def _initialize_selectors(self) -> Dict[str, List[UISelector]]:
        """Initialize common Snapchat UI selectors"""
        return {
            "sign_up": [
                UISelector(text="Sign Up"),
                UISelector(text="SIGN UP"),
                UISelector(description="Sign up"),
                UISelector(resource_id="com.snapchat.android:id/sign_up_button")
            ],
            "continue": [
                UISelector(text="Continue"),
                UISelector(text="CONTINUE"),
                UISelector(description="Continue"),
                UISelector(resource_id="com.snapchat.android:id/continue_button")
            ],
            "first_name": [
                UISelector(text="First name"),
                UISelector(text="First Name"),
                UISelector(resource_id="com.snapchat.android:id/first_name_edit_text"),
                UISelector(class_name="android.widget.EditText", index=0)
            ],
            "last_name": [
                UISelector(text="Last name"),
                UISelector(text="Last Name"), 
                UISelector(resource_id="com.snapchat.android:id/last_name_edit_text"),
                UISelector(class_name="android.widget.EditText", index=1)
            ],
            "username": [
                UISelector(text="Username"),
                UISelector(text="USERNAME"),
                UISelector(resource_id="com.snapchat.android:id/username_edit_text"),
                UISelector(description_contains="username")
            ],
            "password": [
                UISelector(text="Password"),
                UISelector(text="PASSWORD"),
                UISelector(resource_id="com.snapchat.android:id/password_edit_text"),
                UISelector(class_name="android.widget.EditText", description_contains="password")
            ],
            "phone": [
                UISelector(text="Phone"),
                UISelector(text="Phone number"),
                UISelector(resource_id="com.snapchat.android:id/phone_edit_text"),
                UISelector(description_contains="phone")
            ],
            "verification_code": [
                UISelector(text="Verification code"),
                UISelector(text="Enter code"),
                UISelector(resource_id="com.snapchat.android:id/verification_code_edit_text"),
                UISelector(class_name="android.widget.EditText", description_contains="code")
            ],
            "camera": [
                UISelector(description="Camera"),
                UISelector(resource_id="com.snapchat.android:id/camera_capture_button"),
                UISelector(text="Camera")
            ]
        }
    
    def _connect_device(self) -> bool:
        """Connect to UIAutomator2 device"""
        try:
            if u2 is None:
                logger.error("uiautomator2 not available")
                return False
            
            logger.info(f"Connecting to UIAutomator2 device: {self.device_id} ({self.adb_address})")
            
            # Use ADB address for connection (more reliable than device ID)
            self.u2_device = u2.connect(self.adb_address)
            
            # Test connection
            device_info = self.u2_device.info
            logger.info(f"Connected to device: {device_info.get('productName', 'Unknown')} "
                       f"(Android {device_info.get('version', 'Unknown')})")
            
            # Update device status in unified manager
            device_manager = get_device_manager()
            device_manager.update_device_status(self.device_identifier, True)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to UIAutomator2 device {self.device_id}: {e}")
            
            # Update device status in unified manager
            device_manager = get_device_manager()
            device_manager.update_device_status(self.device_identifier, False)
            
            return False
    
    def wait_for_element(self, element_name: str, timeout: int = 10) -> UIActionResult:
        """Wait for element to appear with multiple selector fallbacks"""
        try:
            if not self.u2_device:
                return UIActionResult(False, UIElementState.ERROR, "Device not connected")
            
            selectors = self.selectors.get(element_name, [])
            if not selectors:
                # Fallback to text-based selector
                selectors = [UISelector(text=element_name)]
            
            logger.debug(f"Waiting for element '{element_name}' with {len(selectors)} selectors")
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                for i, selector in enumerate(selectors):
                    try:
                        element = self.u2_device(**selector.to_dict())
                        if element.wait(timeout=2):  # Short wait for each selector
                            bounds = element.info.get('bounds', {})
                            logger.debug(f"Element '{element_name}' found with selector {i}")
                            return UIActionResult(
                                True, 
                                UIElementState.FOUND, 
                                f"Element found with selector {i}",
                                element_bounds=bounds
                            )
                    except Exception as e:
                        logger.debug(f"Selector {i} failed: {e}")
                        continue
                
                # Brief pause before trying again
                _sleep_human("navigation", 0.5)
            
            logger.warning(f"Element '{element_name}' not found after {timeout}s")
            return UIActionResult(False, UIElementState.TIMEOUT, f"Timeout after {timeout}s")
            
        except Exception as e:
            logger.error(f"Error waiting for element '{element_name}': {e}")
            return UIActionResult(False, UIElementState.ERROR, str(e))
    
    def tap_element(self, element_name: str, timeout: int = 10) -> UIActionResult:
        """Tap element with retry logic and proper delays"""
        try:
            # First wait for element
            wait_result = self.wait_for_element(element_name, timeout)
            if not wait_result.success:
                return wait_result
            
            # Get selectors for this element
            selectors = self.selectors.get(element_name, [UISelector(text=element_name)])
            
            for retry in range(self.max_retries):
                for selector in selectors:
                    try:
                        element = self.u2_device(**selector.to_dict())
                        if element.exists:
                            # Add anti-detection delay
                            self._add_human_delay()
                            
                            # Perform tap
                            element.click()
                            
                            # Verify tap was successful (element should change or disappear)
                            _sleep_human("tap", 0.5)  # Brief pause for UI update
                            
                            logger.info(f"Successfully tapped element '{element_name}'")
                            return UIActionResult(
                                True, 
                                UIElementState.CLICKED, 
                                f"Element tapped successfully",
                                retry_count=retry
                            )
                    except Exception as e:
                        logger.debug(f"Tap attempt {retry+1} failed: {e}")
                        continue
                
                # Retry delay with exponential backoff
                if retry < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** retry), self.max_delay)
                    time.sleep(delay)
            
            return UIActionResult(False, UIElementState.ERROR, f"Failed to tap after {self.max_retries} retries")
            
        except Exception as e:
            logger.error(f"Error tapping element '{element_name}': {e}")
            return UIActionResult(False, UIElementState.ERROR, str(e))
    
    def enter_text(self, text: str, element_name: str, timeout: int = 10) -> UIActionResult:
        """Enter text into element with proper clearing and validation"""
        try:
            # Wait for element
            wait_result = self.wait_for_element(element_name, timeout)
            if not wait_result.success:
                return wait_result
            
            selectors = self.selectors.get(element_name, [UISelector(text=element_name)])
            
            for retry in range(self.max_retries):
                for selector in selectors:
                    try:
                        element = self.u2_device(**selector.to_dict())
                        if element.exists:
                            # Add anti-detection delay
                            self._add_human_delay()
                            
                            # Clear existing text
                            element.clear_text()
                            _sleep_human("typing", 0.8)
                            
                            # Enter new text
                            element.set_text(text)
                            
                            # Verify text was entered
                            _sleep_human("typing", 0.5)
                            current_text = element.get_text()
                            if current_text == text:
                                logger.info(f"Successfully entered text in '{element_name}'")
                                return UIActionResult(
                                    True, 
                                    UIElementState.TEXT_ENTERED, 
                                    f"Text entered successfully",
                                    retry_count=retry
                                )
                            else:
                                logger.warning(f"Text verification failed: expected '{text}', got '{current_text}'")
                    
                    except Exception as e:
                        logger.debug(f"Text entry attempt {retry+1} failed: {e}")
                        continue
                
                # Retry delay
                if retry < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** retry), self.max_delay)
                    time.sleep(delay)
            
            return UIActionResult(False, UIElementState.ERROR, f"Failed to enter text after {self.max_retries} retries")
            
        except Exception as e:
            logger.error(f"Error entering text in '{element_name}': {e}")
            return UIActionResult(False, UIElementState.ERROR, str(e))
    
    def take_screenshot(self, save_path: str = None) -> str:
        """Take screenshot with optional save path"""
        try:
            if not self.u2_device:
                raise RuntimeError("Device not connected")
            
            if save_path is None:
                # Use configuration manager for proper path generation
                try:
                    from .config import get_config
                    config = get_config()
                    save_path = config.get_screenshot_path(self.device_id, str(int(time.time())))
                except ImportError:
                    # Fallback to temp directory
                    import tempfile
                    self.screenshot_counter += 1
                    temp_dir = tempfile.gettempdir()
                    save_path = f"{temp_dir}/snapchat_screenshot_{self.device_id}_{self.screenshot_counter}_{int(time.time())}.png"
            
            # Take screenshot
            self.u2_device.screenshot(save_path)
            
            # Verify file was created
            if os.path.exists(save_path):
                logger.debug(f"Screenshot saved: {save_path}")
                return save_path
            else:
                raise RuntimeError("Screenshot file not created")
                
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return None
    
    def get_ui_hierarchy(self) -> Optional[Dict]:
        """Get current UI hierarchy for debugging"""
        try:
            if not self.u2_device:
                return None
            
            # Get UI dump
            hierarchy = self.u2_device.dump_hierarchy()
            return hierarchy
            
        except Exception as e:
            logger.error(f"Failed to get UI hierarchy: {e}")
            return None
    
    def wait_for_stable_ui(self, duration: float = 2.0, max_wait: float = 10.0) -> bool:
        """Wait for UI to stabilize (no changes for specified duration)"""
        try:
            if not self.u2_device:
                return False
            
            last_hierarchy = None
            stable_start = None
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                current_hierarchy = self.get_ui_hierarchy()
                
                if current_hierarchy == last_hierarchy:
                    if stable_start is None:
                        stable_start = time.time()
                    elif time.time() - stable_start >= duration:
                        logger.debug(f"UI stabilized after {time.time() - start_time:.1f}s")
                        return True
                else:
                    stable_start = None
                    last_hierarchy = current_hierarchy
                
                _sleep_human("navigation", 0.5)
            
            logger.warning(f"UI did not stabilize within {max_wait}s")
            return False
            
        except Exception as e:
            logger.error(f"Error waiting for stable UI: {e}")
            return False
    
    def find_element_by_text_pattern(self, pattern: str, timeout: int = 5) -> List[Dict]:
        """Find elements matching text pattern"""
        try:
            if not self.u2_device:
                return []
            
            elements = []
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    # Use xpath to find elements with text containing pattern
                    for element in self.u2_device.xpath(f'//*[contains(@text, "{pattern}")]').all():
                        element_info = element.info
                        elements.append(element_info)
                    
                    if elements:
                        break
                        
                except Exception:
                    pass
                
                time.sleep(0.5)
            
            return elements
            
        except Exception as e:
            logger.error(f"Error finding elements by pattern '{pattern}': {e}")
            return []
    
    def _add_human_delay(self):
        """Add human-like delay between actions"""
        if self.anti_detection:
            delay = self.anti_detection.get_next_action_delay(self.device_id)
            time.sleep(delay)
        else:
            # Fallback to random delay
            time.sleep(random.uniform(0.5, 2.0))
    
    def close_connection(self):
        """Clean up connection"""
        try:
            if self.u2_device:
                # Clean up any watchers or listeners
                self.u2_device = None
                logger.info(f"Closed UIAutomator2 connection for {self.device_id}")
        except Exception as e:
            logger.error(f"Error closing UIAutomator2 connection: {e}")
    
    # Backward compatibility methods that return booleans (for stealth_creator.py integration)
    
    def wait_for_element_bool(self, element_name: str, timeout: int = 10) -> bool:
        """Wait for element - returns boolean for backward compatibility"""
        result = self.wait_for_element(element_name, timeout)
        return result.success
    
    def tap_element_bool(self, element_name: str, timeout: int = 10) -> bool:
        """Tap element - returns boolean for backward compatibility"""
        result = self.tap_element(element_name, timeout)
        return result.success
    
    def enter_text_bool(self, text: str, element_name: str, timeout: int = 10) -> bool:
        """Enter text - returns boolean for backward compatibility"""
        result = self.enter_text(text, element_name, timeout)
        return result.success


class SnapchatUIHelper:
    """Helper class with high-level Snapchat UI operations"""
    
    def __init__(self, automator: SnapchatUIAutomator):
        self.automator = automator
    
    def navigate_to_registration(self) -> bool:
        """Navigate to registration screen"""
        try:
            # Wait for app to load
            if not self.automator.wait_for_element("sign_up", timeout=30).success:
                logger.error("Sign up button not found")
                return False
            
            # Tap sign up
            if not self.automator.tap_element("sign_up").success:
                logger.error("Failed to tap sign up")
                return False
            
            # Wait for name entry screen
            if not self.automator.wait_for_element("first_name", timeout=15).success:
                logger.error("Name entry screen not reached")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error navigating to registration: {e}")
            return False
    
    def fill_name_fields(self, first_name: str, last_name: str) -> bool:
        """Fill first and last name fields"""
        try:
            # Enter first name
            result = self.automator.enter_text(first_name, "first_name")
            if not result.success:
                logger.error(f"Failed to enter first name: {result.message}")
                return False
            
            # Enter last name
            result = self.automator.enter_text(last_name, "last_name")
            if not result.success:
                logger.error(f"Failed to enter last name: {result.message}")
                return False
            
            # Continue
            result = self.automator.tap_element("continue")
            if not result.success:
                logger.error(f"Failed to continue after name entry: {result.message}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error filling name fields: {e}")
            return False
    
    def verify_main_screen_reached(self) -> bool:
        """Verify that main Snapchat screen is reached"""
        try:
            # Look for camera interface
            result = self.automator.wait_for_element("camera", timeout=30)
            return result.success
            
        except Exception as e:
            logger.error(f"Error verifying main screen: {e}")
            return False


def get_snapchat_automator(device_id: str, anti_detection=None) -> SnapchatUIAutomator:
    """Get Snapchat UI automator instance"""
    return SnapchatUIAutomator(device_id, anti_detection)


if __name__ == "__main__":
    # Command line interface for testing
    import argparse
    
    parser = argparse.ArgumentParser(description='Snapchat UI Automation Tester')
    parser.add_argument('--device', type=str, required=True, help='Device ID')
    parser.add_argument('--screenshot', action='store_true', help='Take screenshot')
    parser.add_argument('--hierarchy', action='store_true', help='Get UI hierarchy')
    parser.add_argument('--find', type=str, help='Find element by text pattern')
    
    args = parser.parse_args()
    
    automator = get_snapchat_automator(args.device)
    
    if args.screenshot:
        path = automator.take_screenshot()
        print(f"Screenshot saved: {path}")
    
    elif args.hierarchy:
        hierarchy = automator.get_ui_hierarchy()
        if hierarchy:
            print(json.dumps(hierarchy, indent=2))
        else:
            print("Failed to get UI hierarchy")
    
    elif args.find:
        elements = automator.find_element_by_text_pattern(args.find)
        print(f"Found {len(elements)} elements matching '{args.find}':")
        for element in elements:
            print(f"  Text: {element.get('text', 'N/A')}")
            print(f"  Bounds: {element.get('bounds', 'N/A')}")
    
    else:
        parser.print_help()
    
    automator.close_connection()