#!/usr/bin/env python3
"""
API Testing Framework for Android Apps
Comprehensive API endpoint testing, validation, and performance analysis
"""

import requests
import json
import time
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
import urllib.parse
from typing import Dict, List, Optional
import concurrent.futures
import statistics

class APITestFramework:
    """Framework for testing Android app APIs"""
    
    def __init__(self, base_url: str, proxy_config: Optional[Dict] = None):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.test_results = []
        self.performance_data = []
        
        # Configure proxy if provided
        if proxy_config:
            self.session.proxies.update(proxy_config)
        
        # Set default headers
        self.session.headers.update({
            'User-Agent': 'AndroidAPITester/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
    
    def add_auth_token(self, token: str, header_name: str = 'Authorization'):
        """Add authentication token to requests"""
        self.session.headers[header_name] = f'Bearer {token}'
    
    def test_endpoint(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Test a single API endpoint"""
        url = f"{self.base_url}{endpoint}"
        
        test_info = {
            'timestamp': datetime.now().isoformat(),
            'method': method.upper(),
            'url': url,
            'endpoint': endpoint
        }
        
        try:
            start_time = time.time()
            
            # Make request
            response = self.session.request(method, url, **kwargs)
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # milliseconds
            
            # Parse response
            try:
                response_json = response.json()
            except json.JSONDecodeError:
                response_json = None
            
            result = {
                **test_info,
                'status': 'success',
                'status_code': response.status_code,
                'response_time_ms': response_time,
                'response_size_bytes': len(response.content),
                'response_headers': dict(response.headers),
                'response_json': response_json,
                'response_text': response.text[:1000] if not response_json else None  # First 1000 chars
            }
            
            # Add performance data
            self.performance_data.append({
                'endpoint': endpoint,
                'response_time_ms': response_time,
                'timestamp': start_time
            })
            
        except requests.RequestException as e:
            result = {
                **test_info,
                'status': 'failed',
                'error': str(e),
                'error_type': type(e).__name__
            }
        
        self.test_results.append(result)
        return result
    
    def test_get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Test GET endpoint"""
        return self.test_endpoint('GET', endpoint, params=params)
    
    def test_post(self, endpoint: str, data: Optional[Dict] = None, json_data: Optional[Dict] = None) -> Dict:
        """Test POST endpoint"""
        kwargs = {}
        if data:
            kwargs['data'] = data
        if json_data:
            kwargs['json'] = json_data
        return self.test_endpoint('POST', endpoint, **kwargs)
    
    def test_put(self, endpoint: str, json_data: Optional[Dict] = None) -> Dict:
        """Test PUT endpoint"""
        return self.test_endpoint('PUT', endpoint, json=json_data)
    
    def test_delete(self, endpoint: str) -> Dict:
        """Test DELETE endpoint"""
        return self.test_endpoint('DELETE', endpoint)
    
    def test_endpoint_performance(self, method: str, endpoint: str, iterations: int = 10, **kwargs) -> Dict:
        """Test endpoint performance with multiple requests"""
        response_times = []
        status_codes = []
        errors = []
        
        print(f"Performance testing {method} {endpoint} ({iterations} iterations)...")
        
        for i in range(iterations):
            try:
                start_time = time.time()
                response = self.session.request(method, f"{self.base_url}{endpoint}", **kwargs)
                end_time = time.time()
                
                response_time = (end_time - start_time) * 1000
                response_times.append(response_time)
                status_codes.append(response.status_code)
                
                print(f"  Iteration {i+1}: {response_time:.1f}ms (Status: {response.status_code})")
                
            except requests.RequestException as e:
                errors.append(str(e))
                print(f"  Iteration {i+1}: Failed - {e}")
            
            # Small delay between requests
            time.sleep(0.1)
        
        # Calculate statistics
        performance_result = {
            'endpoint': endpoint,
            'method': method.upper(),
            'iterations': iterations,
            'successful_requests': len(response_times),
            'failed_requests': len(errors),
            'errors': errors
        }
        
        if response_times:
            performance_result.update({
                'avg_response_time_ms': statistics.mean(response_times),
                'median_response_time_ms': statistics.median(response_times),
                'min_response_time_ms': min(response_times),
                'max_response_time_ms': max(response_times),
                'std_dev_ms': statistics.stdev(response_times) if len(response_times) > 1 else 0,
                'status_codes': list(set(status_codes))
            })
        
        return performance_result
    
    def test_concurrent_requests(self, method: str, endpoint: str, concurrent_users: int = 5, requests_per_user: int = 10, **kwargs) -> Dict:
        """Test endpoint with concurrent requests"""
        print(f"Concurrent testing {method} {endpoint} ({concurrent_users} users, {requests_per_user} requests each)...")
        
        def make_requests(user_id: int):
            """Make requests for a single user"""
            user_results = []
            for i in range(requests_per_user):
                try:
                    start_time = time.time()
                    response = self.session.request(method, f"{self.base_url}{endpoint}", **kwargs)
                    end_time = time.time()
                    
                    user_results.append({
                        'user_id': user_id,
                        'request_id': i + 1,
                        'response_time_ms': (end_time - start_time) * 1000,
                        'status_code': response.status_code,
                        'success': True
                    })
                except requests.RequestException as e:
                    user_results.append({
                        'user_id': user_id,
                        'request_id': i + 1,
                        'error': str(e),
                        'success': False
                    })
            return user_results
        
        # Execute concurrent requests
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            future_to_user = {executor.submit(make_requests, user_id): user_id 
                            for user_id in range(concurrent_users)}
            
            all_results = []
            for future in concurrent.futures.as_completed(future_to_user):
                user_results = future.result()
                all_results.extend(user_results)
        
        end_time = time.time()
        
        # Analyze results
        successful_requests = [r for r in all_results if r.get('success', False)]
        failed_requests = [r for r in all_results if not r.get('success', False)]
        
        result = {
            'endpoint': endpoint,
            'method': method.upper(),
            'concurrent_users': concurrent_users,
            'requests_per_user': requests_per_user,
            'total_requests': len(all_results),
            'successful_requests': len(successful_requests),
            'failed_requests': len(failed_requests),
            'total_duration_seconds': end_time - start_time,
            'requests_per_second': len(all_results) / (end_time - start_time)
        }
        
        if successful_requests:
            response_times = [r['response_time_ms'] for r in successful_requests]
            result.update({
                'avg_response_time_ms': statistics.mean(response_times),
                'median_response_time_ms': statistics.median(response_times),
                'min_response_time_ms': min(response_times),
                'max_response_time_ms': max(response_times)
            })
        
        return result
    
    def test_data_validation(self, endpoint: str, expected_schema: Dict) -> Dict:
        """Test response data validation against expected schema"""
        result = self.test_get(endpoint)
        
        if result['status'] != 'success':
            return {**result, 'validation': 'failed', 'validation_error': 'Request failed'}
        
        response_data = result.get('response_json')
        if not response_data:
            return {**result, 'validation': 'failed', 'validation_error': 'No JSON response'}
        
        # Simple schema validation
        validation_errors = []
        
        def validate_field(data, schema, path=""):
            """Recursively validate data against schema"""
            if isinstance(schema, dict):
                if not isinstance(data, dict):
                    validation_errors.append(f"{path}: Expected object, got {type(data).__name__}")
                    return
                
                for key, expected_type in schema.items():
                    if key not in data:
                        validation_errors.append(f"{path}.{key}: Missing required field")
                    else:
                        validate_field(data[key], expected_type, f"{path}.{key}")
            
            elif isinstance(schema, list) and len(schema) == 1:
                if not isinstance(data, list):
                    validation_errors.append(f"{path}: Expected array, got {type(data).__name__}")
                    return
                
                for i, item in enumerate(data):
                    validate_field(item, schema[0], f"{path}[{i}]")
            
            elif schema in [str, int, float, bool]:
                if not isinstance(data, schema):
                    validation_errors.append(f"{path}: Expected {schema.__name__}, got {type(data).__name__}")
        
        validate_field(response_data, expected_schema)
        
        result['validation'] = 'passed' if not validation_errors else 'failed'
        if validation_errors:
            result['validation_errors'] = validation_errors
        
        return result
    
    def run_test_suite(self, test_config: Dict) -> Dict:
        """Run a complete test suite from configuration"""
        print(f"Running API test suite: {test_config.get('name', 'Unnamed')}")
        print("=" * 60)
        
        suite_results = {
            'name': test_config.get('name', 'API Test Suite'),
            'base_url': self.base_url,
            'started_at': datetime.now().isoformat(),
            'tests': []
        }
        
        # Run individual tests
        for test in test_config.get('tests', []):
            test_name = test.get('name', 'Unnamed Test')
            print(f"\nRunning: {test_name}")
            
            test_result = {'name': test_name}
            
            try:
                if test.get('type') == 'performance':
                    result = self.test_endpoint_performance(
                        test['method'],
                        test['endpoint'],
                        iterations=test.get('iterations', 10),
                        **test.get('kwargs', {})
                    )
                elif test.get('type') == 'concurrent':
                    result = self.test_concurrent_requests(
                        test['method'],
                        test['endpoint'],
                        concurrent_users=test.get('concurrent_users', 5),
                        requests_per_user=test.get('requests_per_user', 10),
                        **test.get('kwargs', {})
                    )
                elif test.get('type') == 'validation':
                    result = self.test_data_validation(
                        test['endpoint'],
                        test['expected_schema']
                    )
                else:
                    # Standard functional test
                    result = self.test_endpoint(
                        test['method'],
                        test['endpoint'],
                        **test.get('kwargs', {})
                    )
                
                test_result.update(result)
                
                # Print result summary
                if 'status' in result:
                    print(f"  Status: {result['status']}")
                    if result['status'] == 'success':
                        print(f"  Response time: {result.get('response_time_ms', 'N/A'):.1f}ms")
                        print(f"  Status code: {result.get('status_code', 'N/A')}")
                
            except Exception as e:
                test_result.update({
                    'status': 'error',
                    'error': str(e),
                    'error_type': type(e).__name__
                })
                print(f"  Error: {e}")
            
            suite_results['tests'].append(test_result)
        
        suite_results['completed_at'] = datetime.now().isoformat()
        return suite_results
    
    def generate_report(self, output_file: str = "api_test_report.json") -> str:
        """Generate comprehensive test report"""
        report = {
            'summary': {
                'total_tests': len(self.test_results),
                'successful_tests': len([r for r in self.test_results if r.get('status') == 'success']),
                'failed_tests': len([r for r in self.test_results if r.get('status') == 'failed']),
                'generated_at': datetime.now().isoformat(),
                'base_url': self.base_url
            },
            'test_results': self.test_results,
            'performance_data': self.performance_data
        }
        
        # Add performance statistics
        if self.performance_data:
            response_times = [p['response_time_ms'] for p in self.performance_data]
            report['summary']['performance'] = {
                'avg_response_time_ms': statistics.mean(response_times),
                'median_response_time_ms': statistics.median(response_times),
                'min_response_time_ms': min(response_times),
                'max_response_time_ms': max(response_times)
            }
        
        # Save report
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nAPI Test Report Generated: {output_file}")
        print("=" * 40)
        print(f"Total Tests: {report['summary']['total_tests']}")
        print(f"Successful: {report['summary']['successful_tests']}")
        print(f"Failed: {report['summary']['failed_tests']}")
        
        if 'performance' in report['summary']:
            print(f"Average Response Time: {report['summary']['performance']['avg_response_time_ms']:.1f}ms")
        
        return output_file

def load_test_config(config_file: str) -> Dict:
    """Load test configuration from JSON file"""
    with open(config_file, 'r') as f:
        return json.load(f)

def create_sample_config():
    """Create sample test configuration"""
    config = {
        "name": "Sample API Test Suite",
        "base_url": "http://localhost:8081/api",
        "tests": [
            {
                "name": "Get Users List",
                "type": "functional",
                "method": "GET",
                "endpoint": "/users"
            },
            {
                "name": "Get Single User",
                "type": "functional", 
                "method": "GET",
                "endpoint": "/users/1"
            },
            {
                "name": "User Login",
                "type": "functional",
                "method": "POST",
                "endpoint": "/auth/login",
                "kwargs": {
                    "json": {
                        "username": "testuser",
                        "password": "testpass"
                    }
                }
            },
            {
                "name": "Performance Test - Users",
                "type": "performance",
                "method": "GET",
                "endpoint": "/users",
                "iterations": 20
            },
            {
                "name": "Concurrent Test - Health Check",
                "type": "concurrent",
                "method": "GET", 
                "endpoint": "/health",
                "concurrent_users": 10,
                "requests_per_user": 5
            },
            {
                "name": "Data Validation - User Schema",
                "type": "validation",
                "endpoint": "/users/1",
                "expected_schema": {
                    "id": int,
                    "name": str,
                    "email": str,
                    "profile": {
                        "age": int,
                        "location": str
                    }
                }
            }
        ]
    }
    
    with open("sample_api_tests.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print("Sample configuration created: sample_api_tests.json")
    return config

def main():
    parser = argparse.ArgumentParser(description="API Testing Framework for Android Apps")
    parser.add_argument("base_url", help="Base URL of the API to test")
    parser.add_argument("--config", help="Test configuration file (JSON)")
    parser.add_argument("--proxy-host", help="Proxy host for requests")
    parser.add_argument("--proxy-port", type=int, help="Proxy port")
    parser.add_argument("--auth-token", help="Authentication token")
    parser.add_argument("--output", default="api_test_report.json", help="Output report file")
    parser.add_argument("--create-sample", action="store_true", help="Create sample configuration")
    parser.add_argument("--quick-test", action="store_true", help="Run quick connectivity test")
    
    args = parser.parse_args()
    
    if args.create_sample:
        create_sample_config()
        return
    
    # Set up proxy configuration
    proxy_config = None
    if args.proxy_host and args.proxy_port:
        proxy_config = {
            'http': f'http://{args.proxy_host}:{args.proxy_port}',
            'https': f'http://{args.proxy_host}:{args.proxy_port}'
        }
    
    # Initialize test framework
    tester = APITestFramework(args.base_url, proxy_config)
    
    if args.auth_token:
        tester.add_auth_token(args.auth_token)
    
    if args.quick_test:
        # Quick connectivity test
        print("Running quick connectivity test...")
        result = tester.test_get("/")
        print(f"Status: {result.get('status')}")
        if result.get('status') == 'success':
            print(f"Response time: {result.get('response_time_ms'):.1f}ms")
            print(f"Status code: {result.get('status_code')}")
        else:
            print(f"Error: {result.get('error')}")
        return
    
    if args.config:
        # Run test suite from configuration
        config = load_test_config(args.config)
        suite_results = tester.run_test_suite(config)
        
        # Save suite results
        with open(f"suite_{args.output}", "w") as f:
            json.dump(suite_results, f, indent=2)
    else:
        # Run basic tests
        print("Running basic API tests...")
        
        # Test common endpoints
        endpoints = ["/", "/health", "/api", "/api/users"]
        
        for endpoint in endpoints:
            print(f"Testing {endpoint}...")
            result = tester.test_get(endpoint)
            print(f"  Status: {result.get('status')} ({result.get('status_code', 'N/A')})")
    
    # Generate final report
    tester.generate_report(args.output)

if __name__ == "__main__":
    main()