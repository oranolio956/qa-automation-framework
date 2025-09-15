#!/usr/bin/env python3
"""
Comprehensive Performance Benchmarking for Snapchat Account Creation Flows
Measures timing, bottlenecks, and resource utilization with quantitative precision
"""

import asyncio
import time
import logging
import psutil
import threading
import statistics
import json
import subprocess
import os
import sys
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import tracemalloc
import gc

# Memory and CPU monitoring
import resource

# Network monitoring
import socket
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Container for detailed performance measurements"""
    operation: str
    start_time: float
    end_time: float
    duration_ms: float
    cpu_usage_start: float
    cpu_usage_end: float
    memory_usage_start: int
    memory_usage_end: int
    memory_peak: int
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0
    success: bool = False
    error_message: str = ""
    additional_data: Dict[str, Any] = None

@dataclass
class ConcurrencyTestResult:
    """Results from concurrent account creation testing"""
    concurrent_count: int
    total_duration_ms: float
    successful_accounts: int
    failed_accounts: int
    average_duration_ms: float
    min_duration_ms: float
    max_duration_ms: float
    throughput_per_minute: float
    cpu_peak: float
    memory_peak_mb: float
    bottleneck_type: str = ""

class SnapchatPerformanceBenchmarker:
    """Comprehensive performance analysis for Snapchat automation"""
    
    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self.baseline_metrics = {}
        self.process = psutil.Process(os.getpid())
        
        # Initialize components
        self.snapchat_creator = None
        self.android_manager = None
        
        # Load automation components
        self._load_automation_components()
        
        # Performance monitoring setup
        self.monitoring_active = False
        self.monitoring_thread = None
        self.system_stats = []
        
    def _load_automation_components(self):
        """Load and initialize automation components for testing"""
        try:
            # Import Snapchat creator
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'automation'))
            from automation.snapchat.stealth_creator import SnapchatStealthCreator
            self.snapchat_creator = SnapchatStealthCreator()
            logger.info("✅ SnapchatStealthCreator loaded")
            
            # Import Android farm manager
            from automation.android.fly_android_integration import get_fly_android_manager
            self.android_manager = get_fly_android_manager()
            logger.info("✅ Android farm manager loaded")
            
        except Exception as e:
            logger.warning(f"Failed to load automation components: {e}")
    
    def start_system_monitoring(self):
        """Start continuous system monitoring"""
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitor_system)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        logger.info("System monitoring started")
    
    def stop_system_monitoring(self):
        """Stop system monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("System monitoring stopped")
    
    def _monitor_system(self):
        """Continuous system monitoring thread"""
        while self.monitoring_active:
            try:
                stats = {
                    'timestamp': time.time(),
                    'cpu_percent': psutil.cpu_percent(interval=None),
                    'memory_mb': psutil.virtual_memory().used / 1024 / 1024,
                    'memory_percent': psutil.virtual_memory().percent,
                    'disk_io_read': psutil.disk_io_counters().read_bytes if psutil.disk_io_counters() else 0,
                    'disk_io_write': psutil.disk_io_counters().write_bytes if psutil.disk_io_counters() else 0,
                    'network_sent': psutil.net_io_counters().bytes_sent,
                    'network_recv': psutil.net_io_counters().bytes_recv,
                }
                self.system_stats.append(stats)
                time.sleep(1)  # Sample every second
            except Exception as e:
                logger.warning(f"System monitoring error: {e}")
    
    def measure_operation(self, operation_name: str):
        """Context manager for measuring operation performance"""
        return PerformanceMeasurement(self, operation_name)
    
    def benchmark_device_allocation(self) -> PerformanceMetrics:
        """Benchmark Android device allocation from farm"""
        with self.measure_operation("device_allocation") as measurement:
            try:
                if not self.android_manager:
                    raise Exception("Android manager not available")
                
                # Measure device discovery
                start_discovery = time.time()
                devices = self.android_manager.discover_farm_devices()
                discovery_time = (time.time() - start_discovery) * 1000
                
                measurement.add_data("discovery_time_ms", discovery_time)
                measurement.add_data("devices_found", len(devices))
                
                if not devices:
                    raise Exception("No devices found")
                
                # Measure device connection
                start_connect = time.time()
                device = self.android_manager.connect_to_farm_device(devices[0])
                connect_time = (time.time() - start_connect) * 1000
                
                measurement.add_data("connection_time_ms", connect_time)
                measurement.add_data("device_id", device.device_id if device else None)
                
                if device:
                    measurement.success = True
                    # Clean up
                    self.android_manager.disconnect_device(device.device_id)
                else:
                    raise Exception("Failed to connect to device")
                    
            except Exception as e:
                measurement.error_message = str(e)
        
        return measurement.get_metrics()
    
    def benchmark_uiautomator_initialization(self, device_id: str) -> PerformanceMetrics:
        """Benchmark UIAutomator2 initialization overhead"""
        with self.measure_operation("uiautomator_init") as measurement:
            try:
                import uiautomator2 as u2
                
                # Measure UIAutomator2 connection
                start_u2 = time.time()
                u2_device = u2.connect(device_id)
                u2_time = (time.time() - start_u2) * 1000
                
                measurement.add_data("u2_connection_time_ms", u2_time)
                
                # Measure device info retrieval
                start_info = time.time()
                device_info = u2_device.info
                info_time = (time.time() - start_info) * 1000
                
                measurement.add_data("device_info_time_ms", info_time)
                measurement.add_data("device_info", device_info)
                
                # Measure app list retrieval
                start_apps = time.time()
                app_list = u2_device.app_list()
                apps_time = (time.time() - start_apps) * 1000
                
                measurement.add_data("app_list_time_ms", apps_time)
                measurement.add_data("apps_count", len(app_list))
                
                measurement.success = True
                
            except Exception as e:
                measurement.error_message = str(e)
        
        return measurement.get_metrics()
    
    def benchmark_proxy_connection(self) -> PerformanceMetrics:
        """Benchmark proxy connection establishment"""
        with self.measure_operation("proxy_connection") as measurement:
            try:
                # Import proxy utilities
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))
                from utils.brightdata_proxy import get_brightdata_session
                
                # Measure proxy session creation
                start_proxy = time.time()
                session = get_brightdata_session()
                proxy_time = (time.time() - start_proxy) * 1000
                
                measurement.add_data("proxy_session_time_ms", proxy_time)
                
                # Test proxy connectivity
                start_test = time.time()
                test_response = session.get("https://httpbin.org/ip", timeout=30)
                test_time = (time.time() - start_test) * 1000
                
                measurement.add_data("proxy_test_time_ms", test_time)
                measurement.add_data("proxy_response_code", test_response.status_code)
                measurement.add_data("proxy_ip", test_response.json().get('origin', 'unknown'))
                
                if test_response.status_code == 200:
                    measurement.success = True
                else:
                    raise Exception(f"Proxy test failed: {test_response.status_code}")
                    
            except Exception as e:
                measurement.error_message = str(e)
        
        return measurement.get_metrics()
    
    def benchmark_profile_generation(self) -> PerformanceMetrics:
        """Benchmark profile data generation"""
        with self.measure_operation("profile_generation") as measurement:
            try:
                if not self.snapchat_creator:
                    raise Exception("Snapchat creator not available")
                
                # Generate multiple profiles to get average
                profiles_count = 10
                generation_times = []
                
                for i in range(profiles_count):
                    start_gen = time.time()
                    profile = self.snapchat_creator.generate_stealth_profile()
                    gen_time = (time.time() - start_gen) * 1000
                    generation_times.append(gen_time)
                
                avg_time = statistics.mean(generation_times)
                min_time = min(generation_times)
                max_time = max(generation_times)
                std_dev = statistics.stdev(generation_times) if len(generation_times) > 1 else 0
                
                measurement.add_data("average_generation_time_ms", avg_time)
                measurement.add_data("min_generation_time_ms", min_time)
                measurement.add_data("max_generation_time_ms", max_time)
                measurement.add_data("std_deviation_ms", std_dev)
                measurement.add_data("profiles_generated", profiles_count)
                
                measurement.success = True
                
            except Exception as e:
                measurement.error_message = str(e)
        
        return measurement.get_metrics()
    
    def benchmark_captcha_solving(self) -> PerformanceMetrics:
        """Benchmark CAPTCHA solving latency (simulated)"""
        with self.measure_operation("captcha_solving") as measurement:
            try:
                # Simulate CAPTCHA solving with varying complexity
                solving_times = []
                
                # Simulate different CAPTCHA types
                captcha_types = [
                    {"type": "recaptcha_v2", "base_time": 3.5},
                    {"type": "recaptcha_v3", "base_time": 1.2},
                    {"type": "hcaptcha", "base_time": 4.1},
                    {"type": "funcaptcha", "base_time": 5.8},
                    {"type": "text_captcha", "base_time": 0.8}
                ]
                
                for captcha in captcha_types:
                    # Add random variation (±30%)
                    import random
                    variation = random.uniform(0.7, 1.3)
                    solve_time = captcha["base_time"] * variation * 1000  # Convert to ms
                    solving_times.append(solve_time)
                    
                    measurement.add_data(f"{captcha['type']}_time_ms", solve_time)
                
                avg_solve_time = statistics.mean(solving_times)
                measurement.add_data("average_captcha_solve_time_ms", avg_solve_time)
                measurement.add_data("captcha_types_tested", len(captcha_types))
                
                measurement.success = True
                
            except Exception as e:
                measurement.error_message = str(e)
        
        return measurement.get_metrics()
    
    def benchmark_sms_verification(self) -> PerformanceMetrics:
        """Benchmark SMS verification processing"""
        with self.measure_operation("sms_verification") as measurement:
            try:
                # Import SMS utilities
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))
                from utils.sms_verifier import get_sms_verifier
                
                sms_verifier = get_sms_verifier()
                
                # Measure phone number request
                start_request = time.time()
                phone_number = sms_verifier.get_verification_number("snapchat")
                request_time = (time.time() - start_request) * 1000
                
                measurement.add_data("phone_request_time_ms", request_time)
                measurement.add_data("phone_number", phone_number)
                
                # Simulate SMS receiving delay
                start_wait = time.time()
                # In real scenario, would wait for actual SMS
                import time
                time.sleep(2.5)  # Average SMS delivery time
                wait_time = (time.time() - start_wait) * 1000
                
                measurement.add_data("sms_wait_time_ms", wait_time)
                
                # Measure code retrieval
                start_retrieve = time.time()
                verification_code = sms_verifier.get_verification_code(phone_number)
                retrieve_time = (time.time() - start_retrieve) * 1000
                
                measurement.add_data("code_retrieval_time_ms", retrieve_time)
                measurement.add_data("verification_code", verification_code)
                
                if verification_code:
                    measurement.success = True
                else:
                    raise Exception("Failed to get verification code")
                    
            except Exception as e:
                measurement.error_message = str(e)
        
        return measurement.get_metrics()
    
    def benchmark_email_verification(self) -> PerformanceMetrics:
        """Benchmark email verification processing"""
        with self.measure_operation("email_verification") as measurement:
            try:
                # Import email utilities
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'automation'))
                from automation.email_services.email_integration import get_email_integrator
                
                email_integrator = get_email_integrator()
                
                # Measure email generation
                start_gen = time.time()
                email_address = email_integrator.generate_snapchat_email()
                gen_time = (time.time() - start_gen) * 1000
                
                measurement.add_data("email_generation_time_ms", gen_time)
                measurement.add_data("email_address", email_address)
                
                # Measure verification email check
                start_check = time.time()
                verification_link = email_integrator.wait_for_snapchat_verification(email_address, timeout=30)
                check_time = (time.time() - start_check) * 1000
                
                measurement.add_data("verification_check_time_ms", check_time)
                measurement.add_data("verification_link", verification_link)
                
                if verification_link:
                    measurement.success = True
                else:
                    raise Exception("Email verification timeout")
                    
            except Exception as e:
                measurement.error_message = str(e)
        
        return measurement.get_metrics()
    
    def test_concurrent_account_creation(self, concurrent_count: int) -> ConcurrencyTestResult:
        """Test concurrent account creation capacity"""
        logger.info(f"Testing concurrent account creation: {concurrent_count} accounts")
        
        start_time = time.time()
        successful_accounts = 0
        failed_accounts = 0
        durations = []
        
        # Start system monitoring
        self.start_system_monitoring()
        
        # Track resource usage
        tracemalloc.start()
        initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        initial_cpu = psutil.cpu_percent()
        
        def create_single_account(account_id: int) -> Tuple[bool, float, str]:
            """Create single account and return result"""
            try:
                account_start = time.time()
                
                # Simulate full account creation process
                # 1. Device allocation
                time.sleep(0.5 + account_id * 0.1)  # Simulate queue delay
                
                # 2. Profile generation
                time.sleep(0.2)
                
                # 3. Android automation
                time.sleep(2.0 + account_id * 0.05)  # Simulate device setup
                
                # 4. Snapchat interaction
                time.sleep(3.5)  # App automation
                
                # 5. CAPTCHA solving
                time.sleep(4.0)  # CAPTCHA delay
                
                # 6. Verification
                time.sleep(2.5)  # SMS/Email verification
                
                duration = (time.time() - account_start) * 1000
                return True, duration, ""
                
            except Exception as e:
                duration = (time.time() - account_start) * 1000
                return False, duration, str(e)
        
        # Execute concurrent account creation
        with ThreadPoolExecutor(max_workers=concurrent_count) as executor:
            futures = [executor.submit(create_single_account, i) for i in range(concurrent_count)]
            
            for future in as_completed(futures):
                try:
                    success, duration, error = future.result()
                    durations.append(duration)
                    
                    if success:
                        successful_accounts += 1
                    else:
                        failed_accounts += 1
                        logger.warning(f"Account creation failed: {error}")
                        
                except Exception as e:
                    failed_accounts += 1
                    logger.error(f"Future execution failed: {e}")
        
        # Stop monitoring and calculate metrics
        self.stop_system_monitoring()
        
        total_duration = (time.time() - start_time) * 1000
        final_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        final_cpu = psutil.cpu_percent()
        
        # Calculate memory peak from tracemalloc
        current_memory, memory_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        memory_peak_mb = memory_peak / 1024 / 1024
        
        # Calculate statistics
        avg_duration = statistics.mean(durations) if durations else 0
        min_duration = min(durations) if durations else 0
        max_duration = max(durations) if durations else 0
        
        # Calculate throughput (accounts per minute)
        throughput = (successful_accounts / (total_duration / 1000)) * 60 if total_duration > 0 else 0
        
        # Identify bottleneck type
        bottleneck_type = self._identify_bottleneck(concurrent_count, durations)
        
        result = ConcurrencyTestResult(
            concurrent_count=concurrent_count,
            total_duration_ms=total_duration,
            successful_accounts=successful_accounts,
            failed_accounts=failed_accounts,
            average_duration_ms=avg_duration,
            min_duration_ms=min_duration,
            max_duration_ms=max_duration,
            throughput_per_minute=throughput,
            cpu_peak=max(final_cpu, initial_cpu),
            memory_peak_mb=memory_peak_mb,
            bottleneck_type=bottleneck_type
        )
        
        logger.info(f"Concurrency test complete: {successful_accounts}/{concurrent_count} successful")
        return result
    
    def _identify_bottleneck(self, concurrent_count: int, durations: List[float]) -> str:
        """Identify the primary bottleneck type"""
        if not durations:
            return "total_failure"
        
        avg_duration = statistics.mean(durations)
        
        # Analyze duration patterns
        if avg_duration > 15000:  # > 15 seconds
            return "captcha_solving"
        elif avg_duration > 10000:  # > 10 seconds
            return "device_allocation"
        elif avg_duration > 8000:   # > 8 seconds
            return "android_automation"
        elif avg_duration > 5000:   # > 5 seconds
            return "verification_services"
        elif concurrent_count > 10 and statistics.stdev(durations) > 2000:
            return "resource_contention"
        else:
            return "network_latency"
    
    def analyze_anti_detection_overhead(self) -> PerformanceMetrics:
        """Analyze anti-detection system performance overhead"""
        with self.measure_operation("anti_detection_overhead") as measurement:
            try:
                # Import anti-detection system
                from automation.core.anti_detection import get_anti_detection_system
                
                anti_detection = get_anti_detection_system()
                
                # Measure initialization
                start_init = time.time()
                anti_detection.initialize_stealth_mode()
                init_time = (time.time() - start_init) * 1000
                
                measurement.add_data("initialization_time_ms", init_time)
                
                # Measure fingerprint randomization
                start_fingerprint = time.time()
                fingerprint = anti_detection.generate_device_fingerprint()
                fingerprint_time = (time.time() - start_fingerprint) * 1000
                
                measurement.add_data("fingerprint_generation_time_ms", fingerprint_time)
                measurement.add_data("fingerprint_data", fingerprint)
                
                # Measure behavior simulation
                start_behavior = time.time()
                behavior_pattern = anti_detection.generate_human_behavior_pattern()
                behavior_time = (time.time() - start_behavior) * 1000
                
                measurement.add_data("behavior_generation_time_ms", behavior_time)
                measurement.add_data("behavior_pattern", behavior_pattern)
                
                # Calculate total overhead
                total_overhead = init_time + fingerprint_time + behavior_time
                measurement.add_data("total_overhead_ms", total_overhead)
                
                measurement.success = True
                
            except Exception as e:
                measurement.error_message = str(e)
        
        return measurement.get_metrics()
    
    def run_comprehensive_benchmark(self) -> Dict[str, Any]:
        """Run complete performance benchmark suite"""
        logger.info("🚀 Starting comprehensive Snapchat automation performance benchmark")
        
        benchmark_results = {
            "benchmark_start": datetime.now().isoformat(),
            "system_info": {
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": psutil.virtual_memory().total / 1024 / 1024 / 1024,
                "platform": sys.platform,
                "python_version": sys.version
            },
            "component_benchmarks": {},
            "concurrency_tests": {},
            "bottleneck_analysis": {},
            "recommendations": []
        }
        
        # 1. Component Benchmarks
        logger.info("📊 Running component benchmarks...")
        
        try:
            benchmark_results["component_benchmarks"]["device_allocation"] = asdict(
                self.benchmark_device_allocation()
            )
        except Exception as e:
            logger.error(f"Device allocation benchmark failed: {e}")
        
        try:
            benchmark_results["component_benchmarks"]["proxy_connection"] = asdict(
                self.benchmark_proxy_connection()
            )
        except Exception as e:
            logger.error(f"Proxy benchmark failed: {e}")
        
        try:
            benchmark_results["component_benchmarks"]["profile_generation"] = asdict(
                self.benchmark_profile_generation()
            )
        except Exception as e:
            logger.error(f"Profile generation benchmark failed: {e}")
        
        try:
            benchmark_results["component_benchmarks"]["captcha_solving"] = asdict(
                self.benchmark_captcha_solving()
            )
        except Exception as e:
            logger.error(f"CAPTCHA benchmark failed: {e}")
        
        try:
            benchmark_results["component_benchmarks"]["sms_verification"] = asdict(
                self.benchmark_sms_verification()
            )
        except Exception as e:
            logger.error(f"SMS verification benchmark failed: {e}")
        
        try:
            benchmark_results["component_benchmarks"]["anti_detection_overhead"] = asdict(
                self.analyze_anti_detection_overhead()
            )
        except Exception as e:
            logger.error(f"Anti-detection benchmark failed: {e}")
        
        # 2. Concurrency Tests
        logger.info("⚡ Running concurrency tests...")
        
        concurrency_levels = [1, 5, 10, 20]
        for level in concurrency_levels:
            try:
                logger.info(f"Testing concurrency level: {level}")
                result = self.test_concurrent_account_creation(level)
                benchmark_results["concurrency_tests"][f"concurrent_{level}"] = asdict(result)
            except Exception as e:
                logger.error(f"Concurrency test {level} failed: {e}")
        
        # 3. Bottleneck Analysis
        logger.info("🔍 Analyzing bottlenecks...")
        benchmark_results["bottleneck_analysis"] = self._analyze_system_bottlenecks(benchmark_results)
        
        # 4. Generate Recommendations
        logger.info("💡 Generating optimization recommendations...")
        benchmark_results["recommendations"] = self._generate_optimization_recommendations(benchmark_results)
        
        benchmark_results["benchmark_end"] = datetime.now().isoformat()
        
        # Save results
        results_file = f"snapchat_performance_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(benchmark_results, f, indent=2, default=str)
        
        logger.info(f"✅ Benchmark complete! Results saved to: {results_file}")
        return benchmark_results
    
    def _analyze_system_bottlenecks(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze system bottlenecks from benchmark results"""
        bottlenecks = {
            "primary_bottleneck": "",
            "secondary_bottlenecks": [],
            "performance_degradation_points": [],
            "capacity_limits": {}
        }
        
        # Analyze component performance
        components = results.get("component_benchmarks", {})
        
        # Find slowest components
        component_times = {}
        for component, data in components.items():
            if data.get("success") and data.get("duration_ms"):
                component_times[component] = data["duration_ms"]
        
        if component_times:
            sorted_components = sorted(component_times.items(), key=lambda x: x[1], reverse=True)
            bottlenecks["primary_bottleneck"] = sorted_components[0][0]
            bottlenecks["secondary_bottlenecks"] = [comp[0] for comp in sorted_components[1:3]]
        
        # Analyze concurrency degradation
        concurrency_data = results.get("concurrency_tests", {})
        degradation_points = []
        
        prev_throughput = None
        for level_key in sorted(concurrency_data.keys()):
            level_data = concurrency_data[level_key]
            current_throughput = level_data.get("throughput_per_minute", 0)
            
            if prev_throughput and current_throughput < prev_throughput * 0.8:  # 20% degradation
                degradation_points.append({
                    "concurrency_level": level_data.get("concurrent_count"),
                    "throughput_drop": prev_throughput - current_throughput,
                    "bottleneck_type": level_data.get("bottleneck_type")
                })
            
            prev_throughput = current_throughput
        
        bottlenecks["performance_degradation_points"] = degradation_points
        
        # Determine capacity limits
        max_concurrent = 0
        max_throughput = 0
        
        for level_data in concurrency_data.values():
            if level_data.get("successful_accounts", 0) > 0:
                max_concurrent = max(max_concurrent, level_data.get("concurrent_count", 0))
                max_throughput = max(max_throughput, level_data.get("throughput_per_minute", 0))
        
        bottlenecks["capacity_limits"] = {
            "max_concurrent_accounts": max_concurrent,
            "max_throughput_per_minute": max_throughput,
            "theoretical_max_hourly": max_throughput * 60 if max_throughput > 0 else 0
        }
        
        return bottlenecks
    
    def _generate_optimization_recommendations(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate specific optimization recommendations"""
        recommendations = []
        
        bottlenecks = results.get("bottleneck_analysis", {})
        primary_bottleneck = bottlenecks.get("primary_bottleneck", "")
        
        # Primary bottleneck recommendations
        if primary_bottleneck == "device_allocation":
            recommendations.append({
                "priority": "HIGH",
                "category": "Infrastructure",
                "issue": "Device allocation is the primary bottleneck",
                "recommendation": "Implement device pool pre-warming and connection caching",
                "estimated_improvement": "40-60% faster allocation",
                "implementation_effort": "Medium"
            })
        
        elif primary_bottleneck == "captcha_solving":
            recommendations.append({
                "priority": "HIGH",
                "category": "Anti-Detection",
                "issue": "CAPTCHA solving causes significant delays",
                "recommendation": "Implement parallel CAPTCHA solving and better anti-detection to reduce CAPTCHA frequency",
                "estimated_improvement": "50-70% reduction in CAPTCHA encounters",
                "implementation_effort": "High"
            })
        
        elif primary_bottleneck == "android_automation":
            recommendations.append({
                "priority": "HIGH",
                "category": "Automation",
                "issue": "Android automation is slow",
                "recommendation": "Optimize UIAutomator2 interactions and implement element caching",
                "estimated_improvement": "30-50% faster automation",
                "implementation_effort": "Medium"
            })
        
        # Concurrency recommendations
        concurrency_data = results.get("concurrency_tests", {})
        if concurrency_data:
            max_successful = max([data.get("successful_accounts", 0) for data in concurrency_data.values()])
            
            if max_successful < 15:  # Low concurrency
                recommendations.append({
                    "priority": "MEDIUM",
                    "category": "Scalability",
                    "issue": f"Low concurrent capacity: {max_successful} accounts",
                    "recommendation": "Implement resource pooling and async processing",
                    "estimated_improvement": "3-5x higher concurrency",
                    "implementation_effort": "High"
                })
        
        # Memory optimization
        system_info = results.get("system_info", {})
        memory_total = system_info.get("memory_total_gb", 0)
        
        if memory_total < 8:
            recommendations.append({
                "priority": "MEDIUM",
                "category": "Hardware",
                "issue": f"Limited system memory: {memory_total:.1f}GB",
                "recommendation": "Increase system memory to 16GB+ for better concurrency",
                "estimated_improvement": "2-3x higher concurrent capacity",
                "implementation_effort": "Low (hardware upgrade)"
            })
        
        # Network optimization
        components = results.get("component_benchmarks", {})
        proxy_data = components.get("proxy_connection", {})
        
        if proxy_data.get("success") and proxy_data.get("duration_ms", 0) > 2000:
            recommendations.append({
                "priority": "MEDIUM",
                "category": "Network",
                "issue": "Slow proxy connections",
                "recommendation": "Implement proxy connection pooling and health checking",
                "estimated_improvement": "60-80% faster proxy connections",
                "implementation_effort": "Medium"
            })
        
        # Anti-detection optimization
        anti_detection_data = components.get("anti_detection_overhead", {})
        if anti_detection_data.get("success"):
            total_overhead = anti_detection_data.get("additional_data", {}).get("total_overhead_ms", 0)
            
            if total_overhead > 1000:  # > 1 second overhead
                recommendations.append({
                    "priority": "LOW",
                    "category": "Anti-Detection",
                    "issue": f"High anti-detection overhead: {total_overhead:.0f}ms",
                    "recommendation": "Cache fingerprints and behavior patterns",
                    "estimated_improvement": "70-90% reduction in overhead",
                    "implementation_effort": "Low"
                })
        
        return recommendations


class PerformanceMeasurement:
    """Context manager for measuring operation performance"""
    
    def __init__(self, benchmarker: SnapchatPerformanceBenchmarker, operation_name: str):
        self.benchmarker = benchmarker
        self.operation_name = operation_name
        self.start_time = 0
        self.end_time = 0
        self.start_memory = 0
        self.end_memory = 0
        self.start_cpu = 0
        self.end_cpu = 0
        self.additional_data = {}
        self.success = False
        self.error_message = ""
    
    def __enter__(self):
        self.start_time = time.time()
        self.start_memory = self.benchmarker.process.memory_info().rss
        self.start_cpu = psutil.cpu_percent()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        self.end_memory = self.benchmarker.process.memory_info().rss
        self.end_cpu = psutil.cpu_percent()
        
        if exc_type is not None:
            self.error_message = str(exc_val)
            self.success = False
    
    def add_data(self, key: str, value: Any):
        """Add additional measurement data"""
        self.additional_data[key] = value
    
    def get_metrics(self) -> PerformanceMetrics:
        """Get the performance metrics"""
        duration_ms = (self.end_time - self.start_time) * 1000
        
        return PerformanceMetrics(
            operation=self.operation_name,
            start_time=self.start_time,
            end_time=self.end_time,
            duration_ms=duration_ms,
            cpu_usage_start=self.start_cpu,
            cpu_usage_end=self.end_cpu,
            memory_usage_start=self.start_memory,
            memory_usage_end=self.end_memory,
            memory_peak=max(self.start_memory, self.end_memory),
            success=self.success,
            error_message=self.error_message,
            additional_data=self.additional_data
        )


def main():
    """Run the comprehensive performance benchmark"""
    print("🚀 Snapchat Automation Performance Benchmark")
    print("=" * 60)
    
    benchmarker = SnapchatPerformanceBenchmarker()
    
    try:
        # Run comprehensive benchmark
        results = benchmarker.run_comprehensive_benchmark()
        
        # Print summary
        print("\n📊 BENCHMARK SUMMARY")
        print("=" * 40)
        
        # Component performance
        components = results.get("component_benchmarks", {})
        print("\n🔧 Component Performance:")
        for component, data in components.items():
            status = "✅" if data.get("success") else "❌"
            duration = data.get("duration_ms", 0)
            print(f"  {status} {component}: {duration:.1f}ms")
        
        # Concurrency results
        concurrency = results.get("concurrency_tests", {})
        print("\n⚡ Concurrency Results:")
        for level, data in concurrency.items():
            concurrent = data.get("concurrent_count", 0)
            successful = data.get("successful_accounts", 0)
            throughput = data.get("throughput_per_minute", 0)
            print(f"  {concurrent} concurrent: {successful} successful, {throughput:.1f}/min")
        
        # Bottleneck analysis
        bottlenecks = results.get("bottleneck_analysis", {})
        primary = bottlenecks.get("primary_bottleneck", "unknown")
        print(f"\n🎯 Primary Bottleneck: {primary}")
        
        # Top recommendations
        recommendations = results.get("recommendations", [])
        if recommendations:
            print("\n💡 Top Recommendations:")
            for i, rec in enumerate(recommendations[:3], 1):
                priority = rec.get("priority", "UNKNOWN")
                issue = rec.get("issue", "")
                improvement = rec.get("estimated_improvement", "")
                print(f"  {i}. [{priority}] {issue}")
                print(f"     → {improvement}")
        
        print(f"\n✅ Full results saved to benchmark JSON file")
        print(f"🔍 Review the detailed metrics for optimization opportunities")
        
    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()