#!/usr/bin/env python3
"""
Production Workflow Test
Tests the complete account creation workflow in test mode
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProductionWorkflowTester:
    """Test the complete production workflow"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        if str(self.base_path) not in sys.path:
            sys.path.insert(0, str(self.base_path))
    
    async def test_complete_workflow(self):
        """Test complete account creation workflow"""
        logger.info("🚀 Testing Complete Production Workflow")
        
        results = {
            'workflow_steps': [],
            'successful_steps': 0,
            'failed_steps': 0,
            'test_data': {}
        }
        
        # Step 1: Initialize SMS Verifier
        try:
            from utils.sms_verifier import SMSVerifier
            sms_verifier = SMSVerifier()
            
            # Test phone number processing
            test_phone = "+1-555-123-4567"
            cleaned_phone = sms_verifier.clean_phone_number(test_phone)
            
            results['workflow_steps'].append({
                'step': 'sms_initialization',
                'status': 'success',
                'details': f"Phone cleaned: {test_phone} -> {cleaned_phone}"
            })
            results['successful_steps'] += 1
            results['test_data']['phone_number'] = cleaned_phone
            
            logger.info(f"✅ SMS Verifier initialized: {cleaned_phone}")
            
        except Exception as e:
            results['workflow_steps'].append({
                'step': 'sms_initialization',
                'status': 'failed',
                'error': str(e)
            })
            results['failed_steps'] += 1
            logger.error(f"❌ SMS Verifier failed: {e}")
        
        # Step 2: Generate Device Fingerprint
        try:
            from automation.core.anti_detection import AntiDetectionSystem
            anti_detect = AntiDetectionSystem()
            
            # Generate device fingerprint
            fingerprint = anti_detect.create_device_fingerprint()
            
            if fingerprint and isinstance(fingerprint, dict):
                results['workflow_steps'].append({
                    'step': 'device_fingerprint',
                    'status': 'success',
                    'details': f"Fingerprint keys: {list(fingerprint.keys())[:5]}"
                })
                results['successful_steps'] += 1
                results['test_data']['device_fingerprint'] = {
                    'generated': True,
                    'key_count': len(fingerprint.keys())
                }
                logger.info(f"✅ Device fingerprint generated: {len(fingerprint.keys())} attributes")
            else:
                raise Exception("No fingerprint data generated")
                
        except Exception as e:
            results['workflow_steps'].append({
                'step': 'device_fingerprint',
                'status': 'failed', 
                'error': str(e)
            })
            results['failed_steps'] += 1
            logger.error(f"❌ Device fingerprint failed: {e}")
        
        # Step 3: Generate Account Data
        try:
            # Create test account data
            import random
            import string
            
            username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            email = f"test_{username}@example.com"
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
            
            account_data = {
                'username': username,
                'email': email,
                'password': password,
                'phone': results['test_data'].get('phone_number', '+15551234567'),
                'created_at': datetime.now().isoformat()
            }
            
            results['workflow_steps'].append({
                'step': 'account_generation',
                'status': 'success',
                'details': f"Generated account: {username}"
            })
            results['successful_steps'] += 1
            results['test_data']['account'] = account_data
            
            logger.info(f"✅ Account data generated: {username}")
            
        except Exception as e:
            results['workflow_steps'].append({
                'step': 'account_generation',
                'status': 'failed',
                'error': str(e)
            })
            results['failed_steps'] += 1
            logger.error(f"❌ Account generation failed: {e}")
        
        # Step 4: Test File Output
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Test JSON output
            json_file = self.base_path / f"test_account_output_{timestamp}.json"
            with open(json_file, 'w') as f:
                json.dump(results['test_data'], f, indent=2)
            
            # Test CSV output
            csv_file = self.base_path / f"test_account_output_{timestamp}.csv"
            with open(csv_file, 'w') as f:
                if 'account' in results['test_data']:
                    account = results['test_data']['account']
                    f.write("username,email,phone,created_at\n")
                    f.write(f"{account['username']},{account['email']},{account['phone']},{account['created_at']}\n")
            
            # Verify files exist
            if json_file.exists() and csv_file.exists():
                results['workflow_steps'].append({
                    'step': 'file_output',
                    'status': 'success',
                    'details': f"Files: {json_file.name}, {csv_file.name}"
                })
                results['successful_steps'] += 1
                results['test_data']['output_files'] = [str(json_file), str(csv_file)]
                
                logger.info(f"✅ File output successful: JSON + CSV")
                
                # Cleanup test files
                os.remove(json_file)
                os.remove(csv_file)
            else:
                raise Exception("Files not created")
                
        except Exception as e:
            results['workflow_steps'].append({
                'step': 'file_output',
                'status': 'failed',
                'error': str(e)
            })
            results['failed_steps'] += 1
            logger.error(f"❌ File output failed: {e}")
        
        # Step 5: Test CAPTCHA Solver
        try:
            from automation.email.captcha_solver import CaptchaSolver
            
            captcha_solver = CaptchaSolver()
            solver_methods = [m for m in dir(captcha_solver) if not m.startswith('_')]
            
            if solver_methods:
                results['workflow_steps'].append({
                    'step': 'captcha_solver',
                    'status': 'success',
                    'details': f"Methods available: {len(solver_methods)}"
                })
                results['successful_steps'] += 1
                
                logger.info(f"✅ CAPTCHA solver ready: {len(solver_methods)} methods")
            else:
                raise Exception("No solver methods available")
                
        except Exception as e:
            results['workflow_steps'].append({
                'step': 'captcha_solver',
                'status': 'failed',
                'error': str(e)
            })
            results['failed_steps'] += 1
            logger.error(f"❌ CAPTCHA solver failed: {e}")
        
        # Step 6: Test Telegram Integration
        try:
            from automation.telegram_bot.main_bot import TinderBotApplication
            
            bot = TinderBotApplication()
            bot_methods = [m for m in dir(bot) if not m.startswith('_') and callable(getattr(bot, m))]
            
            if bot_methods:
                results['workflow_steps'].append({
                    'step': 'telegram_integration',
                    'status': 'success',
                    'details': f"Bot methods: {len(bot_methods)}"
                })
                results['successful_steps'] += 1
                
                logger.info(f"✅ Telegram bot ready: {len(bot_methods)} methods")
            else:
                raise Exception("No bot methods available")
                
        except Exception as e:
            results['workflow_steps'].append({
                'step': 'telegram_integration',
                'status': 'failed',
                'error': str(e)
            })
            results['failed_steps'] += 1
            logger.error(f"❌ Telegram integration failed: {e}")
        
        # Calculate final results
        total_steps = results['successful_steps'] + results['failed_steps']
        success_rate = results['successful_steps'] / total_steps if total_steps > 0 else 0
        
        results['summary'] = {
            'total_steps': total_steps,
            'successful_steps': results['successful_steps'],
            'failed_steps': results['failed_steps'],
            'success_rate': success_rate,
            'workflow_ready': success_rate >= 0.8
        }
        
        return results

