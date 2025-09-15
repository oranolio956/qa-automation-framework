#!/usr/bin/env python3
"""
Device Farm Integration Module

Provides reliable device farm connectivity with health checks, backoff, and explicit connection management.
Replaces the problematic fly_integration_patch with a proper typed integration.
"""

import os
import time
import logging
import asyncio
import subprocess
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import random

# Import unified device management
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / 'snapchat'))
from device_types import DeviceInfo, DeviceType, get_device_manager, DeviceAdapter

logger = logging.getLogger(__name__)


class DeviceState(Enum):
    """Device states in the farm"""
    UNKNOWN = "unknown"
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"


@dataclass
class FarmDevice(DeviceAdapter):
    """Device information from farm"""
    device_id: str
    host: str
    port: int
    state: DeviceState = DeviceState.UNKNOWN
    platform: str = "android"
    api_level: Optional[int] = None
    architecture: Optional[str] = None
    screen_resolution: Optional[str] = None
    last_ping: Optional[datetime] = None
    connection_attempts: int = 0
    max_connection_attempts: int = 5
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def address(self) -> str:
        """Get device address string"""
        return f"{self.host}:{self.port}"
    
    @property
    def adb_address(self) -> str:
        """Get ADB address for unified device management"""
        return self.address
    
    @property
    def is_healthy(self) -> bool:
        """Check if device is healthy based on last ping"""
        if not self.last_ping:
            return False
        return (datetime.now() - self.last_ping) < timedelta(minutes=5)
    
    @property
    def can_connect(self) -> bool:
        """Check if device can accept new connections"""
        return (self.state in [DeviceState.AVAILABLE, DeviceState.DISCONNECTED] 
                and self.connection_attempts < self.max_connection_attempts)
    
    @property
    def is_connected(self) -> bool:
        """Check if device is currently connected"""
        return self.state == DeviceState.CONNECTED
    
    def to_device_info(self) -> DeviceInfo:
        """Convert to standardized DeviceInfo"""
        return DeviceInfo(
            device_id=self.device_id,
            device_type=DeviceType.FARM_DEVICE,
            adb_address=self.adb_address,
            display_name=f"Farm: {self.device_id}",
            farm_host=self.host,
            farm_port=self.port,
            capabilities={
                'platform': self.platform,
                'api_level': self.api_level,
                'architecture': self.architecture,
                'screen_resolution': self.screen_resolution,
                **self.metadata
            },
            is_available=(self.state == DeviceState.AVAILABLE and self.is_healthy)
        )
    
    def get_device_id(self) -> str:
        """Get standardized device ID"""
        return self.device_id


@dataclass
class FarmConnectionConfig:
    """Configuration for farm connections"""
    farm_endpoint: str
    api_key: Optional[str] = None
    timeout_seconds: int = 30
    retry_attempts: int = 3
    retry_delay_base: float = 2.0
    retry_delay_max: float = 30.0
    health_check_interval: int = 300  # 5 minutes
    max_concurrent_connections: int = 10
    device_selection_strategy: str = "random"  # random, round_robin, least_loaded


