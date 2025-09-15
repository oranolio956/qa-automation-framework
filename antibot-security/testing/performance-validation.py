#!/usr/bin/env python3
"""
High-Performance Load Testing for Anti-Bot Security Framework
Validates 100K+ RPS with sub-100ms response times
"""

import asyncio
import aiohttp
import json
import time
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import argparse
import logging
import sys
import signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'load_test_{int(time.time())}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TestConfig:
    """Load test configuration"""
    base_url: str = "http://localhost:8000"
    target_rps: int = 100000
    duration_seconds: int = 300
    ramp_up_seconds: int = 60
    concurrent_connections: int = 10000
    timeout_seconds: int = 5
    endpoints: List[str] = field(default_factory=lambda: [
        "/api/v1/risk/assess",
        "/api/v1/sms/send",
        "/api/v1/events/behavioral",
        "/api/v1/events/risk-assessment"
    ])
    
@dataclass 
class RequestResult:
    """Single request result"""
    endpoint: str
    status_code: int
    response_time_ms: float
    response_size: int
    timestamp: float
    error: Optional[str] = None

@dataclass
class TestMetrics:
    """Aggregated test metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    response_times: List[float] = field(default_factory=list)
    errors: Dict[str, int] = field(default_factory=dict)
    rps_per_second: List[float] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0

class LoadTestRunner:
    """High-performance load testing engine"""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.metrics = TestMetrics()
        self.running = False
        self.session: Optional[aiohttp.ClientSession] = None
        self.results_queue: asyncio.Queue = asyncio.Queue(maxsize=1000000)
        
    async def initialize(self):
        """Initialize HTTP client session"""
        connector = aiohttp.TCPConnector(
            limit=self.config.concurrent_connections,
            limit_per_host=self.config.concurrent_connections,
            ttl_dns_cache=300,
            use_dns_cache=True,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(
            total=self.config.timeout_seconds,
            connect=2.0,
            sock_read=2.0
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'AntiBot-LoadTest/1.0',
                'Content-Type': 'application/json',
                'Connection': 'keep-alive'
            }
        )
        
        logger.info(f"Initialized HTTP client with {self.config.concurrent_connections} connections")
    
    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()
    
    def generate_behavioral_data(self) -> Dict[str, Any]:
        """Generate realistic behavioral data"""
        return {
            "user_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "event_type": "mouse_movement",
            "timestamp": time.time(),
            "mouse_movements": [
                {
                    "x": random.randint(0, 1920),
                    "y": random.randint(0, 1080),
                    "timestamp": time.time() + i * 0.1
                }
                for i in range(random.randint(5, 20))
            ],
            "keyboard_events": [
                {
                    "key": random.choice(['a', 'b', 'c', 'd', 'e']),
                    "timestamp": time.time() + i * 0.2,
                    "type": random.choice(['keydown', 'keyup'])
                }
                for i in range(random.randint(3, 10))
            ],
            "viewport_data": {
                "width": 1920,
                "height": 1080,
                "scroll_x": random.randint(0, 500),
                "scroll_y": random.randint(0, 2000)
            },
            "device_fingerprint": {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "screen_resolution": "1920x1080",
                "timezone": "UTC",
                "language": "en-US"
            }
        }
    
    def generate_risk_assessment_data(self) -> Dict[str, Any]:
        """Generate risk assessment request"""
        return {
            "user_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "features": {
                "mouse_speed": random.uniform(0.1, 2.0),
                "keystroke_dynamics": [random.uniform(50, 200) for _ in range(10)],
                "scroll_pattern": random.uniform(0.0, 1.0),
                "time_on_page": random.randint(5, 300),
                "click_patterns": random.uniform(0.0, 1.0)
            },
            "metadata": {
                "ip_address": f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
                "timestamp": time.time()
            }
        }
    
    def generate_sms_data(self) -> Dict[str, Any]:
        """Generate SMS verification request"""
        return {
            "phone_number": f"+1{random.randint(1000000000, 9999999999)}",
            "message": f"Your verification code is: {random.randint(100000, 999999)}",
            "priority": random.randint(1, 5),
            "metadata": {
                "user_id": str(uuid.uuid4()),
                "session_id": str(uuid.uuid4())
            }
        }
    
    async def make_request(self, endpoint: str, data: Dict[str, Any]) -> RequestResult:
        """Make a single HTTP request"""
        start_time = time.time()
        
        try:
            url = f"{self.config.base_url}{endpoint}"
            
            async with self.session.post(url, json=data) as response:
                response_text = await response.text()
                end_time = time.time()
                
                return RequestResult(
                    endpoint=endpoint,
                    status_code=response.status,
                    response_time_ms=(end_time - start_time) * 1000,
                    response_size=len(response_text),
                    timestamp=start_time,
                    error=None if response.status < 400 else f"HTTP {response.status}"
                )
                
        except asyncio.TimeoutError:
            return RequestResult(
                endpoint=endpoint,
                status_code=0,
                response_time_ms=(time.time() - start_time) * 1000,
                response_size=0,
                timestamp=start_time,
                error="Timeout"
            )
        except Exception as e:
            return RequestResult(
                endpoint=endpoint,
                status_code=0,
                response_time_ms=(time.time() - start_time) * 1000,
                response_size=0,
                timestamp=start_time,
                error=str(e)
            )
    
    async def request_worker(self, worker_id: int, requests_per_worker: int):
        """Worker coroutine for making requests"""
        logger.info(f"Worker {worker_id} starting with {requests_per_worker} requests")
        
        for i in range(requests_per_worker):
            if not self.running:
                break
                
            # Select random endpoint and generate appropriate data
            endpoint = random.choice(self.config.endpoints)
            
            if "behavioral" in endpoint:
                data = self.generate_behavioral_data()
            elif "risk" in endpoint:
                data = self.generate_risk_assessment_data()
            elif "sms" in endpoint:
                data = self.generate_sms_data()
            else:
                data = {"test": True, "timestamp": time.time()}
            
            # Make request
            result = await self.make_request(endpoint, data)
            
            # Queue result for processing
            try:
                await self.results_queue.put(result)
            except asyncio.QueueFull:
                logger.warning("Results queue full, dropping result")
            
            # Small delay to control request rate
            if i < requests_per_worker - 1:
                await asyncio.sleep(0.001)  # 1ms delay
        
        logger.info(f"Worker {worker_id} completed")
    
    async def results_processor(self):
        """Process results and update metrics"""
        requests_this_second = 0
        second_start = time.time()
        
        while self.running or not self.results_queue.empty():
            try:
                result = await asyncio.wait_for(self.results_queue.get(), timeout=1.0)
                
                # Update metrics
                self.metrics.total_requests += 1
                
                if result.error is None and 200 <= result.status_code < 300:
                    self.metrics.successful_requests += 1
                else:
                    self.metrics.failed_requests += 1
                    error_key = result.error or f"HTTP_{result.status_code}"
                    self.metrics.errors[error_key] = self.metrics.errors.get(error_key, 0) + 1
                
                # Response time metrics
                rt = result.response_time_ms
                self.metrics.total_response_time += rt
                self.metrics.min_response_time = min(self.metrics.min_response_time, rt)
                self.metrics.max_response_time = max(self.metrics.max_response_time, rt)
                self.metrics.response_times.append(rt)
                
                # Track RPS
                requests_this_second += 1
                current_time = time.time()
                
                if current_time - second_start >= 1.0:
                    self.metrics.rps_per_second.append(requests_this_second / (current_time - second_start))
                    requests_this_second = 0
                    second_start = current_time
                    
                    # Log progress every 10 seconds
                    if len(self.metrics.rps_per_second) % 10 == 0:
                        current_rps = self.metrics.rps_per_second[-1]
                        avg_rt = np.mean(self.metrics.response_times[-1000:]) if self.metrics.response_times else 0
                        logger.info(f"RPS: {current_rps:.0f}, Avg RT: {avg_rt:.1f}ms, "
                                  f"Success Rate: {(self.metrics.successful_requests/self.metrics.total_requests)*100:.1f}%")
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing result: {e}")
    
    async def run_load_test(self):
        """Run the complete load test"""
        logger.info(f"Starting load test: {self.config.target_rps} RPS for {self.config.duration_seconds}s")
        
        await self.initialize()
        
        self.running = True
        self.metrics.start_time = time.time()
        
        # Calculate worker distribution
        total_requests = self.config.target_rps * self.config.duration_seconds
        num_workers = min(self.config.concurrent_connections, total_requests)
        requests_per_worker = total_requests // num_workers
        
        logger.info(f"Distributing {total_requests} requests across {num_workers} workers")
        logger.info(f"Each worker will make ~{requests_per_worker} requests")
        
        # Start results processor
        processor_task = asyncio.create_task(self.results_processor())
        
        # Create and start worker tasks
        worker_tasks = []
        for i in range(num_workers):
            task = asyncio.create_task(self.request_worker(i, requests_per_worker))
            worker_tasks.append(task)
        
        try:
            # Wait for all workers to complete
            await asyncio.gather(*worker_tasks)
            
            # Stop processing
            self.running = False
            await processor_task
            
            self.metrics.end_time = time.time()
            
            logger.info("Load test completed successfully")
            
        except Exception as e:
            logger.error(f"Load test failed: {e}")
            self.running = False
            
        finally:
            await self.cleanup()
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        if not self.metrics.response_times:
            return {"error": "No data collected"}
        
        response_times = np.array(self.metrics.response_times)
        total_duration = self.metrics.end_time - self.metrics.start_time
        
        report = {
            "summary": {
                "total_requests": self.metrics.total_requests,
                "successful_requests": self.metrics.successful_requests,
                "failed_requests": self.metrics.failed_requests,
                "success_rate": (self.metrics.successful_requests / self.metrics.total_requests) * 100,
                "total_duration_seconds": total_duration,
                "actual_rps": self.metrics.total_requests / total_duration if total_duration > 0 else 0,
                "target_rps": self.config.target_rps,
                "rps_achievement": (self.metrics.total_requests / total_duration) / self.config.target_rps * 100 if total_duration > 0 else 0
            },
            "response_times": {
                "min_ms": float(np.min(response_times)),
                "max_ms": float(np.max(response_times)),
                "mean_ms": float(np.mean(response_times)),
                "median_ms": float(np.median(response_times)),
                "p95_ms": float(np.percentile(response_times, 95)),
                "p99_ms": float(np.percentile(response_times, 99)),
                "p99_9_ms": float(np.percentile(response_times, 99.9)),
                "std_dev_ms": float(np.std(response_times))
            },
            "performance_validation": {
                "sub_100ms_target": {
                    "target_p95": 100.0,
                    "actual_p95": float(np.percentile(response_times, 95)),
                    "passed": float(np.percentile(response_times, 95)) < 100.0
                },
                "rps_target": {
                    "target": self.config.target_rps,
                    "actual": self.metrics.total_requests / total_duration if total_duration > 0 else 0,
                    "passed": (self.metrics.total_requests / total_duration) >= (self.config.target_rps * 0.95) if total_duration > 0 else False
                },
                "success_rate_target": {
                    "target": 99.9,
                    "actual": (self.metrics.successful_requests / self.metrics.total_requests) * 100,
                    "passed": (self.metrics.successful_requests / self.metrics.total_requests) * 100 >= 99.9
                }
            },
            "errors": self.metrics.errors,
            "rps_timeline": self.metrics.rps_per_second,
            "configuration": {
                "target_rps": self.config.target_rps,
                "duration_seconds": self.config.duration_seconds,
                "concurrent_connections": self.config.concurrent_connections,
                "endpoints": self.config.endpoints
            }
        }
        
        return report
    
    def save_report(self, report: Dict[str, Any], filename: Optional[str] = None):
        """Save report to file"""
        if filename is None:
            filename = f"load_test_report_{int(time.time())}.json"
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Report saved to {filename}")
    
    def create_visualizations(self, report: Dict[str, Any]):
        """Create performance visualizations"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # Response time histogram
        if self.metrics.response_times:
            axes[0, 0].hist(self.metrics.response_times, bins=50, alpha=0.7)
            axes[0, 0].set_title('Response Time Distribution')
            axes[0, 0].set_xlabel('Response Time (ms)')
            axes[0, 0].set_ylabel('Frequency')
            axes[0, 0].axvline(100, color='red', linestyle='--', label='100ms target')
            axes[0, 0].legend()
        
        # RPS timeline
        if self.metrics.rps_per_second:
            axes[0, 1].plot(self.metrics.rps_per_second)
            axes[0, 1].set_title('Requests Per Second Over Time')
            axes[0, 1].set_xlabel('Time (seconds)')
            axes[0, 1].set_ylabel('RPS')
            axes[0, 1].axhline(self.config.target_rps, color='red', linestyle='--', label=f'{self.config.target_rps} RPS target')
            axes[0, 1].legend()
        
        # Response time percentiles
        if self.metrics.response_times:
            percentiles = [50, 75, 90, 95, 99, 99.9]
            values = [np.percentile(self.metrics.response_times, p) for p in percentiles]
            axes[1, 0].bar(range(len(percentiles)), values)
            axes[1, 0].set_title('Response Time Percentiles')
            axes[1, 0].set_xlabel('Percentile')
            axes[1, 0].set_ylabel('Response Time (ms)')
            axes[1, 0].set_xticks(range(len(percentiles)))
            axes[1, 0].set_xticklabels([f'P{p}' for p in percentiles])
            axes[1, 0].axhline(100, color='red', linestyle='--', label='100ms target')
            axes[1, 0].legend()
        
        # Success/Error breakdown
        success_count = self.metrics.successful_requests
        error_count = self.metrics.failed_requests
        
        if success_count > 0 or error_count > 0:
            labels = ['Success', 'Errors']
            values = [success_count, error_count]
            colors = ['green', 'red']
            
            axes[1, 1].pie(values, labels=labels, colors=colors, autopct='%1.1f%%')
            axes[1, 1].set_title('Success/Error Rate')
        
        plt.tight_layout()
        timestamp = int(time.time())
        plt.savefig(f'load_test_visualization_{timestamp}.png', dpi=300, bbox_inches='tight')
        logger.info(f"Visualizations saved to load_test_visualization_{timestamp}.png")
        plt.close()

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal, stopping test...")
    sys.exit(0)

