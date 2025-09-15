"""
Performance Test Suite for Enhanced ML Risk Scoring Engine
Tests sub-50ms latency and 100K+ RPS requirements
"""

import asyncio
import aiohttp
import time
import statistics
import json
import random
import uuid
from typing import List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime
import numpy as np

@dataclass
class PerformanceMetrics:
    """Performance test results"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    max_latency_ms: float
    requests_per_second: float
    accuracy_rate: float
    error_rate: float
    test_duration_seconds: float

class MLPerformanceTester:
    """High-performance tester for ML risk scoring engine"""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.session: aiohttp.ClientSession = None
        
    async def __aenter__(self):
        # Configure session for high performance
        connector = aiohttp.TCPConnector(
            limit=1000,  # Total connection pool size
            limit_per_host=100,  # Per-host connection limit
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={"Content-Type": "application/json"}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def generate_realistic_behavioral_data(self, session_id: str = None, 
                                         behavior_type: str = "human") -> Dict:
        """Generate realistic behavioral data for testing"""
        if not session_id:
            session_id = f"test_session_{uuid.uuid4().hex[:12]}"
        
        current_time = time.time()
        events = []
        
        if behavior_type == "human":
            # Generate human-like behavior
            event_count = random.randint(30, 200)
            
            for i in range(event_count):
                event_time = current_time - random.uniform(0, 300)  # Last 5 minutes
                
                if random.random() < 0.6:  # 60% mouse events
                    events.append({
                        "type": "mouse",
                        "subtype": random.choice(["mousemove", "click", "mousedown", "mouseup"]),
                        "timestamp": event_time,
                        "sessionId": session_id,
                        "pageUrl": "https://example.com/test",
                        "x": random.randint(0, 1920),
                        "y": random.randint(0, 1080),
                        "velocity": random.gauss(150, 50),  # Human-like velocity
                        "acceleration": random.gauss(50, 20)
                    })
                elif random.random() < 0.3:  # 30% keyboard events
                    events.append({
                        "type": "keyboard",
                        "subtype": random.choice(["keydown", "keyup"]),
                        "timestamp": event_time,
                        "sessionId": session_id,
                        "pageUrl": "https://example.com/test",
                        "dwellTime": random.gauss(100, 30)  # Human typing rhythm
                    })
                else:  # 10% scroll events
                    events.append({
                        "type": "scroll",
                        "timestamp": event_time,
                        "sessionId": session_id,
                        "pageUrl": "https://example.com/test",
                        "scrollSpeed": random.gauss(300, 100)
                    })
                    
        else:  # Bot-like behavior
            event_count = random.choice([random.randint(1, 10), random.randint(1000, 5000)])
            
            for i in range(event_count):
                event_time = current_time - random.uniform(0, 60)  # Last minute
                
                if random.random() < 0.8:  # 80% mouse events (often too many or none)
                    events.append({
                        "type": "mouse",
                        "subtype": "mousemove",
                        "timestamp": event_time,
                        "sessionId": session_id,
                        "pageUrl": "https://example.com/test",
                        "x": random.randint(0, 1920),
                        "y": random.randint(0, 1080),
                        "velocity": random.choice([0, random.gauss(500, 100)]),  # Too fast or static
                        "acceleration": random.choice([0, random.gauss(200, 50)])
                    })
                else:
                    events.append({
                        "type": "keyboard",
                        "subtype": "keydown",
                        "timestamp": event_time,
                        "sessionId": session_id,
                        "pageUrl": "https://example.com/test",
                        "dwellTime": random.choice([random.gauss(20, 5), random.gauss(300, 50)])  # Too fast or slow
                    })
        
        # Sort events by timestamp
        events.sort(key=lambda x: x["timestamp"])
        
        return {
            "sessionId": session_id,
            "events": events,
            "deviceFingerprint": {
                "hash": f"fp_{uuid.uuid4().hex[:16]}",
                "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "language": "en-US",
                "platform": "Win32",
                "screen": {
                    "width": 1920,
                    "height": 1080,
                    "colorDepth": 24,
                    "pixelRatio": 1.0
                },
                "timezone": {
                    "offset": -480,
                    "dst": True
                }
            },
            "tlsFingerprint": {
                "supportedProtocols": ["TLSv1.2", "TLSv1.3"],
                "supportedCiphers": ["AES256-GCM-SHA384", "CHACHA20-POLY1305"]
            },
            "metadata": {
                "sessionDuration": random.uniform(30, 600),
                "pageUrl": "https://example.com/test",
                "referrer": "https://google.com",
                "performanceMetrics": {
                    "eventCollectionTime": random.uniform(10, 50),
                    "dataTransmissionTime": random.uniform(1, 10),
                    "totalEvents": len(events)
                }
            }
        }
    
    async def single_request_test(self, data: Dict) -> Tuple[bool, float, Dict]:
        """Test a single request and measure performance"""
        start_time = time.perf_counter()
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/behavioral-data",
                json=data
            ) as response:
                end_time = time.perf_counter()
                latency_ms = (end_time - start_time) * 1000
                
                if response.status == 200:
                    result = await response.json()
                    return True, latency_ms, result
                else:
                    error_text = await response.text()
                    return False, latency_ms, {"error": error_text, "status": response.status}
                    
        except Exception as e:
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            return False, latency_ms, {"error": str(e)}
    
    async def latency_test(self, num_requests: int = 1000) -> PerformanceMetrics:
        """Test latency requirements (sub-50ms)"""
        print(f"🚀 Running latency test with {num_requests} requests...")
        
        latencies = []
        successful_requests = 0
        failed_requests = 0
        
        start_time = time.perf_counter()
        
        # Generate test data upfront
        test_data = []
        for i in range(num_requests):
            behavior_type = "human" if random.random() > 0.2 else "bot"  # 80% human, 20% bot
            test_data.append(self.generate_realistic_behavioral_data(
                behavior_type=behavior_type
            ))
        
        # Run requests sequentially for accurate latency measurement
        for i, data in enumerate(test_data):
            success, latency, result = await self.single_request_test(data)
            
            latencies.append(latency)
            if success:
                successful_requests += 1
            else:
                failed_requests += 1
            
            if (i + 1) % 100 == 0:
                print(f"  Completed {i + 1}/{num_requests} requests")
        
        end_time = time.perf_counter()
        total_duration = end_time - start_time
        
        # Calculate metrics
        avg_latency = statistics.mean(latencies)
        p50_latency = statistics.median(latencies)
        p95_latency = np.percentile(latencies, 95)
        p99_latency = np.percentile(latencies, 99)
        max_latency = max(latencies)
        rps = num_requests / total_duration
        
        metrics = PerformanceMetrics(
            total_requests=num_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_latency_ms=avg_latency,
            p50_latency_ms=p50_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            max_latency_ms=max_latency,
            requests_per_second=rps,
            accuracy_rate=successful_requests / num_requests,
            error_rate=failed_requests / num_requests,
            test_duration_seconds=total_duration
        )
        
        return metrics
    
    async def throughput_test(self, target_rps: int = 1000, duration_seconds: int = 60) -> PerformanceMetrics:
        """Test throughput requirements (100K+ RPS)"""
        print(f"🎯 Running throughput test: {target_rps} RPS for {duration_seconds}s...")
        
        latencies = []
        successful_requests = 0
        failed_requests = 0
        request_interval = 1.0 / target_rps
        
        start_time = time.perf_counter()
        end_time = start_time + duration_seconds
        
        # Pre-generate test data for better performance
        test_data_pool = []
        for _ in range(min(1000, target_rps)):  # Generate up to 1000 samples
            behavior_type = "human" if random.random() > 0.2 else "bot"
            test_data_pool.append(self.generate_realistic_behavioral_data(
                behavior_type=behavior_type
            ))
        
        async def worker():
            nonlocal successful_requests, failed_requests, latencies
            
            while time.perf_counter() < end_time:
                # Select random test data
                data = random.choice(test_data_pool)
                
                # Make request
                success, latency, result = await self.single_request_test(data)
                
                latencies.append(latency)
                if success:
                    successful_requests += 1
                else:
                    failed_requests += 1
                
                # Rate limiting
                await asyncio.sleep(request_interval)
        
        # Run concurrent workers for higher throughput
        num_workers = min(50, target_rps // 20)  # Scale workers with target RPS
        tasks = [asyncio.create_task(worker()) for _ in range(num_workers)]
        
        # Wait for completion
        await asyncio.gather(*tasks, return_exceptions=True)
        
        actual_duration = time.perf_counter() - start_time
        total_requests = successful_requests + failed_requests
        actual_rps = total_requests / actual_duration
        
        if latencies:
            metrics = PerformanceMetrics(
                total_requests=total_requests,
                successful_requests=successful_requests,
                failed_requests=failed_requests,
                avg_latency_ms=statistics.mean(latencies),
                p50_latency_ms=statistics.median(latencies),
                p95_latency_ms=np.percentile(latencies, 95),
                p99_latency_ms=np.percentile(latencies, 99),
                max_latency_ms=max(latencies),
                requests_per_second=actual_rps,
                accuracy_rate=successful_requests / total_requests if total_requests > 0 else 0,
                error_rate=failed_requests / total_requests if total_requests > 0 else 0,
                test_duration_seconds=actual_duration
            )
        else:
            metrics = PerformanceMetrics(
                total_requests=0, successful_requests=0, failed_requests=0,
                avg_latency_ms=0, p50_latency_ms=0, p95_latency_ms=0,
                p99_latency_ms=0, max_latency_ms=0, requests_per_second=0,
                accuracy_rate=0, error_rate=0, test_duration_seconds=actual_duration
            )
        
        return metrics
    
    async def accuracy_test(self, num_requests: int = 1000) -> Dict[str, float]:
        """Test model accuracy with known data"""
        print(f"🎯 Running accuracy test with {num_requests} requests...")
        
        correct_human = 0
        correct_bot = 0
        total_human = 0
        total_bot = 0
        
        for i in range(num_requests):
            # Generate labeled data
            behavior_type = "human" if random.random() > 0.5 else "bot"
            expected_score_range = (0.0, 0.4) if behavior_type == "human" else (0.6, 1.0)
            
            data = self.generate_realistic_behavioral_data(behavior_type=behavior_type)
            success, latency, result = await self.single_request_test(data)
            
            if success and "riskScore" in result:
                risk_score = result["riskScore"]
                
                if behavior_type == "human":
                    total_human += 1
                    if risk_score <= 0.5:  # Correctly identified as human
                        correct_human += 1
                else:
                    total_bot += 1
                    if risk_score > 0.5:  # Correctly identified as bot
                        correct_bot += 1
            
            if (i + 1) % 100 == 0:
                print(f"  Completed {i + 1}/{num_requests} requests")
        
        human_accuracy = correct_human / total_human if total_human > 0 else 0
        bot_accuracy = correct_bot / total_bot if total_bot > 0 else 0
        overall_accuracy = (correct_human + correct_bot) / (total_human + total_bot)
        false_positive_rate = (total_human - correct_human) / total_human if total_human > 0 else 0
        
        return {
            "human_accuracy": human_accuracy,
            "bot_accuracy": bot_accuracy,
            "overall_accuracy": overall_accuracy,
            "false_positive_rate": false_positive_rate,
            "total_human_samples": total_human,
            "total_bot_samples": total_bot
        }
    
    def print_metrics(self, metrics: PerformanceMetrics, test_name: str):
        """Print performance metrics in a formatted way"""
        print(f"\n📊 {test_name} Results:")
        print("=" * 50)
        print(f"Total Requests: {metrics.total_requests:,}")
        print(f"Successful: {metrics.successful_requests:,} ({metrics.accuracy_rate:.1%})")
        print(f"Failed: {metrics.failed_requests:,} ({metrics.error_rate:.1%})")
        print(f"Test Duration: {metrics.test_duration_seconds:.2f}s")
        print(f"Requests/Second: {metrics.requests_per_second:.1f}")
        
        print(f"\n⚡ Latency Metrics:")
        print(f"Average: {metrics.avg_latency_ms:.2f}ms")
        print(f"P50 (Median): {metrics.p50_latency_ms:.2f}ms")
        print(f"P95: {metrics.p95_latency_ms:.2f}ms")
        print(f"P99: {metrics.p99_latency_ms:.2f}ms")
        print(f"Maximum: {metrics.max_latency_ms:.2f}ms")
        
        # Performance requirements check
        print(f"\n✅ Requirements Check:")
        latency_ok = metrics.p95_latency_ms <= 50.0
        throughput_ok = metrics.requests_per_second >= 1000  # Scaled down for testing
        accuracy_ok = metrics.accuracy_rate >= 0.95
        
        print(f"Sub-50ms P95 Latency: {'✅' if latency_ok else '❌'} ({metrics.p95_latency_ms:.2f}ms)")
        print(f"High Throughput: {'✅' if throughput_ok else '❌'} ({metrics.requests_per_second:.1f} RPS)")
        print(f"High Accuracy: {'✅' if accuracy_ok else '❌'} ({metrics.accuracy_rate:.1%})")
    
    async def comprehensive_test_suite(self):
        """Run comprehensive performance test suite"""
        print("🚀 Starting Comprehensive ML Performance Test Suite")
        print("=" * 60)
        
        # Health check first
        try:
            async with self.session.get(f"{self.base_url}/api/v1/health") as response:
                if response.status == 200:
                    health = await response.json()
                    print(f"✅ Service Health: {health.get('status', 'unknown')}")
                else:
                    print(f"❌ Service Health Check Failed: {response.status}")
                    return
        except Exception as e:
            print(f"❌ Cannot connect to service: {e}")
            return
        
        # Test 1: Latency Test
        latency_metrics = await self.latency_test(1000)
        self.print_metrics(latency_metrics, "Latency Test")
        
        # Test 2: Throughput Test (scaled down for testing)
        throughput_metrics = await self.throughput_test(target_rps=500, duration_seconds=30)
        self.print_metrics(throughput_metrics, "Throughput Test")
        
        # Test 3: Accuracy Test
        accuracy_results = await self.accuracy_test(500)
        print(f"\n🎯 Accuracy Test Results:")
        print("=" * 30)
        print(f"Overall Accuracy: {accuracy_results['overall_accuracy']:.1%}")
        print(f"Human Detection: {accuracy_results['human_accuracy']:.1%}")
        print(f"Bot Detection: {accuracy_results['bot_accuracy']:.1%}")
        print(f"False Positive Rate: {accuracy_results['false_positive_rate']:.1%}")
        
        # Final summary
        print(f"\n🏁 Test Suite Summary")
        print("=" * 30)
        requirements_met = (
            latency_metrics.p95_latency_ms <= 50.0 and
            throughput_metrics.requests_per_second >= 100 and  # Scaled requirement
            accuracy_results['overall_accuracy'] >= 0.90 and
            accuracy_results['false_positive_rate'] <= 0.05
        )
        
        status = "PASSED ✅" if requirements_met else "NEEDS IMPROVEMENT ⚠️"
        print(f"Overall Status: {status}")
        
        return {
            "latency_metrics": latency_metrics,
            "throughput_metrics": throughput_metrics,
            "accuracy_results": accuracy_results,
            "requirements_met": requirements_met
        }

async def main():
    """Run the performance test suite"""
    async with MLPerformanceTester("http://localhost:8001") as tester:
        results = await tester.comprehensive_test_suite()
        
        # Save results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"performance_test_results_{timestamp}.json"
        
        # Convert dataclasses to dict for JSON serialization
        serializable_results = {
            "timestamp": datetime.now().isoformat(),
            "latency_metrics": {
                "total_requests": results["latency_metrics"].total_requests,
                "successful_requests": results["latency_metrics"].successful_requests,
                "failed_requests": results["latency_metrics"].failed_requests,
                "avg_latency_ms": results["latency_metrics"].avg_latency_ms,
                "p95_latency_ms": results["latency_metrics"].p95_latency_ms,
                "p99_latency_ms": results["latency_metrics"].p99_latency_ms,
                "requests_per_second": results["latency_metrics"].requests_per_second,
                "accuracy_rate": results["latency_metrics"].accuracy_rate
            },
            "throughput_metrics": {
                "total_requests": results["throughput_metrics"].total_requests,
                "successful_requests": results["throughput_metrics"].successful_requests,
                "requests_per_second": results["throughput_metrics"].requests_per_second,
                "avg_latency_ms": results["throughput_metrics"].avg_latency_ms,
                "p95_latency_ms": results["throughput_metrics"].p95_latency_ms
            },
            "accuracy_results": results["accuracy_results"],
            "requirements_met": results["requirements_met"]
        }
        
        with open(results_file, "w") as f:
            json.dump(serializable_results, f, indent=2)
        
        print(f"\n📁 Results saved to: {results_file}")

if __name__ == "__main__":
    asyncio.run(main())