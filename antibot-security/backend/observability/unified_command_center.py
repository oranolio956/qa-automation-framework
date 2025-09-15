"""
Unified Observability Command Center with AI-Driven Insights
===============================================================

Advanced observability platform that aggregates telemetry from all microservices,
applies machine learning for threat detection, and provides predictive security insights.

Key Features:
- Real-time threat detection with ML models
- Predictive anomaly detection across all services
- Intelligent alerting with context-aware notifications
- Advanced correlation analysis for security events
- AI-powered incident response recommendations
- Unified dashboard with interactive visualizations
"""

import asyncio
import logging
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import aioredis
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
import joblib
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
from opentelemetry import trace, metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import websockets
import uvicorn
from fastapi import FastAPI, WebSocket, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ThreatLevel(Enum):
    """Security threat severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertType(Enum):
    """Types of security alerts"""
    ANOMALY_DETECTION = "anomaly_detection"
    THREAT_INTELLIGENCE = "threat_intelligence"
    BEHAVIOR_ANALYSIS = "behavior_analysis"
    INFRASTRUCTURE = "infrastructure"
    PERFORMANCE = "performance"

@dataclass
class SecurityAlert:
    """Security alert with enriched context"""
    id: str
    alert_type: AlertType
    threat_level: ThreatLevel
    title: str
    description: str
    timestamp: datetime
    source_service: str
    affected_services: List[str]
    metrics: Dict[str, float]
    recommendations: List[str]
    correlation_id: Optional[str] = None
    ai_confidence: float = 0.0
    predicted_impact: str = ""
    mitigation_steps: List[str] = field(default_factory=list)

@dataclass
class ThreatIntelligence:
    """AI-driven threat intelligence insights"""
    threat_id: str
    attack_vector: str
    confidence_score: float
    predicted_targets: List[str]
    timeline_prediction: str
    countermeasures: List[str]
    related_incidents: List[str]
    risk_assessment: Dict[str, float]

class AIAnomalyDetector:
    """Advanced ML-based anomaly detection system"""
    
    def __init__(self):
        self.models: Dict[str, Any] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        self.training_data: Dict[str, pd.DataFrame] = {}
        self.model_performance: Dict[str, float] = {}
        
    async def initialize_models(self):
        """Initialize ML models for different service types"""
        try:
            # Isolation Forest for general anomaly detection
            self.models['isolation_forest'] = IsolationForest(
                contamination=0.1,
                random_state=42,
                n_estimators=100
            )
            
            # DBSCAN for clustering-based anomaly detection
            self.models['dbscan'] = DBSCAN(eps=0.5, min_samples=5)
            
            # Initialize scalers for each service type
            service_types = ['auth', 'biometric', 'tls', 'temporal', 'messaging']
            for service_type in service_types:
                self.scalers[service_type] = StandardScaler()
                
            logger.info("AI anomaly detection models initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ML models: {e}")
            raise

    async def train_model(self, service_type: str, historical_data: pd.DataFrame):
        """Train anomaly detection model with historical data"""
        try:
            # Prepare features
            features = self._extract_features(historical_data)
            
            # Scale features
            scaled_features = self.scalers[service_type].fit_transform(features)
            
            # Train isolation forest
            self.models['isolation_forest'].fit(scaled_features)
            
            # Store training data for reference
            self.training_data[service_type] = historical_data
            
            # Evaluate model performance
            anomaly_scores = self.models['isolation_forest'].decision_function(scaled_features)
            performance_score = np.mean(anomaly_scores > -0.5)
            self.model_performance[service_type] = performance_score
            
            logger.info(f"Model trained for {service_type} with performance: {performance_score:.3f}")
            
        except Exception as e:
            logger.error(f"Failed to train model for {service_type}: {e}")
            raise

    def _extract_features(self, data: pd.DataFrame) -> np.ndarray:
        """Extract relevant features from telemetry data"""
        try:
            features = []
            
            # Numerical features
            numerical_cols = data.select_dtypes(include=[np.number]).columns
            for col in numerical_cols:
                features.extend([
                    data[col].mean(),
                    data[col].std(),
                    data[col].min(),
                    data[col].max(),
                    data[col].quantile(0.95)
                ])
            
            # Time-based features
            if 'timestamp' in data.columns:
                data['timestamp'] = pd.to_datetime(data['timestamp'])
                features.extend([
                    data['timestamp'].dt.hour.mean(),
                    data['timestamp'].dt.dayofweek.mean(),
                    len(data) / (data['timestamp'].max() - data['timestamp'].min()).total_seconds() * 3600
                ])
            
            return np.array(features).reshape(1, -1)
            
        except Exception as e:
            logger.error(f"Failed to extract features: {e}")
            return np.array([[0.0]])

    async def detect_anomalies(self, service_type: str, current_metrics: Dict[str, float]) -> Tuple[bool, float]:
        """Detect anomalies in real-time metrics"""
        try:
            if service_type not in self.models:
                return False, 0.0
            
            # Convert metrics to feature vector
            feature_vector = np.array(list(current_metrics.values())).reshape(1, -1)
            
            # Scale features
            if service_type in self.scalers:
                feature_vector = self.scalers[service_type].transform(feature_vector)
            
            # Predict anomaly
            anomaly_score = self.models['isolation_forest'].decision_function(feature_vector)[0]
            is_anomaly = self.models['isolation_forest'].predict(feature_vector)[0] == -1
            
            # Convert score to confidence (0-1)
            confidence = max(0.0, min(1.0, (0.5 - anomaly_score) / 0.5))
            
            return is_anomaly, confidence
            
        except Exception as e:
            logger.error(f"Failed to detect anomalies for {service_type}: {e}")
            return False, 0.0

class ThreatIntelligenceEngine:
    """AI-powered threat intelligence and prediction system"""
    
    def __init__(self):
        self.threat_patterns: Dict[str, List[Dict]] = {}
        self.attack_signatures: Dict[str, str] = {}
        self.intelligence_cache: Dict[str, ThreatIntelligence] = {}
        
    async def initialize_intelligence(self):
        """Initialize threat intelligence database"""
        try:
            # Load known attack patterns
            self.threat_patterns = {
                'credential_stuffing': [
                    {'pattern': 'high_login_failure_rate', 'weight': 0.8},
                    {'pattern': 'distributed_ips', 'weight': 0.6},
                    {'pattern': 'common_passwords', 'weight': 0.9}
                ],
                'bot_detection_evasion': [
                    {'pattern': 'tls_fingerprint_rotation', 'weight': 0.7},
                    {'pattern': 'behavioral_mimicry', 'weight': 0.8},
                    {'pattern': 'captcha_solving_patterns', 'weight': 0.9}
                ],
                'ddos_attack': [
                    {'pattern': 'traffic_spike', 'weight': 0.9},
                    {'pattern': 'request_uniformity', 'weight': 0.7},
                    {'pattern': 'resource_exhaustion', 'weight': 0.8}
                ]
            }
            
            # Initialize attack signatures
            self.attack_signatures = {
                'sql_injection': r'(\b(union|select|insert|delete|update|drop)\b)',
                'xss_attempt': r'(<script|javascript:|onerror=|onload=)',
                'path_traversal': r'(\.\./|\.\.\\\)',
                'command_injection': r'(;|\||\`|\$\()'
            }
            
            logger.info("Threat intelligence engine initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize threat intelligence: {e}")
            raise

    async def analyze_threat_patterns(self, security_events: List[Dict]) -> List[ThreatIntelligence]:
        """Analyze security events for threat patterns"""
        try:
            threats = []
            
            for attack_type, patterns in self.threat_patterns.items():
                threat_score = await self._calculate_threat_score(security_events, patterns)
                
                if threat_score > 0.6:  # Threshold for threat detection
                    threat = ThreatIntelligence(
                        threat_id=f"{attack_type}_{datetime.now().isoformat()}",
                        attack_vector=attack_type,
                        confidence_score=threat_score,
                        predicted_targets=await self._predict_targets(attack_type, security_events),
                        timeline_prediction=await self._predict_timeline(attack_type, threat_score),
                        countermeasures=await self._recommend_countermeasures(attack_type),
                        related_incidents=await self._find_related_incidents(attack_type),
                        risk_assessment=await self._assess_risk_impact(attack_type, threat_score)
                    )
                    threats.append(threat)
                    
            return threats
            
        except Exception as e:
            logger.error(f"Failed to analyze threat patterns: {e}")
            return []

    async def _calculate_threat_score(self, events: List[Dict], patterns: List[Dict]) -> float:
        """Calculate composite threat score based on patterns"""
        try:
            total_score = 0.0
            total_weight = 0.0
            
            for pattern in patterns:
                pattern_score = await self._match_pattern(events, pattern['pattern'])
                weighted_score = pattern_score * pattern['weight']
                total_score += weighted_score
                total_weight += pattern['weight']
                
            return total_score / total_weight if total_weight > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Failed to calculate threat score: {e}")
            return 0.0

    async def _predict_targets(self, attack_type: str, events: List[Dict]) -> List[str]:
        """Predict likely targets based on attack type and current events"""
        try:
            targets = []
            
            # Extract affected services from events
            services = set()
            for event in events:
                if 'service' in event:
                    services.add(event['service'])
                if 'affected_services' in event:
                    services.update(event['affected_services'])
            
            # Predict additional targets based on attack type
            if attack_type == 'credential_stuffing':
                targets.extend(['auth-service', 'user-management', 'session-service'])
            elif attack_type == 'bot_detection_evasion':
                targets.extend(['biometric-service', 'tls-service', 'behavioral-analytics'])
            elif attack_type == 'ddos_attack':
                targets.extend(['load-balancer', 'api-gateway', 'database-cluster'])
                
            return list(set(targets) | services)
            
        except Exception as e:
            logger.error(f"Failed to predict targets: {e}")
            return []

    async def _predict_timeline(self, attack_type: str, confidence: float) -> str:
        """Predict attack timeline based on type and confidence"""
        try:
            if confidence > 0.9:
                return "Immediate action required - attack likely in progress"
            elif confidence > 0.8:
                return "High probability of attack within next 1-2 hours"
            elif confidence > 0.7:
                return "Moderate risk - monitor closely for next 6-12 hours"
            else:
                return "Low immediate risk - maintain standard monitoring"
                
        except Exception as e:
            logger.error(f"Failed to predict timeline: {e}")
            return "Unable to determine timeline"

    async def _recommend_countermeasures(self, attack_type: str) -> List[str]:
        """Recommend specific countermeasures for detected attack type"""
        try:
            countermeasures = {
                'credential_stuffing': [
                    "Enable rate limiting on authentication endpoints",
                    "Implement progressive delays for failed logins",
                    "Activate IP-based blocking for suspicious patterns",
                    "Enhance CAPTCHA verification for high-risk logins",
                    "Enable multi-factor authentication enforcement"
                ],
                'bot_detection_evasion': [
                    "Increase TLS fingerprint randomization frequency",
                    "Enhance behavioral biometric sensitivity",
                    "Activate advanced CAPTCHA challenges",
                    "Implement honeypot detection mechanisms",
                    "Increase mouse/keyboard pattern verification"
                ],
                'ddos_attack': [
                    "Activate traffic shaping and rate limiting",
                    "Enable CDN-based DDoS protection",
                    "Scale up infrastructure resources",
                    "Implement emergency traffic filtering",
                    "Activate backup service endpoints"
                ]
            }
            
            return countermeasures.get(attack_type, [
                "Implement general security monitoring",
                "Review and update security policies",
                "Monitor affected services closely"
            ])
            
        except Exception as e:
            logger.error(f"Failed to recommend countermeasures: {e}")
            return []

    async def _find_related_incidents(self, attack_type: str) -> List[str]:
        """Find related historical incidents"""
        try:
            # In production, this would query historical incident database
            # For now, return simulated related incidents
            return [
                f"INC-{datetime.now().strftime('%Y%m%d')}-001",
                f"INC-{(datetime.now() - timedelta(days=1)).strftime('%Y%m%d')}-003"
            ]
            
        except Exception as e:
            logger.error(f"Failed to find related incidents: {e}")
            return []

    async def _assess_risk_impact(self, attack_type: str, confidence: float) -> Dict[str, float]:
        """Assess potential business impact of detected threat"""
        try:
            base_impact = {
                'credential_stuffing': {
                    'user_accounts': 0.8,
                    'data_confidentiality': 0.9,
                    'service_availability': 0.4,
                    'reputation': 0.7
                },
                'bot_detection_evasion': {
                    'security_effectiveness': 0.9,
                    'false_positive_rate': 0.6,
                    'user_experience': 0.5,
                    'compliance_risk': 0.7
                },
                'ddos_attack': {
                    'service_availability': 0.95,
                    'revenue_impact': 0.8,
                    'user_experience': 0.9,
                    'operational_cost': 0.6
                }
            }
            
            # Scale impact by confidence level
            impact = base_impact.get(attack_type, {'general_risk': 0.5})
            scaled_impact = {key: value * confidence for key, value in impact.items()}
            
            return scaled_impact
            
        except Exception as e:
            logger.error(f"Failed to assess risk impact: {e}")
            return {'unknown_risk': 0.5}

class IntelligentAlertingSystem:
    """Context-aware alerting system with smart routing"""
    
    def __init__(self):
        self.alert_rules: Dict[str, Dict] = {}
        self.escalation_policies: Dict[str, List[Dict]] = {}
        self.alert_history: List[SecurityAlert] = []
        self.suppression_rules: Dict[str, Dict] = {}
        
    async def initialize_alerting(self):
        """Initialize alerting rules and policies"""
        try:
            # Define alert rules
            self.alert_rules = {
                'high_anomaly_score': {
                    'condition': lambda metrics: metrics.get('anomaly_confidence', 0) > 0.8,
                    'threat_level': ThreatLevel.HIGH,
                    'alert_type': AlertType.ANOMALY_DETECTION
                },
                'critical_service_failure': {
                    'condition': lambda metrics: metrics.get('error_rate', 0) > 0.5,
                    'threat_level': ThreatLevel.CRITICAL,
                    'alert_type': AlertType.INFRASTRUCTURE
                },
                'suspicious_behavior_pattern': {
                    'condition': lambda metrics: metrics.get('behavior_risk_score', 0) > 0.7,
                    'threat_level': ThreatLevel.MEDIUM,
                    'alert_type': AlertType.BEHAVIOR_ANALYSIS
                }
            }
            
            # Define escalation policies
            self.escalation_policies = {
                ThreatLevel.LOW.value: [
                    {'method': 'log', 'delay': 0},
                    {'method': 'slack', 'delay': 300}  # 5 minutes
                ],
                ThreatLevel.MEDIUM.value: [
                    {'method': 'slack', 'delay': 0},
                    {'method': 'email', 'delay': 60},  # 1 minute
                    {'method': 'sms', 'delay': 600}    # 10 minutes
                ],
                ThreatLevel.HIGH.value: [
                    {'method': 'slack', 'delay': 0},
                    {'method': 'email', 'delay': 0},
                    {'method': 'sms', 'delay': 30},    # 30 seconds
                    {'method': 'call', 'delay': 120}   # 2 minutes
                ],
                ThreatLevel.CRITICAL.value: [
                    {'method': 'slack', 'delay': 0},
                    {'method': 'email', 'delay': 0},
                    {'method': 'sms', 'delay': 0},
                    {'method': 'call', 'delay': 15},   # 15 seconds
                    {'method': 'incident_manager', 'delay': 30}  # 30 seconds
                ]
            }
            
            # Initialize suppression rules to prevent alert fatigue
            self.suppression_rules = {
                'duplicate_window': 300,  # 5 minutes
                'burst_threshold': 5,     # Max 5 similar alerts in window
                'correlation_window': 600 # 10 minutes for correlation
            }
            
            logger.info("Intelligent alerting system initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize alerting system: {e}")
            raise

    async def evaluate_alerts(self, service_metrics: Dict[str, Dict[str, float]]) -> List[SecurityAlert]:
        """Evaluate metrics against alert rules and generate alerts"""
        try:
            alerts = []
            
            for service, metrics in service_metrics.items():
                for rule_name, rule_config in self.alert_rules.items():
                    if rule_config['condition'](metrics):
                        alert = await self._create_alert(
                            rule_name, service, metrics, rule_config
                        )
                        
                        # Check suppression rules
                        if not await self._is_suppressed(alert):
                            alerts.append(alert)
                            
            # Apply correlation analysis
            correlated_alerts = await self._correlate_alerts(alerts)
            
            return correlated_alerts
            
        except Exception as e:
            logger.error(f"Failed to evaluate alerts: {e}")
            return []

    async def _create_alert(self, rule_name: str, service: str, metrics: Dict[str, float], 
                           rule_config: Dict) -> SecurityAlert:
        """Create security alert with enriched context"""
        try:
            alert_id = f"{rule_name}_{service}_{datetime.now().isoformat()}"
            
            # Generate intelligent recommendations
            recommendations = await self._generate_recommendations(rule_name, metrics)
            
            # Predict impact
            predicted_impact = await self._predict_alert_impact(rule_name, metrics)
            
            # Generate mitigation steps
            mitigation_steps = await self._generate_mitigation_steps(rule_name, service)
            
            alert = SecurityAlert(
                id=alert_id,
                alert_type=rule_config['alert_type'],
                threat_level=rule_config['threat_level'],
                title=f"{rule_name.replace('_', ' ').title()} - {service}",
                description=await self._generate_alert_description(rule_name, service, metrics),
                timestamp=datetime.now(),
                source_service=service,
                affected_services=await self._identify_affected_services(service, rule_name),
                metrics=metrics,
                recommendations=recommendations,
                ai_confidence=metrics.get('confidence', 0.8),
                predicted_impact=predicted_impact,
                mitigation_steps=mitigation_steps
            )
            
            return alert
            
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
            return None

    async def _generate_recommendations(self, rule_name: str, metrics: Dict[str, float]) -> List[str]:
        """Generate AI-powered recommendations for alert resolution"""
        try:
            recommendations = []
            
            if rule_name == 'high_anomaly_score':
                recommendations.extend([
                    f"Investigate anomalous behavior in service metrics",
                    f"Check for unusual traffic patterns or request volumes",
                    f"Verify authentication and authorization mechanisms",
                    f"Review recent deployments or configuration changes"
                ])
                
            elif rule_name == 'critical_service_failure':
                recommendations.extend([
                    f"Immediately check service health and error logs",
                    f"Verify database connectivity and performance",
                    f"Check external dependency availability",
                    f"Consider activating fallback mechanisms"
                ])
                
            elif rule_name == 'suspicious_behavior_pattern':
                recommendations.extend([
                    f"Analyze user behavior patterns and session data",
                    f"Increase biometric verification requirements",
                    f"Review TLS fingerprint variations",
                    f"Enable enhanced monitoring for affected users"
                ])
                
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            return ["Review service metrics and logs for anomalies"]

    async def _predict_alert_impact(self, rule_name: str, metrics: Dict[str, float]) -> str:
        """Predict potential impact of the alert"""
        try:
            confidence = metrics.get('confidence', 0.5)
            
            if rule_name == 'critical_service_failure':
                if confidence > 0.9:
                    return "Immediate service disruption affecting all users"
                else:
                    return "Potential service degradation for subset of users"
                    
            elif rule_name == 'high_anomaly_score':
                if confidence > 0.8:
                    return "Possible security breach requiring immediate investigation"
                else:
                    return "Suspicious activity requiring monitoring and analysis"
                    
            elif rule_name == 'suspicious_behavior_pattern':
                return "Potential bot activity or account compromise"
                
            return "Moderate impact requiring standard response procedures"
            
        except Exception as e:
            logger.error(f"Failed to predict alert impact: {e}")
            return "Impact assessment unavailable"

    async def _generate_mitigation_steps(self, rule_name: str, service: str) -> List[str]:
        """Generate specific mitigation steps for the alert"""
        try:
            steps = []
            
            if rule_name == 'critical_service_failure':
                steps.extend([
                    f"1. Verify {service} health status and error rates",
                    f"2. Check database connections and query performance",
                    f"3. Review recent deployments and rollback if necessary",
                    f"4. Scale up service instances if resource constrained",
                    f"5. Enable circuit breaker to prevent cascade failures"
                ])
                
            elif rule_name == 'high_anomaly_score':
                steps.extend([
                    f"1. Isolate suspicious traffic to {service}",
                    f"2. Increase logging verbosity for detailed analysis",
                    f"3. Implement temporary rate limiting",
                    f"4. Review user authentication patterns",
                    f"5. Coordinate with security team for threat assessment"
                ])
                
            elif rule_name == 'suspicious_behavior_pattern':
                steps.extend([
                    f"1. Increase biometric verification thresholds",
                    f"2. Enable additional behavioral analytics",
                    f"3. Implement challenge-response mechanisms",
                    f"4. Review and update bot detection rules",
                    f"5. Monitor affected user sessions closely"
                ])
                
            return steps
            
        except Exception as e:
            logger.error(f"Failed to generate mitigation steps: {e}")
            return ["Follow standard incident response procedures"]

    async def _identify_affected_services(self, source_service: str, rule_name: str) -> List[str]:
        """Identify services potentially affected by the alert"""
        try:
            # Service dependency mapping
            dependencies = {
                'auth-service': ['user-management', 'session-service', 'api-gateway'],
                'biometric-service': ['behavioral-analytics', 'fraud-detection'],
                'tls-service': ['proxy-service', 'traffic-analyzer'],
                'temporal-service': ['workflow-engine', 'task-scheduler'],
                'messaging-service': ['notification-service', 'event-processor']
            }
            
            affected = [source_service]
            
            # Add dependent services
            if source_service in dependencies:
                affected.extend(dependencies[source_service])
                
            # Add services that depend on this one
            for service, deps in dependencies.items():
                if source_service in deps and service not in affected:
                    affected.append(service)
                    
            return affected
            
        except Exception as e:
            logger.error(f"Failed to identify affected services: {e}")
            return [source_service]

    async def _generate_alert_description(self, rule_name: str, service: str, 
                                        metrics: Dict[str, float]) -> str:
        """Generate comprehensive alert description"""
        try:
            description_templates = {
                'high_anomaly_score': (
                    f"Anomalous behavior detected in {service} with confidence "
                    f"{metrics.get('anomaly_confidence', 0):.2f}. "
                    f"This indicates potential security threats or service irregularities."
                ),
                'critical_service_failure': (
                    f"Critical failure detected in {service} with error rate "
                    f"{metrics.get('error_rate', 0):.2f}. "
                    f"Immediate attention required to prevent service disruption."
                ),
                'suspicious_behavior_pattern': (
                    f"Suspicious behavioral patterns detected in {service} with risk score "
                    f"{metrics.get('behavior_risk_score', 0):.2f}. "
                    f"Possible bot activity or malicious behavior."
                )
            }
            
            return description_templates.get(
                rule_name, 
                f"Alert triggered for {rule_name} in service {service}"
            )
            
        except Exception as e:
            logger.error(f"Failed to generate alert description: {e}")
            return f"Alert generated for {service}"

    async def _is_suppressed(self, alert: SecurityAlert) -> bool:
        """Check if alert should be suppressed to prevent fatigue"""
        try:
            current_time = datetime.now()
            duplicate_window = timedelta(seconds=self.suppression_rules['duplicate_window'])
            
            # Count similar alerts in the window
            similar_count = 0
            for historical_alert in self.alert_history:
                if (current_time - historical_alert.timestamp) <= duplicate_window:
                    if (historical_alert.source_service == alert.source_service and
                        historical_alert.alert_type == alert.alert_type):
                        similar_count += 1
                        
            # Suppress if too many similar alerts
            if similar_count >= self.suppression_rules['burst_threshold']:
                logger.info(f"Suppressing alert {alert.id} due to burst threshold")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Failed to check suppression: {e}")
            return False

    async def _correlate_alerts(self, alerts: List[SecurityAlert]) -> List[SecurityAlert]:
        """Correlate related alerts and add correlation IDs"""
        try:
            if len(alerts) <= 1:
                return alerts
                
            correlation_window = timedelta(seconds=self.suppression_rules['correlation_window'])
            current_time = datetime.now()
            
            # Group alerts by time and affected services
            correlated_groups = []
            
            for alert in alerts:
                # Find if this alert belongs to an existing correlation group
                assigned = False
                for group in correlated_groups:
                    group_alert = group[0]  # Use first alert as reference
                    
                    # Check time window and service overlap
                    if (abs((alert.timestamp - group_alert.timestamp).total_seconds()) <= 
                        correlation_window.total_seconds()):
                        
                        # Check for service overlap
                        alert_services = set([alert.source_service] + alert.affected_services)
                        group_services = set([group_alert.source_service] + group_alert.affected_services)
                        
                        if alert_services.intersection(group_services):
                            group.append(alert)
                            assigned = True
                            break
                            
                if not assigned:
                    correlated_groups.append([alert])
                    
            # Assign correlation IDs to grouped alerts
            correlated_alerts = []
            for i, group in enumerate(correlated_groups):
                correlation_id = f"CORR-{current_time.strftime('%Y%m%d%H%M')}-{i+1:03d}"
                
                for alert in group:
                    alert.correlation_id = correlation_id
                    correlated_alerts.append(alert)
                    
            return correlated_alerts
            
        except Exception as e:
            logger.error(f"Failed to correlate alerts: {e}")
            return alerts

class VisualizationEngine:
    """Advanced visualization engine for security dashboards"""
    
    def __init__(self):
        self.dashboard_cache = {}
        
    async def create_threat_landscape_dashboard(self, threats: List[ThreatIntelligence], 
                                              alerts: List[SecurityAlert]) -> Dict[str, Any]:
        """Create comprehensive threat landscape visualization"""
        try:
            # Create subplot figure
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=(
                    'Threat Confidence Over Time', 
                    'Alert Distribution by Service',
                    'Risk Assessment Heatmap',
                    'Threat Timeline Prediction'
                ),
                specs=[[{"secondary_y": False}, {"type": "pie"}],
                       [{"type": "heatmap"}, {"secondary_y": False}]]
            )
            
            # Threat confidence timeline
            if threats:
                threat_times = [datetime.fromisoformat(t.threat_id.split('_')[1]) for t in threats]
                threat_scores = [t.confidence_score for t in threats]
                
                fig.add_trace(
                    go.Scatter(
                        x=threat_times, 
                        y=threat_scores,
                        mode='lines+markers',
                        name='Threat Confidence',
                        line=dict(color='red', width=3)
                    ),
                    row=1, col=1
                )
            
            # Alert distribution pie chart
            if alerts:
                alert_services = [alert.source_service for alert in alerts]
                service_counts = pd.Series(alert_services).value_counts()
                
                fig.add_trace(
                    go.Pie(
                        labels=service_counts.index.tolist(),
                        values=service_counts.values.tolist(),
                        name="Service Alerts"
                    ),
                    row=1, col=2
                )
            
            # Risk heatmap
            if threats:
                risk_data = []
                services = list(set([service for threat in threats for service in threat.predicted_targets]))
                
                for threat in threats:
                    for service in services:
                        risk_value = threat.confidence_score if service in threat.predicted_targets else 0
                        risk_data.append([threat.attack_vector, service, risk_value])
                        
                if risk_data:
                    df = pd.DataFrame(risk_data, columns=['Attack Type', 'Service', 'Risk'])
                    pivot_df = df.pivot(index='Attack Type', columns='Service', values='Risk').fillna(0)
                    
                    fig.add_trace(
                        go.Heatmap(
                            z=pivot_df.values,
                            x=pivot_df.columns.tolist(),
                            y=pivot_df.index.tolist(),
                            colorscale='Reds',
                            name="Risk Heatmap"
                        ),
                        row=2, col=1
                    )
            
            # Threat timeline
            if threats:
                timeline_data = [(t.attack_vector, t.confidence_score, t.timeline_prediction) for t in threats]
                timeline_df = pd.DataFrame(timeline_data, columns=['Attack', 'Confidence', 'Timeline'])
                
                fig.add_trace(
                    go.Bar(
                        x=timeline_df['Attack'],
                        y=timeline_df['Confidence'],
                        name='Timeline Predictions',
                        marker_color='orange'
                    ),
                    row=2, col=2
                )
            
            # Update layout
            fig.update_layout(
                title="Security Threat Intelligence Dashboard",
                height=800,
                showlegend=True,
                template="plotly_dark"
            )
            
            return {
                'dashboard': fig.to_dict(),
                'metrics': {
                    'total_threats': len(threats),
                    'total_alerts': len(alerts),
                    'avg_confidence': np.mean([t.confidence_score for t in threats]) if threats else 0,
                    'critical_alerts': len([a for a in alerts if a.threat_level == ThreatLevel.CRITICAL])
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to create dashboard: {e}")
            return {'dashboard': {}, 'metrics': {}}

    async def create_real_time_metrics_dashboard(self, service_metrics: Dict[str, Dict]) -> Dict[str, Any]:
        """Create real-time metrics visualization"""
        try:
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=(
                    'Service Response Times',
                    'Error Rates by Service', 
                    'Anomaly Scores',
                    'Resource Utilization'
                )
            )
            
            services = list(service_metrics.keys())
            
            # Response times
            response_times = [metrics.get('response_time_ms', 0) for metrics in service_metrics.values()]
            fig.add_trace(
                go.Bar(x=services, y=response_times, name='Response Time', marker_color='blue'),
                row=1, col=1
            )
            
            # Error rates
            error_rates = [metrics.get('error_rate', 0) * 100 for metrics in service_metrics.values()]
            fig.add_trace(
                go.Bar(x=services, y=error_rates, name='Error Rate %', marker_color='red'),
                row=1, col=2
            )
            
            # Anomaly scores
            anomaly_scores = [metrics.get('anomaly_confidence', 0) for metrics in service_metrics.values()]
            fig.add_trace(
                go.Scatter(x=services, y=anomaly_scores, mode='markers+lines', 
                          name='Anomaly Score', line_color='orange'),
                row=2, col=1
            )
            
            # Resource utilization
            cpu_usage = [metrics.get('cpu_usage', 0) for metrics in service_metrics.values()]
            memory_usage = [metrics.get('memory_usage', 0) for metrics in service_metrics.values()]
            
            fig.add_trace(
                go.Bar(x=services, y=cpu_usage, name='CPU %', marker_color='green'),
                row=2, col=2
            )
            fig.add_trace(
                go.Bar(x=services, y=memory_usage, name='Memory %', marker_color='purple'),
                row=2, col=2
            )
            
            fig.update_layout(
                title="Real-Time Service Metrics",
                height=600,
                showlegend=True,
                template="plotly_white"
            )
            
            return {
                'dashboard': fig.to_dict(),
                'summary': {
                    'avg_response_time': np.mean(response_times),
                    'max_error_rate': max(error_rates),
                    'services_with_anomalies': len([s for s in anomaly_scores if s > 0.5]),
                    'high_cpu_services': len([s for s in cpu_usage if s > 80])
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to create metrics dashboard: {e}")
            return {'dashboard': {}, 'summary': {}}

class UnifiedObservabilityCommandCenter:
    """
    Main orchestrator for the unified observability command center.
    Coordinates all AI-driven components for comprehensive security monitoring.
    """
    
    def __init__(self):
        self.anomaly_detector = AIAnomalyDetector()
        self.threat_intelligence = ThreatIntelligenceEngine()
        self.alerting_system = IntelligentAlertingSystem()
        self.visualization_engine = VisualizationEngine()
        
        # Redis connection for real-time data
        self.redis_client: Optional[aioredis.Redis] = None
        
        # WebSocket connections for real-time updates
        self.websocket_connections: List[WebSocket] = []
        
        # Metrics collectors
        self.metrics_registry = CollectorRegistry()
        self.metrics = {
            'alerts_generated': Counter('security_alerts_total', 'Total security alerts generated'),
            'threats_detected': Counter('threats_detected_total', 'Total threats detected'),
            'anomalies_found': Counter('anomalies_detected_total', 'Total anomalies detected'),
            'response_time': Histogram('command_center_response_seconds', 'Response time'),
            'active_threats': Gauge('active_threats_current', 'Current active threats')
        }
        
        # Background tasks
        self.monitoring_tasks: List[asyncio.Task] = []
        self.is_running = False
        
    async def initialize(self):
        """Initialize all components of the command center"""
        try:
            logger.info("Initializing Unified Observability Command Center...")
            
            # Initialize Redis connection
            self.redis_client = await aioredis.from_url(
                "redis://localhost:6379", 
                decode_responses=True,
                health_check_interval=30
            )
            
            # Initialize all AI components
            await self.anomaly_detector.initialize_models()
            await self.threat_intelligence.initialize_intelligence()
            await self.alerting_system.initialize_alerting()
            
            logger.info("All components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize command center: {e}")
            raise

    async def start_monitoring(self):
        """Start all monitoring and background tasks"""
        try:
            if self.is_running:
                logger.warning("Command center already running")
                return
                
            self.is_running = True
            logger.info("Starting monitoring tasks...")
            
            # Start background monitoring tasks
            self.monitoring_tasks = [
                asyncio.create_task(self._continuous_threat_monitoring()),
                asyncio.create_task(self._real_time_anomaly_detection()),
                asyncio.create_task(self._intelligent_alert_processing()),
                asyncio.create_task(self._metrics_collection_loop()),
                asyncio.create_task(self._dashboard_update_loop())
            ]
            
            logger.info("All monitoring tasks started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            raise

    async def stop_monitoring(self):
        """Gracefully stop all monitoring tasks"""
        try:
            logger.info("Stopping monitoring tasks...")
            self.is_running = False
            
            # Cancel all background tasks
            for task in self.monitoring_tasks:
                task.cancel()
                
            # Wait for tasks to complete
            await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
            
            # Close Redis connection
            if self.redis_client:
                await self.redis_client.close()
                
            logger.info("All monitoring tasks stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping monitoring: {e}")

    async def _continuous_threat_monitoring(self):
        """Continuously monitor for threat patterns"""
        try:
            while self.is_running:
                # Collect recent security events from Redis
                security_events = await self._collect_security_events()
                
                if security_events:
                    # Analyze for threat patterns
                    threats = await self.threat_intelligence.analyze_threat_patterns(security_events)
                    
                    # Store detected threats
                    for threat in threats:
                        await self._store_threat_intelligence(threat)
                        self.metrics['threats_detected'].inc()
                        
                    # Update active threats gauge
                    self.metrics['active_threats'].set(len(threats))
                    
                await asyncio.sleep(30)  # Check every 30 seconds
                
        except asyncio.CancelledError:
            logger.info("Threat monitoring task cancelled")
        except Exception as e:
            logger.error(f"Error in threat monitoring: {e}")

    async def _real_time_anomaly_detection(self):
        """Continuously detect anomalies in service metrics"""
        try:
            while self.is_running:
                # Collect current service metrics
                service_metrics = await self._collect_service_metrics()
                
                for service_name, metrics in service_metrics.items():
                    # Detect anomalies
                    is_anomaly, confidence = await self.anomaly_detector.detect_anomalies(
                        service_name, metrics
                    )
                    
                    if is_anomaly:
                        # Store anomaly information
                        await self._store_anomaly_detection(service_name, metrics, confidence)
                        self.metrics['anomalies_found'].inc()
                        
                        # Add anomaly confidence to metrics for alerting
                        metrics['anomaly_confidence'] = confidence
                        
                await asyncio.sleep(10)  # Check every 10 seconds
                
        except asyncio.CancelledError:
            logger.info("Anomaly detection task cancelled")
        except Exception as e:
            logger.error(f"Error in anomaly detection: {e}")

    async def _intelligent_alert_processing(self):
        """Process and generate intelligent alerts"""
        try:
            while self.is_running:
                # Collect current service metrics with anomaly information
                service_metrics = await self._collect_enriched_service_metrics()
                
                # Evaluate alert rules
                alerts = await self.alerting_system.evaluate_alerts(service_metrics)
                
                for alert in alerts:
                    # Store alert
                    await self._store_security_alert(alert)
                    self.metrics['alerts_generated'].inc()
                    
                    # Send real-time notifications
                    await self._send_real_time_alert(alert)
                    
                    # Add to alerting system history
                    self.alerting_system.alert_history.append(alert)
                    
                # Trim old alerts from history (keep last 1000)
                if len(self.alerting_system.alert_history) > 1000:
                    self.alerting_system.alert_history = self.alerting_system.alert_history[-1000:]
                    
                await asyncio.sleep(20)  # Check every 20 seconds
                
        except asyncio.CancelledError:
            logger.info("Alert processing task cancelled")
        except Exception as e:
            logger.error(f"Error in alert processing: {e}")

    async def _metrics_collection_loop(self):
        """Collect and aggregate metrics from all services"""
        try:
            while self.is_running:
                # This would integrate with your existing telemetry system
                # For now, simulate collecting metrics
                
                # In production, this would:
                # 1. Query Prometheus for metrics
                # 2. Collect OpenTelemetry traces and spans
                # 3. Aggregate logs for security events
                # 4. Update Redis with latest metrics
                
                await asyncio.sleep(5)  # Collect every 5 seconds
                
        except asyncio.CancelledError:
            logger.info("Metrics collection task cancelled")
        except Exception as e:
            logger.error(f"Error in metrics collection: {e}")

    async def _dashboard_update_loop(self):
        """Update dashboard visualizations in real-time"""
        try:
            while self.is_running:
                # Get latest threats and alerts
                threats = await self._get_active_threats()
                alerts = await self._get_recent_alerts()
                service_metrics = await self._collect_service_metrics()
                
                # Create updated dashboards
                threat_dashboard = await self.visualization_engine.create_threat_landscape_dashboard(
                    threats, alerts
                )
                metrics_dashboard = await self.visualization_engine.create_real_time_metrics_dashboard(
                    service_metrics
                )
                
                # Send updates to connected WebSocket clients
                dashboard_update = {
                    'type': 'dashboard_update',
                    'timestamp': datetime.now().isoformat(),
                    'threat_dashboard': threat_dashboard,
                    'metrics_dashboard': metrics_dashboard
                }
                
                await self._broadcast_to_websockets(dashboard_update)
                
                await asyncio.sleep(15)  # Update every 15 seconds
                
        except asyncio.CancelledError:
            logger.info("Dashboard update task cancelled")
        except Exception as e:
            logger.error(f"Error in dashboard updates: {e}")

    async def _collect_security_events(self) -> List[Dict]:
        """Collect recent security events from various sources"""
        try:
            events = []
            
            if self.redis_client:
                # Get recent security events from Redis
                event_keys = await self.redis_client.keys("security:event:*")
                
                for key in event_keys[-50:]:  # Get last 50 events
                    event_data = await self.redis_client.hgetall(key)
                    if event_data:
                        events.append(event_data)
                        
            return events
            
        except Exception as e:
            logger.error(f"Failed to collect security events: {e}")
            return []

    async def _collect_service_metrics(self) -> Dict[str, Dict[str, float]]:
        """Collect current metrics from all services"""
        try:
            # In production, this would query your metrics store (Prometheus, etc.)
            # For demonstration, return simulated metrics
            
            services = ['auth-service', 'biometric-service', 'tls-service', 
                       'temporal-service', 'messaging-service']
            
            metrics = {}
            for service in services:
                # Simulate realistic metrics with some randomness
                metrics[service] = {
                    'response_time_ms': np.random.normal(50, 15),
                    'error_rate': max(0, np.random.normal(0.02, 0.01)),
                    'cpu_usage': max(0, min(100, np.random.normal(30, 10))),
                    'memory_usage': max(0, min(100, np.random.normal(40, 15))),
                    'request_rate': max(0, np.random.normal(100, 25))
                }
                
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect service metrics: {e}")
            return {}

    async def _collect_enriched_service_metrics(self) -> Dict[str, Dict[str, float]]:
        """Collect service metrics enriched with anomaly detection results"""
        try:
            base_metrics = await self._collect_service_metrics()
            
            # Add anomaly detection results if available
            if self.redis_client:
                for service_name, metrics in base_metrics.items():
                    anomaly_key = f"anomaly:{service_name}"
                    anomaly_data = await self.redis_client.hgetall(anomaly_key)
                    
                    if anomaly_data:
                        metrics.update({
                            'anomaly_confidence': float(anomaly_data.get('confidence', 0)),
                            'anomaly_detected': anomaly_data.get('detected', 'false') == 'true'
                        })
                        
            return base_metrics
            
        except Exception as e:
            logger.error(f"Failed to collect enriched metrics: {e}")
            return await self._collect_service_metrics()

    async def _store_threat_intelligence(self, threat: ThreatIntelligence):
        """Store threat intelligence in Redis"""
        try:
            if self.redis_client:
                threat_data = {
                    'threat_id': threat.threat_id,
                    'attack_vector': threat.attack_vector,
                    'confidence_score': threat.confidence_score,
                    'predicted_targets': ','.join(threat.predicted_targets),
                    'timeline_prediction': threat.timeline_prediction,
                    'timestamp': datetime.now().isoformat()
                }
                
                await self.redis_client.hset(
                    f"threat:{threat.threat_id}", 
                    mapping=threat_data
                )
                
                # Set expiration (24 hours)
                await self.redis_client.expire(f"threat:{threat.threat_id}", 86400)
                
        except Exception as e:
            logger.error(f"Failed to store threat intelligence: {e}")

    async def _store_anomaly_detection(self, service_name: str, metrics: Dict[str, float], 
                                     confidence: float):
        """Store anomaly detection results"""
        try:
            if self.redis_client:
                anomaly_data = {
                    'service': service_name,
                    'confidence': confidence,
                    'detected': 'true',
                    'metrics': json.dumps(metrics),
                    'timestamp': datetime.now().isoformat()
                }
                
                await self.redis_client.hset(f"anomaly:{service_name}", mapping=anomaly_data)
                await self.redis_client.expire(f"anomaly:{service_name}", 3600)  # 1 hour
                
        except Exception as e:
            logger.error(f"Failed to store anomaly detection: {e}")

    async def _store_security_alert(self, alert: SecurityAlert):
        """Store security alert in Redis"""
        try:
            if self.redis_client:
                alert_data = {
                    'id': alert.id,
                    'alert_type': alert.alert_type.value,
                    'threat_level': alert.threat_level.value,
                    'title': alert.title,
                    'description': alert.description,
                    'source_service': alert.source_service,
                    'affected_services': ','.join(alert.affected_services),
                    'ai_confidence': alert.ai_confidence,
                    'predicted_impact': alert.predicted_impact,
                    'timestamp': alert.timestamp.isoformat()
                }
                
                await self.redis_client.hset(f"alert:{alert.id}", mapping=alert_data)
                await self.redis_client.expire(f"alert:{alert.id}", 604800)  # 7 days
                
        except Exception as e:
            logger.error(f"Failed to store security alert: {e}")

    async def _send_real_time_alert(self, alert: SecurityAlert):
        """Send real-time alert to connected clients"""
        try:
            alert_message = {
                'type': 'security_alert',
                'alert': {
                    'id': alert.id,
                    'title': alert.title,
                    'threat_level': alert.threat_level.value,
                    'description': alert.description,
                    'recommendations': alert.recommendations,
                    'timestamp': alert.timestamp.isoformat()
                }
            }
            
            await self._broadcast_to_websockets(alert_message)
            
        except Exception as e:
            logger.error(f"Failed to send real-time alert: {e}")

    async def _get_active_threats(self) -> List[ThreatIntelligence]:
        """Get currently active threats"""
        try:
            threats = []
            
            if self.redis_client:
                threat_keys = await self.redis_client.keys("threat:*")
                
                for key in threat_keys:
                    threat_data = await self.redis_client.hgetall(key)
                    if threat_data:
                        # Convert back to ThreatIntelligence object
                        threat = ThreatIntelligence(
                            threat_id=threat_data['threat_id'],
                            attack_vector=threat_data['attack_vector'],
                            confidence_score=float(threat_data['confidence_score']),
                            predicted_targets=threat_data['predicted_targets'].split(','),
                            timeline_prediction=threat_data['timeline_prediction'],
                            countermeasures=[],
                            related_incidents=[],
                            risk_assessment={}
                        )
                        threats.append(threat)
                        
            return threats
            
        except Exception as e:
            logger.error(f"Failed to get active threats: {e}")
            return []

    async def _get_recent_alerts(self) -> List[SecurityAlert]:
        """Get recent security alerts"""
        try:
            alerts = []
            
            if self.redis_client:
                alert_keys = await self.redis_client.keys("alert:*")
                
                for key in alert_keys[-20:]:  # Get last 20 alerts
                    alert_data = await self.redis_client.hgetall(key)
                    if alert_data:
                        # Convert back to SecurityAlert object
                        alert = SecurityAlert(
                            id=alert_data['id'],
                            alert_type=AlertType(alert_data['alert_type']),
                            threat_level=ThreatLevel(alert_data['threat_level']),
                            title=alert_data['title'],
                            description=alert_data['description'],
                            timestamp=datetime.fromisoformat(alert_data['timestamp']),
                            source_service=alert_data['source_service'],
                            affected_services=alert_data['affected_services'].split(','),
                            metrics={},
                            recommendations=[],
                            ai_confidence=float(alert_data['ai_confidence']),
                            predicted_impact=alert_data['predicted_impact']
                        )
                        alerts.append(alert)
                        
            return alerts
            
        except Exception as e:
            logger.error(f"Failed to get recent alerts: {e}")
            return []

    async def _broadcast_to_websockets(self, message: Dict):
        """Broadcast message to all connected WebSocket clients"""
        try:
            if not self.websocket_connections:
                return
                
            # Remove disconnected clients
            active_connections = []
            
            for websocket in self.websocket_connections:
                try:
                    await websocket.send_text(json.dumps(message))
                    active_connections.append(websocket)
                except:
                    # Connection closed, skip
                    pass
                    
            self.websocket_connections = active_connections
            
        except Exception as e:
            logger.error(f"Failed to broadcast to WebSockets: {e}")

    async def add_websocket_connection(self, websocket: WebSocket):
        """Add new WebSocket connection for real-time updates"""
        await websocket.accept()
        self.websocket_connections.append(websocket)
        logger.info(f"New WebSocket connection added. Total: {len(self.websocket_connections)}")

    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get current dashboard data for initial load"""
        try:
            threats = await self._get_active_threats()
            alerts = await self._get_recent_alerts()
            service_metrics = await self._collect_service_metrics()
            
            threat_dashboard = await self.visualization_engine.create_threat_landscape_dashboard(
                threats, alerts
            )
            metrics_dashboard = await self.visualization_engine.create_real_time_metrics_dashboard(
                service_metrics
            )
            
            return {
                'threat_dashboard': threat_dashboard,
                'metrics_dashboard': metrics_dashboard,
                'summary': {
                    'active_threats': len(threats),
                    'recent_alerts': len(alerts),
                    'monitored_services': len(service_metrics),
                    'system_health': 'healthy',  # Would be calculated based on metrics
                    'last_updated': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get dashboard data: {e}")
            return {'error': 'Failed to load dashboard data'}


# FastAPI application for the command center
app = FastAPI(
    title="Unified Observability Command Center",
    description="AI-Driven Security Monitoring and Threat Intelligence Platform",
    version="1.0.0"
)

# Global command center instance
command_center: Optional[UnifiedObservabilityCommandCenter] = None

@app.on_event("startup")
async def startup_event():
    """Initialize command center on startup"""
    global command_center
    try:
        command_center = UnifiedObservabilityCommandCenter()
        await command_center.initialize()
        await command_center.start_monitoring()
        logger.info("Command center started successfully")
    except Exception as e:
        logger.error(f"Failed to start command center: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown of command center"""
    global command_center
    if command_center:
        await command_center.stop_monitoring()
        logger.info("Command center stopped successfully")

@app.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates"""
    if command_center:
        try:
            await command_center.add_websocket_connection(websocket)
            
            # Keep connection alive
            while True:
                try:
                    await websocket.receive_text()
                except:
                    break
                    
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
    else:
        await websocket.close()

@app.get("/api/dashboard")
async def get_dashboard():
    """Get current dashboard data"""
    if command_center:
        return await command_center.get_dashboard_data()
    else:
        raise HTTPException(status_code=503, detail="Command center not available")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'command_center_running': command_center is not None and command_center.is_running
    }

@app.get("/")
async def dashboard_page():
    """Serve the main dashboard page"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Security Command Center</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #1a1a1a; color: white; }
            .container { max-width: 1400px; margin: 0 auto; }
            .header { text-align: center; margin-bottom: 30px; }
            .dashboard-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
            .dashboard-item { background: #2a2a2a; border-radius: 8px; padding: 20px; }
            .status { display: flex; justify-content: space-around; background: #2a2a2a; padding: 15px; border-radius: 8px; }
            .status-item { text-align: center; }
            .status-value { font-size: 24px; font-weight: bold; color: #4CAF50; }
            .alert { background: #d32f2f; padding: 10px; margin: 5px 0; border-radius: 4px; }
            .connected { color: #4CAF50; }
            .disconnected { color: #f44336; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🛡️ Unified Security Command Center</h1>
                <p>AI-Driven Threat Intelligence & Real-Time Monitoring</p>
                <div>Status: <span id="connection-status" class="disconnected">Connecting...</span></div>
            </div>
            
            <div class="status" id="summary-stats">
                <div class="status-item">
                    <div class="status-value" id="active-threats">-</div>
                    <div>Active Threats</div>
                </div>
                <div class="status-item">
                    <div class="status-value" id="recent-alerts">-</div>
                    <div>Recent Alerts</div>
                </div>
                <div class="status-item">
                    <div class="status-value" id="monitored-services">-</div>
                    <div>Services</div>
                </div>
                <div class="status-item">
                    <div class="status-value" id="system-health">-</div>
                    <div>System Health</div>
                </div>
            </div>
            
            <div class="dashboard-grid">
                <div class="dashboard-item">
                    <div id="threat-dashboard"></div>
                </div>
                <div class="dashboard-item">
                    <div id="metrics-dashboard"></div>
                </div>
            </div>
            
            <div class="dashboard-item">
                <h3>🚨 Real-Time Alerts</h3>
                <div id="alerts-feed"></div>
            </div>
        </div>

        <script>
            const ws = new WebSocket(`ws://${window.location.host}/ws/dashboard`);
            const connectionStatus = document.getElementById('connection-status');
            const alertsFeed = document.getElementById('alerts-feed');
            
            ws.onopen = function(event) {
                connectionStatus.textContent = 'Connected';
                connectionStatus.className = 'connected';
                loadInitialData();
            };
            
            ws.onclose = function(event) {
                connectionStatus.textContent = 'Disconnected';
                connectionStatus.className = 'disconnected';
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                
                if (data.type === 'dashboard_update') {
                    updateDashboards(data);
                } else if (data.type === 'security_alert') {
                    addAlert(data.alert);
                }
            };
            
            async function loadInitialData() {
                try {
                    const response = await fetch('/api/dashboard');
                    const data = await response.json();
                    updateDashboards(data);
                    updateSummary(data.summary);
                } catch (error) {
                    console.error('Failed to load initial data:', error);
                }
            }
            
            function updateDashboards(data) {
                if (data.threat_dashboard && data.threat_dashboard.dashboard) {
                    Plotly.newPlot('threat-dashboard', data.threat_dashboard.dashboard.data, 
                                  data.threat_dashboard.dashboard.layout);
                }
                
                if (data.metrics_dashboard && data.metrics_dashboard.dashboard) {
                    Plotly.newPlot('metrics-dashboard', data.metrics_dashboard.dashboard.data, 
                                  data.metrics_dashboard.dashboard.layout);
                }
            }
            
            function updateSummary(summary) {
                if (summary) {
                    document.getElementById('active-threats').textContent = summary.active_threats || '-';
                    document.getElementById('recent-alerts').textContent = summary.recent_alerts || '-';
                    document.getElementById('monitored-services').textContent = summary.monitored_services || '-';
                    document.getElementById('system-health').textContent = summary.system_health || '-';
                }
            }
            
            function addAlert(alert) {
                const alertDiv = document.createElement('div');
                alertDiv.className = 'alert';
                alertDiv.innerHTML = `
                    <strong>${alert.title}</strong> (${alert.threat_level})<br>
                    ${alert.description}<br>
                    <small>${new Date(alert.timestamp).toLocaleString()}</small>
                `;
                
                alertsFeed.insertBefore(alertDiv, alertsFeed.firstChild);
                
                // Keep only last 10 alerts
                while (alertsFeed.children.length > 10) {
                    alertsFeed.removeChild(alertsFeed.lastChild);
                }
            }
        </script>
    </body>
    </html>
    """)

if __name__ == "__main__":
    # Run the command center
    uvicorn.run(
        "unified_command_center:app",
        host="0.0.0.0",
        port=8080,
        log_level="info",
        access_log=True
    )