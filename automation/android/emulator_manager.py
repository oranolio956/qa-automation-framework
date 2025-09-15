#!/usr/bin/env python3
"""
Android Emulator Manager for Tinder Account Automation
Manages Android emulators with realistic device fingerprints and configurations
"""

import os
import subprocess
import time
import logging
import json
import random
import shutil
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import threading
import queue
import signal
import sys
from concurrent.futures import ThreadPoolExecutor

# Import existing utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../utils'))
try:
    from brightdata_proxy import get_brightdata_session
except ImportError:
    def get_brightdata_session():
        import requests
        return requests.Session()

# Import UIAutomator2 manager
try:
    from .ui_automator_manager import get_ui_automator_manager
except ImportError:
    try:
        from ui_automator_manager import get_ui_automator_manager
    except ImportError:
        get_ui_automator_manager = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class EmulatorConfig:
    """Android emulator configuration"""
    name: str
    device_type: str
    api_level: int
    target: str
    resolution: str
    density: str
    ram_size: str
    heap_size: str
    internal_storage: str
    sd_card_size: str
    gpu: str = "swiftshader_indirect"
    enable_camera: bool = True
    enable_gps: bool = True
    
@dataclass 
class EmulatorInstance:
    """Running emulator instance"""
    config: EmulatorConfig
    avd_name: str
    port: int
    process: subprocess.Popen
    proxy_port: Optional[int] = None
    is_ready: bool = False
    device_id: str = ""

class AndroidSDKManager:
    """Manages Android SDK components"""
    
    def __init__(self, sdk_path: str = None):
        self.sdk_path = sdk_path or self._detect_sdk_path()
        if self.sdk_path:
            self.avd_manager = os.path.join(self.sdk_path, "cmdline-tools", "latest", "bin", "avdmanager")
            self.sdkmanager = os.path.join(self.sdk_path, "cmdline-tools", "latest", "bin", "sdkmanager")
            self.emulator = os.path.join(self.sdk_path, "emulator", "emulator")
        else:
            self.avd_manager = None
            self.sdkmanager = None
            self.emulator = None
        
    def _detect_sdk_path(self) -> str:
        """Auto-detect Android SDK path"""
        possible_paths = [
            os.path.expanduser("~/Android/Sdk"),
            os.path.expanduser("~/Library/Android/sdk"),
            "/usr/local/android-sdk",
            os.environ.get("ANDROID_HOME", ""),
            os.environ.get("ANDROID_SDK_ROOT", "")
        ]
        
        for path in possible_paths:
            if path and os.path.exists(path):
                logger.info(f"Found Android SDK at: {path}")
                return path
                
        logger.warning("Android SDK not found locally. This is expected when running emulators on Fly.io.")
        return None
    
    def install_system_images(self, api_levels: List[int]) -> bool:
        """Install required system images"""
        success = True
        for api_level in api_levels:
            targets = [
                f"system-images;android-{api_level};google_apis;x86_64",
                f"system-images;android-{api_level};google_apis_playstore;x86_64"
            ]
            
            for target in targets:
                try:
                    cmd = [self.sdkmanager, "--install", target]
                    result = subprocess.run(cmd, check=True, capture_output=True, text=True, input="y\n")
                    logger.info(f"Installed: {target}")
                except subprocess.CalledProcessError as e:
                    logger.warning(f"Failed to install {target}: {e}")
                    success = False
                    
        return success
    
    def list_available_devices(self) -> List[str]:
        """List available device definitions"""
        try:
            cmd = [self.avd_manager, "list", "device"]
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            return result.stdout.split('\n')
        except subprocess.CalledProcessError:
            logger.error("Failed to list available devices")
            return []

