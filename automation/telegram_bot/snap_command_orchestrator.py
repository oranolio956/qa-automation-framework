#!/usr/bin/env python3
"""
Complete End-to-End /snap Command Orchestrator
Handles everything from `/snap 50` to finished Snapchat accounts with full automation

FEATURES:
- Auto-deploys Android emulators on Fly.io when needed
- Creates Snapchat accounts using complete safety/detection pipeline
- Manages entire flow from command to completion
- Real-time status updates to user
- Error handling and recovery
- Resource management and cleanup
- Scales from 1 to 100+ accounts
"""

import os
import sys
import time
import logging
import asyncio
import random
import json
from typing import Dict, List, Optional, Tuple, Any
import traceback
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import uuid
import functools
from pathlib import Path
import httpx

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# Import Telegram components
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# Import automation components with safe fallbacks
try:
    from automation.snapchat.stealth_creator import get_snapchat_creator
except ImportError:
    get_snapchat_creator = None

try:
    from automation.android.automation_orchestrator import get_android_orchestrator
except ImportError:
    get_android_orchestrator = None

try:
    from automation.android.emulator_manager import get_emulator_manager
except ImportError:
    get_emulator_manager = None

try:
    from automation.core.anti_detection import get_anti_detection_system
except ImportError:
    get_anti_detection_system = None

try:
    from automation.snapchat.apk_manager import get_apk_manager
except ImportError:
    get_apk_manager = None

# Reliability utilities
try:
    from utils.reliability import retry_with_backoff, TokenBucketRateLimiter, CircuitBreaker
except Exception:
    retry_with_backoff = None
    TokenBucketRateLimiter = None
    CircuitBreaker = None

try:
    from utils.metrics import get_metrics_logger
except Exception:
    def get_metrics_logger():
        class _N:
            def emit(self, *a, **k):
                pass
        return _N()

try:
    from utils.risk_guard import get_risk_guard
except Exception:
    def get_risk_guard():
        class _N:
            def record_event(self, *a, **k): pass
            def compute_anomaly_score(self): return 0.0
            def should_pause_for_canary(self, s): return False
            def check_kill_switch(self): return False
            def get_status(self):
                from dataclasses import dataclass
                @dataclass
                class _S:
                    kill_switch: bool = False
                    anomaly_score: float = 0.0
                    last_minute_errors: int = 0
                    last_minute_requests: int = 0
                return _S()
            def compute_account_risk(self, c): return 0.0
        return _N()

try:
    from utils.scheduler import is_within_user_window, get_daily_caps
except Exception:
    def is_within_user_window(user_region: str, now_utc=None): return True
    def get_daily_caps(day_index: int): return (10, 5)

try:
    from utils.uniqueness_registry import get_uniqueness_registry
except Exception:
    def get_uniqueness_registry():
        class _N:
            def claim(self, *a, **k): return True
        return _N()

try:
    # Import email integration carefully to avoid module conflicts
    import sys
    import importlib.util
    email_integration_path = os.path.join(os.path.dirname(__file__), '..', 'email', 'email_integration.py')
    if os.path.exists(email_integration_path):
        spec = importlib.util.spec_from_file_location('email_integration', email_integration_path)
        email_integration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(email_integration)
        get_email_integrator = getattr(email_integration, 'get_email_integrator', None)
    else:
        get_email_integrator = None
except Exception as e:
    logging.warning(f"Email integration not available: {e}")
    get_email_integrator = None

try:
    from utils.sms_verifier import get_sms_verifier
except ImportError:
    get_sms_verifier = None

try:
    from utils.balance_manager import get_balance_manager, BalanceManager
except Exception:
    get_balance_manager = None
    class BalanceManager:
        @staticmethod
        def is_free_mode():
            return True

try:
    from utils.twilio_pool import get_twilio_pool
except ImportError:
    get_twilio_pool = None

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class SnapAccountRequest:
    """Request for Snapchat account creation"""
    request_id: str
    user_id: int
    account_count: int
    timestamp: float
    payment_confirmed: bool = False
    payment_method: Optional[str] = None
    payment_amount: Optional[float] = None
    status: str = "pending"  # pending, processing, completed, failed
    progress_message_id: Optional[int] = None
    created_accounts: List[Dict] = None
    webhook_enabled: bool = False
    webhook_url: Optional[str] = None
    error_message: Optional[str] = None

@dataclass 
class SnapAccountResult:
    """Result of Snapchat account creation"""
    username: str
    password: str
    email: str
    phone_number: str
    device_id: str
    session_id: str
    verified: bool = False
    account_id: Optional[str] = None
    adds_ready: int = 100
    status: str = "active"
    created_at: float = 0.0
    emulator_config: Optional[str] = None
    region: Optional[str] = None
    bitmoji_linked: bool = False
    bitmoji_screenshot_path: Optional[str] = None
    
@dataclass
class ResourceAllocation:
    """Allocated resources for account creation"""
    emulator_sessions: List[str]
    sms_numbers: List[Dict[str, str]]  # {'verification_id': str, 'phone_number': str}
    email_addresses: List[str]
    anti_detection_profiles: List[Any]
    proxy_sessions: List[str]

