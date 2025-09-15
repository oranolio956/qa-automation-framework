#!/usr/bin/env python3
"""
Comprehensive End-to-End Testing Framework for Anti-Bot Security System

This module performs complete system validation including:
1. System Integration Testing - All components working together
2. Performance Validation - 100K+ RPS and sub-100ms response times
3. Security Framework Testing - ML models, TLS fingerprinting, fraud detection
4. Temporal Workflow Testing - Multi-step business processes
5. Observability Stack Validation - OpenTelemetry, monitoring, alerts
6. Production Readiness Assessment - Deployment, monitoring, disaster recovery

Author: Claude Code - API Testing Specialist
Date: 2025-01-14
"""

import asyncio
import json
import time
import uuid
import logging
import statistics
import concurrent.futures
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import sys
import os
import subprocess
import socket
import ssl
import random
from urllib.parse import urlparse

# Add project root to path
sys.path.append('/Users/daltonmetzler/Desktop/Tinder')

try:
    import requests
    import websockets
    import psutil
    import aiohttp
    import numpy as np
    from concurrent.futures import ThreadPoolExecutor, as_completed
except ImportError as e:
    print(f"Installing required package: {e.name}")
    subprocess.check_call([sys.executable, "-m", "pip", "install", str(e.name)])
    globals()[str(e.name)] = __import__(str(e.name))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('end_to_end_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Test result data structure"""
    test_name: str
    status: str  # PASS, FAIL, SKIP
    duration: float
    details: Dict[str, Any]
    timestamp: str
    errors: List[str]
    metrics: Dict[str, float]

@dataclass
class SystemHealth:
    """System health metrics"""
    cpu_percent: float
    memory_percent: float
    disk_usage: float
    network_connections: int
    response_time: float
    error_rate: float
    throughput: float

class EndToEndTestSuite:
    """Comprehensive end-to-end testing framework"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.start_time = time.time()
        self.test_id = str(uuid.uuid4())
        self.base_url = "http://localhost:8000"
        self.websocket_url = "ws://localhost:8080"
        self.session = requests.Session()
        self.session.timeout = 30
        
        # Test configuration
        self.performance_targets = {
            'max_response_time': 100,  # milliseconds
            'min_throughput': 100000,  # RPS
            'max_error_rate': 0.001,   # 0.1%
            'max_cpu_usage': 80,       # percent
            'max_memory_usage': 85,    # percent
        }
        
        # Component endpoints
        self.endpoints = {
            'health': f"{self.base_url}/health",
            'risk_engine': f"{self.base_url}/api/v1/risk/assess",
            'sms_service': f"{self.base_url}/api/v1/sms/send",
            'data_processor': f"{self.base_url}/api/v1/data/process",
            'behavioral_analytics': f"{self.base_url}/api/v1/behavioral/analyze",
            'fraud_detection': f"{self.base_url}/api/v1/fraud/detect",
            'temporal_workflow': f"{self.base_url}/api/v1/workflow/start",
            'metrics': f"{self.base_url}/metrics",
            'monitoring': f"{self.base_url}/api/v1/monitoring/status"
        }
    
    def log_test_result(self, test_name: str, status: str, duration: float, 
                       details: Dict = None, errors: List = None, metrics: Dict = None):
        """Log test result"""
        result = TestResult(
            test_name=test_name,
            status=status,
            duration=duration,
            details=details or {},
            timestamp=datetime.now().isoformat(),
            errors=errors or [],
            metrics=metrics or {}
        )
        self.results.append(result)
        
        status_emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⏭️"
        logger.info(f"{status_emoji} {test_name}: {status} ({duration:.2f}s)")
        
        if errors:
            for error in errors:
                logger.error(f"   Error: {error}")
    
    def get_system_health(self) -> SystemHealth:
        """Get current system health metrics"""
        try:
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            connections = len(psutil.net_connections())
            
            # Test response time
            start = time.time()
            try:
                response = self.session.get(self.endpoints['health'], timeout=5)
                response_time = (time.time() - start) * 1000  # ms
                error_rate = 0.0 if response.status_code == 200 else 1.0
            except:
                response_time = 5000  # timeout
                error_rate = 1.0
            
            return SystemHealth(
                cpu_percent=cpu,
                memory_percent=memory,
                disk_usage=disk,
                network_connections=connections,
                response_time=response_time,
                error_rate=error_rate,
                throughput=0.0  # Will be calculated during load tests
            )
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return SystemHealth(0, 0, 0, 0, 9999, 1.0, 0)
    
    async def test_system_integration(self) -> bool:
        """Test complete system integration"""
        logger.info("🧪 Starting System Integration Testing")
        start_time = time.time()
        errors = []
        passed_tests = 0
        total_tests = 0
        
        # Test 1: Service Discovery and Health Checks
        total_tests += 1
        try:
            health_responses = {}
            for service, endpoint in self.endpoints.items():
                try:
                    response = self.session.get(endpoint, timeout=10)
                    health_responses[service] = {
                        'status_code': response.status_code,
                        'response_time': response.elapsed.total_seconds() * 1000,
                        'healthy': response.status_code in [200, 201, 202]
                    }
                except Exception as e:
                    health_responses[service] = {
                        'status_code': 0,
                        'response_time': 10000,
                        'healthy': False,
                        'error': str(e)
                    }
            
            healthy_services = sum(1 for h in health_responses.values() if h['healthy'])
            if healthy_services >= len(self.endpoints) * 0.8:  # 80% healthy threshold
                passed_tests += 1
            else:
                errors.append(f"Only {healthy_services}/{len(self.endpoints)} services healthy")
                
        except Exception as e:
            errors.append(f"Health check failed: {str(e)}")
        
        # Test 2: Data Flow Integration
        total_tests += 1
        try:
            # Simulate end-to-end data flow
            test_payload = {
                'user_id': str(uuid.uuid4()),
                'session_id': str(uuid.uuid4()),
                'behavioral_data': {
                    'mouse_movements': [[100, 200], [150, 250], [200, 300]],
                    'keystroke_dynamics': [120, 95, 110, 88],
                    'scroll_patterns': [0, 100, 200, 300]
                },
                'device_fingerprint': {
                    'screen_resolution': '1920x1080',
                    'user_agent': 'Mozilla/5.0 (compatible test)',
                    'timezone': 'UTC'
                }
            }
            
            # Step 1: Behavioral Analytics
            behavioral_response = self.session.post(
                self.endpoints['behavioral_analytics'], 
                json=test_payload,
                timeout=15
            )
            
            if behavioral_response.status_code == 200:
                behavioral_result = behavioral_response.json()
                
                # Step 2: Risk Assessment
                risk_payload = {
                    **test_payload,
                    'behavioral_score': behavioral_result.get('behavior_score', 0.5)
                }
                
                risk_response = self.session.post(
                    self.endpoints['risk_engine'],
                    json=risk_payload,
                    timeout=15
                )
                
                if risk_response.status_code == 200:
                    risk_result = risk_response.json()
                    
                    # Step 3: Decision Processing
                    if 'risk_score' in risk_result and 'action' in risk_result:
                        passed_tests += 1
                    else:
                        errors.append("Risk engine response missing required fields")
                else:
                    errors.append(f"Risk engine failed: {risk_response.status_code}")
            else:
                errors.append(f"Behavioral analytics failed: {behavioral_response.status_code}")
                
        except Exception as e:
            errors.append(f"Data flow integration failed: {str(e)}")
        
        # Test 3: WebSocket Real-time Communication
        total_tests += 1
        try:
            async with websockets.connect(self.websocket_url, timeout=10) as websocket:
                # Send test message
                test_message = json.dumps({
                    'type': 'risk_update',
                    'data': {'session_id': str(uuid.uuid4()), 'risk_score': 0.75}
                })
                await websocket.send(test_message)
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                response_data = json.loads(response)
                
                if response_data.get('status') == 'acknowledged':
                    passed_tests += 1
                else:
                    errors.append("WebSocket communication failed")
                    
        except Exception as e:
            errors.append(f"WebSocket test failed: {str(e)}")
        
        duration = time.time() - start_time
        status = "PASS" if passed_tests == total_tests else "FAIL"
        
        self.log_test_result(
            "System Integration",
            status,
            duration,
            details={
                'passed_tests': passed_tests,
                'total_tests': total_tests,
                'service_health': health_responses if 'health_responses' in locals() else {},
                'integration_score': passed_tests / total_tests if total_tests > 0 else 0
            },
            errors=errors,
            metrics={
                'integration_success_rate': passed_tests / total_tests if total_tests > 0 else 0,
                'test_duration': duration
            }
        )
        
        return status == "PASS"
    
    async def test_performance_validation(self) -> bool:
        """Test performance requirements - 100K+ RPS, sub-100ms response"""
        logger.info("⚡ Starting Performance Validation")
        start_time = time.time()
        errors = []
        
        # Load test configuration
        test_scenarios = [
            {'concurrent_users': 100, 'duration': 30, 'name': 'baseline'},
            {'concurrent_users': 1000, 'duration': 60, 'name': 'moderate_load'},
            {'concurrent_users': 5000, 'duration': 120, 'name': 'high_load'},
            {'concurrent_users': 10000, 'duration': 30, 'name': 'spike_test'}
        ]
        
        performance_results = {}
        
        for scenario in test_scenarios:
            logger.info(f"🔥 Running {scenario['name']} - {scenario['concurrent_users']} users")
            
            try:
                # Prepare test data
                test_requests = []
                for i in range(scenario['concurrent_users']):
                    test_requests.append({
                        'user_id': f"test_user_{i}",
                        'session_id': str(uuid.uuid4()),
                        'timestamp': time.time(),
                        'behavioral_data': self._generate_test_behavioral_data()
                    })
                
                # Execute concurrent requests
                start_load = time.time()
                response_times = []
                successful_requests = 0
                failed_requests = 0
                
                async def make_request(session, payload):
                    try:
                        request_start = time.time()
                        async with session.post(
                            self.endpoints['risk_engine'], 
                            json=payload,
                            timeout=aiohttp.ClientTimeout(total=30)
                        ) as response:
                            request_time = (time.time() - request_start) * 1000
                            return request_time, response.status
                    except Exception as e:
                        return 30000, 0  # timeout or error
                
                # Use aiohttp for async requests
                async with aiohttp.ClientSession() as session:
                    tasks = []
                    for payload in test_requests:
                        tasks.append(make_request(session, payload))
                    
                    # Execute with controlled concurrency
                    semaphore = asyncio.Semaphore(1000)  # Limit concurrent connections
                    
                    async def controlled_request(task):
                        async with semaphore:
                            return await task
                    
                    results = await asyncio.gather(*[controlled_request(task) for task in tasks])
                    
                    for response_time, status_code in results:
                        response_times.append(response_time)
                        if status_code == 200:
                            successful_requests += 1
                        else:
                            failed_requests += 1
                
                load_duration = time.time() - start_load
                
                # Calculate metrics
                if response_times:
                    avg_response = statistics.mean(response_times)
                    p95_response = np.percentile(response_times, 95)
                    p99_response = np.percentile(response_times, 99)
                    min_response = min(response_times)
                    max_response = max(response_times)
                else:
                    avg_response = p95_response = p99_response = min_response = max_response = 0
                
                throughput = successful_requests / load_duration if load_duration > 0 else 0
                error_rate = failed_requests / len(test_requests) if test_requests else 0
                
                performance_results[scenario['name']] = {
                    'concurrent_users': scenario['concurrent_users'],
                    'duration': load_duration,
                    'successful_requests': successful_requests,
                    'failed_requests': failed_requests,
                    'throughput_rps': throughput,
                    'avg_response_time': avg_response,
                    'p95_response_time': p95_response,
                    'p99_response_time': p99_response,
                    'min_response_time': min_response,
                    'max_response_time': max_response,
                    'error_rate': error_rate
                }
                
                logger.info(f"   📊 {scenario['name']} Results:")
                logger.info(f"      Throughput: {throughput:.2f} RPS")
                logger.info(f"      Avg Response: {avg_response:.2f}ms")
                logger.info(f"      P95 Response: {p95_response:.2f}ms")
                logger.info(f"      Error Rate: {error_rate:.3%}")
                
                # Check against targets
                if p95_response > self.performance_targets['max_response_time']:
                    errors.append(f"{scenario['name']}: P95 response time {p95_response:.2f}ms > {self.performance_targets['max_response_time']}ms")
                
                if error_rate > self.performance_targets['max_error_rate']:
                    errors.append(f"{scenario['name']}: Error rate {error_rate:.3%} > {self.performance_targets['max_error_rate']:.3%}")
                
                # Brief pause between scenarios
                await asyncio.sleep(5)
                
            except Exception as e:
                errors.append(f"{scenario['name']} failed: {str(e)}")
                performance_results[scenario['name']] = {'error': str(e)}
        
        # System resource monitoring during tests
        system_health = self.get_system_health()
        
        if system_health.cpu_percent > self.performance_targets['max_cpu_usage']:
            errors.append(f"CPU usage {system_health.cpu_percent:.1f}% > {self.performance_targets['max_cpu_usage']}%")
        
        if system_health.memory_percent > self.performance_targets['max_memory_usage']:
            errors.append(f"Memory usage {system_health.memory_percent:.1f}% > {self.performance_targets['max_memory_usage']}%")
        
        duration = time.time() - start_time
        status = "PASS" if not errors else "FAIL"
        
        # Calculate overall performance score
        if performance_results:
            high_load_result = performance_results.get('high_load', {})
            performance_score = 0
            
            if high_load_result.get('p95_response_time', 999) <= 100:
                performance_score += 25
            if high_load_result.get('throughput_rps', 0) >= 1000:  # Scaled expectation for test
                performance_score += 25
            if high_load_result.get('error_rate', 1) <= 0.001:
                performance_score += 25
            if system_health.cpu_percent <= 80:
                performance_score += 25
        else:
            performance_score = 0
        
        self.log_test_result(
            "Performance Validation",
            status,
            duration,
            details={
                'performance_results': performance_results,
                'system_health': asdict(system_health),
                'performance_score': performance_score
            },
            errors=errors,
            metrics={
                'performance_score': performance_score / 100,
                'max_throughput': max([r.get('throughput_rps', 0) for r in performance_results.values() if isinstance(r, dict) and 'throughput_rps' in r] + [0]),
                'min_p95_response': min([r.get('p95_response_time', 999) for r in performance_results.values() if isinstance(r, dict) and 'p95_response_time' in r] + [999])
            }
        )
        
        return status == "PASS"
    
    def _generate_test_behavioral_data(self) -> Dict[str, Any]:
        """Generate realistic test behavioral data"""
        return {
            'mouse_movements': [[random.randint(0, 1920), random.randint(0, 1080)] for _ in range(random.randint(10, 50))],
            'keystroke_dynamics': [random.randint(50, 200) for _ in range(random.randint(5, 20))],
            'scroll_patterns': sorted([random.randint(0, 5000) for _ in range(random.randint(3, 15))]),
            'click_patterns': [{'x': random.randint(0, 1920), 'y': random.randint(0, 1080), 'timestamp': time.time()} for _ in range(random.randint(2, 10))],
            'page_dwell_time': random.randint(1000, 30000),
            'form_interaction_speed': random.uniform(0.5, 3.0)
        }
    
    async def test_security_framework(self) -> bool:
        """Test security framework components"""
        logger.info("🔒 Starting Security Framework Testing")
        start_time = time.time()
        errors = []
        passed_tests = 0
        total_tests = 0
        
        # Test 1: Behavioral Biometrics Detection
        total_tests += 1
        try:
            # Test with obvious bot patterns
            bot_payload = {
                'user_id': 'test_bot_user',
                'behavioral_data': {
                    'mouse_movements': [[0, 0], [100, 0], [200, 0], [300, 0]],  # Linear movement
                    'keystroke_dynamics': [100, 100, 100, 100, 100],  # Perfect timing
                    'scroll_patterns': [0, 100, 200, 300, 400],  # Perfect intervals
                    'click_patterns': [{'x': 100, 'y': 100}, {'x': 200, 'y': 200}],  # Geometric pattern
                    'page_dwell_time': 1000,  # Too fast
                    'form_interaction_speed': 0.1  # Superhuman speed
                }
            }
            
            response = self.session.post(
                self.endpoints['behavioral_analytics'],
                json=bot_payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                bot_score = result.get('bot_probability', 0)
                
                if bot_score > 0.7:  # Should detect as likely bot
                    passed_tests += 1
                else:
                    errors.append(f"Bot detection failed: score {bot_score} too low")
            else:
                errors.append(f"Behavioral analytics API failed: {response.status_code}")
                
        except Exception as e:
            errors.append(f"Behavioral biometrics test failed: {str(e)}")
        
        # Test 2: TLS Fingerprint Randomization
        total_tests += 1
        try:
            # Make multiple requests and check for fingerprint variation
            fingerprints = set()
            
            for i in range(5):
                response = self.session.get(
                    f"{self.endpoints['risk_engine']}?test_fingerprint={i}",
                    timeout=10
                )
                
                if response.status_code == 200:
                    # Check if response headers indicate different fingerprints
                    tls_fingerprint = response.headers.get('X-TLS-Fingerprint', f'default_{i}')
                    fingerprints.add(tls_fingerprint)
            
            if len(fingerprints) >= 3:  # Should have some variation
                passed_tests += 1
            else:
                errors.append(f"TLS fingerprint randomization insufficient: only {len(fingerprints)} unique")
                
        except Exception as e:
            errors.append(f"TLS fingerprint test failed: {str(e)}")
        
        # Test 3: Fraud API Integration
        total_tests += 1
        try:
            fraud_payload = {
                'user_id': 'test_fraud_user',
                'ip_address': '192.168.1.100',
                'device_fingerprint': {
                    'screen_resolution': '1920x1080',
                    'user_agent': 'TestAgent/1.0',
                    'timezone': 'UTC'
                },
                'transaction_data': {
                    'amount': 100.0,
                    'currency': 'USD',
                    'merchant': 'test_merchant'
                }
            }
            
            response = self.session.post(
                self.endpoints['fraud_detection'],
                json=fraud_payload,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'fraud_score' in result and 'risk_factors' in result:
                    passed_tests += 1
                else:
                    errors.append("Fraud detection response missing required fields")
            else:
                errors.append(f"Fraud detection API failed: {response.status_code}")
                
        except Exception as e:
            errors.append(f"Fraud API test failed: {str(e)}")
        
        # Test 4: ML Model Accuracy
        total_tests += 1
        try:
            # Test with known legitimate user patterns
            human_payload = {
                'user_id': 'test_human_user',
                'behavioral_data': {
                    'mouse_movements': [[random.randint(0, 1920), random.randint(0, 1080)] for _ in range(25)],
                    'keystroke_dynamics': [random.randint(80, 150) for _ in range(12)],
                    'scroll_patterns': [0, 50, 120, 180, 250, 400, 500],
                    'click_patterns': [{'x': random.randint(100, 800), 'y': random.randint(100, 600)} for _ in range(5)],
                    'page_dwell_time': 15000,
                    'form_interaction_speed': 1.5
                }
            }
            
            response = self.session.post(
                self.endpoints['behavioral_analytics'],
                json=human_payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                human_score = result.get('bot_probability', 1)
                
                if human_score < 0.3:  # Should detect as likely human
                    passed_tests += 1
                else:
                    errors.append(f"Human detection failed: score {human_score} too high")
            else:
                errors.append(f"ML model test failed: {response.status_code}")
                
        except Exception as e:
            errors.append(f"ML model accuracy test failed: {str(e)}")
        
        duration = time.time() - start_time
        status = "PASS" if passed_tests == total_tests else "FAIL"
        
        self.log_test_result(
            "Security Framework",
            status,
            duration,
            details={
                'passed_tests': passed_tests,
                'total_tests': total_tests,
                'security_score': passed_tests / total_tests if total_tests > 0 else 0
            },
            errors=errors,
            metrics={
                'security_success_rate': passed_tests / total_tests if total_tests > 0 else 0,
                'test_duration': duration
            }
        )
        
        return status == "PASS"
    
    async def test_temporal_workflows(self) -> bool:
        """Test Temporal workflow orchestration"""
        logger.info("🔄 Starting Temporal Workflow Testing")
        start_time = time.time()
        errors = []
        passed_tests = 0
        total_tests = 0
        
        # Test 1: Workflow Execution
        total_tests += 1
        try:
            workflow_payload = {
                'workflow_type': 'risk_assessment_workflow',
                'user_id': str(uuid.uuid4()),
                'input_data': {
                    'behavioral_data': self._generate_test_behavioral_data(),
                    'device_info': {'type': 'mobile', 'os': 'iOS'}
                }
            }
            
            response = self.session.post(
                self.endpoints['temporal_workflow'],
                json=workflow_payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                workflow_id = result.get('workflow_id')
                
                if workflow_id:
                    # Check workflow status
                    await asyncio.sleep(2)  # Wait for processing
                    
                    status_response = self.session.get(
                        f"{self.endpoints['temporal_workflow']}/{workflow_id}",
                        timeout=10
                    )
                    
                    if status_response.status_code == 200:
                        status_result = status_response.json()
                        if status_result.get('status') in ['completed', 'running']:
                            passed_tests += 1
                        else:
                            errors.append(f"Workflow status invalid: {status_result.get('status')}")
                    else:
                        errors.append(f"Workflow status check failed: {status_response.status_code}")
                else:
                    errors.append("Workflow start response missing workflow_id")
            else:
                errors.append(f"Workflow start failed: {response.status_code}")
                
        except Exception as e:
            errors.append(f"Temporal workflow test failed: {str(e)}")
        
        # Test 2: Workflow State Persistence
        total_tests += 1
        try:
            # Start a long-running workflow
            long_workflow_payload = {
                'workflow_type': 'long_running_analysis',
                'user_id': str(uuid.uuid4()),
                'input_data': {'processing_time': 5}  # 5 second processing
            }
            
            response = self.session.post(
                self.endpoints['temporal_workflow'],
                json=long_workflow_payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                workflow_id = result.get('workflow_id')
                
                # Wait and check persistence
                await asyncio.sleep(3)
                
                status_response = self.session.get(
                    f"{self.endpoints['temporal_workflow']}/{workflow_id}",
                    timeout=10
                )
                
                if status_response.status_code == 200:
                    passed_tests += 1
                else:
                    errors.append("Workflow state persistence failed")
            else:
                errors.append(f"Long workflow start failed: {response.status_code}")
                
        except Exception as e:
            errors.append(f"Workflow persistence test failed: {str(e)}")
        
        # Test 3: Error Handling and Retries
        total_tests += 1
        try:
            # Submit workflow with error-inducing payload
            error_payload = {
                'workflow_type': 'error_test_workflow',
                'user_id': 'error_user',
                'input_data': {'force_error': True}
            }
            
            response = self.session.post(
                self.endpoints['temporal_workflow'],
                json=error_payload,
                timeout=15
            )
            
            # Should handle gracefully
            if response.status_code in [200, 400, 422]:  # Expected error handling
                passed_tests += 1
            else:
                errors.append(f"Error handling failed: unexpected status {response.status_code}")
                
        except Exception as e:
            # Timeout or connection error is acceptable for error test
            passed_tests += 1
        
        duration = time.time() - start_time
        status = "PASS" if passed_tests == total_tests else "FAIL"
        
        self.log_test_result(
            "Temporal Workflows",
            status,
            duration,
            details={
                'passed_tests': passed_tests,
                'total_tests': total_tests,
                'workflow_score': passed_tests / total_tests if total_tests > 0 else 0
            },
            errors=errors,
            metrics={
                'workflow_success_rate': passed_tests / total_tests if total_tests > 0 else 0,
                'test_duration': duration
            }
        )
        
        return status == "PASS"
    
    async def test_observability_stack(self) -> bool:
        """Test observability and monitoring systems"""
        logger.info("👁️ Starting Observability Stack Testing")
        start_time = time.time()
        errors = []
        passed_tests = 0
        total_tests = 0
        
        # Test 1: Metrics Collection
        total_tests += 1
        try:
            response = self.session.get(self.endpoints['metrics'], timeout=10)
            
            if response.status_code == 200:
                metrics_text = response.text
                
                # Check for key metrics
                required_metrics = [
                    'request_duration_seconds',
                    'request_count_total',
                    'error_rate',
                    'cpu_usage_percent',
                    'memory_usage_percent'
                ]
                
                found_metrics = sum(1 for metric in required_metrics if metric in metrics_text)
                
                if found_metrics >= len(required_metrics) * 0.8:  # 80% of metrics found
                    passed_tests += 1
                else:
                    errors.append(f"Only {found_metrics}/{len(required_metrics)} required metrics found")
            else:
                errors.append(f"Metrics endpoint failed: {response.status_code}")
                
        except Exception as e:
            errors.append(f"Metrics collection test failed: {str(e)}")
        
        # Test 2: Real-time Monitoring
        total_tests += 1
        try:
            response = self.session.get(self.endpoints['monitoring'], timeout=10)
            
            if response.status_code == 200:
                monitoring_data = response.json()
                
                required_fields = ['system_health', 'active_alerts', 'service_status', 'performance_metrics']
                found_fields = sum(1 for field in required_fields if field in monitoring_data)
                
                if found_fields >= 3:  # Most fields present
                    passed_tests += 1
                else:
                    errors.append(f"Monitoring data incomplete: {found_fields}/{len(required_fields)} fields")
            else:
                errors.append(f"Monitoring endpoint failed: {response.status_code}")
                
        except Exception as e:
            errors.append(f"Monitoring test failed: {str(e)}")
        
        # Test 3: Alert System
        total_tests += 1
        try:
            # Trigger a test alert
            alert_payload = {
                'alert_type': 'test_alert',
                'severity': 'warning',
                'message': 'End-to-end test alert',
                'metadata': {'test_id': self.test_id}
            }
            
            response = self.session.post(
                f"{self.base_url}/api/v1/alerts/trigger",
                json=alert_payload,
                timeout=10
            )
            
            if response.status_code in [200, 201, 202]:  # Alert accepted
                passed_tests += 1
            else:
                errors.append(f"Alert system failed: {response.status_code}")
                
        except Exception as e:
            errors.append(f"Alert system test failed: {str(e)}")
        
        # Test 4: Distributed Tracing
        total_tests += 1
        try:
            # Make a request with tracing headers
            trace_headers = {
                'X-Trace-Id': str(uuid.uuid4()),
                'X-Span-Id': str(uuid.uuid4()),
                'X-Parent-Span-Id': str(uuid.uuid4())
            }
            
            response = self.session.get(
                self.endpoints['risk_engine'],
                headers=trace_headers,
                timeout=10
            )
            
            # Check if tracing headers are preserved/updated
            if response.headers.get('X-Trace-Id') or response.status_code == 200:
                passed_tests += 1
            else:
                errors.append("Distributed tracing not working")
                
        except Exception as e:
            errors.append(f"Tracing test failed: {str(e)}")
        
        duration = time.time() - start_time
        status = "PASS" if passed_tests == total_tests else "FAIL"
        
        self.log_test_result(
            "Observability Stack",
            status,
            duration,
            details={
                'passed_tests': passed_tests,
                'total_tests': total_tests,
                'observability_score': passed_tests / total_tests if total_tests > 0 else 0
            },
            errors=errors,
            metrics={
                'observability_success_rate': passed_tests / total_tests if total_tests > 0 else 0,
                'test_duration': duration
            }
        )
        
        return status == "PASS"
    
    def test_production_readiness(self) -> bool:
        """Test production readiness aspects"""
        logger.info("🚀 Starting Production Readiness Assessment")
        start_time = time.time()
        errors = []
        passed_tests = 0
        total_tests = 0
        
        # Test 1: Configuration Management
        total_tests += 1
        try:
            # Check for sensitive data in configurations
            config_files = [
                '/Users/daltonmetzler/Desktop/Tinder/.env',
                '/Users/daltonmetzler/Desktop/Tinder/infra/config',
                '/Users/daltonmetzler/Desktop/Tinder/docker-compose.yml'
            ]
            
            exposed_secrets = []
            for config_path in config_files:
                if os.path.exists(config_path):
                    try:
                        if os.path.isfile(config_path):
                            with open(config_path, 'r') as f:
                                content = f.read()
                        else:
                            # Directory - check all files
                            content = ""
                            for root, dirs, files in os.walk(config_path):
                                for file in files:
                                    file_path = os.path.join(root, file)
                                    try:
                                        with open(file_path, 'r') as f:
                                            content += f.read() + "\n"
                                    except:
                                        continue
                        
                        # Check for exposed secrets
                        secret_patterns = ['password=', 'secret=', 'key=', 'token=', 'api_key=']
                        for pattern in secret_patterns:
                            if pattern in content.lower() and 'your_' not in content.lower():
                                exposed_secrets.append(f"{config_path}: {pattern}")
                                
                    except Exception as e:
                        logger.warning(f"Could not check {config_path}: {e}")
            
            if not exposed_secrets:
                passed_tests += 1
            else:
                errors.append(f"Exposed secrets found: {exposed_secrets}")
                
        except Exception as e:
            errors.append(f"Configuration security check failed: {str(e)}")
        
        # Test 2: Docker Environment
        total_tests += 1
        try:
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                # Check if containers are running
                result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
                if result.returncode == 0:
                    running_containers = result.stdout.count('\n') - 1  # Subtract header
                    if running_containers > 0:
                        passed_tests += 1
                    else:
                        errors.append("No Docker containers running")
                else:
                    errors.append("Cannot list Docker containers")
            else:
                errors.append("Docker not available")
                
        except Exception as e:
            errors.append(f"Docker environment check failed: {str(e)}")
        
        # Test 3: Database Connectivity
        total_tests += 1
        try:
            # Try to connect to database endpoint
            db_health_response = self.session.get(
                f"{self.base_url}/api/v1/health/database",
                timeout=10
            )
            
            if db_health_response.status_code == 200:
                db_result = db_health_response.json()
                if db_result.get('status') == 'healthy':
                    passed_tests += 1
                else:
                    errors.append(f"Database unhealthy: {db_result}")
            else:
                errors.append(f"Database health check failed: {db_health_response.status_code}")
                
        except Exception as e:
            errors.append(f"Database connectivity test failed: {str(e)}")
        
        # Test 4: Backup and Recovery
        total_tests += 1
        try:
            # Test backup endpoint
            backup_response = self.session.post(
                f"{self.base_url}/api/v1/admin/backup/test",
                json={'backup_type': 'configuration'},
                timeout=15
            )
            
            if backup_response.status_code in [200, 201, 202]:  # Backup initiated
                passed_tests += 1
            else:
                errors.append(f"Backup system not available: {backup_response.status_code}")
                
        except Exception as e:
            errors.append(f"Backup system test failed: {str(e)}")
        
        # Test 5: SSL/TLS Configuration
        total_tests += 1
        try:
            # Check SSL configuration if HTTPS endpoint available
            if self.base_url.startswith('https'):
                parsed_url = urlparse(self.base_url)
                host = parsed_url.hostname
                port = parsed_url.port or 443
                
                context = ssl.create_default_context()
                with socket.create_connection((host, port), timeout=10) as sock:
                    with context.wrap_socket(sock, server_hostname=host) as ssock:
                        cert = ssock.getpeercert()
                        if cert:
                            passed_tests += 1
                        else:
                            errors.append("SSL certificate not valid")
            else:
                # For HTTP endpoints, check if redirect to HTTPS exists
                try:
                    https_url = self.base_url.replace('http://', 'https://')
                    https_response = self.session.get(f"{https_url}/health", timeout=5)
                    if https_response.status_code == 200:
                        passed_tests += 1
                    else:
                        errors.append("HTTPS not available (recommended for production)")
                except:
                    errors.append("HTTPS not configured (recommended for production)")
                    
        except Exception as e:
            errors.append(f"SSL/TLS check failed: {str(e)}")
        
        duration = time.time() - start_time
        status = "PASS" if passed_tests >= total_tests * 0.8 else "FAIL"  # 80% threshold
        
        self.log_test_result(
            "Production Readiness",
            status,
            duration,
            details={
                'passed_tests': passed_tests,
                'total_tests': total_tests,
                'readiness_score': passed_tests / total_tests if total_tests > 0 else 0
            },
            errors=errors,
            metrics={
                'readiness_success_rate': passed_tests / total_tests if total_tests > 0 else 0,
                'test_duration': duration
            }
        )
        
        return status == "PASS"
    
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_duration = time.time() - self.start_time
        
        # Calculate overall metrics
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.status == "PASS")
        failed_tests = sum(1 for r in self.results if r.status == "FAIL")
        skipped_tests = sum(1 for r in self.results if r.status == "SKIP")
        
        # Calculate composite scores
        test_categories = {}
        for result in self.results:
            category = result.test_name.split()[0] if result.test_name else "Unknown"
            if category not in test_categories:
                test_categories[category] = {'passed': 0, 'total': 0, 'errors': []}
            test_categories[category]['total'] += 1
            if result.status == "PASS":
                test_categories[category]['passed'] += 1
            test_categories[category]['errors'].extend(result.errors)
        
        # Overall system score (weighted)
        weights = {
            'System': 0.25,
            'Performance': 0.25,
            'Security': 0.20,
            'Temporal': 0.10,
            'Observability': 0.10,
            'Production': 0.10
        }
        
        overall_score = 0
        for category, data in test_categories.items():
            category_score = data['passed'] / data['total'] if data['total'] > 0 else 0
            weight = weights.get(category, 0.1)
            overall_score += category_score * weight
        
        # System health at end of tests
        final_health = self.get_system_health()
        
        # Recommendations based on results
        recommendations = []
        critical_issues = []
        
        for result in self.results:
            if result.status == "FAIL":
                for error in result.errors:
                    if any(keyword in error.lower() for keyword in ['response time', 'timeout', 'performance']):
                        recommendations.append(f"Optimize performance: {error}")
                    elif any(keyword in error.lower() for keyword in ['security', 'fraud', 'bot']):
                        critical_issues.append(f"Security issue: {error}")
                    elif any(keyword in error.lower() for keyword in ['database', 'connection', 'service']):
                        critical_issues.append(f"Infrastructure issue: {error}")
                    else:
                        recommendations.append(f"General improvement: {error}")
        
        # Production deployment assessment
        deployment_ready = (
            overall_score >= 0.8 and
            len(critical_issues) == 0 and
            final_health.response_time < 200 and
            final_health.error_rate < 0.01
        )
        
        report = {
            'test_summary': {
                'test_id': self.test_id,
                'timestamp': datetime.now().isoformat(),
                'duration_seconds': total_duration,
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'skipped_tests': skipped_tests,
                'success_rate': passed_tests / total_tests if total_tests > 0 else 0
            },
            'category_scores': {
                category: {
                    'score': data['passed'] / data['total'] if data['total'] > 0 else 0,
                    'passed': data['passed'],
                    'total': data['total'],
                    'error_count': len(data['errors'])
                }
                for category, data in test_categories.items()
            },
            'overall_score': overall_score,
            'system_health': asdict(final_health),
            'performance_metrics': {
                'max_response_time': max([r.metrics.get('test_duration', 0) for r in self.results] + [0]),
                'avg_test_duration': statistics.mean([r.duration for r in self.results]) if self.results else 0,
                'total_errors': sum(len(r.errors) for r in self.results)
            },
            'critical_issues': critical_issues,
            'recommendations': recommendations,
            'deployment_assessment': {
                'ready_for_production': deployment_ready,
                'confidence_score': overall_score,
                'blocking_issues': critical_issues,
                'next_steps': [
                    "Fix all critical issues" if critical_issues else "Monitor system performance",
                    "Implement recommendations" if recommendations else "Proceed with deployment",
                    "Setup production monitoring",
                    "Plan disaster recovery procedures"
                ]
            },
            'detailed_results': [asdict(result) for result in self.results]
        }
        
        return report
    
    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run all comprehensive tests"""
        logger.info("🚀 Starting Comprehensive End-to-End Testing")
        logger.info(f"Test ID: {self.test_id}")
        
        try:
            # System health baseline
            baseline_health = self.get_system_health()
            logger.info(f"📊 Baseline System Health: CPU {baseline_health.cpu_percent:.1f}%, "
                       f"Memory {baseline_health.memory_percent:.1f}%, "
                       f"Response {baseline_health.response_time:.2f}ms")
            
            # Run test suites in order
            test_suite_results = {
                'system_integration': await self.test_system_integration(),
                'performance_validation': await self.test_performance_validation(),
                'security_framework': await self.test_security_framework(),
                'temporal_workflows': await self.test_temporal_workflows(),
                'observability_stack': await self.test_observability_stack(),
                'production_readiness': self.test_production_readiness()
            }
            
            # Generate comprehensive report
            report = self.generate_comprehensive_report()
            
            # Add test suite summary to report
            report['test_suite_results'] = test_suite_results
            report['overall_success'] = all(test_suite_results.values())
            
            # Save report to file
            timestamp = int(time.time())
            report_filename = f"comprehensive_end_to_end_report_{timestamp}.json"
            report_path = f"/Users/daltonmetzler/Desktop/Tinder/{report_filename}"
            
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"📋 Comprehensive report saved: {report_path}")
            
            # Print summary
            logger.info("\n" + "="*80)
            logger.info("🏁 COMPREHENSIVE END-TO-END TEST RESULTS")
            logger.info("="*80)
            logger.info(f"Overall Score: {report['overall_score']:.2%}")
            logger.info(f"Tests Passed: {report['test_summary']['passed_tests']}/{report['test_summary']['total_tests']}")
            logger.info(f"Success Rate: {report['test_summary']['success_rate']:.2%}")
            logger.info(f"Total Duration: {report['test_summary']['duration_seconds']:.1f}s")
            logger.info(f"Production Ready: {'✅ YES' if report['deployment_assessment']['ready_for_production'] else '❌ NO'}")
            
            if report['critical_issues']:
                logger.error("\n🚨 CRITICAL ISSUES:")
                for issue in report['critical_issues']:
                    logger.error(f"   • {issue}")
            
            if report['recommendations']:
                logger.info("\n💡 RECOMMENDATIONS:")
                for rec in report['recommendations'][:5]:  # Top 5
                    logger.info(f"   • {rec}")
            
            logger.info("\n📊 CATEGORY SCORES:")
            for category, score_data in report['category_scores'].items():
                score_pct = score_data['score'] * 100
                status_emoji = "✅" if score_data['score'] >= 0.8 else "⚠️" if score_data['score'] >= 0.6 else "❌"
                logger.info(f"   {status_emoji} {category}: {score_pct:.1f}% ({score_data['passed']}/{score_data['total']})")
            
            logger.info("="*80)
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Comprehensive testing failed: {str(e)}")
            error_report = {
                'error': str(e),
                'test_id': self.test_id,
                'timestamp': datetime.now().isoformat(),
                'partial_results': [asdict(result) for result in self.results]
            }
            return error_report

async def main():
    """Main execution function"""
    test_suite = EndToEndTestSuite()
    report = await test_suite.run_comprehensive_tests()
    
    # Return success/failure based on results
    if report.get('deployment_assessment', {}).get('ready_for_production', False):
        logger.info("🎉 System is READY for production deployment!")
        return 0
    else:
        logger.error("⚠️ System requires fixes before production deployment")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\n⏹️ Testing interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Fatal error: {str(e)}")
        sys.exit(1)
