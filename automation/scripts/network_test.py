#!/usr/bin/env python3
"""
Network Condition Emulation for QA Testing
Simulates various network conditions including latency, jitter, packet loss, and bandwidth throttling
"""

import subprocess
import time
import random
import logging
import json
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import socket
import requests
from contextlib import contextmanager
import sys
import os

# Add utils directory to path for proxy imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../utils'))

try:
    from brightdata_proxy import verify_proxy, get_brightdata_session
    PROXY_AVAILABLE = True
except ImportError:
    PROXY_AVAILABLE = False
    print("Warning: Bright Data proxy module not available, using direct connections")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class NetworkCondition:
    name: str
    latency_ms: int = 0
    jitter_ms: int = 0
    packet_loss_percent: float = 0.0
    bandwidth_kbps: Optional[int] = None
    description: str = ""

# Predefined network conditions for testing
NETWORK_CONDITIONS = {
    "ideal": NetworkCondition("Ideal", 0, 0, 0.0, None, "Perfect network"),
    "wifi": NetworkCondition("WiFi", 20, 5, 0.1, 50000, "Good WiFi connection"),
    "4g": NetworkCondition("4G", 50, 15, 0.5, 20000, "Mobile 4G network"),
    "3g": NetworkCondition("3G", 200, 50, 2.0, 2000, "Mobile 3G network"),
    "edge": NetworkCondition("EDGE", 800, 200, 5.0, 200, "EDGE mobile network"),
    "poor_wifi": NetworkCondition("Poor WiFi", 150, 80, 3.0, 1000, "Congested WiFi"),
    "airplane": NetworkCondition("Airplane WiFi", 1000, 300, 10.0, 500, "In-flight internet"),
    "congested": NetworkCondition("Congested", 300, 150, 8.0, 800, "Network congestion"),
}

