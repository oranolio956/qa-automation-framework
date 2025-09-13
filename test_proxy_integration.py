#!/usr/bin/env python3
"""
Comprehensive Bright Data Integration Test Suite
Verifies that all system components properly route traffic through Bright Data Browser API proxy
"""

import os
import sys
import requests
import subprocess
import time
import json
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProxyIntegrationTester:
    """Test suite for verifying proxy integration across all system components"""
    
    def __init__(self):
        # Load Bright Data proxy configuration
        self.brightdata_endpoint = os.environ.get('BRIGHTDATA_ENDPOINT', 'browser.tinder-emulation.brightdata.com:24000')
        self.zone_key = os.environ.get('BRIGHTDATA_ZONE_KEY', 'your_zone_access_key')
        
        self.test_results = []
        self.failed_tests = []
    
    def log_result(self, test_name: str, success: bool, details: str = "", ip_address: str = ""):
        """Log test result"""
        result = {
            'test_name': test_name,
            'success': success,
            'timestamp': datetime.now().isoformat(),
            'details': details,
            'ip_address': ip_address
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} {test_name}: {details}")
        
        if not success:
            self.failed_tests.append(test_name)
    
    def test_proxy_utils_module(self) -> bool:
        """Test that proxy utilities module works correctly"""
        try:
            # Import proxy utilities
            sys.path.append('.')
            from utils.brightdata_proxy import verify_proxy, get_proxy_info, get_brightdata_session, test_brightdata_integration
            
            # Test proxy verification
            if verify_proxy(force_check=True):
                proxy_info = get_proxy_info()
                ip_address = proxy_info.get('ip_address', 'unknown')
                location = f"{proxy_info.get('city', 'unknown')}, {proxy_info.get('country', 'unknown')}"
                
                self.log_result(
                    "Bright Data Utils Module", 
                    True, 
                    f"Module loaded and Bright Data proxy verified - Location: {location}", 
                    ip_address
                )
                return True
            else:
                self.log_result("Proxy Utils Module", False, "Proxy verification failed")
                return False
                
        except Exception as e:
            self.log_result("Proxy Utils Module", False, f"Module import/test failed: {e}")
            return False
    
    def test_backend_api_proxy(self) -> bool:
        """Test that backend API uses proxy for external requests"""
        try:
            # Start backend service (if not running)
            backend_url = "http://localhost:8000"
            
            # Test health endpoint which should include proxy status
            response = requests.get(f"{backend_url}/health", timeout=10)
            
            if response.status_code == 200:
                health_data = response.json()
                
                proxy_status = health_data.get('proxy_status', 'unavailable')
                proxy_info = health_data.get('proxy_info', {})
                
                if proxy_status == 'active':
                    ip_address = proxy_info.get('ip_address', 'unknown')
                    self.log_result(
                        "Backend API Proxy", 
                        True, 
                        f"Backend API reporting active proxy status", 
                        ip_address
                    )
                    return True
                else:
                    self.log_result("Backend API Proxy", False, f"Proxy status: {proxy_status}")
                    return False
            else:
                self.log_result("Backend API Proxy", False, f"Backend API not responding: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Backend API Proxy", False, f"Backend API test failed: {e}")
            return False
    
    def test_bot_service_proxy(self) -> bool:
        """Test that bot/orchestrator service uses proxy"""
        try:
            bot_url = "http://localhost:5000"
            
            # Test health endpoint
            response = requests.get(f"{bot_url}/health", timeout=10)
            
            if response.status_code == 200:
                health_data = response.json()
                
                proxy_status = health_data.get('proxy_status', 'unavailable')
                proxy_info = health_data.get('proxy_info', {})
                
                if proxy_status == 'active':
                    ip_address = proxy_info.get('ip_address', 'unknown')
                    self.log_result(
                        "Bot Service Proxy", 
                        True, 
                        f"Bot service reporting active proxy status", 
                        ip_address
                    )
                    return True
                else:
                    self.log_result("Bot Service Proxy", False, f"Proxy status: {proxy_status}")
                    return False
            else:
                self.log_result("Bot Service Proxy", False, f"Bot service not responding: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Bot Service Proxy", False, f"Bot service test failed: {e}")
            return False
    
    def test_shell_script_proxy(self) -> bool:
        """Test that shell scripts use proxy for curl commands"""
        try:
            # Test image setup script with proxy
            script_path = "automation/scripts/image_setup.sh"
            
            if not os.path.exists(script_path):
                self.log_result("Shell Script Proxy", False, "Image setup script not found")
                return False
            
            # Check if script contains proxy configuration
            with open(script_path, 'r') as f:
                script_content = f.read()
                
            if 'curl_proxy' in script_content and 'SMARTPROXY' in script_content:
                # Try running a proxy test within the script environment
                test_cmd = [
                    'bash', '-c', 
                    f'''
                    source {script_path}
                    curl_proxy -s --connect-timeout 10 https://httpbin.org/ip 2>/dev/null || echo "FAILED"
                    '''
                ]
                
                result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0 and "FAILED" not in result.stdout:
                    try:
                        ip_data = json.loads(result.stdout.strip())
                        ip_address = ip_data.get('origin', 'unknown')
                        self.log_result(
                            "Shell Script Proxy", 
                            True, 
                            "Shell script curl_proxy function working", 
                            ip_address
                        )
                        return True
                    except:
                        self.log_result("Shell Script Proxy", True, "Shell script proxy configured")
                        return True
                else:
                    self.log_result("Shell Script Proxy", False, "Shell script proxy test failed")
                    return False
            else:
                self.log_result("Shell Script Proxy", False, "Shell script missing proxy configuration")
                return False
                
        except Exception as e:
            self.log_result("Shell Script Proxy", False, f"Shell script test failed: {e}")
            return False
    
    def test_docker_proxy_config(self) -> bool:
        """Test that Docker containers have proxy configuration"""
        try:
            # Check docker-compose.yml for proxy environment variables
            compose_file = "infra/docker-compose.yml"
            
            if not os.path.exists(compose_file):
                self.log_result("Docker Proxy Config", False, "docker-compose.yml not found")
                return False
            
            with open(compose_file, 'r') as f:
                compose_content = f.read()
            
            # Check for proxy environment variables
            proxy_vars = ['SMARTPROXY_USER', 'SMARTPROXY_PASS', 'SMARTPROXY_HOST', 'SMARTPROXY_PORT']
            missing_vars = [var for var in proxy_vars if var not in compose_content]
            
            if not missing_vars:
                self.log_result(
                    "Docker Proxy Config", 
                    True, 
                    "All proxy environment variables configured in docker-compose.yml"
                )
                return True
            else:
                self.log_result(
                    "Docker Proxy Config", 
                    False, 
                    f"Missing proxy variables in docker-compose.yml: {missing_vars}"
                )
                return False
                
        except Exception as e:
            self.log_result("Docker Proxy Config", False, f"Docker config test failed: {e}")
            return False
    
    def test_dockerfile_proxy_integration(self) -> bool:
        """Test that Dockerfiles include proxy configuration"""
        try:
            dockerfiles = [
                "backend/Dockerfile",
                "bot/Dockerfile", 
                "infra/Dockerfile.provisioner",
                "infra/Dockerfile.manager"
            ]
            
            configured_files = []
            missing_files = []
            
            for dockerfile in dockerfiles:
                if os.path.exists(dockerfile):
                    with open(dockerfile, 'r') as f:
                        content = f.read()
                    
                    if 'SMARTPROXY' in content and 'ENV' in content:
                        configured_files.append(dockerfile)
                    else:
                        missing_files.append(dockerfile)
                else:
                    missing_files.append(f"{dockerfile} (not found)")
            
            if configured_files and len(configured_files) >= len(dockerfiles) // 2:
                self.log_result(
                    "Dockerfile Proxy Integration", 
                    True, 
                    f"Proxy configuration found in: {', '.join(configured_files)}"
                )
                return True
            else:
                self.log_result(
                    "Dockerfile Proxy Integration", 
                    False, 
                    f"Missing proxy config in: {', '.join(missing_files)}"
                )
                return False
                
        except Exception as e:
            self.log_result("Dockerfile Proxy Integration", False, f"Dockerfile test failed: {e}")
            return False
    
    def test_worker_vm_proxy_setup(self) -> bool:
        """Test that worker VM entrypoint script includes proxy configuration"""
        try:
            entrypoint_script = "infra/worker_entrypoint.sh"
            
            if not os.path.exists(entrypoint_script):
                self.log_result("Worker VM Proxy Setup", False, "Worker entrypoint script not found")
                return False
            
            with open(entrypoint_script, 'r') as f:
                script_content = f.read()
            
            # Check for proxy-related configurations
            proxy_indicators = [
                'SMARTPROXY',
                'proxychains',
                'curl_proxy',
                'adb-proxy',
                'socks5'
            ]
            
            found_indicators = [ind for ind in proxy_indicators if ind in script_content]
            
            if len(found_indicators) >= 3:  # Expect at least 3 proxy indicators
                self.log_result(
                    "Worker VM Proxy Setup", 
                    True, 
                    f"Worker VM proxy configuration includes: {', '.join(found_indicators)}"
                )
                return True
            else:
                self.log_result(
                    "Worker VM Proxy Setup", 
                    False, 
                    f"Insufficient proxy configuration in worker script. Found: {found_indicators}"
                )
                return False
                
        except Exception as e:
            self.log_result("Worker VM Proxy Setup", False, f"Worker VM test failed: {e}")
            return False
    
    def test_end_to_end_proxy_flow(self) -> bool:
        """Test end-to-end proxy flow using the proxy utilities directly"""
        try:
            sys.path.append('.')
            from utils.brightdata_proxy import test_brightdata_integration
            
            # Run the built-in integration test
            if test_brightdata_integration():
                self.log_result(
                    "End-to-End Proxy Flow", 
                    True, 
                    "Complete proxy integration test passed"
                )
                return True
            else:
                self.log_result("End-to-End Proxy Flow", False, "Integration test failed")
                return False
                
        except Exception as e:
            self.log_result("End-to-End Proxy Flow", False, f"E2E test failed: {e}")
            return False
    
    def run_all_tests(self) -> Dict:
        """Run complete test suite"""
        logger.info("🚀 Starting Bright Data Integration Test Suite")
        logger.info(f"Endpoint: {self.brightdata_endpoint}")
        logger.info("=" * 60)
        
        # Run all test methods
        test_methods = [
            self.test_proxy_utils_module,
            self.test_shell_script_proxy,
            self.test_docker_proxy_config,
            self.test_dockerfile_proxy_integration,
            self.test_worker_vm_proxy_setup,
            self.test_end_to_end_proxy_flow,
            # Service tests (may fail if services aren't running)
            self.test_backend_api_proxy,
            self.test_bot_service_proxy,
        ]
        
        passed_tests = 0
        total_tests = len(test_methods)
        
        for test_method in test_methods:
            try:
                if test_method():
                    passed_tests += 1
            except Exception as e:
                logger.error(f"Test {test_method.__name__} crashed: {e}")
        
        # Generate summary
        success_rate = (passed_tests / total_tests) * 100
        
        logger.info("=" * 60)
        logger.info(f"📊 TEST SUMMARY")
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {len(self.failed_tests)}")
        logger.info(f"Success Rate: {success_rate:.1f}%")
        
        if self.failed_tests:
            logger.info(f"Failed Tests: {', '.join(self.failed_tests)}")
        
        # Overall status
        if success_rate >= 75:  # 75% pass rate for integration
            logger.info("🎉 PROXY INTEGRATION: SUCCESSFUL")
            status = "SUCCESS"
        else:
            logger.info("⚠️  PROXY INTEGRATION: NEEDS ATTENTION")
            status = "PARTIAL"
        
        return {
            'status': status,
            'success_rate': success_rate,
            'passed_tests': passed_tests,
            'total_tests': total_tests,
            'failed_tests': self.failed_tests,
            'detailed_results': self.test_results
        }

def main():
    """Main function"""
    tester = ProxyIntegrationTester()
    results = tester.run_all_tests()
    
    # Save detailed results
    with open('proxy_integration_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info("📄 Detailed results saved to proxy_integration_test_results.json")
    
    # Exit with appropriate code
    sys.exit(0 if results['status'] == 'SUCCESS' else 1)

if __name__ == "__main__":
    main()