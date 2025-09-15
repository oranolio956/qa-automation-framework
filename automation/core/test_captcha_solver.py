#!/usr/bin/env python3
"""
CAPTCHA Solver Integration Test Script

Tests the real CAPTCHA solving API integration for legitimate security research.
This script verifies provider connectivity, balance checking, and solving capabilities.
"""

import os
import sys
import time
import base64
import logging
from typing import Dict, List
from PIL import Image, ImageDraw, ImageFont
import io

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from anti_detection import CaptchaHandler, CaptchaProvider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CaptchaSolverTester:
    """Test suite for CAPTCHA solver integration"""
    
    def __init__(self):
        self.handler = CaptchaHandler()
        self.test_results = {}
        
    def create_test_captcha(self, text: str = "TEST123", format: str = "PNG") -> str:
        """Create a simple test CAPTCHA image for testing"""
        
        # Create image with text
        img = Image.new('RGB', (200, 80), color='white')
        draw = ImageDraw.Draw(img)
        
        try:
            # Try to use a system font
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 36)
        except:
            # Fallback to default font
            font = ImageFont.load_default()
        
        # Add some noise and distortion for realism
        import random
        
        # Draw background noise
        for _ in range(100):
            x = random.randint(0, 200)
            y = random.randint(0, 80)
            draw.point((x, y), fill='lightgray')
        
        # Draw text with slight offset
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        x = (200 - text_width) // 2 + random.randint(-10, 10)
        y = (80 - text_height) // 2 + random.randint(-5, 5)
        
        draw.text((x, y), text, fill='black', font=font)
        
        # Add some distortion lines
        for _ in range(5):
            x1, y1 = random.randint(0, 200), random.randint(0, 80)
            x2, y2 = random.randint(0, 200), random.randint(0, 80)
            draw.line([(x1, y1), (x2, y2)], fill='gray', width=1)
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format=format)
        image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return image_data
    
    def test_provider_configuration(self) -> Dict[str, any]:
        """Test provider configuration and API key availability"""
        
        logger.info("Testing provider configuration...")
        
        config_results = {}
        
        for provider in CaptchaProvider:
            api_key_env = self.handler.providers[provider]['api_key_env']
            api_key = os.environ.get(api_key_env)
            
            config_results[provider.value] = {
                'api_key_configured': bool(api_key),
                'api_key_env_var': api_key_env,
                'cost_per_solve': self.handler.providers[provider]['cost_per_solve']
            }
            
            if api_key:
                logger.info(f"✓ {provider.value}: API key configured")
            else:
                logger.warning(f"✗ {provider.value}: No API key found in {api_key_env}")
        
        return config_results
    
    def test_balance_checking(self) -> Dict[str, any]:
        """Test balance checking for configured providers"""
        
        logger.info("Testing balance checking...")
        
        balance_results = {}
        
        for provider in CaptchaProvider:
            api_key = os.environ.get(self.handler.providers[provider]['api_key_env'])
            
            if not api_key:
                balance_results[provider.value] = {
                    'configured': False,
                    'error': 'No API key configured'
                }
                continue
            
            logger.info(f"Checking balance for {provider.value}...")
            
            try:
                balance_info = self.handler.get_balance(provider)
                balance_results[provider.value] = balance_info
                
                if balance_info.get('success'):
                    logger.info(f"✓ {provider.value}: Balance ${balance_info.get('balance', 0):.4f}")
                else:
                    logger.error(f"✗ {provider.value}: {balance_info.get('error')}")
                    
            except Exception as e:
                balance_results[provider.value] = {
                    'configured': True,
                    'success': False,
                    'error': str(e)
                }
                logger.error(f"✗ {provider.value}: Exception - {e}")
        
        return balance_results
    
    def test_captcha_solving(self, test_text: str = "ABC123") -> Dict[str, any]:
        """Test actual CAPTCHA solving with a generated test image"""
        
        logger.info(f"Testing CAPTCHA solving with text: {test_text}")
        
        # Create test CAPTCHA
        test_image_b64 = self.create_test_captcha(test_text)
        
        captcha_data = {
            'detected': True,
            'type': 'text_challenge',
            'image_base64': test_image_b64,
            'numeric_only': False,
            'min_length': len(test_text),
            'max_length': len(test_text)
        }
        
        # Test solving
        start_time = time.time()
        result = self.handler._call_captcha_solver_api(captcha_data)
        solve_time = time.time() - start_time
        
        solve_results = {
            'test_text': test_text,
            'solve_time': solve_time,
            'result': result
        }
        
        if result.get('success'):
            solution = result.get('solution', '').upper()
            expected = test_text.upper()
            accuracy = self._calculate_accuracy(solution, expected)
            
            solve_results.update({
                'solution': solution,
                'expected': expected,
                'accuracy': accuracy,
                'provider_used': result.get('provider'),
                'cost': result.get('cost', 0)
            })
            
            if accuracy >= 0.8:  # 80% accuracy threshold
                logger.info(f"✓ CAPTCHA solved: '{solution}' (expected: '{expected}') - {accuracy:.1%} accuracy")
            else:
                logger.warning(f"⚠ Low accuracy: '{solution}' (expected: '{expected}') - {accuracy:.1%} accuracy")
        else:
            logger.error(f"✗ CAPTCHA solving failed: {result.get('error')}")
        
        return solve_results
    
    def _calculate_accuracy(self, solution: str, expected: str) -> float:
        """Calculate character-level accuracy between solution and expected text"""
        
        if not solution or not expected:
            return 0.0
        
        # Simple character matching
        correct = sum(1 for i, char in enumerate(solution) if i < len(expected) and char == expected[i])
        return correct / len(expected)
    
    def test_cost_limits(self) -> Dict[str, any]:
        """Test daily cost limit enforcement"""
        
        logger.info("Testing cost limit enforcement...")
        
        original_limit = self.handler.daily_spend_limit
        original_spend = self.handler.current_daily_spend
        
        # Temporarily set very low limit for testing
        self.handler.daily_spend_limit = 0.01  # $0.01
        self.handler.current_daily_spend = 0.005  # $0.005
        
        # Try to solve - should work
        test_image = self.create_test_captcha("TEST1")
        captcha_data = {'image_base64': test_image}
        
        result1 = self.handler._call_captcha_solver_api(captcha_data)
        
        # Set spend at limit
        self.handler.current_daily_spend = 0.011  # Over limit
        
        # Try again - should fail
        result2 = self.handler._call_captcha_solver_api(captcha_data)
        
        # Restore original values
        self.handler.daily_spend_limit = original_limit
        self.handler.current_daily_spend = original_spend
        
        cost_results = {
            'under_limit_success': result1.get('success', False),
            'over_limit_blocked': not result2.get('success', True),
            'limit_error_message': result2.get('error', '')
        }
        
        if cost_results['under_limit_success'] and cost_results['over_limit_blocked']:
            logger.info("✓ Cost limits working correctly")
        else:
            logger.error("✗ Cost limits not working properly")
        
        return cost_results
    
    def run_comprehensive_test(self) -> Dict[str, any]:
        """Run comprehensive test suite"""
        
        logger.info("Starting comprehensive CAPTCHA solver test...")
        logger.info("=" * 60)
        
        results = {}
        
        try:
            # Test 1: Configuration
            results['configuration'] = self.test_provider_configuration()
            logger.info("")
            
            # Test 2: Balance checking
            results['balances'] = self.test_balance_checking()
            logger.info("")
            
            # Test 3: Cost limits
            results['cost_limits'] = self.test_cost_limits()
            logger.info("")
            
            # Test 4: Actual solving (only if providers are configured)
            configured_providers = [p for p, info in results['configuration'].items() 
                                 if info['api_key_configured']]
            
            if configured_providers:
                logger.info("Testing actual CAPTCHA solving...")
                results['solving'] = self.test_captcha_solving()
            else:
                logger.warning("Skipping solve test - no providers configured")
                results['solving'] = {'skipped': True, 'reason': 'No API keys configured'}
            
            # Test 5: Provider statistics
            results['provider_stats'] = self.handler.get_provider_stats()
            
        except Exception as e:
            logger.error(f"Test suite failed: {e}")
            results['error'] = str(e)
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("Test Results Summary:")
        self._print_summary(results)
        
        return results
    
    def _print_summary(self, results: Dict[str, any]):
        """Print test results summary"""
        
        # Configuration summary
        if 'configuration' in results:
            configured_count = sum(1 for info in results['configuration'].values() 
                                if info['api_key_configured'])
            total_providers = len(results['configuration'])
            logger.info(f"Providers configured: {configured_count}/{total_providers}")
        
        # Balance summary
        if 'balances' in results:
            balance_working = sum(1 for info in results['balances'].values() 
                               if info.get('success', False))
            logger.info(f"Balance checks working: {balance_working} providers")
        
        # Cost limits
        if 'cost_limits' in results:
            limits_ok = (results['cost_limits'].get('under_limit_success', False) and 
                        results['cost_limits'].get('over_limit_blocked', False))
            logger.info(f"Cost limits working: {'✓' if limits_ok else '✗'}")
        
        # Solving test
        if 'solving' in results and not results['solving'].get('skipped'):
            solve_success = results['solving'].get('result', {}).get('success', False)
            if solve_success:
                accuracy = results['solving'].get('accuracy', 0)
                provider = results['solving'].get('provider_used', 'Unknown')
                cost = results['solving'].get('cost', 0)
                logger.info(f"Solving test: ✓ ({accuracy:.1%} accuracy, {provider}, ${cost:.4f})")
            else:
                error = results['solving'].get('result', {}).get('error', 'Unknown error')
                logger.info(f"Solving test: ✗ ({error})")
        
        # Daily spend info
        if 'provider_stats' in results:
            daily_spend = results['provider_stats'].get('daily_spend', 0)
            daily_limit = results['provider_stats'].get('daily_limit', 0)
            logger.info(f"Daily spend: ${daily_spend:.4f} / ${daily_limit:.2f}")

def main():
    """Main test runner"""
    
    print("CAPTCHA Solver Integration Test")
    print("==============================")
    print("")
    print("This script tests the CAPTCHA solving API integration.")
    print("Ensure you have configured at least one provider in your environment:")
    print("")
    for provider in CaptchaProvider:
        api_key_env = CaptchaHandler().providers[provider]['api_key_env']
        print(f"  {provider.value}: {api_key_env}")
    print("")
    
    # Load environment variables if .env file exists
    env_file = os.path.join(os.path.dirname(__file__), '.env.captcha')
    if os.path.exists(env_file):
        print(f"Loading environment from: {env_file}")
        from dotenv import load_dotenv
        load_dotenv(env_file)
    else:
        print(f"No .env.captcha file found at: {env_file}")
        print("Copy .env.captcha.template to .env.captcha and configure your API keys.")
    
    print("")
    
    # Run tests
    tester = CaptchaSolverTester()
    results = tester.run_comprehensive_test()
    
    # Save results
    import json
    results_file = f"captcha_test_results_{int(time.time())}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print("")
    print(f"Test results saved to: {results_file}")
    
    # Exit with appropriate code
    if results.get('error'):
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()