#!/usr/bin/env python3
"""
Tinder Account Warming Scheduler
Implements sophisticated account warming and activity scheduling to avoid bans
"""

import os
import sys
import time
import random
import logging
import json
import schedule
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, date
from enum import Enum
import threading
import queue
import redis
from concurrent.futures import ThreadPoolExecutor

# Import automation components
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from android.emulator_manager import EmulatorInstance, get_emulator_manager
from core.anti_detection import get_anti_detection_system
from tinder.account_creator import TinderAppAutomator, AccountCreationResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AccountStatus(Enum):
    """Account status during warming process"""
    CREATED = "created"
    WARMING_DAY_1 = "warming_day_1" 
    WARMING_WEEK_1 = "warming_week_1"
    WARMING_WEEK_2 = "warming_week_2"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    BANNED = "banned"
    ERROR = "error"

class ActivityType(Enum):
    """Types of activities for warming"""
    APP_OPEN = "app_open"
    PROFILE_VIEW = "profile_view"
    SWIPE_RIGHT = "swipe_right"
    SWIPE_LEFT = "swipe_left"
    SUPER_LIKE = "super_like"
    MESSAGE_SEND = "message_send"
    MESSAGE_READ = "message_read"
    PROFILE_EDIT = "profile_edit"
    SETTINGS_CHECK = "settings_check"
    PHOTO_ADD = "photo_add"

@dataclass
class WarmingSchedule:
    """Warming schedule configuration"""
    status: AccountStatus
    daily_sessions: int
    session_duration_min: int
    session_duration_max: int
    activities_per_session: int
    activity_types: List[ActivityType]
    break_between_sessions_min: int  # minutes
    break_between_sessions_max: int  # minutes
    swipe_ratio_right: float  # 0.0 to 1.0
    super_like_frequency: float  # per session
    messaging_probability: float  # 0.0 to 1.0

@dataclass
class AccountWarmingState:
    """Current warming state of an account"""
    account_id: str
    device_id: str
    status: AccountStatus
    creation_date: datetime
    last_activity: datetime
    total_sessions: int
    total_swipes: int
    total_matches: int
    total_messages: int
    warming_schedule: WarmingSchedule
    next_session_time: datetime
    consecutive_errors: int = 0
    is_suspended: bool = False

@dataclass
class ActivityLog:
    """Log entry for account activity"""
    account_id: str
    timestamp: datetime
    activity_type: ActivityType
    details: Dict[str, any]
    success: bool
    error_message: Optional[str] = None

