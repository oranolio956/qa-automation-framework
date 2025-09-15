"""
Machine Learning Model Monitoring and Feedback Loop System
Real-time model performance tracking, drift detection, and automated retraining triggers
"""

import asyncio
import json
import logging
import time
import pickle
import hashlib
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_auc_score
from sklearn.model_selection import train_test_split
import redis.asyncio as redis
import aiohttp
import joblib
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, push_to_gateway
from collections import defaultdict, deque
import signal
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ModelStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    RETRAINING = "retraining"
    FAILED = "failed"

class DriftType(Enum):
    FEATURE_DRIFT = "feature_drift"
    PREDICTION_DRIFT = "prediction_drift"
    CONCEPT_DRIFT = "concept_drift"
    PERFORMANCE_DRIFT = "performance_drift"

@dataclass
class ModelPerformanceSnapshot:
    """Model performance metrics snapshot"""
    timestamp: datetime
    model_version: str
    model_name: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    auc_score: float
    false_positive_rate: float
    false_negative_rate: float
    prediction_latency_p50: float
    prediction_latency_p95: float
    prediction_latency_p99: float
    throughput_rps: float
    drift_scores: Dict[str, float]
    feature_importance: Dict[str, float]
    prediction_confidence: float
    data_quality_score: float

@dataclass
class ModelDriftAlert:
    """Model drift detection alert"""
    id: str
    model_version: str
    model_name: str
    drift_type: DriftType
    drift_score: float
    threshold: float
    timestamp: datetime
    affected_features: List[str]
    recommended_actions: List[str]
    severity: str

