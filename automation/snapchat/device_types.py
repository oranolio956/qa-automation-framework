#!/usr/bin/env python3
"""
Device Type Definitions and Unified Device ID Management

Provides consistent device identification across all automation modules.
Resolves integration issues between string device IDs and FarmDevice objects.
"""

import logging
from typing import Union, Optional, Dict, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum

logger = logging.getLogger(__name__)


class DeviceType(Enum):
    """Device type enumeration"""
    LOCAL_EMULATOR = "local_emulator"
    FARM_DEVICE = "farm_device"
    PHYSICAL_DEVICE = "physical_device"
    UNKNOWN = "unknown"


@dataclass
class DeviceInfo:
    """Standardized device information"""
    device_id: str
    device_type: DeviceType
    adb_address: str
    display_name: str
    farm_host: Optional[str] = None
    farm_port: Optional[int] = None
    capabilities: Optional[Dict[str, Any]] = None
    is_available: bool = True
    
    def __post_init__(self):
        """Validate device info after initialization"""
        if not self.device_id:
            raise ValueError("device_id cannot be empty")
        if not self.adb_address:
            raise ValueError("adb_address cannot be empty")


class DeviceAdapter(ABC):
    """Abstract base class for device adapters"""
    
    @abstractmethod
    def to_device_info(self) -> DeviceInfo:
        """Convert to standardized DeviceInfo"""
        pass
    
    @abstractmethod
    def get_device_id(self) -> str:
        """Get standardized device ID"""
        pass


class UnifiedDeviceManager:
    """Manages device ID resolution and standardization across all modules"""
    
    def __init__(self):
        self._device_registry: Dict[str, DeviceInfo] = {}
        self._id_mappings: Dict[str, str] = {}  # Maps various ID formats to canonical ID
        
    def register_device(self, device_info: DeviceInfo) -> str:
        """Register a device and return its canonical ID"""
        canonical_id = self._generate_canonical_id(device_info)
        
        self._device_registry[canonical_id] = device_info
        
        # Create mappings for common ID variations
        self._add_id_mapping(device_info.device_id, canonical_id)
        self._add_id_mapping(device_info.adb_address, canonical_id)
        self._add_id_mapping(device_info.display_name, canonical_id)
        
        logger.info(f"Registered device: {canonical_id} ({device_info.display_name})")
        return canonical_id
    
    def resolve_device_id(self, device_identifier: Union[str, 'FarmDevice', Any]) -> Optional[str]:
        """Resolve any device identifier to canonical device ID"""
        try:
            # Handle string IDs
            if isinstance(device_identifier, str):
                return self._resolve_string_id(device_identifier)
            
            # Handle FarmDevice objects (from farm_manager.py)
            if hasattr(device_identifier, 'device_id') and hasattr(device_identifier, 'adb_address'):
                return self._resolve_farm_device(device_identifier)
            
            # Handle UIAutomator2 device objects
            if hasattr(device_identifier, 'serial'):
                return self._resolve_u2_device(device_identifier)
            
            # Handle emulator objects
            if hasattr(device_identifier, 'avd_name'):
                return self._resolve_emulator(device_identifier)
            
            logger.warning(f"Unknown device identifier type: {type(device_identifier)}")
            return None
            
        except Exception as e:
            logger.error(f"Error resolving device ID for {device_identifier}: {e}")
            return None
    
    def get_device_info(self, device_identifier: Union[str, Any]) -> Optional[DeviceInfo]:
        """Get DeviceInfo for any device identifier"""
        canonical_id = self.resolve_device_id(device_identifier)
        if canonical_id:
            return self._device_registry.get(canonical_id)
        return None
    
    def get_adb_address(self, device_identifier: Union[str, Any]) -> Optional[str]:
        """Get ADB address for any device identifier"""
        device_info = self.get_device_info(device_identifier)
        return device_info.adb_address if device_info else None
    
    def is_device_available(self, device_identifier: Union[str, Any]) -> bool:
        """Check if device is available"""
        device_info = self.get_device_info(device_identifier)
        return device_info.is_available if device_info else False
    
    def update_device_status(self, device_identifier: Union[str, Any], is_available: bool):
        """Update device availability status"""
        canonical_id = self.resolve_device_id(device_identifier)
        if canonical_id and canonical_id in self._device_registry:
            self._device_registry[canonical_id].is_available = is_available
            logger.debug(f"Updated device {canonical_id} availability: {is_available}")
    
    def list_devices(self, device_type: Optional[DeviceType] = None) -> Dict[str, DeviceInfo]:
        """List all registered devices, optionally filtered by type"""
        if device_type is None:
            return self._device_registry.copy()
        
        return {
            device_id: info 
            for device_id, info in self._device_registry.items()
            if info.device_type == device_type
        }
    
    def _generate_canonical_id(self, device_info: DeviceInfo) -> str:
        """Generate canonical device ID"""
        if device_info.device_type == DeviceType.FARM_DEVICE:
            return f"farm_{device_info.device_id}"
        elif device_info.device_type == DeviceType.LOCAL_EMULATOR:
            return f"emu_{device_info.device_id}"
        elif device_info.device_type == DeviceType.PHYSICAL_DEVICE:
            return f"phy_{device_info.device_id}"
        else:
            return f"dev_{device_info.device_id}"
    
    def _add_id_mapping(self, alias_id: str, canonical_id: str):
        """Add ID mapping for resolution"""
        if alias_id and alias_id != canonical_id:
            self._id_mappings[alias_id] = canonical_id
    
    def _resolve_string_id(self, device_id: str) -> Optional[str]:
        """Resolve string device ID"""
        # Direct match in registry
        if device_id in self._device_registry:
            return device_id
        
        # Check ID mappings
        if device_id in self._id_mappings:
            return self._id_mappings[device_id]
        
        # Check if it's an ADB address format
        if ':' in device_id:
            for canonical_id, info in self._device_registry.items():
                if info.adb_address == device_id:
                    self._add_id_mapping(device_id, canonical_id)
                    return canonical_id
        
        # Auto-register unknown string IDs as physical devices
        if device_id:
            device_info = DeviceInfo(
                device_id=device_id,
                device_type=DeviceType.PHYSICAL_DEVICE,
                adb_address=device_id,
                display_name=f"Auto-detected: {device_id}"
            )
            return self.register_device(device_info)
        
        return None
    
    def _resolve_farm_device(self, farm_device) -> Optional[str]:
        """Resolve FarmDevice object"""
        device_info = DeviceInfo(
            device_id=farm_device.device_id,
            device_type=DeviceType.FARM_DEVICE,
            adb_address=farm_device.adb_address,
            display_name=getattr(farm_device, 'display_name', f"Farm: {farm_device.device_id}"),
            farm_host=getattr(farm_device, 'host', None),
            farm_port=getattr(farm_device, 'port', None),
            capabilities=getattr(farm_device, 'capabilities', None),
            is_available=getattr(farm_device, 'is_connected', True)
        )
        return self.register_device(device_info)
    
    def _resolve_u2_device(self, u2_device) -> Optional[str]:
        """Resolve UIAutomator2 device object"""
        device_id = u2_device.serial
        adb_address = u2_device.serial if ':' in u2_device.serial else f"{u2_device.serial}:5555"
        
        device_info = DeviceInfo(
            device_id=device_id,
            device_type=DeviceType.PHYSICAL_DEVICE,
            adb_address=adb_address,
            display_name=f"U2: {device_id}"
        )
        return self.register_device(device_info)
    
    def _resolve_emulator(self, emulator) -> Optional[str]:
        """Resolve emulator object"""
        device_id = emulator.avd_name
        adb_address = getattr(emulator, 'adb_address', f"emulator-{device_id}")
        
        device_info = DeviceInfo(
            device_id=device_id,
            device_type=DeviceType.LOCAL_EMULATOR,
            adb_address=adb_address,
            display_name=f"Emulator: {device_id}"
        )
        return self.register_device(device_info)


