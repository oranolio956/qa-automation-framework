#!/usr/bin/env python3
"""
Network Latency Analyzer for Snapchat Automation Infrastructure
Measures real network performance to fly.io Android farm and external services
"""

import asyncio
import time
import socket
import subprocess
import statistics
import json
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import concurrent.futures
import requests
import ping3

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class NetworkLatencyResult:
    """Network latency measurement result"""
    target: str
    protocol: str
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    std_deviation: float
    packet_loss_percent: float
    success_rate: float
    total_tests: int
    failed_tests: int

@dataclass
class AndroidFarmConnectivityTest:
    """Android farm connectivity test result"""
    farm_host: str
    port: int
    tcp_connect_ms: float
    adb_connect_ms: float
    uiautomator_init_ms: float
    device_info_retrieval_ms: float
    total_setup_ms: float
    connection_stable: bool
    error_message: str = ""

class NetworkLatencyAnalyzer:
    """Comprehensive network latency analysis for automation infrastructure"""
    
    def __init__(self):
        self.farm_host = "android-device-farm-prod.fly.dev"
        self.farm_ports = [5555, 5556, 5557, 5558, 5559]
        
        # External services to test
        self.external_services = {
            "snapchat_api": "https://accounts.snapchat.com",
            "google_recaptcha": "https://www.google.com/recaptcha",
            "sms_service": "https://api.sms-activate.org",
            "email_service": "https://api.mailgun.net",
            "proxy_service": "https://brightdata.com",
            "cloudflare": "https://cloudflare.com",
            "google_dns": "8.8.8.8"
        }
        
        self.results = {}
    
    def ping_test(self, target: str, count: int = 20) -> NetworkLatencyResult:
        """Perform ICMP ping test to target"""
        logger.info(f"Ping testing {target} ({count} packets)")
        
        latencies = []
        failed_pings = 0
        
        for i in range(count):
            try:
                # Use ping3 for cross-platform compatibility
                latency = ping3.ping(target, timeout=5)
                
                if latency is not None:
                    latencies.append(latency * 1000)  # Convert to milliseconds
                else:
                    failed_pings += 1
            except Exception as e:
                logger.debug(f"Ping failed: {e}")
                failed_pings += 1
        
        if latencies:
            avg_latency = statistics.mean(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            std_dev = statistics.stdev(latencies) if len(latencies) > 1 else 0
            packet_loss = (failed_pings / count) * 100
            success_rate = ((count - failed_pings) / count) * 100
        else:
            avg_latency = min_latency = max_latency = std_dev = 0
            packet_loss = 100
            success_rate = 0
        
        return NetworkLatencyResult(
            target=target,
            protocol="ICMP",
            avg_latency_ms=avg_latency,
            min_latency_ms=min_latency,
            max_latency_ms=max_latency,
            std_deviation=std_dev,
            packet_loss_percent=packet_loss,
            success_rate=success_rate,
            total_tests=count,
            failed_tests=failed_pings
        )
    
    def tcp_connect_test(self, host: str, port: int, count: int = 10) -> NetworkLatencyResult:
        """Test TCP connection latency to host:port"""
        logger.info(f"TCP testing {host}:{port} ({count} connections)")
        
        latencies = []
        failed_connections = 0
        
        for i in range(count):
            start_time = time.time()
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)
                result = sock.connect_ex((host, port))
                end_time = time.time()
                sock.close()
                
                if result == 0:  # Successful connection
                    latency_ms = (end_time - start_time) * 1000
                    latencies.append(latency_ms)
                else:
                    failed_connections += 1
                    
            except Exception as e:
                logger.debug(f"TCP connection failed: {e}")
                failed_connections += 1
        
        if latencies:
            avg_latency = statistics.mean(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            std_dev = statistics.stdev(latencies) if len(latencies) > 1 else 0
            success_rate = ((count - failed_connections) / count) * 100
        else:
            avg_latency = min_latency = max_latency = std_dev = 0
            success_rate = 0
        
        return NetworkLatencyResult(
            target=f"{host}:{port}",
            protocol="TCP",
            avg_latency_ms=avg_latency,
            min_latency_ms=min_latency,
            max_latency_ms=max_latency,
            std_deviation=std_dev,
            packet_loss_percent=0,  # N/A for TCP
            success_rate=success_rate,
            total_tests=count,
            failed_tests=failed_connections
        )
    
    def http_latency_test(self, url: str, count: int = 15) -> NetworkLatencyResult:
        """Test HTTP request latency"""
        logger.info(f"HTTP testing {url} ({count} requests)")
        
        latencies = []
        failed_requests = 0
        
        session = requests.Session()
        
        for i in range(count):
            start_time = time.time()
            try:
                response = session.get(url, timeout=15)
                end_time = time.time()
                
                if response.status_code < 400:
                    latency_ms = (end_time - start_time) * 1000
                    latencies.append(latency_ms)
                else:
                    failed_requests += 1
                    
            except Exception as e:
                logger.debug(f"HTTP request failed: {e}")
                failed_requests += 1
        
        if latencies:
            avg_latency = statistics.mean(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            std_dev = statistics.stdev(latencies) if len(latencies) > 1 else 0
            success_rate = ((count - failed_requests) / count) * 100
        else:
            avg_latency = min_latency = max_latency = std_dev = 0
            success_rate = 0
        
        return NetworkLatencyResult(
            target=url,
            protocol="HTTP",
            avg_latency_ms=avg_latency,
            min_latency_ms=min_latency,
            max_latency_ms=max_latency,
            std_deviation=std_dev,
            packet_loss_percent=0,  # N/A for HTTP
            success_rate=success_rate,
            total_tests=count,
            failed_tests=failed_requests
        )
    
    def test_android_farm_connectivity(self, port: int) -> AndroidFarmConnectivityTest:
        """Test complete Android farm connectivity"""
        logger.info(f"Testing Android farm connectivity: {self.farm_host}:{port}")
        
        result = AndroidFarmConnectivityTest(
            farm_host=self.farm_host,
            port=port,
            tcp_connect_ms=0,
            adb_connect_ms=0,
            uiautomator_init_ms=0,
            device_info_retrieval_ms=0,
            total_setup_ms=0,
            connection_stable=False
        )
        
        total_start = time.time()
        
        try:
            # 1. Test TCP connection
            tcp_start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(15)
            tcp_result = sock.connect_ex((self.farm_host, port))
            tcp_end = time.time()
            sock.close()
            
            result.tcp_connect_ms = (tcp_end - tcp_start) * 1000
            
            if tcp_result != 0:
                result.error_message = f"TCP connection failed: {tcp_result}"
                return result
            
            # 2. Test ADB connection
            adb_start = time.time()
            device_id = f"{self.farm_host}:{port}"
            
            adb_process = subprocess.run(
                ['adb', 'connect', device_id],
                capture_output=True,
                text=True,
                timeout=30
            )
            adb_end = time.time()
            
            result.adb_connect_ms = (adb_end - adb_start) * 1000
            
            if adb_process.returncode != 0:
                result.error_message = f"ADB connection failed: {adb_process.stderr}"
                return result
            
            # 3. Test UIAutomator2 initialization
            u2_start = time.time()
            try:
                import uiautomator2 as u2
                u2_device = u2.connect(device_id)
                u2_end = time.time()
                
                result.uiautomator_init_ms = (u2_end - u2_start) * 1000
                
                # 4. Test device info retrieval
                info_start = time.time()
                device_info = u2_device.info
                info_end = time.time()
                
                result.device_info_retrieval_ms = (info_end - info_start) * 1000
                
                if device_info:
                    result.connection_stable = True
                else:
                    result.error_message = "Device info retrieval failed"
                
            except ImportError:
                result.error_message = "UIAutomator2 not available"
            except Exception as e:
                result.error_message = f"UIAutomator2 failed: {e}"
            
            # Clean up ADB connection
            subprocess.run(['adb', 'disconnect', device_id], capture_output=True, timeout=10)
            
        except Exception as e:
            result.error_message = f"Connection test failed: {e}"
        
        total_end = time.time()
        result.total_setup_ms = (total_end - total_start) * 1000
        
        return result
    
    def test_concurrent_farm_connections(self, max_concurrent: int = 5) -> List[AndroidFarmConnectivityTest]:
        """Test concurrent connections to Android farm"""
        logger.info(f"Testing concurrent farm connections: {max_concurrent} concurrent")
        
        def test_single_port(port):
            return self.test_android_farm_connectivity(port)
        
        results = []
        
        # Test multiple ports concurrently
        test_ports = self.farm_ports[:max_concurrent]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            futures = [executor.submit(test_single_port, port) for port in test_ports]
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Concurrent test failed: {e}")
        
        return results
    
    def analyze_network_path(self, target: str) -> Dict[str, Any]:
        """Analyze network path to target using traceroute"""
        logger.info(f"Analyzing network path to {target}")
        
        try:
            # Run traceroute (or tracert on Windows)
            import platform
            if platform.system().lower() == "windows":
                cmd = ['tracert', '-h', '15', target]
            else:
                cmd = ['traceroute', '-m', '15', target]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                hops = []
                lines = result.stdout.split('\n')
                
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('traceroute') and not line.startswith('Tracing'):
                        hops.append(line)
                
                return {
                    "target": target,
                    "hops": hops,
                    "hop_count": len(hops),
                    "success": True
                }
            else:
                return {
                    "target": target,
                    "error": result.stderr,
                    "success": False
                }
                
        except Exception as e:
            return {
                "target": target,
                "error": str(e),
                "success": False
            }
    
    def run_comprehensive_network_analysis(self) -> Dict[str, Any]:
        """Run comprehensive network latency analysis"""
        logger.info("🌐 Starting comprehensive network latency analysis")
        
        analysis_results = {
            "analysis_start": datetime.now().isoformat(),
            "ping_tests": {},
            "tcp_tests": {},
            "http_tests": {},
            "android_farm_tests": {},
            "concurrent_farm_tests": [],
            "network_paths": {},
            "performance_summary": {},
            "optimization_recommendations": []
        }
        
        # 1. Ping tests to external services
        logger.info("📡 Running ping tests...")
        for service, target in self.external_services.items():
            try:
                # Extract hostname from URL if needed
                if target.startswith('http'):
                    from urllib.parse import urlparse
                    hostname = urlparse(target).hostname
                else:
                    hostname = target
                
                ping_result = self.ping_test(hostname, count=15)
                analysis_results["ping_tests"][service] = ping_result.__dict__
                
            except Exception as e:
                logger.error(f"Ping test failed for {service}: {e}")
        
        # 2. TCP connection tests to Android farm
        logger.info("🔌 Running TCP connection tests...")
        for port in self.farm_ports:
            try:
                tcp_result = self.tcp_connect_test(self.farm_host, port, count=8)
                analysis_results["tcp_tests"][f"farm_port_{port}"] = tcp_result.__dict__
                
            except Exception as e:
                logger.error(f"TCP test failed for port {port}: {e}")
        
        # 3. HTTP latency tests
        logger.info("🌍 Running HTTP latency tests...")
        for service, url in self.external_services.items():
            if url.startswith('http'):
                try:
                    http_result = self.http_latency_test(url, count=10)
                    analysis_results["http_tests"][service] = http_result.__dict__
                    
                except Exception as e:
                    logger.error(f"HTTP test failed for {service}: {e}")
        
        # 4. Android farm connectivity tests
        logger.info("📱 Running Android farm connectivity tests...")
        for port in self.farm_ports[:3]:  # Test first 3 ports
            try:
                farm_result = self.test_android_farm_connectivity(port)
                analysis_results["android_farm_tests"][f"port_{port}"] = farm_result.__dict__
                
            except Exception as e:
                logger.error(f"Farm connectivity test failed for port {port}: {e}")
        
        # 5. Concurrent farm connection test
        logger.info("⚡ Running concurrent farm connection test...")
        try:
            concurrent_results = self.test_concurrent_farm_connections(max_concurrent=3)
            analysis_results["concurrent_farm_tests"] = [result.__dict__ for result in concurrent_results]
            
        except Exception as e:
            logger.error(f"Concurrent farm test failed: {e}")
        
        # 6. Network path analysis
        logger.info("🗺️ Analyzing network paths...")
        key_targets = [self.farm_host, "snapchat.com", "google.com"]
        for target in key_targets:
            try:
                path_analysis = self.analyze_network_path(target)
                analysis_results["network_paths"][target] = path_analysis
                
            except Exception as e:
                logger.error(f"Network path analysis failed for {target}: {e}")
        
        # 7. Generate performance summary
        logger.info("📊 Generating performance summary...")
        analysis_results["performance_summary"] = self._generate_performance_summary(analysis_results)
        
        # 8. Generate optimization recommendations
        logger.info("💡 Generating optimization recommendations...")
        analysis_results["optimization_recommendations"] = self._generate_network_recommendations(analysis_results)
        
        analysis_results["analysis_end"] = datetime.now().isoformat()
        
        # Save results
        results_file = f"network_latency_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(analysis_results, f, indent=2, default=str)
        
        logger.info(f"✅ Network analysis complete! Results saved to: {results_file}")
        return analysis_results
    
    def _generate_performance_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate performance summary from analysis results"""
        summary = {
            "overall_status": "UNKNOWN",
            "critical_issues": [],
            "performance_metrics": {},
            "bottleneck_identification": {}
        }
        
        # Analyze ping performance
        ping_tests = results.get("ping_tests", {})
        if ping_tests:
            avg_ping_latencies = [test["avg_latency_ms"] for test in ping_tests.values() if test["success_rate"] > 50]
            if avg_ping_latencies:
                summary["performance_metrics"]["average_ping_latency_ms"] = statistics.mean(avg_ping_latencies)
                summary["performance_metrics"]["max_ping_latency_ms"] = max(avg_ping_latencies)
        
        # Analyze farm connectivity
        farm_tests = results.get("android_farm_tests", {})
        successful_farm_connections = [test for test in farm_tests.values() if test["connection_stable"]]
        
        summary["performance_metrics"]["farm_connectivity_success_rate"] = (
            len(successful_farm_connections) / len(farm_tests) * 100 if farm_tests else 0
        )
        
        if successful_farm_connections:
            farm_setup_times = [test["total_setup_ms"] for test in successful_farm_connections]
            summary["performance_metrics"]["average_farm_setup_ms"] = statistics.mean(farm_setup_times)
            summary["performance_metrics"]["max_farm_setup_ms"] = max(farm_setup_times)
        
        # Overall status determination
        farm_success_rate = summary["performance_metrics"].get("farm_connectivity_success_rate", 0)
        avg_ping = summary["performance_metrics"].get("average_ping_latency_ms", 1000)
        
        if farm_success_rate >= 80 and avg_ping < 100:
            summary["overall_status"] = "EXCELLENT"
        elif farm_success_rate >= 60 and avg_ping < 200:
            summary["overall_status"] = "GOOD"
        elif farm_success_rate >= 40 and avg_ping < 500:
            summary["overall_status"] = "FAIR"
        else:
            summary["overall_status"] = "POOR"
        
        # Identify critical issues
        if farm_success_rate < 50:
            summary["critical_issues"].append("Low Android farm connectivity success rate")
        
        if avg_ping > 300:
            summary["critical_issues"].append("High network latency to external services")
        
        # Bottleneck identification
        if successful_farm_connections:
            setup_times = {
                "tcp_connect": statistics.mean([test["tcp_connect_ms"] for test in successful_farm_connections]),
                "adb_connect": statistics.mean([test["adb_connect_ms"] for test in successful_farm_connections]),
                "uiautomator_init": statistics.mean([test["uiautomator_init_ms"] for test in successful_farm_connections]),
                "device_info": statistics.mean([test["device_info_retrieval_ms"] for test in successful_farm_connections])
            }
            
            # Find the slowest component
            slowest_component = max(setup_times.items(), key=lambda x: x[1])
            summary["bottleneck_identification"]["primary_bottleneck"] = slowest_component[0]
            summary["bottleneck_identification"]["bottleneck_time_ms"] = slowest_component[1]
            summary["bottleneck_identification"]["setup_breakdown"] = setup_times
        
        return summary
    
    def _generate_network_recommendations(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate network optimization recommendations"""
        recommendations = []
        
        summary = results.get("performance_summary", {})
        farm_success_rate = summary.get("performance_metrics", {}).get("farm_connectivity_success_rate", 0)
        avg_ping = summary.get("performance_metrics", {}).get("average_ping_latency_ms", 0)
        
        # Farm connectivity recommendations
        if farm_success_rate < 70:
            recommendations.append({
                "priority": "HIGH",
                "category": "Infrastructure",
                "issue": f"Low Android farm connectivity: {farm_success_rate:.1f}%",
                "recommendation": "Investigate fly.io deployment status and implement connection retry logic",
                "estimated_improvement": "Increase success rate to 90%+",
                "implementation": "Deploy redundant farm instances and add circuit breakers"
            })
        
        # Latency recommendations
        if avg_ping > 200:
            recommendations.append({
                "priority": "MEDIUM",
                "category": "Network",
                "issue": f"High network latency: {avg_ping:.1f}ms",
                "recommendation": "Consider CDN or edge deployment closer to target regions",
                "estimated_improvement": "50-70% latency reduction",
                "implementation": "Deploy to multiple fly.io regions"
            })
        
        # Bottleneck-specific recommendations
        bottleneck = summary.get("bottleneck_identification", {})
        primary_bottleneck = bottleneck.get("primary_bottleneck", "")
        
        if primary_bottleneck == "adb_connect":
            recommendations.append({
                "priority": "MEDIUM",
                "category": "ADB",
                "issue": "ADB connection is the slowest component",
                "recommendation": "Implement ADB connection pooling and persistent connections",
                "estimated_improvement": "60-80% faster ADB setup",
                "implementation": "Maintain warm ADB connections to farm devices"
            })
        elif primary_bottleneck == "uiautomator_init":
            recommendations.append({
                "priority": "MEDIUM",
                "category": "UIAutomator",
                "issue": "UIAutomator2 initialization is slow",
                "recommendation": "Pre-initialize UIAutomator2 sessions and cache device connections",
                "estimated_improvement": "70-90% faster automation startup",
                "implementation": "Background UIAutomator2 session warming"
            })
        
        # Concurrent connection recommendations
        concurrent_tests = results.get("concurrent_farm_tests", [])
        successful_concurrent = sum(1 for test in concurrent_tests if test.get("connection_stable", False))
        
        if successful_concurrent < len(concurrent_tests) * 0.8:
            recommendations.append({
                "priority": "MEDIUM",
                "category": "Concurrency",
                "issue": "Poor concurrent connection performance",
                "recommendation": "Implement connection rate limiting and queue management",
                "estimated_improvement": "More stable concurrent operations",
                "implementation": "Add connection pooling with backoff strategies"
            })
        
        return recommendations


def main():
    """Run the comprehensive network latency analysis"""
    print("🌐 Network Latency Analysis for Snapchat Automation")
    print("=" * 60)
    
    analyzer = NetworkLatencyAnalyzer()
    
    try:
        # Run comprehensive analysis
        results = analyzer.run_comprehensive_network_analysis()
        
        # Print summary
        print("\n📊 NETWORK ANALYSIS SUMMARY")
        print("=" * 40)
        
        summary = results.get("performance_summary", {})
        overall_status = summary.get("overall_status", "UNKNOWN")
        print(f"\n🎯 Overall Status: {overall_status}")
        
        metrics = summary.get("performance_metrics", {})
        if metrics:
            print("\n📈 Key Metrics:")
            
            avg_ping = metrics.get("average_ping_latency_ms", 0)
            if avg_ping > 0:
                print(f"  • Average Ping Latency: {avg_ping:.1f}ms")
            
            farm_success = metrics.get("farm_connectivity_success_rate", 0)
            print(f"  • Farm Connectivity Success: {farm_success:.1f}%")
            
            farm_setup = metrics.get("average_farm_setup_ms", 0)
            if farm_setup > 0:
                print(f"  • Average Farm Setup Time: {farm_setup:.1f}ms")
        
        critical_issues = summary.get("critical_issues", [])
        if critical_issues:
            print("\n❌ Critical Issues:")
            for issue in critical_issues:
                print(f"  • {issue}")
        
        bottleneck = summary.get("bottleneck_identification", {})
        primary_bottleneck = bottleneck.get("primary_bottleneck", "")
        if primary_bottleneck:
            bottleneck_time = bottleneck.get("bottleneck_time_ms", 0)
            print(f"\n🎯 Primary Bottleneck: {primary_bottleneck} ({bottleneck_time:.1f}ms)")
        
        recommendations = results.get("optimization_recommendations", [])
        if recommendations:
            print("\n💡 Top Recommendations:")
            for i, rec in enumerate(recommendations[:3], 1):
                priority = rec.get("priority", "UNKNOWN")
                issue = rec.get("issue", "")
                improvement = rec.get("estimated_improvement", "")
                print(f"  {i}. [{priority}] {issue}")
                print(f"     → {improvement}")
        
        print(f"\n✅ Full results saved to network analysis JSON file")
        
    except Exception as e:
        print(f"❌ Network analysis failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()