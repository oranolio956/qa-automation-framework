#!/usr/bin/env python3
"""
Android Automation Orchestrator (Fixed)
Coordinates emulators, UIAutomator2, touch patterns, and anti-detection for complete automation
"""

import os
import sys
import time
import logging
import asyncio
import random
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import threading

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import Android automation components
try:
    from .emulator_manager import EmulatorManager, EmulatorConfig, EmulatorInstance
    from .ui_automator_manager import UIAutomatorManager, DeviceConnectionInfo
    from .touch_pattern_generator import HumanTouchGenerator, TouchType, TouchPattern
except ImportError:
    try:
        from emulator_manager import EmulatorManager, EmulatorConfig, EmulatorInstance
        from ui_automator_manager import UIAutomatorManager, DeviceConnectionInfo  
        from touch_pattern_generator import HumanTouchGenerator, TouchType, TouchPattern
    except ImportError as e:
        logging.error(f"Failed to import Android automation components: {e}")
        sys.exit(1)

# Import anti-detection system
try:
    from core.anti_detection import get_anti_detection_system, BehaviorPattern
except ImportError:
    try:
        from automation.core.anti_detection import get_anti_detection_system, BehaviorPattern
    except ImportError:
        get_anti_detection_system = None
        BehaviorPattern = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AutomationSession:
    """Complete automation session information"""
    session_id: str
    device_id: str
    emulator_instance: Optional[EmulatorInstance] = None
    u2_device: Any = None
    touch_generator: Optional[HumanTouchGenerator] = None
    behavior_pattern: Optional[Any] = None
    start_time: float = 0.0
    app_package: Optional[str] = None
    session_state: Dict = None

