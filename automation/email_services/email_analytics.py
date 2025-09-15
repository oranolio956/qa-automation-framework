#!/usr/bin/env python3
"""
Email Analytics and Monitoring System
Comprehensive analytics, performance monitoring, and reporting for business email operations
"""

import os
import json
import logging
import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
from collections import defaultdict, deque
import statistics
from prometheus_client import Counter, Histogram, Gauge, Summary, generate_latest, CONTENT_TYPE_LATEST
from fastapi import FastAPI, Response
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EventType(Enum):
    EMAIL_SENT = "email_sent"
    EMAIL_RECEIVED = "email_received"
    EMAIL_OPENED = "email_opened"
    EMAIL_CLICKED = "email_clicked"
    EMAIL_BOUNCED = "email_bounced"
    EMAIL_COMPLAINED = "email_complained"
    VERIFICATION_CODE_EXTRACTED = "verification_code_extracted"
    TEMPLATE_RENDERED = "template_rendered"
    CREDENTIAL_ACCESSED = "credential_accessed"
    API_RATE_LIMITED = "api_rate_limited"
    PROVIDER_ERROR = "provider_error"

class DeliveryStatus(Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    BOUNCED = "bounced"
    COMPLAINED = "complained"
    OPENED = "opened"
    CLICKED = "clicked"

@dataclass
class EmailEvent:
    """Email event data structure for analytics"""
    id: str
    event_type: EventType
    timestamp: datetime
    email_address: str
    provider: str
    message_id: Optional[str] = None
    template_id: Optional[str] = None
    subject: Optional[str] = None
    recipient_count: int = 1
    processing_time: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'event_type': self.event_type.value,
            'timestamp': self.timestamp.isoformat(),
            'email_address': self.email_address,
            'provider': self.provider,
            'message_id': self.message_id,
            'template_id': self.template_id,
            'subject': self.subject,
            'recipient_count': self.recipient_count,
            'processing_time': self.processing_time,
            'error_message': self.error_message,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'EmailEvent':
        return cls(
            id=data['id'],
            event_type=EventType(data['event_type']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            email_address=data['email_address'],
            provider=data['provider'],
            message_id=data.get('message_id'),
            template_id=data.get('template_id'),
            subject=data.get('subject'),
            recipient_count=data.get('recipient_count', 1),
            processing_time=data.get('processing_time'),
            error_message=data.get('error_message'),
            metadata=data.get('metadata', {})
        )

@dataclass
class PerformanceMetrics:
    """Performance metrics summary"""
    period_start: datetime
    period_end: datetime
    total_emails_sent: int
    total_emails_received: int
    delivery_rate: float
    bounce_rate: float
    complaint_rate: float
    avg_processing_time: float
    provider_performance: Dict[str, Dict]
    template_performance: Dict[str, Dict]
    error_rate: float
    verification_codes_extracted: int
    api_calls_rate_limited: int

@dataclass
class AlertRule:
    """Email system alert rule"""
    id: str
    name: str
    metric: str
    operator: str  # '>', '<', '>=', '<=', '=='
    threshold: float
    period_minutes: int
    enabled: bool = True
    alert_channels: List[str] = None
    last_triggered: Optional[datetime] = None
    
    def __post_init__(self):
        if self.alert_channels is None:
            self.alert_channels = ['log']

class EmailAnalytics:
    """Comprehensive email analytics and monitoring system"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.db_path = self.config.get('db_path', 'email_analytics.db')
        
        # Initialize Prometheus metrics
        self.init_prometheus_metrics()
        
        # Initialize database
        self.init_database()
        
        # Real-time metrics tracking
        self.realtime_metrics = {
            'emails_sent_last_hour': deque(maxlen=3600),  # 1 hour sliding window
            'processing_times': deque(maxlen=1000),
            'error_counts': defaultdict(int),
            'provider_health': defaultdict(lambda: {'healthy': True, 'last_error': None})
        }
        
        # Alert rules
        self.alert_rules = {}
        self.load_alert_rules()
        
        logger.info("Email Analytics system initialized")
    
    def init_prometheus_metrics(self):
        """Initialize Prometheus metrics"""
        # Email metrics
        self.emails_sent_total = Counter('emails_sent_total', 'Total emails sent', ['provider', 'template'])
        self.emails_received_total = Counter('emails_received_total', 'Total emails received', ['provider'])
        self.email_processing_time = Histogram('email_processing_seconds', 'Email processing time', ['provider', 'operation'])
        self.email_errors_total = Counter('email_errors_total', 'Total email errors', ['provider', 'error_type'])
        
        # Delivery metrics
        self.email_delivery_status = Counter('email_delivery_status_total', 'Email delivery status', ['provider', 'status'])
        self.verification_codes_extracted = Counter('verification_codes_extracted_total', 'Verification codes extracted', ['provider'])
        
        # System metrics
        self.active_email_accounts = Gauge('active_email_accounts', 'Number of active email accounts', ['provider'])
        self.api_rate_limits_hit = Counter('api_rate_limits_total', 'API rate limits hit', ['provider', 'endpoint'])
        self.provider_health_score = Gauge('provider_health_score', 'Provider health score', ['provider'])
        
        # Performance metrics
        self.email_throughput = Gauge('email_throughput_per_minute', 'Email throughput per minute', ['provider'])
        self.template_usage = Counter('template_usage_total', 'Template usage count', ['template_id'])
        
    def init_database(self):
        """Initialize analytics database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create events table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS email_events (
                    id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    email_address TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    message_id TEXT,
                    template_id TEXT,
                    subject TEXT,
                    recipient_count INTEGER DEFAULT 1,
                    processing_time REAL,
                    error_message TEXT,
                    metadata TEXT
                )
            ''')
            
            # Create performance summaries table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    period_start TIMESTAMP NOT NULL,
                    period_end TIMESTAMP NOT NULL,
                    summary_type TEXT NOT NULL,
                    metrics TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create alert rules table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alert_rules (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    operator TEXT NOT NULL,
                    threshold REAL NOT NULL,
                    period_minutes INTEGER NOT NULL,
                    enabled BOOLEAN DEFAULT 1,
                    alert_channels TEXT,
                    last_triggered TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_event_timestamp ON email_events(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_event_type ON email_events(event_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_event_provider ON email_events(provider)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_event_email ON email_events(email_address)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_performance_period ON performance_summaries(period_start, period_end)')
            
            conn.commit()
            conn.close()
            
            logger.info("Analytics database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize analytics database: {e}")
            raise
    
    def track_event(self, event: EmailEvent):
        """Track email event for analytics"""
        try:
            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO email_events (
                    id, event_type, timestamp, email_address, provider,
                    message_id, template_id, subject, recipient_count,
                    processing_time, error_message, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.id,
                event.event_type.value,
                event.timestamp.isoformat(),
                event.email_address,
                event.provider,
                event.message_id,
                event.template_id,
                event.subject,
                event.recipient_count,
                event.processing_time,
                event.error_message,
                json.dumps(event.metadata)
            ))
            
            conn.commit()
            conn.close()
            
            # Update Prometheus metrics
            self._update_prometheus_metrics(event)
            
            # Update real-time metrics
            self._update_realtime_metrics(event)
            
            # Check alert rules
            asyncio.create_task(self._check_alert_rules(event))
            
            logger.debug(f"Tracked event: {event.event_type.value} for {event.email_address}")
            
        except Exception as e:
            logger.error(f"Failed to track event: {e}")
    
    def _update_prometheus_metrics(self, event: EmailEvent):
        """Update Prometheus metrics based on event"""
        try:
            if event.event_type == EventType.EMAIL_SENT:
                self.emails_sent_total.labels(
                    provider=event.provider,
                    template=event.template_id or 'none'
                ).inc(event.recipient_count)
                
                if event.processing_time:
                    self.email_processing_time.labels(
                        provider=event.provider,
                        operation='send'
                    ).observe(event.processing_time)
            
            elif event.event_type == EventType.EMAIL_RECEIVED:
                self.emails_received_total.labels(provider=event.provider).inc()
            
            elif event.event_type == EventType.VERIFICATION_CODE_EXTRACTED:
                self.verification_codes_extracted.labels(provider=event.provider).inc()
            
            elif event.event_type in [EventType.EMAIL_BOUNCED, EventType.EMAIL_COMPLAINED]:
                self.email_delivery_status.labels(
                    provider=event.provider,
                    status=event.event_type.value
                ).inc()
            
            elif event.event_type == EventType.PROVIDER_ERROR:
                self.email_errors_total.labels(
                    provider=event.provider,
                    error_type=event.metadata.get('error_type', 'unknown')
                ).inc()
            
            elif event.event_type == EventType.API_RATE_LIMITED:
                self.api_rate_limits_hit.labels(
                    provider=event.provider,
                    endpoint=event.metadata.get('endpoint', 'unknown')
                ).inc()
            
            elif event.event_type == EventType.TEMPLATE_RENDERED:
                if event.template_id:
                    self.template_usage.labels(template_id=event.template_id).inc()
                    
                    if event.processing_time:
                        self.email_processing_time.labels(
                            provider='template_engine',
                            operation='render'
                        ).observe(event.processing_time)
            
        except Exception as e:
            logger.warning(f"Failed to update Prometheus metrics: {e}")
    
    def _update_realtime_metrics(self, event: EmailEvent):
        """Update real-time metrics tracking"""
        try:
            current_time = time.time()
            
            if event.event_type == EventType.EMAIL_SENT:
                self.realtime_metrics['emails_sent_last_hour'].append(current_time)
            
            if event.processing_time:
                self.realtime_metrics['processing_times'].append(event.processing_time)
            
            if event.error_message:
                self.realtime_metrics['error_counts'][event.provider] += 1
                self.realtime_metrics['provider_health'][event.provider] = {
                    'healthy': False,
                    'last_error': event.timestamp,
                    'error_message': event.error_message
                }
            else:
                # Reset health status on successful operation
                if event.event_type in [EventType.EMAIL_SENT, EventType.EMAIL_RECEIVED]:
                    self.realtime_metrics['provider_health'][event.provider] = {
                        'healthy': True,
                        'last_error': None,
                        'error_message': None
                    }
            
        except Exception as e:
            logger.warning(f"Failed to update real-time metrics: {e}")
    
    async def _check_alert_rules(self, event: EmailEvent):
        """Check if event triggers any alert rules"""
        try:
            for rule_id, rule in self.alert_rules.items():
                if not rule.enabled:
                    continue
                
                # Check if rule applies to this event
                if await self._evaluate_alert_rule(rule, event):
                    await self._trigger_alert(rule, event)
                    
        except Exception as e:
            logger.warning(f"Failed to check alert rules: {e}")
    
    async def _evaluate_alert_rule(self, rule: AlertRule, event: EmailEvent) -> bool:
        """Evaluate if alert rule should be triggered"""
        try:
            # Get metric value for the specified period
            period_start = datetime.now() - timedelta(minutes=rule.period_minutes)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            metric_value = 0
            
            if rule.metric == 'error_rate':
                # Calculate error rate in the period
                cursor.execute('''
                    SELECT 
                        COUNT(CASE WHEN error_message IS NOT NULL THEN 1 END) as errors,
                        COUNT(*) as total
                    FROM email_events 
                    WHERE timestamp >= ?
                ''', (period_start.isoformat(),))
                
                result = cursor.fetchone()
                if result and result[1] > 0:
                    metric_value = result[0] / result[1]
            
            elif rule.metric == 'bounce_rate':
                cursor.execute('''
                    SELECT 
                        COUNT(CASE WHEN event_type = 'email_bounced' THEN 1 END) as bounces,
                        COUNT(CASE WHEN event_type = 'email_sent' THEN 1 END) as sent
                    FROM email_events 
                    WHERE timestamp >= ?
                ''', (period_start.isoformat(),))
                
                result = cursor.fetchone()
                if result and result[1] > 0:
                    metric_value = result[0] / result[1]
            
            elif rule.metric == 'processing_time_avg':
                cursor.execute('''
                    SELECT AVG(processing_time)
                    FROM email_events 
                    WHERE timestamp >= ? AND processing_time IS NOT NULL
                ''', (period_start.isoformat(),))
                
                result = cursor.fetchone()
                if result and result[0]:
                    metric_value = result[0]
            
            elif rule.metric == 'emails_per_minute':
                cursor.execute('''
                    SELECT COUNT(*) / ?
                    FROM email_events 
                    WHERE timestamp >= ? AND event_type = 'email_sent'
                ''', (rule.period_minutes, period_start.isoformat()))
                
                result = cursor.fetchone()
                if result:
                    metric_value = result[0] or 0
            
            conn.close()
            
            # Evaluate condition
            if rule.operator == '>':
                return metric_value > rule.threshold
            elif rule.operator == '<':
                return metric_value < rule.threshold
            elif rule.operator == '>=':
                return metric_value >= rule.threshold
            elif rule.operator == '<=':
                return metric_value <= rule.threshold
            elif rule.operator == '==':
                return abs(metric_value - rule.threshold) < 0.001
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to evaluate alert rule: {e}")
            return False
    
    async def _trigger_alert(self, rule: AlertRule, event: EmailEvent):
        """Trigger alert for rule"""
        try:
            # Check cooldown (don't trigger same alert too frequently)
            if rule.last_triggered:
                cooldown = timedelta(minutes=rule.period_minutes)
                if datetime.now() - rule.last_triggered < cooldown:
                    return
            
            alert_message = f"ALERT: {rule.name} triggered. Metric: {rule.metric}, Threshold: {rule.threshold}"
            
            # Send to configured channels
            for channel in rule.alert_channels:
                if channel == 'log':
                    logger.warning(alert_message)
                elif channel == 'email':
                    # Would send email alert (implement based on your needs)
                    logger.info(f"Would send email alert: {alert_message}")
                elif channel == 'webhook':
                    # Would send webhook alert (implement based on your needs)
                    logger.info(f"Would send webhook alert: {alert_message}")
            
            # Update last triggered time
            rule.last_triggered = datetime.now()
            self._save_alert_rule(rule)
            
        except Exception as e:
            logger.error(f"Failed to trigger alert: {e}")
    
    def get_performance_metrics(self, start_time: datetime, end_time: datetime) -> PerformanceMetrics:
        """Get comprehensive performance metrics for time period"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Basic email counts
            cursor.execute('''
                SELECT 
                    COUNT(CASE WHEN event_type = 'email_sent' THEN 1 END) as sent,
                    COUNT(CASE WHEN event_type = 'email_received' THEN 1 END) as received,
                    COUNT(CASE WHEN event_type = 'email_bounced' THEN 1 END) as bounced,
                    COUNT(CASE WHEN event_type = 'email_complained' THEN 1 END) as complained,
                    COUNT(CASE WHEN error_message IS NOT NULL THEN 1 END) as errors,
                    COUNT(*) as total_events,
                    AVG(processing_time) as avg_processing_time
                FROM email_events 
                WHERE timestamp BETWEEN ? AND ?
            ''', (start_time.isoformat(), end_time.isoformat()))
            
            basic_stats = cursor.fetchone()
            
            # Provider performance
            cursor.execute('''
                SELECT 
                    provider,
                    COUNT(CASE WHEN event_type = 'email_sent' THEN 1 END) as sent,
                    COUNT(CASE WHEN event_type = 'email_bounced' THEN 1 END) as bounced,
                    COUNT(CASE WHEN error_message IS NOT NULL THEN 1 END) as errors,
                    AVG(processing_time) as avg_processing_time
                FROM email_events 
                WHERE timestamp BETWEEN ? AND ?
                GROUP BY provider
            ''', (start_time.isoformat(), end_time.isoformat()))
            
            provider_stats = {}
            for row in cursor.fetchall():
                provider, sent, bounced, errors, avg_time = row
                provider_stats[provider] = {
                    'emails_sent': sent,
                    'bounce_rate': bounced / sent if sent > 0 else 0,
                    'error_rate': errors / (sent + errors) if (sent + errors) > 0 else 0,
                    'avg_processing_time': avg_time or 0
                }
            
            # Template performance
            cursor.execute('''
                SELECT 
                    template_id,
                    COUNT(*) as usage_count,
                    AVG(processing_time) as avg_render_time
                FROM email_events 
                WHERE timestamp BETWEEN ? AND ? 
                    AND template_id IS NOT NULL 
                    AND event_type = 'template_rendered'
                GROUP BY template_id
            ''', (start_time.isoformat(), end_time.isoformat()))
            
            template_stats = {}
            for row in cursor.fetchall():
                template_id, usage_count, avg_render_time = row
                template_stats[template_id] = {
                    'usage_count': usage_count,
                    'avg_render_time': avg_render_time or 0
                }
            
            # Verification codes extracted
            cursor.execute('''
                SELECT COUNT(*) 
                FROM email_events 
                WHERE timestamp BETWEEN ? AND ? 
                    AND event_type = 'verification_code_extracted'
            ''', (start_time.isoformat(), end_time.isoformat()))
            
            verification_codes = cursor.fetchone()[0] or 0
            
            # Rate limited API calls
            cursor.execute('''
                SELECT COUNT(*) 
                FROM email_events 
                WHERE timestamp BETWEEN ? AND ? 
                    AND event_type = 'api_rate_limited'
            ''', (start_time.isoformat(), end_time.isoformat()))
            
            rate_limited_calls = cursor.fetchone()[0] or 0
            
            conn.close()
            
            # Calculate rates
            sent, received, bounced, complained, errors, total_events, avg_processing_time = basic_stats
            
            delivery_rate = (sent - bounced) / sent if sent > 0 else 0
            bounce_rate = bounced / sent if sent > 0 else 0
            complaint_rate = complained / sent if sent > 0 else 0
            error_rate = errors / total_events if total_events > 0 else 0
            
            return PerformanceMetrics(
                period_start=start_time,
                period_end=end_time,
                total_emails_sent=sent or 0,
                total_emails_received=received or 0,
                delivery_rate=delivery_rate,
                bounce_rate=bounce_rate,
                complaint_rate=complaint_rate,
                avg_processing_time=avg_processing_time or 0,
                provider_performance=provider_stats,
                template_performance=template_stats,
                error_rate=error_rate,
                verification_codes_extracted=verification_codes,
                api_calls_rate_limited=rate_limited_calls
            )
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return PerformanceMetrics(
                period_start=start_time,
                period_end=end_time,
                total_emails_sent=0,
                total_emails_received=0,
                delivery_rate=0,
                bounce_rate=0,
                complaint_rate=0,
                avg_processing_time=0,
                provider_performance={},
                template_performance={},
                error_rate=0,
                verification_codes_extracted=0,
                api_calls_rate_limited=0
            )
    
    def get_realtime_metrics(self) -> Dict:
        """Get real-time performance metrics"""
        try:
            current_time = time.time()
            one_hour_ago = current_time - 3600
            
            # Clean old entries from sliding window
            while (self.realtime_metrics['emails_sent_last_hour'] and 
                   self.realtime_metrics['emails_sent_last_hour'][0] < one_hour_ago):
                self.realtime_metrics['emails_sent_last_hour'].popleft()
            
            # Calculate metrics
            emails_per_hour = len(self.realtime_metrics['emails_sent_last_hour'])
            emails_per_minute = emails_per_hour / 60
            
            processing_times = list(self.realtime_metrics['processing_times'])
            avg_processing_time = statistics.mean(processing_times) if processing_times else 0
            p95_processing_time = statistics.quantiles(processing_times, n=20)[18] if len(processing_times) > 20 else 0
            
            return {
                'emails_per_hour': emails_per_hour,
                'emails_per_minute': emails_per_minute,
                'avg_processing_time': avg_processing_time,
                'p95_processing_time': p95_processing_time,
                'error_counts': dict(self.realtime_metrics['error_counts']),
                'provider_health': dict(self.realtime_metrics['provider_health']),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get real-time metrics: {e}")
            return {}
    
    def create_alert_rule(self, rule: AlertRule) -> bool:
        """Create new alert rule"""
        try:
            self.alert_rules[rule.id] = rule
            self._save_alert_rule(rule)
            
            logger.info(f"Created alert rule: {rule.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create alert rule: {e}")
            return False
    
    def _save_alert_rule(self, rule: AlertRule):
        """Save alert rule to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO alert_rules (
                    id, name, metric, operator, threshold, period_minutes,
                    enabled, alert_channels, last_triggered
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                rule.id,
                rule.name,
                rule.metric,
                rule.operator,
                rule.threshold,
                rule.period_minutes,
                rule.enabled,
                json.dumps(rule.alert_channels),
                rule.last_triggered.isoformat() if rule.last_triggered else None
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save alert rule: {e}")
    
    def load_alert_rules(self):
        """Load alert rules from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM alert_rules WHERE enabled = 1')
            rows = cursor.fetchall()
            
            columns = [description[0] for description in cursor.description]
            
            for row in rows:
                data = dict(zip(columns, row))
                
                rule = AlertRule(
                    id=data['id'],
                    name=data['name'],
                    metric=data['metric'],
                    operator=data['operator'],
                    threshold=data['threshold'],
                    period_minutes=data['period_minutes'],
                    enabled=bool(data['enabled']),
                    alert_channels=json.loads(data['alert_channels']) if data['alert_channels'] else ['log']
                )
                
                if data['last_triggered']:
                    rule.last_triggered = datetime.fromisoformat(data['last_triggered'])
                
                self.alert_rules[rule.id] = rule
            
            conn.close()
            
            logger.info(f"Loaded {len(self.alert_rules)} alert rules")
            
        except Exception as e:
            logger.error(f"Failed to load alert rules: {e}")
    
    def generate_report(self, start_time: datetime, end_time: datetime, 
                       report_type: str = 'comprehensive') -> Dict:
        """Generate comprehensive analytics report"""
        try:
            metrics = self.get_performance_metrics(start_time, end_time)
            realtime_metrics = self.get_realtime_metrics()
            
            report = {
                'report_type': report_type,
                'period': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat(),
                    'duration_hours': (end_time - start_time).total_seconds() / 3600
                },
                'summary': {
                    'emails_sent': metrics.total_emails_sent,
                    'emails_received': metrics.total_emails_received,
                    'delivery_rate': f"{metrics.delivery_rate:.2%}",
                    'bounce_rate': f"{metrics.bounce_rate:.2%}",
                    'complaint_rate': f"{metrics.complaint_rate:.2%}",
                    'error_rate': f"{metrics.error_rate:.2%}",
                    'avg_processing_time': f"{metrics.avg_processing_time:.3f}s"
                },
                'provider_performance': metrics.provider_performance,
                'template_performance': metrics.template_performance,
                'verification_codes_extracted': metrics.verification_codes_extracted,
                'api_rate_limits_hit': metrics.api_calls_rate_limited,
                'realtime_metrics': realtime_metrics,
                'generated_at': datetime.now().isoformat()
            }
            
            # Add recommendations based on metrics
            report['recommendations'] = self._generate_recommendations(metrics)
            
            # Save report summary
            self._save_performance_summary(start_time, end_time, report_type, report)
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            return {}
    
    def _generate_recommendations(self, metrics: PerformanceMetrics) -> List[str]:
        """Generate recommendations based on performance metrics"""
        recommendations = []
        
        if metrics.bounce_rate > 0.05:  # 5% bounce rate
            recommendations.append(f"High bounce rate detected ({metrics.bounce_rate:.2%}). Review email list quality and sender reputation.")
        
        if metrics.complaint_rate > 0.001:  # 0.1% complaint rate
            recommendations.append(f"Complaint rate is elevated ({metrics.complaint_rate:.2%}). Review email content and frequency.")
        
        if metrics.error_rate > 0.02:  # 2% error rate
            recommendations.append(f"Error rate is high ({metrics.error_rate:.2%}). Check provider configurations and retry logic.")
        
        if metrics.avg_processing_time > 2.0:  # 2 seconds
            recommendations.append(f"Processing time is slow ({metrics.avg_processing_time:.3f}s). Consider optimizing email templates and provider connections.")
        
        # Provider-specific recommendations
        for provider, stats in metrics.provider_performance.items():
            if stats['error_rate'] > 0.05:
                recommendations.append(f"Provider {provider} has high error rate ({stats['error_rate']:.2%}). Consider switching or troubleshooting.")
        
        if not recommendations:
            recommendations.append("All metrics are within healthy ranges. Continue monitoring.")
        
        return recommendations
    
    def _save_performance_summary(self, start_time: datetime, end_time: datetime, 
                                summary_type: str, report: Dict):
        """Save performance summary to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO performance_summaries (
                    period_start, period_end, summary_type, metrics
                ) VALUES (?, ?, ?, ?)
            ''', (
                start_time.isoformat(),
                end_time.isoformat(),
                summary_type,
                json.dumps(report)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.warning(f"Failed to save performance summary: {e}")
    
    def export_metrics_for_grafana(self) -> str:
        """Export metrics in Prometheus format for Grafana"""
        try:
            return generate_latest()
        except Exception as e:
            logger.error(f"Failed to export metrics for Grafana: {e}")
            return ""
    
    def cleanup_old_data(self, days_to_keep: int = 90) -> int:
        """Clean up old analytics data"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Delete old events
            cursor.execute('DELETE FROM email_events WHERE timestamp < ?', (cutoff_date.isoformat(),))
            deleted_events = cursor.rowcount
            
            # Delete old performance summaries (keep longer for historical analysis)
            old_summary_cutoff = datetime.now() - timedelta(days=days_to_keep * 2)
            cursor.execute('DELETE FROM performance_summaries WHERE created_at < ?', (old_summary_cutoff.isoformat(),))
            deleted_summaries = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            total_deleted = deleted_events + deleted_summaries
            if total_deleted > 0:
                logger.info(f"Cleaned up {deleted_events} events and {deleted_summaries} summaries")
            
            return total_deleted
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return 0

# Global analytics instance
_email_analytics = None

def get_email_analytics(config: Dict = None) -> EmailAnalytics:
    """Get global email analytics instance"""
    global _email_analytics
    if _email_analytics is None:
        _email_analytics = EmailAnalytics(config)
    return _email_analytics

# FastAPI integration for metrics endpoint
def create_metrics_app() -> FastAPI:
    """Create FastAPI app for metrics endpoint"""
    app = FastAPI(title="Email Analytics API", version="1.0.0")
    
    @app.get("/metrics")
    async def get_metrics():
        """Prometheus metrics endpoint"""
        analytics = get_email_analytics()
        metrics_data = analytics.export_metrics_for_grafana()
        return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        analytics = get_email_analytics()
        realtime_metrics = analytics.get_realtime_metrics()
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "metrics": realtime_metrics
        }
    
    @app.get("/report/{hours}")
    async def get_report(hours: int = 24):
        """Get analytics report for last N hours"""
        analytics = get_email_analytics()
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        report = analytics.generate_report(start_time, end_time)
        return report
    
    return app

if __name__ == "__main__":
    def test_email_analytics():
        """Test email analytics functionality"""
        print("Testing Email Analytics System...")
        
        # Initialize analytics
        analytics = get_email_analytics({'db_path': 'test_analytics.db'})
        
        # Create test events
        import uuid
        
        # Email sent event
        sent_event = EmailEvent(
            id=str(uuid.uuid4()),
            event_type=EventType.EMAIL_SENT,
            timestamp=datetime.now(),
            email_address="test@example.com",
            provider="gmail",
            message_id="msg123",
            template_id="welcome",
            subject="Welcome!",
            recipient_count=1,
            processing_time=0.5
        )
        
        analytics.track_event(sent_event)
        
        # Verification code extracted event
        code_event = EmailEvent(
            id=str(uuid.uuid4()),
            event_type=EventType.VERIFICATION_CODE_EXTRACTED,
            timestamp=datetime.now(),
            email_address="verify@example.com",
            provider="outlook",
            processing_time=0.2,
            metadata={'code': '123456'}
        )
        
        analytics.track_event(code_event)
        
        # Get performance metrics
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)
        
        metrics = analytics.get_performance_metrics(start_time, end_time)
        print(f"Emails sent: {metrics.total_emails_sent}")
        print(f"Verification codes extracted: {metrics.verification_codes_extracted}")
        print(f"Average processing time: {metrics.avg_processing_time:.3f}s")
        
        # Get real-time metrics
        realtime = analytics.get_realtime_metrics()
        print(f"Emails per hour: {realtime.get('emails_per_hour', 0)}")
        
        # Generate report
        report = analytics.generate_report(start_time, end_time)
        print(f"Report generated with {len(report.get('recommendations', []))} recommendations")
        
        # Create alert rule
        alert_rule = AlertRule(
            id="high_error_rate",
            name="High Error Rate Alert",
            metric="error_rate",
            operator=">",
            threshold=0.05,
            period_minutes=15,
            alert_channels=["log", "email"]
        )
        
        analytics.create_alert_rule(alert_rule)
        print(f"Created alert rule: {alert_rule.name}")
        
        print("Email analytics test complete!")
    
    # Run test
    test_email_analytics()