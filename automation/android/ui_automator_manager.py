#!/usr/bin/env python3
"""
UIAutomator2 Connection Manager for Android Automation
Handles device connections, setup, and management with proper error handling
"""

import os
import sys
import time
import logging
import subprocess
import socket
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, TimeoutError

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
class DeviceConnectionInfo:
    """Device connection information"""
    device_id: str
    connection_type: str  # 'usb', 'wifi', 'emulator'
    ip_address: Optional[str] = None
    port: Optional[int] = None
    is_connected: bool = False
    u2_device: Any = None
    last_activity: float = 0.0
    connection_retries: int = 0

class UIAutomatorManager:
    """Manages UIAutomator2 connections and device operations for both local and remote devices"""
    
    def __init__(self, max_concurrent_devices: int = 5, use_remote_farm: bool = True):
        if not U2_AVAILABLE:
            raise ImportError("uiautomator2 not available. Install with: pip install uiautomator2")
            
        self.max_concurrent_devices = max_concurrent_devices
        self.use_remote_farm = use_remote_farm
        self.connected_devices: Dict[str, DeviceConnectionInfo] = {}
        self.connection_pool = ThreadPoolExecutor(max_workers=max_concurrent_devices)
        self.health_check_interval = 30  # seconds
        self.max_connection_retries = 3
        
        # Remote Android farm configuration
        self.remote_farm_host = os.getenv('FLY_ANDROID_HOST', 'android-device-farm-prod.fly.dev')
        self.remote_farm_ports = [5555, 5556, 5557, 5558, 5559]  # Multiple device ports
        
        # Import remote Android manager if available
        try:
            from ..telegram_bot.android_remote_config import get_remote_android_manager
            self.remote_manager = get_remote_android_manager()
        except ImportError:
            try:
                sys.path.append(os.path.join(os.path.dirname(__file__), '../telegram_bot'))
                from android_remote_config import get_remote_android_manager
                self.remote_manager = get_remote_android_manager()
            except ImportError:
                logger.warning("Remote Android manager not available")
                self.remote_manager = None
        
        # Start health monitoring
        self._start_health_monitor()
        
    def _start_health_monitor(self):
        """Start background health monitoring thread"""
        def monitor():
            while True:
                try:
                    self._check_device_health()
                    time.sleep(self.health_check_interval)
                except Exception as e:
                    logger.error(f"Health monitor error: {e}")
                    time.sleep(5)
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
        logger.info("Device health monitor started")
    
    def _check_device_health(self):
        """Check health of all connected devices"""
        devices_to_remove = []
        
        for device_id, conn_info in self.connected_devices.items():
            try:
                if conn_info.u2_device and conn_info.is_connected:
                    # Simple health check - get device info
                    info = conn_info.u2_device.info
                    if info:
                        conn_info.last_activity = time.time()
                        logger.debug(f"Device {device_id} is healthy")
                    else:
                        raise Exception("Device not responding")
                        
            except Exception as e:
                logger.warning(f"Device {device_id} health check failed: {e}")
                conn_info.is_connected = False
                
                # Try to reconnect
                if conn_info.connection_retries < self.max_connection_retries:
                    logger.info(f"Attempting to reconnect device {device_id}")
                    conn_info.connection_retries += 1
                    try:
                        self._reconnect_device(conn_info)
                    except Exception as reconnect_error:
                        logger.error(f"Reconnection failed for {device_id}: {reconnect_error}")
                else:
                    logger.error(f"Max retries exceeded for device {device_id}, removing")
                    devices_to_remove.append(device_id)
        
        # Remove failed devices
        for device_id in devices_to_remove:
            del self.connected_devices[device_id]
    
    def _reconnect_device(self, conn_info: DeviceConnectionInfo):
        """Attempt to reconnect a device"""
        if conn_info.connection_type == 'emulator':
            conn_info.u2_device = u2.connect(conn_info.device_id)
        elif conn_info.connection_type == 'wifi' and conn_info.ip_address:
            conn_info.u2_device = u2.connect(f"{conn_info.ip_address}:{conn_info.port or 5555}")
        else:
            conn_info.u2_device = u2.connect(conn_info.device_id)
        
        # Verify connection
        info = conn_info.u2_device.info
        if info:
            conn_info.is_connected = True
            conn_info.connection_retries = 0
            logger.info(f"Successfully reconnected device {conn_info.device_id}")
        else:
            raise Exception("Reconnection verification failed")
    
    def discover_devices(self) -> List[str]:
        """Discover available Android devices (local and remote)"""
        devices = []
        
        # If using remote farm, prioritize remote devices
        if self.use_remote_farm and self.remote_manager:
            try:
                logger.info("Discovering remote Android farm devices...")
                remote_devices = self._discover_remote_devices()
                devices.extend(remote_devices)
                logger.info(f"Found {len(remote_devices)} remote devices")
            except Exception as e:
                logger.error(f"Remote device discovery failed: {e}")
        
        # Discover local devices as backup
        try:
            # Use ADB to list devices
            result = subprocess.run(
                ['adb', 'devices'], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                for line in lines:
                    if line.strip() and '\tdevice' in line:
                        device_id = line.split('\t')[0]
                        if device_id not in devices:  # Avoid duplicates
                            devices.append(device_id)
                        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"ADB device discovery failed: {e}")
            
        # Also check for UIAutomator2 devices
        try:
            u2_devices = u2.device_list()
            for device in u2_devices:
                if device not in devices:
                    devices.append(device)
                    
        except Exception as e:
            logger.warning(f"UIAutomator2 device discovery failed: {e}")
        
        logger.info(f"Discovered devices: {devices}")
        return devices
    
    def connect_device(self, device_id: str, connection_type: str = 'auto', 
                      ip_address: str = None, port: int = None) -> Optional[Any]:
        """Connect to a device using UIAutomator2 (local or remote)"""
        try:
            if device_id in self.connected_devices:
                conn_info = self.connected_devices[device_id]
                if conn_info.is_connected and conn_info.u2_device:
                    logger.info(f"Device {device_id} already connected")
                    return conn_info.u2_device
            
            logger.info(f"Connecting to device: {device_id}")
            
            # Check if this is a remote farm device
            if self._is_remote_device(device_id) or self.use_remote_farm:
                return self._connect_remote_device(device_id, ip_address, port)
            
            # Determine connection type for local devices
            if connection_type == 'auto':
                if device_id.startswith('emulator-'):
                    connection_type = 'emulator'
                elif '.' in device_id or ip_address:
                    connection_type = 'wifi'
                else:
                    connection_type = 'usb'
            
            # Establish UIAutomator2 connection to local device
            u2_device = None
            if connection_type == 'emulator':
                u2_device = u2.connect(device_id)
            elif connection_type == 'wifi':
                address = ip_address or device_id
                u2_device = u2.connect(f"{address}:{port or 5555}")
            else:
                u2_device = u2.connect(device_id)
            
            if not u2_device:
                raise Exception("UIAutomator2 connection failed")
            
            # Verify connection with device info
            device_info = u2_device.info
            if not device_info:
                raise Exception("Device not responding to info request")
            
            # Setup UIAutomator2 service
            self._setup_uiautomator_service(u2_device, device_id)
            
            # Store connection info
            conn_info = DeviceConnectionInfo(
                device_id=device_id,
                connection_type=connection_type,
                ip_address=ip_address,
                port=port,
                is_connected=True,
                u2_device=u2_device,
                last_activity=time.time(),
                connection_retries=0
            )
            
            self.connected_devices[device_id] = conn_info
            
            logger.info(f"Successfully connected to device {device_id}")
            logger.info(f"Device info: {device_info['productName']} - Android {device_info['version']}")
            
            return u2_device
            
        except Exception as e:
            logger.error(f"Failed to connect to device {device_id}: {e}")
            return None
    
    def _setup_uiautomator_service(self, u2_device: Any, device_id: str):
        """Setup UIAutomator2 service on device"""
        try:
            # Check if UIAutomator2 service is running
            service_running = False
            try:
                app_info = u2_device.app_info('com.github.uiautomator')
                service_running = app_info is not None
            except:
                pass
            
            if not service_running:
                logger.info(f"Installing/starting UIAutomator2 service on {device_id}")
                
                # Push and install UIAutomator2 APK if needed
                u2_device.uiautomator.start()
                
                # Wait for service to start
                time.sleep(3)
                
                # Verify service is running
                try:
                    u2_device.info  # This should work if service is running
                except:
                    raise Exception("UIAutomator2 service failed to start")
            
            # Configure UIAutomator2 settings
            self._configure_uiautomator_settings(u2_device)
            
        except Exception as e:
            logger.error(f"UIAutomator2 service setup failed for {device_id}: {e}")
            raise
    
    def _configure_uiautomator_settings(self, u2_device: Any):
        """Configure UIAutomator2 settings for optimal performance"""
        try:
            # Set timeouts
            u2_device.implicitly_wait(10.0)
            u2_device.click_post_delay = 0.1
            
            # Configure screenshot settings for faster captures
            u2_device.settings['operation_delay'] = (0, 0.1)
            u2_device.settings['operation_delay_methods'] = ['click', 'swipe']
            
            # Set up accessibility service if needed
            try:
                u2_device.service("accessibility").start()
            except:
                logger.warning("Failed to start accessibility service (may not be needed)")
            
        except Exception as e:
            logger.warning(f"UIAutomator2 configuration warning: {e}")
    
    def disconnect_device(self, device_id: str):
        """Disconnect from a device"""
        if device_id in self.connected_devices:
            conn_info = self.connected_devices[device_id]
            try:
                if conn_info.u2_device:
                    # Stop UIAutomator2 service
                    conn_info.u2_device.uiautomator.stop()
            except Exception as e:
                logger.warning(f"Error stopping UIAutomator2 service: {e}")
            
            del self.connected_devices[device_id]
            logger.info(f"Disconnected device: {device_id}")
    
    def disconnect_all_devices(self):
        """Disconnect all devices"""
        device_ids = list(self.connected_devices.keys())
        for device_id in device_ids:
            self.disconnect_device(device_id)
    
    def get_connected_devices(self) -> Dict[str, DeviceConnectionInfo]:
        """Get all connected devices"""
        return self.connected_devices.copy()

    def _discover_remote_devices(self) -> List[str]:
        """Discover available remote Android farm devices"""
        remote_devices: List[str] = []
        try:
            if self.remote_manager:
                # Try to connect to the Android farm
                device = self.remote_manager.connect_to_fly_android_farm()
                if device:
                    remote_devices.append(device.device_id)
                    logger.info(f"Connected to remote device: {device.device_id}")
            # Try connecting to multiple potential remote devices
            for port in self.remote_farm_ports:
                try:
                    remote_id = f"{self.remote_farm_host}:{port}"
                    result = subprocess.run(
                        ['adb', 'connect', remote_id],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode == 0 and 'connected' in result.stdout.lower():
                        remote_devices.append(remote_id)
                        logger.info(f"Found remote device: {remote_id}")
                except Exception as e:
                    logger.debug(f"Remote device {remote_id} not available: {e}")
        except Exception as e:
            logger.error(f"Error discovering remote devices: {e}")
        return remote_devices

    def _is_remote_device(self, device_id: str) -> bool:
        """Check if device_id represents a remote device"""
        return (
            ':' in device_id and (
                self.remote_farm_host in device_id or
                'fly.dev' in device_id or
                device_id.startswith('farm_')
            )
        )

    def _connect_remote_device(self, device_id: str, ip_address: str = None, port: int = None) -> Optional[Any]:
        """Connect to remote Android farm device"""
        try:
            logger.info(f"Connecting to remote Android farm device: {device_id}")
            # If device_id is just "farm_device" or similar, get actual remote device
            if device_id.startswith('farm_') and self.remote_manager:
                remote_device = self.remote_manager.connect_to_fly_android_farm()
                if remote_device:
                    actual_device_id = remote_device.device_id
                else:
                    raise Exception("Failed to connect to Android farm")
            else:
                actual_device_id = device_id
            # If not already connected via ADB, connect first
            if ':' in actual_device_id:
                try:
                    subprocess.run(
                        ['adb', 'connect', actual_device_id],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    time.sleep(3)
                except Exception as e:
                    logger.warning(f"ADB connect failed (may already be connected): {e}")
            # Connect with UIAutomator2
            u2_device = u2.connect(actual_device_id)
            if not u2_device:
                raise Exception("UIAutomator2 remote connection failed")
            # Verify remote connection
            device_info = u2_device.info
            if not device_info:
                raise Exception("Remote device not responding to info request")
            # Setup UIAutomator2 service on remote device
            self._setup_uiautomator_service(u2_device, actual_device_id)
            # Store connection info
            conn_info = DeviceConnectionInfo(
                device_id=actual_device_id,
                connection_type='remote',
                ip_address=ip_address or (actual_device_id.split(':')[0] if ':' in actual_device_id else None),
                port=port or (int(actual_device_id.split(':')[1]) if ':' in actual_device_id else None),
                is_connected=True,
                u2_device=u2_device,
                last_activity=time.time(),
                connection_retries=0
            )
            self.connected_devices[actual_device_id] = conn_info
            logger.info(f"Successfully connected to remote device {actual_device_id}")
            logger.info(f"Remote device info: {device_info.get('productName', 'Unknown')} - Android {device_info.get('version', 'Unknown')}")
            return u2_device
        except Exception as e:
            logger.error(f"Failed to connect to remote device {device_id}: {e}")
            return None

    def connect_to_android_farm(self) -> Optional[Any]:
        """Connect to the first available Android farm device"""
        try:
            logger.info("Connecting to Android device farm...")
            if self.remote_manager:
                remote_device = self.remote_manager.connect_to_fly_android_farm()
                if remote_device:
                    u2_device = self._connect_remote_device(remote_device.device_id)
                    if u2_device:
                        logger.info(f"Connected to farm device: {remote_device.device_id}")
                        return u2_device
            for port in self.remote_farm_ports:
                try:
                    farm_device_id = f"{self.remote_farm_host}:{port}"
                    u2_device = self._connect_remote_device(farm_device_id)
                    if u2_device:
                        logger.info(f"Connected to farm device: {farm_device_id}")
                        return u2_device
                except Exception as e:
                    logger.debug(f"Failed to connect to {farm_device_id}: {e}")
                    continue
            raise Exception("No Android farm devices available")
        except Exception as e:
            logger.error(f"Failed to connect to Android farm: {e}")
            return None
    
    def get_device(self, device_id: str) -> Optional[Any]:
        """Get UIAutomator2 device object"""
        conn_info = self.connected_devices.get(device_id)
        if conn_info and conn_info.is_connected:
            return conn_info.u2_device
        return None
    
    def install_app(self, device_id: str, apk_path: str) -> bool:
        """Install APK on device"""
        try:
            u2_device = self.get_device(device_id)
            if not u2_device:
                raise Exception(f"Device {device_id} not connected")
            
            logger.info(f"Installing APK {apk_path} on device {device_id}")
            
            # Install APK using ADB (more reliable than u2)
            result = subprocess.run(
                ['adb', '-s', device_id, 'install', '-r', apk_path],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully installed APK on {device_id}")
                return True
            else:
                logger.error(f"APK installation failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"App installation error: {e}")
            return False
    
    def launch_app(self, device_id: str, package_name: str, activity: str = None) -> bool:
        """Launch app on device"""
        try:
            u2_device = self.get_device(device_id)
            if not u2_device:
                raise Exception(f"Device {device_id} not connected")
            
            logger.info(f"Launching app {package_name} on device {device_id}")
            
            if activity:
                u2_device.app_start(package_name, activity)
            else:
                u2_device.app_start(package_name)
            
            # Wait for app to start
            time.sleep(3)
            
            # Verify app is running
            current_app = u2_device.app_current()
            if current_app['package'] == package_name:
                logger.info(f"Successfully launched {package_name}")
                return True
            else:
                logger.warning(f"App launch verification failed. Current app: {current_app['package']}")
                return False
                
        except Exception as e:
            logger.error(f"App launch error: {e}")
            return False
    
    def take_screenshot(self, device_id: str, save_path: str = None) -> Optional[str]:
        """Take screenshot of device"""
        try:
            u2_device = self.get_device(device_id)
            if not u2_device:
                raise Exception(f"Device {device_id} not connected")
            
            if not save_path:
                timestamp = int(time.time())
                save_path = f"/tmp/screenshot_{device_id}_{timestamp}.png"
            
            # Take screenshot
            screenshot = u2_device.screenshot()
            screenshot.save(save_path)
            
            logger.info(f"Screenshot saved: {save_path}")
            return save_path
            
        except Exception as e:
            logger.error(f"Screenshot error: {e}")
            return None
    
    def get_device_info(self, device_id: str) -> Optional[Dict]:
        """Get detailed device information"""
        try:
            u2_device = self.get_device(device_id)
            if not u2_device:
                raise Exception(f"Device {device_id} not connected")
            
            info = u2_device.info
            
            # Add additional information
            info['screen_size'] = (info.get('displayWidth', 0), info.get('displayHeight', 0))
            info['current_app'] = u2_device.app_current()
            
            return info
            
        except Exception as e:
            logger.error(f"Get device info error: {e}")
            return None
    
    def execute_shell_command(self, device_id: str, command: str) -> Optional[str]:
        """Execute shell command on device"""
        try:
            u2_device = self.get_device(device_id)
            if not u2_device:
                raise Exception(f"Device {device_id} not connected")
            
            result = u2_device.shell(command)
            return result.output if hasattr(result, 'output') else str(result)
            
        except Exception as e:
            logger.error(f"Shell command error: {e}")
            return None

# Global UIAutomator manager
_ui_automator_manager = None

def get_ui_automator_manager() -> UIAutomatorManager:
    """Get global UIAutomator manager instance"""
    global _ui_automator_manager
    if _ui_automator_manager is None:
        _ui_automator_manager = UIAutomatorManager()
    return _ui_automator_manager

def cleanup_ui_automator():
    """Cleanup function for graceful shutdown"""
    global _ui_automator_manager
    if _ui_automator_manager:
        _ui_automator_manager.disconnect_all_devices()

# Register cleanup handler
import atexit
atexit.register(cleanup_ui_automator)

if __name__ == "__main__":
    # Test UIAutomator manager
    if not U2_AVAILABLE:
        print("UIAutomator2 not available. Install with: pip install uiautomator2")
        sys.exit(1)
    
    manager = UIAutomatorManager()
    
    try:
        # Discover devices
        print("Discovering devices...")
        devices = manager.discover_devices()
        print(f"Found devices: {devices}")
        
        if devices:
            # Connect to first device
            device_id = devices[0]
            print(f"Connecting to device: {device_id}")
            u2_device = manager.connect_device(device_id)
            
            if u2_device:
                # Get device info
                info = manager.get_device_info(device_id)
                print(f"Device info: {info}")
                
                # Take screenshot
                screenshot_path = manager.take_screenshot(device_id)
                print(f"Screenshot saved: {screenshot_path}")
                
                # Test shell command
                result = manager.execute_shell_command(device_id, "getprop ro.product.model")
                print(f"Device model: {result}")
        
        print("Test completed successfully")
        
    except KeyboardInterrupt:
        print("Interrupted by user")
    except Exception as e:
        print(f"Test error: {e}")
    finally:
        manager.disconnect_all_devices()