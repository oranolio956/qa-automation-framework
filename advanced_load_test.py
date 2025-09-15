#!/usr/bin/env python3
"""
Advanced Load Testing for Automation System
Tests multiple endpoints with concurrent load and analyzes bottlenecks
"""

import asyncio
import aiohttp
import time
import json
import statistics
import psutil
import concurrent.futures
from datetime import datetime
from typing import List, Dict, Any

class AdvancedLoadTester:
    """Advanced load testing with detailed metrics"""
    
    def __init__(self):
        self.results = {}
        self.start_time = time.time()
        
    async def test_endpoint_under_load(self, url: str, concurrent_users: int = 10, 
                                     requests_per_user: int = 20, test_duration: int = 30) -> Dict[str, Any]:
        """Test single endpoint under sustained load"""
        print(f"Testing {url} with {concurrent_users} concurrent users for {test_duration}s...")
        
        response_times = []
        status_codes = {}
        errors = []
        start_time = time.time()
        
        async def user_load(user_id: int):
            async with aiohttp.ClientSession() as session:
                user_responses = []
                user_start = time.time()
                
                while time.time() - user_start < test_duration:
                    request_start = time.time()
                    
                    try:
                        async with session.get(url, timeout=10) as response:
                            response_time = (time.time() - request_start) * 1000
                            user_responses.append(response_time)
                            
                            status = response.status
                            status_codes[status] = status_codes.get(status, 0) + 1
                            
                    except Exception as e:
                        errors.append(f"User {user_id}: {str(e)}")
                    
                    # Small delay to prevent overwhelming
                    await asyncio.sleep(0.1)
                
                return user_responses
        
        # Run concurrent users
        tasks = [user_load(i) for i in range(concurrent_users)]
        user_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect all response times
        for user_responses in user_results:
            if isinstance(user_responses, list):
                response_times.extend(user_responses)
        
        total_time = time.time() - start_time
        total_requests = len(response_times)
        
        if response_times:
            results = {
                'url': url,
                'test_config': {
                    'concurrent_users': concurrent_users,
                    'test_duration_seconds': test_duration,
                    'actual_duration_seconds': total_time
                },
                'performance_metrics': {
                    'total_requests': total_requests,
                    'requests_per_second': total_requests / total_time,
                    'success_rate': ((total_requests - len(errors)) / max(total_requests, 1)) * 100,
                    'error_count': len(errors)
                },
                'response_times': {
                    'mean_ms': statistics.mean(response_times),
                    'median_ms': statistics.median(response_times),
                    'p95_ms': statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max(response_times),
                    'p99_ms': statistics.quantiles(response_times, n=100)[98] if len(response_times) > 100 else max(response_times),
                    'min_ms': min(response_times),
                    'max_ms': max(response_times),
                    'stddev_ms': statistics.stdev(response_times) if len(response_times) > 1 else 0
                },
                'status_codes': status_codes,
                'errors': errors[:10]  # First 10 errors for analysis
            }
        else:
            results = {
                'url': url,
                'error': 'No successful requests',
                'total_errors': len(errors),
                'sample_errors': errors[:5]
            }
        
        return results
    
    def test_database_under_load(self, operations: int = 1000) -> Dict[str, Any]:
        """Test database performance under load"""
        print(f"Testing database under load ({operations} operations)...")
        
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            
            # Test concurrent writes
            write_times = []
            read_times = []
            
            # Batch write test
            start_time = time.time()
            for i in range(operations):
                op_start = time.time()
                r.set(f"load_test_{i}", f"value_{i}_{time.time()}")
                write_times.append((time.time() - op_start) * 1000)
            total_write_time = time.time() - start_time
            
            # Batch read test
            start_time = time.time()
            for i in range(operations):
                op_start = time.time()
                r.get(f"load_test_{i}")
                read_times.append((time.time() - op_start) * 1000)
            total_read_time = time.time() - start_time
            
            # Cleanup
            for i in range(operations):
                r.delete(f"load_test_{i}")
            
            return {
                'database_type': 'Redis',
                'operations_tested': operations,
                'write_performance': {
                    'total_time_seconds': total_write_time,
                    'operations_per_second': operations / total_write_time,
                    'mean_time_ms': statistics.mean(write_times),
                    'p95_time_ms': statistics.quantiles(write_times, n=20)[18] if len(write_times) > 20 else max(write_times),
                    'max_time_ms': max(write_times)
                },
                'read_performance': {
                    'total_time_seconds': total_read_time,
                    'operations_per_second': operations / total_read_time,
                    'mean_time_ms': statistics.mean(read_times),
                    'p95_time_ms': statistics.quantiles(read_times, n=20)[18] if len(read_times) > 20 else max(read_times),
                    'max_time_ms': max(read_times)
                },
                'status': 'success'
            }
            
        except Exception as e:
            return {
                'database_type': 'Redis',
                'status': 'failed',
                'error': str(e)
            }
    
    def monitor_system_resources(self, duration: int = 30) -> Dict[str, Any]:
        """Monitor system resources during load testing"""
        print(f"Monitoring system resources for {duration} seconds...")
        
        samples = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            sample = {
                'timestamp': time.time() - start_time,
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'memory_percent': psutil.virtual_memory().percent,
                'memory_used_gb': psutil.virtual_memory().used / 1024**3,
                'disk_io': psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {},
                'network_io': psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {},
                'active_processes': len(psutil.pids())
            }
            samples.append(sample)
            time.sleep(1)
        
        if samples:
            cpu_values = [s['cpu_percent'] for s in samples]
            memory_values = [s['memory_percent'] for s in samples]
            
            return {
                'monitoring_duration_seconds': duration,
                'sample_count': len(samples),
                'cpu_usage': {
                    'mean_percent': statistics.mean(cpu_values),
                    'max_percent': max(cpu_values),
                    'min_percent': min(cpu_values),
                    'stddev_percent': statistics.stdev(cpu_values) if len(cpu_values) > 1 else 0
                },
                'memory_usage': {
                    'mean_percent': statistics.mean(memory_values),
                    'max_percent': max(memory_values),
                    'min_percent': min(memory_values),
                    'peak_used_gb': max([s['memory_used_gb'] for s in samples])
                },
                'samples': samples[-5:]  # Last 5 samples for reference
            }
        
        return {'error': 'No samples collected'}
    
    def test_memory_stress(self, max_memory_mb: int = 500) -> Dict[str, Any]:
        """Test system behavior under memory stress"""
        print(f"Testing memory stress up to {max_memory_mb}MB...")
        
        initial_memory = psutil.virtual_memory().percent
        memory_hogs = []
        
        try:
            # Gradually increase memory usage
            chunk_size = 50  # MB per chunk
            chunks_created = 0
            
            while chunks_created * chunk_size < max_memory_mb:
                # Create memory chunk
                chunk = [0] * (chunk_size * 1024 * 256)  # Approximately chunk_size MB
                memory_hogs.append(chunk)
                chunks_created += 1
                
                current_memory = psutil.virtual_memory().percent
                
                if current_memory > 90:  # Stop if memory usage gets too high
                    break
                
                time.sleep(0.5)
            
            peak_memory = psutil.virtual_memory().percent
            
            # Hold memory for a moment
            time.sleep(2)
            
            # Release memory
            del memory_hogs
            time.sleep(2)
            
            final_memory = psutil.virtual_memory().percent
            
            return {
                'memory_stress_test': {
                    'target_memory_mb': max_memory_mb,
                    'chunks_created': chunks_created,
                    'initial_memory_percent': initial_memory,
                    'peak_memory_percent': peak_memory,
                    'final_memory_percent': final_memory,
                    'memory_increase_percent': peak_memory - initial_memory,
                    'memory_released_percent': peak_memory - final_memory
                }
            }
            
        except Exception as e:
            return {
                'memory_stress_test': {
                    'error': str(e),
                    'chunks_created': chunks_created
                }
            }
    
    async def comprehensive_load_test(self) -> Dict[str, Any]:
        """Run comprehensive load testing suite"""
        print("Starting Comprehensive Load Testing Suite")
        print("=" * 60)
        
        # Test multiple endpoints
        endpoints = [
            'http://localhost:8888/health',
            'http://localhost:5000/health'
            # Add more endpoints as available
        ]
        
        endpoint_results = []
        
        for endpoint in endpoints:
            print(f"\nTesting endpoint: {endpoint}")
            try:
                result = await self.test_endpoint_under_load(
                    endpoint, 
                    concurrent_users=15, 
                    test_duration=20
                )
                endpoint_results.append(result)
                
                if 'performance_metrics' in result:
                    pm = result['performance_metrics']
                    rt = result['response_times']
                    print(f"  Results: {pm['requests_per_second']:.1f} RPS, {pm['success_rate']:.1f}% success, {rt['mean_ms']:.1f}ms avg")
                
            except Exception as e:
                print(f"  Failed: {e}")
                endpoint_results.append({'url': endpoint, 'error': str(e)})
        
        # Test database performance
        print("\nTesting database performance under load...")
        db_result = self.test_database_under_load(operations=2000)
        
        if db_result.get('status') == 'success':
            wp = db_result['write_performance']
            rp = db_result['read_performance']
            print(f"  Database: {wp['operations_per_second']:.0f} writes/sec, {rp['operations_per_second']:.0f} reads/sec")
        
        # Monitor system resources
        print("\nMonitoring system resources...")
        resource_monitoring = self.monitor_system_resources(duration=25)
        
        if 'cpu_usage' in resource_monitoring:
            cpu = resource_monitoring['cpu_usage']
            mem = resource_monitoring['memory_usage']
            print(f"  Resources: {cpu['mean_percent']:.1f}% avg CPU (max {cpu['max_percent']:.1f}%), {mem['mean_percent']:.1f}% avg memory")
        
        # Memory stress test
        print("\nRunning memory stress test...")
        memory_stress = self.test_memory_stress(max_memory_mb=300)
        
        if 'memory_stress_test' in memory_stress:
            mst = memory_stress['memory_stress_test']
            if 'memory_increase_percent' in mst:
                print(f"  Memory stress: +{mst['memory_increase_percent']:.1f}% peak increase")
        
        # Compile results
        results = {
            'test_metadata': {
                'timestamp': datetime.now().isoformat(),
                'total_test_duration_minutes': (time.time() - self.start_time) / 60
            },
            'endpoint_load_tests': endpoint_results,
            'database_load_test': db_result,
            'system_resource_monitoring': resource_monitoring,
            'memory_stress_test': memory_stress
        }
        
        return results
    
    def analyze_load_test_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze load test results for bottlenecks and recommendations"""
        analysis = {
            'performance_summary': {},
            'bottlenecks_identified': [],
            'recommendations': [],
            'scalability_assessment': {}
        }
        
        # Analyze endpoint performance
        endpoint_tests = results.get('endpoint_load_tests', [])
        successful_tests = [t for t in endpoint_tests if 'performance_metrics' in t]
        
        if successful_tests:
            avg_rps = statistics.mean([t['performance_metrics']['requests_per_second'] for t in successful_tests])
            avg_response_time = statistics.mean([t['response_times']['mean_ms'] for t in successful_tests])
            min_success_rate = min([t['performance_metrics']['success_rate'] for t in successful_tests])
            
            analysis['performance_summary']['endpoints'] = {
                'average_requests_per_second': avg_rps,
                'average_response_time_ms': avg_response_time,
                'minimum_success_rate': min_success_rate,
                'endpoints_tested': len(successful_tests)
            }
            
            # Identify bottlenecks
            if avg_response_time > 500:
                analysis['bottlenecks_identified'].append(f"High average response time: {avg_response_time:.1f}ms")
            
            if min_success_rate < 95:
                analysis['bottlenecks_identified'].append(f"Low success rate under load: {min_success_rate:.1f}%")
            
            if avg_rps < 50:
                analysis['bottlenecks_identified'].append(f"Low throughput: {avg_rps:.1f} requests/second")
        
        # Analyze database performance
        db_test = results.get('database_load_test', {})
        if db_test.get('status') == 'success':
            write_ops_per_sec = db_test['write_performance']['operations_per_second']
            read_ops_per_sec = db_test['read_performance']['operations_per_second']
            
            analysis['performance_summary']['database'] = {
                'write_operations_per_second': write_ops_per_sec,
                'read_operations_per_second': read_ops_per_sec
            }
            
            if write_ops_per_sec < 500:
                analysis['bottlenecks_identified'].append(f"Slow database writes: {write_ops_per_sec:.0f} ops/sec")
            
            if read_ops_per_sec < 1000:
                analysis['bottlenecks_identified'].append(f"Slow database reads: {read_ops_per_sec:.0f} ops/sec")
        
        # Analyze system resources
        resource_monitoring = results.get('system_resource_monitoring', {})
        if 'cpu_usage' in resource_monitoring:
            cpu = resource_monitoring['cpu_usage']
            memory = resource_monitoring['memory_usage']
            
            analysis['performance_summary']['system_resources'] = {
                'peak_cpu_percent': cpu['max_percent'],
                'average_cpu_percent': cpu['mean_percent'],
                'peak_memory_percent': memory['max_percent'],
                'average_memory_percent': memory['mean_percent']
            }
            
            if cpu['max_percent'] > 80:
                analysis['bottlenecks_identified'].append(f"High CPU usage under load: {cpu['max_percent']:.1f}% peak")
            
            if memory['max_percent'] > 85:
                analysis['bottlenecks_identified'].append(f"High memory usage under load: {memory['max_percent']:.1f}% peak")
        
        # Generate recommendations
        if analysis['bottlenecks_identified']:
            analysis['recommendations'].extend([
                "Optimize slow-performing endpoints and database queries",
                "Consider implementing connection pooling and caching",
                "Monitor resource usage in production and set up alerts",
                "Consider horizontal scaling if vertical scaling is insufficient"
            ])
        else:
            analysis['recommendations'].append("System performance is good under current load levels")
        
        # Scalability assessment
        if successful_tests:
            max_rps = max([t['performance_metrics']['requests_per_second'] for t in successful_tests])
            
            # Rough scalability projections
            analysis['scalability_assessment'] = {
                'current_max_rps': max_rps,
                'estimated_daily_capacity': int(max_rps * 86400),  # requests per day
                'estimated_concurrent_users': int(max_rps * 2),  # rough estimate
                'scaling_recommendation': (
                    "Good for small-medium scale" if max_rps > 100 else
                    "Needs optimization for production scale" if max_rps > 50 else
                    "Requires significant optimization"
                )
            }
        
        return analysis
    
    def print_comprehensive_results(self, results: Dict[str, Any], analysis: Dict[str, Any]):
        """Print comprehensive load test results"""
        print("\n" + "=" * 80)
        print("COMPREHENSIVE LOAD TEST RESULTS")
        print("=" * 80)
        
        # Performance Summary
        perf_summary = analysis.get('performance_summary', {})
        
        if 'endpoints' in perf_summary:
            ep = perf_summary['endpoints']
            print(f"\nAPI ENDPOINT PERFORMANCE:")
            print(f"  • Average Throughput: {ep['average_requests_per_second']:.1f} requests/second")
            print(f"  • Average Response Time: {ep['average_response_time_ms']:.1f}ms")
            print(f"  • Minimum Success Rate: {ep['minimum_success_rate']:.1f}%")
            print(f"  • Endpoints Tested: {ep['endpoints_tested']}")
        
        if 'database' in perf_summary:
            db = perf_summary['database']
            print(f"\nDATABASE PERFORMANCE:")
            print(f"  • Write Operations: {db['write_operations_per_second']:.0f} ops/second")
            print(f"  • Read Operations: {db['read_operations_per_second']:.0f} ops/second")
        
        if 'system_resources' in perf_summary:
            sr = perf_summary['system_resources']
            print(f"\nSYSTEM RESOURCES UNDER LOAD:")
            print(f"  • Peak CPU Usage: {sr['peak_cpu_percent']:.1f}%")
            print(f"  • Average CPU Usage: {sr['average_cpu_percent']:.1f}%")
            print(f"  • Peak Memory Usage: {sr['peak_memory_percent']:.1f}%")
            print(f"  • Average Memory Usage: {sr['average_memory_percent']:.1f}%")
        
        # Scalability Assessment
        scalability = analysis.get('scalability_assessment', {})
        if scalability:
            print(f"\nSCALABILITY ASSESSMENT:")
            print(f"  • Current Max Throughput: {scalability['current_max_rps']:.1f} RPS")
            print(f"  • Estimated Daily Capacity: {scalability['estimated_daily_capacity']:,} requests")
            print(f"  • Estimated Concurrent Users: {scalability['estimated_concurrent_users']:,}")
            print(f"  • Scaling Recommendation: {scalability['scaling_recommendation']}")
        
        # Bottlenecks
        bottlenecks = analysis.get('bottlenecks_identified', [])
        if bottlenecks:
            print(f"\nBOTTLENECKS IDENTIFIED:")
            for bottleneck in bottlenecks:
                print(f"  ⚠️  {bottleneck}")
        
        # Recommendations
        recommendations = analysis.get('recommendations', [])
        if recommendations:
            print(f"\nRECOMMENDATIONS:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
        
        print("\n" + "=" * 80)

async def main():
    """Run advanced load testing"""
    tester = AdvancedLoadTester()
    
    try:
        # Run comprehensive load test
        results = await tester.comprehensive_load_test()
        
        # Analyze results
        analysis = tester.analyze_load_test_results(results)
        
        # Save detailed results
        output_file = f"advanced_load_test_results_{int(time.time())}.json"
        comprehensive_report = {
            'test_results': results,
            'analysis': analysis
        }
        
        with open(output_file, 'w') as f:
            json.dump(comprehensive_report, f, indent=2, default=str)
        
        # Print results
        tester.print_comprehensive_results(results, analysis)
        
        print(f"\nDetailed results saved to: {output_file}")
        
    except KeyboardInterrupt:
        print("\nLoad test interrupted by user")
    except Exception as e:
        print(f"\nLoad test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
