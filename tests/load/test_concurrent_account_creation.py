#!/usr/bin/env python3
"""
Load Testing for Concurrent Account Creation
Tests system behavior under various load conditions
"""

import pytest
import asyncio
import time
import threading
import concurrent.futures
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
import os
import psutil
import statistics
from unittest.mock import patch, MagicMock
import queue
import signal
import sys

# Import system components
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../automation'))

from tinder.account_creator import get_account_creator, AccountCreationResult
from android.emulator_manager import get_emulator_manager
from email_services.temp_email_services import get_email_service_manager
from core.anti_detection import get_anti_detection_system


@dataclass
class LoadTestMetrics:
    """Metrics collected during load testing"""
    test_name: str
    concurrency_level: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    test_duration: float
    average_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    errors_per_second: float
    success_rate: float
    memory_usage_mb: float
    cpu_usage_percent: float
    system_load: float
    error_breakdown: Dict[str, int]
    timestamp: datetime


@dataclass
class LoadTestConfig:
    """Configuration for load tests"""
    name: str
    concurrency_levels: List[int]
    duration_seconds: int
    ramp_up_seconds: int
    operations_per_thread: int
    target_success_rate: float = 0.90
    max_response_time: float = 300.0  # 5 minutes
    max_memory_mb: float = 4000
    max_cpu_percent: float = 90


