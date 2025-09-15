#!/usr/bin/env python3
"""
Quick Performance Analysis for Automation System
Analyzes existing performance data and runs targeted tests
"""

import json
import time
import requests
import psutil
import statistics
import subprocess
from datetime import datetime
from pathlib import Path

def analyze_existing_performance_data():
    """Analyze existing performance test results"""
    results = {
        'existing_data_analysis': {},
        'current_system_metrics': {},
        'bottleneck_analysis': {},
        'recommendations': []
    }
    
    # Load existing test results
    test_files = [
        'quick_load_test_results.json',
        'proxy_integration_test_results.json'
    ]
    
    for test_file in test_files:
        if Path(test_file).exists():
            try:
                with open(test_file, 'r') as f:
                    data = json.load(f)
                    results['existing_data_analysis'][test_file] = data
                    print(f"Loaded data from {test_file}")
            except Exception as e:
                print(f"Error loading {test_file}: {e}")
    
    return results

def get_current_system_metrics():
    """Get current system performance metrics"""
    metrics = {
        'timestamp': datetime.now().isoformat(),
        'cpu': {
            'count': psutil.cpu_count(),
            'percent': psutil.cpu_percent(interval=1),
            'freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
        },
        'memory': {
            'total_gb': psutil.virtual_memory().total / 1024**3,
            'available_gb': psutil.virtual_memory().available / 1024**3,
            'percent': psutil.virtual_memory().percent,
            'used_gb': psutil.virtual_memory().used / 1024**3
        },
        'disk': {
            'usage_percent': psutil.disk_usage('/').percent,
            'free_gb': psutil.disk_usage('/').free / 1024**3,
            'total_gb': psutil.disk_usage('/').total / 1024**3
        },
        'network': psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {},
        'processes': len(psutil.pids()),
        'boot_time': psutil.boot_time()
    }
    
    return metrics

def test_api_endpoints_performance():
    """Test key API endpoints quickly"""
    endpoints = [
        'http://localhost:8000/health',
        'http://localhost:8888/health', # Alternative port
        'http://localhost:5000/health', # Flask default
    ]
    
    results = {'endpoint_tests': []}
    
    for endpoint in endpoints:
        endpoint_result = {
            'url': endpoint,
            'accessible': False,
            'response_time_ms': None,
            'status_code': None,
            'error': None
        }
        
        try:
            start_time = time.time()
            response = requests.get(endpoint, timeout=10)
            response_time = (time.time() - start_time) * 1000
            
            endpoint_result.update({
                'accessible': True,
                'response_time_ms': response_time,
                'status_code': response.status_code,
                'response_size_bytes': len(response.content)
            })
            
            print(f"✓ {endpoint}: {response_time:.1f}ms (HTTP {response.status_code})")
            
        except Exception as e:
            endpoint_result['error'] = str(e)
            print(f"✗ {endpoint}: {e}")
        
        results['endpoint_tests'].append(endpoint_result)
    
    return results

def test_database_connectivity():
    """Test database connections"""
    results = {'database_tests': []}
    
    # Test Redis
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        
        start_time = time.time()
        r.ping()
        ping_time = (time.time() - start_time) * 1000
        
        # Quick performance test
        write_times = []
        for i in range(100):
            start = time.time()
            r.set(f"perf_test_{i}", f"value_{i}")
            write_times.append((time.time() - start) * 1000)
        
        read_times = []
        for i in range(100):
            start = time.time()
            r.get(f"perf_test_{i}")
            read_times.append((time.time() - start) * 1000)
        
        # Cleanup
        for i in range(100):
            r.delete(f"perf_test_{i}")
        
        results['database_tests'].append({
            'type': 'Redis',
            'accessible': True,
            'ping_time_ms': ping_time,
            'avg_write_time_ms': statistics.mean(write_times),
            'avg_read_time_ms': statistics.mean(read_times),
            'p95_write_time_ms': sorted(write_times)[94],  # 95th percentile
            'p95_read_time_ms': sorted(read_times)[94]
        })
        
        print(f"✓ Redis: {ping_time:.2f}ms ping, {statistics.mean(read_times):.2f}ms avg read")
        
    except Exception as e:
        results['database_tests'].append({
            'type': 'Redis',
            'accessible': False,
            'error': str(e)
        })
        print(f"✗ Redis: {e}")
    
    return results

