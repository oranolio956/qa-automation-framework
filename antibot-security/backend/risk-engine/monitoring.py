"""
Real-time Monitoring and Alerting System for ML Risk Scoring Engine
Comprehensive performance monitoring, drift detection, and automated alerting
"""

import asyncio
import json
import logging
import time
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
import redis.asyncio as redis
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
import aiohttp
from collections import defaultdict, deque
import statistics
import hashlib

from .ml_models import EnsemblePrediction
from .feature_engineering import FeatureVector

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class AlertType(Enum):
    PERFORMANCE_DEGRADATION = "performance_degradation"
    LATENCY_SPIKE = "latency_spike"
    ERROR_RATE_HIGH = "error_rate_high"
    MODEL_DRIFT = "model_drift"
    FEATURE_DRIFT = "feature_drift"
    RESOURCE_USAGE = "resource_usage"
    ANOMALY_DETECTED = "anomaly_detected"
    A_B_TEST_SIGNIFICANCE = "ab_test_significance"

@dataclass
class Alert:
    """Alert data structure"""
    id: str
    type: AlertType
    severity: AlertSeverity
    title: str
    description: str
    timestamp: datetime
    model_version: Optional[str] = None
    metrics: Dict[str, float] = None
    remediation_suggestions: List[str] = None
    is_resolved: bool = False