class LoadTestOrchestrator:
    """Orchestrates load testing scenarios"""
    
    def __init__(self):
        self.results: List[LoadTestMetrics] = []
        self.system_monitor = SystemMonitor()
        self.test_interrupted = False
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful interruption"""
        signal.signal(signal.SIGINT, self._handle_interrupt)
        signal.signal(signal.SIGTERM, self._handle_interrupt)
    
    def _handle_interrupt(self, signum, frame):
        """Handle test interruption"""
        print("\n⚠️  Load test interrupted. Cleaning up...")
        self.test_interrupted = True
    
    async def run_load_test(self, config: LoadTestConfig) -> List[LoadTestMetrics]:
        """Run complete load test with multiple concurrency levels"""
        
        print(f"🚀 Starting load test: {config.name}")
        print(f"   Concurrency levels: {config.concurrency_levels}")
        print(f"   Duration: {config.duration_seconds}s")
        print(f"   Operations per thread: {config.operations_per_thread}")
        
        for concurrency in config.concurrency_levels:
            if self.test_interrupted:
                break
                
            print(f"\n📊 Testing concurrency level: {concurrency}")
            
            try:
                metrics = await self._run_concurrency_test(
                    config, concurrency
                )
                self.results.append(metrics)
                
                # Log immediate results
                print(f"   ✅ Success rate: {metrics.success_rate:.1%}")
                print(f"   ⚡ RPS: {metrics.requests_per_second:.1f}")
                print(f"   ⏱️  Avg response: {metrics.average_response_time:.1f}s")
                print(f"   💾 Memory: {metrics.memory_usage_mb:.1f}MB")
                print(f"   🔥 CPU: {metrics.cpu_usage_percent:.1f}%")
                
                # Check if we should continue
                if not self._should_continue_testing(metrics, config):
                    print("   ⚠️  System limits reached, stopping test")
                    break
                    
            except Exception as e:
                print(f"   ❌ Test failed: {e}")
                continue
        
        return self.results
    
    async def _run_concurrency_test(self, config: LoadTestConfig, 
                                  concurrency: int) -> LoadTestMetrics:
        """Run test with specific concurrency level"""
        
        # Start system monitoring
        self.system_monitor.start_monitoring()
        
        # Track all operations
        results_queue = queue.Queue()
        start_time = time.time()
        
        # Create thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            # Submit tasks with ramp-up
            futures = []
            
            for i in range(concurrency):
                if self.test_interrupted:
                    break
                    
                # Ramp-up delay
                if config.ramp_up_seconds > 0:
                    delay = (config.ramp_up_seconds / concurrency) * i
                    time.sleep(delay)
                
                future = executor.submit(
                    self._worker_thread,
                    config.operations_per_thread,
                    results_queue,
                    i
                )
                futures.append(future)
            
            # Wait for completion or timeout
            timeout = config.duration_seconds + config.ramp_up_seconds + 60
            
            try:
                for future in concurrent.futures.as_completed(futures, timeout=timeout):
                    if self.test_interrupted:
                        break
                    try:
                        future.result()
                    except Exception as e:
                        print(f"Worker thread error: {e}")
            
            except concurrent.futures.TimeoutError:
                print("⚠️  Load test timed out")
        
        # Stop monitoring and collect results
        system_metrics = self.system_monitor.stop_monitoring()
        test_duration = time.time() - start_time
        
        # Collect all operation results
        operation_results = []
        while not results_queue.empty():
            try:
                result = results_queue.get_nowait()
                operation_results.append(result)
            except queue.Empty:
                break
        
        # Calculate metrics
        return self._calculate_metrics(
            config.name, concurrency, operation_results, 
            test_duration, system_metrics
        )
    
    def _worker_thread(self, operations_count: int, results_queue: queue.Queue, 
                      thread_id: int) -> None:
        """Worker thread for load testing"""
        
        for op_id in range(operations_count):
            if self.test_interrupted:
                break
            
            start_time = time.time()
            success = False
            error = None
            
            try:
                # Simulate account creation operation
                result = self._simulate_account_creation(thread_id, op_id)
                success = result.get('success', False)
                if not success:
                    error = result.get('error', 'Unknown error')
                    
            except Exception as e:
                error = str(e)
            
            duration = time.time() - start_time
            
            operation_result = {
                'thread_id': thread_id,
                'operation_id': op_id,
                'success': success,
                'duration': duration,
                'error': error,
                'timestamp': time.time()
            }
            
            results_queue.put(operation_result)
            
            # Small delay between operations
            time.sleep(0.1)
    
    def _simulate_account_creation(self, thread_id: int, op_id: int) -> Dict:
        """Simulate account creation for load testing"""
        
        try:
            # Create mock account creation workflow
            # In real load testing, this would call actual account creation
            
            # Simulate variable response times
            operation_time = random.uniform(5.0, 30.0)  # 5-30 seconds
            time.sleep(operation_time)
            
            # Simulate success/failure based on load
            success_probability = 0.95  # 95% success rate under normal conditions
            
            # Reduce success rate under high load
            current_load = psutil.cpu_percent()
            if current_load > 80:
                success_probability = 0.80
            elif current_load > 60:
                success_probability = 0.90
            
            success = random.random() < success_probability
            
            if success:
                return {
                    'success': True,
                    'account_id': f'test_account_{thread_id}_{op_id}',
                    'operation_time': operation_time
                }
            else:
                return {
                    'success': False,
                    'error': 'Simulated failure under load',
                    'operation_time': operation_time
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'operation_time': 0
            }
    
    def _calculate_metrics(self, test_name: str, concurrency: int, 
                          operation_results: List[Dict], test_duration: float,
                          system_metrics: Dict) -> LoadTestMetrics:
        """Calculate load test metrics"""
        
        total_requests = len(operation_results)
        successful_requests = sum(1 for r in operation_results if r['success'])
        failed_requests = total_requests - successful_requests
        
        # Response time statistics
        response_times = [r['duration'] for r in operation_results if r['success']]
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            
            # Calculate percentiles
            sorted_times = sorted(response_times)
            p95_index = int(0.95 * len(sorted_times))
            p99_index = int(0.99 * len(sorted_times))
            
            p95_response_time = sorted_times[p95_index] if p95_index < len(sorted_times) else max_response_time
            p99_response_time = sorted_times[p99_index] if p99_index < len(sorted_times) else max_response_time
        else:
            avg_response_time = min_response_time = max_response_time = 0
            p95_response_time = p99_response_time = 0
        
        # Throughput calculations
        requests_per_second = total_requests / test_duration if test_duration > 0 else 0
        errors_per_second = failed_requests / test_duration if test_duration > 0 else 0
        success_rate = successful_requests / total_requests if total_requests > 0 else 0
        
        # Error breakdown
        error_breakdown = {}
        for result in operation_results:
            if not result['success'] and result['error']:
                error_type = result['error']
                error_breakdown[error_type] = error_breakdown.get(error_type, 0) + 1
        
        return LoadTestMetrics(
            test_name=test_name,
            concurrency_level=concurrency,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            test_duration=test_duration,
            average_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            requests_per_second=requests_per_second,
            errors_per_second=errors_per_second,
            success_rate=success_rate,
            memory_usage_mb=system_metrics.get('memory_max', 0),
            cpu_usage_percent=system_metrics.get('cpu_max', 0),
            system_load=system_metrics.get('load_avg', 0),
            error_breakdown=error_breakdown,
            timestamp=datetime.now()
        )
    
    def _should_continue_testing(self, metrics: LoadTestMetrics, 
                               config: LoadTestConfig) -> bool:
        """Determine if testing should continue based on current metrics"""
        
        # Stop if success rate is too low
        if metrics.success_rate < config.target_success_rate * 0.5:
            return False
        
        # Stop if response times are too high
        if metrics.p95_response_time > config.max_response_time:
            return False
        
        # Stop if system resources are exhausted
        if metrics.memory_usage_mb > config.max_memory_mb:
            return False
        
        if metrics.cpu_usage_percent > config.max_cpu_percent:
            return False
        
        return True


class SystemMonitor:
    """Monitor system resources during load testing"""
    
    def __init__(self):
        self.monitoring = False
        self.metrics = []
        self.monitor_thread = None
    
    def start_monitoring(self):
        """Start monitoring system resources"""
        self.monitoring = True
        self.metrics = []
        
        def monitor():
            process = psutil.Process()
            
            while self.monitoring:
                try:
                    cpu_percent = process.cpu_percent()
                    memory_info = process.memory_info()
                    memory_mb = memory_info.rss / 1024 / 1024
                    
                    # System-wide metrics
                    system_cpu = psutil.cpu_percent()
                    system_memory = psutil.virtual_memory().percent
                    load_avg = os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0
                    
                    metric = {
                        'timestamp': time.time(),
                        'process_cpu': cpu_percent,
                        'process_memory_mb': memory_mb,
                        'system_cpu': system_cpu,
                        'system_memory_percent': system_memory,
                        'load_avg': load_avg,
                        'thread_count': process.num_threads()
                    }
                    
                    self.metrics.append(metric)
                    time.sleep(1.0)  # Sample every second
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    break
        
        self.monitor_thread = threading.Thread(target=monitor, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self) -> Dict:
        """Stop monitoring and return aggregated metrics"""
        self.monitoring = False
        
        if not self.metrics:
            return {}
        
        # Aggregate metrics
        cpu_values = [m['process_cpu'] for m in self.metrics]
        memory_values = [m['process_memory_mb'] for m in self.metrics]
        system_cpu_values = [m['system_cpu'] for m in self.metrics]
        load_values = [m['load_avg'] for m in self.metrics]
        
        return {
            'cpu_avg': statistics.mean(cpu_values),
            'cpu_max': max(cpu_values),
            'memory_avg': statistics.mean(memory_values),
            'memory_max': max(memory_values),
            'system_cpu_avg': statistics.mean(system_cpu_values),
            'system_cpu_max': max(system_cpu_values),
            'load_avg': statistics.mean(load_values) if load_values else 0,
            'sample_count': len(self.metrics)
        }


class TestConcurrentAccountCreation:
    """Load tests for concurrent account creation"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.orchestrator = LoadTestOrchestrator()
    
    @pytest.mark.load
    @pytest.mark.slow
    async def test_basic_concurrency_scaling(self):
        """Test basic concurrency scaling from 1 to 10 users"""
        
        config = LoadTestConfig(
            name="basic_concurrency_scaling",
            concurrency_levels=[1, 2, 5, 10],
            duration_seconds=60,
            ramp_up_seconds=10,
            operations_per_thread=3,
            target_success_rate=0.90,
            max_response_time=180.0
        )
        
        results = await self.orchestrator.run_load_test(config)
        
        # Validate scaling behavior
        assert len(results) >= 2, "Should test multiple concurrency levels"
        
        # Performance should degrade gracefully
        for i in range(1, len(results)):
            current = results[i]
            previous = results[i-1]
            
            # Success rate shouldn't drop dramatically
            success_rate_drop = previous.success_rate - current.success_rate
            assert success_rate_drop <= 0.2, \
                f"Success rate dropped {success_rate_drop:.1%} from {previous.concurrency_level} to {current.concurrency_level} users"
            
            # Response time increase should be reasonable
            response_time_increase = current.average_response_time / previous.average_response_time
            assert response_time_increase <= 3.0, \
                f"Response time increased {response_time_increase:.1f}x from {previous.concurrency_level} to {current.concurrency_level} users"
    
    @pytest.mark.load
    @pytest.mark.slow
    async def test_sustained_load(self):
        """Test sustained load over longer duration"""
        
        config = LoadTestConfig(
            name="sustained_load",
            concurrency_levels=[5],
            duration_seconds=300,  # 5 minutes
            ramp_up_seconds=30,
            operations_per_thread=10,
            target_success_rate=0.85,
            max_response_time=240.0
        )
        
        results = await self.orchestrator.run_load_test(config)
        
        assert len(results) == 1, "Should test one concurrency level"
        
        result = results[0]
        
        # Validate sustained performance
        assert result.success_rate >= 0.85, \
            f"Success rate {result.success_rate:.1%} below 85% threshold"
        
        assert result.average_response_time <= 240.0, \
            f"Average response time {result.average_response_time:.1f}s exceeds 4 minutes"
        
        assert result.memory_usage_mb <= 2000, \
            f"Memory usage {result.memory_usage_mb:.1f}MB too high for sustained load"
    
    @pytest.mark.load
    @pytest.mark.slow
    async def test_high_concurrency_stress(self):
        """Test high concurrency stress scenarios"""
        
        config = LoadTestConfig(
            name="high_concurrency_stress",
            concurrency_levels=[20, 50, 100],
            duration_seconds=120,
            ramp_up_seconds=60,
            operations_per_thread=2,
            target_success_rate=0.70,  # Lower expectation under stress
            max_response_time=300.0
        )
        
        results = await self.orchestrator.run_load_test(config)
        
        # Should handle at least 20 concurrent users
        assert len(results) >= 1, "Should complete at least basic stress test"
        
        # Find highest successful concurrency level
        max_successful_concurrency = 0
        for result in results:
            if result.success_rate >= 0.70:
                max_successful_concurrency = max(max_successful_concurrency, result.concurrency_level)
        
        assert max_successful_concurrency >= 20, \
            f"System should handle at least 20 concurrent users (achieved: {max_successful_concurrency})"
    
    @pytest.mark.load
    async def test_resource_usage_limits(self):
        """Test that resource usage stays within limits"""
        
        config = LoadTestConfig(
            name="resource_usage_limits",
            concurrency_levels=[5, 10],
            duration_seconds=60,
            ramp_up_seconds=15,
            operations_per_thread=3,
            max_memory_mb=3000,
            max_cpu_percent=85
        )
        
        results = await self.orchestrator.run_load_test(config)
        
        for result in results:
            # Memory usage limits
            assert result.memory_usage_mb <= config.max_memory_mb, \
                f"Memory usage {result.memory_usage_mb:.1f}MB exceeds limit {config.max_memory_mb}MB"
            
            # CPU usage limits
            assert result.cpu_usage_percent <= config.max_cpu_percent, \
                f"CPU usage {result.cpu_usage_percent:.1f}% exceeds limit {config.max_cpu_percent}%"
    
    @pytest.mark.load
    async def test_error_handling_under_load(self):
        """Test error handling behavior under load"""
        
        # Inject failures to test error handling
        with patch('random.random', return_value=0.7):  # Force some failures
            config = LoadTestConfig(
                name="error_handling_under_load",
                concurrency_levels=[10],
                duration_seconds=60,
                ramp_up_seconds=10,
                operations_per_thread=3,
                target_success_rate=0.60  # Expect lower success due to injected failures
            )
            
            results = await self.orchestrator.run_load_test(config)
            
            assert len(results) == 1, "Should complete error handling test"
            
            result = results[0]
            
            # Should handle errors gracefully
            assert result.failed_requests > 0, "Should have some failures due to injected errors"
            assert result.success_rate >= 0.60, "Should maintain minimum success rate despite errors"
            
            # Error breakdown should be available
            assert len(result.error_breakdown) > 0, "Should track error types"
    
    def test_load_test_configuration_validation(self):
        """Test load test configuration validation"""
        
        # Valid configuration
        valid_config = LoadTestConfig(
            name="valid_test",
            concurrency_levels=[1, 2, 5],
            duration_seconds=60,
            ramp_up_seconds=10,
            operations_per_thread=2
        )
        
        assert valid_config.name == "valid_test"
        assert valid_config.concurrency_levels == [1, 2, 5]
        
        # Configuration with invalid values should be handled
        # (In real implementation, would add validation)
        assert valid_config.target_success_rate > 0
        assert valid_config.max_response_time > 0
        assert valid_config.duration_seconds > 0