class EmulatorManager:
    """Manages multiple Android emulators for Tinder automation"""
    
    def __init__(self, sdk_manager: AndroidSDKManager = None, max_concurrent: int = 5):
        self.sdk_manager = sdk_manager or AndroidSDKManager()
        self.max_concurrent = max_concurrent
        self.running_emulators: Dict[str, EmulatorInstance] = {}
        self.port_range = range(5554, 5654, 2)  # ADB uses even ports
        self.used_ports = set()
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
        
        # Realistic device configurations
        self.device_configs = [
            EmulatorConfig(
                name="pixel_6_api_30",
                device_type="pixel",
                api_level=30,
                target="google_apis",
                resolution="1080x2340",
                density="420dpi", 
                ram_size="4096M",
                heap_size="256M",
                internal_storage="6144M",
                sd_card_size="512M"
            ),
            EmulatorConfig(
                name="galaxy_s21_api_31",
                device_type="Galaxy S21",
                api_level=31,
                target="google_apis_playstore",
                resolution="1080x2400",
                density="421dpi",
                ram_size="8192M", 
                heap_size="512M",
                internal_storage="8192M",
                sd_card_size="1024M"
            ),
            EmulatorConfig(
                name="pixel_7_api_33",
                device_type="pixel_7",
                api_level=33,
                target="google_apis_playstore",
                resolution="1080x2400",
                density="420dpi",
                ram_size="8192M",
                heap_size="512M",
                internal_storage="8192M",
                sd_card_size="1024M"
            )
        ]
        
    def _get_available_port(self) -> int:
        """Get next available port for emulator"""
        for port in self.port_range:
            if port not in self.used_ports:
                # Test if port is actually available
                import socket
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    if s.connect_ex(('localhost', port)) != 0:
                        self.used_ports.add(port)
                        return port
        raise RuntimeError("No available ports for emulator")
    
    def create_avd(self, config: EmulatorConfig, avd_name: str = None) -> str:
        """Create Android Virtual Device"""
        if not avd_name:
            avd_name = f"{config.name}_{int(time.time())}"
            
        # Check if AVD already exists
        if self._avd_exists(avd_name):
            logger.info(f"AVD {avd_name} already exists")
            return avd_name
            
        target_full = f"system-images;android-{config.api_level};{config.target};x86_64"
        
        try:
            # Create AVD
            cmd = [
                self.sdk_manager.avd_manager,
                "create", "avd",
                "-n", avd_name,
                "-k", target_full,
                "-d", config.device_type
            ]
            
            # Auto-respond to prompts
            input_data = "no\n"  # Don't create custom hardware profile
            result = subprocess.run(cmd, input=input_data, check=True, capture_output=True, text=True)
            
            logger.info(f"Created AVD: {avd_name}")
            
            # Customize AVD config
            self._customize_avd_config(avd_name, config)
            
            return avd_name
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create AVD {avd_name}: {e}")
            logger.error(f"stdout: {e.stdout}")
            logger.error(f"stderr: {e.stderr}")
            raise
    
    def _avd_exists(self, avd_name: str) -> bool:
        """Check if AVD exists"""
        try:
            cmd = [self.sdk_manager.avd_manager, "list", "avd"]
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            return avd_name in result.stdout
        except subprocess.CalledProcessError:
            return False
    
    def _customize_avd_config(self, avd_name: str, config: EmulatorConfig):
        """Customize AVD hardware configuration"""
        avd_path = os.path.expanduser(f"~/.android/avd/{avd_name}.avd/config.ini")
        
        if not os.path.exists(avd_path):
            logger.warning(f"AVD config file not found: {avd_path}")
            return
            
        # Read existing config
        with open(avd_path, 'r') as f:
            lines = f.readlines()
            
        # Update configuration
        config_updates = {
            'hw.ramSize': config.ram_size,
            'vm.heapSize': config.heap_size,
            'disk.dataPartition.size': config.internal_storage,
            'hw.sdCard': 'yes',
            'sdcard.size': config.sd_card_size,
            'hw.camera.back': 'webcam0' if config.enable_camera else 'none',
            'hw.camera.front': 'webcam0' if config.enable_camera else 'none',
            'hw.gps': 'yes' if config.enable_gps else 'no',
            'hw.gpu.enabled': 'yes',
            'hw.gpu.mode': 'swiftshader_indirect',
            'hw.keyboard': 'yes',
            'hw.sensors.proximity': 'yes',
            'hw.sensors.orientation': 'yes',
            'hw.accelerometer': 'yes',
            'hw.gyroscope': 'yes'
        }
        
        # Apply updates
        updated_lines = []
        existing_keys = set()
        
        for line in lines:
            if '=' in line:
                key = line.split('=')[0].strip()
                if key in config_updates:
                    updated_lines.append(f"{key}={config_updates[key]}\n")
                    existing_keys.add(key)
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)
        
        # Add missing keys
        for key, value in config_updates.items():
            if key not in existing_keys:
                updated_lines.append(f"{key}={value}\n")
        
        # Write updated config
        with open(avd_path, 'w') as f:
            f.writelines(updated_lines)
            
        logger.info(f"Customized AVD config: {avd_name}")
    
    def start_emulator(self, avd_name: str, config: EmulatorConfig, headless: bool = True) -> EmulatorInstance:
        """Start Android emulator"""
        port = self._get_available_port()
        
        # Build emulator command
        cmd = [
            self.sdk_manager.emulator,
            "-avd", avd_name,
            "-port", str(port),
            "-gpu", config.gpu,
            "-memory", config.ram_size.replace('M', ''),
            "-cache-size", "1024",
            "-no-snapshot-save",
            "-no-snapshot-load",
            "-wipe-data"  # Start fresh each time
        ]
        
        if headless:
            cmd.extend(["-no-window", "-no-audio"])
        
        # Add proxy settings if available
        proxy_session = None
        try:
            proxy_session = get_brightdata_session()
            if proxy_session.proxies.get('http'):
                proxy_url = proxy_session.proxies['http']
                # Parse proxy URL for emulator format
                if '@' in proxy_url:
                    auth_host = proxy_url.split('@')[1]
                    if ':' in auth_host:
                        host, port_str = auth_host.split(':')
                        cmd.extend(["-http-proxy", f"{host}:{port_str}"])
        except Exception as e:
            logger.warning(f"Could not set up proxy for emulator: {e}")
        
        try:
            # Start emulator process
            logger.info(f"Starting emulator {avd_name} on port {port}")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid  # Create new process group
            )
            
            instance = EmulatorInstance(
                config=config,
                avd_name=avd_name,
                port=port,
                process=process,
                device_id=f"emulator-{port}"
            )
            
            self.running_emulators[avd_name] = instance
            
            # Wait for emulator to start
            self._wait_for_emulator_ready(instance)
            
            return instance
            
        except Exception as e:
            logger.error(f"Failed to start emulator {avd_name}: {e}")
            if port in self.used_ports:
                self.used_ports.remove(port)
            raise
    
    def _wait_for_emulator_ready(self, instance: EmulatorInstance, timeout: int = 300):
        """Wait for emulator to be ready for use"""
        logger.info(f"Waiting for emulator {instance.avd_name} to be ready...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check if emulator is responding to ADB
            try:
                cmd = ["adb", "-s", instance.device_id, "shell", "getprop", "sys.boot_completed"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0 and result.stdout.strip() == "1":
                    # Additional check for UI ready
                    cmd = ["adb", "-s", instance.device_id, "shell", "dumpsys", "window", "windows"]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    
                    if "mCurrentFocus" in result.stdout:
                        instance.is_ready = True
                        logger.info(f"Emulator {instance.avd_name} is ready")
                        self._setup_emulator_environment(instance)
                        return
                        
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                pass
            
            # Check if process is still running
            if instance.process.poll() is not None:
                raise RuntimeError(f"Emulator {instance.avd_name} process died during startup")
            
            time.sleep(5)
        
        raise RuntimeError(f"Emulator {instance.avd_name} failed to start within {timeout} seconds")
    
    def _setup_emulator_environment(self, instance: EmulatorInstance):
        """Set up emulator environment for Tinder automation"""
        device_id = instance.device_id
        
        try:
            # Wait for device to be fully ready
            self._wait_for_device_ready(device_id)
            
            # Disable animations for faster automation
            animations_settings = [
                ("global", "animator_duration_scale", "0"),
                ("global", "transition_animation_scale", "0"),
                ("global", "window_animation_scale", "0")
            ]
            
            for namespace, key, value in animations_settings:
                cmd = ["adb", "-s", device_id, "shell", "settings", "put", namespace, key, value]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.warning(f"Failed to set {key}: {result.stderr}")
            
            # Configure device for automation
            automation_settings = [
                # Disable screen timeout
                ["adb", "-s", device_id, "shell", "settings", "put", "system", "screen_off_timeout", "2147483647"],
                # Keep screen on during charging
                ["adb", "-s", device_id, "shell", "settings", "put", "global", "stay_on_while_plugged_in", "7"],
                # Disable auto-rotate
                ["adb", "-s", device_id, "shell", "settings", "put", "system", "accelerometer_rotation", "0"],
                # Set portrait orientation
                ["adb", "-s", device_id, "shell", "settings", "put", "system", "user_rotation", "0"]
            ]
            
            for cmd in automation_settings:
                subprocess.run(cmd, check=False)  # Don't fail if some settings aren't available
            
            # Set mock location app (for GPS spoofing if needed)
            cmd = ["adb", "-s", device_id, "shell", "appops", "set", "com.android.settings", 
                   "MOCK_LOCATION", "allow"]
            subprocess.run(cmd, check=False)  # May fail on some Android versions
            
            # Enable developer options and USB debugging (if not already enabled)
            dev_settings = [
                ["adb", "-s", device_id, "shell", "settings", "put", "global", "development_settings_enabled", "1"],
                ["adb", "-s", device_id, "shell", "settings", "put", "global", "adb_enabled", "1"]
            ]
            
            for cmd in dev_settings:
                subprocess.run(cmd, check=False)
            
            # Set up file system for automation
            filesystem_cmds = [
                ["adb", "-s", device_id, "shell", "mkdir", "-p", "/sdcard/automation"],
                ["adb", "-s", device_id, "shell", "mkdir", "-p", "/sdcard/Download"],
                ["adb", "-s", device_id, "shell", "mkdir", "-p", "/sdcard/Pictures"]
            ]
            
            for cmd in filesystem_cmds:
                subprocess.run(cmd, check=True)
            
            # Set up UIAutomator2 connection if available
            if get_ui_automator_manager:
                try:
                    ui_manager = get_ui_automator_manager()
                    u2_device = ui_manager.connect_device(device_id, 'emulator')
                    if u2_device:
                        logger.info(f"UIAutomator2 connected to {device_id}")
                        instance.u2_device = u2_device
                except Exception as e:
                    logger.warning(f"UIAutomator2 setup failed: {e}")
            
            logger.info(f"Emulator environment setup complete: {device_id}")
            
        except Exception as e:
            logger.error(f"Failed to set up emulator environment: {e}")
    
    def _wait_for_device_ready(self, device_id: str, timeout: int = 60):
        """Wait for device to be ready for commands"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check if device responds to basic commands
                cmd = ["adb", "-s", device_id, "shell", "getprop", "sys.boot_completed"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0 and result.stdout.strip() == "1":
                    # Additional readiness check
                    cmd = ["adb", "-s", device_id, "shell", "pm", "list", "packages"]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0 and "com.android." in result.stdout:
                        logger.info(f"Device {device_id} is ready for automation")
                        return
                        
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                pass
            
            time.sleep(2)
        
        raise RuntimeError(f"Device {device_id} failed to become ready within {timeout} seconds")
    
    def stop_emulator(self, avd_name: str):
        """Stop running emulator"""
        if avd_name not in self.running_emulators:
            logger.warning(f"Emulator {avd_name} is not running")
            return
        
        instance = self.running_emulators[avd_name]
        
        try:
            # Try graceful shutdown first
            cmd = ["adb", "-s", instance.device_id, "emu", "kill"]
            subprocess.run(cmd, timeout=10)
            
            # Wait for process to terminate
            try:
                instance.process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                # Force kill
                os.killpg(os.getpgid(instance.process.pid), signal.SIGTERM)
                instance.process.wait(timeout=10)
                
        except Exception as e:
            logger.error(f"Error stopping emulator {avd_name}: {e}")
            # Force kill as last resort
            try:
                os.killpg(os.getpgid(instance.process.pid), signal.SIGKILL)
            except:
                pass
        
        # Clean up resources
        if instance.port in self.used_ports:
            self.used_ports.remove(instance.port)
        del self.running_emulators[avd_name]
        
        logger.info(f"Stopped emulator: {avd_name}")
        
        # Also disconnect from UIAutomator2 if connected
        if get_ui_automator_manager:
            try:
                ui_manager = get_ui_automator_manager()
                ui_manager.disconnect_device(instance.device_id)
            except:
                pass
    
    def stop_all_emulators(self):
        """Stop all running emulators"""
        avd_names = list(self.running_emulators.keys())
        for avd_name in avd_names:
            self.stop_emulator(avd_name)
    
    def get_running_emulators(self) -> Dict[str, EmulatorInstance]:
        """Get all running emulator instances"""
        return self.running_emulators.copy()
    
    def create_emulator_pool(self, count: int, headless: bool = True) -> List[EmulatorInstance]:
        """Create a pool of emulators for parallel automation"""
        instances = []
        
        for i in range(min(count, self.max_concurrent)):
            config = random.choice(self.device_configs)
            avd_name = f"tinder_automation_{i}_{int(time.time())}"
            
            try:
                # Create AVD
                self.create_avd(config, avd_name)
                
                # Start emulator
                instance = self.start_emulator(avd_name, config, headless)
                instances.append(instance)
                
                logger.info(f"Created emulator {i+1}/{count}: {avd_name}")
                
                # Small delay between starts to avoid resource conflicts
                time.sleep(10)
                
            except Exception as e:
                logger.error(f"Failed to create emulator {i+1}: {e}")
        
        return instances
    
    def install_apk_on_emulator(self, avd_name: str, apk_path: str) -> bool:
        """Install APK on running emulator"""
        if avd_name not in self.running_emulators:
            logger.error(f"Emulator {avd_name} is not running")
            return False
        
        instance = self.running_emulators[avd_name]
        
        try:
            logger.info(f"Installing APK {apk_path} on emulator {avd_name}")
            
            # Use ADB to install APK
            cmd = ["adb", "-s", instance.device_id, "install", "-r", apk_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info(f"Successfully installed APK on {avd_name}")
                return True
            else:
                logger.error(f"APK installation failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"APK installation error: {e}")
            return False
    
    def launch_app_on_emulator(self, avd_name: str, package_name: str, activity: str = None) -> bool:
        """Launch app on running emulator"""
        if avd_name not in self.running_emulators:
            logger.error(f"Emulator {avd_name} is not running")
            return False
        
        instance = self.running_emulators[avd_name]
        
        try:
            logger.info(f"Launching {package_name} on emulator {avd_name}")
            
            if activity:
                cmd = ["adb", "-s", instance.device_id, "shell", "am", "start", "-n", f"{package_name}/{activity}"]
            else:
                cmd = ["adb", "-s", instance.device_id, "shell", "monkey", "-p", package_name, "1"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info(f"Successfully launched {package_name}")
                time.sleep(3)  # Wait for app to start
                return True
            else:
                logger.error(f"App launch failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"App launch error: {e}")
            return False
    
    def take_screenshot(self, avd_name: str, save_path: str = None) -> Optional[str]:
        """Take screenshot of emulator"""
        if avd_name not in self.running_emulators:
            logger.error(f"Emulator {avd_name} is not running")
            return None
        
        instance = self.running_emulators[avd_name]
        
        try:
            if not save_path:
                timestamp = int(time.time())
                save_path = f"/tmp/emulator_screenshot_{avd_name}_{timestamp}.png"
            
            # Use UIAutomator2 if available, otherwise use ADB
            if hasattr(instance, 'u2_device') and instance.u2_device:
                screenshot = instance.u2_device.screenshot()
                screenshot.save(save_path)
            else:
                # Fallback to ADB screencap
                cmd = ["adb", "-s", instance.device_id, "exec-out", "screencap", "-p"]
                result = subprocess.run(cmd, capture_output=True, timeout=30)
                
                if result.returncode == 0:
                    with open(save_path, 'wb') as f:
                        f.write(result.stdout)
                else:
                    raise Exception(f"screencap failed: {result.stderr}")
            
            logger.info(f"Screenshot saved: {save_path}")
            return save_path
            
        except Exception as e:
            logger.error(f"Screenshot error: {e}")
            return None
    
    def get_emulator_info(self, avd_name: str) -> Optional[Dict]:
        """Get detailed emulator information"""
        if avd_name not in self.running_emulators:
            return None
        
        instance = self.running_emulators[avd_name]
        
        try:
            # Get device properties
            properties = {}
            prop_cmd = ["adb", "-s", instance.device_id, "shell", "getprop"]
            result = subprocess.run(prop_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if ': [' in line:
                        key = line.split(': [')[0].strip('[]')
                        value = line.split(': [')[1].strip('[]')
                        properties[key] = value
            
            # Get current app
            current_app = None
            try:
                if hasattr(instance, 'u2_device') and instance.u2_device:
                    current_app = instance.u2_device.app_current()
                else:
                    # Fallback method
                    app_cmd = ["adb", "-s", instance.device_id, "shell", "dumpsys", "activity", "activities"]
                    app_result = subprocess.run(app_cmd, capture_output=True, text=True, timeout=15)
                    # Parse current activity from dumpsys output
                    # This is a simplified version - full parsing would be more complex
                    if "mCurrentFocus" in app_result.stdout:
                        focus_line = [line for line in app_result.stdout.split('\n') if 'mCurrentFocus' in line]
                        if focus_line:
                            current_app = {'package': 'unknown', 'activity': focus_line[0]}
            except:
                pass
            
            return {
                'avd_name': avd_name,
                'device_id': instance.device_id,
                'port': instance.port,
                'is_ready': instance.is_ready,
                'config': instance.config,
                'current_app': current_app,
                'properties': properties,
                'connection_type': 'emulator',
                'uiautomator_available': hasattr(instance, 'u2_device') and instance.u2_device is not None
            }
            
        except Exception as e:
            logger.error(f"Get emulator info error: {e}")
            return None
    
    def create_emulator(self, name_suffix: str = None) -> EmulatorInstance:
        """Create and start a single emulator for account creation"""
        try:
            # Choose a random device config
            config = random.choice(self.device_configs)
            
            # Generate unique AVD name
            if name_suffix:
                avd_name = f"{config.name}_{name_suffix}_{int(time.time())}"
            else:
                avd_name = f"{config.name}_{int(time.time())}"
            
            # Create AVD if it doesn't exist
            if not self._avd_exists(avd_name):
                self.create_avd(config, avd_name)
            
            # Start the emulator
            instance = self.start_emulator(avd_name, config, headless=True)
            
            if instance and instance.is_ready:
                return instance
            else:
                raise RuntimeError(f"Failed to start emulator {avd_name}")
                
        except Exception as e:
            logger.error(f"Error creating emulator: {e}")
            raise
    
    def create_lightweight_emulator(self, name_suffix: str = None) -> EmulatorInstance:
        """Create a lightweight emulator for emergency/fallback scenarios"""
        try:
            # Use the lightest config available
            lightweight_config = EmulatorConfig(
                name="lightweight_emergency",
                device_type="emergency",
                api_level=29,  # Lighter API level
                target="google_apis",
                resolution="720x1280",  # Lower resolution
                density="280dpi",
                ram_size="2048M",  # Less RAM
                heap_size="128M",  # Smaller heap
                internal_storage="2048M",  # Less storage
                sd_card_size="256M",
                gpu="swiftshader_indirect",
                enable_camera=False,  # Disable camera
                enable_gps=False      # Disable GPS
            )
            
            # Generate unique AVD name
            if name_suffix:
                avd_name = f"emergency_{name_suffix}_{int(time.time())}"
            else:
                avd_name = f"emergency_{int(time.time())}"
            
            # Create AVD if it doesn't exist
            if not self._avd_exists(avd_name):
                self.create_avd(lightweight_config, avd_name)
            
            # Start the emulator
            instance = self.start_emulator(avd_name, lightweight_config, headless=True)
            
            if instance and instance.is_ready:
                return instance
            else:
                raise RuntimeError(f"Failed to start lightweight emulator {avd_name}")
                
        except Exception as e:
            logger.error(f"Error creating lightweight emulator: {e}")
            raise

# Global emulator manager
_emulator_manager = None

def get_emulator_manager() -> EmulatorManager:
    """Get global emulator manager instance"""
    global _emulator_manager
    if _emulator_manager is None:
        _emulator_manager = EmulatorManager()
    return _emulator_manager

def cleanup_emulators():
    """Cleanup function for graceful shutdown"""
    global _emulator_manager
    if _emulator_manager:
        _emulator_manager.stop_all_emulators()

# Register cleanup handler
import atexit
atexit.register(cleanup_emulators)

if __name__ == "__main__":
    # Test emulator manager
    manager = EmulatorManager()
    
    try:
        # Test creating single emulator
        config = manager.device_configs[0]
        avd_name = f"test_emulator_{int(time.time())}"
        
        print(f"Creating AVD: {avd_name}")
        manager.create_avd(config, avd_name)
        
        print(f"Starting emulator: {avd_name}")
        instance = manager.start_emulator(avd_name, config, headless=True)
        
        print(f"Emulator started: {instance.device_id}")
        print(f"Port: {instance.port}")
        print(f"Ready: {instance.is_ready}")
        
        # Wait a bit then stop
        time.sleep(30)
        print("Stopping emulator...")
        manager.stop_emulator(avd_name)
        
    except KeyboardInterrupt:
        print("Interrupted by user")
        manager.stop_all_emulators()
    except Exception as e:
        print(f"Error: {e}")
        manager.stop_all_emulators()
    
    print("Test completed")