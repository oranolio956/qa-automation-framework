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
from brightdata_proxy import get_brightdata_session

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
        self.avd_manager = os.path.join(self.sdk_path, "cmdline-tools", "latest", "bin", "avdmanager")
        self.sdkmanager = os.path.join(self.sdk_path, "cmdline-tools", "latest", "bin", "sdkmanager")
        self.emulator = os.path.join(self.sdk_path, "emulator", "emulator")
        
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
                
        raise RuntimeError("Android SDK not found. Please install Android SDK and set ANDROID_HOME")
    
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
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
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
            # Disable animations for faster automation
            animations_settings = [
                ("global", "animator_duration_scale", "0"),
                ("global", "transition_animation_scale", "0"),
                ("global", "window_animation_scale", "0")
            ]
            
            for namespace, key, value in animations_settings:
                cmd = ["adb", "-s", device_id, "shell", "settings", "put", namespace, key, value]
                subprocess.run(cmd, check=True)
            
            # Set mock location app (for GPS spoofing if needed)
            cmd = ["adb", "-s", device_id, "shell", "appops", "set", "com.android.settings", 
                   "MOCK_LOCATION", "allow"]
            subprocess.run(cmd, check=False)  # May fail on some Android versions
            
            # Install CA certificates for HTTPS interception if needed
            # (Implementation would depend on specific requirements)
            
            # Set up file system for automation
            cmd = ["adb", "-s", device_id, "shell", "mkdir", "-p", "/sdcard/automation"]
            subprocess.run(cmd, check=True)
            
            logger.info(f"Emulator environment setup complete: {device_id}")
            
        except Exception as e:
            logger.error(f"Failed to set up emulator environment: {e}")
    
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