class WarmingSchedules:
    """Predefined warming schedules for different phases"""
    
    @staticmethod
    def day_1_schedule() -> WarmingSchedule:
        """Ultra-conservative schedule for first 24 hours"""
        return WarmingSchedule(
            status=AccountStatus.WARMING_DAY_1,
            daily_sessions=2,
            session_duration_min=3,
            session_duration_max=8,
            activities_per_session=15,
            activity_types=[
                ActivityType.APP_OPEN,
                ActivityType.PROFILE_VIEW,
                ActivityType.SWIPE_LEFT,
                ActivityType.SWIPE_RIGHT,
                ActivityType.SETTINGS_CHECK
            ],
            break_between_sessions_min=180,  # 3 hours minimum
            break_between_sessions_max=480,  # 8 hours maximum
            swipe_ratio_right=0.15,  # Very conservative swiping
            super_like_frequency=0.0,  # No super likes
            messaging_probability=0.0  # No messaging
        )
    
    @staticmethod
    def week_1_schedule() -> WarmingSchedule:
        """Conservative schedule for first week"""
        return WarmingSchedule(
            status=AccountStatus.WARMING_WEEK_1,
            daily_sessions=3,
            session_duration_min=5,
            session_duration_max=15,
            activities_per_session=35,
            activity_types=[
                ActivityType.APP_OPEN,
                ActivityType.PROFILE_VIEW,
                ActivityType.SWIPE_LEFT,
                ActivityType.SWIPE_RIGHT,
                ActivityType.SUPER_LIKE,
                ActivityType.SETTINGS_CHECK,
                ActivityType.PROFILE_EDIT
            ],
            break_between_sessions_min=120,  # 2 hours minimum
            break_between_sessions_max=360,  # 6 hours maximum
            swipe_ratio_right=0.25,
            super_like_frequency=0.2,  # 1 every 5 sessions
            messaging_probability=0.1  # Minimal messaging
        )
    
    @staticmethod
    def week_2_schedule() -> WarmingSchedule:
        """Moderate schedule for second week"""
        return WarmingSchedule(
            status=AccountStatus.WARMING_WEEK_2,
            daily_sessions=4,
            session_duration_min=8,
            session_duration_max=25,
            activities_per_session=60,
            activity_types=list(ActivityType),  # All activities
            break_between_sessions_min=90,   # 1.5 hours minimum
            break_between_sessions_max=300,  # 5 hours maximum
            swipe_ratio_right=0.35,
            super_like_frequency=0.5,  # 1 every 2 sessions
            messaging_probability=0.3
        )
    
    @staticmethod
    def active_schedule() -> WarmingSchedule:
        """Full activity schedule for warmed accounts"""
        return WarmingSchedule(
            status=AccountStatus.ACTIVE,
            daily_sessions=6,
            session_duration_min=10,
            session_duration_max=35,
            activities_per_session=100,
            activity_types=list(ActivityType),
            break_between_sessions_min=60,   # 1 hour minimum
            break_between_sessions_max=240,  # 4 hours maximum
            swipe_ratio_right=0.45,
            super_like_frequency=1.0,  # 1 per session
            messaging_probability=0.6
        )

