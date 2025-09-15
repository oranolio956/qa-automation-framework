#!/usr/bin/env python3
"""
Remote Android Device Configuration for Snapchat Automation
Connects local Snapchat workflow to Fly.io Android device farm
"""

import os
import subprocess
import logging
import time
from typing import Optional, List, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RemoteAndroidDevice:
    """Configuration for remote Android device"""
    host: str
    port: int = 5555
    device_id: Optional[str] = None
    vnc_port: int = 5900
    connected: bool = False

class RemoteAndroidManager:
    """Manages connection to remote Android devices on Fly.io"""
    
    def __init__(self):
        self.devices: List[RemoteAndroidDevice] = []
        self.connected_devices: Dict[str, RemoteAndroidDevice] = {}
        
        # Load configuration
        self.fly_app_name = os.getenv('FLY_ANDROID_APP', 'android-device-farm-prod')
        self.default_host = os.getenv('FLY_ANDROID_HOST', f'{self.fly_app_name}.fly.dev')
        
    def add_device(self, host: str, port: int = 5555, vnc_port: int = 5900):
        """Add a remote Android device"""
        device = RemoteAndroidDevice(
            host=host,
            port=port,
            vnc_port=vnc_port,
            device_id=f"{host}:{port}"
        )
        self.devices.append(device)
        logger.info(f"Added remote device: {device.device_id}")
        return device
    
    def connect_to_device(self, device: RemoteAndroidDevice) -> bool:
        """Connect to remote Android device via ADB"""
        try:
            # First disconnect if already connected
            self.disconnect_device(device)
            
            # Connect to remote device
            logger.info(f"Connecting to remote Android device: {device.host}:{device.port}")
            
            connect_cmd = ['adb', 'connect', f'{device.host}:{device.port}']
            result = subprocess.run(connect_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # Wait for device to be ready
                if self._wait_for_device_ready(device):
                    device.connected = True
                    device.device_id = f"{device.host}:{device.port}"
                    self.connected_devices[device.device_id] = device
                    
                    logger.info(f"✅ Connected to remote device: {device.device_id}")
                    return True
                else:
                    logger.error(f"Device connected but not ready: {device.device_id}")
                    return False
            else:
                logger.error(f"Failed to connect to {device.host}:{device.port}: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to device {device.host}:{device.port}: {e}")
            return False
    
    def _wait_for_device_ready(self, device: RemoteAndroidDevice, timeout: int = 60) -> bool:
        """Wait for device to be ready for automation"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check if device responds
                check_cmd = ['adb', '-s', device.device_id, 'shell', 'getprop', 'sys.boot_completed']
                result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0 and result.stdout.strip() == '1':
                    # Additional check for UI ready
                    ui_cmd = ['adb', '-s', device.device_id, 'shell', 'dumpsys', 'window', 'windows']
                    ui_result = subprocess.run(ui_cmd, capture_output=True, text=True, timeout=10)
                    
                    if ui_result.returncode == 0 and 'mCurrentFocus' in ui_result.stdout:
                        logger.info(f"Device {device.device_id} is ready for automation")
                        return True
                        
            except subprocess.TimeoutExpired:
                logger.warning(f"Timeout checking device readiness: {device.device_id}")
            except Exception as e:
                logger.warning(f"Error checking device readiness: {e}")
            
            time.sleep(5)
        
        logger.error(f"Device {device.device_id} failed to become ready within {timeout}s")
        return False
    
    def disconnect_device(self, device: RemoteAndroidDevice):
        """Disconnect from remote device"""
        try:
            if device.device_id:
                disconnect_cmd = ['adb', 'disconnect', device.device_id]
                subprocess.run(disconnect_cmd, capture_output=True, timeout=10)
                
                if device.device_id in self.connected_devices:
                    del self.connected_devices[device.device_id]
                
                device.connected = False
                logger.info(f"Disconnected from device: {device.device_id}")
                
        except Exception as e:
            logger.warning(f"Error disconnecting device: {e}")
    
    def get_connected_devices(self) -> List[str]:
        """Get list of connected device IDs"""
        try:
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
            devices = []
            
            for line in result.stdout.split('\n')[1:]:  # Skip header
                if '\tdevice' in line:
                    device_id = line.split('\t')[0]
                    if ':' in device_id:  # Remote device
                        devices.append(device_id)
            
            return devices
            
        except Exception as e:
            logger.error(f"Error getting connected devices: {e}")
            return []
    
    def connect_to_fly_android_farm(self) -> Optional[RemoteAndroidDevice]:
        """Connect to the Fly.io Android device farm"""
        try:
            # Get the IP address of the Fly.io app
            fly_ip = self._get_fly_app_ip()
            
            if not fly_ip:
                logger.error("Could not get Fly.io app IP address")
                return None
            
            # Add and connect to device
            device = self.add_device(fly_ip, port=5555, vnc_port=5900)
            
            if self.connect_to_device(device):
                logger.info(f"✅ Successfully connected to Fly.io Android farm: {device.device_id}")
                return device
            else:
                logger.error("Failed to connect to Fly.io Android farm")
                return None
                
        except Exception as e:
            logger.error(f"Error connecting to Fly.io Android farm: {e}")
            return None
    
    def _get_fly_app_ip(self) -> Optional[str]:
        """Get IP address of Fly.io app"""
        try:
            # Try to get IP from flyctl
            cmd = ['flyctl', 'ips', 'list', '--app', self.fly_app_name, '--json']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                import json
                ips = json.loads(result.stdout)
                
                for ip_info in ips:
                    if ip_info.get('type') == 'v4':
                        return ip_info.get('address')
            
            # Fallback: try to resolve hostname
            import socket
            fly_hostname = f"{self.fly_app_name}.fly.dev"
            try:
                ip = socket.gethostbyname(fly_hostname)
                logger.info(f"Resolved {fly_hostname} to {ip}")
                return ip
            except socket.gaierror:
                logger.error(f"Could not resolve {fly_hostname}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting Fly.io app IP: {e}")
            return None
    
    def test_device_connection(self, device_id: str) -> bool:
        """Test if device is responsive"""
        try:
            cmd = ['adb', '-s', device_id, 'shell', 'echo', 'test']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            success = result.returncode == 0 and 'test' in result.stdout
            
            if success:
                logger.info(f"✅ Device {device_id} is responsive")
            else:
                logger.warning(f"❌ Device {device_id} is not responsive")
            
            return success
            
        except Exception as e:
            logger.error(f"Error testing device {device_id}: {e}")
            return False
    
    def install_snapchat_on_device(self, device_id: str, apk_path: str) -> bool:
        """Install Snapchat APK on remote device"""
        try:
            logger.info(f"Installing Snapchat APK on {device_id}")
            
            # Check if APK file exists
            if not os.path.exists(apk_path):
                logger.error(f"APK file not found: {apk_path}")
                return False
            
            # Install APK
            install_cmd = ['adb', '-s', device_id, 'install', '-r', apk_path]
            result = subprocess.run(install_cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info(f"✅ Snapchat installed successfully on {device_id}")
                return True
            else:
                logger.error(f"Failed to install Snapchat: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error installing Snapchat: {e}")
            return False
    
    def launch_snapchat_on_device(self, device_id: str) -> bool:
        """Launch Snapchat on remote device"""
        try:
            logger.info(f"Launching Snapchat on {device_id}")
            
            # Launch Snapchat
            launch_cmd = ['adb', '-s', device_id, 'shell', 'am', 'start', '-n', 'com.snapchat.android/.LandingPageActivity']
            result = subprocess.run(launch_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info(f"✅ Snapchat launched on {device_id}")
                time.sleep(5)  # Wait for app to load
                return True
            else:
                # Try alternative launch method
                monkey_cmd = ['adb', '-s', device_id, 'shell', 'monkey', '-p', 'com.snapchat.android', '1']
                monkey_result = subprocess.run(monkey_cmd, capture_output=True, text=True, timeout=30)
                
                if monkey_result.returncode == 0:
                    logger.info(f"✅ Snapchat launched via monkey on {device_id}")
                    time.sleep(5)
                    return True
                else:
                    logger.error(f"Failed to launch Snapchat: {result.stderr}")
                    return False
                
        except Exception as e:
            logger.error(f"Error launching Snapchat: {e}")
            return False
    
    def take_screenshot(self, device_id: str, save_path: str = None) -> Optional[str]:
        """Take screenshot of remote device"""
        try:
            if not save_path:
                timestamp = int(time.time())
                save_path = f"/tmp/remote_device_screenshot_{timestamp}.png"
            
            # Take screenshot
            cmd = ['adb', '-s', device_id, 'exec-out', 'screencap', '-p']
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            
            if result.returncode == 0:
                with open(save_path, 'wb') as f:
                    f.write(result.stdout)
                
                logger.info(f"Screenshot saved: {save_path}")
                return save_path
            else:
                logger.error(f"Failed to take screenshot: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return None
    
    def get_device_info(self, device_id: str) -> Optional[Dict]:
        """Get device information"""
        try:
            info = {
                'device_id': device_id,
                'connection_type': 'remote',
                'properties': {}
            }
            
            # Get device properties
            prop_cmd = ['adb', '-s', device_id, 'shell', 'getprop']
            result = subprocess.run(prop_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if ': [' in line:
                        key = line.split(': [')[0].strip('[]')
                        value = line.split(': [')[1].strip('[]')
                        info['properties'][key] = value
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting device info: {e}")
            return None
    
    def disconnect_all(self):
        """Disconnect from all remote devices"""
        for device in list(self.connected_devices.values()):
            self.disconnect_device(device)

# Global remote Android manager
_remote_android_manager = None

def get_remote_android_manager() -> RemoteAndroidManager:
    """Get global remote Android manager instance"""
    global _remote_android_manager
    if _remote_android_manager is None:
        _remote_android_manager = RemoteAndroidManager()
    return _remote_android_manager

def connect_to_fly_android_devices() -> List[str]:
    """Connect to all available Fly.io Android devices"""
    manager = get_remote_android_manager()
    
    # Connect to main device farm
    device = manager.connect_to_fly_android_farm()
    
    if device:
        return [device.device_id]
    else:
        return []

def get_available_android_devices() -> List[str]:
    """Get all available Android devices (local + remote)"""
    manager = get_remote_android_manager()
    return manager.get_connected_devices()

if __name__ == "__main__":
    # Test remote Android connection
    print("🔧 Testing Remote Android Device Connection")
    
    manager = RemoteAndroidManager()
    
    # Test connecting to Fly.io device farm
    print("Connecting to Fly.io Android device farm...")
    device = manager.connect_to_fly_android_farm()
    
    if device:
        print(f"✅ Connected to device: {device.device_id}")
        
        # Test device responsiveness
        print("Testing device responsiveness...")
        if manager.test_device_connection(device.device_id):
            print("✅ Device is responsive")
            
            # Take screenshot
            print("Taking screenshot...")
            screenshot_path = manager.take_screenshot(device.device_id)
            if screenshot_path:
                print(f"✅ Screenshot saved: {screenshot_path}")
            
            # Get device info
            print("Getting device info...")
            info = manager.get_device_info(device.device_id)
            if info:
                print(f"✅ Device model: {info.get('properties', {}).get('ro.product.model', 'Unknown')}")
                print(f"✅ Android version: {info.get('properties', {}).get('ro.build.version.release', 'Unknown')}")
        
        print("Disconnecting...")
        manager.disconnect_device(device)
        
    else:
        print("❌ Failed to connect to Fly.io Android device farm")
        print("\nTroubleshooting:")
        print("1. Ensure the Fly.io Android device farm is deployed")
        print("2. Check that the app is running: flyctl status --app android-device-farm-prod")
        print("3. Verify the IP is accessible: ping <fly-app-ip>")
        print("4. Check ADB is installed locally: adb version")
    
    print("\n🔧 Remote Android connection test complete!")