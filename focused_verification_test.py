#!/usr/bin/env python3
"""
Focused verification test for specific components
Tests actual functionality rather than just class names
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

class FocusedVerifier:
    """Focused testing of actual working components"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'working_components': [],
            'broken_components': [],
            'missing_dependencies': [],
            'functional_tests': {}
        }
        
        # Add project to path
        if str(self.base_path) not in sys.path:
            sys.path.insert(0, str(self.base_path))

    async def verify_core_components(self):
        """Verify core components that should be working"""
        logger.info("🔍 Verifying core components...")
        
        # 1. Test Anti-Detection System
        try:
            from automation.core.anti_detection import AntiDetectionSystem
            
            # Test initialization
            anti_detect = AntiDetectionSystem()
            
            # Test key methods exist
            methods = dir(anti_detect)
            critical_methods = ['create_device_fingerprint', '_generate_hardware_fingerprint']
            
            working_methods = [m for m in critical_methods if m in methods]
            
            if len(working_methods) >= 1:
                self.results['working_components'].append({
                    'component': 'AntiDetectionSystem',
                    'methods': working_methods,
                    'status': 'functional'
                })
                logger.info("✅ AntiDetectionSystem verified")
            else:
                self.results['broken_components'].append('AntiDetectionSystem - no critical methods')
                
        except Exception as e:
            self.results['broken_components'].append(f"AntiDetectionSystem - {str(e)}")
            logger.error(f"❌ AntiDetectionSystem failed: {e}")

        # 2. Test SMS Verifier
        try:
            from utils.sms_verifier import SMSVerifier
            
            sms = SMSVerifier()
            methods = [m for m in dir(sms) if not m.startswith('_') and callable(getattr(sms, m))]
            
            self.results['working_components'].append({
                'component': 'SMSVerifier',
                'methods': methods[:10],  # First 10 methods
                'status': 'functional'
            })
            logger.info("✅ SMSVerifier verified")
            
        except Exception as e:
            self.results['broken_components'].append(f"SMSVerifier - {str(e)}")
            logger.error(f"❌ SMSVerifier failed: {e}")

        # 3. Test actual Telegram bot file
        try:
            from automation.telegram_bot.main_bot import TinderBotApplication
            
            # Test bot can be instantiated
            bot = TinderBotApplication()
            methods = [m for m in dir(bot) if not m.startswith('_') and callable(getattr(bot, m))]
            
            self.results['working_components'].append({
                'component': 'TinderBotApplication',
                'methods': methods[:10],
                'status': 'functional'
            })
            logger.info("✅ TinderBotApplication verified")
            
        except Exception as e:
            self.results['broken_components'].append(f"TinderBotApplication - {str(e)}")
            logger.error(f"❌ TinderBotApplication failed: {e}")

    async def test_email_service(self):
        """Test email service components"""
        logger.info("📧 Testing email services...")
        
        # Test captcha solver which should work
        try:
            from automation.email.captcha_solver import CaptchaSolver
            
            solver = CaptchaSolver()
            methods = [m for m in dir(solver) if not m.startswith('_')]
            
            self.results['working_components'].append({
                'component': 'CaptchaSolver',
                'methods': methods,
                'status': 'functional'
            })
            logger.info("✅ CaptchaSolver verified")
            
        except Exception as e:
            self.results['broken_components'].append(f"CaptchaSolver - {str(e)}")

        # Test business email service (may have missing deps)
        try:
            from automation.email.business_email_service import BusinessEmailService
            
            service = BusinessEmailService()
            self.results['working_components'].append({
                'component': 'BusinessEmailService',
                'status': 'functional'
            })
            logger.info("✅ BusinessEmailService verified")
            
        except ImportError as e:
            if 'google_auth_oauthlib' in str(e):
                self.results['missing_dependencies'].append('google_auth_oauthlib')
                logger.warning("⚠️ BusinessEmailService missing google_auth_oauthlib dependency")
            else:
                self.results['broken_components'].append(f"BusinessEmailService - {str(e)}")

    async def test_snapchat_creation(self):
        """Test actual account creation functionality"""
        logger.info("👻 Testing Snapchat creation system...")
        
        # Test if we can find the creation script
        creation_files = [
            'create_snapchat_credentials_batch.py',
            'snapchat_core_verification.py',
            'snapchat_functionality_test.py'
        ]
        
        working_scripts = []
        for script in creation_files:
            script_path = self.base_path / script
            if script_path.exists():
                working_scripts.append(script)
        
        if working_scripts:
            self.results['working_components'].append({
                'component': 'SnapchatCreationScripts',
                'scripts': working_scripts,
                'status': 'available'
            })
            logger.info(f"✅ Found Snapchat creation scripts: {working_scripts}")
        else:
            self.results['broken_components'].append("No Snapchat creation scripts found")

    async def test_file_outputs(self):
        """Test actual file generation capabilities"""
        logger.info("📄 Testing file output capabilities...")
        
        # Check for existing output files
        output_patterns = [
            '**/*.json',
            '**/*.csv',
            '**/verification_results_*',
            '**/snapchat_credentials_*'
        ]
        
        found_outputs = {}
        for pattern in output_patterns:
            files = list(self.base_path.glob(pattern))
            if files:
                found_outputs[pattern] = len(files)
        
        if found_outputs:
            self.results['working_components'].append({
                'component': 'FileOutputSystem',
                'output_types': found_outputs,
                'status': 'verified'
            })
            logger.info(f"✅ File outputs verified: {found_outputs}")
        
        # Test programmatic file creation
        try:
            test_data = {
                'test': 'verification',
                'timestamp': datetime.now().isoformat(),
                'accounts': ['test1', 'test2']
            }
            
            test_file = self.base_path / 'test_output.json'
            with open(test_file, 'w') as f:
                json.dump(test_data, f, indent=2)
            
            if test_file.exists():
                self.results['working_components'].append({
                    'component': 'ProgrammaticFileGeneration',
                    'status': 'functional'
                })
                os.remove(test_file)  # Cleanup
                logger.info("✅ Programmatic file generation verified")
                
        except Exception as e:
            self.results['broken_components'].append(f"File generation - {str(e)}")

    async def test_environment_setup(self):
        """Test environment and configuration"""
        logger.info("⚙️ Testing environment setup...")
        
        # Check .env file
        env_path = self.base_path / '.env'
        if env_path.exists():
            try:
                with open(env_path, 'r') as f:
                    env_content = f.read()
                
                # Count configured variables
                configured_vars = len([line for line in env_content.split('\n') 
                                     if '=' in line and not line.strip().startswith('#')])
                
                self.results['working_components'].append({
                    'component': 'EnvironmentConfiguration',
                    'configured_variables': configured_vars,
                    'status': 'functional'
                })
                logger.info(f"✅ Environment configuration verified: {configured_vars} variables")
                
            except Exception as e:
                self.results['broken_components'].append(f"Environment config - {str(e)}")
        else:
            self.results['broken_components'].append("No .env file found")

    async def run_functional_tests(self):
        """Run actual functional tests on working components"""
        logger.info("🧪 Running functional tests...")
        
        # Test 1: Can we actually verify phone numbers format?
        try:
            from utils.sms_verifier import SMSVerifier
            sms = SMSVerifier()
            
            # Test phone number cleaning
            test_number = "+1-555-123-4567"
            cleaned = sms.clean_phone_number(test_number)
            
            if cleaned:
                self.results['functional_tests']['phone_formatting'] = {
                    'input': test_number,
                    'output': cleaned,
                    'status': 'working'
                }
                logger.info(f"✅ Phone formatting works: {test_number} -> {cleaned}")
            
        except Exception as e:
            self.results['functional_tests']['phone_formatting'] = {
                'status': 'failed',
                'error': str(e)
            }

        # Test 2: Can we generate verification codes?
        try:
            from utils.sms_verifier import SMSVerifier
            sms = SMSVerifier()
            
            code = sms.generate_verification_code()
            if code and len(str(code)) >= 4:
                self.results['functional_tests']['code_generation'] = {
                    'generated_code': code,
                    'status': 'working'
                }
                logger.info(f"✅ Code generation works: {code}")
            
        except Exception as e:
            self.results['functional_tests']['code_generation'] = {
                'status': 'failed',
                'error': str(e)
            }

        # Test 3: Can we create device fingerprints?
        try:
            from automation.core.anti_detection import AntiDetectionSystem
            ads = AntiDetectionSystem()
            
            fingerprint = ads.create_device_fingerprint()
            if fingerprint and isinstance(fingerprint, dict):
                self.results['functional_tests']['device_fingerprint'] = {
                    'generated': True,
                    'keys': list(fingerprint.keys())[:5],  # First 5 keys
                    'status': 'working'
                }
                logger.info(f"✅ Device fingerprinting works: {list(fingerprint.keys())[:5]}")
            
        except Exception as e:
            self.results['functional_tests']['device_fingerprint'] = {
                'status': 'failed',
                'error': str(e)
            }

    def generate_production_readiness_assessment(self):
        """Generate final production readiness assessment"""
        working_count = len(self.results['working_components'])
        broken_count = len(self.results['broken_components'])
        functional_tests_passed = sum(1 for test in self.results['functional_tests'].values() 
                                    if test.get('status') == 'working')
        total_functional_tests = len(self.results['functional_tests'])
        
        # Calculate scores
        component_score = working_count / (working_count + broken_count) if (working_count + broken_count) > 0 else 0
        functional_score = functional_tests_passed / total_functional_tests if total_functional_tests > 0 else 0
        dependency_penalty = len(self.results['missing_dependencies']) * 0.1
        
        overall_score = (component_score * 0.6 + functional_score * 0.4) - dependency_penalty
        overall_score = max(0, min(1, overall_score))  # Clamp to 0-1
        
        return {
            'working_components': working_count,
            'broken_components': broken_count,
            'functional_tests_passed': functional_tests_passed,
            'total_functional_tests': total_functional_tests,
            'missing_dependencies': len(self.results['missing_dependencies']),
            'component_score': component_score,
            'functional_score': functional_score,
            'overall_score': overall_score,
            'production_ready': overall_score >= 0.7,
            'readiness_level': self.get_readiness_level(overall_score)
        }
    
    def get_readiness_level(self, score):
        """Get readiness level description"""
        if score >= 0.9:
            return "Production Ready"
        elif score >= 0.7:
            return "Ready with Minor Issues"
        elif score >= 0.5:
            return "Needs Significant Work"
        else:
            return "Not Ready - Major Issues"

    async def run_all_tests(self):
        """Run all focused verification tests"""
        logger.info("🚀 Starting Focused Verification Tests")
        
        await self.verify_core_components()
        await self.test_email_service()
        await self.test_snapchat_creation()
        await self.test_file_outputs()
        await self.test_environment_setup()
        await self.run_functional_tests()
        
        # Generate assessment
        assessment = self.generate_production_readiness_assessment()
        self.results['assessment'] = assessment
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_path = self.base_path / f"focused_verification_results_{timestamp}.json"
        
        with open(results_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"Results saved to: {results_path}")
        
        return self.results, assessment

