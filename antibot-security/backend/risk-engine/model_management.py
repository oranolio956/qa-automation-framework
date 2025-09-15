"""
Model Management System with Versioning and A/B Testing
Supports continuous deployment, rollback capabilities, and performance monitoring
"""

import asyncio
import json
import logging
import time
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
import numpy as np
import redis.asyncio as redis
from concurrent.futures import ThreadPoolExecutor
import joblib
import shutil
import uuid

from .ml_models import AdvancedEnsembleModel, EnsemblePrediction
from .feature_engineering import FeatureVector

logger = logging.getLogger(__name__)

class ModelStatus(Enum):
    TRAINING = "training"
    TESTING = "testing"
    STAGED = "staged"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"
    FAILED = "failed"

class DeploymentStrategy(Enum):
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    AB_TEST = "ab_test"
    ROLLING = "rolling"

@dataclass
class ModelVersion:
    """Model version metadata"""
    version_id: str
    model_name: str
    version_number: str
    created_at: datetime
    status: ModelStatus
    performance_metrics: Dict[str, float]
    model_hash: str
    training_data_hash: str
    feature_schema: Dict[str, str]
    deployment_config: Dict[str, Any]
    a_b_test_config: Optional[Dict[str, Any]] = None
    rollback_version: Optional[str] = None

@dataclass
class ABTestConfig:
    """A/B test configuration"""
    test_id: str
    name: str
    description: str
    model_a_version: str
    model_b_version: str
    traffic_split: float  # Percentage for model B (0-100)
    start_time: datetime
    end_time: datetime
    success_metrics: List[str]
    is_active: bool = True

@dataclass
class ABTestResult:
    """A/B test results"""
    test_id: str
    model_a_metrics: Dict[str, float]
    model_b_metrics: Dict[str, float]
    sample_size_a: int
    sample_size_b: int
    statistical_significance: bool
    winner: Optional[str]
    confidence_level: float

