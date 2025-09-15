#!/usr/bin/env python3
"""
Anti-Detection Technique Validation Tests
Validates the effectiveness and reliability of stealth measures
"""

import pytest
import numpy as np
import statistics
import time
import random
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
from scipy import stats
from unittest.mock import patch, MagicMock

# Import anti-detection components
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../automation'))

from core.anti_detection import (
    get_anti_detection_system, 
    BehaviorPattern, 
    TouchPatternGenerator,
    DeviceFingerprint
)


@dataclass
class DetectionValidationResult:
    """Result of anti-detection validation test"""
    test_name: str
    passed: bool
    confidence_score: float  # 0.0 to 1.0
    human_likeness_score: float  # 0.0 to 1.0
    detection_risk: str  # "LOW", "MEDIUM", "HIGH"
    details: Dict
    recommendations: List[str]


class TestDeviceFingerprintConsistency:
    """Validate device fingerprint consistency and realism"""
    
    def test_fingerprint_deterministic_generation(self):
        """Test that same device ID generates consistent fingerprints"""
        anti_detection = get_anti_detection_system(aggressiveness=0.3)
        device_id = "test_device_123"
        
        # Generate multiple fingerprints for same device
        fingerprints = []
        for _ in range(10):
            fp = anti_detection.create_device_fingerprint(device_id)
            fingerprints.append(fp)
        
        # Verify consistency of core fields
        assert all(fp.device_id == device_id for fp in fingerprints), \
            "Device ID should be consistent"
        
        assert all(fp.model == fingerprints[0].model for fp in fingerprints), \
            "Device model should be consistent"
        
        assert all(fp.android_version == fingerprints[0].android_version for fp in fingerprints), \
            "Android version should be consistent"
        
        assert all(fp.brand == fingerprints[0].brand for fp in fingerprints), \
            "Device brand should be consistent"
        
        assert all(fp.display_resolution == fingerprints[0].display_resolution for fp in fingerprints), \
            "Display resolution should be consistent"
    
    def test_fingerprint_uniqueness_across_devices(self):
        """Test that different devices generate unique fingerprints"""
        anti_detection = get_anti_detection_system(aggressiveness=0.3)
        
        fingerprints = []
        device_ids = [f"device_{i}" for i in range(50)]
        
        for device_id in device_ids:
            fp = anti_detection.create_device_fingerprint(device_id)
            fingerprints.append(fp)
        
        # Check uniqueness of key identifying fields
        models = [fp.model for fp in fingerprints]
        android_versions = [fp.android_version for fp in fingerprints]
        build_ids = [fp.build_id for fp in fingerprints]
        
        # Should have reasonable diversity
        unique_models = len(set(models))
        unique_versions = len(set(android_versions))
        unique_builds = len(set(build_ids))
        
        assert unique_models >= 10, f"Only {unique_models} unique models in 50 devices"
        assert unique_versions >= 5, f"Only {unique_versions} unique Android versions"
        assert unique_builds >= 40, f"Only {unique_builds} unique build IDs"
    
    def test_fingerprint_hardware_correlation(self):
        """Test that hardware characteristics are realistically correlated"""
        anti_detection = get_anti_detection_system(aggressiveness=0.3)
        
        fingerprints = []
        for i in range(100):
            fp = anti_detection.create_device_fingerprint(f"correlation_test_{i}")
            fingerprints.append(fp)
        
        # Test brand-model correlation
        brand_model_pairs = [(fp.brand, fp.model) for fp in fingerprints]
        
        # Check for realistic brand-model combinations
        samsung_models = [model for brand, model in brand_model_pairs if brand == "Samsung"]
        google_models = [model for brand, model in brand_model_pairs if brand == "Google"]
        
        if samsung_models:
            # Samsung models should contain "Galaxy" or "SM-"
            samsung_valid = any("Galaxy" in model or "SM-" in model for model in samsung_models)
            assert samsung_valid, "Samsung models should follow realistic naming"
        
        if google_models:
            # Google models should contain "Pixel"
            google_valid = any("Pixel" in model for model in google_models)
            assert google_valid, "Google models should follow realistic naming"
    
    def test_fingerprint_entropy_analysis(self):
        """Test fingerprint entropy to avoid detection patterns"""
        anti_detection = get_anti_detection_system(aggressiveness=0.3)
        
        # Generate many fingerprints
        fingerprints = []
        for i in range(200):
            fp = anti_detection.create_device_fingerprint(f"entropy_test_{i}")
            fingerprints.append(fp)
        
        # Calculate entropy for various fields
        def calculate_entropy(values: List[str]) -> float:
            """Calculate Shannon entropy"""
            from collections import Counter
            counts = Counter(values)
            total = len(values)
            entropy = -sum((count/total) * np.log2(count/total) for count in counts.values())
            return entropy
        
        # Test entropy of different fields
        model_entropy = calculate_entropy([fp.model for fp in fingerprints])
        version_entropy = calculate_entropy([fp.android_version for fp in fingerprints])
        timezone_entropy = calculate_entropy([fp.timezone for fp in fingerprints])
        language_entropy = calculate_entropy([fp.language for fp in fingerprints])
        
        # Entropy should be reasonable (not too low = predictable, not too high = suspicious)
        assert model_entropy >= 3.0, f"Model entropy {model_entropy:.2f} too low (predictable)"
        assert version_entropy >= 1.5, f"Version entropy {version_entropy:.2f} too low"
        assert timezone_entropy >= 2.0, f"Timezone entropy {timezone_entropy:.2f} too low"
        assert language_entropy >= 1.0, f"Language entropy {language_entropy:.2f} too low"
        
        # But not too high either
        assert model_entropy <= 6.0, f"Model entropy {model_entropy:.2f} too high (suspicious)"