# Global device manager instance
_device_manager = None


def get_device_manager() -> UnifiedDeviceManager:
    """Get global device manager instance"""
    global _device_manager
    if _device_manager is None:
        _device_manager = UnifiedDeviceManager()
    return _device_manager


def resolve_device_id(device_identifier: Union[str, Any]) -> Optional[str]:
    """Global function to resolve device ID"""
    return get_device_manager().resolve_device_id(device_identifier)


def get_adb_address(device_identifier: Union[str, Any]) -> Optional[str]:
    """Global function to get ADB address"""
    return get_device_manager().get_adb_address(device_identifier)


def register_device(device_info: DeviceInfo) -> str:
    """Global function to register device"""
    return get_device_manager().register_device(device_info)


class DeviceCompatibilityAdapter:
    """Adapter for backward compatibility with existing modules"""
    
    @staticmethod
    def ensure_string_device_id(device_identifier: Union[str, Any]) -> str:
        """Ensure device identifier is converted to string device ID"""
        resolved_id = resolve_device_id(device_identifier)
        if resolved_id is None:
            # Fallback for unknown device types
            if hasattr(device_identifier, 'device_id'):
                return str(device_identifier.device_id)
            elif hasattr(device_identifier, 'serial'):
                return str(device_identifier.serial)
            else:
                return str(device_identifier)
        return resolved_id
    
    @staticmethod
    def ensure_adb_address(device_identifier: Union[str, Any]) -> str:
        """Ensure device identifier is converted to ADB address"""
        adb_address = get_adb_address(device_identifier)
        if adb_address is None:
            # Fallback logic
            string_id = DeviceCompatibilityAdapter.ensure_string_device_id(device_identifier)
            if ':' in string_id:
                return string_id
            else:
                return f"{string_id}:5555"  # Default ADB port
        return adb_address


if __name__ == "__main__":
    # Test device manager functionality
    manager = get_device_manager()
    
    # Test device registration
    test_device = DeviceInfo(
        device_id="test_device_001",
        device_type=DeviceType.LOCAL_EMULATOR,
        adb_address="localhost:5554",
        display_name="Test Emulator"
    )
    
    canonical_id = manager.register_device(test_device)
    print(f"Registered device with canonical ID: {canonical_id}")
    
    # Test resolution
    resolved_id = manager.resolve_device_id("test_device_001")
    print(f"Resolved 'test_device_001' to: {resolved_id}")
    
    resolved_id = manager.resolve_device_id("localhost:5554")
    print(f"Resolved 'localhost:5554' to: {resolved_id}")
    
    # Test device info retrieval
    device_info = manager.get_device_info("test_device_001")
    print(f"Device info: {device_info}")
    
    # Test compatibility adapter
    string_id = DeviceCompatibilityAdapter.ensure_string_device_id("localhost:5554")
    print(f"Compatibility adapter string ID: {string_id}")
    
    adb_addr = DeviceCompatibilityAdapter.ensure_adb_address("test_device_001")
    print(f"Compatibility adapter ADB address: {adb_addr}")