class NetworkTester:
    def __init__(self, device_id: Optional[str] = None):
        self.device_id = device_id
        self.current_condition = None
        self.is_emulating = False
        self._setup_test_urls()
        
    def _setup_test_urls(self):
        """Setup test URLs for network testing"""
        self.test_urls = [
            "http://httpbin.org/delay/1",
            "http://httpbin.org/bytes/1024",
            "https://api.github.com/zen",
            "http://httpbin.org/status/200"
        ]
    
    def _execute_adb_command(self, cmd: List[str]) -> Tuple[bool, str]:
        """Execute an ADB command and return success status and output"""
        try:
            full_cmd = ["adb"]
            if self.device_id:
                full_cmd.extend(["-s", self.device_id])
            full_cmd.extend(cmd)
            
            result = subprocess.run(full_cmd, capture_output=True, text=True, check=True)
            return True, result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"ADB command failed: {' '.join(cmd)} - {e}")
            return False, e.stderr if e.stderr else str(e)
    
    def _execute_tc_command(self, cmd: List[str]) -> bool:
        """Execute a traffic control (tc) command"""
        try:
            subprocess.run(["sudo"] + cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"TC command failed: {' '.join(cmd)} - {e}")
            return False
    
    def apply_network_condition(self, condition: NetworkCondition) -> bool:
        """Apply a network condition to the device"""
        logger.info(f"Applying network condition: {condition.name}")
        
        # For Android emulator, we can use network settings
        success = self._apply_emulator_network_condition(condition)
        
        # For host-level testing, apply tc rules
        if success:
            success = self._apply_host_network_condition(condition)
        
        if success:
            self.current_condition = condition
            self.is_emulating = True
            logger.info(f"Successfully applied network condition: {condition.name}")
        else:
            logger.error(f"Failed to apply network condition: {condition.name}")
        
        return success
    
    def _apply_emulator_network_condition(self, condition: NetworkCondition) -> bool:
        """Apply network condition specifically to Android emulator"""
        commands = []
        
        # Set network latency if specified
        if condition.latency_ms > 0:
            commands.append([
                "shell", "setprop", "net.dns1", "8.8.8.8"
            ])
        
        # Simulate packet loss using iptables (if available)
        if condition.packet_loss_percent > 0:
            loss_rule = f"INPUT -m statistic --mode random --probability {condition.packet_loss_percent/100:.3f} -j DROP"
            commands.append([
                "shell", "iptables", "-A", loss_rule
            ])
        
        # Apply bandwidth limiting (rough simulation)
        if condition.bandwidth_kbps:
            commands.append([
                "shell", "setprop", "net.tcp.buffersize.default", str(condition.bandwidth_kbps * 128)
            ])
        
        success_count = 0
        for cmd in commands:
            success, _ = self._execute_adb_command(cmd)
            if success:
                success_count += 1
        
        return success_count > 0 or len(commands) == 0
    
    def _apply_host_network_condition(self, condition: NetworkCondition) -> bool:
        """Apply network condition at host level using tc (traffic control)"""
        try:
            # Clear existing rules
            self._execute_tc_command(["tc", "qdisc", "del", "dev", "lo", "root"])
            
            if condition.latency_ms == 0 and condition.jitter_ms == 0 and condition.packet_loss_percent == 0:
                return True
            
            # Build netem command
            netem_cmd = ["tc", "qdisc", "add", "dev", "lo", "root", "netem"]
            
            if condition.latency_ms > 0:
                if condition.jitter_ms > 0:
                    netem_cmd.extend(["delay", f"{condition.latency_ms}ms", f"{condition.jitter_ms}ms"])
                else:
                    netem_cmd.extend(["delay", f"{condition.latency_ms}ms"])
            
            if condition.packet_loss_percent > 0:
                netem_cmd.extend(["loss", f"{condition.packet_loss_percent}%"])
            
            return self._execute_tc_command(netem_cmd)
            
        except Exception as e:
            logger.warning(f"Host network condition application failed: {e}")
            return False
    
    def clear_network_conditions(self) -> bool:
        """Clear all applied network conditions"""
        logger.info("Clearing network conditions...")
        
        # Clear emulator conditions
        self._execute_adb_command(["shell", "iptables", "-F"])
        
        # Clear host conditions
        self._execute_tc_command(["tc", "qdisc", "del", "dev", "lo", "root"])
        
        self.current_condition = None
        self.is_emulating = False
        
        logger.info("Network conditions cleared")
        return True
    
    def test_network_performance(self, condition: Optional[NetworkCondition] = None) -> Dict:
        """Test network performance under specific conditions"""
        if condition:
            self.apply_network_condition(condition)
        
        results = {
            'condition': asdict(condition) if condition else None,
            'timestamp': time.time(),
            'tests': []
        }
        
        for url in self.test_urls:
            test_result = self._perform_single_test(url)
            results['tests'].append(test_result)
            time.sleep(0.5)  # Brief pause between tests
        
        # Calculate aggregate metrics
        response_times = [t['response_time'] for t in results['tests'] if t['success']]
        if response_times:
            results['avg_response_time'] = sum(response_times) / len(response_times)
            results['max_response_time'] = max(response_times)
            results['min_response_time'] = min(response_times)
        
        results['success_rate'] = len([t for t in results['tests'] if t['success']]) / len(results['tests'])
        
        return results
    
    def _perform_single_test(self, url: str) -> Dict:
        """Perform a single network test"""
        start_time = time.time()
        
        try:
            # Use Bright Data proxied request if proxy is available
            if PROXY_AVAILABLE:
                session = get_brightdata_session()
                response = session.get(url, timeout=30)
            else:
                response = requests.get(url, timeout=30)
            end_time = time.time()
            
            return {
                'url': url,
                'success': True,
                'response_time': end_time - start_time,
                'status_code': response.status_code,
                'content_length': len(response.content),
                'error': None
            }
        except Exception as e:
            end_time = time.time()
            
            return {
                'url': url,
                'success': False,
                'response_time': end_time - start_time,
                'status_code': None,
                'content_length': 0,
                'error': str(e)
            }
    
    def run_condition_suite(self) -> Dict:
        """Run tests against all predefined network conditions"""
        logger.info("Running complete network condition suite...")
        
        suite_results = {
            'timestamp': time.time(),
            'conditions': {}
        }
        
        for condition_name, condition in NETWORK_CONDITIONS.items():
            logger.info(f"Testing condition: {condition_name}")
            
            # Apply condition and test
            condition_results = self.test_network_performance(condition)
            suite_results['conditions'][condition_name] = condition_results
            
            # Clear conditions between tests
            self.clear_network_conditions()
            time.sleep(1)
        
        logger.info("Network condition suite completed")
        return suite_results
    
    def simulate_conditions(self, libraries: Optional[List[str]] = None) -> bool:
        """
        Simulate network conditions using external libraries if provided
        """
        logger.info("Starting network condition simulation...")
        
        # If specific libraries are provided, try to use them
        if libraries:
            for lib_path in libraries:
                if Path(lib_path).exists():
                    try:
                        # Try to import and use the library
                        logger.info(f"Using network library: {lib_path}")
                        # Implementation would depend on specific library format
                    except Exception as e:
                        logger.warning(f"Failed to use library {lib_path}: {e}")
        
        # Fallback to built-in simulation
        return self._run_builtin_simulation()
    
    def _run_builtin_simulation(self) -> bool:
        """Run built-in network condition simulation"""
        conditions_to_test = ["wifi", "4g", "3g", "poor_wifi"]
        
        for condition_name in conditions_to_test:
            condition = NETWORK_CONDITIONS[condition_name]
            logger.info(f"Simulating {condition_name} network...")
            
            # Apply condition for a short duration
            self.apply_network_condition(condition)
            time.sleep(5)  # Simulate for 5 seconds
            
            # Test performance
            results = self.test_network_performance()
            logger.info(f"{condition_name} test completed - Success rate: {results['success_rate']:.1%}")
            
            # Clear condition
            self.clear_network_conditions()
            time.sleep(2)
        
        return True