@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot"""
    timestamp: datetime
    model_version: str
    requests_per_second: float
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    error_rate: float
    accuracy: float
    false_positive_rate: float
    false_negative_rate: float
    feature_drift_score: float
    prediction_drift_score: float
    cpu_usage_percent: float
    memory_usage_percent: float
    gpu_usage_percent: float

class PrometheusMetrics:
    """Prometheus metrics for monitoring"""
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()
        
        # Request metrics
        self.request_counter = Counter(
            'ml_requests_total',
            'Total number of ML prediction requests',
            ['model_version', 'status'],
            registry=self.registry
        )
        
        self.request_duration = Histogram(
            'ml_request_duration_seconds',
            'Duration of ML prediction requests',
            ['model_version'],
            registry=self.registry
        )
        
        # Model performance metrics
        self.accuracy_gauge = Gauge(
            'ml_model_accuracy',
            'Model accuracy score',
            ['model_version'],
            registry=self.registry
        )
        
        self.false_positive_rate = Gauge(
            'ml_false_positive_rate',
            'False positive rate',
            ['model_version'],
            registry=self.registry
        )
        
        self.risk_score_histogram = Histogram(
            'ml_risk_score_distribution',
            'Distribution of risk scores',
            ['model_version'],
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            registry=self.registry
        )
        
        # Feature drift metrics
        self.feature_drift = Gauge(
            'ml_feature_drift_score',
            'Feature drift detection score',
            ['feature_name', 'model_version'],
            registry=self.registry
        )
        
        # System resource metrics
        self.cpu_usage = Gauge(
            'ml_cpu_usage_percent',
            'CPU usage percentage',
            registry=self.registry
        )
        
        self.memory_usage = Gauge(
            'ml_memory_usage_percent',
            'Memory usage percentage',
            registry=self.registry
        )
        
        self.gpu_usage = Gauge(
            'ml_gpu_usage_percent',
            'GPU usage percentage',
            registry=self.registry
        )

class DriftDetector:
    """Statistical drift detection for features and predictions"""
    
    def __init__(self, reference_window: int = 1000, detection_window: int = 100):
        self.reference_window = reference_window
        self.detection_window = detection_window
        self.reference_data = defaultdict(lambda: deque(maxlen=reference_window))
        self.detection_data = defaultdict(lambda: deque(maxlen=detection_window))
        
    def update_reference(self, feature_name: str, value: float):
        """Update reference distribution"""
        self.reference_data[feature_name].append(value)
    
    def add_sample(self, feature_name: str, value: float):
        """Add new sample for drift detection"""
        self.detection_data[feature_name].append(value)
    
    def calculate_drift_score(self, feature_name: str) -> float:
        """Calculate drift score using KL divergence approximation"""
        if (len(self.reference_data[feature_name]) < 100 or 
            len(self.detection_data[feature_name]) < 50):
            return 0.0
        
        try:
            # Convert to numpy arrays
            reference = np.array(self.reference_data[feature_name])
            current = np.array(self.detection_data[feature_name])
            
            # Calculate statistical measures
            ref_mean, ref_std = np.mean(reference), np.std(reference)
            cur_mean, cur_std = np.mean(current), np.std(current)
            
            # Avoid division by zero
            if ref_std == 0 or cur_std == 0:
                return abs(ref_mean - cur_mean)
            
            # Normalized difference in means
            mean_diff = abs(ref_mean - cur_mean) / ref_std
            
            # Ratio of standard deviations
            std_ratio = max(ref_std / cur_std, cur_std / ref_std)
            
            # Combined drift score
            drift_score = mean_diff + (std_ratio - 1.0)
            
            return min(1.0, drift_score)
            
        except Exception as e:
            logger.warning(f"Drift calculation failed for {feature_name}: {e}")
            return 0.0
    
    def detect_drift(self, threshold: float = 0.3) -> Dict[str, float]:
        """Detect drift across all features"""
        drift_scores = {}
        
        for feature_name in self.reference_data.keys():
            score = self.calculate_drift_score(feature_name)
            if score > threshold:
                drift_scores[feature_name] = score
        
        return drift_scores

class AnomalyDetector:
    """Real-time anomaly detection for predictions and system metrics"""
    
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.data_windows = defaultdict(lambda: deque(maxlen=window_size))
        
    def add_sample(self, metric_name: str, value: float):
        """Add sample for anomaly detection"""
        self.data_windows[metric_name].append(value)
    
    def detect_anomaly(self, metric_name: str, value: float, threshold_std: float = 3.0) -> Tuple[bool, float]:
        """Detect anomaly using z-score method"""
        window = self.data_windows[metric_name]
        
        if len(window) < 50:
            return False, 0.0
        
        try:
            mean = statistics.mean(window)
            stdev = statistics.stdev(window)
            
            if stdev == 0:
                return value != mean, 0.0
            
            z_score = abs(value - mean) / stdev
            is_anomaly = z_score > threshold_std
            
            return is_anomaly, z_score
            
        except Exception as e:
            logger.warning(f"Anomaly detection failed for {metric_name}: {e}")
            return False, 0.0

class AlertManager:
    """Manage alerts with deduplication and escalation"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_cooldowns: Dict[str, datetime] = {}
        self.notification_channels = []
        
    def add_notification_channel(self, channel: 'NotificationChannel'):
        """Add notification channel"""
        self.notification_channels.append(channel)
    
    async def create_alert(self, alert_type: AlertType, severity: AlertSeverity,
                          title: str, description: str, model_version: str = None,
                          metrics: Dict[str, float] = None) -> Alert:
        """Create and process new alert"""
        
        # Generate alert ID
        alert_id = hashlib.md5(f"{alert_type.value}_{model_version}_{title}".encode()).hexdigest()[:16]
        
        # Check cooldown period
        cooldown_key = f"{alert_type.value}_{model_version}"
        if cooldown_key in self.alert_cooldowns:
            time_since_last = datetime.now() - self.alert_cooldowns[cooldown_key]
            if time_since_last < timedelta(minutes=5):  # 5-minute cooldown
                return None
        
        # Create alert
        alert = Alert(
            id=alert_id,
            type=alert_type,
            severity=severity,
            title=title,
            description=description,
            timestamp=datetime.now(),
            model_version=model_version,
            metrics=metrics or {},
            remediation_suggestions=self._get_remediation_suggestions(alert_type),
            is_resolved=False
        )
        
        # Store alert
        self.active_alerts[alert_id] = alert
        self.alert_cooldowns[cooldown_key] = datetime.now()
        
        # Store in Redis
        if self.redis_client:
            await self.redis_client.setex(
                f"alert:{alert_id}",
                3600,  # 1 hour TTL
                json.dumps(asdict(alert), default=str)
            )
        
        # Send notifications
        await self._send_notifications(alert)
        
        logger.warning(f"Alert created: {alert.type.value} - {alert.title}")
        return alert
    
    def _get_remediation_suggestions(self, alert_type: AlertType) -> List[str]:
        """Get remediation suggestions for alert type"""
        suggestions = {
            AlertType.PERFORMANCE_DEGRADATION: [
                "Check model accuracy against validation set",
                "Review recent data quality",
                "Consider model retraining",
                "Verify feature pipeline integrity"
            ],
            AlertType.LATENCY_SPIKE: [
                "Check system resource usage",
                "Review batch size configuration",
                "Verify GPU availability",
                "Check for memory leaks"
            ],
            AlertType.ERROR_RATE_HIGH: [
                "Review recent error logs",
                "Check data input validation",
                "Verify model loading status",
                "Check external dependencies"
            ],
            AlertType.MODEL_DRIFT: [
                "Analyze recent prediction patterns",
                "Review training data distribution",
                "Consider model retraining",
                "Check for data pipeline changes"
            ],
            AlertType.FEATURE_DRIFT: [
                "Investigate data source changes",
                "Review feature engineering pipeline",
                "Check for upstream system changes",
                "Validate feature extraction logic"
            ]
        }
        
        return suggestions.get(alert_type, ["Contact ML engineering team"])
    
    async def _send_notifications(self, alert: Alert):
        """Send alert notifications through configured channels"""
        for channel in self.notification_channels:
            try:
                await channel.send_alert(alert)
            except Exception as e:
                logger.error(f"Failed to send alert through {type(channel).__name__}: {e}")
    
    async def resolve_alert(self, alert_id: str):
        """Mark alert as resolved"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].is_resolved = True
            
            if self.redis_client:
                await self.redis_client.delete(f"alert:{alert_id}")

class NotificationChannel:
    """Base class for notification channels"""
    
    async def send_alert(self, alert: Alert):
        raise NotImplementedError

class WebhookNotificationChannel(NotificationChannel):
    """Webhook-based notifications"""
    
    def __init__(self, webhook_url: str, headers: Dict[str, str] = None):
        self.webhook_url = webhook_url
        self.headers = headers or {'Content-Type': 'application/json'}
    
    async def send_alert(self, alert: Alert):
        """Send alert via webhook"""
        payload = {
            "alert_id": alert.id,
            "type": alert.type.value,
            "severity": alert.severity.value,
            "title": alert.title,
            "description": alert.description,
            "timestamp": alert.timestamp.isoformat(),
            "model_version": alert.model_version,
            "metrics": alert.metrics,
            "suggestions": alert.remediation_suggestions
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        logger.warning(f"Webhook notification failed: {response.status}")
                        
            except Exception as e:
                logger.error(f"Webhook notification error: {e}")

class SlackNotificationChannel(NotificationChannel):
    """Slack-based notifications"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    async def send_alert(self, alert: Alert):
        """Send alert to Slack"""
        color_map = {
            AlertSeverity.INFO: "good",
            AlertSeverity.WARNING: "warning",
            AlertSeverity.CRITICAL: "danger",
            AlertSeverity.EMERGENCY: "danger"
        }
        
        payload = {
            "attachments": [{
                "color": color_map.get(alert.severity, "warning"),
                "title": f"ML Alert: {alert.title}",
                "text": alert.description,
                "fields": [
                    {"title": "Severity", "value": alert.severity.value.upper(), "short": True},
                    {"title": "Type", "value": alert.type.value.replace('_', ' ').title(), "short": True},
                    {"title": "Model Version", "value": alert.model_version or "N/A", "short": True},
                    {"title": "Timestamp", "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "short": True}
                ],
                "footer": "ML Risk Scoring Engine",
                "ts": int(alert.timestamp.timestamp())
            }]
        }
        
        if alert.metrics:
            metrics_text = "\n".join([f"{k}: {v:.4f}" for k, v in alert.metrics.items()])
            payload["attachments"][0]["fields"].append({
                "title": "Metrics",
                "value": f"```{metrics_text}```",
                "short": False
            })
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        logger.warning(f"Slack notification failed: {response.status}")
                        
            except Exception as e:
                logger.error(f"Slack notification error: {e}")

class RealTimeMonitor:
    """
    Real-time monitoring system for ML risk scoring engine
    Comprehensive performance tracking, drift detection, and alerting
    Integrated with the comprehensive monitoring infrastructure
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        
        # Monitoring components
        self.prometheus_metrics = PrometheusMetrics()
        self.drift_detector = DriftDetector()
        self.anomaly_detector = AnomalyDetector()
        self.alert_manager = AlertManager(redis_client)
        
        # Performance tracking
        self.performance_history: List[PerformanceMetrics] = []
        self.current_metrics = {}
        
        # Monitoring configuration
        self.monitoring_config = {
            'latency_threshold_ms': 50,
            'error_rate_threshold': 0.05,
            'accuracy_threshold': 0.95,
            'false_positive_threshold': 0.01,
            'drift_threshold': 0.3,
            'anomaly_threshold_std': 3.0,
            'monitoring_interval_seconds': 60
        }
        
        # Integration with comprehensive monitoring
        self.ml_predictions_stream = 'ml_predictions_stream'
        self.model_configs_key = 'model_config:risk_engine'
        
        # Background task status
        self.monitoring_task: Optional[asyncio.Task] = None
        self.is_running = False
        
    async def initialize(self):
        """Initialize monitoring system"""
        try:
            # Configure notification channels
            await self._setup_notification_channels()
            
            # Start background monitoring
            self.is_running = True
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            
            logger.info("Real-time monitoring system initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize monitoring: {e}")
            raise
    
    async def _setup_notification_channels(self):
        """Setup notification channels from environment"""
        try:
            # Add webhook notifications if configured
            webhook_url = os.getenv('ALERT_WEBHOOK_URL')
            if webhook_url:
                self.alert_manager.add_notification_channel(
                    WebhookNotificationChannel(webhook_url)
                )
            
            # Add Slack notifications if configured
            slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
            if slack_webhook:
                self.alert_manager.add_notification_channel(
                    SlackNotificationChannel(slack_webhook)
                )
                
        except Exception as e:
            logger.warning(f"Failed to setup notification channels: {e}")
    
    async def log_prediction(self, model_version: str, feature_vector: FeatureVector, 
                           prediction: EnsemblePrediction, actual_result: Optional[bool] = None):
        """Log prediction for monitoring"""
        try:
            start_time = time.time()
            
            # Update Prometheus metrics
            self.prometheus_metrics.request_counter.labels(
                model_version=model_version,
                status='success'
            ).inc()
            
            self.prometheus_metrics.request_duration.labels(
                model_version=model_version
            ).observe(prediction.total_inference_time_ms / 1000.0)
            
            self.prometheus_metrics.risk_score_histogram.labels(
                model_version=model_version
            ).observe(prediction.final_risk_score)
            
            # Log feature values for drift detection
            for feature_name, value in feature_vector.features.items():
                self.drift_detector.add_sample(feature_name, value)
                
                # Update feature drift metrics
                drift_score = self.drift_detector.calculate_drift_score(feature_name)
                self.prometheus_metrics.feature_drift.labels(
                    feature_name=feature_name,
                    model_version=model_version
                ).set(drift_score)
            
            # Log prediction for anomaly detection
            self.anomaly_detector.add_sample('risk_score', prediction.final_risk_score)
            self.anomaly_detector.add_sample('confidence', prediction.final_confidence)
            self.anomaly_detector.add_sample('inference_time', prediction.total_inference_time_ms)
            
            # Check for anomalies
            await self._check_prediction_anomalies(model_version, prediction)
            
            # Update accuracy metrics if actual result is available
            if actual_result is not None:
                predicted_positive = prediction.final_risk_score > 0.5
                is_correct = predicted_positive == actual_result
                
                # Store for batch accuracy calculation
                accuracy_key = f"accuracy:{model_version}"
                if self.redis_client:
                    await self.redis_client.lpush(accuracy_key, "1" if is_correct else "0")
                    await self.redis_client.ltrim(accuracy_key, 0, 9999)  # Keep last 10k
                    await self.redis_client.expire(accuracy_key, 86400)  # 24 hours
                
                # Update false positive tracking
                if not actual_result and predicted_positive:
                    fp_key = f"false_positives:{model_version}"
                    if self.redis_client:
                        await self.redis_client.incr(fp_key)
                        await self.redis_client.expire(fp_key, 86400)
            
            # Store prediction details for analysis
            if self.redis_client:
                prediction_data = {
                    "timestamp": datetime.now().isoformat(),
                    "model_name": "risk_engine",
                    "model_version": model_version,
                    "risk_score": prediction.final_risk_score,
                    "confidence": prediction.final_confidence,
                    "inference_time_ms": prediction.total_inference_time_ms,
                    "latency_ms": prediction.total_inference_time_ms,
                    "features": dict(feature_vector.features),
                    "feature_count": len(feature_vector.features),
                    "actual_result": actual_result
                }
                
                # Send to ML monitoring stream for comprehensive analysis
                await self.redis_client.xadd(
                    self.ml_predictions_stream,
                    {"prediction": json.dumps(prediction_data)}
                )
                
                # Also store in legacy format for backward compatibility
                await self.redis_client.lpush(
                    f"predictions:{model_version}",
                    json.dumps(prediction_data)
                )
                await self.redis_client.ltrim(f"predictions:{model_version}", 0, 99999)
                await self.redis_client.expire(f"predictions:{model_version}", 86400)
                
                # Register model configuration if not exists
                await self._register_model_config(model_version)
            
            processing_time = (time.time() - start_time) * 1000
            if processing_time > 10:  # Log if monitoring overhead is high
                logger.warning(f"Monitoring overhead: {processing_time:.2f}ms")
                
        except Exception as e:
            logger.error(f"Failed to log prediction: {e}")
            # Count monitoring failures
            self.prometheus_metrics.request_counter.labels(
                model_version=model_version,
                status='monitoring_error'
            ).inc()
    
    async def _check_prediction_anomalies(self, model_version: str, prediction: EnsemblePrediction):
        """Check for prediction anomalies and create alerts"""
        try:
            # Check latency anomaly
            is_anomaly, z_score = self.anomaly_detector.detect_anomaly(
                'inference_time', 
                prediction.total_inference_time_ms
            )
            
            if is_anomaly and prediction.total_inference_time_ms > self.monitoring_config['latency_threshold_ms']:
                await self.alert_manager.create_alert(
                    AlertType.LATENCY_SPIKE,
                    AlertSeverity.WARNING,
                    f"High inference latency detected",
                    f"Inference time: {prediction.total_inference_time_ms:.2f}ms (z-score: {z_score:.2f})",
                    model_version,
                    {"inference_time_ms": prediction.total_inference_time_ms, "z_score": z_score}
                )
            
            # Check risk score distribution anomaly
            is_anomaly, z_score = self.anomaly_detector.detect_anomaly(
                'risk_score',
                prediction.final_risk_score
            )
            
            if is_anomaly and z_score > 4.0:  # Very high z-score
                await self.alert_manager.create_alert(
                    AlertType.ANOMALY_DETECTED,
                    AlertSeverity.INFO,
                    f"Unusual risk score pattern",
                    f"Risk score: {prediction.final_risk_score:.4f} (z-score: {z_score:.2f})",
                    model_version,
                    {"risk_score": prediction.final_risk_score, "z_score": z_score}
                )
                
        except Exception as e:
            logger.warning(f"Anomaly checking failed: {e}")
    
    async def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.is_running:
            try:
                await asyncio.sleep(self.monitoring_config['monitoring_interval_seconds'])
                
                # Collect system metrics
                await self._collect_system_metrics()
                
                # Check drift across all features
                await self._check_feature_drift()
                
                # Update performance metrics
                await self._update_performance_metrics()
                
                # Check for performance degradation
                await self._check_performance_degradation()
                
                # Cleanup old data
                await self._cleanup_old_data()
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(10)  # Brief pause before continuing
    
    async def _collect_system_metrics(self):
        """Collect system resource metrics"""
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.prometheus_metrics.cpu_usage.set(cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.prometheus_metrics.memory_usage.set(memory.percent)
            
            # GPU usage (if available)
            try:
                import pynvml
                pynvml.nvmlInit()
                gpu_count = pynvml.nvmlDeviceGetCount()
                
                if gpu_count > 0:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    gpu_usage = (info.used / info.total) * 100
                    self.prometheus_metrics.gpu_usage.set(gpu_usage)
                    
            except ImportError:
                pass  # GPU monitoring not available
            except Exception as e:
                logger.warning(f"GPU monitoring failed: {e}")
            
            # Check for resource alerts
            if cpu_percent > 90:
                await self.alert_manager.create_alert(
                    AlertType.RESOURCE_USAGE,
                    AlertSeverity.WARNING,
                    "High CPU usage detected",
                    f"CPU usage: {cpu_percent:.1f}%",
                    metrics={"cpu_percent": cpu_percent}
                )
            
            if memory.percent > 90:
                await self.alert_manager.create_alert(
                    AlertType.RESOURCE_USAGE,
                    AlertSeverity.WARNING,
                    "High memory usage detected",
                    f"Memory usage: {memory.percent:.1f}%",
                    metrics={"memory_percent": memory.percent}
                )
                
        except Exception as e:
            logger.warning(f"System metrics collection failed: {e}")
    
    async def _check_feature_drift(self):
        """Check for feature drift and create alerts"""
        try:
            drift_scores = self.drift_detector.detect_drift(self.monitoring_config['drift_threshold'])
            
            if drift_scores:
                # Create alert for significant drift
                max_drift_feature = max(drift_scores.items(), key=lambda x: x[1])
                
                await self.alert_manager.create_alert(
                    AlertType.FEATURE_DRIFT,
                    AlertSeverity.WARNING,
                    f"Feature drift detected",
                    f"Feature '{max_drift_feature[0]}' has drift score: {max_drift_feature[1]:.4f}",
                    metrics=drift_scores
                )
                
        except Exception as e:
            logger.warning(f"Feature drift checking failed: {e}")
    
    async def _update_performance_metrics(self):
        """Update performance metrics from Redis data"""
        try:
            if not self.redis_client:
                return
            
            # Get active model versions
            model_versions = await self._get_active_model_versions()
            
            for model_version in model_versions:
                # Calculate accuracy
                accuracy_data = await self.redis_client.lrange(f"accuracy:{model_version}", 0, -1)
                if accuracy_data:
                    accuracy = sum(int(x) for x in accuracy_data) / len(accuracy_data)
                    self.prometheus_metrics.accuracy_gauge.labels(model_version=model_version).set(accuracy)
                
                # Calculate false positive rate
                total_predictions = len(accuracy_data) if accuracy_data else 0
                false_positives = await self.redis_client.get(f"false_positives:{model_version}")
                false_positives = int(false_positives) if false_positives else 0
                
                if total_predictions > 0:
                    fpr = false_positives / total_predictions
                    self.prometheus_metrics.false_positive_rate.labels(model_version=model_version).set(fpr)
                
                # Check accuracy threshold
                if accuracy_data and len(accuracy_data) > 100:
                    recent_accuracy = sum(int(x) for x in accuracy_data[:100]) / 100
                    
                    if recent_accuracy < self.monitoring_config['accuracy_threshold']:
                        await self.alert_manager.create_alert(
                            AlertType.PERFORMANCE_DEGRADATION,
                            AlertSeverity.CRITICAL,
                            f"Model accuracy below threshold",
                            f"Recent accuracy: {recent_accuracy:.4f} (threshold: {self.monitoring_config['accuracy_threshold']})",
                            model_version,
                            {"accuracy": recent_accuracy, "threshold": self.monitoring_config['accuracy_threshold']}
                        )
                
                # Check false positive rate
                if total_predictions > 100 and fpr > self.monitoring_config['false_positive_threshold']:
                    await self.alert_manager.create_alert(
                        AlertType.PERFORMANCE_DEGRADATION,
                        AlertSeverity.WARNING,
                        f"High false positive rate",
                        f"FPR: {fpr:.4f} (threshold: {self.monitoring_config['false_positive_threshold']})",
                        model_version,
                        {"false_positive_rate": fpr, "threshold": self.monitoring_config['false_positive_threshold']}
                    )
                
        except Exception as e:
            logger.warning(f"Performance metrics update failed: {e}")
    
    async def _check_performance_degradation(self):
        """Check for overall performance degradation"""
        try:
            # This would typically compare current performance to historical baselines
            # Implementation depends on specific business requirements
            pass
            
        except Exception as e:
            logger.warning(f"Performance degradation check failed: {e}")
    
    async def _get_active_model_versions(self) -> List[str]:
        """Get list of active model versions"""
        try:
            if self.redis_client:
                keys = await self.redis_client.keys("predictions:*")
                return [key.split(":")[1] for key in keys]
            return []
            
        except Exception as e:
            logger.warning(f"Failed to get active model versions: {e}")
            return []
    
    async def _cleanup_old_data(self):
        """Cleanup old monitoring data"""
        try:
            # Clean up old drift detection data
            cutoff_time = time.time() - 86400  # 24 hours
            
            # This is a simplified cleanup - in practice, you'd want more sophisticated retention
            if len(self.performance_history) > 10000:
                self.performance_history = self.performance_history[-5000:]
                
        except Exception as e:
            logger.warning(f"Data cleanup failed: {e}")
    
    def get_prometheus_metrics(self) -> str:
        """Get Prometheus metrics in text format"""
        try:
            return generate_latest(self.prometheus_metrics.registry).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to generate Prometheus metrics: {e}")
            return ""
    
    async def _register_model_config(self, model_version: str):
        """Register model configuration with the ML monitoring system"""
        try:
            config_exists = await self.redis_client.exists(self.model_configs_key)
            if not config_exists:
                config = {
                    "name": "risk_engine",
                    "version": model_version,
                    "type": "ensemble",
                    "features": list(self.feature_extractors.keys()) if hasattr(self, 'feature_extractors') else [],
                    "created_at": datetime.now().isoformat(),
                    "accuracy_threshold": self.monitoring_config['accuracy_threshold'],
                    "latency_threshold_ms": self.monitoring_config['latency_threshold_ms'],
                    "drift_threshold": self.monitoring_config['drift_threshold']
                }
                
                await self.redis_client.set(
                    self.model_configs_key,
                    json.dumps(config),
                    ex=86400  # 24 hours
                )
                logger.info(f"Registered model config for {model_version}")
        except Exception as e:
            logger.warning(f"Failed to register model config: {e}")
    
    async def get_monitoring_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive monitoring data for dashboard"""
        try:
            dashboard_data = {
                "timestamp": datetime.now().isoformat(),
                "system_metrics": {
                    "cpu_usage": self.prometheus_metrics.cpu_usage._value._value,
                    "memory_usage": self.prometheus_metrics.memory_usage._value._value,
                    "gpu_usage": self.prometheus_metrics.gpu_usage._value._value
                },
                "active_alerts": [asdict(alert) for alert in self.alert_manager.active_alerts.values()],
                "performance_summary": {},
                "drift_summary": {}
            }
            
            # Add model-specific metrics
            model_versions = await self._get_active_model_versions()
            
            for model_version in model_versions:
                # Get recent predictions
                if self.redis_client:
                    predictions = await self.redis_client.lrange(f"predictions:{model_version}", 0, 99)
                    if predictions:
                        prediction_data = [json.loads(p) for p in predictions]
                        
                        dashboard_data["performance_summary"][model_version] = {
                            "total_predictions": len(prediction_data),
                            "avg_risk_score": np.mean([p["risk_score"] for p in prediction_data]),
                            "avg_confidence": np.mean([p["confidence"] for p in prediction_data]),
                            "avg_inference_time": np.mean([p["inference_time_ms"] for p in prediction_data]),
                            "p95_inference_time": np.percentile([p["inference_time_ms"] for p in prediction_data], 95)
                        }
            
            # Add drift information
            for feature_name in self.drift_detector.reference_data.keys():
                drift_score = self.drift_detector.calculate_drift_score(feature_name)
                if drift_score > 0.1:  # Only include features with some drift
                    dashboard_data["drift_summary"][feature_name] = drift_score
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Failed to generate dashboard data: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    async def stop(self):
        """Stop monitoring system"""
        self.is_running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Monitoring system stopped")

# Import psutil if available
try:
    import psutil
except ImportError:
    logger.warning("psutil not available - system resource monitoring disabled")

# Import os for environment variables
import os
import asyncio
from contextlib import asynccontextmanager