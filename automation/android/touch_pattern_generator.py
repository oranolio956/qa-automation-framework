#!/usr/bin/env python3
"""
Advanced Touch Pattern Generator for Android Automation
Generates human-like touch patterns with anti-detection measures
"""

import random
import time
import math
import logging
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TouchType(Enum):
    """Types of touch interactions"""
    TAP = "tap"
    SWIPE = "swipe"
    LONG_PRESS = "long_press"
    PINCH = "pinch"
    DOUBLE_TAP = "double_tap"
    DRAG = "drag"

@dataclass
class TouchPoint:
    """Individual touch point with timing"""
    x: float
    y: float
    pressure: float = 0.5
    timestamp: float = 0.0
    duration: float = 0.1

@dataclass
class TouchPattern:
    """Complete touch pattern"""
    touch_type: TouchType
    points: List[TouchPoint]
    total_duration: float
    velocity_profile: List[float]
    pressure_profile: List[float]
    human_characteristics: Dict[str, float]

class HumanTouchGenerator:
    """Generates human-like touch patterns with advanced anti-detection"""
    
    def __init__(self, screen_width: int = 1080, screen_height: int = 1920):
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Human touch characteristics
        self.human_profiles = {
            'careful': {
                'speed_variance': 0.3,
                'accuracy_variance': 0.2,
                'pressure_variance': 0.15,
                'hesitation_probability': 0.1,
                'double_tap_delay': 0.3
            },
            'confident': {
                'speed_variance': 0.5,
                'accuracy_variance': 0.1,
                'pressure_variance': 0.25,
                'hesitation_probability': 0.05,
                'double_tap_delay': 0.2
            },
            'elderly': {
                'speed_variance': 0.2,
                'accuracy_variance': 0.4,
                'pressure_variance': 0.1,
                'hesitation_probability': 0.15,
                'double_tap_delay': 0.5
            },
            'young': {
                'speed_variance': 0.7,
                'accuracy_variance': 0.15,
                'pressure_variance': 0.3,
                'hesitation_probability': 0.03,
                'double_tap_delay': 0.15
            }
        }
        
        self.current_profile = self.human_profiles['confident']
        self.finger_tremor_amplitude = random.uniform(0.5, 2.0)  # pixels
        self.dominant_hand = random.choice(['right', 'left'])
        
    def set_human_profile(self, profile_name: str):
        """Set human touch profile"""
        if profile_name in self.human_profiles:
            self.current_profile = self.human_profiles[profile_name]
            logger.info(f"Set touch profile: {profile_name}")
        else:
            logger.warning(f"Unknown profile: {profile_name}")
    
    def generate_tap_pattern(self, x: float, y: float, 
                           accuracy_offset: float = None) -> TouchPattern:
        """Generate human-like tap pattern"""
        
        # Apply accuracy variance (finger not perfectly accurate)
        if accuracy_offset is None:
            accuracy_offset = self.current_profile['accuracy_variance'] * 10
        
        actual_x = x + random.uniform(-accuracy_offset, accuracy_offset)
        actual_y = y + random.uniform(-accuracy_offset, accuracy_offset)
        
        # Ensure tap stays within screen bounds
        actual_x = max(10, min(self.screen_width - 10, actual_x))
        actual_y = max(10, min(self.screen_height - 10, actual_y))
        
        # Add finger tremor
        tremor_x = random.uniform(-self.finger_tremor_amplitude, self.finger_tremor_amplitude)
        tremor_y = random.uniform(-self.finger_tremor_amplitude, self.finger_tremor_amplitude)
        actual_x += tremor_x
        actual_y += tremor_y
        
        # Generate pressure profile (touch down -> pressure -> release)
        base_pressure = random.uniform(0.3, 0.8)
        pressure_variance = self.current_profile['pressure_variance']
        
        # Tap duration varies by profile
        tap_duration = random.uniform(0.08, 0.15)
        if random.random() < self.current_profile['hesitation_probability']:
            tap_duration *= random.uniform(1.5, 3.0)  # Hesitant tap
        
        # Create touch points for the tap
        points = []
        num_points = random.randint(3, 7)  # Realistic number of touch samples
        
        for i in range(num_points):
            t = i / (num_points - 1) if num_points > 1 else 0
            
            # Pressure follows a curve (low -> high -> low)
            if t < 0.3:
                pressure = base_pressure * (t / 0.3)  # Ramp up
            elif t < 0.7:
                pressure = base_pressure * (1 + random.uniform(-pressure_variance, pressure_variance))  # Hold
            else:
                pressure = base_pressure * ((1 - t) / 0.3)  # Ramp down
            
            # Slight position variance during tap (finger micro-movements)
            point_x = actual_x + random.uniform(-0.5, 0.5)
            point_y = actual_y + random.uniform(-0.5, 0.5)
            
            points.append(TouchPoint(
                x=point_x,
                y=point_y,
                pressure=max(0.1, min(1.0, pressure)),
                timestamp=t * tap_duration,
                duration=tap_duration / num_points
            ))
        
        return TouchPattern(
            touch_type=TouchType.TAP,
            points=points,
            total_duration=tap_duration,
            velocity_profile=[0.0] * len(points),  # No movement in tap
            pressure_profile=[p.pressure for p in points],
            human_characteristics={
                'accuracy_variance': accuracy_offset,
                'hesitation_factor': tap_duration / 0.12,  # Normalized hesitation
                'tremor_amplitude': self.finger_tremor_amplitude
            }
        )
    
    def generate_swipe_pattern(self, start_x: float, start_y: float,
                             end_x: float, end_y: float,
                             duration: float = None) -> TouchPattern:
        """Generate human-like swipe pattern"""
        
        # Calculate swipe distance and direction
        distance = math.sqrt((end_x - start_x) ** 2 + (end_y - start_y) ** 2)
        
        # Determine realistic duration based on distance
        if duration is None:
            base_duration = distance / random.uniform(800, 1500)  # pixels per second
            duration = max(0.2, base_duration)
        
        # Add speed variance
        speed_variance = self.current_profile['speed_variance']
        duration *= random.uniform(1 - speed_variance, 1 + speed_variance)
        
        # Generate curved path (humans don't swipe in perfectly straight lines)
        path_points = self._generate_curved_path(start_x, start_y, end_x, end_y, distance)
        
        # Create touch points with realistic timing
        points = []
        velocity_profile = []
        
        for i, (px, py) in enumerate(path_points):
            t = i / (len(path_points) - 1) if len(path_points) > 1 else 0
            
            # Velocity profile: slow start, accelerate, decelerate
            velocity_curve = self._calculate_velocity_curve(t)
            velocity_profile.append(velocity_curve)
            
            # Pressure varies during swipe
            if t < 0.1:
                pressure = 0.4 + (t / 0.1) * 0.3  # Initial pressure build-up
            elif t > 0.9:
                pressure = 0.7 * ((1 - t) / 0.1)  # Release pressure
            else:
                pressure = 0.7 + random.uniform(-0.1, 0.1)  # Maintain pressure
            
            # Add finger tremor
            tremor_x = random.uniform(-self.finger_tremor_amplitude, self.finger_tremor_amplitude) * 0.5
            tremor_y = random.uniform(-self.finger_tremor_amplitude, self.finger_tremor_amplitude) * 0.5
            
            points.append(TouchPoint(
                x=px + tremor_x,
                y=py + tremor_y,
                pressure=max(0.2, min(1.0, pressure)),
                timestamp=t * duration,
                duration=duration / len(path_points)
            ))
        
        return TouchPattern(
            touch_type=TouchType.SWIPE,
            points=points,
            total_duration=duration,
            velocity_profile=velocity_profile,
            pressure_profile=[p.pressure for p in points],
            human_characteristics={
                'distance': distance,
                'curve_deviation': self._calculate_path_curvature(path_points),
                'velocity_smoothness': self._calculate_velocity_smoothness(velocity_profile)
            }
        )
    
    def generate_long_press_pattern(self, x: float, y: float,
                                  duration: float = None) -> TouchPattern:
        """Generate human-like long press pattern"""
        
        if duration is None:
            duration = random.uniform(0.8, 2.0)  # Typical long press duration
        
        # Apply accuracy variance
        accuracy_offset = self.current_profile['accuracy_variance'] * 8
        actual_x = x + random.uniform(-accuracy_offset, accuracy_offset)
        actual_y = y + random.uniform(-accuracy_offset, accuracy_offset)
        
        # Ensure within screen bounds
        actual_x = max(10, min(self.screen_width - 10, actual_x))
        actual_y = max(10, min(self.screen_height - 10, actual_y))
        
        # Generate points with micro-movements (humans can't hold perfectly still)
        points = []
        num_points = max(10, int(duration * 15))  # Sample rate
        
        base_pressure = random.uniform(0.5, 0.8)
        
        for i in range(num_points):
            t = i / (num_points - 1) if num_points > 1 else 0
            
            # Pressure gradually increases then stabilizes
            if t < 0.2:
                pressure = base_pressure * (0.5 + (t / 0.2) * 0.5)
            else:
                pressure = base_pressure * (1 + random.uniform(-0.1, 0.1))
            
            # Micro-movements during long press
            micro_x = random.uniform(-1.5, 1.5)
            micro_y = random.uniform(-1.5, 1.5)
            
            # Add breathing-like slow drift
            breathing_cycle = math.sin(t * 2 * math.pi * 0.3) * 0.8  # 0.3 Hz breathing
            
            points.append(TouchPoint(
                x=actual_x + micro_x + breathing_cycle,
                y=actual_y + micro_y + breathing_cycle * 0.5,
                pressure=max(0.3, min(1.0, pressure)),
                timestamp=t * duration,
                duration=duration / num_points
            ))
        
        return TouchPattern(
            touch_type=TouchType.LONG_PRESS,
            points=points,
            total_duration=duration,
            velocity_profile=[0.0] * len(points),  # Minimal movement
            pressure_profile=[p.pressure for p in points],
            human_characteristics={
                'micro_movement_amplitude': 1.5,
                'pressure_stability': base_pressure,
                'drift_pattern': 'breathing'
            }
        )
    
    def generate_pinch_pattern(self, center_x: float, center_y: float,
                             scale_factor: float = 2.0,
                             duration: float = None) -> TouchPattern:
        """Generate human-like pinch gesture"""
        
        if duration is None:
            duration = random.uniform(0.5, 1.2)
        
        # Two finger positions for pinch
        initial_distance = random.uniform(100, 200)  # Initial finger separation
        final_distance = initial_distance * scale_factor
        
        # Calculate finger positions
        angle = random.uniform(0, 2 * math.pi)  # Random orientation
        
        finger1_start_x = center_x + (initial_distance / 2) * math.cos(angle)
        finger1_start_y = center_y + (initial_distance / 2) * math.sin(angle)
        finger2_start_x = center_x - (initial_distance / 2) * math.cos(angle)
        finger2_start_y = center_y - (initial_distance / 2) * math.sin(angle)
        
        finger1_end_x = center_x + (final_distance / 2) * math.cos(angle)
        finger1_end_y = center_y + (final_distance / 2) * math.sin(angle)
        finger2_end_x = center_x - (final_distance / 2) * math.cos(angle)
        finger2_end_y = center_y - (final_distance / 2) * math.sin(angle)
        
        # Generate paths for both fingers
        finger1_path = self._generate_curved_path(
            finger1_start_x, finger1_start_y, finger1_end_x, finger1_end_y, 
            abs(final_distance - initial_distance)
        )
        finger2_path = self._generate_curved_path(
            finger2_start_x, finger2_start_y, finger2_end_x, finger2_end_y,
            abs(final_distance - initial_distance)
        )
        
        # Combine finger paths into single pattern
        points = []
        num_points = max(len(finger1_path), len(finger2_path))
        
        for i in range(num_points):
            t = i / (num_points - 1) if num_points > 1 else 0
            
            # Interpolate positions if path lengths differ
            f1_idx = min(i, len(finger1_path) - 1)
            f2_idx = min(i, len(finger2_path) - 1)
            
            # Average the two finger positions (simplified for single-point representation)
            avg_x = (finger1_path[f1_idx][0] + finger2_path[f2_idx][0]) / 2
            avg_y = (finger1_path[f1_idx][1] + finger2_path[f2_idx][1]) / 2
            
            # Pressure increases during pinch
            pressure = 0.6 + (t * 0.3)
            
            points.append(TouchPoint(
                x=avg_x,
                y=avg_y,
                pressure=min(1.0, pressure),
                timestamp=t * duration,
                duration=duration / num_points
            ))
        
        return TouchPattern(
            touch_type=TouchType.PINCH,
            points=points,
            total_duration=duration,
            velocity_profile=self._calculate_pinch_velocity_profile(num_points),
            pressure_profile=[p.pressure for p in points],
            human_characteristics={
                'initial_distance': initial_distance,
                'final_distance': final_distance,
                'scale_factor': scale_factor,
                'finger_coordination': 0.9  # How well fingers move together
            }
        )
    
    def _generate_curved_path(self, start_x: float, start_y: float,
                            end_x: float, end_y: float, distance: float) -> List[Tuple[float, float]]:
        """Generate curved path between two points"""
        
        # Number of path points based on distance
        num_points = max(10, int(distance / 20))
        
        # Add curve deviation (humans don't move in straight lines)
        curve_strength = random.uniform(0.05, 0.2) * distance
        curve_direction = random.choice([-1, 1])
        
        # Control point for bezier curve
        mid_x = (start_x + end_x) / 2
        mid_y = (start_y + end_y) / 2
        
        # Perpendicular offset for curve
        dx = end_x - start_x
        dy = end_y - start_y
        length = math.sqrt(dx * dx + dy * dy)
        
        if length > 0:
            perp_x = -dy / length * curve_strength * curve_direction
            perp_y = dx / length * curve_strength * curve_direction
        else:
            perp_x = perp_y = 0
        
        control_x = mid_x + perp_x
        control_y = mid_y + perp_y
        
        # Generate bezier curve points
        path = []
        for i in range(num_points):
            t = i / (num_points - 1) if num_points > 1 else 0
            
            # Quadratic bezier formula
            x = (1 - t) ** 2 * start_x + 2 * (1 - t) * t * control_x + t ** 2 * end_x
            y = (1 - t) ** 2 * start_y + 2 * (1 - t) * t * control_y + t ** 2 * end_y
            
            path.append((x, y))
        
        return path
    
    def _calculate_velocity_curve(self, t: float) -> float:
        """Calculate realistic velocity curve for swipe"""
        # Human swipes: slow start, accelerate, decelerate
        if t < 0.3:
            # Acceleration phase
            return 0.3 + (t / 0.3) * 0.7
        elif t < 0.7:
            # Constant speed phase
            return 1.0 + random.uniform(-0.1, 0.1)
        else:
            # Deceleration phase
            return 1.0 * ((1 - t) / 0.3)
    
    def _calculate_path_curvature(self, path: List[Tuple[float, float]]) -> float:
        """Calculate how curved a path is"""
        if len(path) < 3:
            return 0.0
        
        total_curvature = 0.0
        for i in range(1, len(path) - 1):
            # Calculate angle between consecutive segments
            x1, y1 = path[i - 1]
            x2, y2 = path[i]
            x3, y3 = path[i + 1]
            
            # Vector from point 1 to 2
            v1_x, v1_y = x2 - x1, y2 - y1
            # Vector from point 2 to 3
            v2_x, v2_y = x3 - x2, y3 - y2
            
            # Calculate angle between vectors
            dot_product = v1_x * v2_x + v1_y * v2_y
            mag1 = math.sqrt(v1_x ** 2 + v1_y ** 2)
            mag2 = math.sqrt(v2_x ** 2 + v2_y ** 2)
            
            if mag1 > 0 and mag2 > 0:
                cos_angle = dot_product / (mag1 * mag2)
                cos_angle = max(-1, min(1, cos_angle))  # Clamp to valid range
                angle = math.acos(cos_angle)
                total_curvature += angle
        
        return total_curvature / max(1, len(path) - 2)
    
    def _calculate_velocity_smoothness(self, velocity_profile: List[float]) -> float:
        """Calculate how smooth the velocity profile is"""
        if len(velocity_profile) < 2:
            return 1.0
        
        # Calculate variance in velocity changes
        changes = []
        for i in range(1, len(velocity_profile)):
            changes.append(abs(velocity_profile[i] - velocity_profile[i - 1]))
        
        return 1.0 / (1.0 + np.std(changes)) if changes else 1.0
    
    def _calculate_pinch_velocity_profile(self, num_points: int) -> List[float]:
        """Calculate velocity profile for pinch gesture"""
        profile = []
        for i in range(num_points):
            t = i / (num_points - 1) if num_points > 1 else 0
            # Pinch starts slow, accelerates, then slows down
            if t < 0.4:
                velocity = t / 0.4 * 0.8
            elif t < 0.6:
                velocity = 0.8
            else:
                velocity = 0.8 * (1 - (t - 0.6) / 0.4)
            profile.append(velocity)
        
        return profile