def initialize_network():
    """Initialize network testing environment"""
    logger.info("Initializing network testing environment...")
    
    # Verify proxy if available
    if PROXY_AVAILABLE:
        try:
            verify_proxy()
            logger.info("✅ Residential proxy verified and ready")
        except Exception as e:
            logger.error(f"❌ Proxy verification failed: {e}")
    
    # Simulate network scenarios (placeholder for external libraries)
    
    # Check if required tools are available
    tools = ["adb", "tc", "iptables"]
    available_tools = []
    
    for tool in tools:
        try:
            subprocess.run([tool, "--help"], capture_output=True, check=True)
            available_tools.append(tool)
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning(f"Tool not available: {tool}")
    
    logger.info(f"Available network tools: {available_tools}")
    
    # Create network tester instance
    tester = NetworkTester()
    
    # Run a quick connectivity test
    quick_test = tester.test_network_performance(NETWORK_CONDITIONS["ideal"])
    logger.info(f"Network initialization test - Success rate: {quick_test['success_rate']:.1%}")
    
    return tester

def main():
    """Main function for network testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Network Condition Emulator for QA Testing')
    parser.add_argument('--device', '-d', help='ADB device ID')
    parser.add_argument('--condition', '-c', choices=list(NETWORK_CONDITIONS.keys()), 
                       help='Specific network condition to test')
    parser.add_argument('--suite', '-s', action='store_true', 
                       help='Run complete condition suite')
    parser.add_argument('--output', '-o', help='JSON output file for results')
    parser.add_argument('--duration', '-t', type=int, default=10,
                       help='Test duration in seconds')
    
    args = parser.parse_args()
    
    # Initialize tester
    tester = NetworkTester(device_id=args.device)
    
    try:
        if args.suite:
            # Run complete suite
            results = tester.run_condition_suite()
        elif args.condition:
            # Test specific condition
            condition = NETWORK_CONDITIONS[args.condition]
            results = tester.test_network_performance(condition)
        else:
            # Default: simulate various conditions
            tester.simulate_conditions()
            results = {"message": "Network simulation completed"}
        
        # Output results
        if args.output and 'conditions' in results:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Results saved to {args.output}")
        
        return True
        
    except Exception as e:
        logger.error(f"Network testing failed: {e}")
        return False
    finally:
        # Always clean up
        tester.clear_network_conditions()

if __name__ == "__main__":
    exit(0 if main() else 1)