def analyze_running_processes():
    """Analyze currently running processes for automation system"""
    automation_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info']):
        try:
            cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
            name = proc.info['name']
            
            # Look for automation-related processes
            if any(keyword in cmdline.lower() or keyword in name.lower() for keyword in 
                   ['python', 'node', 'uvicorn', 'gunicorn', 'flask', 'bot', 'automation']):
                
                automation_processes.append({
                    'pid': proc.info['pid'],
                    'name': name,
                    'cmdline': cmdline[:200],  # Truncate long command lines
                    'cpu_percent': proc.info['cpu_percent'],
                    'memory_mb': proc.info['memory_info'].rss / 1024 / 1024 if proc.info['memory_info'] else 0
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    return {'running_processes': automation_processes}

def generate_performance_text_graphs(data):
    """Generate simple text-based performance graphs"""
    print("\n" + "=" * 60)
    print("PERFORMANCE METRICS VISUALIZATION")
    print("=" * 60)
    
    # System Resource Usage Bar Chart
    metrics = data.get('current_system_metrics', {})
    
    if 'cpu' in metrics:
        cpu_percent = metrics['cpu']['percent']
        print(f"\nCPU Usage: {cpu_percent:.1f}%")
        print("[" + "#" * int(cpu_percent / 2) + "-" * (50 - int(cpu_percent / 2)) + f"] {cpu_percent:.1f}%")
    
    if 'memory' in metrics:
        mem_percent = metrics['memory']['percent']
        print(f"\nMemory Usage: {mem_percent:.1f}%")
        print("[" + "#" * int(mem_percent / 2) + "-" * (50 - int(mem_percent / 2)) + f"] {mem_percent:.1f}%")
    
    if 'disk' in metrics:
        disk_percent = metrics['disk']['usage_percent']
        print(f"\nDisk Usage: {disk_percent:.1f}%")
        print("[" + "#" * int(disk_percent / 2) + "-" * (50 - int(disk_percent / 2)) + f"] {disk_percent:.1f}%")
    
    # API Response Times
    if 'endpoint_tests' in data:
        print("\nAPI Endpoint Response Times:")
        for test in data['endpoint_tests']:
            if test.get('accessible') and test.get('response_time_ms'):
                rt = test['response_time_ms']
                bars = int(min(rt / 10, 50))  # Scale: 10ms = 1 bar, max 50 bars
                print(f"{test['url']:40} [{'#' * bars:<50}] {rt:.1f}ms")

def identify_performance_bottlenecks(data):
    """Identify performance bottlenecks from collected data"""
    bottlenecks = {
        'critical_issues': [],
        'warnings': [],
        'recommendations': [],
        'performance_score': 0
    }
    
    score = 100  # Start with perfect score
    
    # Analyze system metrics
    metrics = data.get('current_system_metrics', {})
    
    if 'cpu' in metrics:
        cpu_percent = metrics['cpu']['percent']
        if cpu_percent > 90:
            bottlenecks['critical_issues'].append(f"Very high CPU usage: {cpu_percent:.1f}%")
            score -= 20
        elif cpu_percent > 70:
            bottlenecks['warnings'].append(f"High CPU usage: {cpu_percent:.1f}%")
            score -= 10
    
    if 'memory' in metrics:
        mem_percent = metrics['memory']['percent']
        if mem_percent > 90:
            bottlenecks['critical_issues'].append(f"Very high memory usage: {mem_percent:.1f}%")
            score -= 20
        elif mem_percent > 75:
            bottlenecks['warnings'].append(f"High memory usage: {mem_percent:.1f}%")
            score -= 10
    
    # Analyze API performance
    if 'endpoint_tests' in data:
        slow_endpoints = []
        for test in data['endpoint_tests']:
            if test.get('accessible') and test.get('response_time_ms'):
                rt = test['response_time_ms']
                if rt > 1000:  # > 1 second
                    slow_endpoints.append(f"{test['url']}: {rt:.1f}ms")
                    score -= 15
                elif rt > 500:  # > 500ms
                    bottlenecks['warnings'].append(f"Slow API endpoint: {test['url']} ({rt:.1f}ms)")
                    score -= 5
        
        if slow_endpoints:
            bottlenecks['critical_issues'].extend([f"Very slow API endpoint: {ep}" for ep in slow_endpoints])
    
    # Analyze database performance
    if 'database_tests' in data:
        for db_test in data['database_tests']:
            if db_test['type'] == 'Redis' and db_test.get('accessible'):
                if db_test.get('avg_read_time_ms', 0) > 10:
                    bottlenecks['warnings'].append(f"Redis read performance slow: {db_test['avg_read_time_ms']:.2f}ms")
                    score -= 5
    
    # Analyze existing test results
    existing_data = data.get('existing_data_analysis', {})
    
    if 'quick_load_test_results.json' in existing_data:
        load_data = existing_data['quick_load_test_results.json']
        test_results = load_data.get('test_results', [])
        
        for test_result in test_results:
            if test_result.get('success_rate', 100) < 95:
                bottlenecks['critical_issues'].append(
                    f"Low success rate in load test: {test_result.get('success_rate', 0):.1f}%"
                )
                score -= 15
            
            avg_response = test_result.get('avg_response_time_ms', 0)
            if avg_response > 1000:
                bottlenecks['critical_issues'].append(
                    f"High average response time: {avg_response:.1f}ms"
                )
                score -= 10
    
    if 'proxy_integration_test_results.json' in existing_data:
        proxy_data = existing_data['proxy_integration_test_results.json']
        success_rate = proxy_data.get('success_rate', 0)
        
        if success_rate < 50:
            bottlenecks['critical_issues'].append(
                f"Very low proxy integration success rate: {success_rate:.1f}%"
            )
            score -= 25
        elif success_rate < 80:
            bottlenecks['warnings'].append(
                f"Low proxy integration success rate: {success_rate:.1f}%"
            )
            score -= 10
    
    # Generate recommendations
    if bottlenecks['critical_issues']:
        bottlenecks['recommendations'].extend([
            "Investigate and optimize high-impact performance issues immediately",
            "Consider scaling resources (CPU, memory) or optimizing algorithms",
            "Implement performance monitoring and alerting"
        ])
    
    if bottlenecks['warnings']:
        bottlenecks['recommendations'].extend([
            "Monitor resource usage trends over time",
            "Consider performance optimization in next development cycle",
            "Implement caching where appropriate"
        ])
    
    if score > 90:
        bottlenecks['recommendations'].append("System performance is excellent - maintain current optimization")
    elif score > 70:
        bottlenecks['recommendations'].append("System performance is good - minor optimizations recommended")
    else:
        bottlenecks['recommendations'].append("System performance needs significant improvement")
    
    bottlenecks['performance_score'] = max(0, score)
    
    return bottlenecks

def main():
    """Run comprehensive performance analysis"""
    print("Starting Quick Performance Analysis")
    print("=" * 50)
    
    # Collect all performance data
    results = analyze_existing_performance_data()
    
    print("\n1. Collecting current system metrics...")
    results['current_system_metrics'] = get_current_system_metrics()
    
    print("\n2. Testing API endpoint performance...")
    api_results = test_api_endpoints_performance()
    results.update(api_results)
    
    print("\n3. Testing database connectivity...")
    db_results = test_database_connectivity()
    results.update(db_results)
    
    print("\n4. Analyzing running processes...")
    process_results = analyze_running_processes()
    results.update(process_results)
    
    print("\n5. Identifying performance bottlenecks...")
    bottleneck_analysis = identify_performance_bottlenecks(results)
    results['bottleneck_analysis'] = bottleneck_analysis
    
    # Generate visualizations
    generate_performance_text_graphs(results)
    
    # Save comprehensive results
    output_file = f"performance_analysis_{int(time.time())}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Print comprehensive summary
    print_performance_summary(results)
    
    print(f"\nDetailed results saved to: {output_file}")
    
    return results

def print_performance_summary(results):
    """Print comprehensive performance summary"""
    print("\n" + "=" * 80)
    print("COMPREHENSIVE PERFORMANCE ANALYSIS SUMMARY")
    print("=" * 80)
    
    # Performance Score
    bottleneck_analysis = results.get('bottleneck_analysis', {})
    score = bottleneck_analysis.get('performance_score', 0)
    grade = 'A' if score >= 90 else 'B' if score >= 80 else 'C' if score >= 70 else 'D' if score >= 60 else 'F'
    
    print(f"\nOVERALL PERFORMANCE SCORE: {score:.1f}/100 (Grade: {grade})")
    
    # System Resources
    metrics = results.get('current_system_metrics', {})
    print(f"\nSYSTEM RESOURCES:")
    if 'cpu' in metrics:
        print(f"  • CPU: {metrics['cpu']['count']} cores, {metrics['cpu']['percent']:.1f}% usage")
    if 'memory' in metrics:
        print(f"  • Memory: {metrics['memory']['used_gb']:.1f}GB used / {metrics['memory']['total_gb']:.1f}GB total ({metrics['memory']['percent']:.1f}%)")
    if 'disk' in metrics:
        print(f"  • Disk: {metrics['disk']['free_gb']:.1f}GB free / {metrics['disk']['total_gb']:.1f}GB total ({metrics['disk']['usage_percent']:.1f}% used)")
    
    # API Performance
    print(f"\nAPI ENDPOINTS:")
    endpoint_tests = results.get('endpoint_tests', [])
    for test in endpoint_tests:
        if test.get('accessible'):
            print(f"  • {test['url']}: {test['response_time_ms']:.1f}ms (HTTP {test['status_code']})")
        else:
            print(f"  • {test['url']}: OFFLINE ({test.get('error', 'Unknown error')})")
    
    # Database Performance
    print(f"\nDATABASE PERFORMANCE:")
    db_tests = results.get('database_tests', [])
    for test in db_tests:
        if test.get('accessible'):
            print(f"  • {test['type']}: {test.get('ping_time_ms', 0):.2f}ms ping, {test.get('avg_read_time_ms', 0):.2f}ms avg read")
        else:
            print(f"  • {test['type']}: OFFLINE ({test.get('error', 'Unknown error')})")
    
    # Running Processes
    processes = results.get('running_processes', [])
    if processes:
        print(f"\nRUNNING AUTOMATION PROCESSES: ({len(processes)} found)")
        for proc in processes[:5]:  # Show top 5
            print(f"  • PID {proc['pid']}: {proc['name']} - {proc['memory_mb']:.1f}MB RAM, {proc['cpu_percent']:.1f}% CPU")
    
    # Critical Issues
    critical_issues = bottleneck_analysis.get('critical_issues', [])
    if critical_issues:
        print(f"\nCRITICAL ISSUES:")
        for issue in critical_issues:
            print(f"  ⚠️  {issue}")
    
    # Warnings
    warnings = bottleneck_analysis.get('warnings', [])
    if warnings:
        print(f"\nWARNINGS:")
        for warning in warnings:
            print(f"  ⚡ {warning}")
    
    # Recommendations
    recommendations = bottleneck_analysis.get('recommendations', [])
    if recommendations:
        print(f"\nRECOMMENDATIONS:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")
    
    # Existing Test Analysis
    existing_data = results.get('existing_data_analysis', {})
    if existing_data:
        print(f"\nEXISTING TEST RESULTS ANALYSIS:")
        
        if 'quick_load_test_results.json' in existing_data:
            load_data = existing_data['quick_load_test_results.json']
            print(f"  • Load Test: {load_data.get('test_results', [{}])[0].get('success_rate', 0):.1f}% success rate")
        
        if 'proxy_integration_test_results.json' in existing_data:
            proxy_data = existing_data['proxy_integration_test_results.json']
            print(f"  • Proxy Integration: {proxy_data.get('success_rate', 0):.1f}% success rate ({proxy_data.get('passed_tests', 0)}/{proxy_data.get('total_tests', 0)} tests passed)")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