@pytest.fixture
def load_test_orchestrator():
    """Fixture providing load test orchestrator"""
    return LoadTestOrchestrator()


@pytest.fixture
def mock_account_creator():
    """Fixture providing mock account creator for load testing"""
    mock_creator = MagicMock()
    
    def mock_create_account(*args, **kwargs):
        # Simulate variable response times and occasional failures
        time.sleep(random.uniform(1.0, 5.0))
        
        success = random.random() > 0.1  # 90% success rate
        
        if success:
            return {
                'success': True,
                'account_id': f'test_account_{int(time.time())}',
                'creation_time': time.time()
            }
        else:
            return {
                'success': False,
                'error': 'Mock creation failure'
            }
    
    mock_creator.create_account.side_effect = mock_create_account
    return mock_creator


# Import required for mocking
import random


# Load test configuration
pytestmark = [
    pytest.mark.load,
    pytest.mark.timeout(1200),  # 20 minute timeout for load tests
]


def save_load_test_results(results: List[LoadTestMetrics], filename: str):
    """Save load test results to file"""
    results_dir = os.path.join(os.path.dirname(__file__), 'results')
    os.makedirs(results_dir, exist_ok=True)
    
    filepath = os.path.join(results_dir, filename)
    
    # Convert to JSON-serializable format
    serializable_results = [asdict(result) for result in results]
    
    with open(filepath, 'w') as f:
        json.dump(serializable_results, f, indent=2, default=str)
    
    print(f"Load test results saved to: {filepath}")


if __name__ == "__main__":
    # Run load tests
    pytest.main([
        __file__,
        "-v",
        "-m", "load",
        "--tb=short",
        "--durations=10"
    ])