#!/usr/bin/env python3
"""
Network Performance Testing for Automation System
Tests network latency, connection pooling, and proxy performance
"""

import time
import requests
import concurrent.futures
import statistics
import json
import subprocess
import socket
from datetime import datetime
from typing import Dict, List, Any

class NetworkPerformanceTester:
    """Network performance testing framework"""
    
    def __init__(self):
        self.results = {}
    
    def test_connection_establishment(self, host: str, port: int, iterations: int = 50) -> Dict[str, Any]:
        """Test TCP connection establishment times"""
        print(f"Testing connection establishment to {host}:{port} ({iterations} iterations)...")
        
        connection_times = []
        successful_connections = 0
        
        for i in range(iterations):
            start_time = time.time()
            
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)
                result = sock.connect_ex((host, port))
                
                if result == 0:
                    connection_time = (time.time() - start_time) * 1000
                    connection_times.append(connection_time)
                    successful_connections += 1
                
                sock.close()
                
            except Exception as e:
                print(f"Connection {i+1} failed: {e}")
        
        if connection_times:
            return {
                'host': host,
                'port': port,
                'successful_connections': successful_connections,
                'total_attempts': iterations,
                'success_rate': (successful_connections / iterations) * 100,
                'connection_times': {
                    'mean_ms': statistics.mean(connection_times),
                    'median_ms': statistics.median(connection_times),
                    'min_ms': min(connection_times),
                    'max_ms': max(connection_times),
                    'p95_ms': statistics.quantiles(connection_times, n=20)[18] if len(connection_times) > 20 else max(connection_times)
                }
            }
        else:
            return {
                'host': host,
                'port': port,
                'error': 'No successful connections',
                'total_attempts': iterations
            }
    
    def test_http_request_performance(self, urls: List[str], iterations: int = 30) -> Dict[str, Any]:
        """Test HTTP request performance to multiple URLs"""
        print(f"Testing HTTP request performance ({iterations} requests per URL)...")
        
        url_results = {}
        
        for url in urls:
            print(f"  Testing {url}...")
            
            response_times = []
            status_codes = {}
            successful_requests = 0
            
            for i in range(iterations):
                start_time = time.time()
                
                try:
                    response = requests.get(url, timeout=10)
                    response_time = (time.time() - start_time) * 1000
                    
                    response_times.append(response_time)
                    status = response.status_code
                    status_codes[status] = status_codes.get(status, 0) + 1
                    
                    if 200 <= status < 400:
                        successful_requests += 1
                        
                except Exception as e:
                    print(f"    Request {i+1} failed: {e}")
            
            if response_times:
                url_results[url] = {
                    'successful_requests': successful_requests,
                    'total_requests': iterations,
                    'success_rate': (successful_requests / iterations) * 100,
                    'response_times': {
                        'mean_ms': statistics.mean(response_times),
                        'median_ms': statistics.median(response_times),
                        'min_ms': min(response_times),
                        'max_ms': max(response_times),
                        'p95_ms': statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max(response_times)
                    },
                    'status_codes': status_codes
                }
            else:
                url_results[url] = {
                    'error': 'No successful requests',
                    'total_requests': iterations
                }
        
        return {'url_performance': url_results}
    
    def test_concurrent_connections(self, url: str, max_connections: int = 20) -> Dict[str, Any]:
        """Test performance with increasing concurrent connections"""
        print(f"Testing concurrent connections to {url} (up to {max_connections} connections)...")
        
        connection_results = []
        
        for num_connections in [1, 5, 10, 15, 20]:
            if num_connections > max_connections:
                break
            
            print(f"  Testing {num_connections} concurrent connections...")
            
            def make_request():
                start_time = time.time()
                try:
                    response = requests.get(url, timeout=15)
                    response_time = (time.time() - start_time) * 1000
                    return {
                        'success': True,
                        'response_time_ms': response_time,
                        'status_code': response.status_code
                    }
                except Exception as e:
                    return {
                        'success': False,
                        'error': str(e),
                        'response_time_ms': (time.time() - start_time) * 1000
                    }
            
            # Execute concurrent requests
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_connections) as executor:
                futures = [executor.submit(make_request) for _ in range(num_connections)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            total_time = time.time() - start_time
            
            # Analyze results
            successful_results = [r for r in results if r['success']]
            failed_results = [r for r in results if not r['success']]
            
            if successful_results:
                response_times = [r['response_time_ms'] for r in successful_results]
                
                connection_results.append({
                    'concurrent_connections': num_connections,
                    'total_time_seconds': total_time,
                    'successful_requests': len(successful_results),
                    'failed_requests': len(failed_results),
                    'success_rate': (len(successful_results) / num_connections) * 100,
                    'requests_per_second': len(successful_results) / total_time,
                    'response_times': {
                        'mean_ms': statistics.mean(response_times),
                        'max_ms': max(response_times),
                        'min_ms': min(response_times)
                    }
                })
            else:
                connection_results.append({
                    'concurrent_connections': num_connections,
                    'error': 'All requests failed',
                    'failed_requests': len(failed_results)
                })
        
        return {'concurrent_connection_test': connection_results}
    
    def test_network_latency_to_services(self) -> Dict[str, Any]:
        """Test network latency to various external services"""
        print("Testing network latency to external services...")
        
        external_services = [
            ('google.com', 80),
            ('github.com', 443),
            ('api.github.com', 443),
            ('httpbin.org', 80),
            ('jsonplaceholder.typicode.com', 80)
        ]
        
        latency_results = []
        
        for host, port in external_services:
            print(f"  Testing latency to {host}:{port}...")
            
            ping_times = []
            
            # Use ping command for ICMP latency
            try:
                result = subprocess.run(
                    ['ping', '-c', '5', host], 
                    capture_output=True, 
                    text=True, 
                    timeout=30
                )
                
                if result.returncode == 0:
                    # Parse ping output for timing
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if 'time=' in line:
                            try:
                                time_part = line.split('time=')[1].split(' ')[0]
                                ping_time = float(time_part)
                                ping_times.append(ping_time)
                            except (IndexError, ValueError):
                                pass
                
            except subprocess.TimeoutExpired:
                print(f"    Ping to {host} timed out")
            except Exception as e:
                print(f"    Ping to {host} failed: {e}")
            
            # Test TCP connection latency
            tcp_result = self.test_connection_establishment(host, port, iterations=5)
            
            service_result = {
                'host': host,
                'port': port,
                'ping_latency': {
                    'samples': len(ping_times),
                    'mean_ms': statistics.mean(ping_times) if ping_times else None,
                    'min_ms': min(ping_times) if ping_times else None,
                    'max_ms': max(ping_times) if ping_times else None
                },
                'tcp_connection': tcp_result
            }
            
            latency_results.append(service_result)
        
        return {'external_service_latency': latency_results}
    
    def test_proxy_performance(self) -> Dict[str, Any]:
        """Test proxy performance if configured"""
        print("Testing proxy performance...")
        
        # Test direct vs proxy requests
        test_url = 'http://httpbin.org/ip'
        
        # Direct request
        direct_times = []
        for i in range(10):
            start_time = time.time()
            try:
                response = requests.get(test_url, timeout=10)
                if response.status_code == 200:
                    direct_times.append((time.time() - start_time) * 1000)
            except Exception as e:
                print(f"Direct request {i+1} failed: {e}")
        
        # Try proxy request (if proxy configured)
        proxy_times = []
        proxy_config = {
            'http': 'http://127.0.0.1:8080',  # Common proxy port
            'https': 'https://127.0.0.1:8080'
        }
        
        for i in range(5):  # Fewer attempts for proxy
            start_time = time.time()
            try:
                response = requests.get(test_url, proxies=proxy_config, timeout=10)
                if response.status_code == 200:
                    proxy_times.append((time.time() - start_time) * 1000)
            except Exception:
                pass  # Proxy might not be configured
        
        result = {
            'test_url': test_url,
            'direct_requests': {
                'successful_requests': len(direct_times),
                'mean_response_time_ms': statistics.mean(direct_times) if direct_times else None,
                'min_response_time_ms': min(direct_times) if direct_times else None,
                'max_response_time_ms': max(direct_times) if direct_times else None
            },
            'proxy_requests': {
                'successful_requests': len(proxy_times),
                'mean_response_time_ms': statistics.mean(proxy_times) if proxy_times else None,
                'min_response_time_ms': min(proxy_times) if proxy_times else None,
                'max_response_time_ms': max(proxy_times) if proxy_times else None
            }
        }
        
        if direct_times and proxy_times:
            result['performance_comparison'] = {
                'proxy_overhead_ms': statistics.mean(proxy_times) - statistics.mean(direct_times),
                'proxy_overhead_percent': ((statistics.mean(proxy_times) / statistics.mean(direct_times)) - 1) * 100
            }
        
        return {'proxy_performance': result}
    
    def run_comprehensive_network_test(self) -> Dict[str, Any]:
        """Run comprehensive network performance test"""
        print("Starting Comprehensive Network Performance Test")
        print("=" * 60)
        
        # Test local services connection establishment
        print("\n1. Testing connection establishment to local services...")
        local_services = [
            ('localhost', 8000),
            ('localhost', 8888),
            ('localhost', 5000),
            ('localhost', 6379)  # Redis
        ]
        
        connection_tests = []
        for host, port in local_services:
            result = self.test_connection_establishment(host, port, iterations=20)
            connection_tests.append(result)
            
            if 'connection_times' in result:
                ct = result['connection_times']
                print(f"  {host}:{port} - {ct['mean_ms']:.2f}ms avg connection time ({result['success_rate']:.1f}% success)")
            else:
                print(f"  {host}:{port} - Failed to establish connections")
        
        self.results['local_connection_tests'] = connection_tests
        
        # Test HTTP request performance
        print("\n2. Testing HTTP request performance...")
        local_urls = [
            'http://localhost:8888/health',
            'http://localhost:5000/health'
        ]
        
        http_results = self.test_http_request_performance(local_urls, iterations=20)
        self.results.update(http_results)
        
        for url, result in http_results['url_performance'].items():
            if 'response_times' in result:
                rt = result['response_times']
                print(f"  {url} - {rt['mean_ms']:.1f}ms avg ({result['success_rate']:.1f}% success)")
        
        # Test concurrent connections
        print("\n3. Testing concurrent connections...")
        if 'http://localhost:8888/health' in [url for url in local_urls]:
            concurrent_results = self.test_concurrent_connections('http://localhost:8888/health', max_connections=15)
            self.results.update(concurrent_results)
            
            for test in concurrent_results['concurrent_connection_test']:
                if 'requests_per_second' in test:
                    print(f"  {test['concurrent_connections']} connections: {test['requests_per_second']:.1f} RPS ({test['success_rate']:.1f}% success)")
        
        # Test external network latency
        print("\n4. Testing external network latency...")
        latency_results = self.test_network_latency_to_services()
        self.results.update(latency_results)
        
        # Test proxy performance
        print("\n5. Testing proxy performance...")
        proxy_results = self.test_proxy_performance()
        self.results.update(proxy_results)
        
        if proxy_results['proxy_performance']['proxy_requests']['successful_requests'] > 0:
            pr = proxy_results['proxy_performance']
            print(f"  Proxy overhead: {pr.get('performance_comparison', {}).get('proxy_overhead_ms', 'N/A')}ms")
        else:
            print("  No proxy configured or proxy unavailable")
        
        return self.results
    
    def analyze_network_performance(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze network performance results"""
        analysis = {
            'network_health_score': 100,
            'performance_issues': [],
            'recommendations': [],
            'summary': {}
        }
        
        score = 100
        
        # Analyze local connection performance
        if 'local_connection_tests' in results:
            successful_connections = 0
            total_tests = len(results['local_connection_tests'])
            slow_connections = []
            
            for test in results['local_connection_tests']:
                if 'connection_times' in test:
                    successful_connections += 1
                    mean_time = test['connection_times']['mean_ms']
                    
                    if mean_time > 100:  # > 100ms for local connection is slow
                        slow_connections.append(f"{test['host']}:{test['port']} ({mean_time:.1f}ms)")
                        score -= 10
            
            analysis['summary']['local_connections'] = {
                'successful_services': successful_connections,
                'total_services_tested': total_tests,
                'success_rate': (successful_connections / total_tests) * 100 if total_tests > 0 else 0
            }
            
            if slow_connections:
                analysis['performance_issues'].append(f"Slow local connections: {', '.join(slow_connections)}")
            
            if successful_connections < total_tests:
                analysis['performance_issues'].append(f"Some local services unreachable: {total_tests - successful_connections}/{total_tests}")
                score -= 20
        
        # Analyze HTTP performance
        if 'url_performance' in results:
            slow_urls = []
            failed_urls = []
            
            for url, result in results['url_performance'].items():
                if 'response_times' in result:
                    mean_time = result['response_times']['mean_ms']
                    success_rate = result['success_rate']
                    
                    if mean_time > 200:
                        slow_urls.append(f"{url} ({mean_time:.1f}ms)")
                        score -= 5
                    
                    if success_rate < 95:
                        failed_urls.append(f"{url} ({success_rate:.1f}% success)")
                        score -= 10
                else:
                    failed_urls.append(url)
                    score -= 15
            
            if slow_urls:
                analysis['performance_issues'].append(f"Slow HTTP responses: {', '.join(slow_urls)}")
            
            if failed_urls:
                analysis['performance_issues'].append(f"Failed HTTP requests: {', '.join(failed_urls)}")
        
        # Analyze external connectivity
        if 'external_service_latency' in results:
            high_latency_services = []
            unreachable_services = []
            
            for service in results['external_service_latency']:
                ping_latency = service['ping_latency']
                if ping_latency['mean_ms'] is not None:
                    if ping_latency['mean_ms'] > 200:
                        high_latency_services.append(f"{service['host']} ({ping_latency['mean_ms']:.1f}ms)")
                        score -= 5
                else:
                    unreachable_services.append(service['host'])
            
            if high_latency_services:
                analysis['performance_issues'].append(f"High external latency: {', '.join(high_latency_services)}")
            
            if len(unreachable_services) > 2:  # More than 2 unreachable is concerning
                analysis['performance_issues'].append(f"Multiple unreachable external services: {len(unreachable_services)}")
                score -= 10
        
        # Generate recommendations
        if analysis['performance_issues']:
            if any('slow' in issue.lower() for issue in analysis['performance_issues']):
                analysis['recommendations'].extend([
                    "Investigate network latency issues and optimize connection handling",
                    "Consider implementing connection pooling and keep-alive connections",
                    "Monitor network performance continuously"
                ])
            
            if any('failed' in issue.lower() or 'unreachable' in issue.lower() for issue in analysis['performance_issues']):
                analysis['recommendations'].extend([
                    "Check service availability and network connectivity",
                    "Implement proper error handling and retry logic",
                    "Set up service health monitoring and alerts"
                ])
        else:
            analysis['recommendations'].append("Network performance is excellent - maintain current configuration")
        
        analysis['network_health_score'] = max(0, score)
        
        return analysis
    
    def print_network_results(self, results: Dict[str, Any], analysis: Dict[str, Any]):
        """Print comprehensive network test results"""
        print("\n" + "=" * 80)
        print("COMPREHENSIVE NETWORK PERFORMANCE RESULTS")
        print("=" * 80)
        
        # Network health score
        score = analysis['network_health_score']
        grade = 'A' if score >= 90 else 'B' if score >= 80 else 'C' if score >= 70 else 'D' if score >= 60 else 'F'
        print(f"\nNETWORK HEALTH SCORE: {score:.1f}/100 (Grade: {grade})")
        
        # Summary
        summary = analysis.get('summary', {})
        if 'local_connections' in summary:
            lc = summary['local_connections']
            print(f"\nLOCAL SERVICE CONNECTIVITY:")
            print(f"  • Services Reachable: {lc['successful_services']}/{lc['total_services_tested']}")
            print(f"  • Success Rate: {lc['success_rate']:.1f}%")
        
        # HTTP Performance Summary
        if 'url_performance' in results:
            print(f"\nHTTP PERFORMANCE SUMMARY:")
            for url, result in results['url_performance'].items():
                if 'response_times' in result:
                    rt = result['response_times']
                    print(f"  • {url}: {rt['mean_ms']:.1f}ms avg (P95: {rt['p95_ms']:.1f}ms)")
                else:
                    print(f"  • {url}: Failed")
        
        # Concurrent Connection Performance
        if 'concurrent_connection_test' in results:
            print(f"\nCONCURRENT CONNECTION PERFORMANCE:")
            for test in results['concurrent_connection_test']:
                if 'requests_per_second' in test:
                    print(f"  • {test['concurrent_connections']} connections: {test['requests_per_second']:.1f} RPS")
        
        # External Connectivity
        if 'external_service_latency' in results:
            print(f"\nEXTERNAL SERVICE LATENCY:")
            for service in results['external_service_latency']:
                ping_latency = service['ping_latency']
                if ping_latency['mean_ms'] is not None:
                    print(f"  • {service['host']}: {ping_latency['mean_ms']:.1f}ms ping")
                else:
                    print(f"  • {service['host']}: Unreachable")
        
        # Performance Issues
        issues = analysis.get('performance_issues', [])
        if issues:
            print(f"\nPERFORMANCE ISSUES DETECTED:")
            for issue in issues:
                print(f"  ⚠️  {issue}")
        
        # Recommendations
        recommendations = analysis.get('recommendations', [])
        if recommendations:
            print(f"\nRECOMMENDATIONS:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
        
        print("\n" + "=" * 80)

def main():
    """Run comprehensive network performance test"""
    tester = NetworkPerformanceTester()
    
    try:
        # Run comprehensive network test
        results = tester.run_comprehensive_network_test()
        
        # Analyze results
        analysis = tester.analyze_network_performance(results)
        
        # Save results
        output_file = f"network_performance_results_{int(time.time())}.json"
        comprehensive_report = {
            'test_results': results,
            'analysis': analysis,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(output_file, 'w') as f:
            json.dump(comprehensive_report, f, indent=2, default=str)
        
        # Print results
        tester.print_network_results(results, analysis)
        
        print(f"\nDetailed results saved to: {output_file}")
        
    except KeyboardInterrupt:
        print("\nNetwork test interrupted by user")
    except Exception as e:
        print(f"\nNetwork test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
