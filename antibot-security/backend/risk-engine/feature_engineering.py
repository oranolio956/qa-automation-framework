"""
Advanced Feature Engineering Pipeline for ML-based Risk Scoring
Processes raw behavioral data into 50+ ML-ready features with sub-50ms latency
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio
import time
import json
import logging
import hashlib
from collections import defaultdict, deque
from scipy import stats
from scipy.signal import find_peaks
from sklearn.preprocessing import StandardScaler, RobustScaler, MinMaxScaler
import redis.asyncio as redis

logger = logging.getLogger(__name__)

@dataclass
class FeatureVector:
    """Container for extracted features with metadata"""
    features: Dict[str, float]
    feature_names: List[str]
    timestamp: datetime
    session_id: str
    confidence: float
    processing_time_ms: float

class AdvancedFeatureExtractor:
    """
    High-performance feature extraction with 50+ behavioral, device, and network features
    Optimized for sub-50ms latency with real-time computation
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.feature_cache = {}
        self.session_history = defaultdict(lambda: deque(maxlen=1000))
        
        # Feature extraction parameters
        self.mouse_velocity_window = 5
        self.typing_rhythm_window = 10
        self.temporal_analysis_window = 50
        self.behavioral_baseline_samples = 100
        
        # Feature scalers for real-time normalization
        self.scalers = {
            'standard': StandardScaler(),
            'robust': RobustScaler(),
            'minmax': MinMaxScaler()
        }
        
        # Initialize baseline statistics
        self.baseline_stats = self._initialize_baseline_stats()
        
    def _initialize_baseline_stats(self) -> Dict[str, Dict[str, float]]:
        """Initialize baseline statistics for feature normalization"""
        return {
            'mouse_velocity': {'mean': 150.0, 'std': 75.0, 'median': 140.0},
            'key_dwell_time': {'mean': 100.0, 'std': 30.0, 'median': 95.0},
            'scroll_speed': {'mean': 300.0, 'std': 150.0, 'median': 280.0},
            'event_interval': {'mean': 500.0, 'std': 200.0, 'median': 450.0},
            'session_duration': {'mean': 300.0, 'std': 180.0, 'median': 240.0}
        }
    
    async def extract_features_async(self, behavioral_data: Dict[str, Any]) -> FeatureVector:
        """
        Asynchronously extract comprehensive feature set with sub-50ms latency
        """
        start_time = time.time()
        session_id = behavioral_data.get('sessionId', '')
        
        try:
            # Run feature extraction in parallel
            tasks = [
                self._extract_mouse_features(behavioral_data),
                self._extract_keyboard_features(behavioral_data),
                self._extract_scroll_features(behavioral_data),
                self._extract_touch_features(behavioral_data),
                self._extract_temporal_features(behavioral_data),
                self._extract_device_features(behavioral_data),
                self._extract_network_features(behavioral_data),
                self._extract_behavioral_patterns(behavioral_data),
                self._extract_session_features(behavioral_data),
                self._extract_statistical_features(behavioral_data)
            ]
            
            feature_sets = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine all features
            combined_features = {}
            for feature_set in feature_sets:
                if isinstance(feature_set, dict):
                    combined_features.update(feature_set)
                elif isinstance(feature_set, Exception):
                    logger.warning(f"Feature extraction error: {feature_set}")
            
            # Add derived and composite features
            combined_features.update(self._extract_composite_features(combined_features))
            
            # Calculate feature importance and confidence
            confidence = self._calculate_feature_confidence(combined_features)
            
            # Store session history for temporal analysis
            await self._update_session_history(session_id, combined_features)
            
            processing_time = (time.time() - start_time) * 1000
            
            feature_vector = FeatureVector(
                features=combined_features,
                feature_names=list(combined_features.keys()),
                timestamp=datetime.now(),
                session_id=session_id,
                confidence=confidence,
                processing_time_ms=processing_time
            )
            
            logger.debug(f"Feature extraction completed in {processing_time:.2f}ms")
            return feature_vector
            
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            # Return minimal feature set as fallback
            return self._create_fallback_features(behavioral_data, time.time() - start_time)
    
    async def _extract_mouse_features(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Extract advanced mouse behavior features"""
        features = {}
        events = data.get('events', [])
        mouse_events = [e for e in events if e.get('type') == 'mouse']
        
        if not mouse_events:
            return self._get_zero_mouse_features()
        
        # Basic mouse metrics
        features['mouse_event_count'] = len(mouse_events)
        features['mouse_events_per_second'] = len(mouse_events) / max(1, data.get('sessionDuration', 1))
        
        # Movement analysis
        moves = [e for e in mouse_events if e.get('subtype') == 'mousemove']
        if moves:
            # Velocity analysis
            velocities = [e.get('velocity', 0) for e in moves if e.get('velocity') is not None]
            if velocities:
                features['mouse_avg_velocity'] = np.mean(velocities)
                features['mouse_max_velocity'] = np.max(velocities)
                features['mouse_velocity_std'] = np.std(velocities)
                features['mouse_velocity_cv'] = np.std(velocities) / (np.mean(velocities) + 1e-6)
                features['mouse_velocity_skewness'] = stats.skew(velocities)
                features['mouse_velocity_kurtosis'] = stats.kurtosis(velocities)
                
                # Velocity peaks analysis
                velocity_peaks, _ = find_peaks(velocities, height=np.mean(velocities))
                features['mouse_velocity_peaks'] = len(velocity_peaks)
                features['mouse_velocity_peak_frequency'] = len(velocity_peaks) / len(velocities)
            
            # Acceleration analysis
            accelerations = [e.get('acceleration', 0) for e in moves if e.get('acceleration') is not None]
            if accelerations:
                features['mouse_avg_acceleration'] = np.mean(accelerations)
                features['mouse_acceleration_std'] = np.std(accelerations)
                features['mouse_acceleration_range'] = np.max(accelerations) - np.min(accelerations)
            
            # Trajectory analysis
            features.update(self._analyze_mouse_trajectory(moves))
            
            # Movement patterns
            features.update(self._analyze_movement_patterns(moves))
        
        # Click analysis
        clicks = [e for e in mouse_events if e.get('subtype') in ['click', 'mousedown', 'mouseup']]
        if clicks:
            features['mouse_click_count'] = len(clicks)
            features['mouse_click_rate'] = len(clicks) / max(1, data.get('sessionDuration', 1))
            
            # Click timing analysis
            click_intervals = []
            for i in range(1, len(clicks)):
                interval = clicks[i].get('timestamp', 0) - clicks[i-1].get('timestamp', 0)
                click_intervals.append(interval)
            
            if click_intervals:
                features['mouse_avg_click_interval'] = np.mean(click_intervals)
                features['mouse_click_interval_std'] = np.std(click_intervals)
                features['mouse_click_regularity'] = 1.0 / (1.0 + np.std(click_intervals) / (np.mean(click_intervals) + 1e-6))
        
        return features
    
    def _get_zero_mouse_features(self) -> Dict[str, float]:
        """Return zero values for mouse features when no mouse events exist"""
        return {
            'mouse_event_count': 0,
            'mouse_events_per_second': 0,
            'mouse_avg_velocity': 0,
            'mouse_max_velocity': 0,
            'mouse_velocity_std': 0,
            'mouse_velocity_cv': 0,
            'mouse_velocity_skewness': 0,
            'mouse_velocity_kurtosis': 0,
            'mouse_velocity_peaks': 0,
            'mouse_velocity_peak_frequency': 0,
            'mouse_avg_acceleration': 0,
            'mouse_acceleration_std': 0,
            'mouse_acceleration_range': 0,
            'mouse_click_count': 0,
            'mouse_click_rate': 0,
            'mouse_avg_click_interval': 0,
            'mouse_click_interval_std': 0,
            'mouse_click_regularity': 0,
            'mouse_trajectory_smoothness': 0,
            'mouse_trajectory_complexity': 0,
            'mouse_curvature_avg': 0,
            'mouse_direction_changes': 0,
            'mouse_movement_efficiency': 0
        }
    
    def _analyze_mouse_trajectory(self, moves: List[Dict]) -> Dict[str, float]:
        """Analyze mouse trajectory characteristics"""
        features = {}
        
        if len(moves) < 3:
            return {
                'mouse_trajectory_smoothness': 0,
                'mouse_trajectory_complexity': 0,
                'mouse_curvature_avg': 0,
                'mouse_direction_changes': 0,
                'mouse_movement_efficiency': 0
            }
        
        # Extract coordinates
        points = [(e.get('x', 0), e.get('y', 0)) for e in moves if e.get('x') is not None and e.get('y') is not None]
        
        if len(points) < 3:
            return features
        
        # Calculate trajectory metrics
        total_distance = 0
        direction_changes = 0
        curvatures = []
        
        for i in range(1, len(points)):
            # Distance calculation
            dx = points[i][0] - points[i-1][0]
            dy = points[i][1] - points[i-1][1]
            distance = np.sqrt(dx**2 + dy**2)
            total_distance += distance
            
            # Direction change calculation
            if i >= 2:
                # Vectors
                v1 = (points[i-1][0] - points[i-2][0], points[i-1][1] - points[i-2][1])
                v2 = (points[i][0] - points[i-1][0], points[i][1] - points[i-1][1])
                
                # Angle between vectors
                if np.linalg.norm(v1) > 0 and np.linalg.norm(v2) > 0:
                    cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                    cos_angle = np.clip(cos_angle, -1, 1)
                    angle = np.arccos(cos_angle)
                    curvatures.append(angle)
                    
                    if angle > np.pi / 4:  # > 45 degrees
                        direction_changes += 1
        
        # Straight-line distance
        start_point = points[0]
        end_point = points[-1]
        straight_distance = np.sqrt((end_point[0] - start_point[0])**2 + (end_point[1] - start_point[1])**2)
        
        # Calculate features
        features['mouse_trajectory_complexity'] = total_distance / (straight_distance + 1e-6)
        features['mouse_curvature_avg'] = np.mean(curvatures) if curvatures else 0
        features['mouse_direction_changes'] = direction_changes
        features['mouse_movement_efficiency'] = (straight_distance + 1e-6) / (total_distance + 1e-6)
        features['mouse_trajectory_smoothness'] = 1.0 / (1.0 + np.std(curvatures)) if curvatures else 0
        
        return features
    
    def _analyze_movement_patterns(self, moves: List[Dict]) -> Dict[str, float]:
        """Analyze high-level movement patterns"""
        features = {}
        
        if len(moves) < 10:
            return {'mouse_pattern_regularity': 0, 'mouse_tremor_score': 0}
        
        # Extract velocities and positions
        velocities = [e.get('velocity', 0) for e in moves if e.get('velocity') is not None]
        positions = [(e.get('x', 0), e.get('y', 0)) for e in moves if e.get('x') is not None and e.get('y') is not None]
        
        # Pattern regularity (autocorrelation)
        if len(velocities) > 5:
            correlation = np.corrcoef(velocities[:-1], velocities[1:])[0, 1] if len(velocities) > 1 else 0
            features['mouse_pattern_regularity'] = max(0, correlation) if not np.isnan(correlation) else 0
        
        # Tremor detection (high-frequency oscillations)
        if len(positions) > 20:
            x_coords = [p[0] for p in positions]
            y_coords = [p[1] for p in positions]
            
            # Calculate micro-movements
            x_diffs = np.diff(x_coords)
            y_diffs = np.diff(y_coords)
            micro_movements = np.sqrt(x_diffs**2 + y_diffs**2)
            
            # Tremor score based on small, frequent movements
            small_movements = micro_movements[micro_movements < 5]  # pixels
            features['mouse_tremor_score'] = len(small_movements) / len(micro_movements) if len(micro_movements) > 0 else 0
        
        return features
    
    async def _extract_keyboard_features(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Extract comprehensive keyboard behavior features"""
        features = {}
        events = data.get('events', [])
        keyboard_events = [e for e in events if e.get('type') == 'keyboard']
        
        if not keyboard_events:
            return self._get_zero_keyboard_features()
        
        # Basic keyboard metrics
        features['keyboard_event_count'] = len(keyboard_events)
        features['keyboard_events_per_second'] = len(keyboard_events) / max(1, data.get('sessionDuration', 1))
        
        # Typing rhythm analysis
        dwell_times = [e.get('dwellTime', 0) for e in keyboard_events if e.get('dwellTime') is not None]
        if dwell_times:
            features['keyboard_avg_dwell_time'] = np.mean(dwell_times)
            features['keyboard_dwell_time_std'] = np.std(dwell_times)
            features['keyboard_dwell_time_cv'] = np.std(dwell_times) / (np.mean(dwell_times) + 1e-6)
            features['keyboard_typing_rhythm_consistency'] = 1.0 / (1.0 + features['keyboard_dwell_time_cv'])
            
            # Advanced rhythm analysis
            features['keyboard_dwell_time_skewness'] = stats.skew(dwell_times)
            features['keyboard_dwell_time_kurtosis'] = stats.kurtosis(dwell_times)
            
            # Typing pattern regularity
            if len(dwell_times) > 5:
                correlation = np.corrcoef(dwell_times[:-1], dwell_times[1:])[0, 1] if len(dwell_times) > 1 else 0
                features['keyboard_pattern_regularity'] = max(0, correlation) if not np.isnan(correlation) else 0
        
        # Key press intervals
        timestamps = [e.get('timestamp', 0) for e in keyboard_events]
        if len(timestamps) > 1:
            intervals = np.diff(timestamps)
            features['keyboard_avg_interval'] = np.mean(intervals)
            features['keyboard_interval_std'] = np.std(intervals)
            features['keyboard_interval_regularity'] = 1.0 / (1.0 + np.std(intervals) / (np.mean(intervals) + 1e-6))
        
        # Key event types analysis
        key_down_events = [e for e in keyboard_events if e.get('subtype') == 'keydown']
        key_up_events = [e for e in keyboard_events if e.get('subtype') == 'keyup']
        
        features['keyboard_down_up_ratio'] = len(key_down_events) / max(1, len(key_up_events))
        
        return features
    
    def _get_zero_keyboard_features(self) -> Dict[str, float]:
        """Return zero values for keyboard features when no keyboard events exist"""
        return {
            'keyboard_event_count': 0,
            'keyboard_events_per_second': 0,
            'keyboard_avg_dwell_time': 0,
            'keyboard_dwell_time_std': 0,
            'keyboard_dwell_time_cv': 0,
            'keyboard_typing_rhythm_consistency': 0,
            'keyboard_dwell_time_skewness': 0,
            'keyboard_dwell_time_kurtosis': 0,
            'keyboard_pattern_regularity': 0,
            'keyboard_avg_interval': 0,
            'keyboard_interval_std': 0,
            'keyboard_interval_regularity': 0,
            'keyboard_down_up_ratio': 1.0
        }
    
    async def _extract_scroll_features(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Extract scroll behavior features"""
        features = {}
        events = data.get('events', [])
        scroll_events = [e for e in events if e.get('type') == 'scroll']
        
        if not scroll_events:
            return {'scroll_event_count': 0, 'scroll_speed_avg': 0, 'scroll_regularity': 0}
        
        # Basic scroll metrics
        features['scroll_event_count'] = len(scroll_events)
        
        # Scroll speed analysis
        scroll_speeds = [e.get('scrollSpeed', 0) for e in scroll_events if e.get('scrollSpeed') is not None]
        if scroll_speeds:
            features['scroll_speed_avg'] = np.mean(scroll_speeds)
            features['scroll_speed_std'] = np.std(scroll_speeds)
            features['scroll_speed_max'] = np.max(scroll_speeds)
            
            # Scroll regularity
            if len(scroll_speeds) > 3:
                correlation = np.corrcoef(scroll_speeds[:-1], scroll_speeds[1:])[0, 1] if len(scroll_speeds) > 1 else 0
                features['scroll_regularity'] = max(0, correlation) if not np.isnan(correlation) else 0
        
        return features
    
    async def _extract_touch_features(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Extract touch-specific features for mobile devices"""
        features = {}
        events = data.get('events', [])
        touch_events = [e for e in events if e.get('type') == 'touch']
        
        features['touch_event_count'] = len(touch_events)
        
        if touch_events:
            # Multi-touch analysis
            multi_touch_events = [e for e in touch_events if len(e.get('touches', [])) > 1]
            features['multi_touch_ratio'] = len(multi_touch_events) / len(touch_events)
            
            # Touch pressure analysis
            pressures = []
            for event in touch_events:
                for touch in event.get('touches', []):
                    if touch.get('force') is not None:
                        pressures.append(touch.get('force'))
            
            if pressures:
                features['touch_pressure_avg'] = np.mean(pressures)
                features['touch_pressure_std'] = np.std(pressures)
        
        return features
    
    async def _extract_temporal_features(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Extract temporal behavior patterns"""
        features = {}
        events = data.get('events', [])
        
        if len(events) < 2:
            return {'temporal_regularity': 0, 'event_burst_score': 0}
        
        # Event timing analysis
        timestamps = [e.get('timestamp', 0) for e in events]
        timestamps.sort()
        
        intervals = np.diff(timestamps)
        features['temporal_avg_interval'] = np.mean(intervals)
        features['temporal_interval_std'] = np.std(intervals)
        features['temporal_regularity'] = 1.0 / (1.0 + np.std(intervals) / (np.mean(intervals) + 1e-6))
        
        # Burst detection
        short_intervals = intervals[intervals < np.percentile(intervals, 10)]
        features['event_burst_score'] = len(short_intervals) / len(intervals) if len(intervals) > 0 else 0
        
        # Idle periods detection
        long_intervals = intervals[intervals > np.percentile(intervals, 90)]
        features['idle_period_score'] = len(long_intervals) / len(intervals) if len(intervals) > 0 else 0
        
        return features
    
    async def _extract_device_features(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Extract device fingerprint features"""
        features = {}
        device_fp = data.get('deviceFingerprint', {})
        
        # Basic device info
        features['has_device_fingerprint'] = 1.0 if device_fp else 0.0
        features['has_webgl'] = 1.0 if device_fp.get('webgl') else 0.0
        features['has_audio_fingerprint'] = 1.0 if device_fp.get('audio') else 0.0
        features['has_canvas_fingerprint'] = 1.0 if device_fp.get('canvas') else 0.0
        
        # Screen characteristics
        screen = device_fp.get('screen', {})
        if screen:
            features['screen_width'] = screen.get('width', 0)
            features['screen_height'] = screen.get('height', 0)
            features['screen_color_depth'] = screen.get('colorDepth', 0)
            features['screen_pixel_ratio'] = screen.get('pixelRatio', 1.0)
            features['screen_resolution'] = features['screen_width'] * features['screen_height']
        
        # Timezone consistency
        timezone = device_fp.get('timezone', {})
        if timezone:
            features['timezone_offset'] = timezone.get('offset', 0)
            features['timezone_dst'] = 1.0 if timezone.get('dst') else 0.0
        
        return features
    
    async def _extract_network_features(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Extract network and connection features"""
        features = {}
        
        # TLS fingerprint analysis
        tls_fp = data.get('tlsFingerprint', {})
        if tls_fp:
            features['has_tls_fingerprint'] = 1.0
            features['tls_protocol_count'] = len(tls_fp.get('supportedProtocols', []))
            features['tls_cipher_count'] = len(tls_fp.get('supportedCiphers', []))
        else:
            features['has_tls_fingerprint'] = 0.0
            features['tls_protocol_count'] = 0
            features['tls_cipher_count'] = 0
        
        # Performance metrics
        performance = data.get('metadata', {}).get('performanceMetrics', {})
        features['event_collection_time'] = performance.get('eventCollectionTime', 0)
        features['data_transmission_time'] = performance.get('dataTransmissionTime', 0)
        features['total_events'] = performance.get('totalEvents', 0)
        
        return features
    
    async def _extract_behavioral_patterns(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Extract high-level behavioral patterns"""
        features = {}
        events = data.get('events', [])
        
        # Event type distribution
        event_types = defaultdict(int)
        for event in events:
            event_types[event.get('type', 'unknown')] += 1
        
        total_events = len(events)
        if total_events > 0:
            features['mouse_event_ratio'] = event_types['mouse'] / total_events
            features['keyboard_event_ratio'] = event_types['keyboard'] / total_events
            features['scroll_event_ratio'] = event_types['scroll'] / total_events
            features['touch_event_ratio'] = event_types['touch'] / total_events
            features['focus_event_ratio'] = event_types['focus'] / total_events
        
        # Behavioral consistency score
        features['behavioral_diversity'] = len(event_types) / 10.0  # Normalized to common event types
        
        return features
    
    async def _extract_session_features(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Extract session-level features"""
        features = {}
        
        # Session duration
        session_duration = data.get('sessionDuration', 0)
        features['session_duration'] = session_duration
        features['session_duration_log'] = np.log(session_duration + 1)
        
        # Page interaction
        features['page_url_length'] = len(data.get('pageUrl', ''))
        features['has_referrer'] = 1.0 if data.get('referrer') else 0.0
        
        # Metadata analysis
        metadata = data.get('metadata', {})
        features['metadata_richness'] = len(metadata)
        
        return features
    
    async def _extract_statistical_features(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Extract statistical features across all events"""
        features = {}
        events = data.get('events', [])
        
        if not events:
            return {}
        
        # Cross-modal timing analysis
        mouse_events = [e for e in events if e.get('type') == 'mouse']
        keyboard_events = [e for e in events if e.get('type') == 'keyboard']
        
        # Interleaving patterns
        if mouse_events and keyboard_events:
            mouse_times = [e.get('timestamp', 0) for e in mouse_events]
            keyboard_times = [e.get('timestamp', 0) for e in keyboard_events]
            
            # Calculate interleaving score
            all_times = sorted(mouse_times + keyboard_times)
            interleaving_score = 0
            for i, timestamp in enumerate(all_times):
                if timestamp in mouse_times and i > 0 and all_times[i-1] in keyboard_times:
                    interleaving_score += 1
                elif timestamp in keyboard_times and i > 0 and all_times[i-1] in mouse_times:
                    interleaving_score += 1
            
            features['mouse_keyboard_interleaving'] = interleaving_score / len(all_times) if all_times else 0
        
        return features
    
    def _extract_composite_features(self, features: Dict[str, float]) -> Dict[str, float]:
        """Create composite features from extracted base features"""
        composite = {}
        
        # Activity ratios
        total_events = features.get('mouse_event_count', 0) + features.get('keyboard_event_count', 0) + features.get('scroll_event_count', 0)
        if total_events > 0:
            composite['mouse_dominance'] = features.get('mouse_event_count', 0) / total_events
            composite['keyboard_dominance'] = features.get('keyboard_event_count', 0) / total_events
            composite['scroll_dominance'] = features.get('scroll_event_count', 0) / total_events
        
        # Speed coherence across modalities
        mouse_speed = features.get('mouse_avg_velocity', 0)
        keyboard_speed = 1.0 / (features.get('keyboard_avg_dwell_time', 1) + 1e-6)
        scroll_speed = features.get('scroll_speed_avg', 0)
        
        speeds = [s for s in [mouse_speed, keyboard_speed, scroll_speed] if s > 0]
        if len(speeds) > 1:
            composite['cross_modal_speed_consistency'] = 1.0 / (1.0 + np.std(speeds) / (np.mean(speeds) + 1e-6))
        
        # Complexity metrics
        mouse_complexity = features.get('mouse_trajectory_complexity', 0)
        temporal_complexity = 1.0 / (features.get('temporal_regularity', 0) + 1e-6)
        composite['overall_complexity'] = (mouse_complexity + temporal_complexity) / 2
        
        # Anomaly indicators
        composite['velocity_anomaly_score'] = min(1.0, features.get('mouse_max_velocity', 0) / 1000.0)
        composite['timing_anomaly_score'] = min(1.0, features.get('keyboard_dwell_time_cv', 0))
        
        return composite
    
    def _calculate_feature_confidence(self, features: Dict[str, float]) -> float:
        """Calculate confidence score based on feature completeness and quality"""
        # Feature completeness
        expected_features = 50  # Target number of features
        actual_features = len([v for v in features.values() if v != 0])
        completeness = actual_features / expected_features
        
        # Data quality indicators
        has_mouse_data = features.get('mouse_event_count', 0) > 0
        has_keyboard_data = features.get('keyboard_event_count', 0) > 0
        has_device_fp = features.get('has_device_fingerprint', 0) > 0
        
        quality_score = (has_mouse_data + has_keyboard_data + has_device_fp) / 3
        
        # Overall confidence
        confidence = (completeness + quality_score) / 2
        return min(1.0, max(0.0, confidence))
    
    async def _update_session_history(self, session_id: str, features: Dict[str, float]):
        """Update session history for temporal analysis"""
        if self.redis_client:
            try:
                # Store recent feature vector
                feature_data = {
                    'timestamp': datetime.now().isoformat(),
                    'features': features
                }
                
                key = f"session_features:{session_id}"
                await self.redis_client.lpush(key, json.dumps(feature_data))
                await self.redis_client.ltrim(key, 0, 99)  # Keep last 100 entries
                await self.redis_client.expire(key, 3600)  # 1 hour TTL
                
            except Exception as e:
                logger.warning(f"Failed to update session history: {e}")
    
    def _create_fallback_features(self, data: Dict[str, Any], processing_time: float) -> FeatureVector:
        """Create minimal fallback feature set"""
        fallback_features = {
            'session_duration': data.get('sessionDuration', 0),
            'total_events': len(data.get('events', [])),
            'has_device_fingerprint': 1.0 if data.get('deviceFingerprint') else 0.0,
            'fallback_mode': 1.0
        }
        
        return FeatureVector(
            features=fallback_features,
            feature_names=list(fallback_features.keys()),
            timestamp=datetime.now(),
            session_id=data.get('sessionId', ''),
            confidence=0.1,  # Low confidence for fallback
            processing_time_ms=processing_time * 1000
        )

class FeatureNormalizer:
    """Real-time feature normalization with adaptive baselines"""
    
    def __init__(self):
        self.scalers = {
            'standard': StandardScaler(),
            'robust': RobustScaler(),
            'minmax': MinMaxScaler()
        }
        self.fitted = False
        
    def normalize_features(self, feature_vector: FeatureVector, method: str = 'robust') -> np.ndarray:
        """Normalize features using specified method"""
        features_array = np.array([[v for v in feature_vector.features.values()]])
        
        if not self.fitted:
            # Use default normalization for first request
            return self._default_normalize(features_array)
        
        try:
            normalized = self.scalers[method].transform(features_array)
            return normalized[0]
        except Exception as e:
            logger.warning(f"Normalization failed, using default: {e}")
            return self._default_normalize(features_array)[0]
    
    def _default_normalize(self, features_array: np.ndarray) -> np.ndarray:
        """Apply default normalization without fitted scaler"""
        # Simple min-max normalization with known bounds
        normalized = np.clip(features_array, 0, 1000)  # Clip extreme values
        normalized = normalized / 1000.0  # Scale to 0-1 range
        return normalized
    
    async def update_scalers(self, feature_vectors: List[FeatureVector]):
        """Update scalers with new data"""
        if len(feature_vectors) < 10:
            return
        
        # Prepare data
        features_matrix = []
        for fv in feature_vectors:
            features_matrix.append(list(fv.features.values()))
        
        features_matrix = np.array(features_matrix)
        
        # Fit scalers
        for scaler in self.scalers.values():
            try:
                scaler.fit(features_matrix)
            except Exception as e:
                logger.warning(f"Scaler fitting failed: {e}")
        
        self.fitted = True