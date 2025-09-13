#!/usr/bin/env python3
"""
Load Testing Validation Script
Validates performance analysis findings with actual load testing
"""

import asyncio
import aiohttp
import time
import statistics
import json
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Dict
import psutil

class LoadTestValidator:
    """Validates performance metrics through actual load testing"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = {
            'test_start': datetime.now().isoformat(),
            'system_info': self.get_system_info(),
            'test_results': []
        }
    
    def get_system_info(self) -> Dict:
        """Capture system information at test start"""
        memory = psutil.virtual_memory()
        return {
            'cpu_count': psutil.cpu_count(),
            'total_memory_gb': memory.total / 1024 / 1024 / 1024,
            'available_memory_gb': memory.available / 1024 / 1024 / 1024,
            'cpu_percent': psutil.cpu_percent(interval=1)
        }
    
    def test_single_request_performance(self, endpoint: str = "/health", iterations: int = 100) -> Dict:
        """Test single request performance metrics"""
        print(f"Testing single request performance: {endpoint}")
        
        response_times = []
        status_codes = []
        errors = []
        
        import requests
        session = requests.Session()
        
        for i in range(iterations):
            try:
                start_time = time.time()
                response = session.get(f"{self.base_url}{endpoint}", timeout=10)
                end_time = time.time()
                
                response_time = (end_time - start_time) * 1000  # ms
                response_times.append(response_time)
                status_codes.append(response.status_code)
                
                if i % 20 == 0:
                    print(f"  Request {i+1}/{iterations}: {response_time:.1f}ms")
                    
            except Exception as e:
                errors.append(str(e))
                if i % 20 == 0:
                    print(f"  Request {i+1}/{iterations}: ERROR - {str(e)[:50]}")
        
        # Calculate statistics
        if response_times:
            result = {
                'test_type': 'single_request',
                'endpoint': endpoint,
                'iterations': iterations,
                'successful_requests': len(response_times),
                'failed_requests': len(errors),
                'avg_response_time_ms': statistics.mean(response_times),
                'median_response_time_ms': statistics.median(response_times),
                'min_response_time_ms': min(response_times),
                'max_response_time_ms': max(response_times),
                'p95_response_time_ms': sorted(response_times)[int(len(response_times) * 0.95)] if response_times else 0,
                'p99_response_time_ms': sorted(response_times)[int(len(response_times) * 0.99)] if response_times else 0,
                'requests_per_second': len(response_times) / (max(response_times) / 1000) if response_times else 0,
                'success_rate': len(response_times) / iterations * 100,
                'errors': errors[:5]  # First 5 errors
            }
            
            print(f"  ✅ Average: {result['avg_response_time_ms']:.1f}ms")
            print(f"  ✅ P95: {result['p95_response_time_ms']:.1f}ms")
            print(f"  ✅ Success rate: {result['success_rate']:.1f}%")
            
            return result
        
        return {'test_type': 'single_request', 'status': 'failed', 'errors': errors}
    
    def test_concurrent_load(self, endpoint: str = "/health", concurrent_users: int = 50, requests_per_user: int = 10) -> Dict:
        """Test concurrent load performance"""
        print(f"Testing concurrent load: {concurrent_users} users, {requests_per_user} requests each")
        
        def worker_requests(worker_id: int) -> List[Dict]:
            """Worker function for concurrent requests"""
            import requests
            session = requests.Session()
            worker_results = []
            
            for req_id in range(requests_per_user):
                try:
                    start_time = time.time()
                    response = session.get(f"{self.base_url}{endpoint}", timeout=15)
                    end_time = time.time()
                    
                    worker_results.append({
                        'worker_id': worker_id,
                        'request_id': req_id,
                        'response_time_ms': (end_time - start_time) * 1000,
                        'status_code': response.status_code,
                        'success': True
                    })
                    
                except Exception as e:
                    worker_results.append({
                        'worker_id': worker_id,
                        'request_id': req_id,
                        'error': str(e),
                        'success': False
                    })
            
            return worker_results
        
        # Record system state before test
        start_memory = psutil.virtual_memory().percent
        start_cpu = psutil.cpu_percent()
        
        # Execute concurrent load test
        test_start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(worker_requests, worker_id) 
                      for worker_id in range(concurrent_users)]
            
            all_results = []
            completed_workers = 0
            
            for future in as_completed(futures):
                worker_results = future.result()
                all_results.extend(worker_results)
                completed_workers += 1
                
                if completed_workers % 10 == 0:
                    print(f"  Completed: {completed_workers}/{concurrent_users} workers")
        
        test_duration = time.time() - test_start_time
        
        # Record system state after test
        end_memory = psutil.virtual_memory().percent
        end_cpu = psutil.cpu_percent()
        
        # Analyze results
        successful_requests = [r for r in all_results if r.get('success', False)]
        failed_requests = [r for r in all_results if not r.get('success', False)]
        
        if successful_requests:
            response_times = [r['response_time_ms'] for r in successful_requests]
            
            result = {
                'test_type': 'concurrent_load',
                'endpoint': endpoint,
                'concurrent_users': concurrent_users,
                'requests_per_user': requests_per_user,
                'total_requests': len(all_results),
                'successful_requests': len(successful_requests),
                'failed_requests': len(failed_requests),
                'test_duration_seconds': test_duration,
                'requests_per_second': len(all_results) / test_duration,
                'avg_response_time_ms': statistics.mean(response_times),
                'median_response_time_ms': statistics.median(response_times),
                'p95_response_time_ms': sorted(response_times)[int(len(response_times) * 0.95)],
                'p99_response_time_ms': sorted(response_times)[int(len(response_times) * 0.99)],
                'min_response_time_ms': min(response_times),
                'max_response_time_ms': max(response_times),
                'success_rate': len(successful_requests) / len(all_results) * 100,
                'system_impact': {
                    'memory_increase_percent': end_memory - start_memory,
                    'cpu_usage_during_test': end_cpu,
                    'start_memory_percent': start_memory,
                    'end_memory_percent': end_memory
                }
            }
            
            print(f"  ✅ Avg response time: {result['avg_response_time_ms']:.1f}ms")
            print(f"  ✅ P95 response time: {result['p95_response_time_ms']:.1f}ms")
            print(f"  ✅ Requests/sec: {result['requests_per_second']:.1f}")
            print(f"  ✅ Success rate: {result['success_rate']:.1f}%")
            print(f"  ✅ Memory impact: +{result['system_impact']['memory_increase_percent']:.1f}%")
            
            return result
        
        return {'test_type': 'concurrent_load', 'status': 'failed', 'errors': failed_requests[:5]}
    
    def test_memory_usage_scaling(self, max_concurrent_users: int = 100, step: int = 25) -> Dict:
        """Test memory usage scaling with increasing load"""
        print(f"Testing memory usage scaling up to {max_concurrent_users} users")
        
        scaling_results = []
        baseline_memory = psutil.virtual_memory().percent
        
        for users in range(step, max_concurrent_users + 1, step):
            print(f"  Testing with {users} concurrent users...")
            
            # Run quick concurrent test
            result = self.test_concurrent_load("/health", users, 5)
            
            if result.get('system_impact'):
                memory_usage = result['system_impact']['end_memory_percent']
                memory_per_user = (memory_usage - baseline_memory) / users if users > 0 else 0
                
                scaling_results.append({
                    'concurrent_users': users,
                    'memory_percent': memory_usage,
                    'memory_per_user_percent': memory_per_user,
                    'avg_response_time_ms': result.get('avg_response_time_ms', 0),
                    'success_rate': result.get('success_rate', 0)
                })
                
                print(f"    Memory: {memory_usage:.1f}% (+{memory_per_user:.3f}% per user)")
                print(f"    Response time: {result.get('avg_response_time_ms', 0):.1f}ms")
        
        return {
            'test_type': 'memory_scaling',
            'baseline_memory_percent': baseline_memory,
            'max_users_tested': max_concurrent_users,
            'scaling_results': scaling_results,
            'memory_efficiency_score': self.calculate_memory_efficiency_score(scaling_results)
        }
    
    def calculate_memory_efficiency_score(self, scaling_results: List[Dict]) -> int:
        """Calculate memory efficiency score based on scaling results"""
        if not scaling_results:
            return 0
        
        # Score based on memory usage per user
        avg_memory_per_user = statistics.mean([r['memory_per_user_percent'] for r in scaling_results])
        
        if avg_memory_per_user < 0.1:
            return 100  # Excellent
        elif avg_memory_per_user < 0.2:
            return 85   # Very Good
        elif avg_memory_per_user < 0.5:
            return 70   # Good
        elif avg_memory_per_user < 1.0:
            return 55   # Acceptable
        else:
            return 30   # Poor
    
    def validate_performance_targets(self, results: Dict) -> Dict:
        """Validate results against performance targets"""
        validation = {
            'targets_met': 0,
            'total_targets': 0,
            'validations': []
        }
        
        # Target: Average response time < 200ms
        for result in results['test_results']:
            if 'avg_response_time_ms' in result:
                target_met = result['avg_response_time_ms'] < 200
                validation['validations'].append({
                    'target': 'Average response time < 200ms',
                    'actual': f"{result['avg_response_time_ms']:.1f}ms",
                    'met': target_met,
                    'test_type': result['test_type']
                })
                validation['total_targets'] += 1
                if target_met:
                    validation['targets_met'] += 1
        
        # Target: P95 response time < 300ms
        for result in results['test_results']:
            if 'p95_response_time_ms' in result:
                target_met = result['p95_response_time_ms'] < 300
                validation['validations'].append({
                    'target': 'P95 response time < 300ms',
                    'actual': f"{result['p95_response_time_ms']:.1f}ms",
                    'met': target_met,
                    'test_type': result['test_type']
                })
                validation['total_targets'] += 1
                if target_met:
                    validation['targets_met'] += 1
        
        # Target: Success rate > 99%
        for result in results['test_results']:
            if 'success_rate' in result:
                target_met = result['success_rate'] > 99
                validation['validations'].append({
                    'target': 'Success rate > 99%',
                    'actual': f"{result['success_rate']:.1f}%",
                    'met': target_met,
                    'test_type': result['test_type']
                })
                validation['total_targets'] += 1
                if target_met:
                    validation['targets_met'] += 1
        
        validation['success_percentage'] = (validation['targets_met'] / validation['total_targets'] * 100) if validation['total_targets'] > 0 else 0
        
        return validation
    
    def run_comprehensive_load_test(self) -> Dict:
        """Run comprehensive load testing validation"""
        print("🚀 Starting Comprehensive Load Test Validation")
        print("=" * 60)
        
        # Test 1: Single request performance baseline
        print("\n📊 Test 1: Single Request Performance")
        single_request_result = self.test_single_request_performance("/health", 50)
        self.results['test_results'].append(single_request_result)
        
        # Test 2: Light concurrent load
        print("\n📊 Test 2: Light Concurrent Load (25 users)")
        light_load_result = self.test_concurrent_load("/health", 25, 8)
        self.results['test_results'].append(light_load_result)
        
        # Test 3: Moderate concurrent load
        print("\n📊 Test 3: Moderate Concurrent Load (50 users)")
        moderate_load_result = self.test_concurrent_load("/health", 50, 6)
        self.results['test_results'].append(moderate_load_result)
        
        # Test 4: Memory usage scaling
        print("\n📊 Test 4: Memory Usage Scaling")
        memory_scaling_result = self.test_memory_usage_scaling(75, 25)
        self.results['test_results'].append(memory_scaling_result)
        
        # Validate against performance targets
        print("\n🎯 Validating Performance Targets")
        validation_results = self.validate_performance_targets(self.results)
        self.results['validation'] = validation_results
        
        # Print validation summary
        print(f"Targets met: {validation_results['targets_met']}/{validation_results['total_targets']} ({validation_results['success_percentage']:.1f}%)")
        
        for val in validation_results['validations']:
            status = "✅" if val['met'] else "❌"
            print(f"{status} {val['target']}: {val['actual']} ({val['test_type']})")
        
        self.results['test_end'] = datetime.now().isoformat()
        
        return self.results
    
    def save_results(self, filename: str = "load_test_validation_results.json"):
        """Save test results to JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n💾 Load test results saved to: {filename}")

def main():
    parser = argparse.ArgumentParser(description="Load Testing Validation")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL to test")
    parser.add_argument("--quick", action="store_true", help="Run quick validation test")
    parser.add_argument("--output", default="load_test_validation_results.json", help="Output file")
    
    args = parser.parse_args()
    
    validator = LoadTestValidator(args.base_url)
    
    if args.quick:
        print("🚀 Running Quick Load Test Validation")
        print("=" * 50)
        
        # Quick test: Just single request performance
        result = validator.test_single_request_performance("/health", 20)
        validator.results['test_results'].append(result)
        
        # Quick concurrent test
        result = validator.test_concurrent_load("/health", 10, 5)
        validator.results['test_results'].append(result)
        
    else:
        # Run comprehensive test suite
        validator.run_comprehensive_load_test()
    
    # Save results
    validator.save_results(args.output)
    
    print("\n🎉 Load test validation completed!")
    return 0

if __name__ == "__main__":
    exit(main())