"""
Telemetry Integration for Anti-Bot Security Framework
Integration layer for OpenTelemetry with existing services and Temporal workflows
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import json
import traceback

# OpenTelemetry imports
from opentelemetry import trace, metrics
from opentelemetry.trace import Status, StatusCode
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.semconv.resource import ResourceAttributes

# Import existing components
from .opentelemetry_config import (
    get_tracer, get_meter, get_security_metrics,
    trace_security_operation, SecurityMetricsCollector
)

# Temporal integration
from temporalio import workflow, activity
from temporalio.common import RetryPolicy

# FastAPI integration
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


logger = logging.getLogger(__name__)


class SecurityTelemetryMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for comprehensive security telemetry
    """
    
    def __init__(self, app, service_name: str = "antibot-security"):
        super().__init__(app)
        self.service_name = service_name
        self.tracer = get_tracer("antibot.middleware")
        self.metrics_collector = get_security_metrics()
        
        # Initialize middleware-specific metrics
        self.meter = get_meter("antibot.middleware")
        self.request_duration = self.meter.create_histogram(
            name="http_request_duration",
            description="HTTP request duration",
            unit="ms"
        )
        self.request_counter = self.meter.create_counter(
            name="http_requests_total",
            description="Total HTTP requests",
            unit="1"
        )
        self.active_requests = self.meter.create_up_down_counter(
            name="http_requests_active",
            description="Active HTTP requests",
            unit="1"
        )
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process HTTP request with telemetry"""
        start_time = time.time()
        
        # Extract request attributes
        attributes = {
            "http.method": request.method,
            "http.url": str(request.url),
            "http.scheme": request.url.scheme,
            "http.host": request.url.hostname or "unknown",
            "http.target": request.url.path,
            "http.user_agent": request.headers.get("user-agent", "unknown"),
            "http.remote_addr": getattr(request.client, "host", "unknown"),
            "security.endpoint": self._classify_endpoint(request.url.path)
        }
        
        # Start tracing span
        with self.tracer.start_as_current_span(
            f"{request.method} {request.url.path}",
            attributes=attributes
        ) as span:
            
            # Increment active requests
            self.active_requests.add(1, {"method": request.method, "endpoint": attributes["security.endpoint"]})
            
            try:
                # Add security context
                await self._add_security_context(request, span)
                
                # Process request
                response = await call_next(request)
                
                # Record successful request
                processing_time = (time.time() - start_time) * 1000
                
                # Update span with response info
                span.set_attribute("http.status_code", response.status_code)
                span.set_attribute("http.response_size", len(response.body) if hasattr(response, 'body') else 0)
                
                # Record metrics
                self._record_request_metrics(request, response, processing_time, attributes)
                
                # Set span status
                if response.status_code >= 400:
                    span.set_status(Status(StatusCode.ERROR, f"HTTP {response.status_code}"))
                else:
                    span.set_status(Status(StatusCode.OK))
                
                return response
                
            except Exception as e:
                # Record error
                processing_time = (time.time() - start_time) * 1000
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                
                # Record error metrics
                self.request_counter.add(1, {
                    **attributes,
                    "status_code": "500",
                    "error": type(e).__name__
                })
                
                logger.error(f"Request processing failed: {e}", extra={"span_context": span.get_span_context()})
                raise
                
            finally:
                # Decrement active requests
                self.active_requests.add(-1, {"method": request.method, "endpoint": attributes["security.endpoint"]})
    
    async def _add_security_context(self, request: Request, span: trace.Span):
        """Add security-specific context to span"""
        # Extract security headers
        security_headers = {}
        for header_name, header_value in request.headers.items():
            if any(security_term in header_name.lower() for security_term in ['auth', 'token', 'key', 'session']):
                # Hash sensitive values for security
                security_headers[header_name] = f"hash:{hash(header_value) % 10000}"
        
        if security_headers:
            span.set_attribute("security.headers_present", json.dumps(security_headers))
        
        # Check for security-relevant query parameters
        if request.query_params:
            security_params = []
            for param in request.query_params.keys():
                if any(security_term in param.lower() for security_term in ['session', 'token', 'key', 'auth']):
                    security_params.append(param)
            
            if security_params:
                span.set_attribute("security.query_params", ",".join(security_params))
        
        # Add request fingerprint
        request_fingerprint = self._generate_request_fingerprint(request)
        span.set_attribute("security.request_fingerprint", request_fingerprint)
    
    def _classify_endpoint(self, path: str) -> str:
        """Classify endpoint for security categorization"""
        if "/api/v1/behavioral-data" in path:
            return "risk_assessment"
        elif "/health" in path:
            return "health_check"
        elif "/metrics" in path:
            return "metrics"
        elif "/api/v1/sms" in path:
            return "sms_verification"
        elif "/api/v1/train-model" in path:
            return "model_training"
        elif "/api/v1/model-versions" in path:
            return "model_management"
        else:
            return "unknown"
    
    def _record_request_metrics(self, request: Request, response: Response, 
                              processing_time: float, attributes: Dict[str, str]):
        """Record HTTP request metrics"""
        metric_attributes = {
            "method": request.method,
            "endpoint": attributes["security.endpoint"],
            "status_code": str(response.status_code),
            "status_class": f"{response.status_code // 100}xx"
        }
        
        # Record duration and count
        self.request_duration.record(processing_time, metric_attributes)
        self.request_counter.add(1, metric_attributes)
        
        # Record security-specific metrics for risk assessment endpoints
        if attributes["security.endpoint"] == "risk_assessment":
            # This would be enhanced with actual response parsing
            self.metrics_collector.record_risk_assessment(
                risk_score=0.5,  # Would extract from response
                confidence=0.8,  # Would extract from response
                processing_time_ms=processing_time,
                model_version="2.0.0",  # Would extract from response
                session_attributes={
                    "user_agent": request.headers.get("user-agent", "unknown"),
                    "remote_addr": getattr(request.client, "host", "unknown")
                }
            )
    
    def _generate_request_fingerprint(self, request: Request) -> str:
        """Generate a fingerprint for the request"""
        fingerprint_data = {
            "method": request.method,
            "path": request.url.path,
            "user_agent": request.headers.get("user-agent", ""),
            "accept": request.headers.get("accept", ""),
            "accept_language": request.headers.get("accept-language", ""),
            "accept_encoding": request.headers.get("accept-encoding", "")
        }
        
        # Create a hash of the fingerprint data
        fingerprint_str = json.dumps(fingerprint_data, sort_keys=True)
        return str(hash(fingerprint_str) % 100000)


class TemporalTelemetryIntegration:
    """
    Integration for Temporal workflows with OpenTelemetry
    """
    
    def __init__(self):
        self.tracer = get_tracer("antibot.temporal")
        self.metrics_collector = get_security_metrics()
        self.meter = get_meter("antibot.temporal")
        
        # Temporal-specific metrics
        self.workflow_duration = self.meter.create_histogram(
            name="temporal_workflow_duration",
            description="Temporal workflow duration",
            unit="ms"
        )
        
        self.activity_duration = self.meter.create_histogram(
            name="temporal_activity_duration",
            description="Temporal activity duration",
            unit="ms"
        )
        
        self.workflow_failures = self.meter.create_counter(
            name="temporal_workflow_failures",
            description="Temporal workflow failures",
            unit="1"
        )
        
        self.activity_retries = self.meter.create_counter(
            name="temporal_activity_retries",
            description="Temporal activity retries",
            unit="1"
        )
    
    @asynccontextmanager
    async def trace_workflow(self, workflow_type: str, workflow_id: str, 
                           input_data: Dict[str, Any] = None):
        """Trace Temporal workflow execution"""
        attributes = {
            "temporal.workflow.type": workflow_type,
            "temporal.workflow.id": workflow_id,
            "temporal.workflow.input_size": len(str(input_data)) if input_data else 0
        }
        
        with self.tracer.start_as_current_span(
            f"workflow/{workflow_type}",
            attributes=attributes
        ) as span:
            start_time = time.time()
            
            try:
                yield span
                
                # Record successful workflow
                duration_ms = (time.time() - start_time) * 1000
                self.workflow_duration.record(duration_ms, {
                    "workflow_type": workflow_type,
                    "status": "completed"
                })
                
                span.set_status(Status(StatusCode.OK))
                
            except Exception as e:
                # Record failed workflow
                duration_ms = (time.time() - start_time) * 1000
                
                self.workflow_duration.record(duration_ms, {
                    "workflow_type": workflow_type,
                    "status": "failed"
                })
                
                self.workflow_failures.add(1, {
                    "workflow_type": workflow_type,
                    "error_type": type(e).__name__
                })
                
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
    
    @asynccontextmanager
    async def trace_activity(self, activity_name: str, input_data: Dict[str, Any] = None,
                           retry_attempt: int = 0):
        """Trace Temporal activity execution"""
        attributes = {
            "temporal.activity.name": activity_name,
            "temporal.activity.retry_attempt": retry_attempt,
            "temporal.activity.input_size": len(str(input_data)) if input_data else 0
        }
        
        with self.tracer.start_as_current_span(
            f"activity/{activity_name}",
            attributes=attributes
        ) as span:
            start_time = time.time()
            
            try:
                yield span
                
                # Record successful activity
                duration_ms = (time.time() - start_time) * 1000
                self.activity_duration.record(duration_ms, {
                    "activity_name": activity_name,
                    "status": "completed",
                    "retry_attempt": str(retry_attempt)
                })
                
                # Record retry if this wasn't the first attempt
                if retry_attempt > 0:
                    self.activity_retries.add(retry_attempt, {
                        "activity_name": activity_name,
                        "final_status": "success"
                    })
                
                span.set_status(Status(StatusCode.OK))
                
            except Exception as e:
                # Record failed activity
                duration_ms = (time.time() - start_time) * 1000
                
                self.activity_duration.record(duration_ms, {
                    "activity_name": activity_name,
                    "status": "failed",
                    "retry_attempt": str(retry_attempt)
                })
                
                if retry_attempt > 0:
                    self.activity_retries.add(retry_attempt, {
                        "activity_name": activity_name,
                        "final_status": "failed"
                    })
                
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise


class DatabaseTelemetryIntegration:
    """
    Enhanced database telemetry for security operations
    """
    
    def __init__(self):
        self.tracer = get_tracer("antibot.database")
        self.meter = get_meter("antibot.database")
        
        # Database-specific metrics
        self.query_duration = self.meter.create_histogram(
            name="database_query_duration",
            description="Database query duration",
            unit="ms"
        )
        
        self.connection_pool_usage = self.meter.create_histogram(
            name="database_connection_pool_usage",
            description="Database connection pool usage",
            unit="percentage"
        )
        
        self.security_data_operations = self.meter.create_counter(
            name="security_data_operations",
            description="Security-related database operations",
            unit="1"
        )
    
    @asynccontextmanager
    async def trace_security_query(self, operation_type: str, table_name: str,
                                 query_type: str = "select"):
        """Trace security-related database operations"""
        attributes = {
            "db.operation": operation_type,
            "db.table": table_name,
            "db.query_type": query_type,
            "security.data_type": self._classify_security_data(table_name)
        }
        
        with self.tracer.start_as_current_span(
            f"db/{operation_type}",
            attributes=attributes
        ) as span:
            start_time = time.time()
            
            try:
                yield span
                
                # Record successful query
                duration_ms = (time.time() - start_time) * 1000
                self.query_duration.record(duration_ms, attributes)
                
                # Count security data operations
                self.security_data_operations.add(1, {
                    "operation": operation_type,
                    "security_data_type": attributes["security.data_type"],
                    "status": "success"
                })
                
                span.set_status(Status(StatusCode.OK))
                
            except Exception as e:
                # Record failed query
                duration_ms = (time.time() - start_time) * 1000
                self.query_duration.record(duration_ms, {
                    **attributes,
                    "status": "error"
                })
                
                self.security_data_operations.add(1, {
                    "operation": operation_type,
                    "security_data_type": attributes["security.data_type"],
                    "status": "error",
                    "error_type": type(e).__name__
                })
                
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
    
    def _classify_security_data(self, table_name: str) -> str:
        """Classify the type of security data being accessed"""
        if "behavioral_data" in table_name.lower():
            return "behavioral"
        elif "risk_assessment" in table_name.lower():
            return "risk_assessment"
        elif "user" in table_name.lower() or "session" in table_name.lower():
            return "user_session"
        elif "model" in table_name.lower():
            return "model_data"
        elif "threat" in table_name.lower() or "security" in table_name.lower():
            return "threat_intelligence"
        else:
            return "general"


class ExternalServiceTelemetry:
    """
    Telemetry for external service integrations
    """
    
    def __init__(self):
        self.tracer = get_tracer("antibot.external")
        self.meter = get_meter("antibot.external")
        self.metrics_collector = get_security_metrics()
        
        # External service metrics
        self.external_request_duration = self.meter.create_histogram(
            name="external_service_request_duration",
            description="External service request duration",
            unit="ms"
        )
        
        self.external_service_availability = self.meter.create_histogram(
            name="external_service_availability",
            description="External service availability",
            unit="percentage"
        )
        
        self.fraud_intelligence_calls = self.meter.create_counter(
            name="fraud_intelligence_api_calls",
            description="Fraud intelligence API calls",
            unit="1"
        )
    
    @asynccontextmanager
    async def trace_fraud_intelligence_call(self, provider: str, query_type: str,
                                          indicators: Dict[str, Any] = None):
        """Trace fraud intelligence API calls"""
        attributes = {
            "external.service": "fraud_intelligence",
            "external.provider": provider,
            "fraud.query_type": query_type,
            "fraud.indicators_count": len(indicators) if indicators else 0
        }
        
        with self.tracer.start_as_current_span(
            f"fraud_intelligence/{provider}",
            attributes=attributes
        ) as span:
            start_time = time.time()
            
            try:
                yield span
                
                # Record successful call
                duration_ms = (time.time() - start_time) * 1000
                
                self.external_request_duration.record(duration_ms, attributes)
                self.fraud_intelligence_calls.add(1, {
                    "provider": provider,
                    "query_type": query_type,
                    "status": "success"
                })
                
                # Record fraud intelligence metrics
                self.metrics_collector.record_fraud_intelligence_query(
                    latency_ms=duration_ms,
                    provider=provider,
                    success=True,
                    threat_indicators=attributes["fraud.indicators_count"]
                )
                
                span.set_status(Status(StatusCode.OK))
                
            except Exception as e:
                # Record failed call
                duration_ms = (time.time() - start_time) * 1000
                
                self.external_request_duration.record(duration_ms, {
                    **attributes,
                    "status": "error"
                })
                
                self.fraud_intelligence_calls.add(1, {
                    "provider": provider,
                    "query_type": query_type,
                    "status": "error",
                    "error_type": type(e).__name__
                })
                
                # Record failed fraud intelligence metrics
                self.metrics_collector.record_fraud_intelligence_query(
                    latency_ms=duration_ms,
                    provider=provider,
                    success=False,
                    threat_indicators=0
                )
                
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise


# Global instances
temporal_telemetry = TemporalTelemetryIntegration()
database_telemetry = DatabaseTelemetryIntegration()
external_service_telemetry = ExternalServiceTelemetry()


# Convenience decorators
def trace_workflow_execution(workflow_type: str):
    """Decorator for tracing workflow execution"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            workflow_id = kwargs.get('workflow_id', f"{workflow_type}-{int(time.time())}")
            input_data = kwargs if kwargs else {}
            
            async with temporal_telemetry.trace_workflow(workflow_type, workflow_id, input_data):
                return await func(*args, **kwargs)
        return wrapper
    return decorator


def trace_activity_execution(activity_name: str):
    """Decorator for tracing activity execution"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            input_data = kwargs if kwargs else {}
            retry_attempt = kwargs.get('retry_attempt', 0)
            
            async with temporal_telemetry.trace_activity(activity_name, input_data, retry_attempt):
                return await func(*args, **kwargs)
        return wrapper
    return decorator


def trace_database_operation(operation_type: str, table_name: str):
    """Decorator for tracing database operations"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            async with database_telemetry.trace_security_query(operation_type, table_name):
                return await func(*args, **kwargs)
        return wrapper
    return decorator


def trace_fraud_intelligence_request(provider: str, query_type: str):
    """Decorator for tracing fraud intelligence requests"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            indicators = kwargs.get('indicators', {})
            async with external_service_telemetry.trace_fraud_intelligence_call(provider, query_type, indicators):
                return await func(*args, **kwargs)
        return wrapper
    return decorator