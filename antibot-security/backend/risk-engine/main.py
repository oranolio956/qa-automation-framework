"""
Advanced Risk Scoring Engine for Anti-Bot Security
Real-time ML-based risk assessment with sub-50ms response times
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json
import hashlib
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import redis.asyncio as redis
from motor.motor_asyncio import AsyncIOMotorClient
import joblib
import aiofiles
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_recall_fscore_support, roc_auc_score
import xgboost as xgb
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for request/response
class TouchEvent(BaseModel):
    identifier: int
    clientX: float
    clientY: float
    force: Optional[float] = None
    radiusX: Optional[float] = None
    radiusY: Optional[float] = None
    rotationAngle: Optional[float] = None

class BehavioralEvent(BaseModel):
    type: str
    subtype: Optional[str] = None
    timestamp: float
    sessionId: str
    pageUrl: str
    referrer: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    velocity: Optional[float] = None
    acceleration: Optional[float] = None
    dwellTime: Optional[float] = None
    scrollSpeed: Optional[float] = None
    direction: Optional[str] = None
    touches: Optional[List[TouchEvent]] = None

class DeviceFingerprint(BaseModel):
    hash: str
    userAgent: str
    language: str
    platform: str
    screen: Dict[str, Any]
    timezone: Dict[str, Any]
    webgl: Optional[Dict[str, Any]] = None
    canvas: Optional[Dict[str, Any]] = None
    audio: Optional[Dict[str, Any]] = None

class PerformanceMetrics(BaseModel):
    eventCollectionTime: float
    dataTransmissionTime: float
    totalEvents: int

class BehavioralDataRequest(BaseModel):
    sessionId: str
    deviceFingerprint: Optional[DeviceFingerprint] = None
    tlsFingerprint: Optional[Dict[str, Any]] = None
    events: List[BehavioralEvent]
    metadata: Dict[str, Any]

class RiskAction(BaseModel):
    type: str  # challenge, block, monitor, allow
    challengeType: Optional[str] = None
    reason: Optional[str] = None
    level: Optional[str] = None
    confidence: float
    
class RiskAssessmentResponse(BaseModel):
    sessionId: str
    riskScore: float = Field(..., ge=0.0, le=1.0, description="Risk score between 0.0 (human) and 1.0 (bot)")
    confidence: float = Field(..., ge=0.0, le=1.0)
    actions: List[RiskAction]
    reasons: List[str]
    modelVersion: str
    processingTimeMs: float
    timestamp: datetime

# Global components
class RiskScoringComponents:
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.mongo_client: Optional[AsyncIOMotorClient] = None
        self.models: Dict[str, Any] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        self.feature_extractors: Dict[str, Any] = {}
        self.model_version = "1.0.0"
        self.last_model_update = datetime.now()
        
    async def initialize(self):
        """Initialize all components"""
        try:
            # Initialize Redis for caching and rate limiting
            self.redis_client = await redis.from_url("redis://localhost:6379", decode_responses=True)
            
            # Initialize MongoDB for historical data
            self.mongo_client = AsyncIOMotorClient("mongodb://localhost:27017")
            
            # Load or train ML models
            await self.load_or_train_models()
            
            logger.info("Risk scoring components initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise

    async def load_or_train_models(self):
        """Load existing models or train new ones"""
        try:
            # Try to load existing models
            try:
                self.models['isolation_forest'] = joblib.load('models/isolation_forest.joblib')
                self.models['random_forest'] = joblib.load('models/random_forest.joblib')
                self.models['xgboost'] = joblib.load('models/xgboost.joblib')
                self.scalers['standard'] = joblib.load('models/scaler.joblib')
                logger.info("Loaded existing ML models")
            except FileNotFoundError:
                # Train new models with synthetic data
                await self.train_initial_models()
                logger.info("Trained new ML models")
                
        except Exception as e:
            logger.error(f"Failed to load/train models: {e}")
            # Use simple rule-based fallback
            self.models['fallback'] = self.create_fallback_model()

    async def train_initial_models(self):
        """Train initial models with synthetic data"""
        # Generate synthetic training data
        synthetic_data = self.generate_synthetic_training_data(10000)
        
        # Prepare features and labels
        X = synthetic_data.drop(['label', 'session_id'], axis=1)
        y = synthetic_data['label']
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train Isolation Forest for anomaly detection
        isolation_forest = IsolationForest(contamination=0.1, random_state=42)
        isolation_forest.fit(X_train_scaled)
        
        # Train Random Forest for classification
        random_forest = RandomForestClassifier(n_estimators=100, random_state=42)
        random_forest.fit(X_train_scaled, y_train)
        
        # Train XGBoost for enhanced classification
        xgb_model = xgb.XGBClassifier(n_estimators=100, random_state=42)
        xgb_model.fit(X_train_scaled, y_train)
        
        # Evaluate models
        rf_pred = random_forest.predict(X_test_scaled)
        xgb_pred = xgb_model.predict(X_test_scaled)
        
        rf_precision, rf_recall, rf_f1, _ = precision_recall_fscore_support(y_test, rf_pred, average='weighted')
        xgb_precision, xgb_recall, xgb_f1, _ = precision_recall_fscore_support(y_test, xgb_pred, average='weighted')
        
        logger.info(f"Random Forest - Precision: {rf_precision:.3f}, Recall: {rf_recall:.3f}, F1: {rf_f1:.3f}")
        logger.info(f"XGBoost - Precision: {xgb_precision:.3f}, Recall: {xgb_recall:.3f}, F1: {xgb_f1:.3f}")
        
        # Store models
        self.models['isolation_forest'] = isolation_forest
        self.models['random_forest'] = random_forest
        self.models['xgboost'] = xgb_model
        self.scalers['standard'] = scaler
        
        # Save models to disk
        import os
        os.makedirs('models', exist_ok=True)
        joblib.dump(isolation_forest, 'models/isolation_forest.joblib')
        joblib.dump(random_forest, 'models/random_forest.joblib')
        joblib.dump(xgb_model, 'models/xgboost.joblib')
        joblib.dump(scaler, 'models/scaler.joblib')

    def generate_synthetic_training_data(self, n_samples: int) -> pd.DataFrame:
        """Generate synthetic training data for initial model training"""
        np.random.seed(42)
        
        data = []
        for i in range(n_samples):
            # Generate human-like behavior (label=0)
            if i < n_samples * 0.8:  # 80% human traffic
                mouse_events = np.random.randint(50, 200)  # Humans generate moderate mouse events
                keyboard_events = np.random.randint(10, 100)  # Moderate typing
                scroll_events = np.random.randint(5, 50)  # Natural scrolling
                click_events = np.random.randint(2, 20)  # Normal clicking
                
                avg_mouse_velocity = np.random.normal(150, 50)  # Natural mouse speed
                avg_dwell_time = np.random.normal(120, 40)  # Natural typing rhythm
                session_duration = np.random.normal(180, 60)  # 3 minutes average
                
                unique_ips = 1  # Humans typically use one IP
                consistent_fingerprint = 1  # Consistent device fingerprint
                
                label = 0  # Human
                
            else:  # 20% bot traffic
                mouse_events = np.random.choice([0, np.random.randint(1000, 5000)])  # Either no mouse or too much
                keyboard_events = np.random.choice([0, np.random.randint(500, 2000)])  # Robotic typing
                scroll_events = np.random.randint(0, 10)  # Minimal scrolling
                click_events = np.random.randint(100, 500)  # Excessive clicking
                
                avg_mouse_velocity = np.random.choice([0, np.random.normal(500, 100)])  # Too fast or none
                avg_dwell_time = np.random.choice([np.random.normal(20, 5), np.random.normal(300, 50)])  # Too fast or too slow
                session_duration = np.random.choice([np.random.normal(5, 2), np.random.normal(600, 100)])  # Too short or too long
                
                unique_ips = np.random.randint(1, 10)  # Bots may rotate IPs
                consistent_fingerprint = np.random.choice([0, 1])  # May have inconsistent fingerprints
                
                label = 1  # Bot
            
            data.append({
                'session_id': f'session_{i}',
                'mouse_events': max(0, mouse_events),
                'keyboard_events': max(0, keyboard_events),
                'scroll_events': max(0, scroll_events),
                'click_events': max(0, click_events),
                'avg_mouse_velocity': max(0, avg_mouse_velocity),
                'avg_dwell_time': max(0, avg_dwell_time),
                'session_duration': max(0, session_duration),
                'unique_ips': unique_ips,
                'consistent_fingerprint': consistent_fingerprint,
                'label': label
            })
        
        return pd.DataFrame(data)

    def create_fallback_model(self):
        """Create simple rule-based fallback model"""
        def fallback_predict(features):
            risk_score = 0.0
            
            # Simple rules
            if features.get('mouse_events', 0) == 0:
                risk_score += 0.3
            if features.get('keyboard_events', 0) == 0:
                risk_score += 0.3
            if features.get('avg_mouse_velocity', 0) > 1000:
                risk_score += 0.4
            if features.get('session_duration', 0) < 10:
                risk_score += 0.2
                
            return min(1.0, risk_score)
        
        return fallback_predict

# Global components instance
components = RiskScoringComponents()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    # Startup
    await components.initialize()
    yield
    # Shutdown
    if components.redis_client:
        await components.redis_client.close()
    if components.mongo_client:
        components.mongo_client.close()

# Initialize FastAPI app
app = FastAPI(
    title="Anti-Bot Risk Scoring Engine",
    description="Advanced ML-based risk assessment for bot detection",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

class FeatureExtractor:
    """Extract features from behavioral data for ML models"""
    
    @staticmethod
    def extract_features(data: BehavioralDataRequest) -> Dict[str, float]:
        """Extract numerical features from behavioral data"""
        features = {}
        
        # Basic session features
        features['session_duration'] = time.time() - (data.metadata.get('timestamp', time.time()) / 1000)
        features['total_events'] = len(data.events)
        features['events_per_second'] = features['total_events'] / max(1, features['session_duration'])
        
        # Event type distributions
        event_types = {}
        for event in data.events:
            event_types[event.type] = event_types.get(event.type, 0) + 1
        
        features['mouse_events'] = event_types.get('mouse', 0)
        features['keyboard_events'] = event_types.get('keyboard', 0)
        features['scroll_events'] = event_types.get('scroll', 0)
        features['touch_events'] = event_types.get('touch', 0)
        features['focus_events'] = event_types.get('focus', 0)
        
        # Mouse behavior features
        mouse_events = [e for e in data.events if e.type == 'mouse']
        if mouse_events:
            velocities = [e.velocity for e in mouse_events if e.velocity is not None]
            accelerations = [e.acceleration for e in mouse_events if e.acceleration is not None]
            
            features['avg_mouse_velocity'] = np.mean(velocities) if velocities else 0
            features['max_mouse_velocity'] = np.max(velocities) if velocities else 0
            features['mouse_velocity_variance'] = np.var(velocities) if velocities else 0
            features['avg_mouse_acceleration'] = np.mean(accelerations) if accelerations else 0
            
            # Mouse movement patterns
            mouse_moves = [e for e in mouse_events if e.subtype == 'mousemove']
            if len(mouse_moves) > 1:
                features['mouse_movement_smoothness'] = FeatureExtractor.calculate_smoothness(mouse_moves)
                features['mouse_trajectory_complexity'] = FeatureExtractor.calculate_trajectory_complexity(mouse_moves)
        else:
            features['avg_mouse_velocity'] = 0
            features['max_mouse_velocity'] = 0
            features['mouse_velocity_variance'] = 0
            features['avg_mouse_acceleration'] = 0
            features['mouse_movement_smoothness'] = 0
            features['mouse_trajectory_complexity'] = 0
        
        # Keyboard behavior features
        keyboard_events = [e for e in data.events if e.type == 'keyboard']
        if keyboard_events:
            dwell_times = [e.dwellTime for e in keyboard_events if e.dwellTime is not None]
            
            features['avg_dwell_time'] = np.mean(dwell_times) if dwell_times else 0
            features['dwell_time_variance'] = np.var(dwell_times) if dwell_times else 0
            features['typing_rhythm_consistency'] = FeatureExtractor.calculate_typing_consistency(dwell_times)
        else:
            features['avg_dwell_time'] = 0
            features['dwell_time_variance'] = 0
            features['typing_rhythm_consistency'] = 0
        
        # Scroll behavior features
        scroll_events = [e for e in data.events if e.type == 'scroll']
        if scroll_events:
            scroll_speeds = [e.scrollSpeed for e in scroll_events if e.scrollSpeed is not None]
            
            features['avg_scroll_speed'] = np.mean(scroll_speeds) if scroll_speeds else 0
            features['scroll_speed_variance'] = np.var(scroll_speeds) if scroll_speeds else 0
            features['scroll_pattern_regularity'] = FeatureExtractor.calculate_scroll_regularity(scroll_events)
        else:
            features['avg_scroll_speed'] = 0
            features['scroll_speed_variance'] = 0
            features['scroll_pattern_regularity'] = 0
        
        # Device fingerprint features
        if data.deviceFingerprint:
            features['fingerprint_consistency'] = 1.0  # Assume consistent for now
            features['has_webgl'] = 1.0 if data.deviceFingerprint.webgl else 0.0
            features['has_audio'] = 1.0 if data.deviceFingerprint.audio else 0.0
            features['screen_resolution'] = data.deviceFingerprint.screen.get('width', 0) * data.deviceFingerprint.screen.get('height', 0)
        else:
            features['fingerprint_consistency'] = 0.0
            features['has_webgl'] = 0.0
            features['has_audio'] = 0.0
            features['screen_resolution'] = 0.0
        
        # TLS fingerprint features
        if data.tlsFingerprint:
            features['tls_protocol_count'] = len(data.tlsFingerprint.get('supportedProtocols', []))
        else:
            features['tls_protocol_count'] = 0.0
        
        # Performance-based features
        performance = data.metadata.get('performanceMetrics', {})
        features['avg_event_collection_time'] = performance.get('eventCollectionTime', 0) / max(1, performance.get('totalEvents', 1))
        features['data_transmission_time'] = performance.get('dataTransmissionTime', 0)
        
        # Time-based patterns
        if len(data.events) > 1:
            timestamps = [e.timestamp for e in data.events]
            intervals = np.diff(timestamps)
            features['avg_event_interval'] = np.mean(intervals)
            features['event_interval_variance'] = np.var(intervals)
            features['temporal_regularity'] = FeatureExtractor.calculate_temporal_regularity(intervals)
        else:
            features['avg_event_interval'] = 0
            features['event_interval_variance'] = 0
            features['temporal_regularity'] = 0
        
        return features
    
    @staticmethod
    def calculate_smoothness(mouse_moves: List[BehavioralEvent]) -> float:
        """Calculate smoothness of mouse movements"""
        if len(mouse_moves) < 3:
            return 0.0
        
        # Calculate curvature at each point
        curvatures = []
        for i in range(1, len(mouse_moves) - 1):
            p1 = (mouse_moves[i-1].x, mouse_moves[i-1].y)
            p2 = (mouse_moves[i].x, mouse_moves[i].y)
            p3 = (mouse_moves[i+1].x, mouse_moves[i+1].y)
            
            # Calculate curvature using three points
            curvature = FeatureExtractor.calculate_curvature(p1, p2, p3)
            curvatures.append(curvature)
        
        # Smoothness is inverse of average curvature
        avg_curvature = np.mean(curvatures) if curvatures else 0
        return 1.0 / (1.0 + avg_curvature)
    
    @staticmethod
    def calculate_curvature(p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float]) -> float:
        """Calculate curvature at p2 given three points"""
        # Vector from p1 to p2
        v1 = (p2[0] - p1[0], p2[1] - p1[1])
        # Vector from p2 to p3
        v2 = (p3[0] - p2[0], p3[1] - p2[1])
        
        # Calculate angle between vectors
        dot_product = v1[0] * v2[0] + v1[1] * v2[1]
        mag1 = (v1[0]**2 + v1[1]**2)**0.5
        mag2 = (v2[0]**2 + v2[1]**2)**0.5
        
        if mag1 == 0 or mag2 == 0:
            return 0.0
        
        cos_angle = dot_product / (mag1 * mag2)
        cos_angle = max(-1.0, min(1.0, cos_angle))  # Clamp to valid range
        
        angle = np.arccos(cos_angle)
        return angle
    
    @staticmethod
    def calculate_trajectory_complexity(mouse_moves: List[BehavioralEvent]) -> float:
        """Calculate complexity of mouse trajectory"""
        if len(mouse_moves) < 2:
            return 0.0
        
        # Calculate total path length
        total_distance = 0.0
        for i in range(1, len(mouse_moves)):
            dx = mouse_moves[i].x - mouse_moves[i-1].x
            dy = mouse_moves[i].y - mouse_moves[i-1].y
            total_distance += (dx**2 + dy**2)**0.5
        
        # Calculate straight-line distance
        start = (mouse_moves[0].x, mouse_moves[0].y)
        end = (mouse_moves[-1].x, mouse_moves[-1].y)
        straight_distance = ((end[0] - start[0])**2 + (end[1] - start[1])**2)**0.5
        
        # Complexity is ratio of path length to straight distance
        if straight_distance == 0:
            return 0.0
        
        return total_distance / straight_distance
    
    @staticmethod
    def calculate_typing_consistency(dwell_times: List[float]) -> float:
        """Calculate consistency of typing rhythm"""
        if len(dwell_times) < 3:
            return 0.0
        
        # Calculate coefficient of variation
        mean_dwell = np.mean(dwell_times)
        if mean_dwell == 0:
            return 0.0
        
        std_dwell = np.std(dwell_times)
        cv = std_dwell / mean_dwell
        
        # Consistency is inverse of coefficient of variation
        return 1.0 / (1.0 + cv)
    
    @staticmethod
    def calculate_scroll_regularity(scroll_events: List[BehavioralEvent]) -> float:
        """Calculate regularity of scroll patterns"""
        if len(scroll_events) < 3:
            return 0.0
        
        speeds = [e.scrollSpeed for e in scroll_events if e.scrollSpeed is not None]
        if len(speeds) < 3:
            return 0.0
        
        # Calculate autocorrelation at lag 1
        speeds_array = np.array(speeds)
        if len(speeds_array) < 2:
            return 0.0
        
        correlation = np.corrcoef(speeds_array[:-1], speeds_array[1:])[0, 1]
        return max(0.0, correlation) if not np.isnan(correlation) else 0.0
    
    @staticmethod
    def calculate_temporal_regularity(intervals: np.ndarray) -> float:
        """Calculate temporal regularity of events"""
        if len(intervals) < 3:
            return 0.0
        
        # Calculate coefficient of variation for intervals
        mean_interval = np.mean(intervals)
        if mean_interval == 0:
            return 0.0
        
        std_interval = np.std(intervals)
        cv = std_interval / mean_interval
        
        # Regularity is inverse of coefficient of variation
        return 1.0 / (1.0 + cv)

class RiskAssessmentEngine:
    """Core risk assessment engine using ML models"""
    
    def __init__(self, components: RiskScoringComponents):
        self.components = components
        self.feature_extractor = FeatureExtractor()
    
    async def assess_risk(self, data: BehavioralDataRequest) -> Tuple[float, float, List[str]]:
        """Assess risk score for behavioral data"""
        start_time = time.time()
        
        try:
            # Extract features
            features = self.feature_extractor.extract_features(data)
            
            # Prepare feature vector for ML models
            feature_names = [
                'session_duration', 'total_events', 'events_per_second',
                'mouse_events', 'keyboard_events', 'scroll_events', 'touch_events',
                'avg_mouse_velocity', 'max_mouse_velocity', 'mouse_velocity_variance',
                'avg_dwell_time', 'dwell_time_variance', 'typing_rhythm_consistency',
                'avg_scroll_speed', 'scroll_speed_variance', 'scroll_pattern_regularity',
                'fingerprint_consistency', 'has_webgl', 'has_audio', 'screen_resolution'
            ]
            
            feature_vector = np.array([[features.get(name, 0.0) for name in feature_names]])
            
            # Scale features
            if 'standard' in self.components.scalers:
                feature_vector = self.components.scalers['standard'].transform(feature_vector)
            
            # Ensemble prediction
            risk_scores = []
            confidences = []
            model_predictions = {}
            
            # Isolation Forest (anomaly detection)
            if 'isolation_forest' in self.components.models:
                anomaly_score = self.components.models['isolation_forest'].decision_function(feature_vector)[0]
                # Convert to 0-1 scale (more negative = more anomalous)
                risk_score_iso = max(0.0, min(1.0, (0.5 - anomaly_score) / 1.0))
                risk_scores.append(risk_score_iso)
                confidences.append(0.7)  # Medium confidence for unsupervised
                model_predictions['isolation_forest'] = risk_score_iso
            
            # Random Forest
            if 'random_forest' in self.components.models:
                rf_proba = self.components.models['random_forest'].predict_proba(feature_vector)[0]
                risk_score_rf = rf_proba[1] if len(rf_proba) > 1 else rf_proba[0]
                risk_scores.append(risk_score_rf)
                confidences.append(0.8)  # High confidence for supervised
                model_predictions['random_forest'] = risk_score_rf
            
            # XGBoost
            if 'xgboost' in self.components.models:
                xgb_proba = self.components.models['xgboost'].predict_proba(feature_vector)[0]
                risk_score_xgb = xgb_proba[1] if len(xgb_proba) > 1 else xgb_proba[0]
                risk_scores.append(risk_score_xgb)
                confidences.append(0.9)  # Highest confidence for gradient boosting
                model_predictions['xgboost'] = risk_score_xgb
            
            # Fallback model
            if not risk_scores and 'fallback' in self.components.models:
                risk_score_fallback = self.components.models['fallback'](features)
                risk_scores.append(risk_score_fallback)
                confidences.append(0.5)  # Low confidence for rule-based
                model_predictions['fallback'] = risk_score_fallback
            
            # Calculate ensemble score (weighted average)
            if risk_scores:
                weights = np.array(confidences)
                weights = weights / weights.sum()  # Normalize weights
                final_risk_score = np.average(risk_scores, weights=weights)
                final_confidence = np.mean(confidences)
            else:
                final_risk_score = 0.5  # Default uncertain score
                final_confidence = 0.1  # Very low confidence
            
            # Generate reasoning
            reasons = self.generate_reasoning(features, model_predictions)
            
            processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            logger.info(f"Risk assessment completed in {processing_time:.2f}ms - Score: {final_risk_score:.3f}")
            
            return final_risk_score, final_confidence, reasons
            
        except Exception as e:
            logger.error(f"Error in risk assessment: {e}")
            return 0.5, 0.1, ["Error in risk assessment - using default score"]
    
    def generate_reasoning(self, features: Dict[str, float], model_predictions: Dict[str, float]) -> List[str]:
        """Generate human-readable reasoning for risk score"""
        reasons = []
        
        # Mouse behavior analysis
        if features.get('mouse_events', 0) == 0:
            reasons.append("No mouse activity detected")
        elif features.get('avg_mouse_velocity', 0) > 500:
            reasons.append("Unusually fast mouse movements")
        elif features.get('mouse_movement_smoothness', 0) < 0.3:
            reasons.append("Jerky or unnatural mouse movements")
        
        # Keyboard behavior analysis
        if features.get('keyboard_events', 0) == 0:
            reasons.append("No keyboard activity detected")
        elif features.get('typing_rhythm_consistency', 0) < 0.2:
            reasons.append("Inconsistent typing patterns")
        elif features.get('avg_dwell_time', 0) < 30:
            reasons.append("Unusually fast typing speed")
        
        # Session behavior analysis
        if features.get('session_duration', 0) < 10:
            reasons.append("Unusually short session duration")
        elif features.get('events_per_second', 0) > 10:
            reasons.append("High event frequency suggests automation")
        
        # Device fingerprint analysis
        if features.get('fingerprint_consistency', 0) == 0:
            reasons.append("Missing or inconsistent device fingerprint")
        elif features.get('has_webgl', 0) == 0 and features.get('has_audio', 0) == 0:
            reasons.append("Limited browser capabilities suggest headless environment")
        
        # Temporal pattern analysis
        if features.get('temporal_regularity', 0) > 0.9:
            reasons.append("Highly regular event timing suggests automation")
        
        # Model-specific insights
        if 'isolation_forest' in model_predictions and model_predictions['isolation_forest'] > 0.7:
            reasons.append("Behavioral pattern identified as anomalous")
        
        if not reasons:
            reasons.append("Normal human-like behavior patterns detected")
        
        return reasons

@app.post("/api/v1/behavioral-data", response_model=RiskAssessmentResponse)
async def assess_behavioral_data(
    request: BehavioralDataRequest,
    background_tasks: BackgroundTasks,
    http_request: Request
):
    """Main endpoint for behavioral data analysis and risk scoring"""
    start_time = time.time()
    
    try:
        # Rate limiting check
        client_ip = http_request.client.host
        session_key = f"session:{request.sessionId}"
        ip_key = f"ip:{client_ip}"
        
        if components.redis_client:
            # Check session rate limit (10 requests per minute)
            session_count = await components.redis_client.get(session_key)
            if session_count and int(session_count) > 10:
                raise HTTPException(status_code=429, detail="Session rate limit exceeded")
            
            # Check IP rate limit (100 requests per minute)
            ip_count = await components.redis_client.get(ip_key)
            if ip_count and int(ip_count) > 100:
                raise HTTPException(status_code=429, detail="IP rate limit exceeded")
            
            # Increment counters
            await components.redis_client.setex(session_key, 60, int(session_count or 0) + 1)
            await components.redis_client.setex(ip_key, 60, int(ip_count or 0) + 1)
        
        # Perform risk assessment
        engine = RiskAssessmentEngine(components)
        risk_score, confidence, reasons = await engine.assess_risk(request)
        
        # Determine actions based on risk score
        actions = determine_actions(risk_score, confidence)
        
        # Store data for model improvement (background task)
        background_tasks.add_task(store_behavioral_data, request, risk_score, confidence)
        
        processing_time = (time.time() - start_time) * 1000
        
        response = RiskAssessmentResponse(
            sessionId=request.sessionId,
            riskScore=risk_score,
            confidence=confidence,
            actions=actions,
            reasons=reasons,
            modelVersion=components.model_version,
            processingTimeMs=processing_time,
            timestamp=datetime.now()
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing behavioral data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

def determine_actions(risk_score: float, confidence: float) -> List[RiskAction]:
    """Determine actions based on risk score and confidence"""
    actions = []
    
    # High confidence thresholds
    if confidence > 0.8:
        if risk_score > 0.8:
            actions.append(RiskAction(type="block", reason="High risk bot behavior detected", confidence=confidence))
        elif risk_score > 0.6:
            actions.append(RiskAction(type="challenge", challengeType="sms", confidence=confidence))
        elif risk_score > 0.4:
            actions.append(RiskAction(type="monitor", level="high", confidence=confidence))
        else:
            actions.append(RiskAction(type="allow", confidence=confidence))
    
    # Medium confidence thresholds (more conservative)
    elif confidence > 0.6:
        if risk_score > 0.9:
            actions.append(RiskAction(type="challenge", challengeType="sms", confidence=confidence))
        elif risk_score > 0.7:
            actions.append(RiskAction(type="monitor", level="high", confidence=confidence))
        elif risk_score > 0.5:
            actions.append(RiskAction(type="monitor", level="medium", confidence=confidence))
        else:
            actions.append(RiskAction(type="allow", confidence=confidence))
    
    # Low confidence - mostly monitoring
    else:
        if risk_score > 0.95:
            actions.append(RiskAction(type="challenge", challengeType="sms", confidence=confidence))
        elif risk_score > 0.5:
            actions.append(RiskAction(type="monitor", level="medium", confidence=confidence))
        else:
            actions.append(RiskAction(type="allow", confidence=confidence))
    
    return actions

async def store_behavioral_data(request: BehavioralDataRequest, risk_score: float, confidence: float):
    """Store behavioral data for model training and analysis"""
    try:
        if components.mongo_client:
            db = components.mongo_client.antibot_security
            collection = db.behavioral_data
            
            document = {
                "sessionId": request.sessionId,
                "timestamp": datetime.now(),
                "deviceFingerprint": request.deviceFingerprint.dict() if request.deviceFingerprint else None,
                "tlsFingerprint": request.tlsFingerprint,
                "eventCount": len(request.events),
                "metadata": request.metadata,
                "riskScore": risk_score,
                "confidence": confidence,
                "modelVersion": components.model_version
            }
            
            await collection.insert_one(document)
            
    except Exception as e:
        logger.error(f"Failed to store behavioral data: {e}")

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "modelVersion": components.model_version,
        "modelsLoaded": list(components.models.keys())
    }

@app.get("/api/v1/metrics")
async def get_metrics():
    """Get performance and system metrics"""
    metrics = {
        "modelVersion": components.model_version,
        "modelsLoaded": list(components.models.keys()),
        "lastModelUpdate": components.last_model_update.isoformat(),
        "systemStatus": "operational"
    }
    
    if components.redis_client:
        try:
            redis_info = await components.redis_client.info()
            metrics["redis"] = {
                "connected": True,
                "usedMemory": redis_info.get("used_memory_human"),
                "connections": redis_info.get("connected_clients")
            }
        except:
            metrics["redis"] = {"connected": False}
    
    return metrics

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")