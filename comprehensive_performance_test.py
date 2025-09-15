#!/usr/bin/env python3
"""
Comprehensive Performance Testing Suite for Automation System
Testing all components: API endpoints, database queries, memory usage, network latency, concurrent users
"""

import asyncio
import aiohttp
import time
import json
import statistics
import psutil
import threading
import subprocess
import requests
import redis
import sqlite3
import concurrent.futures
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend

class PerformanceTestSuite:
    """Comprehensive performance testing framework"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = {}
        self.monitoring_data = {
            'cpu_usage': [],
            'memory_usage': [],
            'network_io': [],
            'disk_io': []
        }
        self.start_time = time.time()
        self.monitoring_active = False
        
    def start_system_monitoring(self):
        """Start continuous system monitoring"""
        self.monitoring_active = True
        
        def monitor():
            while self.monitoring_active:
                timestamp = time.time()
                
                # CPU Usage
                cpu_percent = psutil.cpu_percent(interval=0.1)
                self.monitoring_data['cpu_usage'].append({
                    'timestamp': timestamp,
                    'value': cpu_percent
                })
                
                # Memory Usage
                memory = psutil.virtual_memory()
                self.monitoring_data['memory_usage'].append({
                    'timestamp': timestamp,
                    'percent': memory.percent,
                    'used_mb': memory.used / 1024 / 1024,
                    'available_mb': memory.available / 1024 / 1024
                })
                
                # Network I/O
                net_io = psutil.net_io_counters()
                self.monitoring_data['network_io'].append({
                    'timestamp': timestamp,
                    'bytes_sent': net_io.bytes_sent,
                    'bytes_recv': net_io.bytes_recv,
                    'packets_sent': net_io.packets_sent,
                    'packets_recv': net_io.packets_recv
                })
                
                # Disk I/O
                disk_io = psutil.disk_io_counters()
                if disk_io:
                    self.monitoring_data['disk_io'].append({
                        'timestamp': timestamp,
                        'read_bytes': disk_io.read_bytes,
                        'write_bytes': disk_io.write_bytes,
                        'read_count': disk_io.read_count,
                        'write_count': disk_io.write_count
                    })
                
                time.sleep(0.5)  # Sample every 500ms
        
        self.monitor_thread = threading.Thread(target=monitor, daemon=True)
        self.monitor_thread.start()
        
    def stop_system_monitoring(self):
        """Stop system monitoring"""
        self.monitoring_active = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=2)
    
    async def test_api_endpoint_performance(self, endpoint: str, method: str = 'GET', 
                                          payload: dict = None, iterations: int = 100) -> Dict[str, Any]:
        """Test individual API endpoint performance"""
        print(f"Testing {method} {endpoint} - {iterations} iterations...")
        
        response_times = []
        success_count = 0
        error_count = 0
        status_codes = {}
        
        headers = {'Content-Type': 'application/json'}
        if endpoint != '/health':  # Add auth for non-health endpoints
            headers['Authorization'] = 'Bearer test-token-change-me'
        
        async with aiohttp.ClientSession() as session:
            for i in range(iterations):
                start_time = time.time()
                
                try:
                    if method == 'GET':
                        async with session.get(f"{self.base_url}{endpoint}", headers=headers) as response:
                            response_time = (time.time() - start_time) * 1000
                            response_times.append(response_time)
                            
                            status = response.status
                            status_codes[status] = status_codes.get(status, 0) + 1
                            
                            if 200 <= status < 400:
                                success_count += 1
                            else:
                                error_count += 1
                                
                    elif method == 'POST':
                        async with session.post(f"{self.base_url}{endpoint}", 
                                               json=payload, headers=headers) as response:
                            response_time = (time.time() - start_time) * 1000
                            response_times.append(response_time)
                            
                            status = response.status
                            status_codes[status] = status_codes.get(status, 0) + 1
                            
                            if 200 <= status < 400:
                                success_count += 1
                            else:
                                error_count += 1
                                
                except Exception as e:
                    error_count += 1
                    print(f"Request {i+1} failed: {e}")
        
        if response_times:
            results = {
                'endpoint': endpoint,
                'method': method,
                'iterations': iterations,
                'success_count': success_count,
                'error_count': error_count,
                'success_rate': (success_count / iterations) * 100,
                'response_times': {
                    'mean': statistics.mean(response_times),
                    'median': statistics.median(response_times),
                    'p95': np.percentile(response_times, 95),
                    'p99': np.percentile(response_times, 99),
                    'min': min(response_times),
                    'max': max(response_times),
                    'stddev': statistics.stdev(response_times) if len(response_times) > 1 else 0
                },
                'status_codes': status_codes,
                'throughput_rps': success_count / (max(response_times) / 1000) if response_times else 0
            }
        else:
            results = {
                'endpoint': endpoint,
                'method': method,
                'error': 'No successful requests',
                'error_count': error_count
            }
        
        return results
    
    def test_database_performance(self) -> Dict[str, Any]:
        """Test database query performance"""
        print("Testing database performance...")
        
        results = {}
        
        # Test Redis performance
        try:
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            
            # Test Redis write performance
            write_times = []
            for i in range(1000):
                start_time = time.time()
                r.set(f"test_key_{i}", f"test_value_{i}")
                write_times.append((time.time() - start_time) * 1000)
            
            # Test Redis read performance
            read_times = []
            for i in range(1000):
                start_time = time.time()
                r.get(f"test_key_{i}")
                read_times.append((time.time() - start_time) * 1000)
            
            # Cleanup
            for i in range(1000):
                r.delete(f"test_key_{i}")
            
            results['redis'] = {
                'write_performance': {
                    'mean_ms': statistics.mean(write_times),
                    'p95_ms': np.percentile(write_times, 95),
                    'p99_ms': np.percentile(write_times, 99),
                    'operations_per_second': 1000 / (sum(write_times) / 1000)
                },
                'read_performance': {
                    'mean_ms': statistics.mean(read_times),
                    'p95_ms': np.percentile(read_times, 95),
                    'p99_ms': np.percentile(read_times, 99),
                    'operations_per_second': 1000 / (sum(read_times) / 1000)
                },
                'status': 'connected'
            }
            
        except Exception as e:
            results['redis'] = {'status': 'disconnected', 'error': str(e)}
        
        # Test SQLite performance (if available)
        try:
            db_path = '/tmp/performance_test.db'
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create test table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_test (
                    id INTEGER PRIMARY KEY,
                    data TEXT,
                    timestamp REAL
                )
            ''')
            
            # Test insert performance
            insert_times = []
            for i in range(1000):
                start_time = time.time()
                cursor.execute(
                    "INSERT INTO performance_test (data, timestamp) VALUES (?, ?)",
                    (f"test_data_{i}", time.time())
                )
                insert_times.append((time.time() - start_time) * 1000)
            conn.commit()
            
            # Test query performance
            query_times = []
            for i in range(100):
                start_time = time.time()
                cursor.execute("SELECT * FROM performance_test WHERE id = ?", (i + 1,))
                cursor.fetchone()
                query_times.append((time.time() - start_time) * 1000)
            
            # Cleanup
            cursor.execute("DROP TABLE performance_test")
            conn.close()
            
            results['sqlite'] = {
                'insert_performance': {
                    'mean_ms': statistics.mean(insert_times),
                    'p95_ms': np.percentile(insert_times, 95),
                    'operations_per_second': 1000 / (sum(insert_times) / 1000)
                },
                'query_performance': {
                    'mean_ms': statistics.mean(query_times),
                    'p95_ms': np.percentile(query_times, 95),
                    'operations_per_second': 100 / (sum(query_times) / 1000)
                },
                'status': 'available'
            }
            
        except Exception as e:
            results['sqlite'] = {'status': 'unavailable', 'error': str(e)}
        
        return results
    
    def test_memory_usage_patterns(self, duration: int = 30) -> Dict[str, Any]:
        """Test memory usage patterns under load"""
        print(f"Testing memory usage patterns for {duration} seconds...")
        
        memory_snapshots = []
        start_time = time.time()
        
        # Baseline memory usage
        initial_memory = psutil.virtual_memory()
        
        # Create memory pressure
        memory_hogs = []
        
        def create_memory_load():
            # Create some data structures to simulate load
            data = []
            for i in range(10000):
                data.append({
                    'id': i,
                    'data': f"memory_test_data_{i}" * 100,
                    'timestamp': time.time(),
                    'nested': {
                        'level1': [j for j in range(50)],
                        'level2': {f"key_{k}": f"value_{k}" for k in range(20)}
                    }
                })
            return data
        
        # Monitor memory while creating load
        load_thread = threading.Thread(target=lambda: memory_hogs.append(create_memory_load()))
        load_thread.start()
        
        while time.time() - start_time < duration:
            memory = psutil.virtual_memory()
            memory_snapshots.append({
                'timestamp': time.time() - start_time,
                'percent_used': memory.percent,
                'used_mb': memory.used / 1024 / 1024,
                'available_mb': memory.available / 1024 / 1024,
                'cached_mb': getattr(memory, 'cached', 0) / 1024 / 1024,
                'buffers_mb': getattr(memory, 'buffers', 0) / 1024 / 1024
            })
            time.sleep(1)
        
        load_thread.join()
        
        # Calculate memory usage statistics
        if memory_snapshots:
            used_mb_values = [s['used_mb'] for s in memory_snapshots]
            percent_values = [s['percent_used'] for s in memory_snapshots]
            
            results = {
                'initial_memory_mb': initial_memory.used / 1024 / 1024,
                'peak_memory_mb': max(used_mb_values),
                'average_memory_mb': statistics.mean(used_mb_values),
                'memory_growth_mb': max(used_mb_values) - min(used_mb_values),
                'peak_percent': max(percent_values),
                'average_percent': statistics.mean(percent_values),
                'samples': len(memory_snapshots),
                'test_duration_seconds': duration,
                'snapshots': memory_snapshots[-10:]  # Last 10 samples
            }
        else:
            results = {'error': 'No memory snapshots collected'}
        
        # Cleanup memory
        del memory_hogs
        
        return results
    
    async def test_concurrent_users(self, endpoint: str = '/health', 
                                  concurrent_users: int = 50, 
                                  requests_per_user: int = 10) -> Dict[str, Any]:
        """Simulate concurrent users"""
        print(f"Testing {concurrent_users} concurrent users, {requests_per_user} requests each...")
        
        all_response_times = []
        success_count = 0
        error_count = 0
        start_time = time.time()
        
        async def user_session(user_id: int):
            nonlocal success_count, error_count
            session_times = []
            
            headers = {'Content-Type': 'application/json'}
            if endpoint != '/health':
                headers['Authorization'] = f'Bearer test-token-user-{user_id}'
            
            async with aiohttp.ClientSession() as session:
                for request_num in range(requests_per_user):
                    request_start = time.time()
                    
                    try:
                        async with session.get(f"{self.base_url}{endpoint}", headers=headers) as response:
                            response_time = (time.time() - request_start) * 1000
                            session_times.append(response_time)
                            
                            if 200 <= response.status < 400:
                                success_count += 1
                            else:
                                error_count += 1
                                
                    except Exception as e:
                        error_count += 1
                        print(f"User {user_id} request {request_num + 1} failed: {e}")
            
            return session_times
        
        # Run concurrent user sessions
        tasks = [user_session(user_id) for user_id in range(concurrent_users)]
        session_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect all response times
        for session_times in session_results:
            if isinstance(session_times, list):
                all_response_times.extend(session_times)
        
        total_time = time.time() - start_time
        total_requests = concurrent_users * requests_per_user
        
        if all_response_times:
            results = {
                'concurrent_users': concurrent_users,
                'requests_per_user': requests_per_user,
                'total_requests': total_requests,
                'success_count': success_count,
                'error_count': error_count,
                'success_rate': (success_count / total_requests) * 100,
                'total_test_time_seconds': total_time,
                'throughput_rps': success_count / total_time,
                'response_times': {
                    'mean': statistics.mean(all_response_times),
                    'median': statistics.median(all_response_times),
                    'p95': np.percentile(all_response_times, 95),
                    'p99': np.percentile(all_response_times, 99),
                    'min': min(all_response_times),
                    'max': max(all_response_times)
                }
            }
        else:
            results = {
                'error': 'No successful requests',
                'concurrent_users': concurrent_users,
                'total_requests': total_requests,
                'error_count': error_count
            }
        
        return results
    
    def test_network_latency(self) -> Dict[str, Any]:
        """Test network latency and connectivity"""
        print("Testing network latency...")
        
        results = {}
        
        # Test local API latency
        api_times = []
        for i in range(20):
            start_time = time.time()
            try:
                response = requests.get(f"{self.base_url}/health", timeout=10)
                latency = (time.time() - start_time) * 1000
                api_times.append(latency)
            except Exception as e:
                print(f"API latency test {i+1} failed: {e}")
        
        if api_times:
            results['api_latency'] = {
                'mean_ms': statistics.mean(api_times),
                'median_ms': statistics.median(api_times),
                'p95_ms': np.percentile(api_times, 95),
                'min_ms': min(api_times),
                'max_ms': max(api_times),
                'samples': len(api_times)
            }
        
        # Test external connectivity
        external_hosts = [
            'https://httpbin.org/delay/0',
            'https://jsonplaceholder.typicode.com/posts/1',
            'https://api.github.com'
        ]
        
        results['external_connectivity'] = {}
        
        for host in external_hosts:
            host_times = []
            for i in range(5):
                start_time = time.time()
                try:
                    response = requests.get(host, timeout=10)
                    latency = (time.time() - start_time) * 1000
                    host_times.append(latency)
                except Exception as e:
                    print(f"External connectivity test to {host} failed: {e}")
            
            if host_times:
                results['external_connectivity'][host] = {
                    'mean_ms': statistics.mean(host_times),
                    'min_ms': min(host_times),
                    'max_ms': max(host_times),
                    'samples': len(host_times)
                }
        
        return results
    
    def identify_bottlenecks(self) -> Dict[str, Any]:
        """Analyze results to identify performance bottlenecks"""
        print("Analyzing performance bottlenecks...")
        
        bottlenecks = {
            'critical_issues': [],
            'warnings': [],
            'recommendations': []
        }
        
        # Analyze API performance
        if 'api_endpoints' in self.results:
            for endpoint_result in self.results['api_endpoints']:
                if 'response_times' in endpoint_result:
                    mean_time = endpoint_result['response_times']['mean']
                    p95_time = endpoint_result['response_times']['p95']
                    
                    if mean_time > 1000:  # > 1 second
                        bottlenecks['critical_issues'].append(
                            f"Endpoint {endpoint_result['endpoint']} has high mean response time: {mean_time:.1f}ms"
                        )
                    elif mean_time > 500:  # > 500ms
                        bottlenecks['warnings'].append(
                            f"Endpoint {endpoint_result['endpoint']} response time could be improved: {mean_time:.1f}ms"
                        )
                    
                    if p95_time > 2000:  # > 2 seconds for 95th percentile
                        bottlenecks['critical_issues'].append(
                            f"Endpoint {endpoint_result['endpoint']} has high P95 response time: {p95_time:.1f}ms"
                        )
        
        # Analyze database performance
        if 'database' in self.results:
            db_results = self.results['database']
            
            if 'redis' in db_results and 'read_performance' in db_results['redis']:
                redis_read_time = db_results['redis']['read_performance']['mean_ms']
                if redis_read_time > 10:
                    bottlenecks['warnings'].append(
                        f"Redis read performance is slow: {redis_read_time:.2f}ms average"
                    )
        
        # Analyze memory usage
        if 'memory_usage' in self.results:
            memory_results = self.results['memory_usage']
            if 'peak_percent' in memory_results:
                if memory_results['peak_percent'] > 85:
                    bottlenecks['critical_issues'].append(
                        f"High memory usage detected: {memory_results['peak_percent']:.1f}% peak"
                    )
                elif memory_results['peak_percent'] > 70:
                    bottlenecks['warnings'].append(
                        f"Moderate memory usage: {memory_results['peak_percent']:.1f}% peak"
                    )
        
        # Analyze concurrent user performance
        if 'concurrent_users' in self.results:
            concurrent_results = self.results['concurrent_users']
            if 'success_rate' in concurrent_results:
                if concurrent_results['success_rate'] < 95:
                    bottlenecks['critical_issues'].append(
                        f"Low success rate under load: {concurrent_results['success_rate']:.1f}%"
                    )
                
                if concurrent_results.get('throughput_rps', 0) < 10:
                    bottlenecks['warnings'].append(
                        f"Low throughput under load: {concurrent_results.get('throughput_rps', 0):.1f} RPS"
                    )
        
        # Generate recommendations
        if bottlenecks['critical_issues']:
            bottlenecks['recommendations'].extend([
                "Consider implementing connection pooling for database operations",
                "Add caching layers for frequently accessed data",
                "Optimize database queries and add appropriate indexes",
                "Consider horizontal scaling or load balancing"
            ])
        
        if bottlenecks['warnings']:
            bottlenecks['recommendations'].extend([
                "Monitor resource usage in production",
                "Consider implementing request/response compression",
                "Optimize memory allocation patterns",
                "Add performance monitoring and alerting"
            ])
        
        return bottlenecks
    
    def generate_performance_graphs(self, output_dir: str = "performance_graphs"):
        """Generate performance visualization graphs"""
        Path(output_dir).mkdir(exist_ok=True)
        
        # System monitoring graphs
        if self.monitoring_data['cpu_usage']:
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
            
            # CPU Usage
            cpu_times = [d['timestamp'] - self.start_time for d in self.monitoring_data['cpu_usage']]
            cpu_values = [d['value'] for d in self.monitoring_data['cpu_usage']]
            ax1.plot(cpu_times, cpu_values, 'b-', linewidth=2)
            ax1.set_title('CPU Usage Over Time')
            ax1.set_xlabel('Time (seconds)')
            ax1.set_ylabel('CPU Usage (%)')
            ax1.grid(True)
            
            # Memory Usage
            mem_times = [d['timestamp'] - self.start_time for d in self.monitoring_data['memory_usage']]
            mem_values = [d['percent'] for d in self.monitoring_data['memory_usage']]
            ax2.plot(mem_times, mem_values, 'r-', linewidth=2)
            ax2.set_title('Memory Usage Over Time')
            ax2.set_xlabel('Time (seconds)')
            ax2.set_ylabel('Memory Usage (%)')
            ax2.grid(True)
            
            # Network I/O
            if self.monitoring_data['network_io']:
                net_times = [d['timestamp'] - self.start_time for d in self.monitoring_data['network_io']]
                net_sent = [d['bytes_sent'] / 1024 / 1024 for d in self.monitoring_data['network_io']]
                net_recv = [d['bytes_recv'] / 1024 / 1024 for d in self.monitoring_data['network_io']]
                ax3.plot(net_times, net_sent, 'g-', label='Sent (MB)', linewidth=2)
                ax3.plot(net_times, net_recv, 'orange', label='Received (MB)', linewidth=2)
                ax3.set_title('Network I/O Over Time')
                ax3.set_xlabel('Time (seconds)')
                ax3.set_ylabel('Network I/O (MB)')
                ax3.legend()
                ax3.grid(True)
            
            # Response time distribution (if API results available)
            if 'api_endpoints' in self.results and self.results['api_endpoints']:
                response_times = []
                for endpoint_result in self.results['api_endpoints']:
                    if 'response_times' in endpoint_result:
                        response_times.append(endpoint_result['response_times']['mean'])
                
                if response_times:
                    ax4.hist(response_times, bins=20, alpha=0.7, color='purple')
                    ax4.set_title('API Response Time Distribution')
                    ax4.set_xlabel('Response Time (ms)')
                    ax4.set_ylabel('Frequency')
                    ax4.grid(True)
            
            plt.tight_layout()
            plt.savefig(f'{output_dir}/system_performance.png', dpi=150, bbox_inches='tight')
            plt.close()
            
            print(f"Performance graphs saved to {output_dir}/")
    
    def calculate_performance_score(self) -> Dict[str, Any]:
        """Calculate overall performance score (0-100)"""
        score = 100
        details = {'deductions': []}
        
        # API Performance (40 points max)
        api_score = 40
        if 'api_endpoints' in self.results:
            for endpoint_result in self.results['api_endpoints']:
                if 'response_times' in endpoint_result:
                    mean_time = endpoint_result['response_times']['mean']
                    if mean_time > 1000:
                        deduction = min(20, (mean_time - 1000) / 50)
                        api_score -= deduction
                        details['deductions'].append(f"API {endpoint_result['endpoint']}: -{deduction:.1f} points for slow response")
        
        # Database Performance (20 points max)
        db_score = 20
        if 'database' in self.results:
            db_results = self.results['database']
            if 'redis' in db_results and 'read_performance' in db_results['redis']:
                redis_time = db_results['redis']['read_performance']['mean_ms']
                if redis_time > 5:
                    deduction = min(10, (redis_time - 5) / 2)
                    db_score -= deduction
                    details['deductions'].append(f"Database: -{deduction:.1f} points for slow Redis")
        
        # Memory Usage (20 points max)
        memory_score = 20
        if 'memory_usage' in self.results:
            peak_percent = self.results['memory_usage'].get('peak_percent', 0)
            if peak_percent > 80:
                deduction = min(15, (peak_percent - 80) / 2)
                memory_score -= deduction
                details['deductions'].append(f"Memory: -{deduction:.1f} points for high usage")
        
        # Concurrency Performance (20 points max)
        concurrency_score = 20
        if 'concurrent_users' in self.results:
            success_rate = self.results['concurrent_users'].get('success_rate', 100)
            if success_rate < 98:
                deduction = min(15, (98 - success_rate) * 2)
                concurrency_score -= deduction
                details['deductions'].append(f"Concurrency: -{deduction:.1f} points for low success rate")
        
        total_score = max(0, api_score + db_score + memory_score + concurrency_score)
        
        return {
            'total_score': round(total_score, 1),
            'component_scores': {
                'api_performance': round(api_score, 1),
                'database_performance': round(db_score, 1),
                'memory_usage': round(memory_score, 1),
                'concurrency_performance': round(concurrency_score, 1)
            },
            'grade': 'A' if total_score >= 90 else 'B' if total_score >= 80 else 'C' if total_score >= 70 else 'D' if total_score >= 60 else 'F',
            'details': details
        }
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run complete performance test suite"""
        print("Starting Comprehensive Performance Test Suite")
        print("=" * 60)
        
        # Start system monitoring
        self.start_system_monitoring()
        
        try:
            # 1. Test individual API endpoints
            print("\n1. Testing API endpoint performance...")
            api_endpoints = [
                ('/health', 'GET'),
                ('/metrics', 'GET'),
                # Add more endpoints as needed
            ]
            
            api_results = []
            for endpoint, method in api_endpoints:
                result = await self.test_api_endpoint_performance(endpoint, method, iterations=50)
                api_results.append(result)
                
                # Print immediate results
                if 'response_times' in result:
                    print(f"  {endpoint}: {result['response_times']['mean']:.1f}ms avg, {result['success_rate']:.1f}% success")
                else:
                    print(f"  {endpoint}: FAILED")
            
            self.results['api_endpoints'] = api_results
            
            # 2. Test database performance
            print("\n2. Testing database performance...")
            db_results = self.test_database_performance()
            self.results['database'] = db_results
            
            if 'redis' in db_results and 'read_performance' in db_results['redis']:
                print(f"  Redis read: {db_results['redis']['read_performance']['mean_ms']:.2f}ms avg")
                print(f"  Redis write: {db_results['redis']['write_performance']['mean_ms']:.2f}ms avg")
            
            # 3. Test memory usage
            print("\n3. Testing memory usage patterns...")
            memory_results = self.test_memory_usage_patterns(duration=20)
            self.results['memory_usage'] = memory_results
            
            if 'peak_memory_mb' in memory_results:
                print(f"  Peak memory: {memory_results['peak_memory_mb']:.1f}MB ({memory_results['peak_percent']:.1f}%)")
                print(f"  Average memory: {memory_results['average_memory_mb']:.1f}MB")
            
            # 4. Test network latency
            print("\n4. Testing network latency...")
            network_results = self.test_network_latency()
            self.results['network_latency'] = network_results
            
            if 'api_latency' in network_results:
                print(f"  API latency: {network_results['api_latency']['mean_ms']:.1f}ms avg")
            
            # 5. Test concurrent users
            print("\n5. Testing concurrent user load...")
            concurrent_results = await self.test_concurrent_users(
                endpoint='/health', 
                concurrent_users=25, 
                requests_per_user=8
            )
            self.results['concurrent_users'] = concurrent_results
            
            if 'throughput_rps' in concurrent_results:
                print(f"  Throughput: {concurrent_results['throughput_rps']:.1f} requests/second")
                print(f"  Success rate: {concurrent_results['success_rate']:.1f}%")
            
            # 6. Identify bottlenecks
            print("\n6. Analyzing bottlenecks...")
            bottlenecks = self.identify_bottlenecks()
            self.results['bottlenecks'] = bottlenecks
            
            # 7. Calculate performance score
            score = self.calculate_performance_score()
            self.results['performance_score'] = score
            
            # Generate performance graphs
            print("\n7. Generating performance visualizations...")
            self.generate_performance_graphs()
            
        finally:
            # Stop monitoring
            self.stop_system_monitoring()
        
        return self.results
    
    def generate_detailed_report(self, output_file: str = "performance_report.json"):
        """Generate comprehensive performance report"""
        report = {
            'test_metadata': {
                'timestamp': datetime.now().isoformat(),
                'test_duration_minutes': (time.time() - self.start_time) / 60,
                'base_url': self.base_url,
                'system_info': {
                    'cpu_count': psutil.cpu_count(),
                    'total_memory_gb': psutil.virtual_memory().total / 1024**3,
                    'python_version': f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}",
                    'platform': psutil.sys.platform
                }
            },
            'performance_results': self.results,
            'system_monitoring': {
                'cpu_samples': len(self.monitoring_data['cpu_usage']),
                'memory_samples': len(self.monitoring_data['memory_usage']),
                'average_cpu': statistics.mean([d['value'] for d in self.monitoring_data['cpu_usage']]) if self.monitoring_data['cpu_usage'] else 0,
                'peak_cpu': max([d['value'] for d in self.monitoring_data['cpu_usage']]) if self.monitoring_data['cpu_usage'] else 0
            }
        }
        
        # Save detailed report
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\nDetailed performance report saved to: {output_file}")
        
        # Print executive summary
        self.print_executive_summary()
        
        return output_file
    
    def print_executive_summary(self):
        """Print executive summary of performance test"""
        print("\n" + "=" * 80)
        print("PERFORMANCE TEST EXECUTIVE SUMMARY")
        print("=" * 80)
        
        # Performance score
        if 'performance_score' in self.results:
            score_data = self.results['performance_score']
            print(f"\nOVERALL PERFORMANCE SCORE: {score_data['total_score']}/100 (Grade: {score_data['grade']})")
            print("\nComponent Scores:")
            for component, score in score_data['component_scores'].items():
                print(f"  • {component.replace('_', ' ').title()}: {score}/20")
        
        # Key metrics
        print("\nKEY PERFORMANCE METRICS:")
        
        if 'api_endpoints' in self.results:
            for endpoint_result in self.results['api_endpoints']:
                if 'response_times' in endpoint_result:
                    rt = endpoint_result['response_times']
                    print(f"  • {endpoint_result['endpoint']}: {rt['mean']:.1f}ms avg, {rt['p95']:.1f}ms P95")
        
        if 'concurrent_users' in self.results:
            cu = self.results['concurrent_users']
            print(f"  • Concurrent Load: {cu.get('throughput_rps', 0):.1f} RPS, {cu.get('success_rate', 0):.1f}% success")
        
        if 'database' in self.results and 'redis' in self.results['database']:
            redis_data = self.results['database']['redis']
            if 'read_performance' in redis_data:
                print(f"  • Redis Performance: {redis_data['read_performance']['mean_ms']:.2f}ms reads")
        
        if 'memory_usage' in self.results:
            mem = self.results['memory_usage']
            print(f"  • Memory Usage: {mem.get('peak_percent', 0):.1f}% peak, {mem.get('average_percent', 0):.1f}% avg")
        
        # Critical issues and recommendations
        if 'bottlenecks' in self.results:
            bottlenecks = self.results['bottlenecks']
            
            if bottlenecks['critical_issues']:
                print("\nCRITICAL ISSUES:")
                for issue in bottlenecks['critical_issues']:
                    print(f"  ⚠️  {issue}")
            
            if bottlenecks['warnings']:
                print("\nWARNINGS:")
                for warning in bottlenecks['warnings']:
                    print(f"  ⚡ {warning}")
            
            if bottlenecks['recommendations']:
                print("\nRECOMMENDATIONS:")
                for i, rec in enumerate(bottlenecks['recommendations'], 1):
                    print(f"  {i}. {rec}")
        
        print("\n" + "=" * 80)

async def main():
    """Run comprehensive performance test"""
    # Test against local backend if available
    base_url = "http://localhost:8000"
    
    # Check if backend is running
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"Backend detected at {base_url}")
        else:
            print(f"Backend responded with status {response.status_code}")
    except Exception as e:
        print(f"Backend not available at {base_url}: {e}")
        print("Running tests against mock endpoints...")
        # Could add mock server here for testing
    
    # Run comprehensive performance test
    test_suite = PerformanceTestSuite(base_url)
    
    try:
        results = await test_suite.run_comprehensive_test()
        test_suite.generate_detailed_report("comprehensive_performance_report.json")
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        test_suite.stop_system_monitoring()

if __name__ == "__main__":
    asyncio.run(main())
