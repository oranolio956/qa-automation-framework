#!/usr/bin/env python3
"""
Touch Simulation and Gesture Testing for QA Framework
Implements realistic touch patterns with bezier curves and natural variations
"""

import numpy as np
import random
import subprocess
import time
import logging
import json
from typing import Tuple, List, Optional
from dataclasses import dataclass
from pathlib import Path
import sys
import os

# Add utils directory to path for proxy imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../utils'))

try:
    from proxy import verify_proxy
    PROXY_AVAILABLE = True
except ImportError:
    PROXY_AVAILABLE = False

# Try to import bezier, fallback to simple interpolation
try:
    import bezier
    BEZIER_AVAILABLE = True
except ImportError:
    BEZIER_AVAILABLE = False
    print("Warning: bezier library not available, using linear interpolation")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class TouchPoint:
    x: float
    y: float
    pressure: float = 1.0
    duration: int = 50  # milliseconds

@dataclass
class GestureConfig:
    min_duration: int = 100
    max_duration: int = 800
    min_points: int = 10
    max_points: int = 30
    pressure_variation: float = 0.2
    timing_variation: float = 0.3

class TouchSimulator:
    def __init__(self, device_id: Optional[str] = None):
        self.device_id = device_id
        self.config = GestureConfig()
        self.screen_width = 1080
        self.screen_height = 1920
        self._detect_screen_size()
        
    def _detect_screen_size(self):
        """Detect the screen size of the connected device"""
        try:
            cmd = ["adb"]
            if self.device_id:
                cmd.extend(["-s", self.device_id])
            cmd.extend(["shell", "wm", "size"])
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            output = result.stdout.strip()
            
            # Parse output like "Physical size: 1080x1920"
            if ":" in output:
                size_part = output.split(":")[-1].strip()
                if "x" in size_part:
                    width, height = map(int, size_part.split("x"))
                    self.screen_width = width
                    self.screen_height = height
                    logger.info(f"Detected screen size: {width}x{height}")
        except Exception as e:
            logger.warning(f"Could not detect screen size: {e}, using default 1080x1920")
    
    def _execute_adb_command(self, cmd: List[str]) -> bool:
        """Execute an ADB command with error handling"""
        try:
            full_cmd = ["adb"]
            if self.device_id:
                full_cmd.extend(["-s", self.device_id])
            full_cmd.extend(cmd)
            
            subprocess.run(full_cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"ADB command failed: {' '.join(cmd)} - {e}")
            return False
    
    def tap(self, x: int, y: int, duration: int = 100) -> bool:
        """Simulate a tap at the specified coordinates"""
        return self._execute_adb_command([
            "shell", "input", "touchscreen", "tap", str(x), str(y)
        ])
    
    def long_press(self, x: int, y: int, duration: int = 1000) -> bool:
        """Simulate a long press"""
        return self._execute_adb_command([
            "shell", "input", "touchscreen", "swipe", 
            str(x), str(y), str(x), str(y), str(duration)
        ])
    
    def swipe_linear(self, start: Tuple[int, int], end: Tuple[int, int], duration: int = 300) -> bool:
        """Simple linear swipe"""
        return self._execute_adb_command([
            "shell", "input", "touchscreen", "swipe",
            str(start[0]), str(start[1]), str(end[0]), str(end[1]), str(duration)
        ])
    
    def simulate_swipe(self, start: Tuple[int, int], end: Tuple[int, int]) -> bool:
        """
        Simulate a natural swipe with bezier curves or linear interpolation
        """
        if not BEZIER_AVAILABLE:
            return self._simulate_swipe_linear(start, end)
        
        try:
            # Create control points for a natural curve
            control_points = self._generate_control_points(start, end)
            nodes = np.asfortranarray(control_points)
            curve = bezier.Curve(nodes, degree=len(control_points[0]) - 1)
            
            # Generate points along the curve
            num_points = random.randint(self.config.min_points, self.config.max_points)
            t_values = np.linspace(0, 1, num_points)
            points = curve.evaluate_multi(t_values).T
            
            # Execute the swipe
            return self._execute_touch_sequence(points)
            
        except Exception as e:
            logger.warning(f"Bezier swipe failed, falling back to linear: {e}")
            return self._simulate_swipe_linear(start, end)
    
    def _generate_control_points(self, start: Tuple[int, int], end: Tuple[int, int]) -> List[List[float]]:
        """Generate control points for a natural swipe curve"""
        # Add some randomness to make the swipe more natural
        mid_x = (start[0] + end[0]) / 2 + random.randint(-50, 50)
        mid_y = (start[1] + end[1]) / 2 + random.randint(-30, 30)
        
        # Create 3-point bezier curve
        x_points = [float(start[0]), mid_x, float(end[0])]
        y_points = [float(start[1]), mid_y, float(end[1])]
        
        return [x_points, y_points]
    
    def _simulate_swipe_linear(self, start: Tuple[int, int], end: Tuple[int, int]) -> bool:
        """Fallback linear swipe with natural timing"""
        num_points = random.randint(15, 25)
        points = []
        
        for i in range(num_points):
            t = i / (num_points - 1)
            x = start[0] + t * (end[0] - start[0])
            y = start[1] + t * (end[1] - start[1])
            points.append([x, y])
        
        return self._execute_touch_sequence(points)
    
    def _execute_touch_sequence(self, points: List[List[float]]) -> bool:
        """Execute a sequence of touch points"""
        success_count = 0
        
        for i, (x, y) in enumerate(points):
            # Add natural timing variation
            if i > 0:
                delay = random.randint(10, 50)  # 10-50ms between points
                time.sleep(delay / 1000.0)
            
            # Ensure coordinates are within screen bounds
            x = max(0, min(int(x), self.screen_width - 1))
            y = max(0, min(int(y), self.screen_height - 1))
            
            # Execute touch point
            if self._execute_adb_command([
                "shell", "input", "touchscreen", "swipe",
                str(x), str(y), str(x), str(y), "50"
            ]):
                success_count += 1
        
        return success_count > len(points) * 0.8  # 80% success rate threshold
    
    def swipe_up(self, start_y_ratio: float = 0.8) -> bool:
        """Swipe up from bottom of screen"""
        start_x = self.screen_width // 2 + random.randint(-100, 100)
        start_y = int(self.screen_height * start_y_ratio)
        end_x = start_x + random.randint(-50, 50)
        end_y = int(self.screen_height * 0.2)
        
        return self.simulate_swipe((start_x, start_y), (end_x, end_y))
    
    def swipe_down(self, start_y_ratio: float = 0.2) -> bool:
        """Swipe down from top of screen"""
        start_x = self.screen_width // 2 + random.randint(-100, 100)
        start_y = int(self.screen_height * start_y_ratio)
        end_x = start_x + random.randint(-50, 50)
        end_y = int(self.screen_height * 0.8)
        
        return self.simulate_swipe((start_x, start_y), (end_x, end_y))
    
    def swipe_left(self) -> bool:
        """Swipe left across screen"""
        start_x = int(self.screen_width * 0.8)
        start_y = self.screen_height // 2 + random.randint(-200, 200)
        end_x = int(self.screen_width * 0.2)
        end_y = start_y + random.randint(-100, 100)
        
        return self.simulate_swipe((start_x, start_y), (end_x, end_y))
    
    def swipe_right(self) -> bool:
        """Swipe right across screen"""
        start_x = int(self.screen_width * 0.2)
        start_y = self.screen_height // 2 + random.randint(-200, 200)
        end_x = int(self.screen_width * 0.8)
        end_y = start_y + random.randint(-100, 100)
        
        return self.simulate_swipe((start_x, start_y), (end_x, end_y))
    
    def pinch_zoom(self, center: Tuple[int, int], scale: float = 2.0) -> bool:
        """Simulate pinch-to-zoom gesture"""
        # This would require more complex multi-touch simulation
        # For now, implement as two-finger tap simulation
        offset = int(100 * scale)
        
        success = True
        success &= self.tap(center[0] - offset, center[1] - offset, 100)
        time.sleep(0.1)
        success &= self.tap(center[0] + offset, center[1] + offset, 100)
        
        return success
    
    def random_gesture(self) -> bool:
        """Execute a random gesture for testing"""
        gestures = [
            self.swipe_up,
            self.swipe_down,
            self.swipe_left,
            self.swipe_right,
            lambda: self.tap(
                random.randint(100, self.screen_width - 100),
                random.randint(100, self.screen_height - 100)
            )
        ]
        
        gesture = random.choice(gestures)
        return gesture()
    
    def test_gesture_sequence(self, count: int = 10) -> dict:
        """Execute a sequence of test gestures and return results"""
        results = {
            'total': count,
            'successful': 0,
            'failed': 0,
            'gestures': []
        }
        
        for i in range(count):
            gesture_type = random.choice(['swipe_up', 'swipe_down', 'swipe_left', 'swipe_right', 'tap'])
            
            start_time = time.time()
            success = self.random_gesture()
            end_time = time.time()
            
            result = {
                'index': i + 1,
                'type': gesture_type,
                'success': success,
                'duration': end_time - start_time
            }
            
            results['gestures'].append(result)
            
            if success:
                results['successful'] += 1
            else:
                results['failed'] += 1
            
            # Random delay between gestures
            time.sleep(random.uniform(0.5, 2.0))
        
        results['success_rate'] = results['successful'] / results['total']
        return results

def main():
    """Main function for testing touch simulation"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Touch Simulator for QA Testing')
    parser.add_argument('--device', '-d', help='ADB device ID')
    parser.add_argument('--test-count', '-c', type=int, default=10, help='Number of test gestures')
    parser.add_argument('--output', '-o', help='JSON output file for results')
    
    args = parser.parse_args()
    
    # Verify proxy if available
    if PROXY_AVAILABLE:
        try:
            verify_proxy()
            logger.info("✅ Residential proxy verified for session")
        except Exception as e:
            logger.warning(f"⚠ Proxy verification failed: {e}")
    
    # Initialize simulator
    simulator = TouchSimulator(device_id=args.device)
    
    # Run test sequence
    logger.info(f"Starting touch simulation test with {args.test_count} gestures")
    results = simulator.test_gesture_sequence(args.test_count)
    
    # Output results
    logger.info(f"Test completed: {results['successful']}/{results['total']} successful ({results['success_rate']:.1%})")
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {args.output}")
    
    return results['success_rate'] > 0.8  # Success if >80% gestures work

if __name__ == "__main__":
    exit(0 if main() else 1)