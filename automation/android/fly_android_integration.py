#!/usr/bin/env python3
"""
Fly.io Android Farm Integration for Snapchat Automation
Handles remote device connections, UIAutomator2 setup, and automation coordination
"""

import os
import sys
import time
import logging
import subprocess
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../telegram_bot'))

# UIAutomator2 import with fallback
try:
    import uiautomator2 as u2
    U2_AVAILABLE = True
except ImportError:
    U2_AVAILABLE = False
    u2 = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class FlyAndroidDevice:
    """Represents a connected fly.io Android device"""
    device_id: str
    host: str
    port: int
    u2_device: Any = None
    is_connected: bool = False
    last_activity: float = 0.0
    device_info: Optional[Dict] = None

class FlyAndroidManager:
    """Manages fly.io Android farm devices for Snapchat automation"""
    
    def __init__(self):
        self.connected_devices: Dict[str, FlyAndroidDevice] = {}
        self.farm_host = os.getenv('FLY_ANDROID_HOST', 'android-device-farm-prod.fly.dev')
        self.farm_ports = [5555, 5556, 5557, 5558, 5559]  # Multiple device ports
        
        # Import managers
        self.ui_manager = None
        self.remote_manager = None
        
        try:
            from ui_automator_manager import get_ui_automator_manager
            self.ui_manager = get_ui_automator_manager()
            logger.info("UIAutomator manager loaded")
        except ImportError:
            logger.warning("UIAutomator manager not available")
        
        try:
            from android_remote_config import get_remote_android_manager
            self.remote_manager = get_remote_android_manager()
            logger.info("Remote Android manager loaded")
        except ImportError:
            logger.warning("Remote Android manager not available")
    
    def discover_farm_devices(self) -> List[str]:
        """Discover available fly.io Android farm devices"""
        available_devices = []
        
        try:
            logger.info(f"Discovering devices on Android farm: {self.farm_host}")
            
            # Method 1: Use remote manager if available
            if self.remote_manager:
                try:
                    device = self.remote_manager.connect_to_fly_android_farm()
                    if device:
                        available_devices.append(device.device_id)
                        logger.info(f"Found farm device via remote manager: {device.device_id}")
                except Exception as e:
                    logger.warning(f"Remote manager connection failed: {e}")
            
            # Method 2: Try direct connections to multiple ports
            for port in self.farm_ports:
                try:
                    device_id = f"{self.farm_host}:{port}"
                    
                    # Test ADB connection
                    result = subprocess.run(
                        ['adb', 'connect', device_id],
                        capture_output=True,
                        text=True,
                        timeout=15
                    )
                    
                    if result.returncode == 0 and 'connected' in result.stdout.lower():
                        # Verify device is responsive
                        test_result = subprocess.run(
                            ['adb', '-s', device_id, 'shell', 'getprop', 'sys.boot_completed'],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        
                        if test_result.returncode == 0 and test_result.stdout.strip() == '1':
                            available_devices.append(device_id)
                            logger.info(f"Verified farm device: {device_id}")
                        else:
                            logger.debug(f"Device {device_id} not ready")
                    else:
                        logger.debug(f"Could not connect to {device_id}")
                        
                except Exception as e:
                    logger.debug(f"Error testing {device_id}: {e}")
                    continue
            
            # Remove duplicates
            available_devices = list(set(available_devices))
            logger.info(f"Found {len(available_devices)} available farm devices: {available_devices}")
            
        except Exception as e:
            logger.error(f"Error discovering farm devices: {e}")
        
        return available_devices
    
    def connect_to_farm_device(self, device_id: str = None) -> Optional[FlyAndroidDevice]:
        """Connect to a specific farm device or get any available one"""
        try:
            if device_id:
                target_devices = [device_id]
            else:
                # Get any available device
                target_devices = self.discover_farm_devices()
                if not target_devices:
                    logger.error("No farm devices available")
                    return None
            
            for target_id in target_devices:
                try:
                    logger.info(f"Connecting to farm device: {target_id}")
                    
                    # Parse device info
                    if ':' in target_id:
                        host, port = target_id.split(':')
                        port = int(port)
                    else:
                        host = target_id
                        port = 5555
                    
                    # Ensure ADB connection
                    adb_result = subprocess.run(
                        ['adb', 'connect', f"{host}:{port}"],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if adb_result.returncode != 0:
                        logger.warning(f"ADB connect failed for {target_id}: {adb_result.stderr}")
                        continue
                    
                    # Wait for connection to stabilize
                    time.sleep(3)
                    
                    # Connect with UIAutomator2
                    if not U2_AVAILABLE:
                        raise RuntimeError("UIAutomator2 not available")
                    
                    u2_device = u2.connect(target_id)
                    if not u2_device:
                        logger.warning(f"UIAutomator2 connection failed for {target_id}")
                        continue
                    
                    # Verify device info
                    device_info = u2_device.info
                    if not device_info:
                        logger.warning(f"Device {target_id} not responding to info request")
                        continue
                    
                    # Create device object
                    farm_device = FlyAndroidDevice(
                        device_id=target_id,
                        host=host,
                        port=port,
                        u2_device=u2_device,
                        is_connected=True,
                        last_activity=time.time(),
                        device_info=device_info
                    )
                    
                    self.connected_devices[target_id] = farm_device
                    
                    logger.info(f"✅ Connected to farm device: {target_id}")
                    logger.info(f"Device info: {device_info.get('productName', 'Unknown')} - Android {device_info.get('version', 'Unknown')}")
                    
                    return farm_device
                    
                except Exception as e:
                    logger.warning(f"Failed to connect to {target_id}: {e}")
                    continue
            
            logger.error("Failed to connect to any farm device")
            return None
            
        except Exception as e:
            logger.error(f"Error connecting to farm device: {e}")
            return None
    
    def get_connected_device(self, device_id: str = None) -> Optional[FlyAndroidDevice]:
        """Get a connected farm device"""
        if device_id:
            return self.connected_devices.get(device_id)
        
        # Return any connected device
        for device in self.connected_devices.values():
            if device.is_connected:
                return device
        
        return None
    
    def get_all_connected_devices(self) -> List[FlyAndroidDevice]:
        """Get all connected farm devices"""
        return [device for device in self.connected_devices.values() if device.is_connected]
    
    def disconnect_device(self, device_id: str):
        """Disconnect from a farm device"""
        try:
            if device_id in self.connected_devices:
                device = self.connected_devices[device_id]
                
                # Disconnect ADB
                subprocess.run(['adb', 'disconnect', device_id], capture_output=True, timeout=10)
                
                # Mark as disconnected
                device.is_connected = False
                device.u2_device = None
                
                del self.connected_devices[device_id]
                logger.info(f"Disconnected from farm device: {device_id}")
                
        except Exception as e:
            logger.warning(f"Error disconnecting from {device_id}: {e}")
    
    def disconnect_all_devices(self):
        """Disconnect from all farm devices"""
        device_ids = list(self.connected_devices.keys())
        for device_id in device_ids:
            self.disconnect_device(device_id)
    
    def install_snapchat_on_device(self, device_id: str, apk_path: str) -> bool:
        """Install Snapchat APK on farm device"""
        try:
            device = self.connected_devices.get(device_id)
            if not device or not device.is_connected:
                logger.error(f"Device {device_id} not connected")
                return False
            
            logger.info(f"Installing Snapchat on farm device: {device_id}")
            
            # Check if APK exists
            if not os.path.exists(apk_path):
                logger.error(f"APK file not found: {apk_path}")
                return False
            
            # Uninstall existing version
            uninstall_cmd = ['adb', '-s', device_id, 'uninstall', 'com.snapchat.android']
            subprocess.run(uninstall_cmd, capture_output=True, timeout=60)
            
            # Install new APK
            install_cmd = ['adb', '-s', device_id, 'install', '-r', apk_path]
            result = subprocess.run(install_cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0 and 'Success' in result.stdout:
                logger.info(f"✅ Snapchat installed successfully on {device_id}")
                return True
            else:
                logger.error(f"Snapchat installation failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error installing Snapchat on {device_id}: {e}")
            return False
    
    def launch_snapchat_on_device(self, device_id: str) -> bool:
        """Launch Snapchat on farm device"""
        try:
            device = self.connected_devices.get(device_id)
            if not device or not device.is_connected:
                logger.error(f"Device {device_id} not connected")
                return False
            
            logger.info(f"Launching Snapchat on farm device: {device_id}")
            
            # Launch using UIAutomator2
            device.u2_device.app_start('com.snapchat.android')
            time.sleep(5)  # Wait for app to start
            
            # Verify app is running
            current_app = device.u2_device.app_current()
            if current_app.get('package') == 'com.snapchat.android':
                logger.info(f"✅ Snapchat launched successfully on {device_id}")
                return True
            else:
                logger.warning(f"Snapchat launch verification failed on {device_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error launching Snapchat on {device_id}: {e}")
            return False
    
    def take_screenshot(self, device_id: str, save_path: str = None) -> Optional[str]:
        """Take screenshot of farm device"""
        try:
            device = self.connected_devices.get(device_id)
            if not device or not device.is_connected:
                logger.error(f"Device {device_id} not connected")
                return None
            
            if not save_path:
                timestamp = int(time.time())
                save_path = f"/tmp/farm_screenshot_{device_id.replace(':', '_')}_{timestamp}.png"
            
            # Take screenshot using UIAutomator2
            screenshot = device.u2_device.screenshot()
            screenshot.save(save_path)
            
            logger.info(f"Screenshot saved: {save_path}")
            return save_path
            
        except Exception as e:
            logger.error(f"Error taking screenshot of {device_id}: {e}")
            return None
    
    def get_device_for_automation(self) -> Optional[str]:
        """Get a farm device ready for Snapchat automation"""
        try:
            # Check if we have any connected devices
            connected = self.get_all_connected_devices()
            if connected:
                device = connected[0]
                logger.info(f"Using existing connected device: {device.device_id}")
                return device.device_id
            
            # Connect to a new device
            device = self.connect_to_farm_device()
            if device:
                logger.info(f"Connected to new farm device: {device.device_id}")
                return device.device_id
            
            logger.error("No farm devices available for automation")
            return None
            
        except Exception as e:
            logger.error(f"Error getting device for automation: {e}")
            return None


# Global manager instance
_fly_android_manager = None

def get_fly_android_manager() -> FlyAndroidManager:
    """Get global fly.io Android manager instance"""
    global _fly_android_manager
    if _fly_android_manager is None:
        _fly_android_manager = FlyAndroidManager()
    return _fly_android_manager

def get_farm_device_for_snapchat() -> Optional[str]:
    """Get a farm device ready for Snapchat automation"""
    manager = get_fly_android_manager()
    return manager.get_device_for_automation()

def connect_to_android_farm() -> Optional[str]:
    """Connect to Android farm and return device ID"""
    manager = get_fly_android_manager()
    device = manager.connect_to_farm_device()
    return device.device_id if device else None

if __name__ == "__main__":
    # Test the fly.io Android farm integration
    print("🔧 Testing Fly.io Android Farm Integration")
    
    manager = FlyAndroidManager()
    
    # Discover devices
    print("Discovering farm devices...")
    devices = manager.discover_farm_devices()
    print(f"Found devices: {devices}")
    
    if devices:
        # Connect to first device
        print(f"Connecting to device: {devices[0]}")
        device = manager.connect_to_farm_device(devices[0])
        
        if device:
            print(f"✅ Connected to: {device.device_id}")
            print(f"Device info: {device.device_info}")
            
            # Take screenshot
            print("Taking screenshot...")
            screenshot_path = manager.take_screenshot(device.device_id)
            if screenshot_path:
                print(f"✅ Screenshot saved: {screenshot_path}")
            
            # Clean up
            print("Disconnecting...")
            manager.disconnect_device(device.device_id)
        else:
            print("❌ Failed to connect to farm device")
    else:
        print("❌ No farm devices found")
        print("\nTroubleshooting:")
        print("1. Ensure the fly.io Android farm is deployed and running")
        print("2. Check network connectivity to the farm")
        print("3. Verify ADB is installed and working")
    
    print("🔧 Farm integration test complete!")