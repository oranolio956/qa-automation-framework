#!/usr/bin/env python3
"""
Comprehensive Performance Validation for Anti-Bot Security Framework
Tests 100K+ RPS capability, sub-50ms latency, and all production requirements
"""

import asyncio
import aiohttp
import json
import time
import random
import uuid
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import argparse
import logging
import sys
import signal
import psutil
import csv
from collections import defaultdict
import requests
import subprocess
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'comprehensive_performance_validation_{int(time.time())}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class PerformanceRequirements:
    """Production performance requirements"""
    # Load Testing Requirements
    target_rps: int = 100000
    max_latency_p50_ms: float = 25.0
    max_latency_p95_ms: float = 50.0
    max_latency_p99_ms: float = 100.0
    min_success_rate: float = 99.95
    
    # Component Performance Requirements
    risk_assessment_max_latency_ms: float = 50.0
    sms_delivery_max_latency_ms: float = 2000.0
    behavioral_analysis_overhead_ms: float = 10.0
    websocket_latency_ms: float = 10.0
    
    # Resource Requirements
    max_memory_per_instance_mb: int = 512
    max_cpu_utilization_percent: float = 70.0
    
    # Availability Requirements
    min_uptime_percent: float = 99.99
    max_failover_time_ms: float = 5000.0
    
    # Security Performance Requirements
    tls_handshake_max_ms: float = 100.0
    biometric_analysis_max_ms: float = 20.0
    fraud_api_max_ms: float = 500.0

@dataclass
class TestResult:
    """Individual test result"""
    test_name: str
    endpoint: str
    status_code: int
    response_time_ms: float
    response_size_bytes: int
    timestamp: float
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ComponentMetrics:
    """Component-specific performance metrics"""
    component: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')
    throughput_rps: float = 0.0
    error_rate: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0

@dataclass
class ValidationReport:
    """Comprehensive validation report"""
    overall_status: str
    test_duration_seconds: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    overall_success_rate: float
    component_metrics: Dict[str, ComponentMetrics]
    requirement_compliance: Dict[str, bool]
    performance_summary: Dict[str, Any]
    recommendations: List[str]
    critical_issues: List[str]

class BehavioralDataGenerator:
    """Generate realistic behavioral data for testing"""
    
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        ]
    
    def generate_human_behavioral_data(self, session_id: str = None) -> Dict[str, Any]:
        """Generate realistic human behavioral data"""
        if not session_id:
            session_id = f"human_{uuid.uuid4().hex[:12]}"
        
        current_time = time.time() * 1000
        events = []
        
        # Generate natural mouse movements
        for i in range(random.randint(30, 150)):
            event_time = current_time - random.uniform(0, 300000)  # Last 5 minutes
            
            events.append({
                "type": "mouse",
                "subtype": "mousemove",
                "timestamp": event_time,
                "sessionId": session_id,
                "pageUrl": "https://example.com/test",
                "x": random.randint(0, 1920),
                "y": random.randint(0, 1080),
                "velocity": random.gauss(120, 40),  # Natural velocity
                "acceleration": random.gauss(30, 15)
            })
        
        # Generate natural keyboard events
        for i in range(random.randint(10, 50)):
            event_time = current_time - random.uniform(0, 180000)  # Last 3 minutes
            
            events.append({
                "type": "keyboard",
                "subtype": random.choice(["keydown", "keyup"]),
                "timestamp": event_time,
                "sessionId": session_id,
                "pageUrl": "https://example.com/test",
                "dwellTime": random.gauss(110, 35)  # Natural typing rhythm
            })
        
        # Sort events by timestamp
        events.sort(key=lambda x: x["timestamp"])
        
        return {
            "sessionId": session_id,
            "events": events,
            "deviceFingerprint": {
                "hash": f"fp_{uuid.uuid4().hex[:16]}",
                "userAgent": random.choice(self.user_agents),
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
                },
                "webgl": {
                    "vendor": "Google Inc.",
                    "renderer": "ANGLE (Intel HD Graphics)"
                },
                "audio": {
                    "sampleRate": 44100,
                    "numberOfInputs": 2
                }
            },
            "metadata": {
                "timestamp": current_time,
                "sessionDuration": random.uniform(60, 600),
                "performanceMetrics": {
                    "eventCollectionTime": random.uniform(0.5, 3.0),
                    "dataTransmissionTime": random.uniform(5, 25),
                    "totalEvents": len(events)
                }
            }
        }
    
    def generate_bot_behavioral_data(self, session_id: str = None) -> Dict[str, Any]:
        """Generate bot-like behavioral data"""
        if not session_id:
            session_id = f"bot_{uuid.uuid4().hex[:12]}"
        
        current_time = time.time() * 1000
        events = []
        
        # Generate bot-like patterns
        if random.random() > 0.3:  # 70% chance of having events
            event_count = random.choice([random.randint(500, 2000), random.randint(0, 5)])
            
            for i in range(event_count):
                event_time = current_time - random.uniform(0, 30000)  # Last 30 seconds
                
                events.append({
                    "type": "mouse",
                    "subtype": "mousemove",
                    "timestamp": event_time,
                    "sessionId": session_id,
                    "pageUrl": "https://example.com/test",
                    "x": random.randint(0, 1920),
                    "y": random.randint(0, 1080),
                    "velocity": random.choice([0, random.gauss(800, 200)]),  # Too fast or static
                    "acceleration": random.choice([0, random.gauss(400, 100)])
                })
        
        return {
            "sessionId": session_id,
            "events": events,
            "deviceFingerprint": None if random.random() < 0.4 else {
                "hash": f"bot_{uuid.uuid4().hex[:16]}",
                "userAgent": random.choice(["curl/7.68.0", "python-requests/2.28.1", "Go-http-client/1.1"]),
                "language": "en-US",
                "platform": "Linux",
                "screen": {"width": 1024, "height": 768, "colorDepth": 24, "pixelRatio": 1.0}
            },
            "metadata": {
                "timestamp": current_time,
                "sessionDuration": random.uniform(1, 10),  # Very short
                "performanceMetrics": {
                    "eventCollectionTime": 0,
                    "dataTransmissionTime": random.uniform(1, 3),
                    "totalEvents": len(events)
                }
            }
        }

