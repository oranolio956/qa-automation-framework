#!/usr/bin/env python3
"""
System Monitoring and Alerting Test Coverage
Tests monitoring systems, alerting mechanisms, and observability
"""

import pytest
import asyncio
import time
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, call
import tempfile
import os
import threading
import queue

# Import monitoring components
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../automation'))


@dataclass
class MonitoringEvent:
    """Monitoring event data structure"""
    timestamp: datetime
    severity: str  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    source: str
    event_type: str
    message: str
    metadata: Dict[str, Any]
    metrics: Optional[Dict[str, float]] = None


@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    condition: str
    threshold: float
    duration: int  # seconds
    severity: str
    actions: List[str]
    enabled: bool = True


class MockPrometheusClient:
    """Mock Prometheus client for testing"""
    
    def __init__(self):
        self.metrics = {}
        self.counters = {}
        self.histograms = {}
        self.gauges = {}
        
    def counter(self, name: str, description: str = "", labelnames: List[str] = None):
        """Create mock counter"""
        counter = MagicMock()
        counter.inc = MagicMock()
        counter.labels = MagicMock(return_value=counter)
        self.counters[name] = counter
        return counter
    
    def histogram(self, name: str, description: str = "", labelnames: List[str] = None):
        """Create mock histogram"""
        histogram = MagicMock()
        histogram.observe = MagicMock()
        histogram.labels = MagicMock(return_value=histogram)
        histogram.time = MagicMock()
        self.histograms[name] = histogram
        return histogram
    
    def gauge(self, name: str, description: str = "", labelnames: List[str] = None):
        """Create mock gauge"""
        gauge = MagicMock()
        gauge.set = MagicMock()
        gauge.inc = MagicMock()
        gauge.dec = MagicMock()
        gauge.labels = MagicMock(return_value=gauge)
        self.gauges[name] = gauge
        return gauge