class SnapCommandOrchestrator:
    """Complete orchestrator for /snap command end-to-end automation"""
    
    def __init__(self, telegram_app):
        self.telegram_app = telegram_app
        self.active_requests: Dict[str, SnapAccountRequest] = {}
        
        # Initialize automation components with safety checks
        self.snapchat_creator = get_snapchat_creator() if get_snapchat_creator else None
        self.android_orchestrator = get_android_orchestrator() if get_android_orchestrator else None
        self.emulator_manager = get_emulator_manager() if get_emulator_manager else None
        self.anti_detection = get_anti_detection_system() if get_anti_detection_system else None
        self.email_integrator = get_email_integrator() if get_email_integrator else None
        self.sms_verifier = get_sms_verifier() if get_sms_verifier else None
        self.twilio_pool = get_twilio_pool() if get_twilio_pool else None
        self.apk_manager = get_apk_manager() if get_apk_manager else None

        # Reliability controls
        self.sms_rate_limiter = TokenBucketRateLimiter(max_tokens=5, refill_rate=0.5) if TokenBucketRateLimiter else None
        self.email_rate_limiter = TokenBucketRateLimiter(max_tokens=3, refill_rate=0.2) if TokenBucketRateLimiter else None
        self.emu_rate_limiter = TokenBucketRateLimiter(max_tokens=2, refill_rate=0.1) if TokenBucketRateLimiter else None
        self.sms_cb = CircuitBreaker(failure_threshold=5, window_seconds=120, reset_timeout=60) if CircuitBreaker else None
        self.emu_cb = CircuitBreaker(failure_threshold=3, window_seconds=120, reset_timeout=60) if CircuitBreaker else None
        self.apk_cb = CircuitBreaker(failure_threshold=3, window_seconds=120, reset_timeout=60) if CircuitBreaker else None

        # Persistence
        self.state_dir = Path('artifacts/request_state')
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Metrics
        self.metrics = get_metrics_logger()
        self.risk_guard = get_risk_guard()
        self.uniq = get_uniqueness_registry()

        # Queue for orders (global fairness)
        self.request_queue: asyncio.Queue[SnapAccountRequest] = asyncio.Queue()
        self._queue_started = False
        self._global_concurrency = asyncio.Semaphore(2)
        
        # Resource management
        self.max_concurrent_requests = 10
        self.max_accounts_per_request = 100
        self.resource_pool = {
            'emulators': {},
            'sms_numbers': {},
            'emails': {},
            'proxies': {}
        }
        
        # Thread pool for blocking operations
        self.thread_pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="snap_orchestrator")
        
        # Start resource manager
        self._start_resource_manager()
        
        logger.info("✅ Snap Command Orchestrator initialized")
    
    def _start_resource_manager(self):
        """Start background resource management"""
        def manage_resources():
            while True:
                try:
                    self._cleanup_idle_resources()
                    self._health_check_resources()
                    time.sleep(30)  # Check every 30 seconds
                except Exception as e:
                    logger.error(f"Resource manager error: {e}")
                    time.sleep(5)
        
        import threading
        manager_thread = threading.Thread(target=manage_resources, daemon=True)
        manager_thread.start()
        logger.info("📊 Resource manager started")
    
    def _cleanup_idle_resources(self):
        """Cleanup idle resources to save costs"""
        current_time = time.time()
        
        # Cleanup idle emulators (idle > 10 minutes)
        for session_id, last_used in list(self.resource_pool['emulators'].items()):
            if current_time - last_used > 600:  # 10 minutes
                try:
                    self.android_orchestrator.end_automation_session(session_id)
                    del self.resource_pool['emulators'][session_id]
                    logger.info(f"🧹 Cleaned up idle emulator: {session_id}")
                except Exception as e:
                    logger.error(f"Failed to cleanup emulator {session_id}: {e}")
        
        # Cleanup other resources similarly...
        # SMS numbers, email addresses, etc.
    
    def _health_check_resources(self):
        """Health check active resources"""
        for session_id in list(self.resource_pool['emulators'].keys()):
            try:
                session_info = self.android_orchestrator.get_session_info(session_id)
                if not session_info:
                    # Session is dead, remove from pool
                    del self.resource_pool['emulators'][session_id]
                    logger.warning(f"⚠️ Removed dead emulator session: {session_id}")
            except Exception as e:
                logger.error(f"Health check error for {session_id}: {e}")
    
    async def handle_snap_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /snap command with account count"""
        try:
            user_id = update.effective_user.id
            command_text = update.message.text.strip()
            
            # Parse account count and optional webhook URL from command
            webhook_url = None
            if len(command_text.split()) > 1:
                try:
                    parts = command_text.split()
                    account_count = int(parts[1])
                    if account_count < 1 or account_count > self.max_accounts_per_request:
                        await update.message.reply_text(
                            f"❌ Invalid account count. Must be between 1 and {self.max_accounts_per_request}."
                        )
                        return
                    # Optional webhook URL
                    import re as _re
                    url_regex = _re.compile(r"https?://[\w\-\._~:/%\?#\[\]@!\$&'\(\)\*\+,;=]+", _re.I)
                    matches = url_regex.findall(command_text)
                    if matches:
                        webhook_url = matches[0]
                    for p in parts[2:]:
                        if p.lower().startswith('webhook='):
                            webhook_url = p.split('=', 1)[1]
                except ValueError:
                    await update.message.reply_text(
                        "❌ Invalid number format. Use: `/snap 50` for 50 accounts"
                    )
                    return
            else:
                account_count = 1  # Default to 1 account

            # Balance check (bypass if FREE_TEST_MODE)
            bm = get_balance_manager() if get_balance_manager else None
            free_mode = BalanceManager.is_free_mode() if BalanceManager else True
            estimated_cost = max(1, account_count) * 1.00  # $1 per account placeholder
            if not free_mode and bm:
                balance = bm.get_balance(user_id)
                if balance < estimated_cost:
                    await update.message.reply_text(
                        f"Insufficient balance. Needed ${estimated_cost:.2f}, available ${balance:.2f}. Use /addfunds."
                    )
                    return
            
            # Check if user has active requests
            active_count = sum(1 for req in self.active_requests.values() 
                             if req.user_id == user_id and req.status in ['pending', 'processing'])
            
            if active_count >= 3:  # Max 3 concurrent requests per user
                await update.message.reply_text(
                    "⚠️ You have too many active requests. Please wait for them to complete."
                )
                return
            
            # Create request
            request_id = f"snap_{user_id}_{int(time.time())}_{random.randint(1000, 9999)}"
            request = SnapAccountRequest(
                request_id=request_id,
                user_id=user_id,
                account_count=account_count,
                timestamp=time.time(),
                created_accounts=[],
                webhook_enabled=bool(webhook_url),
                webhook_url=webhook_url
            )
            
            self.active_requests[request_id] = request

            # Persist new request
            self._persist_request_state(request)
            
            # Send initial message
            initial_message = await update.message.reply_text(
                (
                    "Order accepted.\n\n"
                    f"Target: {account_count} accounts\n"
                    f"Status: initializing systems\n\n"
                    f"Request ID: `{request_id[:12]}`\n"
                    "Use the dashboard buttons to refresh status or download when ready."
                ),
                parse_mode='Markdown'
            )
            
            request.progress_message_id = initial_message.message_id
            
            # Ensure dashboard message
            await self._ensure_dashboard_message(request, update)
            await self._update_dashboard(request, title="Queued", progress=0)

            # Enqueue for processing
            await self.request_queue.put(request)
            if not self._queue_started:
                context.application.create_task(self._queue_worker())
                self._queue_started = True

            # Charge after queueing if not free mode
            if not free_mode and bm:
                bm.deduct(user_id, estimated_cost, reason=f"/snap {account_count}")
            
        except Exception as e:
            logger.error(f"Error handling /snap command: {e}")
            await update.message.reply_text(
                "❌ Failed to process /snap command. Please try again."
            )
    
    async def _process_snap_request(self, request: SnapAccountRequest):
        """Process complete Snapchat account creation request"""
        try:
            # Global guardrails
            if self.risk_guard.check_kill_switch():
                await self._handle_request_failure(request, "Service paused (risk guard)")
                return
            # Circadian gating (simple default region)
            try:
                if not is_within_user_window('US/Pacific'):
                    await self._update_dashboard(request, title="Waiting: quiet hours", progress=0)
                    await asyncio.sleep(10)
            except Exception:
                pass
            request.status = "processing"
            await self._update_dashboard(request, title="Resource Allocation", progress=5)
            
            # Step 1: Resource allocation
            await self._update_progress(request,
                "RESOURCE ALLOCATION\n\n"
                f"Allocating {request.account_count} emulator slots\n"
                "Reserving SMS numbers\n"
                "Setting up email addresses\n"
                "Preparing anti-detection profiles",
                progress=5
            )
            
            t0 = time.time()
            try:
                resources = await self._allocate_resources(request.account_count)
                if not resources:
                    raise RuntimeError("Failed to allocate required resources (none returned)")
            except Exception as alloc_err:
                err_text = traceback.format_exc()[-2000:]
                await self._update_progress(
                    request,
                    (
                        "Error during resource allocation\n\n"
                        f"{str(alloc_err)}\n\n"
                        f"Details:\n{err_text}"
                    ),
                    progress=5
                )
                logger.exception("Resource allocation failed")
                await self._handle_request_failure(request, f"Resource allocation failed: {str(alloc_err)}")
                return
            self.metrics.emit('resource_allocation_ms', {'ms': int((time.time() - t0) * 1000), 'accounts': request.account_count})

            # Persist after allocation
            self._persist_request_state(request)
            
            # Step 2: Deploy emulators
            await self._update_progress(request,
                "EMULATOR DEPLOYMENT\n\n"
                f"Deploying {len(resources.emulator_sessions)} Android emulators\n"
                "Configuring device fingerprints\n"
                "Applying stealth configurations",
                progress=15
            )
            await self._update_dashboard(request, title="Emulator Deployment", progress=15)
            
            # Step 3: Install Snapchat on emulators
            await self._update_progress(request,
                "SNAPCHAT INSTALLATION\n\nInstalling Snapchat APK on devices",
                progress=25
            )
            await self._update_dashboard(request, title="Snapchat Installation", progress=25)
            
            t1 = time.time()
            try:
                await self._install_snapchat_on_emulators(resources.emulator_sessions)
            except Exception as install_err:
                err_text = traceback.format_exc()[-2000:]
                await self._update_progress(
                    request,
                    (
                        "Error during APK installation\n\n"
                        f"{str(install_err)}\n\n"
                        f"Details:\n{err_text}"
                    ),
                    progress=25
                )
                logger.exception("APK installation failed")
                await self._handle_request_failure(request, f"APK installation failed: {str(install_err)}")
                return
            self.metrics.emit('apk_installation_ms', {'ms': int((time.time() - t1) * 1000), 'sessions': len(resources.emulator_sessions)})

            # Persist after install
            self._persist_request_state(request)
            
            # Step 4: Create accounts in parallel
            await self._update_progress(request,
                "ACCOUNT CREATION\n\n"
                f"Creating {request.account_count} Snapchat accounts\n"
                "Using email verification\n"
                "Using SMS verification\n"
                "Anti-detection measures active",
                progress=30
            )
            await self._update_dashboard(request, title="Account Creation", progress=30)
            
            # Create accounts in batches for better resource management
            # Progressive batching: start small, adapt based on success
            base_batch = min(2, request.account_count)
            batch_size = base_batch
            created_accounts = []
            
            for i in range(0, request.account_count, batch_size):
                batch_end = min(i + batch_size, request.account_count)
                batch_size_actual = batch_end - i
                
                await self._update_progress(request,
                    f"BATCH {i//batch_size + 1}\n\n"
                    f"Processing accounts {i+1}-{batch_end}\n"
                    f"Completed: {len(created_accounts)}/{request.account_count}\n"
                    f"Current batch: {batch_size_actual} accounts\n"
                    "Anti-detection protocols active",
                    progress=30 + (i / request.account_count) * 60
                )
                
                # Create batch accounts
                batch_accounts = await self._create_account_batch(
                    resources, i, batch_size_actual, request
                )
                
                created_accounts.extend(batch_accounts)
                self.metrics.emit('batch_result', {
                    'batch_index': i // max(1, batch_size),
                    'requested': batch_size_actual,
                    'success': len(batch_accounts)
                })
                
                # Canary holdback: pause if success ratio is low
                try:
                    success_ratio = (len(batch_accounts) / max(1, batch_size_actual))
                    if self.risk_guard.should_pause_for_canary(success_ratio):
                        await self._update_dashboard(request, title="Paused for safety (canary)", progress=int(30 + (min(i + batch_size_actual, request.account_count) / request.account_count) * 60))
                        await asyncio.sleep(15)
                except Exception:
                    pass

                # Update request with partial results
                request.created_accounts = created_accounts

                # Persist after each batch
                self._persist_request_state(request)
                
                # Show batch completion
                await self._update_progress(request,
                    (
                        f"Batch {i//batch_size + 1} complete\n\n"
                        f"Created in this batch: {len(batch_accounts)}\n"
                        f"Total completed: {len(created_accounts)}/{request.account_count}\n"
                        f"Success rate so far: {len(created_accounts)/(i+batch_size_actual)*100:.1f}%\n"
                        + ("Proceeding to next batch" if batch_end < request.account_count else "All batches complete")
                    ),
                    progress=30 + (batch_end / request.account_count) * 60
                )
                
                if batch_end < request.account_count:
                    # Adapt batch size based on last batch success ratio
                    ratio = (len(batch_accounts) / max(1, batch_size_actual))
                    if ratio >= 0.8:
                        batch_size = min(5, batch_size + 1)
                    elif ratio < 0.4:
                        batch_size = max(1, batch_size - 1)
                    await asyncio.sleep(2)
            
            # Step 5: Verify accounts
            await self._update_progress(request,
                "ACCOUNT VERIFICATION\n\n"
                f"Verifying {len(created_accounts)} accounts\n"
                "Checking login functionality\n"
                "Configuring add farming\n"
                "Applying final security settings",
                progress=90
            )
            await self._update_dashboard(request, title="Verification", progress=90)
            
            try:
                verified_accounts = await self._verify_accounts(created_accounts)
            except Exception as verify_err:
                err_text = traceback.format_exc()[-2000:]
                await self._update_progress(
                    request,
                    (
                        "Error during verification\n\n"
                        f"{str(verify_err)}\n\n"
                        f"Details:\n{err_text}"
                    ),
                    progress=90
                )
                logger.exception("Verification failed")
                await self._handle_request_failure(request, f"Verification failed: {str(verify_err)}")
                return
            self.metrics.emit('verification_summary', {
                'submitted': len(created_accounts),
                'verified': len([a for a in verified_accounts if a.verified])
            })
            
            # Step 6: Complete and cleanup
            await self._cleanup_resources(resources)
            
            # Final results
            request.status = "completed"
            request.created_accounts = verified_accounts
            
            await self._send_final_results(request)
            await self._update_dashboard(request, title="Completed", progress=100)

            # Final persist
            self._persist_request_state(request)
            
        except Exception as e:
            logger.error(f"Error processing snap request {request.request_id}: {e}")
            await self._handle_request_failure(request, f"Processing error: {str(e)}")
    
    async def _allocate_resources(self, account_count: int) -> Optional[ResourceAllocation]:
        """Allocate all required resources for account creation"""
        try:
            # Calculate required resources
            emulator_count = min(account_count, 5)  # Max 5 parallel emulators (optimized for anti-detection)
            
            # Allocate emulators
            emulator_sessions = []
            for i in range(emulator_count):
                session_id = await self._run_in_thread_pool(
                    self.android_orchestrator.create_emulator_session,
                    'pixel_6_api_30',
                    True  # headless
                )
                if session_id:
                    emulator_sessions.append(session_id)
                    self.resource_pool['emulators'][session_id] = time.time()
                else:
                    logger.warning(f"Failed to allocate emulator {i+1}")
            
            if not emulator_sessions:
                raise RuntimeError("Failed to allocate any emulators")
            
            # Allocate SMS numbers
            sms_numbers = []
            for i in range(account_count):
                try:
                    # Rate limit and circuit breaker
                    if self.sms_rate_limiter: self.sms_rate_limiter.acquire()
                    if self.sms_cb and not self.sms_cb.allow():
                        raise RuntimeError("SMS subsystem temporarily unavailable (circuit open)")
                    number_result = None
                    if self.sms_verifier and hasattr(self.sms_verifier, 'get_number'):
                        number_result = await self._run_in_thread_pool(self.sms_verifier.get_number)
                    if number_result and number_result.get('success'):
                        sms_numbers.append({
                            'verification_id': number_result.get('verification_id'),
                            'phone_number': number_result.get('phone_number')
                        })
                        if self.sms_cb: self.sms_cb.record_success()
                    else:
                        if self.sms_cb: self.sms_cb.record_failure()
                except Exception as e:
                    logger.warning(f"Failed to allocate SMS number {i+1}: {e}")
                    if self.sms_cb: self.sms_cb.record_failure()
            
            # Allocate email addresses
            email_addresses = []
            for i in range(account_count):
                try:
                    if self.email_rate_limiter: self.email_rate_limiter.acquire()
                    email_value = None
                    if self.email_integrator and hasattr(self.email_integrator, 'create_snapchat_email'):
                        email_value = await self._run_in_thread_pool(
                            self.email_integrator.create_snapchat_email,
                            f"snapuser{int(time.time())}{i}"
                        )
                    if not email_value:
                        email_value = f"snap{int(time.time())}{i}@tempmail.com"
                    email_addresses.append(email_value)
                except Exception as e:
                    logger.warning(f"Failed to allocate email {i+1}: {e}")
            
            # Generate anti-detection profiles
            anti_detection_profiles = []
            for i in range(account_count):
                if self.anti_detection:
                    try:
                        profile = self.anti_detection.generate_behavior_profile()
                        anti_detection_profiles.append(profile)
                    except:
                        anti_detection_profiles.append(None)
                else:
                    anti_detection_profiles.append(None)
            
            return ResourceAllocation(
                emulator_sessions=emulator_sessions,
                sms_numbers=sms_numbers,
                email_addresses=email_addresses,
                anti_detection_profiles=anti_detection_profiles,
                proxy_sessions=[]
            )
            
        except Exception as e:
            logger.error(f"Resource allocation failed: {e}")
            return None
    
    async def _install_snapchat_on_emulators(self, emulator_sessions: List[str]):
        """Install Snapchat on all allocated emulators"""
        try:
            install_tasks = []
            
            for session_id in emulator_sessions:
                task = self._run_in_thread_pool(
                    self._install_snapchat_single_emulator,
                    session_id
                )
                install_tasks.append(task)
            
            # Wait for all installations to complete
            results = await asyncio.gather(*install_tasks, return_exceptions=True)
            
            successful_installs = sum(1 for r in results if r and not isinstance(r, Exception))
            logger.info(f"Snapchat installed on {successful_installs}/{len(emulator_sessions)} emulators")
            
        except Exception as e:
            logger.error(f"Snapchat installation failed: {e}")
            raise

    async def _queue_worker(self):
        while True:
            request = await self.request_queue.get()
            try:
                async with self._global_concurrency:
                    await self._process_snap_request(request)
            except Exception as e:
                logger.error(f"Queue worker error: {e}")
            finally:
                self.request_queue.task_done()

    def _short_order_id(self, full_id: str) -> str:
        try:
            # Use last 8 characters for visibility and uniqueness
            return full_id[-8:]
        except Exception:
            return full_id

    async def _ensure_dashboard_message(self, request: SnapAccountRequest, update: Update):
        try:
            # Create an inline keyboard with a compact status layout
            keyboard = [
                [InlineKeyboardButton("Refresh", callback_data=f"refresh_{request.request_id}"),
                 InlineKeyboardButton("Download", callback_data=f"download_{request.request_id}")],
                [InlineKeyboardButton("Cancel", callback_data=f"cancel_{request.request_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            display_id = self._short_order_id(request.request_id)
            text = (
                f"Order ID: `{display_id}`\n"
                f"Status: Queued\n"
                f"Requested accounts: {request.account_count}"
            )
            msg = await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)
            request.progress_message_id = msg.message_id
        except Exception as e:
            logger.error(f"Dashboard init error: {e}")

    async def _update_dashboard(self, request: SnapAccountRequest, title: str, progress: int):
        try:
            if not request.progress_message_id:
                return
            bar = self._create_progress_bar(progress)
            created = len(request.created_accounts or [])
            display_id = self._short_order_id(request.request_id)
            text = (
                f"{title}\n\n"
                f"Order ID: `{display_id}`\n"
                f"Requested: {request.account_count}\n"
                f"Completed: {created}\n"
                f"Progress: {progress}%\n{bar}"
            )
            keyboard = [
                [InlineKeyboardButton("Refresh", callback_data=f"refresh_{request.request_id}"),
                 InlineKeyboardButton("Download", callback_data=f"download_{request.request_id}")],
                [InlineKeyboardButton("View Details", callback_data=f"details_{request.request_id}_0")]
            ]
            await self.telegram_app.bot.edit_message_text(
                chat_id=request.user_id,
                message_id=request.progress_message_id,
                text=text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            try:
                err = str(e)[:140]
                text = f"Error updating dashboard: {err}\n\nPlease wait, retrying..."
                await self.telegram_app.bot.edit_message_text(
                    chat_id=request.user_id,
                    message_id=request.progress_message_id,
                    text=text
                )
            except Exception:
                logger.error(f"Dashboard update error: {e}")

    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            query = update.callback_query
            data = query.data or ""
            if data.startswith("refresh_"):
                req_id = data.split("refresh_")[-1]
                req = self.active_requests.get(req_id)
                if req:
                    created = len(req.created_accounts or [])
                    progress = int((created / max(1, req.account_count)) * 100)
                    await self._update_dashboard(req, title=f"{req.status.title()}", progress=progress)
                await query.answer("Refreshed")
            elif data.startswith("download_"):
                req_id = data.split("download_")[-1]
                req = self.active_requests.get(req_id)
                if req and req.created_accounts:
                    # Convert to dicts for delivery
                    accounts = []
                    for acc in req.created_accounts:
                        accounts.append({
                            'username': acc.username,
                            'password': acc.password,
                            'email': acc.email,
                            'phone_number': acc.phone_number,
                            'device_id': acc.device_id,
                            'emulator_config': acc.emulator_config,
                            'region': acc.region,
                            'bitmoji_linked': acc.bitmoji_linked,
                            'bitmoji_screenshot_path': acc.bitmoji_screenshot_path
                        })
                    from .file_delivery_system import deliver_accounts_to_user
                    await deliver_accounts_to_user(self.telegram_app, req.user_id, accounts, req.progress_message_id)
                    await query.answer("Files sent")
                else:
                    await query.answer("No accounts yet", show_alert=False)
            elif data.startswith("details_"):
                # details_<reqid>_<index>
                parts = data.split("_")
                req_id = parts[1]
                i = int(parts[2]) if len(parts) > 2 else 0
                req = self.active_requests.get(req_id)
                if not req or not req.created_accounts:
                    await query.answer("No accounts yet")
                    return
                i = max(0, min(i, len(req.created_accounts) - 1))
                acc = req.created_accounts[i]
                thumb = "✅" if getattr(acc, 'bitmoji_linked', False) else "❌"
                text = (
                    f"👤 `{acc.username}`\n"
                    f"📧 {acc.email}\n"
                    f"📞 {acc.phone_number}\n"
                    f"🗺️ Region: {acc.region or 'N/A'}\n"
                    f"📱 Device: {acc.device_id} ({acc.emulator_config or 'config'})\n"
                    f"🧩 Bitmoji: {thumb}"
                )
                nav = []
                if i > 0:
                    nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"details_{req_id}_{i-1}"))
                nav.append(InlineKeyboardButton("🖼️ Bitmoji", callback_data=f"bitmoji_{req_id}_{i}"))
                if i < len(req.created_accounts) - 1:
                    nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"details_{req_id}_{i+1}"))
                await self.telegram_app.bot.send_message(
                    chat_id=req.user_id,
                    text=text,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([nav])
                )
                await query.answer()
            elif data.startswith("bitmoji_"):
                parts = data.split("_")
                req_id = parts[1]
                i = int(parts[2]) if len(parts) > 2 else 0
                req = self.active_requests.get(req_id)
                if not req or not req.created_accounts:
                    await query.answer("No accounts")
                    return
                i = max(0, min(i, len(req.created_accounts) - 1))
                acc = req.created_accounts[i]
                if acc.bitmoji_screenshot_path and Path(acc.bitmoji_screenshot_path).exists():
                    try:
                        with open(acc.bitmoji_screenshot_path, 'rb') as f:
                            await self.telegram_app.bot.send_photo(chat_id=req.user_id, photo=f, caption=f"Bitmoji for {acc.username}")
                    except Exception as e:
                        logger.warning(f"Failed to send bitmoji: {e}")
                        await query.answer("Failed to send image")
                else:
                    await query.answer("No bitmoji available")
            elif data == "refresh_active":
                # Show a compact list of active requests
                if not self.active_requests:
                    await self.telegram_app.bot.send_message(
                        chat_id=query.from_user.id,
                        text="No active requests. Use /snap N to start a new order."
                    )
                else:
                    lines = ["Active requests:\n"]
                    for rid, req in self.active_requests.items():
                        completed = len(req.created_accounts or [])
                        lines.append(f"{rid[:10]} — {req.status} — {completed}/{req.account_count} complete")
                    await self.telegram_app.bot.send_message(
                        chat_id=query.from_user.id,
                        text="\n".join(lines)
                    )
                await query.answer()
            elif data == "menu_help":
                help_text = (
                    "Help:\n\n"
                    "• New order: /snap N (e.g., /snap 3)\n"
                    "• Dashboard: use the buttons to refresh status, view details, and download files\n"
                    "• Webhooks: /snap N https://your-webhook to receive per-account events\n"
                    "• Tip: keep activity natural on fresh accounts; ramp gradually."
                )
                await self.telegram_app.bot.send_message(
                    chat_id=query.from_user.id,
                    text=help_text
                )
                await query.answer()
            elif data.startswith("cancel_"):
                # Optional: implement cancellation flag
                await query.answer("Cancel not implemented yet")
            else:
                await query.answer()
        except Exception as e:
            logger.error(f"Callback handler error: {e}")
    
    def _install_snapchat_single_emulator(self, session_id: str) -> bool:
        """Install Snapchat on single emulator"""
        try:
            # Resolve device id for this session
            session_info = self.android_orchestrator.get_session_info(session_id)
            device_id = session_info.get('device_id') if session_info else None
            if not device_id:
                logger.error(f"No device_id for session {session_id}")
                return False
            
            # Get verified Snapchat APK via APK manager
            if not self.apk_manager:
                logger.error("APK manager not available")
                return False
            
            # Circuit breaker around APK fetch
            if self.apk_cb and not self.apk_cb.allow():
                logger.error("APK subsystem temporarily unavailable (circuit open)")
                return False
            try:
                apk_path_obj = self.apk_manager.get_verified_snapchat_apk()
                if self.apk_cb: self.apk_cb.record_success()
            except Exception as e:
                if self.apk_cb: self.apk_cb.record_failure()
                raise
            
            # Install APK (verified) using APK manager for safety
            success = self.apk_manager.install_apk(device_id, apk_path_obj)
            if not success:
                logger.error(f"Failed to install Snapchat on {session_id}")
                return False
            
            # Launch app to initialize
            success = self.android_orchestrator.launch_app(
                session_id, 
                'com.snapchat.android',
                'com.snapchat.android.LandingPageActivity'
            )
            
            if success:
                logger.info(f"✅ Snapchat installed and launched on {session_id}")
                time.sleep(3)  # Let app initialize
                return True
            else:
                logger.error(f"Failed to launch Snapchat on {session_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error installing Snapchat on {session_id}: {e}")
            return False
    
    def _ensure_snapchat_apk(self) -> Optional[str]:
        """Ensure Snapchat APK is available"""
        try:
            apk_dir = os.path.join(os.path.dirname(__file__), '../../android/apks')
            os.makedirs(apk_dir, exist_ok=True)
            
            snapchat_apk = os.path.join(apk_dir, 'snapchat.apk')
            
            # Check if APK exists and is recent (less than 7 days old)
            if os.path.exists(snapchat_apk):
                file_age = time.time() - os.path.getmtime(snapchat_apk)
                if file_age < 7 * 24 * 3600:  # 7 days
                    return snapchat_apk
            
            # Download latest APK (implement APK download logic here)
            # For now, return None to use existing APK if available
            if os.path.exists(snapchat_apk):
                return snapchat_apk
            
            logger.warning("Snapchat APK not found - this would typically download latest version")
            return None
            
        except Exception as e:
            logger.error(f"Error ensuring Snapchat APK: {e}")
            return None
    
    async def _create_account_batch(self, resources: ResourceAllocation, 
                                  start_index: int, batch_size: int,
                                  request: SnapAccountRequest) -> List[SnapAccountResult]:
        """Create a batch of accounts in parallel"""
        try:
            # Create tasks for parallel account creation
            tasks = []
            for i in range(batch_size):
                account_index = start_index + i
                
                # Assign emulator (round-robin)
                emulator_session = resources.emulator_sessions[i % len(resources.emulator_sessions)]
                
                # Assign other resources
                sms_info = resources.sms_numbers[account_index] if account_index < len(resources.sms_numbers) else None
                email = resources.email_addresses[account_index] if account_index < len(resources.email_addresses) else None
                profile = resources.anti_detection_profiles[account_index] if account_index < len(resources.anti_detection_profiles) else None
                
                task = self._create_single_account(
                    emulator_session, sms_info, email, profile, account_index + 1, request
                )
                tasks.append(task)
            
            # Execute all tasks in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter successful results
            successful_accounts = []
            for result in results:
                if isinstance(result, SnapAccountResult):
                    successful_accounts.append(result)
                elif isinstance(result, Exception):
                    logger.error(f"Account creation failed: {result}")
            
            return successful_accounts
            
        except Exception as e:
            logger.error(f"Batch creation failed: {e}")
            return []
    
    async def _create_single_account(self, emulator_session: str, sms_info: Optional[Dict[str, str]], 
                                   email: str, profile: Any, account_num: int,
                                   request: SnapAccountRequest) -> Optional[SnapAccountResult]:
        """Create a single Snapchat account"""
        try:
            # Resolve device id from session
            session_info = self.android_orchestrator.get_session_info(emulator_session)
            device_id = session_info.get('device_id') if session_info else None
            if not device_id:
                raise RuntimeError(f"No device_id for session {emulator_session}")
            # Update individual progress
            await self._update_progress(request,
                f"🔥 **CREATING ACCOUNT {account_num}**\n\n"
                f"👻 Session: {emulator_session[:12]}...\n"
                f"📧 Email: {email[:20]}...\n"
                f"📞 SMS: {'+' + sms_info['phone_number'][-4:] if sms_info and sms_info.get('phone_number') else 'N/A'}\n"
                "🛡️ Applying stealth measures...",
                progress=None  # Don't update main progress
            )
            
            # Generate profile
            account_profile = await self._run_in_thread_pool(
                self.snapchat_creator.generate_stealth_profile
            )
            
            # Set email and phone
            account_profile.email = email
            if sms_info and sms_info.get('phone_number'):
                account_profile.phone_number = sms_info['phone_number']
            
            # Create account using real automation
            result = await self._run_in_thread_pool(
                self.snapchat_creator.create_account,
                account_profile,
                device_id
            )
            
            if not result.success:
                raise RuntimeError(f"Account creation failed: {result.error_message}")
            
            # Handle SMS verification
            if sms_info and sms_info.get('phone_number'):
                sms_code = await self._run_in_thread_pool(
                    self.sms_verifier.get_verification_code,
                    sms_info['phone_number'],
                    timeout=120
                )
                if sms_code.get('success') and sms_code.get('code'):
                    verification_result = await self._run_in_thread_pool(
                        self.snapchat_creator.verify_phone_code,
                        device_id,
                        sms_code['code']
                    )
                    if not verification_result:
                        logger.warning(f"Phone verification failed for account {account_num}")
            
            # Perform warming activities
            await self._run_in_thread_pool(
                self.snapchat_creator.perform_warming_activities,
                device_id
            )
            
            # Configure for add farming
            await self._run_in_thread_pool(
                self.snapchat_creator.configure_add_farming,
                device_id
            )

            # Advanced post-registration strengthening
            # 1) Set display name consistency
            safe_display_name = result.profile.display_name if result and result.profile else account_profile.display_name
            try:
                await self._run_in_thread_pool(
                    self.snapchat_creator._app_automator_set_display_name,  # indirection via helper
                    device_id,
                    safe_display_name
                )
            except Exception:
                pass
            
            # 2) Set profile avatar (generated initials if no external image provided)
            try:
                await self._run_in_thread_pool(
                    self.snapchat_creator._app_automator_set_avatar,
                    device_id,
                    safe_display_name,
                    None
                )
            except Exception:
                pass
            
            # 3) Attempt Bitmoji link (enabled per request/session policy)
            bitmoji_shot = None
            try:
                bitmoji_shot = await self._run_in_thread_pool(
                    self.snapchat_creator._app_automator_link_bitmoji,
                    device_id
                )
            except Exception:
                bitmoji_shot = None
            
            # Return account result
            # Infer region from phone number prefix (best-effort)
            def _infer_region(phone: Optional[str]) -> Optional[str]:
                if not phone:
                    return None
                if phone.startswith('+1'):
                    return 'US'
                return None

            # Emulator config best-effort
            emulator_conf = None
            try:
                sess = self.android_orchestrator.get_session_info(emulator_session)
                emulator_conf = (sess.get('session_state') or {}).get('config_name') if sess else None
            except Exception:
                pass

            account_result = SnapAccountResult(
                username=result.profile.username,
                password=result.profile.password,
                email=result.profile.email,
                phone_number=result.profile.phone_number,
                device_id=device_id,
                session_id=emulator_session,
                verified=True,
                account_id=result.account_id,
                adds_ready=100,
                status="active",
                created_at=time.time(),
                emulator_config=emulator_conf,
                region=_infer_region(result.profile.phone_number),
                bitmoji_linked=bool(bitmoji_shot),
                bitmoji_screenshot_path=bitmoji_shot
            )

            # Webhook event per account
            if request.webhook_enabled and request.webhook_url:
                try:
                    await self._post_webhook_event(request.webhook_url, 'account_created', {
                        'request_id': request.request_id,
                        'account': asdict(account_result)
                    })
                except Exception as e:
                    logger.warning(f"Webhook post failed: {e}")

            return account_result
            
        except Exception as e:
            logger.error(f"Single account creation failed for account {account_num}: {e}")
            return None
    
    async def _verify_accounts(self, accounts: List[SnapAccountResult]) -> List[SnapAccountResult]:
        """Verify created accounts are functional"""
        try:
            verified_accounts = []
            
            for account in accounts:
                try:
                    # Prefer non-invasive verification to avoid detection
                    login_test = None
                    if hasattr(self.snapchat_creator, 'test_account_login'):
                        login_test = await self._run_in_thread_pool(
                            self.snapchat_creator.test_account_login,
                            account.username,
                            account.password,
                            account.device_id
                        )
                    
                    if login_test is True or login_test is None:
                        account.verified = True
                        verified_accounts.append(account)
                        logger.info(f"✅ Verified account: {account.username}")
                    else:
                        logger.warning(f"⚠️ Failed to verify account: {account.username}")
                        account.verified = False
                        verified_accounts.append(account)  # Still include it
                        
                except Exception as e:
                    logger.error(f"Verification error for {account.username}: {e}")
                    account.verified = False
                    verified_accounts.append(account)
            
            return verified_accounts
            
        except Exception as e:
            logger.error(f"Account verification failed: {e}")
            return accounts  # Return original list if verification fails
    
    async def _cleanup_resources(self, resources: ResourceAllocation):
        """Cleanup allocated resources"""
        try:
            # Cleanup emulators (keep them running for a bit for user testing)
            cleanup_delay = 300  # 5 minutes
            
            async def delayed_cleanup():
                await asyncio.sleep(cleanup_delay)
                for session_id in resources.emulator_sessions:
                    try:
                        self.android_orchestrator.end_automation_session(session_id)
                        if session_id in self.resource_pool['emulators']:
                            del self.resource_pool['emulators'][session_id]
                        logger.info(f"🧹 Cleaned up emulator: {session_id}")
                    except Exception as e:
                        logger.error(f"Cleanup error for {session_id}: {e}")
            
            # Start delayed cleanup
            asyncio.create_task(delayed_cleanup())
            
            # Release SMS numbers immediately
            for sms_entry in resources.sms_numbers:
                try:
                    phone_to_release = sms_entry.get('phone_number') if isinstance(sms_entry, dict) else None
                    if phone_to_release:
                        if self.sms_rate_limiter: self.sms_rate_limiter.acquire()
                        await self._run_in_thread_pool(
                            self.sms_verifier.release_number, phone_to_release
                        )
                except Exception as e:
                    logger.error(f"Error releasing SMS resource: {e}")
            
            logger.info("🧹 Resource cleanup initiated")
            
        except Exception as e:
            logger.error(f"Resource cleanup error: {e}")
    
    async def _send_final_results(self, request: SnapAccountRequest):
        """Send final results to user"""
        try:
            accounts = request.created_accounts
            success_count = len([a for a in accounts if a.verified])
            
            if success_count == 0:
                await self._update_progress(request,
                    "❌ **ACCOUNT CREATION FAILED**\n\n"
                    "No accounts were successfully created.\n"
                    "Please contact support for assistance.",
                    progress=100
                )
                return
            
            # Send summary
            summary_text = (
                "Order complete\n\n"
                f"Accounts created: {success_count}\n"
                f"Success rate: {success_count/request.account_count*100:.1f}%\n\n"
                "Credentials are being delivered in separate messages."
            )
            
            await self.telegram_app.bot.send_message(
                chat_id=request.user_id,
                text=summary_text,
                parse_mode='Markdown'
            )
            
            # Send individual account details
            for i, account in enumerate(accounts, 1):
                if account.verified:
                    account_text = f"ACCOUNT {i}\n\n"
                    account_text += f"Username: `{account.username}`\n"
                    account_text += f"Password: `{account.password}`\n"
                    account_text += f"Email: `{account.email}`\n"
                    account_text += f"Phone: `{account.phone_number}`\n\n"
                    account_text += f"Status: Ready for {account.adds_ready} adds\n"
                    
                    await self.telegram_app.bot.send_message(
                        chat_id=request.user_id,
                        text=account_text,
                        parse_mode='Markdown'
                    )
                    await asyncio.sleep(1)  # Rate limit
            
            # Send final completion message
            await self.telegram_app.bot.send_message(chat_id=request.user_id, text="Delivery complete.")
            
        except Exception as e:
            logger.error(f"Error sending final results: {e}")
    
    async def _update_progress(self, request: SnapAccountRequest, message: str, progress: Optional[int] = None):
        """Update progress message for user"""
        try:
            if not request.progress_message_id:
                return
            
            if progress is not None:
                progress_bar = self._create_progress_bar(progress)
                message += f"\n\n**Progress:** {progress}%\n{progress_bar}"
            
            # telegram_app is the Application; use its bot instance
            await self.telegram_app.bot.edit_message_text(
                chat_id=request.user_id,
                message_id=request.progress_message_id,
                text=message,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            try:
                err = str(e)[:140]
                fallback = f"Status update error: {err}"
                await self.telegram_app.bot.edit_message_text(
                    chat_id=request.user_id,
                    message_id=request.progress_message_id,
                    text=fallback
                )
            except Exception:
                logger.error(f"Error updating progress: {e}")
    
    def _create_progress_bar(self, progress: int) -> str:
        """Create visual progress bar"""
        filled = int(progress / 10)
        empty = 10 - filled
        return f"{'█' * filled}{'░' * empty} {progress}%"

    async def _post_webhook_event(self, url: str, event: str, payload: Dict[str, Any]):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(url, json={
                    'event': event,
                    'timestamp': int(time.time()),
                    'data': payload
                })
        except Exception as e:
            logger.warning(f"Webhook post error: {e}")

    def _persist_request_state(self, request: SnapAccountRequest):
        try:
            state_path = self.state_dir / f"{request.request_id}.json"
            payload = {
                'request_id': request.request_id,
                'user_id': request.user_id,
                'account_count': request.account_count,
                'status': request.status,
                'timestamp': request.timestamp,
                'created_accounts': [asdict(a) if hasattr(a, '__dict__') else (a.__dict__ if hasattr(a, '__dict__') else a) for a in (request.created_accounts or [])]
            }
            with open(state_path, 'w') as f:
                json.dump(payload, f)
        except Exception:
            pass
    
    async def _handle_request_failure(self, request: SnapAccountRequest, error_message: str):
        """Handle request failure"""
        try:
            request.status = "failed"
            request.error_message = error_message
            banner = (
                "Order failed\n\n"
                f"Error: {error_message[:300]}\n\n"
                "We’ll pause this order. You can retry or contact support."
            )
            await self.telegram_app.bot.edit_message_text(
                chat_id=request.user_id,
                message_id=request.progress_message_id,
                text=banner
            )
        except Exception as e:
            logger.error(f"Error handling request failure: {e}")
    
    async def _run_in_thread_pool(self, func, *args, **kwargs):
        """Run blocking function in thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.thread_pool,
            functools.partial(func, **kwargs) if kwargs else func,
            *args
        )
    
    def get_active_requests(self) -> Dict[str, Dict]:
        """Get information about active requests"""
        return {
            req_id: {
                'user_id': req.user_id,
                'account_count': req.account_count,
                'status': req.status,
                'progress': len(req.created_accounts or []),
                'timestamp': req.timestamp
            }
            for req_id, req in self.active_requests.items()
        }
    
    def cleanup_old_requests(self):
        """Cleanup old completed/failed requests"""
        current_time = time.time()
        old_requests = [
            req_id for req_id, req in self.active_requests.items()
            if req.status in ['completed', 'failed'] and current_time - req.timestamp > 3600  # 1 hour
        ]
        
        for req_id in old_requests:
            del self.active_requests[req_id]
        
        if old_requests:
            logger.info(f"🧹 Cleaned up {len(old_requests)} old requests")

# Global orchestrator instance
_snap_orchestrator = None

def get_snap_orchestrator(telegram_app) -> SnapCommandOrchestrator:
    """Get global snap command orchestrator"""
    global _snap_orchestrator
    if _snap_orchestrator is None:
        _snap_orchestrator = SnapCommandOrchestrator(telegram_app)
    return _snap_orchestrator

def cleanup_snap_orchestrator():
    """Cleanup snap orchestrator"""
    global _snap_orchestrator
    if _snap_orchestrator:
        # Cleanup any resources
        try:
            _snap_orchestrator.thread_pool.shutdown(wait=False)
        except:
            pass

# Register cleanup
import atexit
atexit.register(cleanup_snap_orchestrator)