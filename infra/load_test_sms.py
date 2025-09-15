#!/usr/bin/env python3
"""
SMS Infrastructure Load Testing
Tests SMS service under various load conditions with real performance metrics
"""

import asyncio
import aiohttp
import argparse
import json
import time
import statistics
from datetime import datetime, timedelta
from typing import List, Dict
import random

class SMSLoadTester:
    """Load testing for SMS infrastructure"""
    
    def __init__(self, base_url: str = "http://localhost:8002"):
        self.base_url = base_url
        self.results = []
        self.errors = []
        
    async def send_test_sms(self, session: aiohttp.ClientSession, phone_number: str, priority: int = 1) -> Dict:
        """Send a single test SMS and measure performance"""
        start_time = time.time()
        
        payload = {
            "phone_number": phone_number,
            "message": f"Load test message {int(time.time())} - Priority {priority}",
            "priority": priority,
            "metadata": {
                "test": True,
                "load_test": True,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        try:
            async with session.post(
                f"{self.base_url}/api/v1/sms/queue",  # Use queue endpoint for load testing
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                
                result = {
                    "timestamp": datetime.now().isoformat(),
                    "phone_number": phone_number,
                    "priority": priority,
                    "response_time_ms": response_time,
                    "status_code": response.status,
                    "success": response.status in [200, 201, 202]
                }
                
                if result["success"]:
                    response_data = await response.json()
                    result["response_data"] = response_data
                else:
                    error_text = await response.text()
                    result["error"] = error_text
                    self.errors.append(result)
                
                return result
                
        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            error_result = {
                "timestamp": datetime.now().isoformat(),
                "phone_number": phone_number,
                "priority": priority,
                "response_time_ms": response_time,
                "status_code": 0,
                "success": False,
                "error": str(e)
            }
            
            self.errors.append(error_result)
            return error_result
    
    async def queue_burst_test(self, concurrent_requests: int, total_messages: int) -> List[Dict]:
        """Test queue endpoint with concurrent requests"""
        print(f"🚀 Starting queue burst test: {concurrent_requests} concurrent, {total_messages} total messages")
        
        # Generate test phone numbers
        phone_numbers = [f"+155512{str(i).zfill(5)}" for i in range(1000)]
        
        async with aiohttp.ClientSession() as session:
            semaphore = asyncio.Semaphore(concurrent_requests)
            
            async def bounded_request(phone_number: str, priority: int):
                async with semaphore:
                    return await self.send_test_sms(session, phone_number, priority)
            
            # Create tasks with random priorities and phone numbers
            tasks = []
            for i in range(total_messages):
                phone_number = random.choice(phone_numbers)
                priority = random.randint(1, 5)  # Random priority 1-5
                tasks.append(bounded_request(phone_number, priority))
            
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # Filter out exceptions and process results
            valid_results = [r for r in results if isinstance(r, dict)]
            exceptions = [r for r in results if not isinstance(r, dict)]
            
            test_duration = end_time - start_time
            successful_requests = sum(1 for r in valid_results if r.get("success", False))
            failed_requests = len(valid_results) - successful_requests + len(exceptions)
            
            print(f"✅ Queue burst test completed:")
            print(f"   Duration: {test_duration:.2f}s")
            print(f"   Throughput: {total_messages/test_duration:.2f} requests/second")
            print(f"   Success: {successful_requests}/{total_messages} ({successful_requests/total_messages*100:.1f}%)")
            print(f"   Failed: {failed_requests}")
            print(f"   Exceptions: {len(exceptions)}")
            
            self.results.extend(valid_results)
            return valid_results
    
    async def sustained_load_test(self, rps: int, duration_seconds: int) -> List[Dict]:
        """Test sustained load at specific requests per second"""
        print(f"⏱️  Starting sustained load test: {rps} RPS for {duration_seconds} seconds")
        
        phone_numbers = [f"+155513{str(i).zfill(5)}" for i in range(100)]
        results = []
        
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            request_interval = 1.0 / rps
            next_request_time = start_time
            
            while (time.time() - start_time) < duration_seconds:
                current_time = time.time()
                
                if current_time >= next_request_time:
                    phone_number = random.choice(phone_numbers)
                    priority = random.randint(1, 3)
                    
                    # Fire and forget to maintain RPS
                    task = asyncio.create_task(self.send_test_sms(session, phone_number, priority))
                    results.append(task)
                    
                    next_request_time += request_interval
                
                # Small sleep to prevent busy waiting
                await asyncio.sleep(0.01)
            
            print(f"🔄 Waiting for {len(results)} requests to complete...")
            completed_results = await asyncio.gather(*results, return_exceptions=True)
            
            valid_results = [r for r in completed_results if isinstance(r, dict)]
            successful_requests = sum(1 for r in valid_results if r.get("success", False))
            
            actual_duration = time.time() - start_time
            actual_rps = len(valid_results) / actual_duration
            
            print(f"✅ Sustained load test completed:")
            print(f"   Target RPS: {rps}, Actual RPS: {actual_rps:.2f}")
            print(f"   Total requests: {len(valid_results)}")
            print(f"   Success rate: {successful_requests/len(valid_results)*100:.1f}%")
            
            self.results.extend(valid_results)
            return valid_results
    
    async def priority_test(self, messages_per_priority: int) -> Dict:
        """Test priority queue handling"""
        print(f"🎯 Starting priority queue test: {messages_per_priority} messages per priority level")
        
        phone_numbers = [f"+155514{str(i).zfill(5)}" for i in range(50)]
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            
            # Create messages for each priority level (1-5)
            for priority in range(1, 6):
                for i in range(messages_per_priority):
                    phone_number = random.choice(phone_numbers)
                    tasks.append(self.send_test_sms(session, phone_number, priority))
            
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            valid_results = [r for r in results if isinstance(r, dict)]
            
            # Analyze by priority
            priority_stats = {}
            for priority in range(1, 6):
                priority_results = [r for r in valid_results if r.get("priority") == priority]
                if priority_results:
                    response_times = [r["response_time_ms"] for r in priority_results]
                    success_count = sum(1 for r in priority_results if r.get("success", False))
                    
                    priority_stats[priority] = {
                        "count": len(priority_results),
                        "success_rate": success_count / len(priority_results) * 100,
                        "avg_response_time": statistics.mean(response_times),
                        "p95_response_time": statistics.quantiles(response_times, n=20)[18] if len(response_times) > 5 else 0
                    }
            
            print(f"✅ Priority test completed in {end_time - start_time:.2f}s:")
            for priority, stats in priority_stats.items():
                print(f"   P{priority}: {stats['count']} msgs, {stats['success_rate']:.1f}% success, {stats['avg_response_time']:.0f}ms avg")
            
            self.results.extend(valid_results)
            return priority_stats
    
    async def health_check_during_load(self) -> Dict:
        """Check service health during load testing"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health", timeout=5) as response:
                    if response.status == 200:
                        health_data = await response.json()
                        return {
                            "healthy": True,
                            "data": health_data,
                            "response_time": response.headers.get("X-Response-Time", "unknown")
                        }
                    else:
                        return {"healthy": False, "status_code": response.status}
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    def generate_report(self):
        """Generate comprehensive load test report"""
        if not self.results:
            print("❌ No test results to analyze")
            return
        
        successful_results = [r for r in self.results if r.get("success", False)]
        failed_results = [r for r in self.results if not r.get("success", False)]
        
        response_times = [r["response_time_ms"] for r in successful_results]
        
        if not response_times:
            print("❌ No successful requests to analyze")
            return
        
        print(f"\n{'='*60}")
        print(f"SMS LOAD TEST REPORT")
        print(f"{'='*60}")
        
        print(f"\n📊 Overall Statistics:")
        print(f"   Total Requests: {len(self.results)}")
        print(f"   Successful: {len(successful_results)} ({len(successful_results)/len(self.results)*100:.1f}%)")
        print(f"   Failed: {len(failed_results)} ({len(failed_results)/len(self.results)*100:.1f}%)")
        
        print(f"\n⚡ Response Time Statistics:")
        print(f"   Average: {statistics.mean(response_times):.2f}ms")
        print(f"   Median: {statistics.median(response_times):.2f}ms")
        print(f"   Min: {min(response_times):.2f}ms")
        print(f"   Max: {max(response_times):.2f}ms")
        
        if len(response_times) > 10:
            percentiles = statistics.quantiles(response_times, n=100)
            print(f"   P50: {percentiles[49]:.2f}ms")
            print(f"   P95: {percentiles[94]:.2f}ms")
            print(f"   P99: {percentiles[98]:.2f}ms")
        
        # Error analysis
        if self.errors:
            print(f"\n❌ Error Analysis:")
            error_types = {}
            for error in self.errors:
                error_key = str(error.get("status_code", "unknown"))
                error_types[error_key] = error_types.get(error_key, 0) + 1
            
            for error_type, count in error_types.items():
                print(f"   Status {error_type}: {count} errors")
        
        # Performance assessment
        avg_response_time = statistics.mean(response_times)
        success_rate = len(successful_results) / len(self.results) * 100
        
        print(f"\n🎯 Performance Assessment:")
        if avg_response_time < 100 and success_rate > 99:
            print(f"   ✅ EXCELLENT: Service handling load very well")
        elif avg_response_time < 200 and success_rate > 95:
            print(f"   ✅ GOOD: Service performing well under load")
        elif avg_response_time < 500 and success_rate > 90:
            print(f"   ⚠️  ACCEPTABLE: Service handling load with some degradation")
        else:
            print(f"   ❌ POOR: Service struggling with current load")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        if avg_response_time > 200:
            print(f"   • Consider scaling SMS workers (current may be overloaded)")
        if success_rate < 95:
            print(f"   • Investigate error causes and improve error handling")
        if len(failed_results) > 0:
            print(f"   • Review failed requests for patterns")
        print(f"   • Monitor queue sizes during peak load")
        print(f"   • Consider adding more phone numbers to pool if rate limited")

async def main():
    """Main load testing function"""
    parser = argparse.ArgumentParser(description="SMS Infrastructure Load Testing")
    parser.add_argument("--base-url", default="http://localhost:8002", help="SMS service base URL")
    parser.add_argument("--concurrent", type=int, default=10, help="Concurrent requests for burst test")
    parser.add_argument("--messages", type=int, default=100, help="Total messages for burst test")
    parser.add_argument("--rps", type=int, default=5, help="Requests per second for sustained test")
    parser.add_argument("--duration", type=int, default=30, help="Duration in seconds for sustained test")
    parser.add_argument("--priority-messages", type=int, default=20, help="Messages per priority level")
    parser.add_argument("--test-type", choices=["all", "burst", "sustained", "priority"], default="all", 
                       help="Type of test to run")
    
    args = parser.parse_args()
    
    tester = SMSLoadTester(args.base_url)
    
    print(f"🧪 SMS Infrastructure Load Testing")
    print(f"Target: {args.base_url}")
    print(f"Test Type: {args.test_type}\n")
    
    # Check service health before testing
    health = await tester.health_check_during_load()
    if not health.get("healthy"):
        print("❌ Service is not healthy, aborting tests")
        print(f"Health check result: {health}")
        return
    
    print("✅ Service is healthy, starting tests...\n")
    
    try:
        if args.test_type in ["all", "burst"]:
            await tester.queue_burst_test(args.concurrent, args.messages)
            print()
        
        if args.test_type in ["all", "sustained"]:
            await tester.sustained_load_test(args.rps, args.duration)
            print()
        
        if args.test_type in ["all", "priority"]:
            await tester.priority_test(args.priority_messages)
            print()
        
        # Final health check
        print("🔍 Final health check...")
        final_health = await tester.health_check_during_load()
        if final_health.get("healthy"):
            print("✅ Service remained healthy throughout testing")
        else:
            print("⚠️  Service health degraded during testing")
            print(f"Final health: {final_health}")
        
        # Generate comprehensive report
        tester.generate_report()
        
    except KeyboardInterrupt:
        print("\n⚠️  Load testing interrupted by user")
        if tester.results:
            tester.generate_report()

if __name__ == "__main__":
    asyncio.run(main())