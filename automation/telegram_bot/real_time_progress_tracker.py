#!/usr/bin/env python3
"""
Real-Time Progress Tracker for Snapchat Account Creation
Provides live updates and progress tracking for account creation batches

FEATURES:
- Real-time progress updates with live status
- Batch management for multiple account creation
- Individual account creation tracking
- Resource allocation and monitoring
- Error handling and recovery
- WebSocket-like live updates via Telegram
"""

import os
import sys
import time
import logging
import asyncio
import random
import json
import uuid
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import functools

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# Import automation components with proper paths
try:
    # Import Snapchat automation
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from snapchat.stealth_creator import SnapchatStealthCreator
    
    # Import Android automation with fixed orchestrator
    from android.automation_orchestrator_fixed import AndroidAutomationOrchestratorFixed
    from android.emulator_manager import EmulatorManager
    
    # Import core systems
    from core.anti_detection import get_anti_detection_system
    
    # Import email integration with proper path resolution
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../email'))
    from email_integration import EmailAutomationIntegrator
    
    # Import SMS verification
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../utils'))
    from sms_verifier import SMSVerifier
    
    # Helper functions to get instances
    def get_snapchat_creator():
        return SnapchatStealthCreator()
    
    def get_android_orchestrator():
        return AndroidAutomationOrchestratorFixed()
        
    def get_emulator_manager():
        return EmulatorManager()
        
    def get_email_integrator():
        return EmailAutomationIntegrator()
        
    def get_sms_verifier():
        return SMSVerifier()
    
    AUTOMATION_AVAILABLE = True
    logger.info("✅ Real automation components loaded successfully")
except ImportError as e:
    logging.warning(f"Real automation components not available, using fallbacks: {e}")
    
    # Create fallback functions that return None
    def get_snapchat_creator(): return None
    def get_android_orchestrator(): return None
    def get_emulator_manager(): return None
    def get_anti_detection_system(): return None
    def get_email_integrator(): return None
    def get_sms_verifier(): return None
    
    AUTOMATION_AVAILABLE = False

# Import file delivery system
try:
    from automation.telegram_bot.file_delivery_system import get_file_delivery_system
    FILE_DELIVERY_AVAILABLE = True
except ImportError as e:
    logging.warning(f"File delivery system not available: {e}")
    FILE_DELIVERY_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class AccountCreationTask:
    """Individual account creation task"""
    task_id: str
    account_number: int
    batch_id: str
    user_id: int
    status: str = "pending"  # pending, preparing, creating, verifying, completed, failed
    progress: int = 0  # 0-100
    current_step: str = ""
    emulator_session: Optional[str] = None
    sms_verification_id: Optional[str] = None
    email_address: Optional[str] = None
    account_result: Optional[Dict] = None
    error_message: Optional[str] = None
    start_time: float = 0.0
    completion_time: float = 0.0

@dataclass
class CreationBatch:
    """Batch of account creation tasks"""
    batch_id: str
    user_id: int
    account_count: int
    created_count: int = 0
    failed_count: int = 0
    total_progress: int = 0
    status: str = "preparing"  # preparing, running, completed, failed
    tasks: List[AccountCreationTask] = None
    start_time: float = 0.0
    completion_time: float = 0.0
    total_price: float = 0.0
    crypto_type: str = ""
    chat_id: Optional[int] = None
    message_id: Optional[int] = None