async def main():
    parser = argparse.ArgumentParser(description="Anti-Bot Security Framework Load Test")
    parser.add_argument('--url', default='http://localhost:8000', help='Base URL for testing')
    parser.add_argument('--rps', type=int, default=100000, help='Target requests per second')
    parser.add_argument('--duration', type=int, default=300, help='Test duration in seconds')
    parser.add_argument('--connections', type=int, default=10000, help='Concurrent connections')
    parser.add_argument('--timeout', type=int, default=5, help='Request timeout in seconds')
    parser.add_argument('--output', help='Output file for report')
    parser.add_argument('--visualize', action='store_true', help='Generate visualizations')
    
    args = parser.parse_args()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    config = TestConfig(
        base_url=args.url,
        target_rps=args.rps,
        duration_seconds=args.duration,
        concurrent_connections=args.connections,
        timeout_seconds=args.timeout
    )
    
    runner = LoadTestRunner(config)
    
    try:
        await runner.run_load_test()
        
        # Generate and save report
        report = runner.generate_report()
        runner.save_report(report, args.output)
        
        # Print summary
        summary = report.get('summary', {})
        perf_validation = report.get('performance_validation', {})
        
        print("\n" + "="*80)
        print("LOAD TEST RESULTS SUMMARY")
        print("="*80)
        print(f"Total Requests: {summary.get('total_requests', 0):,}")
        print(f"Successful Requests: {summary.get('successful_requests', 0):,}")
        print(f"Failed Requests: {summary.get('failed_requests', 0):,}")
        print(f"Success Rate: {summary.get('success_rate', 0):.2f}%")
        print(f"Actual RPS: {summary.get('actual_rps', 0):,.0f}")
        print(f"Target RPS: {summary.get('target_rps', 0):,}")
        print(f"RPS Achievement: {summary.get('rps_achievement', 0):.1f}%")
        
        print("\nPERFORMANCE VALIDATION:")
        print(f"Sub-100ms (P95): {'✓ PASSED' if perf_validation.get('sub_100ms_target', {}).get('passed') else '✗ FAILED'}")
        print(f"  Target: <100ms, Actual: {perf_validation.get('sub_100ms_target', {}).get('actual_p95', 0):.1f}ms")
        
        print(f"RPS Target: {'✓ PASSED' if perf_validation.get('rps_target', {}).get('passed') else '✗ FAILED'}")
        print(f"  Target: {perf_validation.get('rps_target', {}).get('target', 0):,}, Actual: {perf_validation.get('rps_target', {}).get('actual', 0):,.0f}")
        
        print(f"Success Rate: {'✓ PASSED' if perf_validation.get('success_rate_target', {}).get('passed') else '✗ FAILED'}")
        print(f"  Target: >99.9%, Actual: {perf_validation.get('success_rate_target', {}).get('actual', 0):.2f}%")
        
        # Response time breakdown
        rt = report.get('response_times', {})
        print("\nRESPONSE TIMES:")
        print(f"  Min: {rt.get('min_ms', 0):.1f}ms")
        print(f"  Mean: {rt.get('mean_ms', 0):.1f}ms")
        print(f"  Median: {rt.get('median_ms', 0):.1f}ms")
        print(f"  P95: {rt.get('p95_ms', 0):.1f}ms")
        print(f"  P99: {rt.get('p99_ms', 0):.1f}ms")
        print(f"  Max: {rt.get('max_ms', 0):.1f}ms")
        
        # Error breakdown
        errors = report.get('errors', {})
        if errors:
            print("\nERRORS:")
            for error_type, count in errors.items():
                print(f"  {error_type}: {count:,}")
        
        print("="*80)
        
        # Generate visualizations if requested
        if args.visualize:
            runner.create_visualizations(report)
            
        # Determine overall test result
        all_passed = all([
            perf_validation.get('sub_100ms_target', {}).get('passed', False),
            perf_validation.get('rps_target', {}).get('passed', False),
            perf_validation.get('success_rate_target', {}).get('passed', False)
        ])
        
        if all_passed:
            print("\n🎉 LOAD TEST PASSED - All performance targets met!")
            sys.exit(0)
        else:
            print("\n❌ LOAD TEST FAILED - Some performance targets not met")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Load test failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())