#!/usr/bin/env python3
"""
Comprehensive Performance Report Generator
Compiles all performance test results into a detailed analysis report
"""

import json
import glob
import statistics
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

class PerformanceReportGenerator:
    """Generate comprehensive performance reports from test results"""
    
    def __init__(self):
        self.all_results = {}
        self.performance_metrics = {}
        self.bottlenecks = []
        self.recommendations = []
    
    def load_all_test_results(self) -> Dict[str, Any]:
        """Load all available performance test results"""
        print("Loading all performance test results...")
        
        # Load existing test files
        test_files = [
            'quick_load_test_results.json',
            'proxy_integration_test_results.json',
            'performance_analysis_*.json',
            'advanced_load_test_results_*.json',
            'network_performance_results_*.json'
        ]
        
        loaded_results = {}
        
        for pattern in test_files:
            for file_path in glob.glob(pattern):
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        loaded_results[file_path] = data
                        print(f"  Loaded: {file_path}")
                except Exception as e:
                    print(f"  Failed to load {file_path}: {e}")
        
        return loaded_results
    
    def analyze_api_performance(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze API endpoint performance across all tests"""
        api_analysis = {
            'endpoints_tested': [],
            'average_response_times': {},
            'throughput_metrics': {},
            'reliability_metrics': {},
            'performance_trends': []
        }
        
        # Collect API performance data from various test results
        for file_name, data in results.items():
            # From quick load tests
            if 'test_results' in data and isinstance(data['test_results'], list):
                for test in data['test_results']:
                    if 'endpoint' in test:
                        endpoint = test['endpoint']
                        if endpoint not in api_analysis['endpoints_tested']:
                            api_analysis['endpoints_tested'].append(endpoint)
                        
                        if 'avg_response_time_ms' in test:
                            if endpoint not in api_analysis['average_response_times']:
                                api_analysis['average_response_times'][endpoint] = []
                            api_analysis['average_response_times'][endpoint].append(test['avg_response_time_ms'])
            
            # From advanced load tests
            if 'test_results' in data and 'endpoint_load_tests' in data['test_results']:
                for test in data['test_results']['endpoint_load_tests']:
                    if 'url' in test and 'response_times' in test:
                        url = test['url']
                        if url not in api_analysis['endpoints_tested']:
                            api_analysis['endpoints_tested'].append(url)
                        
                        if url not in api_analysis['average_response_times']:
                            api_analysis['average_response_times'][url] = []
                        api_analysis['average_response_times'][url].append(test['response_times']['mean_ms'])
                        
                        # Throughput data
                        if 'performance_metrics' in test:
                            if url not in api_analysis['throughput_metrics']:
                                api_analysis['throughput_metrics'][url] = []
                            api_analysis['throughput_metrics'][url].append(test['performance_metrics']['requests_per_second'])
            
            # From network performance tests
            if 'test_results' in data and 'url_performance' in data['test_results']:
                for url, perf_data in data['test_results']['url_performance'].items():
                    if url not in api_analysis['endpoints_tested']:
                        api_analysis['endpoints_tested'].append(url)
                    
                    if 'response_times' in perf_data:
                        if url not in api_analysis['average_response_times']:
                            api_analysis['average_response_times'][url] = []
                        api_analysis['average_response_times'][url].append(perf_data['response_times']['mean_ms'])
        
        # Calculate summary statistics
        for endpoint in api_analysis['endpoints_tested']:
            if endpoint in api_analysis['average_response_times']:
                times = api_analysis['average_response_times'][endpoint]
                api_analysis['average_response_times'][endpoint] = {
                    'measurements': len(times),
                    'mean_ms': statistics.mean(times),
                    'min_ms': min(times),
                    'max_ms': max(times),
                    'trend': 'improving' if len(times) > 1 and times[-1] < times[0] else 'stable'
                }
        
        return api_analysis
    
    def analyze_database_performance(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze database performance across all tests"""
        db_analysis = {
            'redis_performance': {
                'connection_tests': [],
                'read_performance': [],
                'write_performance': [],
                'load_test_results': []
            },
            'performance_summary': {},
            'issues_identified': []
        }
        
        # Collect database performance data
        for file_name, data in results.items():
            # From performance analysis
            if 'database_tests' in data:
                for db_test in data['database_tests']:
                    if db_test.get('type') == 'Redis' and db_test.get('accessible'):
                        db_analysis['redis_performance']['read_performance'].append(
                            db_test.get('avg_read_time_ms', 0)
                        )
                        if 'avg_write_time_ms' in db_test:
                            db_analysis['redis_performance']['write_performance'].append(
                                db_test['avg_write_time_ms']
                            )
            
            # From advanced load tests
            if 'test_results' in data and 'database_load_test' in data['test_results']:
                db_load = data['test_results']['database_load_test']
                if db_load.get('status') == 'success':
                    db_analysis['redis_performance']['load_test_results'].append({
                        'write_ops_per_sec': db_load['write_performance']['operations_per_second'],
                        'read_ops_per_sec': db_load['read_performance']['operations_per_second'],
                        'operations_tested': db_load['operations_tested']
                    })
        
        # Calculate summary statistics
        redis_perf = db_analysis['redis_performance']
        
        if redis_perf['read_performance']:
            avg_read_time = statistics.mean(redis_perf['read_performance'])
            db_analysis['performance_summary']['redis_read_avg_ms'] = avg_read_time
            
            if avg_read_time > 10:
                db_analysis['issues_identified'].append(f"Slow Redis read performance: {avg_read_time:.2f}ms average")
        
        if redis_perf['write_performance']:
            avg_write_time = statistics.mean(redis_perf['write_performance'])
            db_analysis['performance_summary']['redis_write_avg_ms'] = avg_write_time
            
            if avg_write_time > 20:
                db_analysis['issues_identified'].append(f"Slow Redis write performance: {avg_write_time:.2f}ms average")
        
        if redis_perf['load_test_results']:
            load_results = redis_perf['load_test_results']
            avg_read_ops = statistics.mean([r['read_ops_per_sec'] for r in load_results])
            avg_write_ops = statistics.mean([r['write_ops_per_sec'] for r in load_results])
            
            db_analysis['performance_summary']['redis_read_ops_per_sec'] = avg_read_ops
            db_analysis['performance_summary']['redis_write_ops_per_sec'] = avg_write_ops
        
        return db_analysis
    
    def analyze_system_resources(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze system resource usage patterns"""
        resource_analysis = {
            'cpu_usage_patterns': [],
            'memory_usage_patterns': [],
            'resource_peaks': {},
            'resource_efficiency': {},
            'scaling_indicators': []
        }
        
        # Collect resource usage data
        for file_name, data in results.items():
            # From current system metrics
            if 'current_system_metrics' in data:
                metrics = data['current_system_metrics']
                
                if 'cpu' in metrics:
                    resource_analysis['cpu_usage_patterns'].append({
                        'file': file_name,
                        'cpu_percent': metrics['cpu']['percent'],
                        'cpu_count': metrics['cpu']['count']
                    })
                
                if 'memory' in metrics:
                    resource_analysis['memory_usage_patterns'].append({
                        'file': file_name,
                        'memory_percent': metrics['memory']['percent'],
                        'memory_used_gb': metrics['memory']['used_gb'],
                        'memory_total_gb': metrics['memory']['total_gb']
                    })
            
            # From system resource monitoring during load tests
            if 'test_results' in data and 'system_resource_monitoring' in data['test_results']:
                monitoring = data['test_results']['system_resource_monitoring']
                
                if 'cpu_usage' in monitoring:
                    cpu = monitoring['cpu_usage']
                    resource_analysis['cpu_usage_patterns'].append({
                        'file': file_name,
                        'cpu_percent': cpu['max_percent'],
                        'cpu_avg_percent': cpu['mean_percent'],
                        'test_type': 'load_test'
                    })
                
                if 'memory_usage' in monitoring:
                    mem = monitoring['memory_usage']
                    resource_analysis['memory_usage_patterns'].append({
                        'file': file_name,
                        'memory_percent': mem['max_percent'],
                        'memory_avg_percent': mem['mean_percent'],
                        'test_type': 'load_test'
                    })
        
        # Calculate resource peaks and efficiency
        if resource_analysis['cpu_usage_patterns']:
            cpu_values = [p['cpu_percent'] for p in resource_analysis['cpu_usage_patterns']]
            resource_analysis['resource_peaks']['max_cpu_percent'] = max(cpu_values)
            resource_analysis['resource_peaks']['avg_cpu_percent'] = statistics.mean(cpu_values)
        
        if resource_analysis['memory_usage_patterns']:
            mem_values = [p['memory_percent'] for p in resource_analysis['memory_usage_patterns']]
            resource_analysis['resource_peaks']['max_memory_percent'] = max(mem_values)
            resource_analysis['resource_peaks']['avg_memory_percent'] = statistics.mean(mem_values)
        
        # Identify scaling indicators
        peaks = resource_analysis['resource_peaks']
        if peaks.get('max_cpu_percent', 0) > 80:
            resource_analysis['scaling_indicators'].append(f"High CPU usage detected: {peaks['max_cpu_percent']:.1f}% peak")
        
        if peaks.get('max_memory_percent', 0) > 85:
            resource_analysis['scaling_indicators'].append(f"High memory usage detected: {peaks['max_memory_percent']:.1f}% peak")
        
        return resource_analysis
    
    def calculate_overall_performance_score(self, api_analysis: Dict, db_analysis: Dict, 
                                          resource_analysis: Dict, network_analysis: Dict) -> Dict[str, Any]:
        """Calculate overall performance score based on all metrics"""
        scoring = {
            'total_score': 0,
            'component_scores': {
                'api_performance': 0,
                'database_performance': 0,
                'system_resources': 0,
                'network_performance': 0
            },
            'grade': 'F',
            'performance_level': 'Poor',
            'critical_issues': [],
            'improvement_areas': []
        }
        
        # API Performance Score (0-25 points)
        api_score = 25
        if api_analysis['average_response_times']:
            avg_times = [metrics['mean_ms'] for metrics in api_analysis['average_response_times'].values() 
                        if isinstance(metrics, dict)]
            if avg_times:
                overall_avg = statistics.mean(avg_times)
                if overall_avg > 1000:
                    api_score -= 20
                    scoring['critical_issues'].append(f"Very slow API responses: {overall_avg:.1f}ms average")
                elif overall_avg > 500:
                    api_score -= 10
                    scoring['improvement_areas'].append(f"Slow API responses: {overall_avg:.1f}ms average")
                elif overall_avg > 200:
                    api_score -= 5
        
        # Database Performance Score (0-25 points)
        db_score = 25
        db_summary = db_analysis.get('performance_summary', {})
        
        if 'redis_read_avg_ms' in db_summary:
            read_time = db_summary['redis_read_avg_ms']
            if read_time > 50:
                db_score -= 15
                scoring['critical_issues'].append(f"Very slow database reads: {read_time:.2f}ms")
            elif read_time > 10:
                db_score -= 5
                scoring['improvement_areas'].append(f"Slow database reads: {read_time:.2f}ms")
        
        if db_analysis.get('issues_identified'):
            db_score -= 5
            scoring['improvement_areas'].extend(db_analysis['issues_identified'])
        
        # System Resources Score (0-25 points)
        resource_score = 25
        peaks = resource_analysis.get('resource_peaks', {})
        
        if peaks.get('max_cpu_percent', 0) > 90:
            resource_score -= 15
            scoring['critical_issues'].append(f"Very high CPU usage: {peaks['max_cpu_percent']:.1f}%")
        elif peaks.get('max_cpu_percent', 0) > 70:
            resource_score -= 8
            scoring['improvement_areas'].append(f"High CPU usage: {peaks['max_cpu_percent']:.1f}%")
        
        if peaks.get('max_memory_percent', 0) > 90:
            resource_score -= 15
            scoring['critical_issues'].append(f"Very high memory usage: {peaks['max_memory_percent']:.1f}%")
        elif peaks.get('max_memory_percent', 0) > 80:
            resource_score -= 8
            scoring['improvement_areas'].append(f"High memory usage: {peaks['max_memory_percent']:.1f}%")
        
        # Network Performance Score (0-25 points)
        network_score = 25
        if network_analysis.get('issues_identified'):
            network_score -= len(network_analysis['issues_identified']) * 5
            scoring['improvement_areas'].extend(network_analysis['issues_identified'])
        
        # Calculate total score
        scoring['component_scores'] = {
            'api_performance': max(0, api_score),
            'database_performance': max(0, db_score),
            'system_resources': max(0, resource_score),
            'network_performance': max(0, network_score)
        }
        
        total_score = sum(scoring['component_scores'].values())
        scoring['total_score'] = total_score
        
        # Assign grade and performance level
        if total_score >= 90:
            scoring['grade'] = 'A'
            scoring['performance_level'] = 'Excellent'
        elif total_score >= 80:
            scoring['grade'] = 'B'
            scoring['performance_level'] = 'Good'
        elif total_score >= 70:
            scoring['grade'] = 'C'
            scoring['performance_level'] = 'Fair'
        elif total_score >= 60:
            scoring['grade'] = 'D'
            scoring['performance_level'] = 'Poor'
        else:
            scoring['grade'] = 'F'
            scoring['performance_level'] = 'Critical'
        
        return scoring
    
    def generate_recommendations(self, api_analysis: Dict, db_analysis: Dict, 
                               resource_analysis: Dict, scoring: Dict) -> List[str]:
        """Generate comprehensive performance recommendations"""
        recommendations = []
        
        # Critical issues first
        if scoring['critical_issues']:
            recommendations.append("IMMEDIATE ACTION REQUIRED:")
            recommendations.extend([f"  - {issue}" for issue in scoring['critical_issues']])
            recommendations.append("")
        
        # API Performance Recommendations
        if scoring['component_scores']['api_performance'] < 20:
            recommendations.extend([
                "API Performance Optimization:",
                "  - Implement response caching for frequently accessed endpoints",
                "  - Optimize database queries and add appropriate indexes",
                "  - Consider implementing connection pooling",
                "  - Review and optimize slow code paths",
                "  - Implement request/response compression"
            ])
        
        # Database Performance Recommendations
        if scoring['component_scores']['database_performance'] < 20:
            recommendations.extend([
                "Database Performance Optimization:",
                "  - Optimize Redis configuration (memory policies, persistence)",
                "  - Implement connection pooling for database connections",
                "  - Add database query monitoring and slow query analysis",
                "  - Consider implementing read replicas for scaling",
                "  - Review data structure design and access patterns"
            ])
        
        # System Resource Recommendations
        if scoring['component_scores']['system_resources'] < 20:
            recommendations.extend([
                "System Resource Optimization:",
                "  - Monitor and optimize memory allocation patterns",
                "  - Implement CPU profiling to identify bottlenecks",
                "  - Consider vertical scaling (more CPU/RAM) if consistently high usage",
                "  - Implement resource monitoring and alerting",
                "  - Review process management and threading strategies"
            ])
        
        # General Recommendations
        if scoring['total_score'] >= 80:
            recommendations.extend([
                "Performance Maintenance:",
                "  - Continue monitoring performance metrics regularly",
                "  - Implement automated performance testing in CI/CD pipeline",
                "  - Set up alerting for performance degradation",
                "  - Document current performance baselines"
            ])
        else:
            recommendations.extend([
                "Performance Improvement Strategy:",
                "  - Establish performance testing as part of development workflow",
                "  - Implement comprehensive monitoring and alerting",
                "  - Create performance budgets for key metrics",
                "  - Plan regular performance optimization sprints",
                "  - Consider architectural changes for better scalability"
            ])
        
        # Scaling Recommendations
        scaling_indicators = resource_analysis.get('scaling_indicators', [])
        if scaling_indicators:
            recommendations.extend([
                "Scaling Considerations:",
                "  - Plan for horizontal scaling if vertical scaling is insufficient",
                "  - Implement load balancing for better resource distribution",
                "  - Consider microservices architecture for better resource isolation",
                "  - Evaluate cloud auto-scaling options"
            ])
        
        return recommendations
    
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        print("Generating Comprehensive Performance Report...")
        
        # Load all test results
        all_results = self.load_all_test_results()
        
        if not all_results:
            return {'error': 'No performance test results found'}
        
        # Analyze different performance aspects
        print("Analyzing API performance...")
        api_analysis = self.analyze_api_performance(all_results)
        
        print("Analyzing database performance...")
        db_analysis = self.analyze_database_performance(all_results)
        
        print("Analyzing system resources...")
        resource_analysis = self.analyze_system_resources(all_results)
        
        print("Analyzing network performance...")
        # Network analysis from loaded results
        network_analysis = {'issues_identified': []}
        for file_name, data in all_results.items():
            if 'analysis' in data and 'performance_issues' in data['analysis']:
                network_analysis['issues_identified'].extend(data['analysis']['performance_issues'])
        
        print("Calculating overall performance score...")
        scoring = self.calculate_overall_performance_score(
            api_analysis, db_analysis, resource_analysis, network_analysis
        )
        
        print("Generating recommendations...")
        recommendations = self.generate_recommendations(
            api_analysis, db_analysis, resource_analysis, scoring
        )
        
        # Compile comprehensive report
        report = {
            'report_metadata': {
                'generated_at': datetime.now().isoformat(),
                'test_files_analyzed': list(all_results.keys()),
                'total_test_files': len(all_results)
            },
            'executive_summary': {
                'overall_score': scoring['total_score'],
                'grade': scoring['grade'],
                'performance_level': scoring['performance_level'],
                'key_findings': {
                    'apis_tested': len(api_analysis['endpoints_tested']),
                    'critical_issues': len(scoring['critical_issues']),
                    'improvement_areas': len(scoring['improvement_areas'])
                }
            },
            'detailed_analysis': {
                'api_performance': api_analysis,
                'database_performance': db_analysis,
                'system_resources': resource_analysis,
                'network_performance': network_analysis
            },
            'performance_scoring': scoring,
            'recommendations': recommendations,
            'test_data_sources': all_results
        }
        
        return report
    
    def print_executive_summary(self, report: Dict[str, Any]):
        """Print executive summary of the performance report"""
        print("\n" + "=" * 100)
        print("COMPREHENSIVE AUTOMATION SYSTEM PERFORMANCE REPORT")
        print("=" * 100)
        
        summary = report['executive_summary']
        scoring = report['performance_scoring']
        
        print(f"\nEXECUTIVE SUMMARY")
        print(f"Report Generated: {report['report_metadata']['generated_at']}")
        print(f"Test Files Analyzed: {report['report_metadata']['total_test_files']}")
        
        print(f"\nOVERALL PERFORMANCE SCORE: {summary['overall_score']}/100 (Grade: {summary['grade']})")
        print(f"Performance Level: {summary['performance_level']}")
        
        print(f"\nCOMPONENT SCORES:")
        for component, score in scoring['component_scores'].items():
            print(f"  • {component.replace('_', ' ').title()}: {score}/25")
        
        print(f"\nKEY FINDINGS:")
        print(f"  • API Endpoints Tested: {summary['key_findings']['apis_tested']}")
        print(f"  • Critical Issues Identified: {summary['key_findings']['critical_issues']}")
        print(f"  • Areas for Improvement: {summary['key_findings']['improvement_areas']}")
        
        # API Performance Summary
        api_data = report['detailed_analysis']['api_performance']
        if api_data['average_response_times']:
            print(f"\nAPI PERFORMANCE HIGHLIGHTS:")
            for endpoint, metrics in api_data['average_response_times'].items():
                if isinstance(metrics, dict):
                    print(f"  • {endpoint}: {metrics['mean_ms']:.1f}ms avg (trend: {metrics['trend']})")
        
        # Database Performance Summary
        db_data = report['detailed_analysis']['database_performance']
        db_summary = db_data.get('performance_summary', {})
        if db_summary:
            print(f"\nDATABASE PERFORMANCE HIGHLIGHTS:")
            if 'redis_read_avg_ms' in db_summary:
                print(f"  • Redis Read Performance: {db_summary['redis_read_avg_ms']:.2f}ms average")
            if 'redis_read_ops_per_sec' in db_summary:
                print(f"  • Redis Throughput: {db_summary['redis_read_ops_per_sec']:.0f} reads/sec, {db_summary['redis_write_ops_per_sec']:.0f} writes/sec")
        
        # System Resources Summary
        resource_data = report['detailed_analysis']['system_resources']
        peaks = resource_data.get('resource_peaks', {})
        if peaks:
            print(f"\nSYSTEM RESOURCE UTILIZATION:")
            print(f"  • Peak CPU Usage: {peaks.get('max_cpu_percent', 0):.1f}% (avg: {peaks.get('avg_cpu_percent', 0):.1f}%)")
            print(f"  • Peak Memory Usage: {peaks.get('max_memory_percent', 0):.1f}% (avg: {peaks.get('avg_memory_percent', 0):.1f}%)")
        
        # Critical Issues
        if scoring['critical_issues']:
            print(f"\nCRITICAL ISSUES REQUIRING IMMEDIATE ATTENTION:")
            for issue in scoring['critical_issues']:
                print(f"  ⚠️  {issue}")
        
        # Top Recommendations
        recommendations = report['recommendations']
        if recommendations:
            print(f"\nTOP RECOMMENDATIONS:")
            rec_count = 0
            for rec in recommendations:
                if rec and not rec.endswith(':') and rec_count < 5:
                    print(f"  {rec_count + 1}. {rec.strip('- ')}")
                    rec_count += 1
        
        print("\n" + "=" * 100)
        
        # Performance comparison against industry benchmarks
        print(f"\nPERFORMANCE BENCHMARKS COMPARISON:")
        print(f"Industry Standards vs Current Performance:")
        
        if api_data['average_response_times']:
            avg_response_times = [metrics['mean_ms'] for metrics in api_data['average_response_times'].values() 
                                if isinstance(metrics, dict)]
            if avg_response_times:
                overall_avg = statistics.mean(avg_response_times)
                benchmark_status = (
                    "Excellent (< 100ms)" if overall_avg < 100 else
                    "Good (< 200ms)" if overall_avg < 200 else
                    "Acceptable (< 500ms)" if overall_avg < 500 else
                    "Needs Improvement (> 500ms)"
                )
                print(f"  • API Response Time: {overall_avg:.1f}ms - {benchmark_status}")
        
        if 'redis_read_avg_ms' in db_summary:
            read_time = db_summary['redis_read_avg_ms']
            db_benchmark = (
                "Excellent (< 1ms)" if read_time < 1 else
                "Good (< 5ms)" if read_time < 5 else
                "Acceptable (< 10ms)" if read_time < 10 else
                "Needs Improvement (> 10ms)"
            )
            print(f"  • Database Read Time: {read_time:.2f}ms - {db_benchmark}")
        
        print("\n" + "=" * 100)

def main():
    """Generate and display comprehensive performance report"""
    generator = PerformanceReportGenerator()
    
    try:
        # Generate comprehensive report
        report = generator.generate_comprehensive_report()
        
        if 'error' in report:
            print(f"Error: {report['error']}")
            return
        
        # Save detailed report
        timestamp = int(time.time())
        report_file = f"comprehensive_performance_report_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Print executive summary
        generator.print_executive_summary(report)
        
        print(f"\nFull detailed report saved to: {report_file}")
        print(f"Report includes {len(report['test_data_sources'])} test result files")
        
    except Exception as e:
        print(f"Failed to generate performance report: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