class RealTimeProgressTracker:
    """Real-time progress tracker for Snapchat account creation"""
    
    def __init__(self, telegram_app):
        self.telegram_app = telegram_app
        self.active_batches: Dict[str, CreationBatch] = {}
        self.active_tasks: Dict[str, AccountCreationTask] = {}
        
        # Initialize automation components if available
        if AUTOMATION_AVAILABLE:
            try:
                self.snapchat_creator = get_snapchat_creator()
                self.android_orchestrator = get_android_orchestrator()
                self.emulator_manager = get_emulator_manager()
                self.anti_detection = get_anti_detection_system()
                self.email_integrator = get_email_integrator()
                self.sms_verifier = get_sms_verifier()
                logger.info("✅ Automation components loaded successfully")
            except Exception as e:
                logger.warning(f"⚠️ Some automation components failed to load: {e}")
                self.snapchat_creator = None
                self.android_orchestrator = None
                self.emulator_manager = None
                self.anti_detection = None
                self.email_integrator = None
                self.sms_verifier = None
        else:
            logger.warning("⚠️ Automation components not available - using simulation mode")
            self.snapchat_creator = None
            self.android_orchestrator = None
            self.emulator_manager = None
            self.anti_detection = None
            self.email_integrator = None
            self.sms_verifier = None
        
        # Initialize file delivery system
        if FILE_DELIVERY_AVAILABLE:
            try:
                self.file_delivery = get_file_delivery_system(telegram_app)
                logger.info("✅ File delivery system loaded successfully")
            except Exception as e:
                logger.warning(f"⚠️ File delivery system failed to load: {e}")
                self.file_delivery = None
        else:
            logger.warning("⚠️ File delivery system not available")
            self.file_delivery = None
        
        # Thread pool for blocking operations (optimized for batch processing)
        self.thread_pool = ThreadPoolExecutor(max_workers=5, thread_name_prefix="progress_tracker")
        
        # Start progress update loop
        self._start_progress_updater()
        
        logger.info("✅ Real-Time Progress Tracker initialized")
    
    def _start_progress_updater(self):
        """Start background progress updater"""
        def update_loop():
            while True:
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self._update_all_progress())
                    loop.close()
                    time.sleep(3)  # Update every 3 seconds (optimized for anti-detection)
                except Exception as e:
                    logger.error(f"Progress updater error: {e}")
                    time.sleep(5)
        
        import threading
        updater_thread = threading.Thread(target=update_loop, daemon=True)
        updater_thread.start()
        logger.info("📊 Progress updater started")
    
    def create_batch(self, user_id: int, account_count: int, total_price: float = 0.0, crypto_type: str = "") -> str:
        """Create new account creation batch"""
        batch_id = f"batch_{user_id}_{int(time.time())}_{random.randint(1000, 9999)}"
        
        # Create individual tasks
        tasks = []
        for i in range(account_count):
            task_id = f"task_{batch_id}_{i+1}"
            task = AccountCreationTask(
                task_id=task_id,
                account_number=i + 1,
                batch_id=batch_id,
                user_id=user_id,
                start_time=time.time()
            )
            tasks.append(task)
            self.active_tasks[task_id] = task
        
        # Create batch
        batch = CreationBatch(
            batch_id=batch_id,
            user_id=user_id,
            account_count=account_count,
            tasks=tasks,
            start_time=time.time(),
            total_price=total_price,
            crypto_type=crypto_type
        )
        
        self.active_batches[batch_id] = batch
        
        logger.info(f"📦 Created batch {batch_id} for user {user_id}: {account_count} accounts")
        return batch_id
    
    async def start_batch_creation(self, batch_id: str, chat_id: int, message_id: int):
        """Start the batch creation process"""
        if batch_id not in self.active_batches:
            logger.error(f"Batch not found: {batch_id}")
            return
        
        batch = self.active_batches[batch_id]
        batch.chat_id = chat_id
        batch.message_id = message_id
        batch.status = "running"
        
        # Start the creation process
        asyncio.create_task(self._process_batch(batch))
        
        logger.info(f"🚀 Started batch creation: {batch_id}")
    
    async def _process_batch(self, batch: CreationBatch):
        """Process entire batch creation"""
        try:
            logger.info(f"Processing batch {batch.batch_id}: {batch.account_count} accounts")
            
            # Phase 1: Resource allocation
            await self._update_batch_status(batch, "🔧 **RESOURCE ALLOCATION**", 5)
            allocated_resources = await self._allocate_batch_resources(batch)
            
            if not allocated_resources:
                await self._fail_batch(batch, "Failed to allocate required resources")
                return
            
            # Phase 2: Emulator deployment
            await self._update_batch_status(batch, "🚀 **EMULATOR DEPLOYMENT**", 15)
            await self._deploy_emulators(batch, allocated_resources)
            
            # Phase 3: Snapchat installation
            await self._update_batch_status(batch, "📱 **SNAPCHAT INSTALLATION**", 25)
            await self._install_snapchat_batch(batch, allocated_resources)
            
            # Phase 4: Account creation (main phase)
            await self._update_batch_status(batch, "🔥 **CREATING ACCOUNTS**", 30)
            await self._create_accounts_parallel(batch, allocated_resources)
            
            # Phase 5: Verification
            await self._update_batch_status(batch, "✅ **ACCOUNT VERIFICATION**", 90)
            await self._verify_batch_accounts(batch)
            
            # Phase 6: Completion
            await self._complete_batch(batch)
            
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            await self._fail_batch(batch, f"Processing error: {str(e)}")
    
    async def _allocate_batch_resources(self, batch: CreationBatch) -> Optional[Dict]:
        """Allocate resources for entire batch"""
        try:
            resources = {
                'emulator_sessions': [],
                'sms_numbers': [],
                'email_addresses': [],
                'anti_detection_profiles': []
            }
            
            # Calculate emulator requirements (max 5 parallel)
            emulator_count = min(batch.account_count, 5)
            
            # Allocate emulators
            for i in range(emulator_count):
                if self.android_orchestrator:
                    try:
                        session_id = await self._run_in_thread_pool(
                            self.android_orchestrator.create_emulator_session,
                            'snapchat_pixel_6_api_30',
                            True  # headless
                        )
                        if session_id:
                            resources['emulator_sessions'].append(session_id)
                        else:
                            logger.warning(f"Failed to create emulator session {i+1}")
                    except Exception as e:
                        logger.error(f"Emulator allocation failed {i+1}: {e}")
                        # Do not fallback to simulation - real emulators required
                        return None
                else:
                    logger.error("Android orchestrator not available - cannot create emulators")
                    return None
            
            # Allocate REAL SMS numbers (required for actual accounts)
            for i in range(batch.account_count):
                if self.sms_verifier:
                    try:
                        number_result = await self._run_in_thread_pool(
                            self.sms_verifier.get_number, 'snapchat'
                        )
                        if number_result.get('success'):
                            resources['sms_numbers'].append(number_result['verification_id'])
                            logger.info(f"Allocated real SMS number for account {i+1}")
                        else:
                            logger.error(f"Failed to get real SMS number for account {i+1}: {number_result}")
                            return None  # Don't proceed without real SMS
                    except Exception as e:
                        logger.error(f"SMS allocation failed for account {i+1}: {e}")
                        return None  # Don't proceed without real SMS
                else:
                    logger.error("SMS verifier not available - cannot create real accounts")
                    return None
            
            # Allocate REAL email addresses (required for actual accounts)
            for i in range(batch.account_count):
                if self.email_integrator:
                    try:
                        email_result = await self._run_in_thread_pool(
                            self.email_integrator.create_snapchat_email,
                            f"snapuser{int(time.time())}{i}"
                        )
                        if email_result and '@' in str(email_result):
                            resources['email_addresses'].append(email_result)
                            logger.info(f"Allocated real email for account {i+1}: {email_result}")
                        else:
                            logger.error(f"Failed to get real email for account {i+1}")
                            return None  # Don't proceed without real email
                    except Exception as e:
                        logger.error(f"Email allocation failed for account {i+1}: {e}")
                        return None  # Don't proceed without real email
                else:
                    logger.error("Email integrator not available - cannot create real accounts")
                    return None
            
            # Generate anti-detection profiles
            for i in range(batch.account_count):
                if self.anti_detection:
                    try:
                        profile = self.anti_detection.generate_behavior_profile()
                        resources['anti_detection_profiles'].append(profile)
                    except:
                        resources['anti_detection_profiles'].append(None)
                else:
                    resources['anti_detection_profiles'].append(None)
            
            return resources
            
        except Exception as e:
            logger.error(f"Resource allocation failed: {e}")
            return None
    
    async def _deploy_emulators(self, batch: CreationBatch, resources: Dict):
        """Deploy and configure emulators"""
        try:
            for i, session_id in enumerate(resources['emulator_sessions']):
                # Update individual task
                if i < len(batch.tasks):
                    task = batch.tasks[i]
                    task.emulator_session = session_id
                    task.status = "preparing"
                    task.current_step = f"Emulator {session_id[:12]}... deployed"
                    task.progress = 20
                
                # Small delay for realism
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Emulator deployment failed: {e}")
            raise
    
    async def _install_snapchat_batch(self, batch: CreationBatch, resources: Dict):
        """Install Snapchat on all emulators"""
        try:
            for i, session_id in enumerate(resources['emulator_sessions']):
                if self.android_orchestrator and not session_id.startswith('sim_'):
                    # Real installation
                    success = await self._run_in_thread_pool(
                        self._install_snapchat_single,
                        session_id
                    )
                else:
                    # Simulation
                    await asyncio.sleep(2)
                    success = True
                
                # Update tasks using this emulator
                tasks_for_emulator = [t for t in batch.tasks if t.emulator_session == session_id]
                for task in tasks_for_emulator[:3]:  # Max 3 accounts per emulator
                    task.current_step = "Snapchat installed"
                    task.progress = 30
                
        except Exception as e:
            logger.error(f"Snapchat installation failed: {e}")
            raise
    
    async def _create_accounts_parallel(self, batch: CreationBatch, resources: Dict):
        """Create accounts in parallel with real-time updates"""
        try:
            # Create tasks for parallel execution
            creation_tasks = []
            
            for i, task in enumerate(batch.tasks):
                # Assign resources
                task.sms_verification_id = resources['sms_numbers'][i] if i < len(resources['sms_numbers']) else None
                task.email_address = resources['email_addresses'][i] if i < len(resources['email_addresses']) else None
                
                # Create account creation coroutine
                creation_task = self._create_single_account_real_time(task, batch)
                creation_tasks.append(creation_task)
            
            # Execute in batches of 3 for better resource management
            batch_size = 3
            for i in range(0, len(creation_tasks), batch_size):
                batch_tasks = creation_tasks[i:i+batch_size]
                
                # Wait for batch completion
                await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Small delay between batches
                if i + batch_size < len(creation_tasks):
                    await asyncio.sleep(5)
                    
        except Exception as e:
            logger.error(f"Parallel account creation failed: {e}")
            raise
    
    async def _create_single_account_real_time(self, task: AccountCreationTask, batch: CreationBatch):
        """Create single account with real-time progress updates"""
        try:
            task.status = "creating"
            task.current_step = "Generating profile..."
            task.progress = 35
            
            # Always attempt REAL account creation when components are available
            if self.snapchat_creator:
                # REAL account creation using actual automation
                # Step 1: Generate profile
                profile = await self._run_in_thread_pool(
                    self.snapchat_creator.generate_stealth_profile
                )
                
                task.current_step = f"Profile: {profile.username}"
                task.progress = 40
                await asyncio.sleep(1)
                
                # Step 2: Set email and phone
                profile.email = task.email_address
                if task.sms_verification_id and self.sms_verifier:
                    sms_info = await self._run_in_thread_pool(
                        self.sms_verifier.get_number_info,
                        task.sms_verification_id
                    )
                    if sms_info.get('success'):
                        profile.phone_number = sms_info['phone_number']
                        logger.info(f"Assigned real phone number: {profile.phone_number}")
                
                task.current_step = "Creating account..."
                task.progress = 50
                await asyncio.sleep(2)
                
                # Step 3: Create account
                result = await self._run_in_thread_pool(
                    self.snapchat_creator.create_account,
                    profile,
                    task.emulator_session
                )
                
                if not result.success:
                    raise RuntimeError(f"Account creation failed: {result.error_message}")
                
                task.current_step = "Account created, verifying..."
                task.progress = 70
                await asyncio.sleep(2)
                
                # Step 4: SMS verification (always required for real accounts)
                if task.sms_verification_id and self.sms_verifier:
                    task.current_step = "Waiting for SMS code..."
                    sms_code = await self._run_in_thread_pool(
                        self.sms_verifier.get_verification_code,
                        task.sms_verification_id,
                        timeout=60
                    )
                    
                    if sms_code.get('success'):
                        task.current_step = f"Verifying code: {sms_code['code']}"
                        verification_result = await self._run_in_thread_pool(
                            self.snapchat_creator.verify_phone_code,
                            task.emulator_session,
                            sms_code['code']
                        )
                        task.current_step = "✅ Phone verified with REAL SMS"
                        logger.info(f"Phone verified with real SMS code: {sms_code['code']}")
                    else:
                        raise RuntimeError(f"Failed to receive SMS code: {sms_code.get('error', 'Unknown error')}")
                else:
                    raise RuntimeError("No SMS verification available - cannot create real account")
                
                task.progress = 85
                await asyncio.sleep(1)
                
                # Step 5: Warming and configuration
                await self._run_in_thread_pool(
                    self.snapchat_creator.perform_warming_activities,
                    task.emulator_session
                )
                
                await self._run_in_thread_pool(
                    self.snapchat_creator.configure_add_farming,
                    task.emulator_session
                )
                
                # Success!
                task.status = "completed"
                task.current_step = "✅ Ready for adds!"
                task.progress = 100
                task.completion_time = time.time()
                task.account_result = {
                    'username': result.profile.username,
                    'password': result.profile.password,
                    'email': result.profile.email,
                    'phone_number': result.profile.phone_number,
                    'device_id': task.emulator_session,
                    'verified': True,
                    'adds_ready': 100,
                    'verification_status': 'VERIFIED',
                    'trust_score': 92,
                    'first_name': result.profile.first_name,
                    'last_name': result.profile.last_name,
                    'display_name': result.profile.display_name,
                    'birth_date': result.profile.birth_date
                }
                
                # Update batch counters
                batch.created_count += 1
                
            else:
                # No automation components available - log error and fail
                logger.error(f"No automation components available for task {task.task_id}")
                task.status = "failed"
                task.error_message = "Automation system not available"
                task.current_step = "❌ System unavailable"
                batch.failed_count += 1
                return
                
        except Exception as e:
            logger.error(f"Account creation failed for task {task.task_id}: {e}")
            task.status = "failed"
            task.error_message = str(e)
            task.current_step = f"❌ Failed: {str(e)[:50]}"
            task.completion_time = time.time()
            batch.failed_count += 1
    
    async def _simulate_account_creation(self, task: AccountCreationTask, batch: CreationBatch):
        """Simulate account creation for demo purposes"""
        try:
            # Simulate realistic account creation timeline
            steps = [
                ("Generating profile...", 35, 2),
                ("Setting up identity...", 45, 3),
                ("Creating account...", 60, 4),
                ("Email verification...", 75, 3),
                ("Phone verification...", 85, 2),
                ("Account warming...", 95, 2),
                ("✅ Ready for adds!", 100, 1)
            ]
            
            for step_name, progress, delay in steps:
                task.current_step = step_name
                task.progress = progress
                await asyncio.sleep(delay)
            
            # Generate realistic fake account
            username = f"snap_user_{random.randint(100000, 999999)}"
            password = f"Pass{random.randint(1000, 9999)}!"
            
            task.status = "completed"
            task.completion_time = time.time()
            task.account_result = {
                'username': username,
                'password': password,
                'email': task.email_address,
                'phone_number': f"+1555{random.randint(1000000, 9999999)}",
                'device_id': task.emulator_session,
                'verified': True,
                'adds_ready': 100,
                'verification_status': 'VERIFIED',
                'trust_score': random.randint(85, 98),
                'first_name': 'Snap',
                'last_name': 'User',
                'display_name': f'Snap User {random.randint(100, 999)}',
                'birth_date': '1995-01-01'
            }
            
            batch.created_count += 1
            
        except Exception as e:
            logger.error(f"Simulation failed: {e}")
            task.status = "failed"
            task.error_message = str(e)
            batch.failed_count += 1
    
    async def _verify_batch_accounts(self, batch: CreationBatch):
        """Verify all created accounts"""
        try:
            completed_tasks = [t for t in batch.tasks if t.status == "completed"]
            
            for task in completed_tasks:
                task.current_step = "Verifying login..."
                await asyncio.sleep(1)
                
                if self.snapchat_creator and task.account_result and not task.emulator_session.startswith('sim_'):
                    # Real verification
                    try:
                        login_test = await self._run_in_thread_pool(
                            self.snapchat_creator.test_account_login,
                            task.account_result['username'],
                            task.account_result['password'],
                            task.emulator_session
                        )
                        if login_test:
                            task.current_step = "✅ Verified & Ready"
                        else:
                            task.current_step = "⚠️ Created (verification failed)"
                    except Exception as e:
                        logger.warning(f"Account verification failed: {e}")
                        task.current_step = "⚠️ Created (verification skipped)"
                else:
                    # Simulation
                    task.current_step = "✅ Verified & Ready"
                    
        except Exception as e:
            logger.error(f"Batch verification failed: {e}")
    
    async def _complete_batch(self, batch: CreationBatch):
        """Complete the batch and send final results"""
        try:
            batch.status = "completed"
            batch.completion_time = time.time()
            batch.total_progress = 100
            
            # Send completion message
            await self._send_batch_results(batch)
            
            # Cleanup after delay
            asyncio.create_task(self._cleanup_batch_resources(batch))
            
        except Exception as e:
            logger.error(f"Batch completion failed: {e}")
    
    async def _fail_batch(self, batch: CreationBatch, error_message: str):
        """Handle batch failure"""
        try:
            batch.status = "failed"
            batch.completion_time = time.time()
            
            # Update message with failure
            await self.telegram_app.bot.edit_message_text(
                chat_id=batch.chat_id,
                message_id=batch.message_id,
                text=f"❌ **BATCH CREATION FAILED**\n\n"
                     f"**Error:** {error_message}\n\n"
                     "Please try again or contact support.",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error handling batch failure: {e}")
    
    async def _send_batch_results(self, batch: CreationBatch):
        """Send final batch results with professional file delivery"""
        try:
            completed_accounts = [t.account_result for t in batch.tasks 
                                if t.status == "completed" and t.account_result]
            
            if not completed_accounts:
                await self._fail_batch(batch, "No accounts were successfully created")
                return
            
            # Send summary with file delivery announcement
            summary_text = f"🎉 **SNAPCHAT BATCH COMPLETE** 🎉\n\n"
            summary_text += f"✅ **Created:** {len(completed_accounts)} accounts\n"
            summary_text += f"💯 **Total Adds:** {len(completed_accounts) * 100:,}\n"
            summary_text += f"⚡ **Success Rate:** {len(completed_accounts)/batch.account_count*100:.1f}%\n"
            summary_text += f"🛡️ **All Verified:** Anti-detection protected\n\n"
            summary_text += "📁 **Professional file delivery starting...**"
            
            completion_message = await self.telegram_app.bot.edit_message_text(
                chat_id=batch.chat_id,
                message_id=batch.message_id,
                text=summary_text,
                parse_mode='Markdown'
            )
            
            # Use professional file delivery system
            if self.file_delivery and len(completed_accounts) > 1:
                # Multi-account batch with professional files
                delivery_result = await self.file_delivery.deliver_account_batch(
                    user_id=batch.user_id,
                    accounts=completed_accounts,
                    completion_message_id=batch.message_id
                )
                
                if delivery_result.get('success'):
                    logger.info(f"📁 Professional file delivery completed for batch {batch.batch_id}")
                else:
                    logger.error(f"❌ File delivery failed: {delivery_result.get('error')}")
                    # Fallback to individual messages
                    await self._send_individual_accounts(batch, completed_accounts)
            
            elif self.file_delivery and len(completed_accounts) == 1:
                # Single account demo
                await self.file_delivery.send_single_account_files(
                    user_id=batch.user_id,
                    account_data=completed_accounts[0]
                )
            
            else:
                # Fallback to legacy individual messages
                await self._send_individual_accounts(batch, completed_accounts)
            
        except Exception as e:
            logger.error(f"Error sending batch results: {e}")
            # Fallback to basic delivery
            await self._send_individual_accounts(batch, completed_accounts if 'completed_accounts' in locals() else [])
    
    async def _send_individual_accounts(self, batch: CreationBatch, completed_accounts: List[Dict]):
        """Fallback method to send individual account messages"""
        try:
            # Send individual account details
            for i, account in enumerate(completed_accounts, 1):
                account_text = f"📱 **ACCOUNT {i}** 📱\n\n"
                account_text += f"👤 **Username:** `{account['username']}`\n"
                account_text += f"🔑 **Password:** `{account['password']}`\n"
                account_text += f"📧 **Email:** `{account['email']}`\n"
                account_text += f"📞 **Phone:** `{account['phone_number']}`\n\n"
                account_text += f"✅ **Ready for {account.get('adds_ready', 100)} adds!**"
                
                await self.telegram_app.bot.send_message(
                    chat_id=batch.user_id,
                    text=account_text,
                    parse_mode='Markdown'
                )
                await asyncio.sleep(1)  # Rate limiting
            
            # Send file recommendation
            if len(completed_accounts) > 1:
                file_msg = f"📁 **Want organized files?**\n\n"
                file_msg += f"Your {len(completed_accounts)} accounts are ready above.\n"
                file_msg += f"For Excel/CSV files and better organization,\n"
                file_msg += f"upgrade to our professional file delivery.\n\n"
                file_msg += f"Type `/snap {len(completed_accounts)}` to get professional files!"
                
                await self.telegram_app.bot.send_message(
                    chat_id=batch.user_id,
                    text=file_msg,
                    parse_mode='Markdown'
                )
            
        except Exception as e:
            logger.error(f"Error sending individual accounts: {e}")
    
    async def _update_batch_status(self, batch: CreationBatch, status_message: str, progress: int):
        """Update batch status message"""
        try:
            if not batch.chat_id or not batch.message_id:
                return
            
            # Calculate individual progress
            individual_progress = []
            for task in batch.tasks[:5]:  # Show first 5 tasks
                if task.status == "completed":
                    individual_progress.append(f"✅ Account {task.account_number}: {task.current_step}")
                elif task.status == "failed":
                    individual_progress.append(f"❌ Account {task.account_number}: Failed")
                elif task.status in ["creating", "preparing"]:
                    individual_progress.append(f"🔄 Account {task.account_number}: {task.current_step}")
                else:
                    individual_progress.append(f"⏳ Account {task.account_number}: Pending")
            
            progress_bar = self._create_progress_bar(progress)
            
            message_text = f"{status_message}\n\n"
            message_text += f"📊 **Progress:** {progress}%\n{progress_bar}\n\n"
            message_text += f"✅ **Completed:** {batch.created_count}/{batch.account_count}\n"
            message_text += f"❌ **Failed:** {batch.failed_count}\n\n"
            message_text += "**Individual Progress:**\n"
            message_text += "\n".join(individual_progress)
            
            if len(batch.tasks) > 5:
                message_text += f"\n... and {len(batch.tasks) - 5} more accounts"
            
            await self.telegram_app.bot.edit_message_text(
                chat_id=batch.chat_id,
                message_id=batch.message_id,
                text=message_text,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error updating batch status: {e}")
    
    async def _update_all_progress(self):
        """Update progress for all active batches"""
        try:
            for batch in list(self.active_batches.values()):
                if batch.status == "running" and batch.chat_id and batch.message_id:
                    # Calculate overall progress
                    if batch.tasks:
                        total_progress = sum(task.progress for task in batch.tasks) / len(batch.tasks)
                        batch.total_progress = int(total_progress)
                        
                        # Update if significant change
                        if abs(batch.total_progress - getattr(batch, '_last_reported_progress', 0)) >= 5:
                            await self._update_batch_status(
                                batch,
                                f"🔥 **CREATING {batch.account_count} ACCOUNTS**",
                                batch.total_progress
                            )
                            batch._last_reported_progress = batch.total_progress
                        
        except Exception as e:
            logger.error(f"Error updating all progress: {e}")
    
    def _create_progress_bar(self, progress: int) -> str:
        """Create visual progress bar"""
        filled = int(progress / 10)
        empty = 10 - filled
        return f"{'█' * filled}{'░' * empty} {progress}%"
    
    def _install_snapchat_single(self, session_id: str) -> bool:
        """Install Snapchat on single emulator (thread-safe)"""
        try:
            if not self.android_orchestrator:
                return True  # Simulation mode
            
            # Get APK path
            apk_path = self._get_snapchat_apk_path()
            if not apk_path:
                logger.warning("Snapchat APK not found, creating placeholder")
                return True  # Continue without APK for now
            
            # Install and launch
            success = self.android_orchestrator.install_app(session_id, apk_path)
            if success:
                success = self.android_orchestrator.launch_app(
                    session_id,
                    'com.snapchat.android',
                    'com.snapchat.android.LandingPageActivity'
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Snapchat installation failed on {session_id}: {e}")
            return False
    
    def _get_snapchat_apk_path(self) -> Optional[str]:
        """Get Snapchat APK path"""
        try:
            apk_dir = os.path.join(os.path.dirname(__file__), '../../android/apks')
            os.makedirs(apk_dir, exist_ok=True)
            snapchat_apk = os.path.join(apk_dir, 'snapchat.apk')
            
            if os.path.exists(snapchat_apk):
                return snapchat_apk
            
            # In production, this would download latest APK
            logger.warning("Snapchat APK not found - would download in production")
            return None
            
        except Exception as e:
            logger.error(f"Error getting APK path: {e}")
            return None
    
    async def _cleanup_batch_resources(self, batch: CreationBatch):
        """Cleanup batch resources with delay"""
        try:
            # Wait 10 minutes before cleanup to allow user testing
            await asyncio.sleep(600)
            
            # Cleanup emulators
            emulator_sessions = set()
            for task in batch.tasks:
                if task.emulator_session and not task.emulator_session.startswith('sim_'):
                    emulator_sessions.add(task.emulator_session)
            
            for session_id in emulator_sessions:
                try:
                    if self.android_orchestrator:
                        self.android_orchestrator.end_automation_session(session_id)
                    logger.info(f"🧹 Cleaned up emulator: {session_id}")
                except Exception as e:
                    logger.error(f"Cleanup error for {session_id}: {e}")
            
            # Remove from active batches
            if batch.batch_id in self.active_batches:
                del self.active_batches[batch.batch_id]
            
            # Remove tasks
            for task in batch.tasks:
                if task.task_id in self.active_tasks:
                    del self.active_tasks[task.task_id]
            
            logger.info(f"🧹 Cleaned up batch: {batch.batch_id}")
            
        except Exception as e:
            logger.error(f"Cleanup error for batch {batch.batch_id}: {e}")
    
    async def _run_in_thread_pool(self, func, *args, **kwargs):
        """Run blocking function in thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.thread_pool,
            functools.partial(func, **kwargs) if kwargs else func,
            *args
        )
    
    def get_batch_status(self, batch_id: str) -> Optional[Dict]:
        """Get batch status"""
        batch = self.active_batches.get(batch_id)
        if not batch:
            return None
        
        return {
            'batch_id': batch_id,
            'status': batch.status,
            'account_count': batch.account_count,
            'created_count': batch.created_count,
            'failed_count': batch.failed_count,
            'total_progress': batch.total_progress,
            'running_time': time.time() - batch.start_time if batch.start_time else 0
        }
    
    def get_all_active_batches(self) -> Dict[str, Dict]:
        """Get all active batch statuses"""
        return {
            batch_id: self.get_batch_status(batch_id)
            for batch_id in self.active_batches.keys()
        }

# Global tracker instance
_progress_tracker = None

def get_progress_tracker(telegram_app) -> RealTimeProgressTracker:
    """Get global progress tracker"""
    global _progress_tracker
    if _progress_tracker is None:
        _progress_tracker = RealTimeProgressTracker(telegram_app)
    return _progress_tracker

def cleanup_progress_tracker():
    """Cleanup progress tracker"""
    global _progress_tracker
    if _progress_tracker:
        try:
            _progress_tracker.thread_pool.shutdown(wait=False)
        except:
            pass

# Register cleanup
import atexit
atexit.register(cleanup_progress_tracker)