class TestBehaviorPatternValidation:
    """Validate behavior patterns simulate realistic human activity"""
    
    def test_swipe_timing_human_distribution(self):
        """Test that swipe timing follows human-like distribution"""
        
        behavior = BehaviorPattern(aggressiveness=0.3, personality_profile='cautious')
        
        # Generate many timing samples
        timing_samples = []
        for _ in range(1000):
            timing = behavior.get_swipe_timing()
            timing_samples.append(timing)
        
        # Statistical analysis
        mean_timing = statistics.mean(timing_samples)
        std_timing = statistics.stdev(timing_samples)
        
        # Human swipe timing should be:
        # - Average between 1-8 seconds (not too fast, not too slow)
        # - Have reasonable variance (humans aren't perfectly consistent)
        # - Follow roughly normal or log-normal distribution
        
        assert 1.0 <= mean_timing <= 8.0, f"Mean timing {mean_timing:.2f}s outside human range"
        assert 0.5 <= std_timing <= 4.0, f"Timing variance {std_timing:.2f}s unrealistic"
        
        # Test for normality (relaxed test)
        _, p_value = stats.normaltest(timing_samples)
        # Don't require perfect normality, but shouldn't be completely non-normal
        assert p_value >= 0.001, f"Timing distribution too non-normal (p={p_value:.4f})"
    
    def test_session_duration_realistic_patterns(self):
        """Test session duration patterns are realistic"""
        
        # Test different personality profiles
        personalities = ['cautious', 'confident', 'impulsive', 'methodical']
        
        for personality in personalities:
            behavior = BehaviorPattern(aggressiveness=0.3, personality_profile=personality)
            
            durations = []
            for _ in range(100):
                duration = behavior.get_session_duration()
                durations.append(duration)
            
            mean_duration = statistics.mean(durations)
            
            # Session durations should be realistic:
            # - Cautious: shorter sessions (1-10 minutes)
            # - Confident: longer sessions (5-20 minutes)
            # - Impulsive: variable sessions (2-15 minutes)
            # - Methodical: consistent sessions (5-15 minutes)
            
            if personality == 'cautious':
                assert 1.0 <= mean_duration <= 12.0, \
                    f"Cautious duration {mean_duration:.1f}m unrealistic"
            elif personality == 'confident':
                assert 3.0 <= mean_duration <= 25.0, \
                    f"Confident duration {mean_duration:.1f}m unrealistic"
            
            # All personalities should have reasonable bounds
            assert 0.5 <= mean_duration <= 30.0, \
                f"Duration {mean_duration:.1f}m for {personality} outside bounds"
    
    def test_daily_activity_pattern_realism(self):
        """Test daily activity patterns are realistic"""
        
        behavior = BehaviorPattern(aggressiveness=0.5)  # Moderate aggressiveness
        
        # Generate daily patterns for a week
        daily_sessions = []
        for day in range(7):
            sessions = behavior.get_daily_session_count()
            daily_sessions.append(sessions)
        
        mean_sessions = statistics.mean(daily_sessions)
        
        # Daily sessions should be realistic:
        # - Not too few (minimum engagement)
        # - Not too many (suspicious activity)
        # - Some variance day-to-day
        
        assert 1 <= mean_sessions <= 12, f"Mean daily sessions {mean_sessions} unrealistic"
        
        # Should have some variance (humans aren't perfectly consistent)
        if len(set(daily_sessions)) > 1:  # If there's any variance
            variance = statistics.variance(daily_sessions)
            assert variance >= 0.5, "Daily session variance too low (robotic)"
    
    def test_aggressiveness_scaling_validation(self):
        """Test that aggressiveness scaling affects behavior appropriately"""
        
        aggressiveness_levels = [0.1, 0.3, 0.5, 0.7, 0.9]
        
        timing_by_level = {}
        sessions_by_level = {}
        
        for level in aggressiveness_levels:
            behavior = BehaviorPattern(aggressiveness=level)
            
            # Sample timing and sessions
            timings = [behavior.get_swipe_timing() for _ in range(50)]
            sessions = [behavior.get_daily_session_count() for _ in range(10)]
            
            timing_by_level[level] = statistics.mean(timings)
            sessions_by_level[level] = statistics.mean(sessions)
        
        # Verify aggressiveness scaling:
        # - Higher aggressiveness should mean faster swiping (lower timing)
        # - Higher aggressiveness should mean more sessions
        
        timing_values = [timing_by_level[level] for level in aggressiveness_levels]
        session_values = [sessions_by_level[level] for level in aggressiveness_levels]
        
        # Timing should generally decrease with aggressiveness
        # (allowing for some variance due to randomness)
        timing_trend = np.polyfit(aggressiveness_levels, timing_values, 1)[0]
        assert timing_trend < 0, f"Timing should decrease with aggressiveness (trend: {timing_trend:.3f})"
        
        # Sessions should generally increase with aggressiveness
        session_trend = np.polyfit(aggressiveness_levels, session_values, 1)[0]
        assert session_trend > 0, f"Sessions should increase with aggressiveness (trend: {session_trend:.3f})"