class MockStructuredLogger:
    """Mock structured logger for testing"""
    
    def __init__(self):
        self.events = []
        self.log_levels = {
            'debug': [],
            'info': [],
            'warning': [],
            'error': [],
            'critical': []
        }
    
    def log_event(self, level: str, message: str, **kwargs):
        """Log structured event"""
        event = MonitoringEvent(
            timestamp=datetime.now(),
            severity=level.upper(),
            source=kwargs.get('source', 'test'),
            event_type=kwargs.get('event_type', 'general'),
            message=message,
            metadata=kwargs,
            metrics=kwargs.get('metrics')
        )
        
        self.events.append(event)
        self.log_levels[level].append(event)
    
    def debug(self, message: str, **kwargs):
        self.log_event('debug', message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self.log_event('info', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self.log_event('warning', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self.log_event('error', message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self.log_event('critical', message, **kwargs)


class TestSystemMetricsCollection:
    """Test system metrics collection and reporting"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.prometheus_client = MockPrometheusClient()
        self.logger = MockStructuredLogger()
    
    @pytest.mark.monitoring
    def test_account_creation_metrics_collection(self):
        """Test collection of account creation metrics"""
        
        # Create metrics collectors
        account_creation_counter = self.prometheus_client.counter(
            'account_creation_attempts_total',
            'Total number of account creation attempts',
            ['status', 'platform']
        )
        
        account_creation_duration = self.prometheus_client.histogram(
            'account_creation_duration_seconds',
            'Time taken for account creation',
            ['platform', 'status']
        )
        
        concurrent_accounts = self.prometheus_client.gauge(
            'concurrent_account_creations',
            'Number of concurrent account creation operations'
        )
        
        # Simulate account creation operations
        test_scenarios = [
            {'platform': 'tinder', 'status': 'success', 'duration': 45.2},
            {'platform': 'tinder', 'status': 'success', 'duration': 52.1},
            {'platform': 'tinder', 'status': 'failed', 'duration': 30.5},
            {'platform': 'snapchat', 'status': 'success', 'duration': 38.7},
        ]
        
        for scenario in test_scenarios:
            # Increment counter
            account_creation_counter.labels(
                status=scenario['status'], 
                platform=scenario['platform']
            ).inc()
            
            # Record duration
            account_creation_duration.labels(
                platform=scenario['platform'],
                status=scenario['status']
            ).observe(scenario['duration'])
            
            # Update concurrent operations gauge
            concurrent_accounts.inc()
            
            # Log structured event
            self.logger.info(
                "Account creation completed",
                source="account_creator",
                event_type="account_creation",
                platform=scenario['platform'],
                status=scenario['status'],
                duration=scenario['duration'],
                metrics={
                    'creation_duration': scenario['duration'],
                    'success': scenario['status'] == 'success'
                }
            )
        
        # Verify metrics were collected
        assert len(self.prometheus_client.counters) == 1
        assert len(self.prometheus_client.histograms) == 1
        assert len(self.prometheus_client.gauges) == 1
        
        # Verify counter calls
        account_creation_counter.labels.assert_called()
        account_creation_counter.labels.return_value.inc.assert_called()
        
        # Verify histogram calls
        account_creation_duration.labels.assert_called()
        account_creation_duration.labels.return_value.observe.assert_called()
        
        # Verify structured logging
        assert len(self.logger.events) == 4
        assert all(event.event_type == 'account_creation' for event in self.logger.events)
        
        # Check log levels distribution
        assert len(self.logger.log_levels['info']) == 4
        assert len(self.logger.log_levels['error']) == 0
    
    @pytest.mark.monitoring
    def test_error_metrics_collection(self):
        """Test collection of error metrics and events"""
        
        # Create error metrics
        error_counter = self.prometheus_client.counter(
            'automation_errors_total',
            'Total number of automation errors',
            ['error_type', 'component', 'severity']
        )
        
        error_scenarios = [
            {
                'error_type': 'sms_verification_failed',
                'component': 'sms_service',
                'severity': 'high',
                'message': 'SMS verification timeout after 5 minutes'
            },
            {
                'error_type': 'captcha_solve_failed',
                'component': 'captcha_solver',
                'severity': 'medium',
                'message': '2Captcha service unavailable'
            },
            {
                'error_type': 'emulator_crash',
                'component': 'emulator_manager',
                'severity': 'critical',
                'message': 'Android emulator crashed during account creation'
            },
            {
                'error_type': 'proxy_connection_failed',
                'component': 'proxy_service',
                'severity': 'high',
                'message': 'BrightData proxy connection timeout'
            }
        ]
        
        for scenario in error_scenarios:
            # Increment error counter
            error_counter.labels(
                error_type=scenario['error_type'],
                component=scenario['component'],
                severity=scenario['severity']
            ).inc()
            
            # Log error event
            log_level = 'critical' if scenario['severity'] == 'critical' else 'error'
            
            self.logger.log_event(
                log_level,
                scenario['message'],
                source=scenario['component'],
                event_type='error',
                error_type=scenario['error_type'],
                severity=scenario['severity'],
                component=scenario['component']
            )
        
        # Verify error tracking
        assert len(self.logger.log_levels['error']) == 3
        assert len(self.logger.log_levels['critical']) == 1
        
        # Verify error counter usage
        error_counter.labels.assert_called()
        assert error_counter.labels.call_count == 4
        
        # Check critical error logging
        critical_events = [e for e in self.logger.events if e.severity == 'CRITICAL']
        assert len(critical_events) == 1
        assert critical_events[0].metadata['error_type'] == 'emulator_crash'
    
    @pytest.mark.monitoring
    def test_performance_metrics_collection(self):
        """Test collection of performance metrics"""
        
        # Create performance metrics
        response_time_histogram = self.prometheus_client.histogram(
            'operation_response_time_seconds',
            'Response time for various operations',
            ['operation', 'status']
        )
        
        memory_usage_gauge = self.prometheus_client.gauge(
            'memory_usage_bytes',
            'Memory usage by component',
            ['component']
        )
        
        cpu_usage_gauge = self.prometheus_client.gauge(
            'cpu_usage_percent',
            'CPU usage by component',
            ['component']
        )
        
        # Simulate performance monitoring
        performance_data = [
            {
                'operation': 'profile_generation',
                'response_time': 0.145,
                'status': 'success',
                'memory_mb': 245.7,
                'cpu_percent': 15.3
            },
            {
                'operation': 'device_fingerprint_creation',
                'response_time': 0.423,
                'status': 'success',
                'memory_mb': 289.1,
                'cpu_percent': 22.8
            },
            {
                'operation': 'email_account_creation',
                'response_time': 12.567,
                'status': 'success',
                'memory_mb': 156.4,
                'cpu_percent': 8.2
            }
        ]
        
        for data in performance_data:
            # Record response time
            response_time_histogram.labels(
                operation=data['operation'],
                status=data['status']
            ).observe(data['response_time'])
            
            # Update resource usage
            memory_usage_gauge.labels(
                component=data['operation']
            ).set(data['memory_mb'] * 1024 * 1024)  # Convert to bytes
            
            cpu_usage_gauge.labels(
                component=data['operation']
            ).set(data['cpu_percent'])
            
            # Log performance event
            self.logger.info(
                f"Operation {data['operation']} completed",
                source="performance_monitor",
                event_type="performance",
                operation=data['operation'],
                metrics={
                    'response_time': data['response_time'],
                    'memory_mb': data['memory_mb'],
                    'cpu_percent': data['cpu_percent']
                }
            )
        
        # Verify performance metrics collection
        assert response_time_histogram.labels.call_count == 3
        assert memory_usage_gauge.labels.call_count == 3
        assert cpu_usage_gauge.labels.call_count == 3
        
        # Verify performance logging
        performance_events = [e for e in self.logger.events if e.event_type == 'performance']
        assert len(performance_events) == 3
        
        # Check metrics data
        for event in performance_events:
            assert 'response_time' in event.metrics
            assert 'memory_mb' in event.metrics
            assert 'cpu_percent' in event.metrics


class TestAlertingSystem:
    """Test alerting system functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.alert_rules = []
        self.triggered_alerts = []
        self.notification_queue = queue.Queue()
    
    @pytest.mark.monitoring
    def test_alert_rule_evaluation(self):
        """Test alert rule evaluation logic"""
        
        # Define alert rules
        alert_rules = [
            AlertRule(
                name="high_error_rate",
                condition="error_rate > 0.05",
                threshold=0.05,
                duration=60,
                severity="warning",
                actions=["email", "slack"]
            ),
            AlertRule(
                name="critical_error_rate",
                condition="error_rate > 0.20",
                threshold=0.20,
                duration=30,
                severity="critical",
                actions=["email", "slack", "pagerduty"]
            ),
            AlertRule(
                name="high_response_time",
                condition="avg_response_time > 120",
                threshold=120.0,
                duration=300,
                severity="warning",
                actions=["slack"]
            ),
            AlertRule(
                name="service_unavailable",
                condition="success_rate < 0.50",
                threshold=0.50,
                duration=60,
                severity="critical",
                actions=["email", "pagerduty"]
            )
        ]
        
        # Test scenarios with different metric values
        test_scenarios = [
            {
                'name': 'normal_operation',
                'metrics': {
                    'error_rate': 0.02,
                    'avg_response_time': 45.0,
                    'success_rate': 0.98
                },
                'expected_alerts': []
            },
            {
                'name': 'high_error_rate',
                'metrics': {
                    'error_rate': 0.08,
                    'avg_response_time': 50.0,
                    'success_rate': 0.92
                },
                'expected_alerts': ['high_error_rate']
            },
            {
                'name': 'critical_errors',
                'metrics': {
                    'error_rate': 0.25,
                    'avg_response_time': 80.0,
                    'success_rate': 0.75
                },
                'expected_alerts': ['high_error_rate', 'critical_error_rate']
            },
            {
                'name': 'service_degradation',
                'metrics': {
                    'error_rate': 0.15,
                    'avg_response_time': 150.0,
                    'success_rate': 0.40
                },
                'expected_alerts': ['high_error_rate', 'high_response_time', 'service_unavailable']
            }
        ]
        
        for scenario in test_scenarios:
            triggered_alerts = []
            
            for rule in alert_rules:
                if self._evaluate_alert_rule(rule, scenario['metrics']):
                    triggered_alerts.append(rule.name)
            
            # Verify expected alerts
            for expected_alert in scenario['expected_alerts']:
                assert expected_alert in triggered_alerts, \
                    f"Expected alert '{expected_alert}' not triggered for scenario '{scenario['name']}'"
            
            # Verify no unexpected alerts
            for triggered_alert in triggered_alerts:
                assert triggered_alert in scenario['expected_alerts'], \
                    f"Unexpected alert '{triggered_alert}' triggered for scenario '{scenario['name']}'"
    
    def _evaluate_alert_rule(self, rule: AlertRule, metrics: Dict[str, float]) -> bool:
        """Evaluate alert rule against metrics"""
        
        if not rule.enabled:
            return False
        
        # Simple rule evaluation logic
        if rule.name == 'high_error_rate':
            return metrics.get('error_rate', 0) > rule.threshold
        elif rule.name == 'critical_error_rate':
            return metrics.get('error_rate', 0) > rule.threshold
        elif rule.name == 'high_response_time':
            return metrics.get('avg_response_time', 0) > rule.threshold
        elif rule.name == 'service_unavailable':
            return metrics.get('success_rate', 1.0) < rule.threshold
        
        return False
    
    @pytest.mark.monitoring
    async def test_alert_notification_system(self):
        """Test alert notification delivery"""
        
        # Mock notification services
        mock_email_service = MagicMock()
        mock_slack_service = MagicMock()
        mock_pagerduty_service = MagicMock()
        
        notification_services = {
            'email': mock_email_service,
            'slack': mock_slack_service,
            'pagerduty': mock_pagerduty_service
        }
        
        # Test alert scenarios
        test_alerts = [
            {
                'name': 'test_warning_alert',
                'severity': 'warning',
                'message': 'Error rate above threshold',
                'actions': ['email', 'slack'],
                'metadata': {'error_rate': 0.08, 'threshold': 0.05}
            },
            {
                'name': 'test_critical_alert',
                'severity': 'critical',
                'message': 'Service unavailable',
                'actions': ['email', 'slack', 'pagerduty'],
                'metadata': {'success_rate': 0.30, 'threshold': 0.50}
            }
        ]
        
        for alert in test_alerts:
            # Send notifications
            for action in alert['actions']:
                service = notification_services.get(action)
                if service:
                    await self._send_notification(service, alert)
        
        # Verify notification calls
        mock_email_service.send_alert.assert_called()
        mock_slack_service.send_alert.assert_called()
        
        # Critical alert should trigger PagerDuty
        mock_pagerduty_service.send_alert.assert_called_once()
        
        # Verify alert content
        email_calls = mock_email_service.send_alert.call_args_list
        assert len(email_calls) == 2  # Both alerts sent via email
        
        # Check critical alert reached PagerDuty
        pagerduty_call = mock_pagerduty_service.send_alert.call_args
        assert 'critical' in str(pagerduty_call)
    
    async def _send_notification(self, service: MagicMock, alert: Dict):
        """Send notification via service"""
        service.send_alert = MagicMock()
        await asyncio.sleep(0.01)  # Simulate async operation
        service.send_alert(alert)
    
    @pytest.mark.monitoring
    def test_alert_deduplication(self):
        """Test alert deduplication to prevent spam"""
        
        alert_manager = AlertManager()
        
        # Same alert triggered multiple times
        alert_data = {
            'name': 'high_error_rate',
            'severity': 'warning',
            'message': 'Error rate above 5%',
            'fingerprint': 'high_error_rate_tinder_service'
        }
        
        # First alert should be sent
        should_send_1 = alert_manager.should_send_alert(alert_data)
        assert should_send_1 == True
        
        # Immediate duplicate should be suppressed
        should_send_2 = alert_manager.should_send_alert(alert_data)
        assert should_send_2 == False
        
        # Alert after cooldown period should be sent
        alert_manager.last_alert_times[alert_data['fingerprint']] = time.time() - 3600  # 1 hour ago
        should_send_3 = alert_manager.should_send_alert(alert_data)
        assert should_send_3 == True
    
    @pytest.mark.monitoring
    def test_alert_escalation(self):
        """Test alert escalation based on duration and severity"""
        
        escalation_manager = AlertEscalationManager()
        
        # Warning alert that persists
        warning_alert = {
            'name': 'high_response_time',
            'severity': 'warning',
            'first_triggered': time.time() - 1800,  # 30 minutes ago
            'still_active': True
        }
        
        # Should escalate after 30 minutes
        should_escalate = escalation_manager.should_escalate(warning_alert)
        assert should_escalate == True
        
        escalated_alert = escalation_manager.escalate_alert(warning_alert)
        assert escalated_alert['severity'] == 'critical'
        assert 'pagerduty' in escalated_alert['actions']
        
        # Critical alert should not escalate further
        critical_alert = {
            'name': 'service_down',
            'severity': 'critical',
            'first_triggered': time.time() - 3600,
            'still_active': True
        }
        
        should_escalate_critical = escalation_manager.should_escalate(critical_alert)
        assert should_escalate_critical == False


class TestObservabilityIntegration:
    """Test observability integration and dashboards"""
    
    @pytest.mark.monitoring
    def test_metrics_export_format(self):
        """Test metrics export in Prometheus format"""
        
        # Mock metrics data
        metrics_data = {
            'account_creation_attempts_total{status="success",platform="tinder"}': 150,
            'account_creation_attempts_total{status="failed",platform="tinder"}': 12,
            'account_creation_duration_seconds_bucket{platform="tinder",le="30"}': 45,
            'account_creation_duration_seconds_bucket{platform="tinder",le="60"}': 89,
            'account_creation_duration_seconds_bucket{platform="tinder",le="120"}': 135,
            'account_creation_duration_seconds_bucket{platform="tinder",le="+Inf"}': 150,
            'concurrent_account_creations': 5,
            'automation_errors_total{error_type="sms_timeout",component="sms_service"}': 3
        }
        
        # Format for Prometheus export
        prometheus_output = self._format_prometheus_metrics(metrics_data)
        
        # Verify Prometheus format
        lines = prometheus_output.strip().split('\n')
        assert len(lines) > 0
        
        # Check counter format
        counter_lines = [line for line in lines if 'account_creation_attempts_total' in line]
        assert len(counter_lines) >= 2
        
        # Check histogram format  
        histogram_lines = [line for line in lines if 'account_creation_duration_seconds_bucket' in line]
        assert len(histogram_lines) >= 4
        
        # Check gauge format
        gauge_lines = [line for line in lines if 'concurrent_account_creations' in line]
        assert len(gauge_lines) == 1
    
    def _format_prometheus_metrics(self, metrics_data: Dict[str, float]) -> str:
        """Format metrics in Prometheus export format"""
        lines = []
        for metric_name, value in metrics_data.items():
            lines.append(f"{metric_name} {value}")
        return '\n'.join(lines)
    
    @pytest.mark.monitoring
    def test_structured_logging_integration(self):
        """Test structured logging integration with log aggregation"""
        
        logger = MockStructuredLogger()
        
        # Simulate various system events
        events = [
            {
                'level': 'info',
                'message': 'Account creation started',
                'user_id': 'user_123',
                'platform': 'tinder',
                'trace_id': 'trace_abc123'
            },
            {
                'level': 'error',
                'message': 'SMS verification failed',
                'user_id': 'user_123',
                'error_code': 'SMS_TIMEOUT',
                'trace_id': 'trace_abc123'
            },
            {
                'level': 'info',
                'message': 'Account creation completed',
                'user_id': 'user_123',
                'platform': 'tinder',
                'duration': 67.5,
                'trace_id': 'trace_abc123'
            }
        ]
        
        for event in events:
            logger.log_event(event['level'], event['message'], **event)
        
        # Verify structured logging
        assert len(logger.events) == 3
        
        # Check trace correlation
        trace_events = [e for e in logger.events if e.metadata.get('trace_id') == 'trace_abc123']
        assert len(trace_events) == 3
        
        # Check error tracking
        error_events = [e for e in logger.events if e.severity == 'ERROR']
        assert len(error_events) == 1
        assert error_events[0].metadata['error_code'] == 'SMS_TIMEOUT'
    
    @pytest.mark.monitoring
    def test_dashboard_data_queries(self):
        """Test data queries for monitoring dashboards"""
        
        # Mock time series data
        time_series_data = self._generate_mock_time_series()
        
        # Test dashboard queries
        dashboard_queries = {
            'success_rate_1h': self._query_success_rate(time_series_data, '1h'),
            'error_rate_24h': self._query_error_rate(time_series_data, '24h'),
            'avg_response_time_1h': self._query_avg_response_time(time_series_data, '1h'),
            'concurrent_operations': self._query_current_operations(time_series_data)
        }
        
        # Verify query results
        assert 0 <= dashboard_queries['success_rate_1h'] <= 1.0
        assert 0 <= dashboard_queries['error_rate_24h'] <= 1.0
        assert dashboard_queries['avg_response_time_1h'] > 0
        assert dashboard_queries['concurrent_operations'] >= 0
        
        # Success rate + error rate should be reasonable
        assert dashboard_queries['success_rate_1h'] + dashboard_queries['error_rate_24h'] <= 1.1  # Allow small variance
    
    def _generate_mock_time_series(self) -> Dict:
        """Generate mock time series data for testing"""
        now = time.time()
        
        return {
            'account_creation_success': [
                {'timestamp': now - 3600, 'value': 145},
                {'timestamp': now - 1800, 'value': 167},
                {'timestamp': now - 900, 'value': 123},
                {'timestamp': now, 'value': 156}
            ],
            'account_creation_failed': [
                {'timestamp': now - 3600, 'value': 8},
                {'timestamp': now - 1800, 'value': 12},
                {'timestamp': now - 900, 'value': 6},
                {'timestamp': now, 'value': 9}
            ],
            'response_times': [
                {'timestamp': now - 3600, 'value': 45.2},
                {'timestamp': now - 1800, 'value': 52.1},
                {'timestamp': now - 900, 'value': 38.7},
                {'timestamp': now, 'value': 41.3}
            ]
        }
    
    def _query_success_rate(self, data: Dict, timerange: str) -> float:
        """Calculate success rate for timerange"""
        success_data = data.get('account_creation_success', [])
        failed_data = data.get('account_creation_failed', [])
        
        if not success_data or not failed_data:
            return 0.0
        
        total_success = sum(point['value'] for point in success_data)
        total_failed = sum(point['value'] for point in failed_data)
        total_attempts = total_success + total_failed
        
        return total_success / total_attempts if total_attempts > 0 else 0.0
    
    def _query_error_rate(self, data: Dict, timerange: str) -> float:
        """Calculate error rate for timerange"""
        return 1.0 - self._query_success_rate(data, timerange)
    
    def _query_avg_response_time(self, data: Dict, timerange: str) -> float:
        """Calculate average response time for timerange"""
        response_data = data.get('response_times', [])
        
        if not response_data:
            return 0.0
        
        total_time = sum(point['value'] for point in response_data)
        return total_time / len(response_data)
    
    def _query_current_operations(self, data: Dict) -> int:
        """Get current concurrent operations"""
        # Mock current operations
        return 7


class AlertManager:
    """Mock alert manager for testing"""
    
    def __init__(self):
        self.last_alert_times = {}
        self.cooldown_period = 300  # 5 minutes
    
    def should_send_alert(self, alert: Dict) -> bool:
        """Determine if alert should be sent (deduplication)"""
        fingerprint = alert.get('fingerprint', alert['name'])
        last_sent = self.last_alert_times.get(fingerprint, 0)
        
        if time.time() - last_sent > self.cooldown_period:
            self.last_alert_times[fingerprint] = time.time()
            return True
        
        return False


class AlertEscalationManager:
    """Mock alert escalation manager"""
    
    def __init__(self):
        self.escalation_timeout = 1800  # 30 minutes
    
    def should_escalate(self, alert: Dict) -> bool:
        """Determine if alert should be escalated"""
        if alert['severity'] == 'critical':
            return False  # Already at highest level
        
        time_active = time.time() - alert['first_triggered']
        return time_active > self.escalation_timeout and alert['still_active']
    
    def escalate_alert(self, alert: Dict) -> Dict:
        """Escalate alert to higher severity"""
        escalated = alert.copy()
        escalated['severity'] = 'critical'
        escalated['actions'] = alert.get('actions', []) + ['pagerduty']
        escalated['escalated_at'] = time.time()
        return escalated


# Test configuration
pytestmark = [
    pytest.mark.monitoring,
    pytest.mark.timeout(120),  # 2 minute timeout for monitoring tests
]


if __name__ == "__main__":
    # Run monitoring tests
    pytest.main([
        __file__,
        "-v",
        "-m", "monitoring",
        "--tb=short"
    ])