class TinderActivitySimulator:
    """Simulates realistic Tinder activities"""
    
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.automator = TinderAppAutomator(device_id)
        self.anti_detection = get_anti_detection_system()
        
    def execute_activity(self, activity_type: ActivityType, context: Dict[str, any] = None) -> bool:
        """Execute a specific activity type"""
        try:
            # Record activity start
            self.anti_detection.record_action(self.device_id, activity_type.value)
            
            # Get appropriate delay
            delay = self.anti_detection.get_next_action_delay(self.device_id)
            time.sleep(delay)
            
            # Execute activity
            if activity_type == ActivityType.APP_OPEN:
                return self._simulate_app_open()
            elif activity_type == ActivityType.PROFILE_VIEW:
                return self._simulate_profile_view()
            elif activity_type == ActivityType.SWIPE_RIGHT:
                return self._simulate_swipe_right()
            elif activity_type == ActivityType.SWIPE_LEFT:
                return self._simulate_swipe_left()
            elif activity_type == ActivityType.SUPER_LIKE:
                return self._simulate_super_like()
            elif activity_type == ActivityType.MESSAGE_SEND:
                return self._simulate_message_send(context)
            elif activity_type == ActivityType.MESSAGE_READ:
                return self._simulate_message_read()
            elif activity_type == ActivityType.PROFILE_EDIT:
                return self._simulate_profile_edit()
            elif activity_type == ActivityType.SETTINGS_CHECK:
                return self._simulate_settings_check()
            elif activity_type == ActivityType.PHOTO_ADD:
                return self._simulate_photo_add()
            else:
                logger.warning(f"Unknown activity type: {activity_type}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to execute activity {activity_type}: {e}")
            return False
    
    def _simulate_app_open(self) -> bool:
        """Simulate opening the app"""
        return self.automator.launch_tinder()
    
    def _simulate_profile_view(self) -> bool:
        """Simulate viewing a profile without swiping"""
        try:
            # Wait for card to load
            time.sleep(random.uniform(1, 3))
            
            # Simulate reading profile (scroll down, view photos)
            if self.automator.u2_device:
                # Scroll down to read bio
                self.automator.u2_device.swipe(540, 1200, 540, 800, duration=0.3)
                time.sleep(random.uniform(2, 5))
                
                # View additional photos
                for _ in range(random.randint(1, 3)):
                    self.automator.u2_device.swipe(800, 960, 200, 960, duration=0.3)
                    time.sleep(random.uniform(1, 2))
            
            return True
            
        except Exception as e:
            logger.error(f"Profile view simulation failed: {e}")
            return False
    
    def _simulate_swipe_right(self) -> bool:
        """Simulate swiping right (like)"""
        try:
            if self.automator.u2_device:
                # Natural swipe right gesture
                start_x = random.randint(200, 400)
                start_y = random.randint(800, 1200)
                end_x = random.randint(700, 900)
                end_y = start_y + random.randint(-50, 50)
                
                self.automator.u2_device.swipe(start_x, start_y, end_x, end_y, duration=0.5)
                
                # Wait for next card
                time.sleep(random.uniform(1, 3))
                return True
            
            return self.automator.swipe_right()
            
        except Exception as e:
            logger.error(f"Swipe right simulation failed: {e}")
            return False
    
    def _simulate_swipe_left(self) -> bool:
        """Simulate swiping left (pass)"""
        try:
            if self.automator.u2_device:
                # Natural swipe left gesture
                start_x = random.randint(600, 800)
                start_y = random.randint(800, 1200)
                end_x = random.randint(100, 300)
                end_y = start_y + random.randint(-50, 50)
                
                self.automator.u2_device.swipe(start_x, start_y, end_x, end_y, duration=0.5)
                
                # Wait for next card
                time.sleep(random.uniform(0.5, 2))
                return True
            
            return self.automator.swipe_left()
            
        except Exception as e:
            logger.error(f"Swipe left simulation failed: {e}")
            return False
    
    def _simulate_super_like(self) -> bool:
        """Simulate super like"""
        try:
            if self.automator.u2_device:
                # Swipe up for super like
                start_x = random.randint(400, 680)
                start_y = random.randint(1000, 1200)
                end_x = start_x + random.randint(-30, 30)
                end_y = random.randint(300, 500)
                
                self.automator.u2_device.swipe(start_x, start_y, end_x, end_y, duration=0.6)
                
                # Wait for animation
                time.sleep(random.uniform(2, 4))
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Super like simulation failed: {e}")
            return False
    
    def _simulate_message_send(self, context: Dict[str, any] = None) -> bool:
        """Simulate sending a message"""
        try:
            # Navigate to matches
            if not self.automator.tap_element("Messages"):
                return False
            
            time.sleep(2)
            
            # Select a match (would need more sophisticated logic)
            if self.automator.u2_device:
                # Tap first match
                self.automator.u2_device.click(540, 400)
                time.sleep(2)
                
                # Type message
                messages = [
                    "Hey! How's your day going?",
                    "Love your photos! That hiking pic is amazing",
                    "Coffee lover too! What's your favorite spot?",
                    "Your bio made me smile 😊",
                    "Adventure buddy found? 🗺️"
                ]
                
                message = random.choice(messages)
                if self.automator.u2_device(resourceId="com.tinder:id/chatTextInput").exists:
                    self.automator.u2_device(resourceId="com.tinder:id/chatTextInput").send_keys(message)
                    time.sleep(1)
                    self.automator.u2_device(resourceId="com.tinder:id/chatSendButton").click()
                    
                # Go back to main screen
                self.automator.u2_device.press("back")
                self.automator.u2_device.press("back")
                
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Message send simulation failed: {e}")
            return False
    
    def _simulate_message_read(self) -> bool:
        """Simulate reading messages"""
        try:
            # Navigate to messages
            if not self.automator.tap_element("Messages"):
                return False
            
            time.sleep(2)
            
            # Read messages for a bit
            time.sleep(random.uniform(5, 15))
            
            # Go back
            if self.automator.u2_device:
                self.automator.u2_device.press("back")
            
            return True
            
        except Exception as e:
            logger.error(f"Message read simulation failed: {e}")
            return False
    
    def _simulate_profile_edit(self) -> bool:
        """Simulate editing profile"""
        try:
            # Navigate to profile
            if not self.automator.tap_element("Profile"):
                return False
            
            time.sleep(2)
            
            # View/edit for a moment
            time.sleep(random.uniform(5, 10))
            
            # Go back
            if self.automator.u2_device:
                self.automator.u2_device.press("back")
            
            return True
            
        except Exception as e:
            logger.error(f"Profile edit simulation failed: {e}")
            return False
    
    def _simulate_settings_check(self) -> bool:
        """Simulate checking settings"""
        try:
            # Navigate to settings
            if not self.automator.tap_element("Settings"):
                return False
            
            time.sleep(2)
            
            # Browse settings briefly
            time.sleep(random.uniform(3, 8))
            
            # Go back
            if self.automator.u2_device:
                self.automator.u2_device.press("back")
            
            return True
            
        except Exception as e:
            logger.error(f"Settings check simulation failed: {e}")
            return False
    
    def _simulate_photo_add(self) -> bool:
        """Simulate adding/viewing photos"""
        try:
            # This would be complex - skip for now
            logger.info("Photo add simulation - complex implementation needed")
            return True
            
        except Exception as e:
            logger.error(f"Photo add simulation failed: {e}")
            return False