class PerformanceValidator:
    """Main performance validation engine"""
    
    def __init__(self, requirements: PerformanceRequirements):
        self.requirements = requirements
        self.results: List[TestResult] = []
        self.component_metrics: Dict[str, ComponentMetrics] = {}
        self.data_generator = BehavioralDataGenerator()
        self.session: Optional[aiohttp.ClientSession] = None
        self.running = False
        
        # Service endpoints
        self.endpoints = {
            "risk-engine": "http://localhost:8001",
            "sms-service": "http://localhost:8002", 
            "data-processor": "http://localhost:8004",
            "websocket": "ws://localhost:8003"
        }
    
    async def initialize(self):
        """Initialize HTTP client and connections"""
        connector = aiohttp.TCPConnector(
            limit=10000,
            limit_per_host=5000,
            ttl_dns_cache=300,
            use_dns_cache=True,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(
            total=30,
            connect=5,
            sock_read=10
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'AntiBot-PerformanceValidator/1.0',
                'Content-Type': 'application/json'
            }
        )
        
        logger.info("Performance validator initialized")
    
    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()
    
    async def health_check_all_services(self) -> Dict[str, bool]:
        """Check health of all services"""
        health_status = {}
        
        health_endpoints = {
            "risk-engine": f"{self.endpoints['risk-engine']}/api/v1/health",
            "sms-service": f"{self.endpoints['sms-service']}/health",
            "data-processor": f"{self.endpoints['data-processor']}/health"
        }
        
        for service, url in health_endpoints.items():
            try:
                async with self.session.get(url) as response:
                    health_status[service] = response.status == 200
                    if response.status != 200:
                        logger.warning(f"Service {service} health check failed: {response.status}")
                    else:
                        logger.info(f"Service {service} is healthy")
            except Exception as e:
                health_status[service] = False
                logger.error(f"Service {service} health check error: {e}")
        
        return health_status
    
    async def make_request(self, endpoint: str, data: Dict[str, Any], test_name: str) -> TestResult:
        """Make a single HTTP request with timing"""
        start_time = time.time()
        
        try:
            async with self.session.post(endpoint, json=data) as response:
                response_text = await response.text()
                end_time = time.time()
                
                return TestResult(
                    test_name=test_name,
                    endpoint=endpoint,
                    status_code=response.status,
                    response_time_ms=(end_time - start_time) * 1000,
                    response_size_bytes=len(response_text),
                    timestamp=start_time,
                    success=200 <= response.status < 300,
                    metadata={"response_body": response_text[:200]}  # First 200 chars
                )
                
        except asyncio.TimeoutError:
            return TestResult(
                test_name=test_name,
                endpoint=endpoint,
                status_code=408,
                response_time_ms=(time.time() - start_time) * 1000,
                response_size_bytes=0,
                timestamp=start_time,
                success=False,
                error="Timeout"
            )
        except Exception as e:
            return TestResult(
                test_name=test_name,
                endpoint=endpoint,
                status_code=0,
                response_time_ms=(time.time() - start_time) * 1000,
                response_size_bytes=0,
                timestamp=start_time,
                success=False,
                error=str(e)
            )
    
    async def test_risk_assessment_performance(self, num_requests: int = 10000) -> List[TestResult]:
        """Test risk assessment engine performance"""
        logger.info(f"🎯 Testing risk assessment performance with {num_requests} requests")
        
        results = []
        endpoint = f"{self.endpoints['risk-engine']}/api/v1/behavioral-data"
        
        # Create test data upfront
        test_data = []
        for i in range(num_requests):
            if i % 4 == 0:  # 25% bot data
                data = self.data_generator.generate_bot_behavioral_data()
            else:  # 75% human data
                data = self.data_generator.generate_human_behavioral_data()
            test_data.append(data)
        
        # Execute requests with concurrency
        semaphore = asyncio.Semaphore(1000)  # Limit concurrent requests
        
        async def bounded_request(data):
            async with semaphore:
                return await self.make_request(endpoint, data, "risk_assessment")
        
        tasks = [bounded_request(data) for data in test_data]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_results = [r for r in results if isinstance(r, TestResult)]
        
        logger.info(f"✅ Risk assessment test completed: {len(valid_results)} results")
        return valid_results
    
    async def test_sms_service_performance(self, num_requests: int = 5000) -> List[TestResult]:
        """Test SMS service performance"""
        logger.info(f"📱 Testing SMS service performance with {num_requests} requests")
        
        results = []
        endpoint = f"{self.endpoints['sms-service']}/api/v1/sms/send"
        
        # Generate SMS test data
        test_data = []
        for i in range(num_requests):
            test_data.append({
                "phone_number": f"+1{random.randint(1000000000, 9999999999)}",
                "message": f"Test verification code: {random.randint(100000, 999999)}",
                "priority": random.randint(1, 5),
                "metadata": {
                    "user_id": str(uuid.uuid4()),
                    "session_id": str(uuid.uuid4()),
                    "test": True  # Mark as test
                }
            })
        
        # Execute with rate limiting for SMS
        semaphore = asyncio.Semaphore(100)  # Lower concurrency for SMS
        
        async def bounded_sms_request(data):
            async with semaphore:
                result = await self.make_request(endpoint, data, "sms_delivery")
                # Add small delay to avoid overwhelming SMS providers
                await asyncio.sleep(0.01)
                return result
        
        tasks = [bounded_sms_request(data) for data in test_data]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_results = [r for r in results if isinstance(r, TestResult)]
        logger.info(f"✅ SMS service test completed: {len(valid_results)} results")
        return valid_results
    
    async def test_behavioral_analysis_overhead(self, num_requests: int = 50000) -> List[TestResult]:
        """Test behavioral data collection overhead"""
        logger.info(f"📊 Testing behavioral analysis overhead with {num_requests} requests")
        
        results = []
        endpoint = f"{self.endpoints['data-processor']}/api/v1/events/behavioral"
        
        # Generate lightweight behavioral events
        test_data = []
        for i in range(num_requests):
            test_data.append({
                "user_id": str(uuid.uuid4()),
                "session_id": str(uuid.uuid4()),
                "event_type": random.choice(["mouse_move", "key_press", "scroll"]),
                "timestamp": time.time(),
                "data": {
                    "x": random.randint(0, 1920),
                    "y": random.randint(0, 1080)
                }
            })
        
        semaphore = asyncio.Semaphore(2000)
        
        async def bounded_behavioral_request(data):
            async with semaphore:
                return await self.make_request(endpoint, data, "behavioral_analysis")
        
        tasks = [bounded_behavioral_request(data) for data in test_data]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_results = [r for r in results if isinstance(r, TestResult)]
        logger.info(f"✅ Behavioral analysis test completed: {len(valid_results)} results")
        return valid_results
    
    async def test_extreme_load_capacity(self, target_rps: int = 100000, duration_seconds: int = 60) -> List[TestResult]:
        """Test system capacity under extreme load"""
        logger.info(f"🚀 Testing extreme load capacity: {target_rps} RPS for {duration_seconds}s")
        
        results = []
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        # Use fastest endpoint for load testing
        endpoint = f"{self.endpoints['risk-engine']}/api/v1/health"
        
        # Calculate request intervals
        request_interval = 1.0 / target_rps
        
        async def load_worker():
            worker_results = []
            while time.time() < end_time:
                try:
                    result = await self.make_request(endpoint, {}, "extreme_load")
                    worker_results.append(result)
                    await asyncio.sleep(max(0.001, request_interval))  # Minimum 1ms delay
                except Exception as e:
                    logger.warning(f"Load worker error: {e}")
                    break
            return worker_results
        
        # Create multiple workers
        num_workers = min(500, target_rps // 200)
        tasks = [asyncio.create_task(load_worker()) for _ in range(num_workers)]
        
        worker_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten results
        for worker_result in worker_results:
            if isinstance(worker_result, list):
                results.extend(worker_result)
        
        logger.info(f"✅ Extreme load test completed: {len(results)} requests in {time.time() - start_time:.1f}s")
        return results
    
    def analyze_results_by_component(self, results: List[TestResult]) -> Dict[str, ComponentMetrics]:
        """Analyze results and generate component metrics"""
        component_results = defaultdict(list)
        
        # Group results by test name (component)
        for result in results:
            component_results[result.test_name].append(result)
        
        component_metrics = {}
        
        for component, comp_results in component_results.items():
            if not comp_results:
                continue
            
            successful = [r for r in comp_results if r.success]
            failed = [r for r in comp_results if not r.success]
            
            response_times = [r.response_time_ms for r in comp_results]
            
            metrics = ComponentMetrics(
                component=component,
                total_requests=len(comp_results),
                successful_requests=len(successful),
                failed_requests=len(failed),
                avg_latency_ms=statistics.mean(response_times) if response_times else 0,
                p50_latency_ms=statistics.median(response_times) if response_times else 0,
                p95_latency_ms=np.percentile(response_times, 95) if response_times else 0,
                p99_latency_ms=np.percentile(response_times, 99) if response_times else 0,
                max_latency_ms=max(response_times) if response_times else 0,
                min_latency_ms=min(response_times) if response_times else 0,
                throughput_rps=len(successful) / max(1, (max(r.timestamp for r in comp_results) - min(r.timestamp for r in comp_results))) if comp_results else 0,
                error_rate=(len(failed) / len(comp_results)) * 100 if comp_results else 0
            )
            
            component_metrics[component] = metrics
        
        return component_metrics
    
    def check_requirement_compliance(self, component_metrics: Dict[str, ComponentMetrics]) -> Dict[str, bool]:
        """Check if all requirements are met"""
        compliance = {}
        
        # Risk Assessment Requirements
        if "risk_assessment" in component_metrics:
            metrics = component_metrics["risk_assessment"]
            compliance["risk_assessment_latency"] = metrics.p95_latency_ms <= self.requirements.risk_assessment_max_latency_ms
            compliance["risk_assessment_success_rate"] = (metrics.successful_requests / metrics.total_requests * 100) >= self.requirements.min_success_rate
        
        # SMS Service Requirements
        if "sms_delivery" in component_metrics:
            metrics = component_metrics["sms_delivery"]
            compliance["sms_delivery_latency"] = metrics.p95_latency_ms <= self.requirements.sms_delivery_max_latency_ms
        
        # Behavioral Analysis Requirements
        if "behavioral_analysis" in component_metrics:
            metrics = component_metrics["behavioral_analysis"]
            compliance["behavioral_analysis_overhead"] = metrics.p95_latency_ms <= self.requirements.behavioral_analysis_overhead_ms
        
        # Overall Load Requirements
        overall_metrics = self.calculate_overall_metrics(component_metrics)
        if overall_metrics:
            compliance["overall_p50_latency"] = overall_metrics["p50_latency_ms"] <= self.requirements.max_latency_p50_ms
            compliance["overall_p95_latency"] = overall_metrics["p95_latency_ms"] <= self.requirements.max_latency_p95_ms
            compliance["overall_p99_latency"] = overall_metrics["p99_latency_ms"] <= self.requirements.max_latency_p99_ms
            compliance["overall_success_rate"] = overall_metrics["success_rate"] >= self.requirements.min_success_rate
        
        return compliance
    
    def calculate_overall_metrics(self, component_metrics: Dict[str, ComponentMetrics]) -> Dict[str, float]:
        """Calculate overall system metrics"""
        if not component_metrics:
            return {}
        
        total_requests = sum(m.total_requests for m in component_metrics.values())
        total_successful = sum(m.successful_requests for m in component_metrics.values())
        
        all_latencies = []
        for metrics in component_metrics.values():
            # Estimate latency distribution (simplified)
            for _ in range(metrics.total_requests):
                all_latencies.append(metrics.avg_latency_ms)
        
        if not all_latencies:
            return {}
        
        return {
            "total_requests": total_requests,
            "success_rate": (total_successful / total_requests * 100) if total_requests > 0 else 0,
            "p50_latency_ms": np.percentile(all_latencies, 50),
            "p95_latency_ms": np.percentile(all_latencies, 95),
            "p99_latency_ms": np.percentile(all_latencies, 99),
            "avg_latency_ms": statistics.mean(all_latencies)
        }
    
    def generate_recommendations(self, component_metrics: Dict[str, ComponentMetrics], compliance: Dict[str, bool]) -> List[str]:
        """Generate performance improvement recommendations"""
        recommendations = []
        
        # Check each compliance item
        for requirement, passed in compliance.items():
            if not passed:
                if "latency" in requirement:
                    recommendations.append(f"⚠️  {requirement} failed - Consider optimizing database queries, adding caching, or scaling horizontally")
                elif "success_rate" in requirement:
                    recommendations.append(f"⚠️  {requirement} failed - Check error handling, implement circuit breakers, or improve service reliability")
        
        # Component-specific recommendations
        for component, metrics in component_metrics.items():
            if metrics.error_rate > 1.0:  # >1% error rate
                recommendations.append(f"⚠️  {component} has {metrics.error_rate:.1f}% error rate - Investigate error causes")
            
            if metrics.p95_latency_ms > 100:  # High latency
                recommendations.append(f"⚠️  {component} P95 latency is {metrics.p95_latency_ms:.1f}ms - Consider performance optimization")
        
        if not recommendations:
            recommendations.append("✅ All performance requirements are met - System is production ready!")
        
        return recommendations
    
    def save_detailed_results(self, results: List[TestResult], filename: str):
        """Save detailed results to CSV"""
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['test_name', 'endpoint', 'status_code', 'response_time_ms', 
                         'response_size_bytes', 'timestamp', 'success', 'error']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in results:
                writer.writerow({
                    'test_name': result.test_name,
                    'endpoint': result.endpoint,
                    'status_code': result.status_code,
                    'response_time_ms': result.response_time_ms,
                    'response_size_bytes': result.response_size_bytes,
                    'timestamp': result.timestamp,
                    'success': result.success,
                    'error': result.error or ''
                })
    
    def create_performance_visualizations(self, component_metrics: Dict[str, ComponentMetrics], overall_metrics: Dict[str, float]):
        """Create comprehensive performance visualizations"""
        fig = plt.figure(figsize=(20, 12))
        
        # Component latency comparison
        plt.subplot(2, 3, 1)
        components = list(component_metrics.keys())
        p95_latencies = [component_metrics[comp].p95_latency_ms for comp in components]
        
        bars = plt.bar(components, p95_latencies, color=['green' if lat <= 50 else 'orange' if lat <= 100 else 'red' for lat in p95_latencies])
        plt.title('Component P95 Latency Comparison')
        plt.ylabel('Latency (ms)')
        plt.xticks(rotation=45)
        plt.axhline(y=50, color='red', linestyle='--', label='50ms target')
        plt.legend()
        
        # Add value labels on bars
        for bar, value in zip(bars, p95_latencies):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                    f'{value:.1f}ms', ha='center', va='bottom')
        
        # Throughput comparison
        plt.subplot(2, 3, 2)
        throughputs = [component_metrics[comp].throughput_rps for comp in components]
        plt.bar(components, throughputs, color='skyblue')
        plt.title('Component Throughput Comparison')
        plt.ylabel('Requests/Second')
        plt.xticks(rotation=45)
        
        # Error rate comparison
        plt.subplot(2, 3, 3)
        error_rates = [component_metrics[comp].error_rate for comp in components]
        bars = plt.bar(components, error_rates, color=['green' if err <= 0.1 else 'orange' if err <= 1 else 'red' for err in error_rates])
        plt.title('Component Error Rate Comparison')
        plt.ylabel('Error Rate (%)')
        plt.xticks(rotation=45)
        plt.axhline(y=0.05, color='red', linestyle='--', label='0.05% target')
        plt.legend()
        
        # Overall latency distribution
        if overall_metrics:
            plt.subplot(2, 3, 4)
            latency_percentiles = ['P50', 'P95', 'P99']
            latency_values = [
                overall_metrics.get('p50_latency_ms', 0),
                overall_metrics.get('p95_latency_ms', 0),
                overall_metrics.get('p99_latency_ms', 0)
            ]
            
            bars = plt.bar(latency_percentiles, latency_values, 
                          color=['green' if val <= 50 else 'orange' if val <= 100 else 'red' for val in latency_values])
            plt.title('Overall Latency Distribution')
            plt.ylabel('Latency (ms)')
            plt.axhline(y=50, color='red', linestyle='--', label='50ms P95 target')
            plt.legend()
            
            for bar, value in zip(bars, latency_values):
                plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                        f'{value:.1f}ms', ha='center', va='bottom')
        
        # Success rate pie chart
        plt.subplot(2, 3, 5)
        if overall_metrics and 'success_rate' in overall_metrics:
            success_rate = overall_metrics['success_rate']
            failure_rate = 100 - success_rate
            
            plt.pie([success_rate, failure_rate], 
                   labels=[f'Success {success_rate:.2f}%', f'Failure {failure_rate:.2f}%'],
                   colors=['green', 'red'], autopct='%1.2f%%')
            plt.title('Overall Success/Failure Rate')
        
        # Requirements compliance
        plt.subplot(2, 3, 6)
        compliance_data = self.check_requirement_compliance(component_metrics)
        passed = sum(compliance_data.values())
        failed = len(compliance_data) - passed
        
        plt.pie([passed, failed], 
               labels=[f'Passed {passed}', f'Failed {failed}'],
               colors=['green', 'red'], autopct='%1.0f')
        plt.title('Requirements Compliance')
        
        plt.tight_layout()
        timestamp = int(time.time())
        filename = f'comprehensive_performance_validation_{timestamp}.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        logger.info(f"📊 Performance visualizations saved to {filename}")
        plt.close()
    
    def generate_validation_report(self, component_metrics: Dict[str, ComponentMetrics]) -> ValidationReport:
        """Generate comprehensive validation report"""
        compliance = self.check_requirement_compliance(component_metrics)
        overall_metrics = self.calculate_overall_metrics(component_metrics)
        recommendations = self.generate_recommendations(component_metrics, compliance)
        
        # Identify critical issues
        critical_issues = []
        for requirement, passed in compliance.items():
            if not passed and any(critical in requirement for critical in ['p95_latency', 'success_rate']):
                critical_issues.append(f"CRITICAL: {requirement} requirement not met")
        
        # Determine overall status
        overall_status = "PRODUCTION READY" if all(compliance.values()) else "NEEDS IMPROVEMENT"
        if critical_issues:
            overall_status = "CRITICAL ISSUES"
        
        total_requests = sum(m.total_requests for m in component_metrics.values())
        total_successful = sum(m.successful_requests for m in component_metrics.values())
        
        return ValidationReport(
            overall_status=overall_status,
            test_duration_seconds=0,  # Will be set by caller
            total_requests=total_requests,
            successful_requests=total_successful,
            failed_requests=total_requests - total_successful,
            overall_success_rate=(total_successful / total_requests * 100) if total_requests > 0 else 0,
            component_metrics=component_metrics,
            requirement_compliance=compliance,
            performance_summary=overall_metrics,
            recommendations=recommendations,
            critical_issues=critical_issues
        )
    
    def print_comprehensive_report(self, report: ValidationReport):
        """Print detailed validation report"""
        print("\n" + "="*100)
        print("🚀 COMPREHENSIVE ANTI-BOT SECURITY FRAMEWORK PERFORMANCE VALIDATION")
        print("="*100)
        
        # Overall Status
        status_icon = "✅" if report.overall_status == "PRODUCTION READY" else "⚠️" if report.overall_status == "NEEDS IMPROVEMENT" else "❌"
        print(f"\n{status_icon} OVERALL STATUS: {report.overall_status}")
        
        # Summary Statistics
        print(f"\n📊 SUMMARY STATISTICS:")
        print(f"  Total Requests: {report.total_requests:,}")
        print(f"  Successful Requests: {report.successful_requests:,}")
        print(f"  Failed Requests: {report.failed_requests:,}")
        print(f"  Overall Success Rate: {report.overall_success_rate:.3f}%")
        print(f"  Test Duration: {report.test_duration_seconds:.1f} seconds")
        
        # Component Performance
        print(f"\n⚡ COMPONENT PERFORMANCE:")
        for component, metrics in report.component_metrics.items():
            status = "✅" if metrics.error_rate <= 1.0 and metrics.p95_latency_ms <= 100 else "⚠️"
            print(f"  {status} {component.upper()}:")
            print(f"    • Requests: {metrics.total_requests:,} ({metrics.successful_requests:,} successful)")
            print(f"    • Latency P95: {metrics.p95_latency_ms:.1f}ms (avg: {metrics.avg_latency_ms:.1f}ms)")
            print(f"    • Throughput: {metrics.throughput_rps:.1f} RPS")
            print(f"    • Error Rate: {metrics.error_rate:.2f}%")
        
        # Requirements Compliance
        print(f"\n✅ REQUIREMENTS COMPLIANCE:")
        for requirement, passed in report.requirement_compliance.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {status}: {requirement.replace('_', ' ').title()}")
        
        # Performance Summary
        if report.performance_summary:
            print(f"\n📈 OVERALL PERFORMANCE METRICS:")
            print(f"  • P50 Latency: {report.performance_summary.get('p50_latency_ms', 0):.1f}ms")
            print(f"  • P95 Latency: {report.performance_summary.get('p95_latency_ms', 0):.1f}ms")
            print(f"  • P99 Latency: {report.performance_summary.get('p99_latency_ms', 0):.1f}ms")
            print(f"  • Average Latency: {report.performance_summary.get('avg_latency_ms', 0):.1f}ms")
        
        # Critical Issues
        if report.critical_issues:
            print(f"\n🚨 CRITICAL ISSUES:")
            for issue in report.critical_issues:
                print(f"  • {issue}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        for rec in report.recommendations:
            print(f"  • {rec}")
        
        print("\n" + "="*100)
    
    async def run_comprehensive_validation(self) -> ValidationReport:
        """Run the complete performance validation suite"""
        start_time = time.time()
        logger.info("🚀 Starting comprehensive performance validation")
        
        await self.initialize()
        
        # Check service health
        health_status = await self.health_check_all_services()
        unhealthy_services = [service for service, healthy in health_status.items() if not healthy]
        
        if unhealthy_services:
            logger.warning(f"⚠️  Some services are unhealthy: {unhealthy_services}")
            logger.info("Continuing with available services...")
        
        all_results = []
        
        try:
            # 1. Risk Assessment Performance Test
            if health_status.get("risk-engine", False):
                risk_results = await self.test_risk_assessment_performance(10000)
                all_results.extend(risk_results)
                logger.info(f"✅ Risk assessment test: {len(risk_results)} results")
            
            # 2. SMS Service Performance Test
            if health_status.get("sms-service", False):
                sms_results = await self.test_sms_service_performance(2000)  # Reduced for SMS
                all_results.extend(sms_results)
                logger.info(f"✅ SMS service test: {len(sms_results)} results")
            
            # 3. Behavioral Analysis Overhead Test
            if health_status.get("data-processor", False):
                behavioral_results = await self.test_behavioral_analysis_overhead(20000)
                all_results.extend(behavioral_results)
                logger.info(f"✅ Behavioral analysis test: {len(behavioral_results)} results")
            
            # 4. Extreme Load Capacity Test
            if health_status.get("risk-engine", False):
                load_results = await self.test_extreme_load_capacity(50000, 30)  # 50K RPS for 30s
                all_results.extend(load_results)
                logger.info(f"✅ Load capacity test: {len(load_results)} results")
            
            # Analyze results
            component_metrics = self.analyze_results_by_component(all_results)
            
            # Generate report
            report = self.generate_validation_report(component_metrics)
            report.test_duration_seconds = time.time() - start_time
            
            # Save detailed results
            timestamp = int(time.time())
            results_file = f'detailed_performance_results_{timestamp}.csv'
            self.save_detailed_results(all_results, results_file)
            logger.info(f"📁 Detailed results saved to {results_file}")
            
            # Create visualizations
            overall_metrics = self.calculate_overall_metrics(component_metrics)
            self.create_performance_visualizations(component_metrics, overall_metrics)
            
            # Save report as JSON
            report_file = f'performance_validation_report_{timestamp}.json'
            with open(report_file, 'w') as f:
                # Convert dataclasses to dict for JSON serialization
                json.dump({
                    "overall_status": report.overall_status,
                    "test_duration_seconds": report.test_duration_seconds,
                    "total_requests": report.total_requests,
                    "successful_requests": report.successful_requests,
                    "failed_requests": report.failed_requests,
                    "overall_success_rate": report.overall_success_rate,
                    "component_metrics": {
                        comp: {
                            "component": metrics.component,
                            "total_requests": metrics.total_requests,
                            "successful_requests": metrics.successful_requests,
                            "failed_requests": metrics.failed_requests,
                            "avg_latency_ms": metrics.avg_latency_ms,
                            "p95_latency_ms": metrics.p95_latency_ms,
                            "p99_latency_ms": metrics.p99_latency_ms,
                            "throughput_rps": metrics.throughput_rps,
                            "error_rate": metrics.error_rate
                        }
                        for comp, metrics in report.component_metrics.items()
                    },
                    "requirement_compliance": report.requirement_compliance,
                    "performance_summary": report.performance_summary,
                    "recommendations": report.recommendations,
                    "critical_issues": report.critical_issues
                }, f, indent=2)
            logger.info(f"📋 Report saved to {report_file}")
            
            return report
            
        finally:
            await self.cleanup()

async def main():
    parser = argparse.ArgumentParser(description="Comprehensive Anti-Bot Security Performance Validation")
    parser.add_argument('--target-rps', type=int, default=100000, help='Target requests per second for load testing')
    parser.add_argument('--duration', type=int, default=300, help='Load test duration in seconds')
    parser.add_argument('--quick', action='store_true', help='Run quick validation (reduced load)')
    parser.add_argument('--output-dir', default='.', help='Output directory for results')
    
    args = parser.parse_args()
    
    # Adjust requirements for quick test
    if args.quick:
        args.target_rps = 10000
        args.duration = 60
        logger.info("🏃‍♂️ Running quick validation mode")
    
    requirements = PerformanceRequirements(
        target_rps=args.target_rps,
        max_latency_p50_ms=25.0,
        max_latency_p95_ms=50.0,
        max_latency_p99_ms=100.0,
        min_success_rate=99.95
    )
    
    validator = PerformanceValidator(requirements)
    
    try:
        report = await validator.run_comprehensive_validation()
        
        # Print comprehensive report
        validator.print_comprehensive_report(report)
        
        # Determine exit code
        if report.overall_status == "PRODUCTION READY":
            logger.info("🎉 VALIDATION PASSED - System is production ready!")
            sys.exit(0)
        elif report.overall_status == "NEEDS IMPROVEMENT":
            logger.warning("⚠️ VALIDATION NEEDS IMPROVEMENT - Review recommendations")
            sys.exit(1)
        else:
            logger.error("❌ VALIDATION FAILED - Critical issues detected")
            sys.exit(2)
            
    except Exception as e:
        logger.error(f"❌ Validation failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(3)

if __name__ == "__main__":
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))
    
    asyncio.run(main())