class StatisticalDriftDetector:
    """Advanced statistical drift detection using multiple methods"""
    
    def __init__(self, reference_window_size: int = 10000):
        self.reference_window_size = reference_window_size
        self.reference_distributions = {}
        self.detection_windows = defaultdict(lambda: deque(maxlen=1000))
        
    def update_reference_distribution(self, feature_name: str, values: np.ndarray):
        """Update reference distribution for a feature"""
        self.reference_distributions[feature_name] = {
            'mean': np.mean(values),
            'std': np.std(values),
            'min': np.min(values),
            'max': np.max(values),
            'percentiles': np.percentile(values, [25, 50, 75, 90, 95, 99])
        }
    
    def detect_drift(self, feature_name: str, new_values: np.ndarray, method: str = 'ks_test') -> Tuple[float, bool]:
        """Detect drift using specified statistical method"""
        if feature_name not in self.reference_distributions:
            return 0.0, False
        
        ref_dist = self.reference_distributions[feature_name]
        
        if method == 'ks_test':
            return self._kolmogorov_smirnov_test(ref_dist, new_values)
        elif method == 'psi':
            return self._population_stability_index(ref_dist, new_values)
        elif method == 'wasserstein':
            return self._wasserstein_distance(ref_dist, new_values)
        else:
            return self._statistical_distance(ref_dist, new_values)
    
    def _kolmogorov_smirnov_test(self, ref_dist: Dict, new_values: np.ndarray) -> Tuple[float, bool]:
        """Kolmogorov-Smirnov test for distribution comparison"""
        try:
            from scipy import stats
            
            # Generate reference samples from stored statistics
            ref_samples = np.random.normal(ref_dist['mean'], ref_dist['std'], len(new_values))
            
            # Perform KS test
            statistic, p_value = stats.ks_2samp(ref_samples, new_values)
            
            # Convert to drift score (higher = more drift)
            drift_score = statistic
            is_drifted = p_value < 0.05
            
            return drift_score, is_drifted
            
        except ImportError:
            # Fallback to simple statistical comparison
            return self._statistical_distance(ref_dist, new_values)
    
    def _population_stability_index(self, ref_dist: Dict, new_values: np.ndarray) -> Tuple[float, bool]:
        """Population Stability Index calculation"""
        try:
            # Create bins based on reference percentiles
            bins = [-np.inf] + list(ref_dist['percentiles']) + [np.inf]
            
            # Calculate proportions for reference (uniform across percentiles)
            ref_proportions = np.array([0.25, 0.25, 0.25, 0.05, 0.04, 0.01, 0.15])
            
            # Calculate proportions for new data
            hist, _ = np.histogram(new_values, bins=bins)
            new_proportions = hist / len(new_values)
            
            # Avoid division by zero
            new_proportions = np.maximum(new_proportions, 1e-6)
            ref_proportions = np.maximum(ref_proportions, 1e-6)
            
            # Calculate PSI
            psi = np.sum((new_proportions - ref_proportions) * np.log(new_proportions / ref_proportions))
            
            # PSI thresholds: <0.1 (no drift), 0.1-0.2 (moderate), >0.2 (significant)
            is_drifted = psi > 0.2
            
            return psi, is_drifted
            
        except Exception as e:
            logger.warning(f"PSI calculation failed: {e}")
            return self._statistical_distance(ref_dist, new_values)
    
    def _wasserstein_distance(self, ref_dist: Dict, new_values: np.ndarray) -> Tuple[float, bool]:
        """Earth Mover's Distance (Wasserstein distance) calculation"""
        try:
            from scipy import stats
            
            ref_samples = np.random.normal(ref_dist['mean'], ref_dist['std'], len(new_values))
            distance = stats.wasserstein_distance(ref_samples, new_values)
            
            # Normalize distance by reference standard deviation
            normalized_distance = distance / (ref_dist['std'] + 1e-6)
            
            is_drifted = normalized_distance > 0.5
            
            return normalized_distance, is_drifted
            
        except ImportError:
            return self._statistical_distance(ref_dist, new_values)
    
    def _statistical_distance(self, ref_dist: Dict, new_values: np.ndarray) -> Tuple[float, bool]:
        """Simple statistical distance calculation as fallback"""
        new_mean = np.mean(new_values)
        new_std = np.std(new_values)
        
        # Calculate normalized differences
        mean_diff = abs(new_mean - ref_dist['mean']) / (ref_dist['std'] + 1e-6)
        std_ratio = abs(new_std - ref_dist['std']) / (ref_dist['std'] + 1e-6)
        
        # Combined drift score
        drift_score = mean_diff + std_ratio
        is_drifted = drift_score > 1.0
        
        return drift_score, is_drifted

