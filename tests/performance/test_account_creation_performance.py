#!/usr/bin/env python3
"""
Performance Regression Test Suite for Account Creation
Monitors performance metrics and detects regressions
"""

import pytest
import asyncio
import time
import psutil
import statistics
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
import os
import threading
import concurrent.futures
from unittest.mock import patch, MagicMock

# Import system components
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../automation'))

from tinder.account_creator import get_account_creator, AccountProfile
from core.anti_detection import get_anti_detection_system, BehaviorPattern
from android.emulator_manager import get_emulator_manager
from email_services.temp_email_services import get_email_service_manager


@dataclass
class PerformanceMetrics:
    """Performance metrics for benchmarking"""
    operation: str
    duration: float
    memory_usage_mb: float
    cpu_usage_percent: float
    success: bool
    timestamp: datetime
    thread_count: int = 1
    concurrent_operations: int = 1
    error: Optional[str] = None


@dataclass
class PerformanceBenchmark:
    """Performance benchmark thresholds"""
    operation: str
    max_duration_seconds: float
    max_memory_mb: float
    max_cpu_percent: float
    min_success_rate: float = 0.95


class PerformanceMonitor:
    """Monitor system performance during operations"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.monitoring = False
        self.metrics = []
        
    def start_monitoring(self, interval: float = 0.1):
        """Start performance monitoring"""
        self.monitoring = True
        self.metrics = []
        
        def monitor():
            while self.monitoring:
                try:
                    cpu_percent = self.process.cpu_percent()
                    memory_mb = self.process.memory_info().rss / 1024 / 1024
                    thread_count = self.process.num_threads()
                    
                    self.metrics.append({
                        'timestamp': time.time(),
                        'cpu_percent': cpu_percent,
                        'memory_mb': memory_mb,
                        'thread_count': thread_count
                    })
                    
                    time.sleep(interval)
                except psutil.NoSuchProcess:
                    break
        
        self.monitor_thread = threading.Thread(target=monitor, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self) -> Dict:
        """Stop monitoring and return aggregated metrics"""
        self.monitoring = False
        
        if not self.metrics:
            return {}
        
        cpu_values = [m['cpu_percent'] for m in self.metrics]
        memory_values = [m['memory_mb'] for m in self.metrics]
        thread_values = [m['thread_count'] for m in self.metrics]
        
        return {
            'cpu_avg': statistics.mean(cpu_values),
            'cpu_max': max(cpu_values),
            'memory_avg': statistics.mean(memory_values),
            'memory_max': max(memory_values),
            'memory_min': min(memory_values),
            'thread_avg': statistics.mean(thread_values),
            'thread_max': max(thread_values),
            'sample_count': len(self.metrics)
        }


class TestAccountCreationPerformance:
    """Performance tests for account creation workflows"""
    
    # Performance benchmarks based on requirements
    BENCHMARKS = {
        'profile_generation': PerformanceBenchmark(
            operation='profile_generation',
            max_duration_seconds=0.1,
            max_memory_mb=50,
            max_cpu_percent=20
        ),
        'device_fingerprint_creation': PerformanceBenchmark(
            operation='device_fingerprint_creation',
            max_duration_seconds=0.5,
            max_memory_mb=100,
            max_cpu_percent=30
        ),
        'behavior_pattern_generation': PerformanceBenchmark(
            operation='behavior_pattern_generation',
            max_duration_seconds=0.2,
            max_memory_mb=25,
            max_cpu_percent=15
        ),
        'email_account_creation': PerformanceBenchmark(
            operation='email_account_creation',
            max_duration_seconds=30.0,
            max_memory_mb=200,
            max_cpu_percent=50
        ),
        'complete_account_creation': PerformanceBenchmark(
            operation='complete_account_creation',
            max_duration_seconds=180.0,  # 3 minutes max
            max_memory_mb=1000,
            max_cpu_percent=80,
            min_success_rate=0.90
        )
    }
    
    def setup_method(self):
        """Setup for each test method"""
        self.monitor = PerformanceMonitor()
        self.metrics_history = []
    
    def teardown_method(self):
        """Cleanup after each test method"""
        if hasattr(self, 'monitor'):
            self.monitor.monitoring = False
    
    @pytest.mark.performance
    def test_profile_generation_performance(self):
        """Test profile generation performance"""
        account_creator = get_account_creator(aggressiveness=0.3)
        benchmark = self.BENCHMARKS['profile_generation']
        
        # Warm up
        for _ in range(5):
            account_creator.generate_random_profile()
        
        # Performance test
        results = []
        
        for i in range(100):  # Test 100 generations
            self.monitor.start_monitoring()
            start_time = time.time()
            
            try:
                profile = account_creator.generate_random_profile(f"test_user_{i}")
                success = profile is not None
            except Exception as e:
                success = False
                error = str(e)
            else:
                error = None
            
            duration = time.time() - start_time
            system_metrics = self.monitor.stop_monitoring()
            
            metric = PerformanceMetrics(
                operation='profile_generation',
                duration=duration,
                memory_usage_mb=system_metrics.get('memory_max', 0),
                cpu_usage_percent=system_metrics.get('cpu_max', 0),
                success=success,
                timestamp=datetime.now(),
                error=error
            )
            
            results.append(metric)
        
        # Analyze results
        self._analyze_performance_results(results, benchmark)
    
    @pytest.mark.performance
    def test_device_fingerprint_performance(self):
        """Test device fingerprint creation performance"""
        anti_detection = get_anti_detection_system(aggressiveness=0.3)
        benchmark = self.BENCHMARKS['device_fingerprint_creation']
        
        results = []
        
        for i in range(50):  # Test 50 fingerprints
            device_id = f"test_device_{i}"
            
            self.monitor.start_monitoring()
            start_time = time.time()
            
            try:
                fingerprint = anti_detection.create_device_fingerprint(device_id)
                success = fingerprint is not None
            except Exception as e:
                success = False
                error = str(e)
            else:
                error = None
            
            duration = time.time() - start_time
            system_metrics = self.monitor.stop_monitoring()
            
            metric = PerformanceMetrics(
                operation='device_fingerprint_creation',
                duration=duration,
                memory_usage_mb=system_metrics.get('memory_max', 0),
                cpu_usage_percent=system_metrics.get('cpu_max', 0),
                success=success,
                timestamp=datetime.now(),
                error=error
            )
            
            results.append(metric)
        
        self._analyze_performance_results(results, benchmark)
    
    @pytest.mark.performance
    def test_behavior_pattern_performance(self):
        """Test behavior pattern generation performance"""
        benchmark = self.BENCHMARKS['behavior_pattern_generation']
        
        results = []
        
        for i in range(200):  # Test 200 pattern generations
            self.monitor.start_monitoring()
            start_time = time.time()
            
            try:
                behavior = BehaviorPattern(aggressiveness=0.3)
                
                # Test multiple pattern operations
                swipe_timing = behavior.get_swipe_timing()
                session_duration = behavior.get_session_duration()
                session_count = behavior.get_daily_session_count()
                
                success = all(v is not None for v in [swipe_timing, session_duration, session_count])
            except Exception as e:
                success = False
                error = str(e)
            else:
                error = None
            
            duration = time.time() - start_time
            system_metrics = self.monitor.stop_monitoring()
            
            metric = PerformanceMetrics(
                operation='behavior_pattern_generation',
                duration=duration,
                memory_usage_mb=system_metrics.get('memory_max', 0),
                cpu_usage_percent=system_metrics.get('cpu_max', 0),
                success=success,
                timestamp=datetime.now(),
                error=error
            )
            
            results.append(metric)
        
        self._analyze_performance_results(results, benchmark)
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_email_creation_performance(self):
        """Test email account creation performance"""
        benchmark = self.BENCHMARKS['email_account_creation']
        
        email_manager = get_email_service_manager()
        results = []
        created_emails = []
        
        try:
            for i in range(10):  # Test 10 email creations
                self.monitor.start_monitoring()
                start_time = time.time()
                
                try:
                    account = await asyncio.wait_for(
                        email_manager.create_email_account(),
                        timeout=45  # 45 second timeout
                    )
                    
                    if account and account.email:
                        created_emails.append(account.email)
                        success = True
                    else:
                        success = False
                        
                except asyncio.TimeoutError:
                    success = False
                    error = "Timeout"
                except Exception as e:
                    success = False
                    error = str(e)
                else:
                    error = None
                
                duration = time.time() - start_time
                system_metrics = self.monitor.stop_monitoring()
                
                metric = PerformanceMetrics(
                    operation='email_account_creation',
                    duration=duration,
                    memory_usage_mb=system_metrics.get('memory_max', 0),
                    cpu_usage_percent=system_metrics.get('cpu_max', 0),
                    success=success,
                    timestamp=datetime.now(),
                    error=error
                )
                
                results.append(metric)
                
                # Small delay between creations
                await asyncio.sleep(1)
        
        finally:
            # Cleanup created emails
            for email in created_emails:
                try:
                    await email_manager.delete_email_account(email)
                except Exception:
                    pass  # Ignore cleanup errors
        
        self._analyze_performance_results(results, benchmark)
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_concurrent_profile_generation_performance(self):
        """Test concurrent profile generation performance"""
        
        def generate_profiles_batch(batch_size: int) -> List[PerformanceMetrics]:
            """Generate a batch of profiles and measure performance"""
            account_creator = get_account_creator(aggressiveness=0.3)
            results = []
            
            self.monitor.start_monitoring()
            start_time = time.time()
            
            try:
                profiles = []
                for i in range(batch_size):
                    profile = account_creator.generate_random_profile(f"concurrent_user_{i}")
                    profiles.append(profile)
                
                success = len(profiles) == batch_size
                
            except Exception as e:
                success = False
                error = str(e)
            else:
                error = None
            
            duration = time.time() - start_time
            system_metrics = self.monitor.stop_monitoring()
            
            metric = PerformanceMetrics(
                operation='concurrent_profile_generation',
                duration=duration,
                memory_usage_mb=system_metrics.get('memory_max', 0),
                cpu_usage_percent=system_metrics.get('cpu_max', 0),
                success=success,
                timestamp=datetime.now(),
                concurrent_operations=batch_size,
                error=error
            )
            
            return [metric]
        
        # Test different concurrency levels
        concurrency_levels = [1, 5, 10, 20]
        all_results = []
        
        for concurrency in concurrency_levels:
            print(f"\nTesting concurrency level: {concurrency}")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = [
                    executor.submit(generate_profiles_batch, 10)  # 10 profiles per thread
                    for _ in range(concurrency)
                ]
                
                for future in concurrent.futures.as_completed(futures):
                    try:
                        results = future.result(timeout=60)
                        all_results.extend(results)
                    except Exception as e:
                        print(f"Thread failed: {e}")
        
        # Analyze concurrency performance
        self._analyze_concurrency_performance(all_results)
    
    @pytest.mark.performance
    @pytest.mark.benchmark
    def test_memory_usage_regression(self):
        """Test for memory usage regressions"""
        
        account_creator = get_account_creator(aggressiveness=0.3)
        
        # Baseline memory usage
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Generate many profiles to test memory growth
        profiles = []
        memory_samples = []
        
        for i in range(1000):
            profile = account_creator.generate_random_profile(f"memory_test_{i}")
            profiles.append(profile)
            
            if i % 100 == 0:
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                memory_growth = current_memory - initial_memory
                memory_samples.append(memory_growth)
                
                print(f"After {i} profiles: {memory_growth:.1f}MB growth")
        
        # Check for memory leaks
        final_memory_growth = memory_samples[-1]
        
        # Memory growth should be reasonable (< 500MB for 1000 profiles)
        assert final_memory_growth < 500, f"Memory growth {final_memory_growth:.1f}MB exceeds 500MB limit"
        
        # Memory growth should be roughly linear (no major leaks)
        if len(memory_samples) > 2:
            growth_rate = (memory_samples[-1] - memory_samples[0]) / len(memory_samples)
            assert growth_rate < 1.0, f"Memory growth rate {growth_rate:.2f}MB per 100 profiles too high"
    
    def _analyze_performance_results(self, results: List[PerformanceMetrics], 
                                   benchmark: PerformanceBenchmark):
        """Analyze performance results against benchmarks"""
        
        if not results:
            pytest.fail("No performance results to analyze")
        
        # Calculate statistics
        durations = [r.duration for r in results if r.success]
        memory_usage = [r.memory_usage_mb for r in results if r.success]
        cpu_usage = [r.cpu_usage_percent for r in results if r.success]
        
        success_rate = sum(1 for r in results if r.success) / len(results)
        
        if durations:
            avg_duration = statistics.mean(durations)
            max_duration = max(durations)
            p95_duration = statistics.quantiles(durations, n=20)[18]  # 95th percentile
        else:
            avg_duration = max_duration = p95_duration = float('inf')
        
        if memory_usage:
            avg_memory = statistics.mean(memory_usage)
            max_memory = max(memory_usage)
        else:
            avg_memory = max_memory = 0
        
        if cpu_usage:
            avg_cpu = statistics.mean(cpu_usage)
            max_cpu = max(cpu_usage)
        else:
            avg_cpu = max_cpu = 0
        
        # Generate performance report
        report = {
            'operation': benchmark.operation,
            'test_count': len(results),
            'success_rate': success_rate,
            'duration': {
                'avg': avg_duration,
                'max': max_duration,
                'p95': p95_duration,
                'benchmark': benchmark.max_duration_seconds
            },
            'memory': {
                'avg': avg_memory,
                'max': max_memory,
                'benchmark': benchmark.max_memory_mb
            },
            'cpu': {
                'avg': avg_cpu,
                'max': max_cpu,
                'benchmark': benchmark.max_cpu_percent
            }
        }
        
        # Print performance report
        print(f"\n=== Performance Report: {benchmark.operation} ===")
        print(f"Tests: {len(results)}, Success Rate: {success_rate:.1%}")
        print(f"Duration - Avg: {avg_duration:.3f}s, Max: {max_duration:.3f}s, P95: {p95_duration:.3f}s")
        print(f"Memory - Avg: {avg_memory:.1f}MB, Max: {max_memory:.1f}MB")
        print(f"CPU - Avg: {avg_cpu:.1f}%, Max: {max_cpu:.1f}%")
        
        # Performance assertions
        assert success_rate >= benchmark.min_success_rate, \
            f"Success rate {success_rate:.1%} below benchmark {benchmark.min_success_rate:.1%}"
        
        assert p95_duration <= benchmark.max_duration_seconds, \
            f"95th percentile duration {p95_duration:.3f}s exceeds benchmark {benchmark.max_duration_seconds}s"
        
        assert max_memory <= benchmark.max_memory_mb, \
            f"Max memory usage {max_memory:.1f}MB exceeds benchmark {benchmark.max_memory_mb}MB"
        
        assert max_cpu <= benchmark.max_cpu_percent, \
            f"Max CPU usage {max_cpu:.1f}% exceeds benchmark {benchmark.max_cpu_percent}%"
        
        # Save results for regression tracking
        self._save_performance_results(report)
    
    def _analyze_concurrency_performance(self, results: List[PerformanceMetrics]):
        """Analyze concurrent operation performance"""
        
        # Group results by concurrency level
        by_concurrency = {}
        for result in results:
            concurrency = result.concurrent_operations
            if concurrency not in by_concurrency:
                by_concurrency[concurrency] = []
            by_concurrency[concurrency].append(result)
        
        print(f"\n=== Concurrency Performance Analysis ===")
        
        for concurrency in sorted(by_concurrency.keys()):
            group_results = by_concurrency[concurrency]
            
            durations = [r.duration for r in group_results if r.success]
            success_rate = sum(1 for r in group_results if r.success) / len(group_results)
            
            if durations:
                avg_duration = statistics.mean(durations)
                throughput = concurrency / avg_duration if avg_duration > 0 else 0
            else:
                avg_duration = 0
                throughput = 0
            
            print(f"Concurrency {concurrency}: {success_rate:.1%} success, "
                  f"{avg_duration:.2f}s avg, {throughput:.1f} ops/sec")
            
            # Assert reasonable performance scaling
            if concurrency == 1:
                baseline_duration = avg_duration
            elif concurrency > 1 and baseline_duration > 0:
                # Duration shouldn't increase more than 3x with concurrency
                scaling_factor = avg_duration / baseline_duration
                assert scaling_factor < 3.0, \
                    f"Performance degradation {scaling_factor:.1f}x too high for concurrency {concurrency}"
    
    def _save_performance_results(self, report: Dict):
        """Save performance results for regression tracking"""
        
        results_dir = os.path.join(os.path.dirname(__file__), 'results')
        os.makedirs(results_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"performance_{report['operation']}_{timestamp}.json"
        filepath = os.path.join(results_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"Performance results saved to: {filepath}")


@pytest.fixture
def performance_monitor():
    """Fixture providing performance monitor"""
    monitor = PerformanceMonitor()
    yield monitor
    monitor.monitoring = False


@pytest.fixture
def benchmark_thresholds():
    """Fixture providing benchmark thresholds"""
    return TestAccountCreationPerformance.BENCHMARKS


# Performance test configuration
pytestmark = [
    pytest.mark.performance,
    pytest.mark.timeout(600),  # 10 minute timeout for performance tests
]


if __name__ == "__main__":
    # Run performance tests
    pytest.main([
        __file__,
        "-v",
        "-m", "performance",
        "--tb=short",
        "--durations=10"
    ])