# Global touch generator
_touch_generator = None

def get_touch_generator(screen_width: int = 1080, screen_height: int = 1920) -> HumanTouchGenerator:
    """Get global touch generator instance"""
    global _touch_generator
    if _touch_generator is None:
        _touch_generator = HumanTouchGenerator(screen_width, screen_height)
    return _touch_generator

if __name__ == "__main__":
    # Test touch generator
    generator = HumanTouchGenerator()
    
    print("Testing touch pattern generation...")
    
    # Test tap pattern
    tap = generator.generate_tap_pattern(540, 960)
    print(f"Tap pattern: {len(tap.points)} points, duration: {tap.total_duration:.3f}s")
    
    # Test swipe pattern
    swipe = generator.generate_swipe_pattern(100, 100, 900, 1800)
    print(f"Swipe pattern: {len(swipe.points)} points, duration: {swipe.total_duration:.3f}s")
    
    # Test long press
    long_press = generator.generate_long_press_pattern(540, 960, 1.5)
    print(f"Long press pattern: {len(long_press.points)} points, duration: {long_press.total_duration:.3f}s")
    
    # Test pinch
    pinch = generator.generate_pinch_pattern(540, 960, 2.0)
    print(f"Pinch pattern: {len(pinch.points)} points, duration: {pinch.total_duration:.3f}s")
    
    print("Touch pattern generation test completed successfully!")