class ModelPerformanceTracker:
    """Track and analyze model performance over time"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.drift_detector = StatisticalDriftDetector()
        self.performance_history = defaultdict(list)
        self.model_configs = {}
        
        # Performance thresholds
        self.performance_thresholds = {
            'accuracy_min': 0.90,
            'precision_min': 0.85,
            'recall_min': 0.80,
            'f1_min': 0.82,
            'auc_min': 0.85,
            'latency_p95_max': 100.0,  # milliseconds
            'throughput_min': 50.0     # requests per second
        }
        
        # Drift thresholds
        self.drift_thresholds = {
            'feature_drift': 0.3,
            'prediction_drift': 0.2,
            'performance_drift': 0.15
        }
        
    async def initialize_model_tracking(self, model_name: str, model_version: str, config: Dict[str, Any]):
        """Initialize tracking for a new model"""
        try:
            model_key = f"{model_name}:{model_version}"
            self.model_configs[model_key] = config
            
            # Initialize reference data
            await self._initialize_reference_data(model_name, model_version)
            
            logger.info(f"Initialized tracking for model {model_key}")
            
        except Exception as e:
            logger.error(f"Failed to initialize model tracking: {e}")
    
    async def _initialize_reference_data(self, model_name: str, model_version: str):
        """Initialize reference data distributions for drift detection"""
        try:
            # Load reference data from Redis or file system
            ref_key = f"model_reference:{model_name}:{model_version}"
            reference_data = await self.redis_client.get(ref_key)
            
            if reference_data:
                ref_dict = json.loads(reference_data)
                
                for feature_name, values in ref_dict.items():
                    self.drift_detector.update_reference_distribution(
                        f"{model_name}_{feature_name}",
                        np.array(values)
                    )
                    
                logger.info(f"Loaded reference data for {model_name}:{model_version}")
            else:
                logger.warning(f"No reference data found for {model_name}:{model_version}")
                
        except Exception as e:
            logger.error(f"Failed to initialize reference data: {e}")
    
    async def record_prediction_batch(self, model_name: str, model_version: str, 
                                    predictions: List[Dict[str, Any]], actuals: List[bool] = None):
        """Record a batch of predictions for performance tracking"""
        try:
            timestamp = datetime.now()
            model_key = f"{model_name}:{model_version}"
            
            # Extract metrics from predictions
            risk_scores = [p.get('risk_score', 0.0) for p in predictions]
            confidences = [p.get('confidence', 0.0) for p in predictions]
            latencies = [p.get('latency_ms', 0.0) for p in predictions]
            feature_data = [p.get('features', {}) for p in predictions]
            
            # Calculate performance metrics
            if actuals and len(actuals) == len(predictions):
                predicted_labels = [1 if score > 0.5 else 0 for score in risk_scores]
                
                accuracy = accuracy_score(actuals, predicted_labels)
                precision, recall, f1, _ = precision_recall_fscore_support(
                    actuals, predicted_labels, average='binary', zero_division=0
                )
                
                try:
                    auc = roc_auc_score(actuals, risk_scores)
                except ValueError:
                    auc = 0.5  # If all same class
                
                # Calculate FPR and FNR
                tp = sum(1 for a, p in zip(actuals, predicted_labels) if a == 1 and p == 1)
                fp = sum(1 for a, p in zip(actuals, predicted_labels) if a == 0 and p == 1)
                fn = sum(1 for a, p in zip(actuals, predicted_labels) if a == 1 and p == 0)
                tn = sum(1 for a, p in zip(actuals, predicted_labels) if a == 0 and p == 0)
                
                fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
                fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
            else:
                # No ground truth available
                accuracy = precision = recall = f1 = auc = 0.0
                fpr = fnr = 0.0
            
            # Calculate latency percentiles
            if latencies:
                latency_p50 = np.percentile(latencies, 50)
                latency_p95 = np.percentile(latencies, 95)
                latency_p99 = np.percentile(latencies, 99)
            else:
                latency_p50 = latency_p95 = latency_p99 = 0.0
            
            # Calculate throughput
            throughput = len(predictions) / max(sum(latencies) / 1000, 1.0)  # RPS
            
            # Detect feature drift
            drift_scores = {}
            if feature_data:
                feature_names = set()
                for features in feature_data:
                    feature_names.update(features.keys())
                
                for feature_name in feature_names:
                    feature_values = []
                    for features in feature_data:
                        if feature_name in features:
                            feature_values.append(features[feature_name])
                    
                    if feature_values and len(feature_values) > 10:
                        drift_key = f"{model_name}_{feature_name}"
                        drift_score, is_drifted = self.drift_detector.detect_drift(
                            drift_key, np.array(feature_values)
                        )
                        drift_scores[feature_name] = drift_score
            
            # Calculate feature importance (simplified)
            feature_importance = {}
            if feature_data and actuals:
                for feature_name in feature_names:
                    # Simple correlation-based importance
                    feature_values = []
                    for features in feature_data:
                        if feature_name in features:
                            feature_values.append(features[feature_name])
                    
                    if len(feature_values) == len(actuals):
                        corr = np.corrcoef(feature_values, actuals)[0, 1]
                        feature_importance[feature_name] = abs(corr) if not np.isnan(corr) else 0.0
            
            # Create performance snapshot
            snapshot = ModelPerformanceSnapshot(
                timestamp=timestamp,
                model_version=model_version,
                model_name=model_name,
                accuracy=accuracy,
                precision=precision,
                recall=recall,
                f1_score=f1,
                auc_score=auc,
                false_positive_rate=fpr,
                false_negative_rate=fnr,
                prediction_latency_p50=latency_p50,
                prediction_latency_p95=latency_p95,
                prediction_latency_p99=latency_p99,
                throughput_rps=throughput,
                drift_scores=drift_scores,
                feature_importance=feature_importance,
                prediction_confidence=np.mean(confidences) if confidences else 0.0,
                data_quality_score=self._calculate_data_quality_score(feature_data)
            )
            
            # Store snapshot
            await self._store_performance_snapshot(snapshot)
            
            # Check for alerts
            await self._check_performance_alerts(snapshot)
            
            logger.info(f"Recorded performance for {model_key}: "
                       f"accuracy={accuracy:.3f}, latency_p95={latency_p95:.1f}ms")
            
        except Exception as e:
            logger.error(f"Failed to record prediction batch: {e}")
    
    def _calculate_data_quality_score(self, feature_data: List[Dict[str, Any]]) -> float:
        """Calculate data quality score based on completeness and validity"""
        if not feature_data:
            return 0.0
        
        try:
            total_fields = 0
            valid_fields = 0
            
            for features in feature_data:
                for value in features.values():
                    total_fields += 1
                    if value is not None and not np.isnan(float(value)) and np.isfinite(float(value)):
                        valid_fields += 1
            
            return valid_fields / total_fields if total_fields > 0 else 0.0
            
        except Exception as e:
            logger.warning(f"Data quality calculation failed: {e}")
            return 0.5  # Default neutral score
    
    async def _store_performance_snapshot(self, snapshot: ModelPerformanceSnapshot):
        """Store performance snapshot in Redis"""
        try:
            # Store latest snapshot
            snapshot_key = f"model_performance:{snapshot.model_name}:{snapshot.model_version}:latest"
            await self.redis_client.set(
                snapshot_key,
                json.dumps(asdict(snapshot), default=str),
                ex=86400  # 24 hours
            )
            
            # Store in time series
            ts_key = f"model_performance_ts:{snapshot.model_name}:{snapshot.model_version}"
            await self.redis_client.lpush(
                ts_key,
                json.dumps(asdict(snapshot), default=str)
            )
            await self.redis_client.ltrim(ts_key, 0, 999)  # Keep last 1000 snapshots
            await self.redis_client.expire(ts_key, 604800)  # 7 days
            
        except Exception as e:
            logger.error(f"Failed to store performance snapshot: {e}")
    
    async def _check_performance_alerts(self, snapshot: ModelPerformanceSnapshot):
        """Check performance metrics against thresholds and create alerts"""
        try:
            alerts = []
            
            # Check accuracy threshold
            if snapshot.accuracy < self.performance_thresholds['accuracy_min']:
                alerts.append({
                    'type': 'performance_degradation',
                    'metric': 'accuracy',
                    'value': snapshot.accuracy,
                    'threshold': self.performance_thresholds['accuracy_min'],
                    'severity': 'critical' if snapshot.accuracy < 0.8 else 'warning'
                })
            
            # Check precision threshold
            if snapshot.precision < self.performance_thresholds['precision_min']:
                alerts.append({
                    'type': 'performance_degradation',
                    'metric': 'precision',
                    'value': snapshot.precision,
                    'threshold': self.performance_thresholds['precision_min'],
                    'severity': 'warning'
                })
            
            # Check latency threshold
            if snapshot.prediction_latency_p95 > self.performance_thresholds['latency_p95_max']:
                alerts.append({
                    'type': 'performance_degradation',
                    'metric': 'latency_p95',
                    'value': snapshot.prediction_latency_p95,
                    'threshold': self.performance_thresholds['latency_p95_max'],
                    'severity': 'warning' if snapshot.prediction_latency_p95 < 200 else 'critical'
                })
            
            # Check throughput threshold
            if snapshot.throughput_rps < self.performance_thresholds['throughput_min']:
                alerts.append({
                    'type': 'performance_degradation',
                    'metric': 'throughput',
                    'value': snapshot.throughput_rps,
                    'threshold': self.performance_thresholds['throughput_min'],
                    'severity': 'warning'
                })
            
            # Check drift scores
            for feature_name, drift_score in snapshot.drift_scores.items():
                if drift_score > self.drift_thresholds['feature_drift']:
                    drift_alert = ModelDriftAlert(
                        id=str(hashlib.md5(f"{snapshot.model_name}_{feature_name}_{snapshot.timestamp}".encode()).hexdigest())[:16],
                        model_version=snapshot.model_version,
                        model_name=snapshot.model_name,
                        drift_type=DriftType.FEATURE_DRIFT,
                        drift_score=drift_score,
                        threshold=self.drift_thresholds['feature_drift'],
                        timestamp=snapshot.timestamp,
                        affected_features=[feature_name],
                        recommended_actions=self._get_drift_recommendations(DriftType.FEATURE_DRIFT),
                        severity='critical' if drift_score > 0.5 else 'warning'
                    )
                    
                    await self._handle_drift_alert(drift_alert)
            
            # Handle performance alerts
            for alert in alerts:
                await self._handle_performance_alert(alert, snapshot)
                
        except Exception as e:
            logger.error(f"Failed to check performance alerts: {e}")
    
    def _get_drift_recommendations(self, drift_type: DriftType) -> List[str]:
        """Get recommendations for handling drift"""
        recommendations = {
            DriftType.FEATURE_DRIFT: [
                "Analyze data pipeline for changes",
                "Check feature engineering logic",
                "Consider model retraining",
                "Review data source quality"
            ],
            DriftType.PREDICTION_DRIFT: [
                "Evaluate model performance",
                "Check for concept drift",
                "Consider ensemble model update",
                "Review prediction threshold"
            ],
            DriftType.CONCEPT_DRIFT: [
                "Immediate model retraining required",
                "Update training data",
                "Review business assumptions",
                "Consider A/B testing new model"
            ],
            DriftType.PERFORMANCE_DRIFT: [
                "Optimize model inference",
                "Check system resources",
                "Review model complexity",
                "Consider model compression"
            ]
        }
        
        return recommendations.get(drift_type, ["Contact ML engineering team"])
    
    async def _handle_drift_alert(self, drift_alert: ModelDriftAlert):
        """Handle drift detection alert"""
        try:
            # Store alert
            alert_key = f"drift_alerts:{drift_alert.model_name}:{drift_alert.id}"
            await self.redis_client.setex(
                alert_key,
                86400,  # 24 hours
                json.dumps(asdict(drift_alert), default=str)
            )
            
            logger.warning(f"Drift alert: {drift_alert.drift_type.value} in model "
                          f"{drift_alert.model_name}:{drift_alert.model_version} "
                          f"(score: {drift_alert.drift_score:.3f})")
            
            # Send notification if critical
            if drift_alert.severity == 'critical':
                await self._send_drift_notification(drift_alert)
                
        except Exception as e:
            logger.error(f"Failed to handle drift alert: {e}")
    
    async def _handle_performance_alert(self, alert: Dict[str, Any], snapshot: ModelPerformanceSnapshot):
        """Handle performance degradation alert"""
        try:
            alert_data = {
                'model_name': snapshot.model_name,
                'model_version': snapshot.model_version,
                'timestamp': snapshot.timestamp.isoformat(),
                'alert_type': alert['type'],
                'metric': alert['metric'],
                'current_value': alert['value'],
                'threshold': alert['threshold'],
                'severity': alert['severity']
            }
            
            alert_key = f"performance_alerts:{snapshot.model_name}:{alert['metric']}"
            await self.redis_client.setex(
                alert_key,
                3600,  # 1 hour
                json.dumps(alert_data, default=str)
            )
            
            logger.warning(f"Performance alert: {alert['metric']} = {alert['value']:.3f} "
                          f"(threshold: {alert['threshold']}) for model "
                          f"{snapshot.model_name}:{snapshot.model_version}")
            
            # Send critical alerts
            if alert['severity'] == 'critical':
                await self._send_performance_notification(alert_data)
                
        except Exception as e:
            logger.error(f"Failed to handle performance alert: {e}")
    
    async def _send_drift_notification(self, drift_alert: ModelDriftAlert):
        """Send drift detection notification"""
        try:
            webhook_url = os.getenv('ML_ALERT_WEBHOOK_URL')
            if webhook_url:
                payload = {
                    'alert_type': 'model_drift',
                    'model_name': drift_alert.model_name,
                    'model_version': drift_alert.model_version,
                    'drift_type': drift_alert.drift_type.value,
                    'drift_score': drift_alert.drift_score,
                    'severity': drift_alert.severity,
                    'affected_features': drift_alert.affected_features,
                    'recommendations': drift_alert.recommended_actions
                }
                
                async with aiohttp.ClientSession() as session:
                    await session.post(webhook_url, json=payload, timeout=10)
                    
        except Exception as e:
            logger.error(f"Failed to send drift notification: {e}")
    
    async def _send_performance_notification(self, alert_data: Dict[str, Any]):
        """Send performance alert notification"""
        try:
            webhook_url = os.getenv('ML_ALERT_WEBHOOK_URL')
            if webhook_url:
                async with aiohttp.ClientSession() as session:
                    await session.post(webhook_url, json=alert_data, timeout=10)
                    
        except Exception as e:
            logger.error(f"Failed to send performance notification: {e}")

class MLMonitorService:
    """Main ML monitoring service"""
    
    def __init__(self):
        self.redis_client = None
        self.performance_tracker = None
        self.running = False
        self.tasks = []
        
        # Prometheus metrics
        self.metrics = {
            'model_accuracy': Gauge('ml_model_accuracy', 'Model accuracy', ['model_name', 'model_version']),
            'model_latency': Histogram('ml_model_latency_seconds', 'Model prediction latency', ['model_name', 'model_version']),
            'model_throughput': Gauge('ml_model_throughput_rps', 'Model throughput RPS', ['model_name', 'model_version']),
            'drift_score': Gauge('ml_feature_drift_score', 'Feature drift score', ['model_name', 'feature_name']),
            'false_positive_rate': Gauge('ml_false_positive_rate', 'False positive rate', ['model_name', 'model_version']),
            'false_negative_rate': Gauge('ml_false_negative_rate', 'False negative rate', ['model_name', 'model_version']),
            'data_quality_score': Gauge('ml_data_quality_score', 'Data quality score', ['model_name', 'model_version']),
            'predictions_processed': Counter('ml_predictions_processed_total', 'Total predictions processed', ['model_name', 'model_version'])
        }
    
    async def initialize(self):
        """Initialize the ML monitoring service"""
        try:
            # Initialize Redis connection
            self.redis_client = await redis.from_url(
                "redis://redis:6379",
                decode_responses=True
            )
            
            # Initialize performance tracker
            self.performance_tracker = ModelPerformanceTracker(self.redis_client)
            
            # Initialize model tracking for existing models
            await self._initialize_existing_models()
            
            logger.info("ML monitoring service initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize ML monitoring: {e}")
            raise
    
    async def _initialize_existing_models(self):
        """Initialize tracking for existing models"""
        try:
            # Look for model configurations in Redis
            model_keys = await self.redis_client.keys("model_config:*")
            
            for key in model_keys:
                try:
                    config_data = await self.redis_client.get(key)
                    if config_data:
                        config = json.loads(config_data)
                        model_name = config.get('name', 'unknown')
                        model_version = config.get('version', '1.0.0')
                        
                        await self.performance_tracker.initialize_model_tracking(
                            model_name, model_version, config
                        )
                except Exception as e:
                    logger.warning(f"Failed to initialize model from {key}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to initialize existing models: {e}")
    
    async def start_monitoring(self):
        """Start the ML monitoring process"""
        try:
            self.running = True
            
            # Start monitoring tasks
            self.tasks.append(asyncio.create_task(self._monitor_predictions_loop()))
            self.tasks.append(asyncio.create_task(self._update_metrics_loop()))
            self.tasks.append(asyncio.create_task(self._cleanup_loop()))
            
            logger.info("ML monitoring started")
            
            # Wait for tasks
            await asyncio.gather(*self.tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"ML monitoring error: {e}")
        finally:
            await self.shutdown()
    
    async def _monitor_predictions_loop(self):
        """Monitor prediction streams"""
        while self.running:
            try:
                # Read from ML prediction streams
                streams = await self.redis_client.xread(
                    {'ml_predictions_stream': '$'},
                    count=100,
                    block=1000
                )
                
                for stream_name, messages in streams:
                    prediction_batches = defaultdict(list)
                    actual_batches = defaultdict(list)
                    
                    # Group by model
                    for message_id, fields in messages:
                        try:
                            prediction_data = json.loads(fields.get('prediction', '{}'))
                            actual_data = fields.get('actual')
                            
                            model_name = prediction_data.get('model_name', 'unknown')
                            model_version = prediction_data.get('model_version', '1.0.0')
                            model_key = f"{model_name}:{model_version}"
                            
                            prediction_batches[model_key].append(prediction_data)
                            if actual_data:
                                actual_batches[model_key].append(json.loads(actual_data))
                            
                            # Acknowledge message
                            await self.redis_client.xack('ml_predictions_stream', 'ml_monitor_group', message_id)
                            
                        except Exception as e:
                            logger.error(f"Error processing prediction message: {e}")
                    
                    # Process batches
                    for model_key, predictions in prediction_batches.items():
                        try:
                            model_name, model_version = model_key.split(':', 1)
                            actuals = actual_batches.get(model_key, [])
                            
                            if len(actuals) != len(predictions) and actuals:
                                actuals = None  # Don't use mismatched actuals
                            
                            await self.performance_tracker.record_prediction_batch(
                                model_name, model_version, predictions, actuals
                            )
                            
                            # Update Prometheus metrics
                            self.metrics['predictions_processed'].labels(
                                model_name=model_name,
                                model_version=model_version
                            ).inc(len(predictions))
                            
                        except Exception as e:
                            logger.error(f"Error processing batch for {model_key}: {e}")
                
            except Exception as e:
                logger.error(f"Prediction monitoring loop error: {e}")
                await asyncio.sleep(5)
    
    async def _update_metrics_loop(self):
        """Update Prometheus metrics periodically"""
        while self.running:
            try:
                await asyncio.sleep(30)  # Update every 30 seconds
                
                # Get all model performance snapshots
                pattern = "model_performance:*:latest"
                keys = await self.redis_client.keys(pattern)
                
                for key in keys:
                    try:
                        snapshot_data = await self.redis_client.get(key)
                        if snapshot_data:
                            snapshot_dict = json.loads(snapshot_data)
                            
                            model_name = snapshot_dict['model_name']
                            model_version = snapshot_dict['model_version']
                            
                            # Update Prometheus metrics
                            self.metrics['model_accuracy'].labels(
                                model_name=model_name,
                                model_version=model_version
                            ).set(snapshot_dict['accuracy'])
                            
                            self.metrics['model_latency'].labels(
                                model_name=model_name,
                                model_version=model_version
                            ).observe(snapshot_dict['prediction_latency_p95'] / 1000.0)
                            
                            self.metrics['model_throughput'].labels(
                                model_name=model_name,
                                model_version=model_version
                            ).set(snapshot_dict['throughput_rps'])
                            
                            self.metrics['false_positive_rate'].labels(
                                model_name=model_name,
                                model_version=model_version
                            ).set(snapshot_dict['false_positive_rate'])
                            
                            self.metrics['false_negative_rate'].labels(
                                model_name=model_name,
                                model_version=model_version
                            ).set(snapshot_dict['false_negative_rate'])
                            
                            self.metrics['data_quality_score'].labels(
                                model_name=model_name,
                                model_version=model_version
                            ).set(snapshot_dict['data_quality_score'])
                            
                            # Update drift scores
                            for feature_name, drift_score in snapshot_dict['drift_scores'].items():
                                self.metrics['drift_score'].labels(
                                    model_name=model_name,
                                    feature_name=feature_name
                                ).set(drift_score)
                            
                    except Exception as e:
                        logger.error(f"Error updating metrics for {key}: {e}")
                
                # Push metrics to Prometheus
                gateway = os.getenv('PROMETHEUS_PUSHGATEWAY_URL', 'prometheus:9091')
                registry = CollectorRegistry()
                
                for metric in self.metrics.values():
                    registry.register(metric)
                
                push_to_gateway(gateway, job='ml-monitor', registry=registry)
                
            except Exception as e:
                logger.error(f"Metrics update error: {e}")
    
    async def _cleanup_loop(self):
        """Periodic cleanup tasks"""
        while self.running:
            try:
                await asyncio.sleep(3600)  # Every hour
                
                # Clean up old alerts
                await self._cleanup_old_alerts()
                
                # Clean up old performance data
                await self._cleanup_old_performance_data()
                
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
    
    async def _cleanup_old_alerts(self):
        """Clean up old alert data"""
        try:
            # Clean drift alerts older than 7 days
            cutoff_time = datetime.now() - timedelta(days=7)
            
            alert_keys = await self.redis_client.keys("drift_alerts:*")
            for key in alert_keys:
                try:
                    alert_data = await self.redis_client.get(key)
                    if alert_data:
                        alert = json.loads(alert_data)
                        alert_time = datetime.fromisoformat(alert['timestamp'])
                        
                        if alert_time < cutoff_time:
                            await self.redis_client.delete(key)
                except Exception as e:
                    logger.warning(f"Error cleaning alert {key}: {e}")
            
            # Clean performance alerts older than 24 hours
            perf_cutoff = datetime.now() - timedelta(hours=24)
            perf_keys = await self.redis_client.keys("performance_alerts:*")
            
            for key in perf_keys:
                try:
                    ttl = await self.redis_client.ttl(key)
                    if ttl == -1:  # No expiry set
                        await self.redis_client.delete(key)
                except Exception as e:
                    logger.warning(f"Error cleaning performance alert {key}: {e}")
                    
        except Exception as e:
            logger.error(f"Alert cleanup error: {e}")
    
    async def _cleanup_old_performance_data(self):
        """Clean up old performance time series data"""
        try:
            # Keep only last 1000 entries per model
            ts_keys = await self.redis_client.keys("model_performance_ts:*")
            
            for key in ts_keys:
                try:
                    await self.redis_client.ltrim(key, 0, 999)
                except Exception as e:
                    logger.warning(f"Error trimming {key}: {e}")
                    
        except Exception as e:
            logger.error(f"Performance data cleanup error: {e}")
    
    async def shutdown(self):
        """Shutdown the ML monitoring service"""
        logger.info("Shutting down ML monitoring service")
        self.running = False
        
        # Cancel tasks
        for task in self.tasks:
            task.cancel()
        
        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()

async def main():
    """Main entry point"""
    service = MLMonitorService()
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        asyncio.create_task(service.shutdown())
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        await service.initialize()
        await service.start_monitoring()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"ML monitoring service error: {e}")
    finally:
        await service.shutdown()

if __name__ == "__main__":
    asyncio.run(main())