class TestTouchPatternValidation:
    """Validate touch patterns are human-like and varied"""
    
    def test_bezier_curve_smoothness(self):
        """Test that generated touch paths are smooth and natural"""
        
        generator = TouchPatternGenerator()
        
        # Test various swipe scenarios
        test_cases = [
            ((100, 200), (500, 800)),  # Diagonal swipe
            ((300, 300), (300, 700)),  # Vertical swipe
            ((200, 400), (600, 400)),  # Horizontal swipe
            ((150, 150), (450, 450)),  # Perfect diagonal
        ]
        
        for start, end in test_cases:
            points = generator.generate_bezier_swipe(start, end)
            
            # Validate path properties
            assert len(points) >= 10, f"Path too short: {len(points)} points"
            assert len(points) <= 50, f"Path too long: {len(points)} points"
            
            # Check smoothness - calculate curvature changes
            if len(points) >= 3:
                curvature_changes = []
                for i in range(1, len(points) - 1):
                    # Calculate angle change at each point
                    p1, p2, p3 = points[i-1], points[i], points[i+1]
                    
                    v1 = (p2[0] - p1[0], p2[1] - p1[1])
                    v2 = (p3[0] - p2[0], p3[1] - p2[1])
                    
                    # Calculate angle between vectors
                    dot_product = v1[0] * v2[0] + v1[1] * v2[1]
                    mag1 = (v1[0]**2 + v1[1]**2)**0.5
                    mag2 = (v2[0]**2 + v2[1]**2)**0.5
                    
                    if mag1 > 0 and mag2 > 0:
                        cos_angle = dot_product / (mag1 * mag2)
                        cos_angle = max(-1, min(1, cos_angle))  # Clamp to valid range
                        angle_change = abs(np.arccos(cos_angle))
                        curvature_changes.append(angle_change)
                
                if curvature_changes:
                    max_curvature = max(curvature_changes)
                    # Path shouldn't have extreme direction changes
                    assert max_curvature < np.pi/2, f"Path too jerky: {max_curvature:.3f} rad max change"
    
    def test_touch_timing_variation(self):
        """Test that touch timing has realistic human variation"""
        
        generator = TouchPatternGenerator()
        
        # Generate multiple paths and measure timing
        timings = []
        for _ in range(100):
            # Generate path
            start = (random.randint(50, 200), random.randint(50, 200))
            end = (random.randint(400, 700), random.randint(400, 800))
            
            points = generator.generate_bezier_swipe(start, end)
            
            # Calculate total timing for path
            total_timing = len(points) * 0.016  # Assume 60fps (16ms per frame)
            timings.append(total_timing)
        
        # Analyze timing distribution
        mean_timing = statistics.mean(timings)
        std_timing = statistics.stdev(timings)
        
        # Human touch timing should be:
        # - Between 100ms and 2000ms for typical swipes
        # - Have reasonable variance
        
        assert 0.1 <= mean_timing <= 2.0, f"Mean touch timing {mean_timing:.3f}s unrealistic"
        assert std_timing >= 0.02, f"Touch timing variance {std_timing:.3f}s too low"
    
    def test_touch_pressure_simulation(self):
        """Test touch pressure variation simulation"""
        
        generator = TouchPatternGenerator()
        
        # Generate path with pressure data
        start = (200, 300)
        end = (600, 700)
        
        # Test if pressure simulation is implemented
        try:
            points_with_pressure = generator.generate_bezier_swipe(
                start, end, 
                include_pressure=True
            )
            
            # If pressure is included, validate it
            if isinstance(points_with_pressure[0], (tuple, list)) and len(points_with_pressure[0]) >= 3:
                pressures = [point[2] for point in points_with_pressure if len(point) >= 3]
                
                if pressures:
                    # Pressure should vary realistically
                    min_pressure = min(pressures)
                    max_pressure = max(pressures)
                    
                    assert 0.0 <= min_pressure <= 1.0, f"Pressure values should be normalized"
                    assert 0.0 <= max_pressure <= 1.0, f"Pressure values should be normalized"
                    assert max_pressure > min_pressure, "Pressure should vary during touch"
        
        except (TypeError, AttributeError):
            # Pressure simulation not implemented yet - that's OK
            pytest.skip("Pressure simulation not yet implemented")
    
    def test_touch_path_uniqueness(self):
        """Test that touch paths are unique and not predictable"""
        
        generator = TouchPatternGenerator()
        
        # Generate multiple paths between same points
        start = (200, 200)
        end = (600, 600)
        
        paths = []
        for _ in range(20):
            path = generator.generate_bezier_swipe(start, end)
            paths.append(path)
        
        # Calculate path similarity
        path_hashes = []
        for path in paths:
            # Create hash of path shape
            path_str = ",".join(f"{x},{y}" for x, y in path)
            path_hash = hashlib.md5(path_str.encode()).hexdigest()
            path_hashes.append(path_hash)
        
        # Paths should be unique
        unique_paths = len(set(path_hashes))
        uniqueness_ratio = unique_paths / len(paths)
        
        assert uniqueness_ratio >= 0.8, f"Touch paths too similar: {uniqueness_ratio:.1%} unique"