class ModelVersionManager:
    """
    Manages model versions with automated deployment and rollback
    """
    
    def __init__(self, base_path: str = "models", redis_client: Optional[redis.Redis] = None):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
        self.redis_client = redis_client
        
        # Version storage
        self.versions: Dict[str, ModelVersion] = {}
        self.active_models: Dict[str, AdvancedEnsembleModel] = {}
        self.production_version: Optional[str] = None
        self.staged_version: Optional[str] = None
        
        # A/B testing
        self.active_ab_tests: Dict[str, ABTestConfig] = {}
        self.ab_test_results: Dict[str, ABTestResult] = {}
        
        # Performance tracking
        self.performance_history: Dict[str, List[Dict[str, Any]]] = {}
        self.last_performance_check = datetime.now()
        
        # Thread pool for background tasks
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    async def initialize(self):
        """Initialize the version manager"""
        try:
            # Load existing versions
            await self.load_versions()
            
            # Load active A/B tests
            await self.load_ab_tests()
            
            # Initialize models for active versions
            await self.load_active_models()
            
            logger.info("Model version manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize version manager: {e}")
            raise
    
    async def create_new_version(self, 
                               model_name: str,
                               training_data: pd.DataFrame,
                               labels: pd.Series,
                               deployment_config: Dict[str, Any] = None) -> str:
        """Create a new model version"""
        try:
            # Generate version ID
            version_id = f"{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            version_number = self._get_next_version_number(model_name)
            
            # Create version directory
            version_dir = self.base_path / version_id
            version_dir.mkdir(exist_ok=True)
            
            # Calculate data hash for reproducibility
            training_data_hash = hashlib.md5(
                pd.util.hash_pandas_object(training_data, index=True).values
            ).hexdigest()
            
            # Initialize and train model
            model = AdvancedEnsembleModel(str(version_dir))
            await model.initialize_models(feature_dim=len(training_data.columns))
            
            logger.info(f"Training new model version: {version_id}")
            training_results = await model.train_models(training_data, labels)
            
            # Calculate model hash
            model_hash = await self._calculate_model_hash(version_dir)
            
            # Create version metadata
            version = ModelVersion(
                version_id=version_id,
                model_name=model_name,
                version_number=version_number,
                created_at=datetime.now(),
                status=ModelStatus.TRAINING,
                performance_metrics=self._extract_best_metrics(training_results),
                model_hash=model_hash,
                training_data_hash=training_data_hash,
                feature_schema=self._create_feature_schema(training_data),
                deployment_config=deployment_config or {}
            )
            
            # Save version metadata
            await self._save_version_metadata(version)
            
            # Store in memory
            self.versions[version_id] = version
            self.active_models[version_id] = model
            
            # Update status to testing
            await self.update_version_status(version_id, ModelStatus.TESTING)
            
            logger.info(f"Created new model version: {version_id}")
            return version_id
            
        except Exception as e:
            logger.error(f"Failed to create new version: {e}")
            raise
    
    async def deploy_to_production(self, version_id: str, strategy: DeploymentStrategy = DeploymentStrategy.BLUE_GREEN):
        """Deploy a model version to production"""
        try:
            if version_id not in self.versions:
                raise ValueError(f"Version {version_id} not found")
            
            version = self.versions[version_id]
            
            if version.status != ModelStatus.STAGED:
                raise ValueError(f"Version {version_id} must be staged before production deployment")
            
            if strategy == DeploymentStrategy.BLUE_GREEN:
                await self._deploy_blue_green(version_id)
            elif strategy == DeploymentStrategy.CANARY:
                await self._deploy_canary(version_id)
            elif strategy == DeploymentStrategy.AB_TEST:
                await self._deploy_ab_test(version_id)
            else:
                await self._deploy_rolling(version_id)
            
            logger.info(f"Deployed version {version_id} to production using {strategy.value}")
            
        except Exception as e:
            logger.error(f"Failed to deploy version {version_id}: {e}")
            raise
    
    async def _deploy_blue_green(self, version_id: str):
        """Blue-green deployment strategy"""
        old_production = self.production_version
        
        # Update production version
        await self.update_version_status(version_id, ModelStatus.PRODUCTION)
        self.production_version = version_id
        
        # Update Redis for real-time switching
        if self.redis_client:
            await self.redis_client.set("production_model_version", version_id)
            await self.redis_client.set("deployment_strategy", "blue_green")
        
        # Deprecate old version after successful deployment
        if old_production:
            await self.update_version_status(old_production, ModelStatus.DEPRECATED)
    
    async def _deploy_canary(self, version_id: str, traffic_percentage: float = 10.0):
        """Canary deployment with gradual traffic increase"""
        # Set up canary configuration
        canary_config = {
            "canary_version": version_id,
            "production_version": self.production_version,
            "traffic_percentage": traffic_percentage,
            "start_time": datetime.now().isoformat(),
            "monitoring_period_hours": 2
        }
        
        if self.redis_client:
            await self.redis_client.set("canary_deployment", json.dumps(canary_config))
        
        await self.update_version_status(version_id, ModelStatus.PRODUCTION)
        logger.info(f"Started canary deployment with {traffic_percentage}% traffic")
    
    async def _deploy_ab_test(self, version_id: str):
        """Deploy as A/B test"""
        if not self.production_version:
            raise ValueError("Need existing production version for A/B test")
        
        # Create A/B test configuration
        test_config = ABTestConfig(
            test_id=f"ab_test_{uuid.uuid4().hex[:8]}",
            name=f"Model A/B Test: {self.production_version} vs {version_id}",
            description="Comparing model performance",
            model_a_version=self.production_version,
            model_b_version=version_id,
            traffic_split=50.0,  # 50/50 split
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(days=7),
            success_metrics=["accuracy", "false_positive_rate", "inference_time"]
        )
        
        # Store A/B test
        self.active_ab_tests[test_config.test_id] = test_config
        await self._save_ab_test_config(test_config)
        
        await self.update_version_status(version_id, ModelStatus.PRODUCTION)
        logger.info(f"Started A/B test: {test_config.test_id}")
    
    async def rollback_version(self, target_version_id: Optional[str] = None) -> str:
        """Rollback to previous or specified version"""
        try:
            if target_version_id:
                if target_version_id not in self.versions:
                    raise ValueError(f"Target version {target_version_id} not found")
                rollback_to = target_version_id
            else:
                # Find last known good version
                rollback_to = self._find_rollback_version()
                if not rollback_to:
                    raise ValueError("No suitable rollback version found")
            
            logger.info(f"Rolling back to version: {rollback_to}")
            
            # Stop any active A/B tests
            for test_id, test_config in self.active_ab_tests.items():
                if test_config.model_b_version == self.production_version:
                    test_config.is_active = False
                    await self._save_ab_test_config(test_config)
            
            # Update production version
            old_version = self.production_version
            self.production_version = rollback_to
            
            # Update statuses
            if old_version:
                await self.update_version_status(old_version, ModelStatus.DEPRECATED)
            await self.update_version_status(rollback_to, ModelStatus.PRODUCTION)
            
            # Update Redis
            if self.redis_client:
                await self.redis_client.set("production_model_version", rollback_to)
                await self.redis_client.set("last_rollback", json.dumps({
                    "from_version": old_version,
                    "to_version": rollback_to,
                    "timestamp": datetime.now().isoformat(),
                    "reason": "manual_rollback"
                }))
            
            logger.info(f"Successfully rolled back from {old_version} to {rollback_to}")
            return rollback_to
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            raise
    
    async def get_model_for_prediction(self, session_id: str) -> Tuple[AdvancedEnsembleModel, str]:
        """Get the appropriate model for prediction based on routing rules"""
        try:
            # Check for active A/B tests
            for test_id, test_config in self.active_ab_tests.items():
                if test_config.is_active and self._should_use_ab_test(test_config, session_id):
                    model_version = self._route_ab_traffic(test_config, session_id)
                    if model_version in self.active_models:
                        return self.active_models[model_version], model_version
            
            # Check for canary deployment
            if self.redis_client:
                canary_config_str = await self.redis_client.get("canary_deployment")
                if canary_config_str:
                    canary_config = json.loads(canary_config_str)
                    if self._should_use_canary(canary_config, session_id):
                        canary_version = canary_config["canary_version"]
                        if canary_version in self.active_models:
                            return self.active_models[canary_version], canary_version
            
            # Use production version
            if self.production_version and self.production_version in self.active_models:
                return self.active_models[self.production_version], self.production_version
            
            # Fallback to any available model
            if self.active_models:
                version_id = next(iter(self.active_models.keys()))
                return self.active_models[version_id], version_id
            
            raise RuntimeError("No models available for prediction")
            
        except Exception as e:
            logger.error(f"Failed to get model for prediction: {e}")
            raise
    
    def _should_use_ab_test(self, test_config: ABTestConfig, session_id: str) -> bool:
        """Determine if session should participate in A/B test"""
        if not test_config.is_active:
            return False
        
        now = datetime.now()
        if now < test_config.start_time or now > test_config.end_time:
            return False
        
        return True
    
    def _route_ab_traffic(self, test_config: ABTestConfig, session_id: str) -> str:
        """Route traffic between A/B test models"""
        # Use session ID hash for consistent routing
        session_hash = hashlib.md5(session_id.encode()).hexdigest()
        hash_value = int(session_hash[:8], 16)
        
        # Route based on traffic split
        if (hash_value % 100) < test_config.traffic_split:
            return test_config.model_b_version
        else:
            return test_config.model_a_version
    
    def _should_use_canary(self, canary_config: Dict[str, Any], session_id: str) -> bool:
        """Determine if session should use canary version"""
        session_hash = hashlib.md5(session_id.encode()).hexdigest()
        hash_value = int(session_hash[:8], 16)
        
        traffic_percentage = canary_config.get("traffic_percentage", 10.0)
        return (hash_value % 100) < traffic_percentage
    
    async def log_prediction_result(self, version_id: str, prediction: EnsemblePrediction, 
                                  actual_result: Optional[bool] = None, session_metadata: Dict[str, Any] = None):
        """Log prediction result for model performance tracking"""
        try:
            result_log = {
                "timestamp": datetime.now().isoformat(),
                "version_id": version_id,
                "risk_score": prediction.final_risk_score,
                "confidence": prediction.final_confidence,
                "inference_time_ms": prediction.total_inference_time_ms,
                "actual_result": actual_result,
                "session_metadata": session_metadata or {}
            }
            
            # Store in version history
            if version_id not in self.performance_history:
                self.performance_history[version_id] = []
            
            self.performance_history[version_id].append(result_log)
            
            # Keep only recent history
            if len(self.performance_history[version_id]) > 10000:
                self.performance_history[version_id] = self.performance_history[version_id][-5000:]
            
            # Store in Redis for real-time monitoring
            if self.redis_client:
                await self.redis_client.lpush(f"predictions:{version_id}", json.dumps(result_log))
                await self.redis_client.ltrim(f"predictions:{version_id}", 0, 9999)
                await self.redis_client.expire(f"predictions:{version_id}", 86400)  # 24 hours
            
            # Update A/B test results if applicable
            await self._update_ab_test_metrics(version_id, prediction, actual_result)
            
        except Exception as e:
            logger.error(f"Failed to log prediction result: {e}")
    
    async def _update_ab_test_metrics(self, version_id: str, prediction: EnsemblePrediction, actual_result: Optional[bool]):
        """Update A/B test metrics with new prediction"""
        for test_id, test_config in self.active_ab_tests.items():
            if version_id in [test_config.model_a_version, test_config.model_b_version]:
                
                if test_id not in self.ab_test_results:
                    self.ab_test_results[test_id] = ABTestResult(
                        test_id=test_id,
                        model_a_metrics={},
                        model_b_metrics={},
                        sample_size_a=0,
                        sample_size_b=0,
                        statistical_significance=False,
                        winner=None,
                        confidence_level=0.0
                    )
                
                result = self.ab_test_results[test_id]
                
                # Update metrics
                if version_id == test_config.model_a_version:
                    result.sample_size_a += 1
                    self._update_metrics_dict(result.model_a_metrics, prediction, actual_result)
                else:
                    result.sample_size_b += 1
                    self._update_metrics_dict(result.model_b_metrics, prediction, actual_result)
                
                # Check for statistical significance
                if result.sample_size_a > 100 and result.sample_size_b > 100:
                    await self._calculate_statistical_significance(test_id)
    
    def _update_metrics_dict(self, metrics_dict: Dict[str, float], prediction: EnsemblePrediction, actual_result: Optional[bool]):
        """Update metrics dictionary with new prediction"""
        # Initialize if empty
        if not metrics_dict:
            metrics_dict.update({
                "avg_risk_score": 0.0,
                "avg_confidence": 0.0,
                "avg_inference_time": 0.0,
                "accuracy": 0.0,
                "false_positive_rate": 0.0,
                "count": 0
            })
        
        count = metrics_dict["count"]
        
        # Update running averages
        metrics_dict["avg_risk_score"] = (metrics_dict["avg_risk_score"] * count + prediction.final_risk_score) / (count + 1)
        metrics_dict["avg_confidence"] = (metrics_dict["avg_confidence"] * count + prediction.final_confidence) / (count + 1)
        metrics_dict["avg_inference_time"] = (metrics_dict["avg_inference_time"] * count + prediction.total_inference_time_ms) / (count + 1)
        
        # Update accuracy if actual result is available
        if actual_result is not None:
            predicted_positive = prediction.final_risk_score > 0.5
            is_correct = predicted_positive == actual_result
            
            metrics_dict["accuracy"] = (metrics_dict["accuracy"] * count + (1.0 if is_correct else 0.0)) / (count + 1)
            
            # Update false positive rate
            if not actual_result and predicted_positive:
                current_fp = metrics_dict["false_positive_rate"] * count
                metrics_dict["false_positive_rate"] = (current_fp + 1.0) / (count + 1)
            else:
                metrics_dict["false_positive_rate"] = (metrics_dict["false_positive_rate"] * count) / (count + 1)
        
        metrics_dict["count"] = count + 1
    
    async def _calculate_statistical_significance(self, test_id: str):
        """Calculate statistical significance for A/B test"""
        try:
            result = self.ab_test_results[test_id]
            
            # Simple significance test based on accuracy difference
            accuracy_a = result.model_a_metrics.get("accuracy", 0.5)
            accuracy_b = result.model_b_metrics.get("accuracy", 0.5)
            
            sample_size_a = result.sample_size_a
            sample_size_b = result.sample_size_b
            
            # Calculate standard error and z-score
            p_pooled = (accuracy_a * sample_size_a + accuracy_b * sample_size_b) / (sample_size_a + sample_size_b)
            se_diff = np.sqrt(p_pooled * (1 - p_pooled) * (1/sample_size_a + 1/sample_size_b))
            
            if se_diff > 0:
                z_score = abs(accuracy_a - accuracy_b) / se_diff
                
                # 95% confidence level (z > 1.96)
                result.statistical_significance = z_score > 1.96
                result.confidence_level = min(0.99, 2 * (1 - 0.5 * (1 + np.tanh(z_score - 1.96))))
                
                # Determine winner
                if result.statistical_significance:
                    if accuracy_a > accuracy_b:
                        result.winner = self.active_ab_tests[test_id].model_a_version
                    else:
                        result.winner = self.active_ab_tests[test_id].model_b_version
                
                logger.info(f"A/B test {test_id}: significance={result.statistical_significance}, confidence={result.confidence_level:.3f}")
            
        except Exception as e:
            logger.error(f"Failed to calculate statistical significance: {e}")
    
    async def get_model_performance(self, version_id: str, hours: int = 24) -> Dict[str, Any]:
        """Get performance metrics for a model version"""
        try:
            if version_id not in self.performance_history:
                return {}
            
            # Get recent history
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_logs = [
                log for log in self.performance_history[version_id]
                if datetime.fromisoformat(log["timestamp"]) > cutoff_time
            ]
            
            if not recent_logs:
                return {}
            
            # Calculate metrics
            risk_scores = [log["risk_score"] for log in recent_logs]
            confidences = [log["confidence"] for log in recent_logs]
            inference_times = [log["inference_time_ms"] for log in recent_logs]
            
            # Accuracy metrics (if actual results available)
            with_results = [log for log in recent_logs if log["actual_result"] is not None]
            
            performance = {
                "version_id": version_id,
                "time_period_hours": hours,
                "total_predictions": len(recent_logs),
                "avg_risk_score": np.mean(risk_scores),
                "avg_confidence": np.mean(confidences),
                "avg_inference_time_ms": np.mean(inference_times),
                "p95_inference_time_ms": np.percentile(inference_times, 95),
                "max_inference_time_ms": np.max(inference_times)
            }
            
            if with_results:
                correct_predictions = sum(
                    1 for log in with_results
                    if (log["risk_score"] > 0.5) == log["actual_result"]
                )
                performance["accuracy"] = correct_predictions / len(with_results)
                
                # False positive rate
                negatives = [log for log in with_results if not log["actual_result"]]
                if negatives:
                    false_positives = sum(1 for log in negatives if log["risk_score"] > 0.5)
                    performance["false_positive_rate"] = false_positives / len(negatives)
            
            return performance
            
        except Exception as e:
            logger.error(f"Failed to get model performance: {e}")
            return {}
    
    async def auto_promote_model(self, version_id: str, min_predictions: int = 1000, min_accuracy: float = 0.95) -> bool:
        """Automatically promote model if it meets performance criteria"""
        try:
            performance = await self.get_model_performance(version_id, hours=24)
            
            if not performance:
                return False
            
            # Check promotion criteria
            meets_volume = performance.get("total_predictions", 0) >= min_predictions
            meets_accuracy = performance.get("accuracy", 0.0) >= min_accuracy
            meets_fpr = performance.get("false_positive_rate", 1.0) <= 0.01
            meets_latency = performance.get("p95_inference_time_ms", 1000) <= 50
            
            if meets_volume and meets_accuracy and meets_fpr and meets_latency:
                logger.info(f"Auto-promoting version {version_id} to production")
                await self.deploy_to_production(version_id, DeploymentStrategy.BLUE_GREEN)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Auto-promotion failed for version {version_id}: {e}")
            return False
    
    def _get_next_version_number(self, model_name: str) -> str:
        """Get next version number for model"""
        existing_versions = [
            v for v in self.versions.values()
            if v.model_name == model_name
        ]
        
        if not existing_versions:
            return "1.0.0"
        
        # Extract version numbers and increment
        version_numbers = []
        for v in existing_versions:
            try:
                parts = v.version_number.split('.')
                version_numbers.append((int(parts[0]), int(parts[1]), int(parts[2])))
            except (ValueError, IndexError):
                continue
        
        if not version_numbers:
            return "1.0.0"
        
        # Get latest version and increment patch
        latest = max(version_numbers)
        return f"{latest[0]}.{latest[1]}.{latest[2] + 1}"
    
    async def _calculate_model_hash(self, version_dir: Path) -> str:
        """Calculate hash of model files"""
        hash_md5 = hashlib.md5()
        
        for file_path in sorted(version_dir.glob("**/*")):
            if file_path.is_file():
                with open(file_path, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hash_md5.update(chunk)
        
        return hash_md5.hexdigest()
    
    def _create_feature_schema(self, training_data: pd.DataFrame) -> Dict[str, str]:
        """Create feature schema from training data"""
        schema = {}
        for column in training_data.columns:
            dtype = str(training_data[column].dtype)
            schema[column] = dtype
        return schema
    
    def _extract_best_metrics(self, training_results: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        """Extract best metrics from training results"""
        best_metrics = {}
        
        for model_name, metrics in training_results.items():
            for metric_name, value in metrics.items():
                key = f"best_{metric_name}"
                if key not in best_metrics or value > best_metrics[key]:
                    best_metrics[key] = value
                    best_metrics[f"{key}_model"] = model_name
        
        return best_metrics
    
    def _find_rollback_version(self) -> Optional[str]:
        """Find suitable rollback version"""
        # Look for last stable production version
        production_versions = [
            v for v in self.versions.values()
            if v.status == ModelStatus.PRODUCTION and v.version_id != self.production_version
        ]
        
        if production_versions:
            # Return most recent production version
            return max(production_versions, key=lambda v: v.created_at).version_id
        
        # Look for staged versions
        staged_versions = [
            v for v in self.versions.values()
            if v.status == ModelStatus.STAGED
        ]
        
        if staged_versions:
            return max(staged_versions, key=lambda v: v.created_at).version_id
        
        return None
    
    async def update_version_status(self, version_id: str, status: ModelStatus):
        """Update version status"""
        if version_id in self.versions:
            self.versions[version_id].status = status
            await self._save_version_metadata(self.versions[version_id])
            
            if self.redis_client:
                await self.redis_client.set(f"version_status:{version_id}", status.value)
    
    async def load_versions(self):
        """Load existing versions from disk"""
        try:
            for version_dir in self.base_path.iterdir():
                if version_dir.is_dir():
                    metadata_file = version_dir / "version_metadata.json"
                    if metadata_file.exists():
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        
                        version = ModelVersion(
                            version_id=metadata["version_id"],
                            model_name=metadata["model_name"],
                            version_number=metadata["version_number"],
                            created_at=datetime.fromisoformat(metadata["created_at"]),
                            status=ModelStatus(metadata["status"]),
                            performance_metrics=metadata["performance_metrics"],
                            model_hash=metadata["model_hash"],
                            training_data_hash=metadata["training_data_hash"],
                            feature_schema=metadata["feature_schema"],
                            deployment_config=metadata["deployment_config"],
                            a_b_test_config=metadata.get("a_b_test_config"),
                            rollback_version=metadata.get("rollback_version")
                        )
                        
                        self.versions[version.version_id] = version
                        
                        # Set production version
                        if version.status == ModelStatus.PRODUCTION:
                            self.production_version = version.version_id
            
            logger.info(f"Loaded {len(self.versions)} model versions")
            
        except Exception as e:
            logger.error(f"Failed to load versions: {e}")
    
    async def load_active_models(self):
        """Load models for active versions"""
        try:
            active_statuses = [ModelStatus.PRODUCTION, ModelStatus.STAGED, ModelStatus.TESTING]
            
            for version_id, version in self.versions.items():
                if version.status in active_statuses:
                    version_dir = self.base_path / version_id
                    if version_dir.exists():
                        model = AdvancedEnsembleModel(str(version_dir))
                        await model.initialize_models()
                        self.active_models[version_id] = model
                        logger.info(f"Loaded model for version: {version_id}")
            
        except Exception as e:
            logger.error(f"Failed to load active models: {e}")
    
    async def load_ab_tests(self):
        """Load active A/B tests"""
        try:
            ab_test_file = self.base_path / "ab_tests.json"
            if ab_test_file.exists():
                with open(ab_test_file, 'r') as f:
                    tests_data = json.load(f)
                
                for test_data in tests_data:
                    test_config = ABTestConfig(
                        test_id=test_data["test_id"],
                        name=test_data["name"],
                        description=test_data["description"],
                        model_a_version=test_data["model_a_version"],
                        model_b_version=test_data["model_b_version"],
                        traffic_split=test_data["traffic_split"],
                        start_time=datetime.fromisoformat(test_data["start_time"]),
                        end_time=datetime.fromisoformat(test_data["end_time"]),
                        success_metrics=test_data["success_metrics"],
                        is_active=test_data["is_active"]
                    )
                    
                    self.active_ab_tests[test_config.test_id] = test_config
            
        except Exception as e:
            logger.error(f"Failed to load A/B tests: {e}")
    
    async def _save_version_metadata(self, version: ModelVersion):
        """Save version metadata to disk"""
        try:
            version_dir = self.base_path / version.version_id
            version_dir.mkdir(exist_ok=True)
            
            metadata_file = version_dir / "version_metadata.json"
            with open(metadata_file, 'w') as f:
                metadata = asdict(version)
                metadata["created_at"] = version.created_at.isoformat()
                metadata["status"] = version.status.value
                json.dump(metadata, f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to save version metadata: {e}")
    
    async def _save_ab_test_config(self, test_config: ABTestConfig):
        """Save A/B test configuration"""
        try:
            ab_test_file = self.base_path / "ab_tests.json"
            
            # Load existing tests
            if ab_test_file.exists():
                with open(ab_test_file, 'r') as f:
                    tests_data = json.load(f)
            else:
                tests_data = []
            
            # Update or add test config
            test_dict = asdict(test_config)
            test_dict["start_time"] = test_config.start_time.isoformat()
            test_dict["end_time"] = test_config.end_time.isoformat()
            
            # Remove existing config for same test_id
            tests_data = [t for t in tests_data if t["test_id"] != test_config.test_id]
            tests_data.append(test_dict)
            
            # Save updated tests
            with open(ab_test_file, 'w') as f:
                json.dump(tests_data, f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to save A/B test config: {e}")
    
    async def cleanup_old_versions(self, keep_count: int = 5):
        """Clean up old model versions"""
        try:
            # Group versions by model name
            versions_by_model = {}
            for version in self.versions.values():
                if version.model_name not in versions_by_model:
                    versions_by_model[version.model_name] = []
                versions_by_model[version.model_name].append(version)
            
            # Clean up each model's old versions
            for model_name, versions in versions_by_model.items():
                # Sort by creation date, newest first
                versions.sort(key=lambda v: v.created_at, reverse=True)
                
                # Keep recent versions and production/staged versions
                to_keep = []
                for version in versions:
                    if (len(to_keep) < keep_count or 
                        version.status in [ModelStatus.PRODUCTION, ModelStatus.STAGED]):
                        to_keep.append(version)
                
                # Delete old versions
                for version in versions:
                    if version not in to_keep and version.status == ModelStatus.DEPRECATED:
                        await self._delete_version(version.version_id)
            
            logger.info("Cleaned up old model versions")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old versions: {e}")
    
    async def _delete_version(self, version_id: str):
        """Delete a model version"""
        try:
            # Remove from memory
            if version_id in self.versions:
                del self.versions[version_id]
            
            if version_id in self.active_models:
                del self.active_models[version_id]
            
            # Delete directory
            version_dir = self.base_path / version_id
            if version_dir.exists():
                shutil.rmtree(version_dir)
            
            logger.info(f"Deleted version: {version_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete version {version_id}: {e}")