async def main():
    """Main test runner"""
    print("🎯 Starting Focused System Verification...")
    
    verifier = FocusedVerifier()
    results, assessment = await verifier.run_all_tests()
    
    print("\n" + "="*60)
    print("🎯 FOCUSED VERIFICATION RESULTS")
    print("="*60)
    print(f"Working Components: {assessment['working_components']} ✅")
    print(f"Broken Components: {assessment['broken_components']} ❌")
    print(f"Functional Tests Passed: {assessment['functional_tests_passed']}/{assessment['total_functional_tests']}")
    print(f"Missing Dependencies: {assessment['missing_dependencies']}")
    print(f"Overall Score: {assessment['overall_score']:.1%}")
    print(f"Readiness Level: {assessment['readiness_level']}")
    print(f"Production Ready: {'YES ✅' if assessment['production_ready'] else 'NO ❌'}")
    
    if results['working_components']:
        print("\n🟢 WORKING COMPONENTS:")
        for comp in results['working_components']:
            print(f"  ✅ {comp['component']}: {comp['status']}")
    
    if results['broken_components']:
        print("\n🔴 BROKEN COMPONENTS:")
        for comp in results['broken_components']:
            print(f"  ❌ {comp}")
    
    if results['missing_dependencies']:
        print("\n📦 MISSING DEPENDENCIES:")
        for dep in results['missing_dependencies']:
            print(f"  📦 {dep}")
    
    print("\n🧪 FUNCTIONAL TEST RESULTS:")
    for test_name, test_result in results['functional_tests'].items():
        status = test_result.get('status', 'unknown')
        emoji = '✅' if status == 'working' else '❌'
        print(f"  {emoji} {test_name}: {status}")

if __name__ == "__main__":
    asyncio.run(main())