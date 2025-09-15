"""
Enhanced Risk Scoring Engine for Anti-Bot Security
Production-ready ML pipeline with sub-50ms inference, model versioning, and real-time monitoring
Version 2.0 with comprehensive ML infrastructure
"""

import asyncio
import logging
import time
import os
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
from fastapi.responses import PlainTextResponse
import redis.asyncio as redis
from motor.motor_asyncio import AsyncIOMotorClient
import joblib
from contextlib import asynccontextmanager

# Import enhanced ML components
from .feature_engineering import AdvancedFeatureExtractor, FeatureVector
from .ml_models import AdvancedEnsembleModel, EnsemblePrediction, ModelPrediction
from .model_management import ModelVersionManager, ModelStatus, DeploymentStrategy
from .monitoring import RealTimeMonitor, AlertSeverity, AlertType

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
    featureCount: Optional[int] = None
    modelDetails: Optional[Dict[str, Any]] = None

class ModelTrainingRequest(BaseModel):
    model_name: str
    training_data_path: Optional[str] = None
    deployment_config: Optional[Dict[str, Any]] = None
    auto_promote: bool = False

class EnhancedRiskScoringComponents:
    """Enhanced components with production ML infrastructure"""
    
    def __init__(self):
        # Core infrastructure
        self.redis_client: Optional[redis.Redis] = None
        self.mongo_client: Optional[AsyncIOMotorClient] = None
        
        # Enhanced ML pipeline
        self.feature_extractor: Optional[AdvancedFeatureExtractor] = None
        self.model_manager: Optional[ModelVersionManager] = None
        self.monitor: Optional[RealTimeMonitor] = None
        
        # Configuration
        self.model_version = "2.0.0"
        self.last_model_update = datetime.now()
        self.initialization_complete = False
        
        # Performance tracking
        self.request_count = 0
        self.total_processing_time = 0.0
        self.error_count = 0
        
    async def initialize(self):
        """Initialize enhanced ML infrastructure"""
        try:
            logger.info("Initializing enhanced risk scoring components...")
            
            # Initialize Redis
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            self.redis_client = await redis.from_url(redis_url, decode_responses=True)
            await self.redis_client.ping()
            logger.info("Redis connection established")
            
            # Initialize MongoDB
            mongo_url = os.getenv('MONGODB_URL', 'mongodb://localhost:27017')
            self.mongo_client = AsyncIOMotorClient(mongo_url)
            # Test connection
            await self.mongo_client.admin.command('ping')
            logger.info("MongoDB connection established")
            
            # Initialize advanced feature extractor
            self.feature_extractor = AdvancedFeatureExtractor(self.redis_client)
            logger.info("Advanced feature extractor initialized")
            
            # Initialize model version manager
            models_dir = os.getenv('MODELS_DIR', 'models')
            self.model_manager = ModelVersionManager(models_dir, self.redis_client)
            await self.model_manager.initialize()
            logger.info("Model version manager initialized")
            
            # Initialize real-time monitoring
            self.monitor = RealTimeMonitor(self.redis_client)
            await self.monitor.initialize()
            logger.info("Real-time monitoring initialized")
            
            # Setup initial model if none exists
            await self._ensure_production_model()
            
            self.initialization_complete = True
            logger.info("Enhanced risk scoring components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize enhanced components: {e}")
            self.initialization_complete = False
            raise
    
    async def _ensure_production_model(self):
        """Ensure there's a production model available"""
        try:
            if not self.model_manager.production_version:
                logger.info("No production model found, creating initial model...")
                
                # Generate synthetic training data for initial model
                synthetic_data = self._generate_initial_training_data()
                labels = synthetic_data['label']
                features = synthetic_data.drop(['label', 'session_id'], axis=1)
                
                # Create initial model version
                version_id = await self.model_manager.create_new_version(
                    "risk_scoring_model",
                    features,
                    labels,
                    {"initial_model": True, "synthetic_data": True}
                )
                
                # Stage and deploy the model
                await self.model_manager.update_version_status(version_id, ModelStatus.STAGED)
                await self.model_manager.deploy_to_production(version_id, DeploymentStrategy.BLUE_GREEN)
                
                logger.info(f"Initial production model created: {version_id}")
                
        except Exception as e:
            logger.warning(f"Failed to create initial model: {e}")
    
    def _generate_initial_training_data(self, n_samples: int = 10000) -> pd.DataFrame:
        """Generate synthetic training data for initial model"""
        np.random.seed(42)
        
        data = []
        for i in range(n_samples):
            if i < n_samples * 0.8:  # 80% human-like behavior
                features = {
                    'session_duration': np.random.normal(300, 120),  # 5 minutes avg
                    'total_events': np.random.randint(50, 300),
                    'mouse_events': np.random.randint(20, 150),
                    'keyboard_events': np.random.randint(10, 80),
                    'scroll_events': np.random.randint(5, 30),
                    'avg_mouse_velocity': np.random.normal(150, 50),
                    'avg_dwell_time': np.random.normal(100, 30),
                    'temporal_regularity': np.random.uniform(0.3, 0.8),
                    'mouse_trajectory_complexity': np.random.uniform(1.1, 2.5),
                    'behavioral_diversity': np.random.uniform(0.4, 0.9),
                    'session_id': f'human_{i}',
                    'label': 0
                }
            else:  # 20% bot-like behavior
                features = {
                    'session_duration': np.random.choice([np.random.normal(30, 10), np.random.normal(600, 100)]),
                    'total_events': np.random.choice([np.random.randint(1, 20), np.random.randint(500, 2000)]),
                    'mouse_events': np.random.choice([0, np.random.randint(1000, 5000)]),
                    'keyboard_events': np.random.choice([0, np.random.randint(200, 1000)]),
                    'scroll_events': np.random.randint(0, 5),
                    'avg_mouse_velocity': np.random.choice([0, np.random.normal(500, 100)]),
                    'avg_dwell_time': np.random.choice([np.random.normal(20, 5), np.random.normal(300, 50)]),
                    'temporal_regularity': np.random.choice([np.random.uniform(0.9, 1.0), np.random.uniform(0.0, 0.2)]),
                    'mouse_trajectory_complexity': np.random.choice([1.0, np.random.uniform(5.0, 10.0)]),
                    'behavioral_diversity': np.random.uniform(0.0, 0.3),
                    'session_id': f'bot_{i}',
                    'label': 1
                }
            
            # Ensure positive values
            for key in features:
                if key not in ['session_id', 'label']:
                    features[key] = max(0, features[key])
            
            data.append(features)
        
        return pd.DataFrame(data)
    
    async def shutdown(self):
        """Gracefully shutdown components"""
        try:
            if self.monitor:
                await self.monitor.stop()
            
            if self.redis_client:
                await self.redis_client.close()
            
            if self.mongo_client:
                self.mongo_client.close()
                
            logger.info("Enhanced components shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

# Global components instance
components = EnhancedRiskScoringComponents()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    # Startup
    await components.initialize()
    yield
    # Shutdown
    await components.shutdown()

# Initialize FastAPI app
app = FastAPI(
    title="Enhanced Anti-Bot Risk Scoring Engine",
    description="Production ML pipeline for real-time bot detection with sub-50ms response times",
    version="2.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv('CORS_ORIGINS', '*').split(','),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

class EnhancedRiskAssessmentEngine:
    """Enhanced risk assessment with full ML pipeline"""
    
    def __init__(self, components: EnhancedRiskScoringComponents):
        self.components = components
    
    async def assess_risk(self, data: BehavioralDataRequest) -> Tuple[float, float, List[str], Dict[str, Any]]:
        """Perform comprehensive risk assessment"""
        start_time = time.time()
        
        try:
            # Validate components are initialized
            if not self.components.initialization_complete:
                raise RuntimeError("ML pipeline not fully initialized")
            
            # Convert request to feature extraction format
            data_dict = {
                'sessionId': data.sessionId,
                'events': [event.dict() for event in data.events],
                'deviceFingerprint': data.deviceFingerprint.dict() if data.deviceFingerprint else None,
                'tlsFingerprint': data.tlsFingerprint,
                'metadata': data.metadata,
                'sessionDuration': data.metadata.get('sessionDuration', time.time() - data.events[0].timestamp if data.events else 0),
                'pageUrl': data.metadata.get('pageUrl', ''),
                'referrer': data.metadata.get('referrer', '')
            }
            
            # Extract advanced features
            feature_vector = await self.components.feature_extractor.extract_features_async(data_dict)
            
            # Get appropriate model for prediction (handles A/B testing, canary deployments)
            model, model_version = await self.components.model_manager.get_model_for_prediction(data.sessionId)
            
            # Prepare features for model
            feature_names = feature_vector.feature_names
            features_array = np.array([list(feature_vector.features.values())])
            
            # Get ensemble prediction
            ensemble_prediction = await model.predict_risk(features_array, feature_names)
            
            # Log prediction for monitoring and model improvement
            await self.components.monitor.log_prediction(
                model_version, feature_vector, ensemble_prediction
            )
            
            # Store prediction for model versioning
            await self.components.model_manager.log_prediction_result(
                model_version, ensemble_prediction, session_metadata=data.metadata
            )
            
            # Generate detailed reasoning
            reasons = self._generate_detailed_reasoning(
                feature_vector.features, 
                ensemble_prediction.individual_predictions
            )
            
            # Create model details for response
            model_details = {
                "model_version": model_version,
                "ensemble_method": ensemble_prediction.ensemble_method,
                "feature_count": len(feature_vector.features),
                "feature_confidence": feature_vector.confidence,
                "models_used": [pred.model_name for pred in ensemble_prediction.individual_predictions],
                "individual_scores": {
                    pred.model_name: pred.risk_score 
                    for pred in ensemble_prediction.individual_predictions
                }
            }
            
            processing_time = (time.time() - start_time) * 1000
            
            # Update component metrics
            self.components.request_count += 1
            self.components.total_processing_time += processing_time
            
            logger.info(f"Enhanced risk assessment completed in {processing_time:.2f}ms - Score: {ensemble_prediction.final_risk_score:.3f}")
            
            return ensemble_prediction.final_risk_score, ensemble_prediction.final_confidence, reasons, model_details
            
        except Exception as e:
            logger.error(f"Enhanced risk assessment failed: {e}")
            self.components.error_count += 1
            
            # Fallback assessment
            return await self._fallback_assessment(data, start_time)
    
    async def _fallback_assessment(self, data: BehavioralDataRequest, start_time: float) -> Tuple[float, float, List[str], Dict[str, Any]]:
        """Simple fallback risk assessment"""
        try:
            # Simple heuristic-based assessment
            risk_score = 0.0
            
            # Check for basic suspicious patterns
            if len(data.events) == 0:
                risk_score += 0.5
            
            mouse_events = len([e for e in data.events if e.type == 'mouse'])
            keyboard_events = len([e for e in data.events if e.type == 'keyboard'])
            
            if mouse_events == 0:
                risk_score += 0.3
            if keyboard_events == 0:
                risk_score += 0.3
            
            session_duration = data.metadata.get('sessionDuration', 0)
            if session_duration < 10:
                risk_score += 0.2
            
            risk_score = min(1.0, risk_score)
            confidence = 0.3  # Low confidence for fallback
            
            reasons = ["Fallback assessment due to ML pipeline error"]
            if risk_score > 0.5:
                reasons.append("Basic heuristics indicate suspicious behavior")
            
            model_details = {
                "model_version": "fallback_1.0",
                "ensemble_method": "heuristic",
                "feature_count": 3,
                "models_used": ["fallback"]
            }
            
            processing_time = (time.time() - start_time) * 1000
            
            return risk_score, confidence, reasons, model_details
            
        except Exception as e:
            logger.error(f"Fallback assessment also failed: {e}")
            return 0.5, 0.1, ["Assessment failed - default uncertain score"], {"error": str(e)}
    
    def _generate_detailed_reasoning(self, features: Dict[str, float], 
                                   individual_predictions: List[ModelPrediction]) -> List[str]:
        """Generate detailed reasoning for risk assessment"""
        reasons = []
        
        # Analyze model consensus
        risk_scores = [pred.risk_score for pred in individual_predictions]
        if len(risk_scores) > 1:
            score_variance = np.var(risk_scores)
            if score_variance < 0.01:
                reasons.append("High consensus among ML models")
            elif score_variance > 0.1:
                reasons.append("Models show disagreement - assessment uncertainty")
        
        # Feature-based analysis
        mouse_events = features.get('mouse_event_count', 0)
        keyboard_events = features.get('keyboard_event_count', 0)
        session_duration = features.get('session_duration', 0)
        
        if mouse_events == 0:
            reasons.append("No mouse activity detected")
        elif mouse_events > 1000:
            reasons.append("Unusually high mouse activity")
        
        if keyboard_events == 0:
            reasons.append("No keyboard activity detected")
        elif features.get('keyboard_typing_rhythm_consistency', 0) < 0.2:
            reasons.append("Inconsistent typing patterns suggest automation")
        
        if session_duration < 10:
            reasons.append("Extremely short session duration")
        elif session_duration > 3600:
            reasons.append("Unusually long session duration")
        
        # Advanced behavioral analysis
        behavioral_diversity = features.get('behavioral_diversity', 0)
        if behavioral_diversity < 0.2:
            reasons.append("Limited behavioral diversity indicates automation")
        
        temporal_regularity = features.get('temporal_regularity', 0)
        if temporal_regularity > 0.9:
            reasons.append("Highly regular timing patterns suggest scripted behavior")
        
        mouse_complexity = features.get('mouse_trajectory_complexity', 1.0)
        if mouse_complexity < 1.1:
            reasons.append("Mouse movements too simple and direct")
        elif mouse_complexity > 5.0:
            reasons.append("Mouse movements unusually complex")
        
        # Model-specific insights
        for pred in individual_predictions:
            if pred.model_name == 'xgboost' and pred.risk_score > 0.8:
                reasons.append("Gradient boosting model detected high-risk behavioral patterns")
            elif pred.model_name == 'isolation_forest' and pred.risk_score > 0.7:
                reasons.append("Anomaly detection flagged unusual behavior compared to baseline")
            elif pred.model_name == 'pytorch' and pred.risk_score > 0.8:
                reasons.append("Neural network identified complex automation signatures")
            elif pred.model_name == 'random_forest' and pred.risk_score > 0.8:
                reasons.append("Ensemble decision trees indicate bot-like behavior")
        
        # Device and network analysis
        if features.get('has_device_fingerprint', 0) == 0:
            reasons.append("Missing device fingerprint suggests headless environment")
        
        if features.get('has_webgl', 0) == 0 and features.get('has_audio_fingerprint', 0) == 0:
            reasons.append("Limited browser capabilities consistent with automation")
        
        # Positive indicators
        if not reasons or all('no' in reason.lower() or 'missing' in reason.lower() for reason in reasons):
            if features.get('mouse_movement_smoothness', 0) > 0.7:
                reasons.append("Natural mouse movement patterns detected")
            if features.get('keyboard_typing_rhythm_consistency', 0) > 0.6:
                reasons.append("Human-like typing rhythm observed")
            if behavioral_diversity > 0.5:
                reasons.append("Diverse behavioral patterns indicate human interaction")
        
        if not reasons:
            reasons.append("Normal human-like behavior patterns detected")
        
        return reasons

def determine_actions(risk_score: float, confidence: float, model_details: Dict[str, Any] = None) -> List[RiskAction]:
    """Enhanced action determination with model-aware thresholds"""
    actions = []
    
    # Adjust thresholds based on model confidence and type
    base_block_threshold = 0.8
    base_challenge_threshold = 0.6
    base_monitor_threshold = 0.4
    
    # Adjust thresholds based on confidence
    if confidence > 0.9:
        # High confidence - use standard thresholds
        block_threshold = base_block_threshold
        challenge_threshold = base_challenge_threshold
        monitor_threshold = base_monitor_threshold
    elif confidence > 0.7:
        # Medium confidence - be more conservative
        block_threshold = base_block_threshold + 0.1
        challenge_threshold = base_challenge_threshold + 0.1
        monitor_threshold = base_monitor_threshold
    else:
        # Low confidence - be very conservative
        block_threshold = 0.95
        challenge_threshold = base_challenge_threshold + 0.2
        monitor_threshold = base_monitor_threshold + 0.1
    
    # Determine primary action
    if risk_score >= block_threshold:
        actions.append(RiskAction(
            type="block",
            reason=f"High risk score ({risk_score:.3f}) with {confidence:.1%} confidence",
            confidence=confidence
        ))
    elif risk_score >= challenge_threshold:
        # Choose challenge type based on risk level
        challenge_type = "captcha" if risk_score < 0.75 else "sms"
        actions.append(RiskAction(
            type="challenge",
            challengeType=challenge_type,
            reason=f"Moderate risk score ({risk_score:.3f}) requires verification",
            confidence=confidence
        ))
    elif risk_score >= monitor_threshold:
        monitor_level = "high" if risk_score > 0.5 else "medium"
        actions.append(RiskAction(
            type="monitor",
            level=monitor_level,
            reason=f"Elevated risk score ({risk_score:.3f}) requires monitoring",
            confidence=confidence
        ))
    else:
        actions.append(RiskAction(
            type="allow",
            reason=f"Low risk score ({risk_score:.3f}) indicates human behavior",
            confidence=confidence
        ))
    
    return actions

@app.post("/api/v1/behavioral-data", response_model=RiskAssessmentResponse)
async def assess_behavioral_data(
    request: BehavioralDataRequest,
    background_tasks: BackgroundTasks,
    http_request: Request
):
    """Enhanced endpoint for behavioral data analysis and risk scoring"""
    start_time = time.time()
    
    try:
        # Rate limiting check
        client_ip = http_request.client.host
        session_key = f"session:{request.sessionId}"
        ip_key = f"ip:{client_ip}"
        
        if components.redis_client:
            # Enhanced rate limiting with different limits for different risk levels
            session_count = await components.redis_client.get(session_key)
            if session_count and int(session_count) > 20:  # Increased limit
                raise HTTPException(status_code=429, detail="Session rate limit exceeded")
            
            ip_count = await components.redis_client.get(ip_key)
            if ip_count and int(ip_count) > 200:  # Increased limit for production
                raise HTTPException(status_code=429, detail="IP rate limit exceeded")
            
            # Increment counters with exponential backoff
            await components.redis_client.setex(session_key, 60, int(session_count or 0) + 1)
            await components.redis_client.setex(ip_key, 60, int(ip_count or 0) + 1)
        
        # Perform enhanced risk assessment
        engine = EnhancedRiskAssessmentEngine(components)
        risk_score, confidence, reasons, model_details = await engine.assess_risk(request)
        
        # Determine actions with enhanced logic
        actions = determine_actions(risk_score, confidence, model_details)
        
        # Store behavioral data for continuous learning (background task)
        background_tasks.add_task(store_behavioral_data, request, risk_score, confidence, model_details)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Enhanced response with model details
        response = RiskAssessmentResponse(
            sessionId=request.sessionId,
            riskScore=risk_score,
            confidence=confidence,
            actions=actions,
            reasons=reasons,
            modelVersion=model_details.get("model_version", components.model_version),
            processingTimeMs=processing_time,
            timestamp=datetime.now(),
            featureCount=model_details.get("feature_count"),
            modelDetails=model_details
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing behavioral data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def store_behavioral_data(request: BehavioralDataRequest, risk_score: float, 
                              confidence: float, model_details: Dict[str, Any]):
    """Enhanced data storage for continuous learning"""
    try:
        if components.mongo_client:
            db = components.mongo_client.antibot_security
            collection = db.behavioral_data_v2
            
            document = {
                "sessionId": request.sessionId,
                "timestamp": datetime.now(),
                "deviceFingerprint": request.deviceFingerprint.dict() if request.deviceFingerprint else None,
                "tlsFingerprint": request.tlsFingerprint,
                "eventCount": len(request.events),
                "eventTypes": list(set(event.type for event in request.events)),
                "metadata": request.metadata,
                "riskScore": risk_score,
                "confidence": confidence,
                "modelVersion": model_details.get("model_version"),
                "modelDetails": model_details,
                "feature_count": model_details.get("feature_count", 0)
            }
            
            await collection.insert_one(document)
            
    except Exception as e:
        logger.error(f"Failed to store behavioral data: {e}")

# Enhanced API endpoints
@app.get("/api/v1/health")
async def health_check():
    """Enhanced health check with detailed status"""
    health_status = {
        "status": "healthy" if components.initialization_complete else "initializing",
        "timestamp": datetime.now().isoformat(),
        "modelVersion": components.model_version,
        "uptime_seconds": (datetime.now() - components.last_model_update).total_seconds(),
        "requests_processed": components.request_count,
        "avg_processing_time_ms": (
            components.total_processing_time / components.request_count 
            if components.request_count > 0 else 0
        ),
        "error_rate": (
            components.error_count / components.request_count 
            if components.request_count > 0 else 0
        )
    }
    
    # Add component status
    if components.initialization_complete:
        health_status.update({
            "components": {
                "feature_extractor": "active",
                "model_manager": "active",
                "monitor": "active",
                "redis": "connected" if components.redis_client else "disconnected",
                "mongodb": "connected" if components.mongo_client else "disconnected"
            }
        })
        
        # Add model status
        if components.model_manager:
            health_status["model_status"] = {
                "production_version": components.model_manager.production_version,
                "active_models": len(components.model_manager.active_models),
                "active_ab_tests": len(components.model_manager.active_ab_tests)
            }
    
    return health_status

@app.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    if components.initialization_complete and components.monitor:
        try:
            return components.monitor.get_prometheus_metrics()
        except Exception as e:
            logger.error(f"Failed to get Prometheus metrics: {e}")
            return f"# Error generating metrics: {e}\\n"
    else:
        return "# Service not ready\\n"

@app.get("/api/v1/dashboard")
async def monitoring_dashboard():
    """Real-time monitoring dashboard data"""
    if components.initialization_complete and components.monitor:
        try:
            return await components.monitor.get_monitoring_dashboard_data()
        except Exception as e:
            logger.error(f"Failed to get dashboard data: {e}")
            return {"error": str(e)}
    else:
        return {"error": "Monitoring not available"}

@app.get("/api/v1/model-versions")
async def get_model_versions():
    """Get comprehensive model version information"""
    if components.initialization_complete and components.model_manager:
        try:
            versions_info = {}
            for version_id, version in components.model_manager.versions.items():
                # Get recent performance metrics
                performance = await components.model_manager.get_model_performance(version_id, hours=24)
                
                versions_info[version_id] = {
                    "model_name": version.model_name,
                    "version_number": version.version_number,
                    "status": version.status.value,
                    "created_at": version.created_at.isoformat(),
                    "performance_metrics": version.performance_metrics,
                    "recent_performance": performance,
                    "deployment_config": version.deployment_config
                }
            
            return {
                "production_version": components.model_manager.production_version,
                "staged_version": components.model_manager.staged_version,
                "total_versions": len(versions_info),
                "versions": versions_info,
                "active_ab_tests": {
                    test_id: {
                        "name": test.name,
                        "description": test.description,
                        "model_a": test.model_a_version,
                        "model_b": test.model_b_version,
                        "traffic_split": test.traffic_split,
                        "start_time": test.start_time.isoformat(),
                        "end_time": test.end_time.isoformat(),
                        "is_active": test.is_active
                    }
                    for test_id, test in components.model_manager.active_ab_tests.items()
                },
                "ab_test_results": {
                    test_id: {
                        "model_a_metrics": result.model_a_metrics,
                        "model_b_metrics": result.model_b_metrics,
                        "sample_size_a": result.sample_size_a,
                        "sample_size_b": result.sample_size_b,
                        "statistical_significance": result.statistical_significance,
                        "winner": result.winner,
                        "confidence_level": result.confidence_level
                    }
                    for test_id, result in components.model_manager.ab_test_results.items()
                }
            }
        except Exception as e:
            logger.error(f"Failed to get model versions: {e}")
            return {"error": str(e)}
    else:
        return {"error": "Model management not available"}

@app.post("/api/v1/train-model")
async def train_new_model(request: ModelTrainingRequest, background_tasks: BackgroundTasks):
    """Train a new model version"""
    if components.initialization_complete and components.model_manager:
        try:
            # Start training in background
            background_tasks.add_task(
                _train_model_background,
                request.model_name,
                request.training_data_path,
                request.deployment_config,
                request.auto_promote
            )
            
            return {
                "success": True,
                "message": f"Model training started for {request.model_name}",
                "training_id": hashlib.md5(f"{request.model_name}_{datetime.now()}".encode()).hexdigest()[:16]
            }
            
        except Exception as e:
            logger.error(f"Failed to start model training: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    else:
        raise HTTPException(status_code=503, detail="Model management not available")

async def _train_model_background(model_name: str, training_data_path: Optional[str],
                                deployment_config: Optional[Dict[str, Any]], auto_promote: bool):
    """Background task for model training"""
    try:
        # Generate training data (in production, this would load from training_data_path)
        training_data = components._generate_initial_training_data(50000)
        labels = training_data['label']
        features = training_data.drop(['label', 'session_id'], axis=1)
        
        # Create new model version
        version_id = await components.model_manager.create_new_version(
            model_name,
            features,
            labels,
            deployment_config or {}
        )
        
        logger.info(f"Model training completed: {version_id}")
        
        # Auto-promote if requested
        if auto_promote:
            success = await components.model_manager.auto_promote_model(version_id)
            if success:
                logger.info(f"Model {version_id} auto-promoted to production")
            else:
                logger.info(f"Model {version_id} did not meet auto-promotion criteria")
        
    except Exception as e:
        logger.error(f"Background model training failed: {e}")

@app.post("/api/v1/model-versions/{version_id}/promote")
async def promote_model_version(version_id: str, strategy: str = "blue_green"):
    """Promote a model version to production"""
    if components.initialization_complete and components.model_manager:
        try:
            # Map string to enum
            strategy_map = {
                "blue_green": DeploymentStrategy.BLUE_GREEN,
                "canary": DeploymentStrategy.CANARY,
                "ab_test": DeploymentStrategy.AB_TEST,
                "rolling": DeploymentStrategy.ROLLING
            }
            
            deployment_strategy = strategy_map.get(strategy, DeploymentStrategy.BLUE_GREEN)
            
            # Stage the version first
            await components.model_manager.update_version_status(version_id, ModelStatus.STAGED)
            
            # Deploy to production
            await components.model_manager.deploy_to_production(version_id, deployment_strategy)
            
            return {
                "success": True,
                "message": f"Model version {version_id} promoted to production using {strategy}",
                "production_version": version_id,
                "deployment_strategy": strategy
            }
            
        except Exception as e:
            logger.error(f"Failed to promote model version: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    else:
        raise HTTPException(status_code=503, detail="Model management not available")

@app.post("/api/v1/rollback")
async def rollback_model(target_version: Optional[str] = None):
    """Rollback to previous or specified model version"""
    if components.initialization_complete and components.model_manager:
        try:
            rollback_version = await components.model_manager.rollback_version(target_version)
            
            return {
                "success": True,
                "message": f"Successfully rolled back to version {rollback_version}",
                "production_version": rollback_version,
                "rollback_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to rollback model: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    else:
        raise HTTPException(status_code=503, detail="Model management not available")

@app.get("/api/v1/performance/{version_id}")
async def get_model_performance(version_id: str, hours: int = 24):
    """Get detailed performance metrics for a model version"""
    if components.initialization_complete and components.model_manager:
        try:
            performance = await components.model_manager.get_model_performance(version_id, hours)
            return performance
            
        except Exception as e:
            logger.error(f"Failed to get model performance: {e}")
            return {"error": str(e)}
    else:
        return {"error": "Model management not available"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")