class TestAntiDetectionIntegration:
    """Integration tests for complete anti-detection system"""
    
    def test_complete_stealth_profile_generation(self):
        """Test complete stealth profile generation"""
        
        anti_detection = get_anti_detection_system(aggressiveness=0.4)
        
        # Generate complete stealth profile
        device_id = "integration_test_device"
        
        # Create fingerprint
        fingerprint = anti_detection.create_device_fingerprint(device_id)
        
        # Create behavior pattern
        behavior = BehaviorPattern(aggressiveness=0.4)
        
        # Create touch patterns
        touch_generator = TouchPatternGenerator()
        
        # Validate integration
        assert fingerprint is not None, "Fingerprint generation failed"
        assert behavior is not None, "Behavior pattern generation failed"
        
        # Test that components work together
        swipe_timing = behavior.get_swipe_timing()
        session_duration = behavior.get_session_duration()
        
        touch_path = touch_generator.generate_bezier_swipe((100, 100), (500, 500))
        
        # All components should produce valid output
        assert swipe_timing > 0, "Invalid swipe timing"
        assert session_duration > 0, "Invalid session duration"
        assert len(touch_path) > 0, "Invalid touch path"
    
    def test_detection_risk_assessment(self):
        """Test overall detection risk assessment"""
        
        def assess_detection_risk(aggressiveness: float) -> DetectionValidationResult:
            """Assess detection risk for given aggressiveness level"""
            
            anti_detection = get_anti_detection_system(aggressiveness=aggressiveness)
            behavior = BehaviorPattern(aggressiveness=aggressiveness)
            
            # Generate samples for analysis
            timing_samples = [behavior.get_swipe_timing() for _ in range(50)]
            session_samples = [behavior.get_daily_session_count() for _ in range(10)]
            
            # Calculate risk factors
            avg_timing = statistics.mean(timing_samples)
            avg_sessions = statistics.mean(session_samples)
            timing_variance = statistics.variance(timing_samples)
            
            # Risk assessment logic
            risk_factors = []
            
            if avg_timing < 0.5:
                risk_factors.append("Extremely fast swiping")
            elif avg_timing < 1.0:
                risk_factors.append("Very fast swiping")
            
            if avg_sessions > 10:
                risk_factors.append("Excessive daily activity")
            elif avg_sessions > 8:
                risk_factors.append("High daily activity")
            
            if timing_variance < 0.1:
                risk_factors.append("Overly consistent timing")
            
            # Determine overall risk
            if len(risk_factors) == 0:
                risk_level = "LOW"
                confidence = 0.9
            elif len(risk_factors) <= 2:
                risk_level = "MEDIUM" 
                confidence = 0.7
            else:
                risk_level = "HIGH"
                confidence = 0.5
            
            return DetectionValidationResult(
                test_name="detection_risk_assessment",
                passed=risk_level != "HIGH",
                confidence_score=confidence,
                human_likeness_score=1.0 - (len(risk_factors) * 0.2),
                detection_risk=risk_level,
                details={
                    'avg_timing': avg_timing,
                    'avg_sessions': avg_sessions,
                    'timing_variance': timing_variance,
                    'risk_factors': risk_factors
                },
                recommendations=[
                    "Increase timing variance" if timing_variance < 0.1 else "",
                    "Reduce session frequency" if avg_sessions > 8 else "",
                    "Slow down swiping" if avg_timing < 1.0 else ""
                ]
            )
        
        # Test different aggressiveness levels
        test_levels = [0.1, 0.3, 0.5, 0.7, 0.9]
        
        for level in test_levels:
            result = assess_detection_risk(level)
            
            print(f"\nAggressiveness {level}: {result.detection_risk} risk")
            print(f"  Confidence: {result.confidence_score:.1%}")
            print(f"  Human-likeness: {result.human_likeness_score:.1%}")
            
            if result.details['risk_factors']:
                print(f"  Risk factors: {', '.join(result.details['risk_factors'])}")
            
            # Higher aggressiveness should generally mean higher risk
            if level >= 0.7:
                assert result.detection_risk in ["MEDIUM", "HIGH"], \
                    f"High aggressiveness should have elevated risk"
            elif level <= 0.3:
                assert result.detection_risk in ["LOW", "MEDIUM"], \
                    f"Low aggressiveness should have lower risk"
    
    def test_stealth_measure_effectiveness(self):
        """Test effectiveness of stealth measures over time"""
        
        # Simulate extended usage patterns
        anti_detection = get_anti_detection_system(aggressiveness=0.3)
        
        # Generate activity over simulated days
        daily_patterns = []
        
        for day in range(7):  # Simulate a week
            day_pattern = {
                'fingerprint_consistency': True,
                'behavior_variance': [],
                'timing_patterns': []
            }
            
            # Generate behavior for the day
            behavior = BehaviorPattern(aggressiveness=0.3)
            
            # Simulate sessions throughout the day
            session_count = behavior.get_daily_session_count()
            
            for session in range(session_count):
                session_duration = behavior.get_session_duration()
                
                # Simulate swipes in session
                swipes_in_session = int(session_duration * 2)  # ~2 swipes per minute
                
                session_timings = []
                for _ in range(swipes_in_session):
                    timing = behavior.get_swipe_timing()
                    session_timings.append(timing)
                
                day_pattern['behavior_variance'].extend(session_timings)
                day_pattern['timing_patterns'].append(statistics.mean(session_timings))
            
            daily_patterns.append(day_pattern)
        
        # Analyze patterns over time
        all_timings = []
        for day in daily_patterns:
            all_timings.extend(day['behavior_variance'])
        
        # Statistical analysis of long-term patterns
        overall_variance = statistics.variance(all_timings) if len(all_timings) > 1 else 0
        daily_averages = [statistics.mean(day['behavior_variance']) if day['behavior_variance'] else 0 
                         for day in daily_patterns]
        
        day_to_day_variance = statistics.variance(daily_averages) if len(daily_averages) > 1 else 0
        
        # Validate long-term stealth
        assert overall_variance > 0.5, f"Overall timing variance {overall_variance:.3f} too low"
        assert day_to_day_variance > 0.1, f"Day-to-day variance {day_to_day_variance:.3f} too low"
        
        print(f"\nLong-term stealth analysis:")
        print(f"  Overall timing variance: {overall_variance:.3f}")
        print(f"  Day-to-day variance: {day_to_day_variance:.3f}")
        print(f"  Total sessions simulated: {sum(len(d['timing_patterns']) for d in daily_patterns)}")


# Test configuration
pytestmark = [
    pytest.mark.unit,
    pytest.mark.anti_detection,
]


if __name__ == "__main__":
    # Run anti-detection validation tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-m", "anti_detection"
    ])