class AccountWarmingManager:
    """Manages account warming schedules and execution"""
    
    def __init__(self, redis_client: redis.Redis = None):
        self.redis_client = redis_client or redis.Redis(host='localhost', port=6379, db=0)
        self.emulator_manager = get_emulator_manager()
        self.anti_detection = get_anti_detection_system()
        self.warming_states: Dict[str, AccountWarmingState] = {}
        self.activity_logs: List[ActivityLog] = []
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.is_running = False
        self.scheduler_thread = None
        
    def add_account_for_warming(self, account_result: AccountCreationResult, device_id: str):
        """Add newly created account to warming system"""
        account_id = account_result.account_id
        
        # Create initial warming state
        warming_state = AccountWarmingState(
            account_id=account_id,
            device_id=device_id,
            status=AccountStatus.CREATED,
            creation_date=account_result.creation_time or datetime.now(),
            last_activity=datetime.now(),
            total_sessions=0,
            total_swipes=0,
            total_matches=0,
            total_messages=0,
            warming_schedule=WarmingSchedules.day_1_schedule(),
            next_session_time=self._calculate_next_session_time(WarmingSchedules.day_1_schedule()),
            consecutive_errors=0,
            is_suspended=False
        )
        
        self.warming_states[account_id] = warming_state
        self._save_warming_state(warming_state)
        
        logger.info(f"Added account {account_id} to warming system")
    
    def _calculate_next_session_time(self, schedule: WarmingSchedule) -> datetime:
        """Calculate next session time based on schedule"""
        min_wait = schedule.break_between_sessions_min
        max_wait = schedule.break_between_sessions_max
        
        wait_minutes = random.randint(min_wait, max_wait)
        return datetime.now() + timedelta(minutes=wait_minutes)
    
    def execute_warming_session(self, account_id: str) -> bool:
        """Execute warming session for account"""
        if account_id not in self.warming_states:
            logger.error(f"Account {account_id} not found in warming states")
            return False
        
        state = self.warming_states[account_id]
        
        # Check if account should continue session
        if not self.anti_detection.should_continue_session(state.device_id):
            logger.info(f"Anti-detection system suggests break for {account_id}")
            return True
        
        try:
            logger.info(f"Starting warming session for account {account_id}")
            
            # Initialize activity simulator
            simulator = TinderActivitySimulator(state.device_id)
            
            # Execute session activities
            session_start = datetime.now()
            successful_activities = 0
            
            for i in range(state.warming_schedule.activities_per_session):
                # Select random activity
                activity_type = random.choice(state.warming_schedule.activity_types)
                
                # Execute activity
                success = simulator.execute_activity(activity_type)
                
                # Log activity
                log_entry = ActivityLog(
                    account_id=account_id,
                    timestamp=datetime.now(),
                    activity_type=activity_type,
                    details={'session_activity': i + 1},
                    success=success
                )
                self.activity_logs.append(log_entry)
                
                if success:
                    successful_activities += 1
                    
                    # Update counters
                    if activity_type in [ActivityType.SWIPE_LEFT, ActivityType.SWIPE_RIGHT]:
                        state.total_swipes += 1
                else:
                    state.consecutive_errors += 1
                    if state.consecutive_errors >= 5:
                        logger.warning(f"Multiple errors for account {account_id}, ending session")
                        break
                
                # Check session duration
                session_duration = (datetime.now() - session_start).total_seconds() / 60
                if session_duration >= state.warming_schedule.session_duration_max:
                    break
            
            # Update state
            state.last_activity = datetime.now()
            state.total_sessions += 1
            state.next_session_time = self._calculate_next_session_time(state.warming_schedule)
            
            # Check for status progression
            self._check_status_progression(state)
            
            # Save state
            self._save_warming_state(state)
            
            success_rate = successful_activities / state.warming_schedule.activities_per_session
            logger.info(f"Warming session completed for {account_id}: {success_rate:.1%} success rate")
            
            return success_rate > 0.7  # Consider successful if >70% activities succeeded
            
        except Exception as e:
            logger.error(f"Warming session failed for account {account_id}: {e}")
            state.consecutive_errors += 1
            self._save_warming_state(state)
            return False
    
    def _check_status_progression(self, state: AccountWarmingState):
        """Check if account should progress to next warming phase"""
        account_age = datetime.now() - state.creation_date
        
        if state.status == AccountStatus.CREATED:
            # Move to day 1 warming immediately
            state.status = AccountStatus.WARMING_DAY_1
            state.warming_schedule = WarmingSchedules.day_1_schedule()
            
        elif state.status == AccountStatus.WARMING_DAY_1 and account_age.days >= 1:
            # Move to week 1 warming
            state.status = AccountStatus.WARMING_WEEK_1
            state.warming_schedule = WarmingSchedules.week_1_schedule()
            logger.info(f"Account {state.account_id} progressed to week 1 warming")
            
        elif state.status == AccountStatus.WARMING_WEEK_1 and account_age.days >= 7:
            # Move to week 2 warming
            state.status = AccountStatus.WARMING_WEEK_2
            state.warming_schedule = WarmingSchedules.week_2_schedule()
            logger.info(f"Account {state.account_id} progressed to week 2 warming")
            
        elif state.status == AccountStatus.WARMING_WEEK_2 and account_age.days >= 14:
            # Move to active status
            state.status = AccountStatus.ACTIVE
            state.warming_schedule = WarmingSchedules.active_schedule()
            logger.info(f"Account {state.account_id} is now fully warmed and active")
    
    def _save_warming_state(self, state: AccountWarmingState):
        """Save warming state to Redis"""
        try:
            key = f"warming_state:{state.account_id}"
            data = asdict(state)
            # Convert datetime objects to ISO strings for JSON serialization
            data['creation_date'] = state.creation_date.isoformat()
            data['last_activity'] = state.last_activity.isoformat()
            data['next_session_time'] = state.next_session_time.isoformat()
            data['status'] = state.status.value
            data['warming_schedule'] = asdict(state.warming_schedule)
            data['warming_schedule']['status'] = state.warming_schedule.status.value
            data['warming_schedule']['activity_types'] = [at.value for at in state.warming_schedule.activity_types]
            
            self.redis_client.set(key, json.dumps(data), ex=86400 * 30)  # 30 day expiry
            
        except Exception as e:
            logger.error(f"Failed to save warming state for {state.account_id}: {e}")
    
    def _load_warming_state(self, account_id: str) -> Optional[AccountWarmingState]:
        """Load warming state from Redis"""
        try:
            key = f"warming_state:{account_id}"
            data = self.redis_client.get(key)
            
            if not data:
                return None
            
            data = json.loads(data)
            
            # Convert back from JSON
            data['creation_date'] = datetime.fromisoformat(data['creation_date'])
            data['last_activity'] = datetime.fromisoformat(data['last_activity'])
            data['next_session_time'] = datetime.fromisoformat(data['next_session_time'])
            data['status'] = AccountStatus(data['status'])
            
            schedule_data = data['warming_schedule']
            schedule_data['status'] = AccountStatus(schedule_data['status'])
            schedule_data['activity_types'] = [ActivityType(at) for at in schedule_data['activity_types']]
            data['warming_schedule'] = WarmingSchedule(**schedule_data)
            
            return AccountWarmingState(**data)
            
        except Exception as e:
            logger.error(f"Failed to load warming state for {account_id}: {e}")
            return None
    
    def start_warming_scheduler(self):
        """Start background warming scheduler"""
        if self.is_running:
            logger.warning("Warming scheduler already running")
            return
        
        self.is_running = True
        
        # Schedule regular checks
        schedule.every(5).minutes.do(self._check_pending_sessions)
        schedule.every(1).hours.do(self._cleanup_old_logs)
        schedule.every(6).hours.do(self._check_account_health)
        
        # Start scheduler thread
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("Warming scheduler started")
    
    def stop_warming_scheduler(self):
        """Stop warming scheduler"""
        self.is_running = False
        schedule.clear()
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=10)
        
        logger.info("Warming scheduler stopped")
    
    def _run_scheduler(self):
        """Run scheduler loop"""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
    
    def _check_pending_sessions(self):
        """Check for accounts that need warming sessions"""
        current_time = datetime.now()
        
        for account_id, state in self.warming_states.items():
            if current_time >= state.next_session_time and not state.is_suspended:
                # Submit session to thread pool
                self.executor.submit(self.execute_warming_session, account_id)
    
    def _cleanup_old_logs(self):
        """Clean up old activity logs"""
        cutoff = datetime.now() - timedelta(hours=24)
        self.activity_logs = [log for log in self.activity_logs if log.timestamp > cutoff]
    
    def _check_account_health(self):
        """Check account health and detect issues"""
        for account_id, state in self.warming_states.items():
            # Check for excessive errors
            if state.consecutive_errors >= 10:
                logger.warning(f"Account {account_id} has excessive errors, suspending")
                state.is_suspended = True
                self._save_warming_state(state)
    
    def get_warming_statistics(self) -> Dict[str, any]:
        """Get warming system statistics"""
        stats = {
            'total_accounts': len(self.warming_states),
            'status_breakdown': {},
            'recent_activity': len([log for log in self.activity_logs 
                                  if log.timestamp > datetime.now() - timedelta(hours=1)]),
            'success_rate': 0.0
        }
        
        # Status breakdown
        for status in AccountStatus:
            count = sum(1 for state in self.warming_states.values() if state.status == status)
            stats['status_breakdown'][status.value] = count
        
        # Success rate
        recent_logs = [log for log in self.activity_logs 
                      if log.timestamp > datetime.now() - timedelta(hours=24)]
        if recent_logs:
            successful = sum(1 for log in recent_logs if log.success)
            stats['success_rate'] = successful / len(recent_logs)
        
        return stats

# Global warming manager
_warming_manager = None

def get_warming_manager() -> AccountWarmingManager:
    """Get global warming manager instance"""
    global _warming_manager
    if _warming_manager is None:
        _warming_manager = AccountWarmingManager()
    return _warming_manager

if __name__ == "__main__":
    # Test warming system
    manager = AccountWarmingManager()
    
    # Test schedule generation
    schedules = [
        WarmingSchedules.day_1_schedule(),
        WarmingSchedules.week_1_schedule(),
        WarmingSchedules.week_2_schedule(),
        WarmingSchedules.active_schedule()
    ]
    
    for schedule in schedules:
        print(f"Schedule {schedule.status.value}:")
        print(f"  Daily sessions: {schedule.daily_sessions}")
        print(f"  Activities per session: {schedule.activities_per_session}")
        print(f"  Swipe ratio right: {schedule.swipe_ratio_right}")
        print(f"  Super like frequency: {schedule.super_like_frequency}")
        print()
    
    # Test statistics
    stats = manager.get_warming_statistics()
    print(f"Warming statistics: {json.dumps(stats, indent=2)}")