#!/usr/bin/env python3
"""
Android Performance Testing Suite
Comprehensive performance testing for Android applications
"""

import time
import json
import statistics
import subprocess
import threading
from datetime import datetime
from pathlib import Path
import psutil
import argparse

class PerformanceTestSuite:
    """Android app performance testing framework"""
    
    def __init__(self, package_name, test_duration=60):
        self.package_name = package_name
        self.test_duration = test_duration
        self.results = {}
        self.monitoring_active = False
        
    def start_performance_monitoring(self):
        """Start system performance monitoring"""
        self.monitoring_active = True
        self.cpu_usage = []
        self.memory_usage = []
        self.battery_data = []
        
        def monitor_system():
            while self.monitoring_active:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                self.cpu_usage.append({
                    'timestamp': time.time(),
                    'cpu_percent': cpu_percent
                })
                
                # Memory usage
                memory = psutil.virtual_memory()
                self.memory_usage.append({
                    'timestamp': time.time(),
                    'memory_percent': memory.percent,
                    'memory_used_mb': memory.used / 1024 / 1024
                })
                
                # Android-specific metrics via ADB
                try:
                    self._collect_android_metrics()
                except Exception as e:
                    print(f"Warning: Could not collect Android metrics: {e}")
                
                time.sleep(1)
        
        self.monitor_thread = threading.Thread(target=monitor_system)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
    def stop_performance_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring_active = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=5)
    
    def _collect_android_metrics(self):
        """Collect Android-specific performance metrics"""
        try:
            # App memory usage
            cmd = ['adb', 'shell', 'dumpsys', 'meminfo', self.package_name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            # Parse memory info (simplified)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'TOTAL' in line and 'PSS' in line:
                        # Extract PSS memory usage
                        parts = line.split()
                        if len(parts) > 1:
                            try:
                                memory_kb = int(parts[1])
                                self.app_memory_usage.append({
                                    'timestamp': time.time(),
                                    'pss_memory_kb': memory_kb
                                })
                                break
                            except (ValueError, IndexError):
                                pass
            
            # CPU usage for app
            cmd = ['adb', 'shell', 'top', '-n', '1', '-p', 
                   subprocess.check_output(['adb', 'shell', 'pidof', self.package_name]).decode().strip()]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            # Battery info
            cmd = ['adb', 'shell', 'dumpsys', 'battery']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                battery_level = self._parse_battery_level(result.stdout)
                if battery_level:
                    self.battery_data.append({
                        'timestamp': time.time(),
                        'battery_level': battery_level
                    })
                    
        except Exception as e:
            # Silently continue if Android metrics fail
            pass
    
    def _parse_battery_level(self, battery_output):
        """Parse battery level from dumpsys output"""
        for line in battery_output.split('\n'):
            if 'level:' in line:
                try:
                    return int(line.split(':')[1].strip())
                except (ValueError, IndexError):
                    pass
        return None
    
    def test_app_launch_time(self, iterations=10):
        """Test app launch time performance"""
        print(f"Testing app launch time ({iterations} iterations)...")
        
        launch_times = []
        
        for i in range(iterations):
            print(f"Launch test {i+1}/{iterations}")
            
            # Force stop app
            subprocess.run(['adb', 'shell', 'am', 'force-stop', self.package_name])
            time.sleep(2)
            
            # Clear app cache
            subprocess.run(['adb', 'shell', 'pm', 'clear', self.package_name])
            time.sleep(1)
            
            # Launch app and measure time
            start_time = time.time()
            
            subprocess.run(['adb', 'shell', 'monkey', '-p', self.package_name, 
                          '-c', 'android.intent.category.LAUNCHER', '1'])
            
            # Wait for app to fully load (simplified check)
            time.sleep(3)
            
            # Check if app is running
            result = subprocess.run(['adb', 'shell', 'pidof', self.package_name], 
                                  capture_output=True)
            
            if result.returncode == 0:
                end_time = time.time()
                launch_time = end_time - start_time
                launch_times.append(launch_time)
                print(f"  Launch time: {launch_time:.2f}s")
            else:
                print(f"  Launch failed")
        
        if launch_times:
            self.results['launch_time'] = {
                'average': statistics.mean(launch_times),
                'median': statistics.median(launch_times),
                'min': min(launch_times),
                'max': max(launch_times),
                'iterations': len(launch_times)
            }
            
            print(f"Launch time results:")
            print(f"  Average: {self.results['launch_time']['average']:.2f}s")
            print(f"  Median: {self.results['launch_time']['median']:.2f}s")
            print(f"  Min: {self.results['launch_time']['min']:.2f}s")
            print(f"  Max: {self.results['launch_time']['max']:.2f}s")
    
    def test_memory_usage(self, duration=30):
        """Test memory usage over time"""
        print(f"Testing memory usage for {duration} seconds...")
        
        self.app_memory_usage = []
        
        # Start monitoring
        self.start_performance_monitoring()
        
        # Run app through basic interactions
        subprocess.run(['adb', 'shell', 'monkey', '-p', self.package_name, 
                       '--pct-touch', '70', '--pct-nav', '30', 
                       '--throttle', '1000', str(duration)])
        
        time.sleep(duration)
        
        # Stop monitoring
        self.stop_performance_monitoring()
        
        if self.app_memory_usage:
            memory_values = [entry['pss_memory_kb'] for entry in self.app_memory_usage]
            
            self.results['memory_usage'] = {
                'average_kb': statistics.mean(memory_values),
                'peak_kb': max(memory_values),
                'samples': len(memory_values)
            }
            
            print(f"Memory usage results:")
            print(f"  Average: {self.results['memory_usage']['average_kb']:.0f} KB")
            print(f"  Peak: {self.results['memory_usage']['peak_kb']:.0f} KB")
    
    def test_ui_responsiveness(self, interactions=100):
        """Test UI responsiveness"""
        print(f"Testing UI responsiveness ({interactions} interactions)...")
        
        response_times = []
        
        for i in range(interactions):
            if i % 10 == 0:
                print(f"  Interaction {i+1}/{interactions}")
            
            start_time = time.time()
            
            # Perform UI interaction
            subprocess.run(['adb', 'shell', 'input', 'tap', '500', '500'])
            
            # Wait for response (simplified)
            time.sleep(0.1)
            
            end_time = time.time()
            response_time = end_time - start_time
            response_times.append(response_time)
            
            # Small delay between interactions
            time.sleep(0.5)
        
        if response_times:
            self.results['ui_responsiveness'] = {
                'average_ms': statistics.mean(response_times) * 1000,
                'median_ms': statistics.median(response_times) * 1000,
                'max_ms': max(response_times) * 1000,
                'interactions': len(response_times)
            }
            
            print(f"UI responsiveness results:")
            print(f"  Average: {self.results['ui_responsiveness']['average_ms']:.1f} ms")
            print(f"  Median: {self.results['ui_responsiveness']['median_ms']:.1f} ms")
            print(f"  Max: {self.results['ui_responsiveness']['max_ms']:.1f} ms")
    
    def test_network_performance(self, url="https://httpbin.org/json"):
        """Test network performance"""
        print("Testing network performance...")
        
        network_times = []
        
        for i in range(10):
            try:
                # Trigger network request in app (simplified - using curl as proxy)
                start_time = time.time()
                
                result = subprocess.run(['adb', 'shell', 'curl', '-s', '-w', 
                                       '%{time_total}', '-o', '/dev/null', url], 
                                      capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    network_time = float(result.stdout.strip())
                    network_times.append(network_time)
                    print(f"  Request {i+1}: {network_time:.3f}s")
                
            except Exception as e:
                print(f"  Request {i+1}: Failed ({e})")
            
            time.sleep(1)
        
        if network_times:
            self.results['network_performance'] = {
                'average_s': statistics.mean(network_times),
                'median_s': statistics.median(network_times),
                'min_s': min(network_times),
                'max_s': max(network_times),
                'requests': len(network_times)
            }
            
            print(f"Network performance results:")
            print(f"  Average: {self.results['network_performance']['average_s']:.3f}s")
            print(f"  Median: {self.results['network_performance']['median_s']:.3f}s")
    
    def test_battery_drain(self, duration=300):
        """Test battery drain during app usage"""
        print(f"Testing battery drain for {duration} seconds...")
        
        # Get initial battery level
        result = subprocess.run(['adb', 'shell', 'dumpsys', 'battery'], 
                              capture_output=True, text=True)
        initial_battery = self._parse_battery_level(result.stdout)
        
        if initial_battery is None:
            print("Could not get initial battery level")
            return
        
        print(f"Initial battery level: {initial_battery}%")
        
        # Start monitoring
        self.battery_data = []
        self.start_performance_monitoring()
        
        # Run app with continuous activity
        subprocess.run(['adb', 'shell', 'monkey', '-p', self.package_name, 
                       '--pct-touch', '60', '--pct-nav', '40', 
                       '--throttle', '2000', str(duration // 2)])
        
        time.sleep(duration)
        
        # Stop monitoring
        self.stop_performance_monitoring()
        
        # Get final battery level
        result = subprocess.run(['adb', 'shell', 'dumpsys', 'battery'], 
                              capture_output=True, text=True)
        final_battery = self._parse_battery_level(result.stdout)
        
        if final_battery is not None:
            battery_drain = initial_battery - final_battery
            drain_rate = battery_drain / (duration / 3600)  # per hour
            
            self.results['battery_drain'] = {
                'initial_level': initial_battery,
                'final_level': final_battery,
                'total_drain': battery_drain,
                'drain_rate_per_hour': drain_rate,
                'test_duration_minutes': duration / 60
            }
            
            print(f"Battery drain results:")
            print(f"  Initial: {initial_battery}%")
            print(f"  Final: {final_battery}%")
            print(f"  Total drain: {battery_drain}%")
            print(f"  Drain rate: {drain_rate:.2f}%/hour")
    
    def run_full_performance_test(self):
        """Run complete performance test suite"""
        print(f"Starting full performance test for {self.package_name}")
        print("=" * 60)
        
        # Ensure app is installed
        result = subprocess.run(['adb', 'shell', 'pm', 'list', 'packages', 
                               self.package_name], capture_output=True, text=True)
        
        if self.package_name not in result.stdout:
            print(f"Error: App {self.package_name} not installed")
            return False
        
        # Run individual tests
        try:
            self.test_app_launch_time(iterations=5)
            print("\n" + "-" * 40 + "\n")
            
            self.test_memory_usage(duration=30)
            print("\n" + "-" * 40 + "\n")
            
            self.test_ui_responsiveness(interactions=50)
            print("\n" + "-" * 40 + "\n")
            
            self.test_network_performance()
            print("\n" + "-" * 40 + "\n")
            
            # Skip battery test in quick mode
            # self.test_battery_drain(duration=60)
            
        except KeyboardInterrupt:
            print("\nTest interrupted by user")
            self.stop_performance_monitoring()
            return False
        except Exception as e:
            print(f"\nTest failed with error: {e}")
            self.stop_performance_monitoring()
            return False
        
        return True
    
    def generate_report(self, output_file="performance_report.json"):
        """Generate performance test report"""
        report = {
            'test_info': {
                'package_name': self.package_name,
                'timestamp': datetime.now().isoformat(),
                'test_duration': self.test_duration
            },
            'results': self.results,
            'system_info': {
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024
            }
        }
        
        # Add system monitoring data if available
        if hasattr(self, 'cpu_usage') and self.cpu_usage:
            cpu_values = [entry['cpu_percent'] for entry in self.cpu_usage]
            report['system_monitoring'] = {
                'cpu_usage': {
                    'average': statistics.mean(cpu_values),
                    'max': max(cpu_values),
                    'samples': len(cpu_values)
                }
            }
        
        if hasattr(self, 'memory_usage') and self.memory_usage:
            memory_values = [entry['memory_percent'] for entry in self.memory_usage]
            report['system_monitoring']['memory_usage'] = {
                'average': statistics.mean(memory_values),
                'max': max(memory_values),
                'samples': len(memory_values)
            }
        
        # Save report
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nPerformance report saved to: {output_file}")
        
        # Print summary
        print("\nPERFORMANCE TEST SUMMARY")
        print("=" * 40)
        
        if 'launch_time' in self.results:
            print(f"App Launch Time: {self.results['launch_time']['average']:.2f}s avg")
        
        if 'memory_usage' in self.results:
            memory_mb = self.results['memory_usage']['average_kb'] / 1024
            print(f"Memory Usage: {memory_mb:.1f} MB avg")
        
        if 'ui_responsiveness' in self.results:
            print(f"UI Response Time: {self.results['ui_responsiveness']['average_ms']:.1f} ms avg")
        
        if 'network_performance' in self.results:
            print(f"Network Requests: {self.results['network_performance']['average_s']:.3f}s avg")
        
        if 'battery_drain' in self.results:
            print(f"Battery Drain: {self.results['battery_drain']['drain_rate_per_hour']:.2f}%/hour")
        
        return output_file

def main():
    parser = argparse.ArgumentParser(description="Android Performance Testing Suite")
    parser.add_argument("package_name", help="Android app package name to test")
    parser.add_argument("--duration", type=int, default=60, 
                       help="Test duration in seconds (default: 60)")
    parser.add_argument("--output", default="performance_report.json",
                       help="Output report file (default: performance_report.json)")
    parser.add_argument("--quick", action="store_true",
                       help="Run quick performance test (reduced iterations)")
    
    args = parser.parse_args()
    
    # Check ADB connection
    result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
    if 'device' not in result.stdout:
        print("Error: No Android device connected")
        print("Please connect a device and enable USB debugging")
        return 1
    
    # Run performance tests
    test_suite = PerformanceTestSuite(args.package_name, args.duration)
    
    if args.quick:
        print("Running quick performance test...")
        test_suite.test_app_launch_time(iterations=3)
        test_suite.test_memory_usage(duration=15)
        test_suite.test_ui_responsiveness(interactions=20)
    else:
        test_suite.run_full_performance_test()
    
    # Generate report
    test_suite.generate_report(args.output)
    
    return 0

if __name__ == "__main__":
    exit(main())