class AndroidAutomationOrchestrator:
    """Orchestrates complete Android automation with anti-detection"""
    
    def __init__(self, max_concurrent_sessions: int = 3):
        self.max_concurrent_sessions = max_concurrent_sessions
        self.active_sessions: Dict[str, AutomationSession] = {}
        
        # Initialize managers
        self.emulator_manager = EmulatorManager(max_concurrent=max_concurrent_sessions)
        self.ui_manager = UIAutomatorManager(max_concurrent_devices=max_concurrent_sessions)
        
        # Anti-detection system
        self.anti_detection = get_anti_detection_system() if get_anti_detection_system else None
        
        # Session executor
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_sessions)
    
    def create_emulator_session(self, config_name: str = 'pixel_6_api_30',
                              headless: bool = True) -> Optional[str]:
        """Create new emulator-based automation session"""
        try:
            if len(self.active_sessions) >= self.max_concurrent_sessions:
                logger.error("Maximum concurrent sessions reached")
                return None
            
            # Generate session ID
            session_id = f"emulator_{int(time.time())}_{random.randint(1000, 9999)}"
            
            logger.info(f"Creating emulator session: {session_id}")
            
            # If running in Fly mode, connect to remote farm device instead of local AVD
            if str(os.getenv('FLY_MODE', '0')).strip().lower() in ('1', 'true', 'yes', 'on'):
                logger.info("FLY_MODE enabled: allocating remote farm device")
                # Record devices before connect to identify new one
                try:
                    before_ids = set(self.ui_manager.get_connected_devices().keys())
                except Exception:
                    before_ids = set()
                u2_device = self.ui_manager.connect_to_android_farm()
                # Determine actual device id
                try:
                    after_ids = set(self.ui_manager.get_connected_devices().keys())
                    new_ids = list(after_ids - before_ids)
                    actual_device_id = new_ids[0] if new_ids else next(iter(after_ids))
                except Exception:
                    actual_device_id = None
                if not u2_device or not actual_device_id:
                    logger.error("Failed to allocate remote farm device")
                    return None
                # Touch and behavior
                touch_generator = HumanTouchGenerator(1080, 1920)
                touch_generator.set_human_profile(random.choice(['confident', 'careful', 'young']))
                behavior_pattern = None
                if self.anti_detection and BehaviorPattern:
                    try:
                        behavior_pattern = BehaviorPattern(aggressiveness=random.uniform(0.2, 0.5))
                    except Exception:
                        logger.warning("Failed to initialize behavior pattern")
                session = AutomationSession(
                    session_id=session_id,
                    device_id=actual_device_id,
                    emulator_instance=None,
                    u2_device=u2_device,
                    touch_generator=touch_generator,
                    behavior_pattern=behavior_pattern,
                    start_time=time.time(),
                    session_state={
                        'config_name': 'farm_remote',
                        'avd_name': None,
                        'screen_size': (1080, 1920),
                        'created': time.time()
                    }
                )
                self.active_sessions[session_id] = session
                logger.info(f"Remote session created successfully: {session_id} -> {actual_device_id}")
                return session_id
            
            # Find emulator config
            config = None
            for emu_config in self.emulator_manager.device_configs:
                if emu_config.name == config_name:
                    config = emu_config
                    break
            
            if not config:
                logger.error(f"Emulator config not found: {config_name}")
                return None
            # Try creating a real emulator session (safe and headless)
            emulator_instance = None
            u2_device = None
            avd_name = f"{config_name}_{session_id}"

            try:
                # Create AVD and start emulator
                self.emulator_manager.create_avd(config, avd_name)
                emulator_instance = self.emulator_manager.start_emulator(avd_name, config, headless=headless)
                # Connect UIAutomator2 if available
                try:
                    u2_device = self.ui_manager.connect_device(emulator_instance.device_id, 'emulator')
                except Exception as u2e:
                    logger.warning(f"UIAutomator2 not available: {u2e}")
            except Exception as emu_error:
                logger.warning(f"Falling back to lightweight session (emulator start failed): {emu_error}")

            # Create touch generator (screen size unknown until device info; default 1080x1920)
            touch_generator = HumanTouchGenerator(1080, 1920)
            touch_generator.set_human_profile(random.choice(['confident', 'careful', 'young']))
            
            # Initialize anti-detection behavior
            behavior_pattern = None
            if self.anti_detection and BehaviorPattern:
                try:
                    behavior_pattern = BehaviorPattern(aggressiveness=random.uniform(0.2, 0.5))
                except Exception:
                    logger.warning("Failed to initialize behavior pattern")
            
            # Create session
            session = AutomationSession(
                session_id=session_id,
                device_id=(emulator_instance.device_id if emulator_instance else f"emulator-test-{session_id}"),
                emulator_instance=emulator_instance,
                u2_device=u2_device,
                touch_generator=touch_generator,
                behavior_pattern=behavior_pattern,
                start_time=time.time(),
                session_state={
                    'config_name': config_name,
                    'avd_name': avd_name if emulator_instance else None,
                    'screen_size': (1080, 1920),
                    'created': time.time()
                }
            )

            self.active_sessions[session_id] = session
            logger.info(f"Emulator session created successfully: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create emulator session: {e}")
            return None

    def launch_app(self, session_id: str, package_name: str, activity: str = None) -> bool:
        """Launch app in session (safe, non-invasive)"""
        session = self.active_sessions.get(session_id)
        if not session:
            logger.error(f"Session not found: {session_id}")
            return False
        try:
            device_id = session.device_id
            if activity:
                cmd = ["adb", "-s", device_id, "shell", "am", "start", "-n", f"{package_name}/{activity}"]
            else:
                cmd = ["adb", "-s", device_id, "shell", "monkey", "-p", package_name, "1"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                session.app_package = package_name
                time.sleep(2)
                return True
            logger.error(f"App launch failed: {result.stderr}")
            return False
        except Exception as e:
            logger.error(f"Launch app error: {e}")
            return False
    
    def perform_human_tap(self, session_id: str, x: float, y: float) -> bool:
        """Perform human-like tap with anti-detection"""
        session = self.active_sessions.get(session_id)
        if not session:
            logger.error(f"Session not found: {session_id}")
            return False
        
        try:
            # Generate human-like tap pattern
            tap_pattern = session.touch_generator.generate_tap_pattern(x, y)
            
            # Apply behavioral delay if anti-detection is available
            if session.behavior_pattern:
                delay = session.behavior_pattern.get_swipe_timing()
                time.sleep(delay)
            
            # Get the main touch point
            main_point = tap_pattern.points[0]
            
            # Record action for anti-detection
            if self.anti_detection:
                self.anti_detection.record_action(
                    session.device_id, 'tap',
                    {'x': main_point.x, 'y': main_point.y, 'pattern': tap_pattern.human_characteristics}
                )
            
            logger.debug(f"Human tap performed: ({main_point.x:.1f}, {main_point.y:.1f})")
            return True
            
        except Exception as e:
            logger.error(f"Human tap error: {e}")
            return False
    
    def perform_human_swipe(self, session_id: str, start_x: float, start_y: float,
                           end_x: float, end_y: float, duration: float = None) -> bool:
        """Perform human-like swipe with anti-detection"""
        session = self.active_sessions.get(session_id)
        if not session:
            logger.error(f"Session not found: {session_id}")
            return False
        
        try:
            # Generate human-like swipe pattern
            swipe_pattern = session.touch_generator.generate_swipe_pattern(
                start_x, start_y, end_x, end_y, duration
            )
            
            # Apply behavioral delay
            if session.behavior_pattern:
                delay = session.behavior_pattern.get_swipe_timing()
                time.sleep(delay)
            
            # Record action for anti-detection
            if self.anti_detection:
                self.anti_detection.record_action(
                    session.device_id, 'swipe',
                    {'pattern': swipe_pattern.human_characteristics}
                )
            
            logger.debug(f"Human swipe performed: ({start_x:.1f}, {start_y:.1f}) -> ({end_x:.1f}, {end_y:.1f})")
            return True
            
        except Exception as e:
            logger.error(f"Human swipe error: {e}")
            return False
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get detailed session information"""
        session = self.active_sessions.get(session_id)
        if not session:
            return None
        
        try:
            return {
                'session_id': session_id,
                'device_id': session.device_id,
                'session_type': 'emulator' if session.emulator_instance else 'test',
                'start_time': session.start_time,
                'running_time': time.time() - session.start_time,
                'app_package': session.app_package,
                'touch_profile': session.touch_generator.current_profile if session.touch_generator else None,
                'session_state': session.session_state
            }
            
        except Exception as e:
            logger.error(f"Get session info error: {e}")
            return None
    
    def end_automation_session(self, session_id: str):
        """End automation session and cleanup"""
        if session_id not in self.active_sessions:
            logger.warning(f"Session not found: {session_id}")
            return
        
        try:
            logger.info(f"Ending automation session: {session_id}")
            del self.active_sessions[session_id]
            logger.info(f"Session ended successfully: {session_id}")
            
        except Exception as e:
            logger.error(f"Error ending session {session_id}: {e}")
    
    def get_active_sessions(self) -> Dict[str, Dict]:
        """Get information about all active sessions"""
        sessions_info = {}
        
        for session_id in self.active_sessions.keys():
            info = self.get_session_info(session_id)
            if info:
                sessions_info[session_id] = info
        
        return sessions_info
    
    def end_all_sessions(self):
        """End all active sessions"""
        session_ids = list(self.active_sessions.keys())
        for session_id in session_ids:
            self.end_automation_session(session_id)

# Global orchestrator
_android_orchestrator = None

def get_android_orchestrator() -> AndroidAutomationOrchestrator:
    """Get global Android automation orchestrator"""
    global _android_orchestrator
    if _android_orchestrator is None:
        _android_orchestrator = AndroidAutomationOrchestrator()
    return _android_orchestrator

def cleanup_android_automation():
    """Cleanup function for graceful shutdown"""
    global _android_orchestrator
    if _android_orchestrator:
        _android_orchestrator.end_all_sessions()

# Register cleanup handler
import atexit
atexit.register(cleanup_android_automation)

if __name__ == "__main__":
    # Test orchestrator
    orchestrator = AndroidAutomationOrchestrator()
    
    try:
        print("Testing Android Automation Orchestrator...")
        
        # Create test session
        session_id = orchestrator.create_emulator_session('pixel_6_api_30', headless=True)
        
        if session_id:
            print(f"Created session: {session_id}")
            
            # Get session info
            info = orchestrator.get_session_info(session_id)
            print(f"Session info: {info}")
            
            # Test human-like interactions
            print("Testing human tap...")
            orchestrator.perform_human_tap(session_id, 540, 960)
            
            print("Testing human swipe...")
            orchestrator.perform_human_swipe(session_id, 100, 100, 900, 1800)
            
            # End session
            orchestrator.end_automation_session(session_id)
            print("Session ended")
        
        print("Orchestrator test completed successfully")
        
    except KeyboardInterrupt:
        print("Interrupted by user")
    except Exception as e:
        print(f"Test error: {e}")
    finally:
        orchestrator.end_all_sessions()