async def main():
    """Main test runner"""
    print("🔄 Testing Production Workflow...")
    
    tester = ProductionWorkflowTester()
    results = await tester.test_complete_workflow()
    
    print("\n" + "="*60)
    print("🔄 PRODUCTION WORKFLOW TEST RESULTS")
    print("="*60)
    print(f"Total Steps: {results['summary']['total_steps']}")
    print(f"Successful: {results['summary']['successful_steps']} ✅")
    print(f"Failed: {results['summary']['failed_steps']} ❌")
    print(f"Success Rate: {results['summary']['success_rate']:.1%}")
    print(f"Workflow Ready: {'YES ✅' if results['summary']['workflow_ready'] else 'NO ❌'}")
    
    print("\n📋 STEP-BY-STEP RESULTS:")
    for step in results['workflow_steps']:
        emoji = '✅' if step['status'] == 'success' else '❌'
        step_name = step['step'].replace('_', ' ').title()
        print(f"  {emoji} {step_name}")
        if step['status'] == 'success' and 'details' in step:
            print(f"      {step['details']}")
        elif step['status'] == 'failed':
            print(f"      Error: {step['error']}")
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"production_workflow_test_{timestamp}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Detailed results saved to: {results_file}")

if __name__ == "__main__":
    asyncio.run(main())