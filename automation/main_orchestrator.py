#!/usr/bin/env python3
"""
Main Tinder Automation Orchestrator
Coordinates the entire account creation and management pipeline
"""

import os
import sys
import time
import random
import logging
import json
import argparse
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import all automation components
from android.emulator_manager import get_emulator_manager, EmulatorInstance
from core.anti_detection import get_anti_detection_system
from tinder.account_creator import get_account_creator, AccountCreationResult
from tinder.profile_manager import get_profile_manager
from tinder.warming_scheduler import get_warming_manager
from snapchat.stealth_creator import get_snapchat_creator

# Import existing utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../utils'))
from brightdata_proxy import verify_proxy
from sms_verifier import get_sms_verifier, get_statistics_sync

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class AutomationConfig:
    """Configuration for automation pipeline"""
    tinder_account_count: int
    snapchat_account_count: int
    emulator_count: int
    aggressiveness_level: float  # 0.1 (conservative) to 1.0 (aggressive)
    warming_enabled: bool
    parallel_creation: bool
    output_directory: str
    headless_emulators: bool = True

class TinderAutomationOrchestrator:
    """Main orchestrator for Tinder account automation"""
    
    def __init__(self, config: AutomationConfig):
        self.config = config
        self.emulator_manager = get_emulator_manager()
        self.anti_detection = get_anti_detection_system(config.aggressiveness_level)
        self.account_creator = get_account_creator(config.aggressiveness_level)
        self.profile_manager = get_profile_manager()
        self.warming_manager = get_warming_manager()
        self.snapchat_creator = get_snapchat_creator()
        self.sms_verifier = get_sms_verifier()
        
        # Results storage
        self.snapchat_results: List = []
        self.tinder_results: List = []
        self.emulator_instances: List[EmulatorInstance] = []
        
        # Create output directory
        Path(config.output_directory).mkdir(parents=True, exist_ok=True)
    
    def verify_prerequisites(self) -> bool:
        """Verify all prerequisites are met"""
        logger.info("Verifying automation prerequisites...")
        
        checks = {}
        
        # Check proxy connection
        try:
            verify_proxy()
            checks['proxy'] = True
            logger.info("✅ Proxy connection verified")
        except Exception as e:
            checks['proxy'] = False
            logger.error(f"❌ Proxy verification failed: {e}")
        
        # Check anti-detection system
        try:
            stealth_results = self.anti_detection.verify_stealth_setup()
            checks['anti_detection'] = all(stealth_results.values())
            if checks['anti_detection']:
                logger.info("✅ Anti-detection system verified")
            else:
                logger.error(f"❌ Anti-detection issues: {stealth_results}")
        except Exception as e:
            checks['anti_detection'] = False
            logger.error(f"❌ Anti-detection verification failed: {e}")
        
        # Check SMS verification
        try:
            stats = get_statistics_sync()
            checks['sms'] = stats.get('pool_status', {}).get('available_numbers', 0) > 0
            if checks['sms']:
                logger.info(f"✅ SMS verification ready ({stats['pool_status']['available_numbers']} numbers)")
            else:
                logger.error("❌ No SMS numbers available")
        except Exception as e:
            checks['sms'] = False
            logger.error(f"❌ SMS verification check failed: {e}")
        
        # Check Android SDK
        try:
            sdk_manager = self.emulator_manager.sdk_manager
            if os.path.exists(sdk_manager.emulator):
                checks['android_sdk'] = True
                logger.info("✅ Android SDK found")
            else:
                checks['android_sdk'] = False
                logger.error("❌ Android SDK not found")
        except Exception as e:
            checks['android_sdk'] = False
            logger.error(f"❌ Android SDK check failed: {e}")
        
        all_good = all(checks.values())
        if all_good:
            logger.info("✅ All prerequisites verified")
        else:
            logger.error("❌ Some prerequisites failed - see above")
        
        return all_good
    
    def setup_emulator_pool(self) -> List[EmulatorInstance]:
        """Set up emulator pool for automation"""
        logger.info(f"Setting up {self.config.emulator_count} emulators...")
        
        try:
            self.emulator_instances = self.emulator_manager.create_emulator_pool(
                count=self.config.emulator_count,
                headless=self.config.headless_emulators
            )
            
            if len(self.emulator_instances) < self.config.emulator_count:
                logger.warning(f"Only {len(self.emulator_instances)}/{self.config.emulator_count} emulators available")
            
            logger.info(f"✅ Emulator pool ready: {len(self.emulator_instances)} instances")
            return self.emulator_instances
            
        except Exception as e:
            logger.error(f"Failed to set up emulator pool: {e}")
            return []
    
    def create_snapchat_accounts(self) -> List[str]:
        """Create Snapchat accounts and return usernames"""
        if self.config.snapchat_account_count == 0:
            return []
        
        logger.info(f"Creating {self.config.snapchat_account_count} Snapchat accounts...")
        
        try:
            # Use subset of emulators for Snapchat
            snapchat_emulators = self.emulator_instances[:self.config.snapchat_account_count]
            device_ids = [inst.device_id for inst in snapchat_emulators]
            
            # Create accounts
            results = self.snapchat_creator.create_multiple_accounts(
                count=self.config.snapchat_account_count,
                device_ids=device_ids
            )
            
            self.snapchat_results = results
            
            # Extract successful usernames
            usernames = []
            for result in results:
                if result.success and result.profile:
                    usernames.append(result.profile.username)
            
            logger.info(f"✅ Snapchat creation completed: {len(usernames)}/{self.config.snapchat_account_count} successful")
            
            # Save results
            self._save_results('snapchat_results.json', results)
            
            return usernames
            
        except Exception as e:
            logger.error(f"Snapchat account creation failed: {e}")
            return []
    
    def create_tinder_accounts(self, snapchat_usernames: List[str] = None) -> List[AccountCreationResult]:
        """Create Tinder accounts with Snapchat integration"""
        logger.info(f"Creating {self.config.tinder_account_count} Tinder accounts...")
        
        try:
            if self.config.parallel_creation:
                results = self._create_tinder_accounts_parallel(snapchat_usernames)
            else:
                results = self._create_tinder_accounts_sequential(snapchat_usernames)
            
            self.tinder_results = results
            
            # Summary
            successful = sum(1 for r in results if r.success)
            logger.info(f"✅ Tinder creation completed: {successful}/{self.config.tinder_account_count} successful")
            
            # Save results
            self._save_results('tinder_results.json', results)
            
            return results
            
        except Exception as e:
            logger.error(f"Tinder account creation failed: {e}")
            return []
    
    def _create_tinder_accounts_parallel(self, snapchat_usernames: List[str] = None) -> List[AccountCreationResult]:
        """Create Tinder accounts in parallel"""
        results = []
        
        # Create thread pool
        with ThreadPoolExecutor(max_workers=min(self.config.tinder_account_count, len(self.emulator_instances))) as executor:
            # Submit tasks
            futures = []
            
            for i in range(min(self.config.tinder_account_count, len(self.emulator_instances))):
                emulator = self.emulator_instances[i]
                snapchat_username = snapchat_usernames[i] if snapchat_usernames and i < len(snapchat_usernames) else None
                
                future = executor.submit(self._create_single_tinder_account, emulator, snapchat_username)
                futures.append(future)
            
            # Collect results
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Parallel account creation failed: {e}")
                    results.append(AccountCreationResult(success=False, error=str(e)))
        
        return results
    
    def _create_tinder_accounts_sequential(self, snapchat_usernames: List[str] = None) -> List[AccountCreationResult]:
        """Create Tinder accounts sequentially"""
        results = []
        
        for i in range(min(self.config.tinder_account_count, len(self.emulator_instances))):
            emulator = self.emulator_instances[i]
            snapchat_username = snapchat_usernames[i] if snapchat_usernames and i < len(snapchat_usernames) else None
            
            try:
                result = self._create_single_tinder_account(emulator, snapchat_username)
                results.append(result)
                
                # Delay between sequential creations
                if i < self.config.tinder_account_count - 1:
                    delay = random.uniform(30, 90)
                    logger.info(f"Waiting {delay:.1f}s before next account...")
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Sequential account creation {i+1} failed: {e}")
                results.append(AccountCreationResult(success=False, error=str(e)))
        
        return results
    
    def _create_single_tinder_account(self, emulator: EmulatorInstance, snapchat_username: str = None) -> AccountCreationResult:
        """Create single Tinder account"""
        # Generate profile with Snapchat integration
        profile = self.account_creator.generate_random_profile(snapchat_username)
        
        # Create account
        result = self.account_creator.create_account(profile, emulator)
        
        return result
    
    def start_account_warming(self) -> bool:
        """Start account warming for created accounts"""
        if not self.config.warming_enabled:
            logger.info("Account warming disabled")
            return True
        
        logger.info("Starting account warming system...")
        
        try:
            # Add successful accounts to warming system
            for result in self.tinder_results:
                if result.success:
                    self.warming_manager.add_account_for_warming(result, result.device_id)
            
            # Start warming scheduler
            self.warming_manager.start_warming_scheduler()
            
            logger.info(f"✅ Account warming started for {len([r for r in self.tinder_results if r.success])} accounts")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start account warming: {e}")
            return False
    
    def _save_results(self, filename: str, results: List):
        """Save results to JSON file"""
        try:
            output_path = os.path.join(self.config.output_directory, filename)
            
            # Convert dataclass objects to dict for JSON serialization
            serializable_results = []
            for result in results:
                if hasattr(result, '__dict__'):
                    data = asdict(result) if hasattr(result, '__dataclass_fields__') else result.__dict__
                else:
                    data = result
                serializable_results.append(data)
            
            with open(output_path, 'w') as f:
                json.dump(serializable_results, f, indent=2, default=str)
            
            logger.info(f"Results saved to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to save results to {filename}: {e}")
    
    def generate_summary_report(self) -> Dict[str, any]:
        """Generate comprehensive summary report"""
        report = {
            'execution_time': datetime.now().isoformat(),
            'configuration': asdict(self.config),
            'snapchat_results': {
                'total_attempts': len(self.snapchat_results),
                'successful': sum(1 for r in self.snapchat_results if r.success),
                'success_rate': 0.0
            },
            'tinder_results': {
                'total_attempts': len(self.tinder_results),
                'successful': sum(1 for r in self.tinder_results if r.success),
                'verified': sum(1 for r in self.tinder_results if r.verification_status == "verified"),
                'success_rate': 0.0,
                'verification_rate': 0.0
            },
            'infrastructure': {
                'emulators_created': len(self.emulator_instances),
                'emulators_ready': sum(1 for e in self.emulator_instances if e.is_ready)
            }
        }
        
        # Calculate rates
        if report['snapchat_results']['total_attempts'] > 0:
            report['snapchat_results']['success_rate'] = (
                report['snapchat_results']['successful'] / 
                report['snapchat_results']['total_attempts']
            )
        
        if report['tinder_results']['total_attempts'] > 0:
            report['tinder_results']['success_rate'] = (
                report['tinder_results']['successful'] / 
                report['tinder_results']['total_attempts']
            )
            report['tinder_results']['verification_rate'] = (
                report['tinder_results']['verified'] / 
                report['tinder_results']['total_attempts']
            )
        
        # Add warming statistics if enabled
        if self.config.warming_enabled:
            try:
                report['warming_stats'] = self.warming_manager.get_warming_statistics()
            except Exception as e:
                report['warming_stats'] = {'error': str(e)}
        
        return report
    
    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up automation resources...")
        
        try:
            # Stop warming scheduler
            if self.config.warming_enabled:
                self.warming_manager.stop_warming_scheduler()
            
            # Stop all emulators
            self.emulator_manager.stop_all_emulators()
            
            logger.info("✅ Cleanup completed")
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
    
    def run_full_automation(self) -> Dict[str, any]:
        """Run complete automation pipeline"""
        logger.info("🚀 Starting Tinder automation pipeline...")
        start_time = datetime.now()
        
        try:
            # Step 1: Verify prerequisites
            if not self.verify_prerequisites():
                raise RuntimeError("Prerequisites not met")
            
            # Step 2: Set up emulator pool
            emulators = self.setup_emulator_pool()
            if not emulators:
                raise RuntimeError("Failed to set up emulators")
            
            # Step 3: Create Snapchat accounts (if requested)
            snapchat_usernames = self.create_snapchat_accounts()
            
            # Step 4: Create Tinder accounts
            tinder_results = self.create_tinder_accounts(snapchat_usernames)
            
            # Step 5: Start account warming
            if self.config.warming_enabled:
                self.start_account_warming()
            
            # Step 6: Generate report
            report = self.generate_summary_report()
            
            # Save final report
            self._save_results('automation_report.json', [report])
            
            execution_time = datetime.now() - start_time
            logger.info(f"✅ Automation pipeline completed in {execution_time}")
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Automation pipeline failed: {e}")
            raise
        finally:
            self.cleanup()

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description='Tinder Account Automation System')
    
    # Account configuration
    parser.add_argument('--tinder-accounts', '-t', type=int, default=5, 
                       help='Number of Tinder accounts to create')
    parser.add_argument('--snapchat-accounts', '-s', type=int, default=0,
                       help='Number of Snapchat accounts to create')
    parser.add_argument('--emulators', '-e', type=int, default=3,
                       help='Number of Android emulators to use')
    
    # Behavior configuration
    parser.add_argument('--aggressiveness', '-a', type=float, default=0.3,
                       help='Aggressiveness level (0.1-1.0)')
    parser.add_argument('--no-warming', action='store_true',
                       help='Disable account warming')
    parser.add_argument('--parallel', action='store_true',
                       help='Create accounts in parallel')
    
    # Output configuration
    parser.add_argument('--output', '-o', default='./automation_results',
                       help='Output directory for results')
    parser.add_argument('--headless', action='store_true', default=True,
                       help='Run emulators in headless mode')
    
    args = parser.parse_args()
    
    # Create configuration
    config = AutomationConfig(
        tinder_account_count=args.tinder_accounts,
        snapchat_account_count=args.snapchat_accounts,
        emulator_count=args.emulators,
        aggressiveness_level=args.aggressiveness,
        warming_enabled=not args.no_warming,
        parallel_creation=args.parallel,
        output_directory=args.output,
        headless_emulators=args.headless
    )
    
    # Print configuration
    logger.info("Automation Configuration:")
    logger.info(f"  Tinder accounts: {config.tinder_account_count}")
    logger.info(f"  Snapchat accounts: {config.snapchat_account_count}")
    logger.info(f"  Emulators: {config.emulator_count}")
    logger.info(f"  Aggressiveness: {config.aggressiveness_level}")
    logger.info(f"  Warming enabled: {config.warming_enabled}")
    logger.info(f"  Parallel creation: {config.parallel_creation}")
    logger.info(f"  Output directory: {config.output_directory}")
    
    try:
        # Create orchestrator and run
        orchestrator = TinderAutomationOrchestrator(config)
        report = orchestrator.run_full_automation()
        
        # Print summary
        print("\n" + "="*50)
        print("AUTOMATION SUMMARY")
        print("="*50)
        print(f"Snapchat accounts: {report['snapchat_results']['successful']}/{report['snapchat_results']['total_attempts']} successful")
        print(f"Tinder accounts: {report['tinder_results']['successful']}/{report['tinder_results']['total_attempts']} successful")
        print(f"Verification rate: {report['tinder_results']['verification_rate']:.1%}")
        print(f"Results saved to: {config.output_directory}")
        print("="*50)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Automation interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Automation failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())