class DeviceFarmManager:
    """Manages connections to remote device farms with reliability and health monitoring"""
    
    def __init__(self, config: FarmConnectionConfig):
        self.config = config
        self.devices: Dict[str, FarmDevice] = {}
        self.active_connections: Dict[str, Any] = {}
        self.connection_pool_size = 0
        self.last_health_check = datetime.now()
        
        # Connection management
        self._connection_lock = asyncio.Lock()
        self._device_locks: Dict[str, asyncio.Lock] = {}
        
        logger.info(f"Device Farm Manager initialized: {config.farm_endpoint}")
    
    async def discover_devices(self) -> List[FarmDevice]:
        """Discover available devices from the farm"""
        try:
            logger.info("Discovering devices from farm...")
            
            # Implementation depends on farm API
            # For now, simulate discovery with environment-based config
            discovered = await self._discover_from_environment()
            
            # Update device registry and register with unified device manager
            device_manager = get_device_manager()
            for device in discovered:
                self.devices[device.device_id] = device
                if device.device_id not in self._device_locks:
                    self._device_locks[device.device_id] = asyncio.Lock()
                
                # Register with unified device manager
                device_info = device.to_device_info()
                canonical_id = device_manager.register_device(device_info)
                logger.debug(f"Registered farm device {device.device_id} as {canonical_id}")
            
            # Perform initial health checks
            await self._perform_health_checks()
            
            logger.info(f"Discovered {len(discovered)} devices")
            return discovered
            
        except Exception as e:
            logger.error(f"Device discovery failed: {e}")
            return []
    
    async def connect_device(self, device_id: str = None) -> Optional[FarmDevice]:
        """Connect to a specific device or select best available"""
        async with self._connection_lock:
            try:
                # Select device
                if device_id:
                    if device_id not in self.devices:
                        logger.error(f"Device {device_id} not found in registry")
                        return None
                    device = self.devices[device_id]
                else:
                    device = await self._select_best_device()
                    if not device:
                        logger.error("No suitable devices available")
                        return None
                
                # Check connection limits
                if len(self.active_connections) >= self.config.max_concurrent_connections:
                    logger.warning("Maximum concurrent connections reached")
                    return None
                
                # Connect with device-specific lock
                async with self._device_locks[device.device_id]:
                    if device.device_id in self.active_connections:
                        logger.warning(f"Device {device.device_id} already connected")
                        return device
                    
                    # Attempt connection with retry
                    connected = await self._connect_with_retry(device)
                    if connected:
                        self.active_connections[device.device_id] = {
                            'device': device,
                            'connected_at': datetime.now(),
                            'last_activity': datetime.now()
                        }
                        device.state = DeviceState.CONNECTED
                        logger.info(f"Successfully connected to device {device.device_id}")
                        return device
                    else:
                        logger.error(f"Failed to connect to device {device.device_id}")
                        return None
                        
            except Exception as e:
                logger.error(f"Device connection error: {e}")
                return None
    
    async def disconnect_device(self, device_id: str) -> bool:
        """Disconnect from a specific device"""
        try:
            if device_id not in self.active_connections:
                logger.warning(f"Device {device_id} not connected")
                return True
            
            async with self._device_locks.get(device_id, asyncio.Lock()):
                # Perform disconnection
                success = await self._disconnect_device_safely(device_id)
                
                if success:
                    # Clean up connection tracking
                    del self.active_connections[device_id]
                    if device_id in self.devices:
                        self.devices[device_id].state = DeviceState.DISCONNECTED
                    logger.info(f"Disconnected from device {device_id}")
                    return True
                else:
                    logger.error(f"Failed to disconnect from device {device_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Device disconnection error: {e}")
            return False
    
    async def health_check_device(self, device_id: str) -> bool:
        """Perform health check on specific device"""
        try:
            if device_id not in self.devices:
                return False
            
            device = self.devices[device_id]
            
            # Ping device
            ping_success = await self._ping_device(device)
            
            if ping_success:
                device.last_ping = datetime.now()
                if device.state == DeviceState.ERROR:
                    device.state = DeviceState.AVAILABLE
                return True
            else:
                device.state = DeviceState.ERROR
                return False
                
        except Exception as e:
            logger.error(f"Health check failed for {device_id}: {e}")
            return False
    
    async def get_device_info(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed device information"""
        try:
            if device_id not in self.devices:
                return None
            
            device = self.devices[device_id]
            
            # Get real-time device info if connected
            if device_id in self.active_connections:
                runtime_info = await self._get_runtime_device_info(device)
            else:
                runtime_info = {}
            
            return {
                'device_id': device.device_id,
                'address': device.address,
                'state': device.state.value,
                'platform': device.platform,
                'api_level': device.api_level,
                'architecture': device.architecture,
                'screen_resolution': device.screen_resolution,
                'last_ping': device.last_ping.isoformat() if device.last_ping else None,
                'is_healthy': device.is_healthy,
                'connection_attempts': device.connection_attempts,
                'metadata': device.metadata,
                **runtime_info
            }
            
        except Exception as e:
            logger.error(f"Error getting device info for {device_id}: {e}")
            return None
    
    async def cleanup_all_connections(self):
        """Clean up all active connections"""
        try:
            logger.info("Cleaning up all device connections...")
            
            disconnect_tasks = []
            for device_id in list(self.active_connections.keys()):
                disconnect_tasks.append(self.disconnect_device(device_id))
            
            if disconnect_tasks:
                await asyncio.gather(*disconnect_tasks, return_exceptions=True)
            
            self.active_connections.clear()
            logger.info("All connections cleaned up")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    async def get_farm_status(self) -> Dict[str, Any]:
        """Get overall farm status"""
        try:
            total_devices = len(self.devices)
            available_devices = len([d for d in self.devices.values() if d.state == DeviceState.AVAILABLE])
            connected_devices = len(self.active_connections)
            healthy_devices = len([d for d in self.devices.values() if d.is_healthy])
            
            return {
                'farm_endpoint': self.config.farm_endpoint,
                'total_devices': total_devices,
                'available_devices': available_devices,
                'connected_devices': connected_devices,
                'healthy_devices': healthy_devices,
                'connection_utilization': connected_devices / self.config.max_concurrent_connections if self.config.max_concurrent_connections > 0 else 0,
                'last_health_check': self.last_health_check.isoformat(),
                'devices': {device_id: device.state.value for device_id, device in self.devices.items()}
            }
            
        except Exception as e:
            logger.error(f"Error getting farm status: {e}")
            return {'error': str(e)}
    
    # Private methods
    
    async def _discover_from_environment(self) -> List[FarmDevice]:
        """Discover devices from environment configuration"""
        devices = []
        
        # Example: read from environment variables
        farm_devices_config = os.environ.get('FARM_DEVICES_CONFIG')
        if farm_devices_config:
            try:
                config = json.loads(farm_devices_config)
                for device_config in config.get('devices', []):
                    device = FarmDevice(
                        device_id=device_config['device_id'],
                        host=device_config['host'],
                        port=device_config['port'],
                        state=DeviceState.AVAILABLE,
                        api_level=device_config.get('api_level'),
                        architecture=device_config.get('architecture'),
                        screen_resolution=device_config.get('screen_resolution'),
                        metadata=device_config.get('metadata', {})
                    )
                    devices.append(device)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid farm devices config: {e}")
        
        # Fallback: discover from standard ports
        if not devices:
            farm_host = os.environ.get('FARM_HOST', 'localhost')
            for port in range(5555, 5565):  # Standard ADB port range
                device = FarmDevice(
                    device_id=f"farm_device_{port}",
                    host=farm_host,
                    port=port,
                    state=DeviceState.UNKNOWN
                )
                devices.append(device)
        
        return devices
    
    async def _select_best_device(self) -> Optional[FarmDevice]:
        """Select best available device based on strategy"""
        available_devices = [d for d in self.devices.values() if d.can_connect and d.is_healthy]
        
        if not available_devices:
            return None
        
        if self.config.device_selection_strategy == "random":
            return random.choice(available_devices)
        elif self.config.device_selection_strategy == "round_robin":
            # Simple round-robin based on connection attempts
            return min(available_devices, key=lambda d: d.connection_attempts)
        elif self.config.device_selection_strategy == "least_loaded":
            # Select device with least active connections (simplified)
            return min(available_devices, key=lambda d: d.connection_attempts)
        else:
            return available_devices[0]
    
    async def _connect_with_retry(self, device: FarmDevice) -> bool:
        """Connect to device with exponential backoff retry"""
        for attempt in range(self.config.retry_attempts):
            try:
                device.connection_attempts += 1
                device.state = DeviceState.CONNECTING
                
                # Attempt ADB connection
                success = await self._perform_adb_connect(device)
                
                if success:
                    device.connection_attempts = 0  # Reset on success
                    return True
                
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed for {device.device_id}: {e}")
            
            # Exponential backoff
            if attempt < self.config.retry_attempts - 1:
                delay = min(
                    self.config.retry_delay_base * (2 ** attempt),
                    self.config.retry_delay_max
                )
                await asyncio.sleep(delay)
        
        device.state = DeviceState.ERROR
        return False
    
    async def _perform_adb_connect(self, device: FarmDevice) -> bool:
        """Perform actual ADB connection"""
        try:
            # Connect via ADB
            result = await asyncio.create_subprocess_exec(
                'adb', 'connect', device.address,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=self.config.timeout_seconds)
            
            if result.returncode == 0 and b'connected' in stdout.lower():
                # Verify connection with device info
                return await self._verify_device_connection(device)
            else:
                logger.warning(f"ADB connect failed for {device.address}: {stderr.decode()}")
                return False
                
        except asyncio.TimeoutError:
            logger.warning(f"ADB connect timeout for {device.address}")
            return False
        except Exception as e:
            logger.error(f"ADB connect error for {device.address}: {e}")
            return False
    
    async def _verify_device_connection(self, device: FarmDevice) -> bool:
        """Verify device connection is working"""
        try:
            # Get device properties
            result = await asyncio.create_subprocess_exec(
                'adb', '-s', device.address, 'shell', 'getprop', 'ro.build.version.sdk',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=10)
            
            if result.returncode == 0:
                api_level = stdout.decode().strip()
                if api_level.isdigit():
                    device.api_level = int(api_level)
                    device.last_ping = datetime.now()
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Device verification failed for {device.address}: {e}")
            return False
    
    async def _disconnect_device_safely(self, device_id: str) -> bool:
        """Safely disconnect device"""
        try:
            device = self.devices.get(device_id)
            if not device:
                return True
            
            # Disconnect via ADB
            result = await asyncio.create_subprocess_exec(
                'adb', 'disconnect', device.address,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(result.communicate(), timeout=10)
            
            return True
            
        except Exception as e:
            logger.error(f"Device disconnect error for {device_id}: {e}")
            return False
    
    async def _ping_device(self, device: FarmDevice) -> bool:
        """Ping device to check if it's responsive"""
        try:
            result = await asyncio.create_subprocess_exec(
                'adb', '-s', device.address, 'shell', 'echo', 'ping',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=5)
            
            return result.returncode == 0 and b'ping' in stdout
            
        except Exception:
            return False
    
    async def _get_runtime_device_info(self, device: FarmDevice) -> Dict[str, Any]:
        """Get runtime device information"""
        try:
            info = {}
            
            # Get battery level
            result = await asyncio.create_subprocess_exec(
                'adb', '-s', device.address, 'shell', 'dumpsys', 'battery',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=5)
            
            if result.returncode == 0:
                battery_output = stdout.decode()
                for line in battery_output.split('\n'):
                    if 'level:' in line:
                        try:
                            info['battery_level'] = int(line.split(':')[1].strip())
                        except:
                            pass
                        break
            
            return info
            
        except Exception:
            return {}
    
    async def _perform_health_checks(self):
        """Perform health checks on all devices"""
        try:
            if not self.devices:
                return
            
            health_tasks = []
            for device_id in self.devices:
                health_tasks.append(self.health_check_device(device_id))
            
            results = await asyncio.gather(*health_tasks, return_exceptions=True)
            
            healthy_count = sum(1 for result in results if result is True)
            logger.info(f"Health check complete: {healthy_count}/{len(self.devices)} devices healthy")
            
            self.last_health_check = datetime.now()
            
        except Exception as e:
            logger.error(f"Health check error: {e}")


# Sync wrapper for backward compatibility
class DeviceFarmManagerSync:
    """Synchronous wrapper for DeviceFarmManager"""
    
    def __init__(self, config: FarmConnectionConfig):
        self.async_manager = DeviceFarmManager(config)
        self._loop = None
    
    def _ensure_loop(self):
        """Ensure event loop is available"""
        try:
            self._loop = asyncio.get_event_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
    
    def discover_devices(self) -> List[FarmDevice]:
        """Sync wrapper for discover_devices"""
        self._ensure_loop()
        return self._loop.run_until_complete(self.async_manager.discover_devices())
    
    def connect_device(self, device_id: str = None) -> Optional[FarmDevice]:
        """Sync wrapper for connect_device"""
        self._ensure_loop()
        return self._loop.run_until_complete(self.async_manager.connect_device(device_id))
    
    def disconnect_device(self, device_id: str) -> bool:
        """Sync wrapper for disconnect_device"""
        self._ensure_loop()
        return self._loop.run_until_complete(self.async_manager.disconnect_device(device_id))
    
    def get_farm_status(self) -> Dict[str, Any]:
        """Sync wrapper for get_farm_status"""
        self._ensure_loop()
        return self._loop.run_until_complete(self.async_manager.get_farm_status())


def get_device_farm_manager(config: FarmConnectionConfig, sync: bool = False):
    """Get device farm manager instance"""
    if sync:
        return DeviceFarmManagerSync(config)
    else:
        return DeviceFarmManager(config)


if __name__ == "__main__":
    # Command line interface for farm management
    import argparse
    
    async def main():
        parser = argparse.ArgumentParser(description='Device Farm Manager')
        parser.add_argument('--endpoint', type=str, default='http://localhost:8080', help='Farm endpoint')
        parser.add_argument('--discover', action='store_true', help='Discover devices')
        parser.add_argument('--status', action='store_true', help='Get farm status')
        parser.add_argument('--connect', type=str, help='Connect to specific device')
        parser.add_argument('--disconnect', type=str, help='Disconnect from device')
        
        args = parser.parse_args()
        
        config = FarmConnectionConfig(farm_endpoint=args.endpoint)
        manager = DeviceFarmManager(config)
        
        try:
            if args.discover:
                devices = await manager.discover_devices()
                print(f"Discovered {len(devices)} devices:")
                for device in devices:
                    print(f"  {device.device_id} - {device.address} ({device.state.value})")
            
            elif args.status:
                status = await manager.get_farm_status()
                print(json.dumps(status, indent=2))
            
            elif args.connect:
                device = await manager.connect_device(args.connect)
                if device:
                    print(f"✅ Connected to {device.device_id}")
                else:
                    print(f"❌ Failed to connect to {args.connect}")
            
            elif args.disconnect:
                success = await manager.disconnect_device(args.disconnect)
                if success:
                    print(f"✅ Disconnected from {args.disconnect}")
                else:
                    print(f"❌ Failed to disconnect from {args.disconnect}")
            
            else:
                parser.print_help()
        
        finally:
            await manager.cleanup_all_connections()
    
    asyncio.run(main())