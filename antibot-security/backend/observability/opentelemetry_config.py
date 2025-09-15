"""
OpenTelemetry Configuration for Anti-Bot Security Framework
Production-ready observability with distributed tracing, metrics, and logging
"""

import os
import logging
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
import asyncio

# OpenTelemetry imports
from opentelemetry import trace, metrics, _logs
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.pymongo import PymongoInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.kafka import KafkaInstrumentor
from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentor
from opentelemetry.instrumentation.runtime_metrics import RuntimeMetricsInstrumentor

from opentelemetry.propagator.b3 import B3Format, B3MultiFormat
from opentelemetry.propagator.jaeger import JaegerPropagator
from opentelemetry.propagators import set_global_textmap

from opentelemetry.resource import SERVICE_NAME, SERVICE_VERSION, DEPLOYMENT_ENVIRONMENT, Resource
from opentelemetry.sdk.trace import TracerProvider, BatchSpanProcessor, SpanProcessor
from opentelemetry.sdk.trace.export import SpanExporter, ConsoleSpanExporter, BatchSpanProcessor as BatchProcessor
from opentelemetry.sdk.metrics import MeterProvider, PeriodicExportingMetricReader
from opentelemetry.sdk._logs import LoggerProvider, BatchLogRecordProcessor
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor as LogBatchProcessor

from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.semconv.resource import ResourceAttributes

# Custom processors and exporters
from opentelemetry.sdk.trace.export import SpanExportResult
from opentelemetry.trace import Status, StatusCode
import json
import time
from datetime import datetime


class SecurityMetricsCollector:
    """
    Custom metrics collector for security-specific metrics
    """
    
    def __init__(self, meter):
        self.meter = meter
        
        # Security-specific metrics
        self.risk_score_histogram = self.meter.create_histogram(
            name="antibot_risk_score",
            description="Risk score distribution",
            unit="score"
        )
        
        self.threat_detection_counter = self.meter.create_counter(
            name="antibot_threats_detected",
            description="Number of threats detected",
            unit="1"
        )
        
        self.challenge_success_rate = self.meter.create_histogram(
            name="antibot_challenge_success_rate",
            description="Challenge success rate",
            unit="percentage"
        )
        
        self.model_inference_duration = self.meter.create_histogram(
            name="antibot_model_inference_duration",
            description="ML model inference duration",
            unit="ms"
        )
        
        self.behavioral_anomaly_score = self.meter.create_histogram(
            name="antibot_behavioral_anomaly_score",
            description="Behavioral anomaly score",
            unit="score"
        )
        
        self.session_duration = self.meter.create_histogram(
            name="antibot_session_duration",
            description="User session duration",
            unit="s"
        )
        
        self.fraud_intelligence_latency = self.meter.create_histogram(
            name="antibot_fraud_intelligence_latency",
            description="Fraud intelligence API latency",
            unit="ms"
        )
        
        # System performance metrics
        self.workflow_execution_duration = self.meter.create_histogram(
            name="temporal_workflow_execution_duration",
            description="Temporal workflow execution duration",
            unit="ms"
        )
        
        self.activity_failure_rate = self.meter.create_counter(
            name="temporal_activity_failures",
            description="Temporal activity failures",
            unit="1"
        )
    
    def record_risk_assessment(self, risk_score: float, confidence: float, 
                             processing_time_ms: float, model_version: str,
                             session_attributes: Dict[str, Any] = None):
        """Record risk assessment metrics"""
        attributes = {
            "model_version": model_version,
            "confidence_bucket": self._get_confidence_bucket(confidence)
        }
        
        if session_attributes:
            attributes.update({
                "device_type": session_attributes.get("device_type", "unknown"),
                "user_agent_family": session_attributes.get("user_agent_family", "unknown"),
                "geo_country": session_attributes.get("geo_country", "unknown")
            })
        
        self.risk_score_histogram.record(risk_score, attributes)
        self.model_inference_duration.record(processing_time_ms, attributes)
        
        # Record threat detection
        if risk_score > 0.8:
            self.threat_detection_counter.add(1, {
                **attributes,
                "threat_level": "high",
                "risk_bucket": self._get_risk_bucket(risk_score)
            })
        elif risk_score > 0.6:
            self.threat_detection_counter.add(1, {
                **attributes,
                "threat_level": "medium",
                "risk_bucket": self._get_risk_bucket(risk_score)
            })
    
    def record_challenge_result(self, challenge_type: str, success: bool, 
                              duration_ms: float, session_id: str):
        """Record challenge completion metrics"""
        attributes = {
            "challenge_type": challenge_type,
            "success": str(success).lower(),
            "session_id_hash": hash(session_id) % 1000  # Anonymized session tracking
        }
        
        success_rate = 100.0 if success else 0.0
        self.challenge_success_rate.record(success_rate, attributes)
    
    def record_behavioral_analysis(self, anomaly_score: float, session_duration_s: float,
                                 event_count: int, patterns_detected: List[str]):
        """Record behavioral analysis metrics"""
        attributes = {
            "event_count_bucket": self._get_event_count_bucket(event_count),
            "pattern_types": ",".join(sorted(patterns_detected)[:3])  # Top 3 patterns
        }
        
        self.behavioral_anomaly_score.record(anomaly_score, attributes)
        self.session_duration.record(session_duration_s, attributes)
    
    def record_fraud_intelligence_query(self, latency_ms: float, provider: str, 
                                      success: bool, threat_indicators: int):
        """Record fraud intelligence query metrics"""
        attributes = {
            "provider": provider,
            "success": str(success).lower(),
            "threat_indicators_bucket": self._get_threat_indicators_bucket(threat_indicators)
        }
        
        self.fraud_intelligence_latency.record(latency_ms, attributes)
    
    def record_temporal_workflow(self, workflow_type: str, duration_ms: float, 
                               status: str, activities_count: int):
        """Record Temporal workflow metrics"""
        attributes = {
            "workflow_type": workflow_type,
            "status": status,
            "activities_count": str(activities_count)
        }
        
        self.workflow_execution_duration.record(duration_ms, attributes)
        
        if status == "failed":
            self.activity_failure_rate.add(1, attributes)
    
    @staticmethod
    def _get_confidence_bucket(confidence: float) -> str:
        """Get confidence bucket for grouping"""
        if confidence >= 0.9:
            return "very_high"
        elif confidence >= 0.8:
            return "high"
        elif confidence >= 0.7:
            return "medium"
        elif confidence >= 0.5:
            return "low"
        else:
            return "very_low"
    
    @staticmethod
    def _get_risk_bucket(risk_score: float) -> str:
        """Get risk score bucket for grouping"""
        if risk_score >= 0.9:
            return "critical"
        elif risk_score >= 0.8:
            return "high"
        elif risk_score >= 0.6:
            return "medium"
        elif risk_score >= 0.4:
            return "low"
        else:
            return "minimal"
    
    @staticmethod
    def _get_event_count_bucket(event_count: int) -> str:
        """Get event count bucket for grouping"""
        if event_count >= 1000:
            return "very_high"
        elif event_count >= 500:
            return "high"
        elif event_count >= 100:
            return "medium"
        elif event_count >= 20:
            return "low"
        else:
            return "very_low"
    
    @staticmethod
    def _get_threat_indicators_bucket(indicators: int) -> str:
        """Get threat indicators bucket for grouping"""
        if indicators >= 10:
            return "many"
        elif indicators >= 5:
            return "several"
        elif indicators >= 1:
            return "few"
        else:
            return "none"


class SecuritySpanProcessor(SpanProcessor):
    """
    Custom span processor for security-specific enrichment
    """
    
    def on_start(self, span: trace.Span, parent_context) -> None:
        """Enrich span on start"""
        # Add security-specific attributes
        span.set_attribute("security.framework", "antibot-v2")
        span.set_attribute("security.timestamp", int(time.time()))
        
        # Add deployment environment
        span.set_attribute("deployment.environment", os.getenv("DEPLOYMENT_ENV", "development"))
        span.set_attribute("deployment.version", os.getenv("APP_VERSION", "unknown"))
    
    def on_end(self, span: trace.ReadableSpan) -> None:
        """Process span on end"""
        # Log security-relevant spans
        if span.name.startswith("security/") or "risk" in span.name.lower():
            self._log_security_span(span)
    
    def shutdown(self) -> None:
        """Shutdown processor"""
        pass
    
    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush processor"""
        return True
    
    def _log_security_span(self, span: trace.ReadableSpan):
        """Log security-relevant span data"""
        span_data = {
            "trace_id": format(span.get_span_context().trace_id, "032x"),
            "span_id": format(span.get_span_context().span_id, "016x"),
            "name": span.name,
            "duration_ms": (span.end_time - span.start_time) / 1_000_000,
            "status": span.status.status_code.name if span.status else "OK",
            "attributes": dict(span.attributes) if span.attributes else {}
        }
        
        # Use structured logging for security events
        security_logger = logging.getLogger("antibot.security.tracing")
        security_logger.info("Security span completed", extra={"span_data": span_data})


class OpenTelemetryConfigurator:
    """
    Comprehensive OpenTelemetry configuration for Anti-Bot Security Framework
    """
    
    def __init__(self, service_name: str, service_version: str = "2.0.0", 
                 environment: str = None):
        self.service_name = service_name
        self.service_version = service_version
        self.environment = environment or os.getenv("DEPLOYMENT_ENV", "development")
        
        # Configuration from environment
        self.otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        self.jaeger_endpoint = os.getenv("JAEGER_ENDPOINT", "http://localhost:14268/api/traces")
        self.prometheus_port = int(os.getenv("PROMETHEUS_METRICS_PORT", "8000"))
        
        # Component references
        self.tracer_provider = None
        self.meter_provider = None
        self.logger_provider = None
        self.metrics_collector = None
        
        # Instrumentation flags
        self.instrumentations_enabled = {
            "fastapi": True,
            "requests": True,
            "redis": True,
            "postgresql": True,
            "mongodb": True,
            "celery": True,
            "kafka": True,
            "system_metrics": True,
            "runtime_metrics": True
        }
    
    def initialize_tracing(self) -> trace.Tracer:
        """Initialize distributed tracing"""
        # Create resource
        resource = Resource.create({
            SERVICE_NAME: self.service_name,
            SERVICE_VERSION: self.service_version,
            DEPLOYMENT_ENVIRONMENT: self.environment,
            ResourceAttributes.SERVICE_INSTANCE_ID: os.getenv("HOSTNAME", "unknown"),
            ResourceAttributes.SERVICE_NAMESPACE: "antibot-security",
            "security.framework.version": "2.0.0",
            "security.deployment.tier": os.getenv("DEPLOYMENT_TIER", "production")
        })
        
        # Create tracer provider
        self.tracer_provider = TracerProvider(resource=resource)
        
        # Add span processors
        # OTLP exporter (primary)
        otlp_exporter = OTLPSpanExporter(endpoint=self.otlp_endpoint, insecure=True)
        self.tracer_provider.add_span_processor(BatchProcessor(otlp_exporter))
        
        # Jaeger exporter (backup/additional)
        jaeger_exporter = JaegerExporter(
            agent_host_name=os.getenv("JAEGER_AGENT_HOST", "localhost"),
            agent_port=int(os.getenv("JAEGER_AGENT_PORT", "6831")),
            collector_endpoint=self.jaeger_endpoint,
        )
        self.tracer_provider.add_span_processor(BatchProcessor(jaeger_exporter))
        
        # Custom security span processor
        security_processor = SecuritySpanProcessor()
        self.tracer_provider.add_span_processor(security_processor)
        
        # Console exporter for development
        if self.environment == "development":
            console_exporter = ConsoleSpanExporter()
            self.tracer_provider.add_span_processor(BatchProcessor(console_exporter))
        
        # Set global tracer provider
        trace.set_tracer_provider(self.tracer_provider)
        
        # Configure propagators
        set_global_textmap([B3MultiFormat(), B3Format(), JaegerPropagator()])
        
        return trace.get_tracer(__name__)
    
    def initialize_metrics(self) -> metrics.Meter:
        """Initialize metrics collection"""
        # Create resource (same as tracing)
        resource = Resource.create({
            SERVICE_NAME: self.service_name,
            SERVICE_VERSION: self.service_version,
            DEPLOYMENT_ENVIRONMENT: self.environment,
            ResourceAttributes.SERVICE_INSTANCE_ID: os.getenv("HOSTNAME", "unknown"),
            ResourceAttributes.SERVICE_NAMESPACE: "antibot-security"
        })
        
        # Create metric readers
        readers = []
        
        # Prometheus reader (for scraping)
        prometheus_reader = PrometheusMetricReader(port=self.prometheus_port)
        readers.append(prometheus_reader)
        
        # OTLP metrics exporter (for push)
        otlp_metric_exporter = OTLPMetricExporter(endpoint=self.otlp_endpoint, insecure=True)
        otlp_reader = PeriodicExportingMetricReader(
            exporter=otlp_metric_exporter,
            export_interval_millis=30000,  # Export every 30 seconds
            export_timeout_millis=10000
        )
        readers.append(otlp_reader)
        
        # Create meter provider
        self.meter_provider = MeterProvider(resource=resource, metric_readers=readers)
        metrics.set_meter_provider(self.meter_provider)
        
        # Create meter
        meter = metrics.get_meter(__name__)
        
        # Initialize security metrics collector
        self.metrics_collector = SecurityMetricsCollector(meter)
        
        return meter
    
    def initialize_logging(self):
        """Initialize structured logging with OpenTelemetry"""
        # Create resource (same as tracing)
        resource = Resource.create({
            SERVICE_NAME: self.service_name,
            SERVICE_VERSION: self.service_version,
            DEPLOYMENT_ENVIRONMENT: self.environment
        })
        
        # Create logger provider
        self.logger_provider = LoggerProvider(resource=resource)
        
        # Add log processors
        # OTLP log exporter
        otlp_log_exporter = OTLPLogExporter(endpoint=self.otlp_endpoint, insecure=True)
        self.logger_provider.add_log_record_processor(LogBatchProcessor(otlp_log_exporter))
        
        # Set global logger provider
        _logs.set_logger_provider(self.logger_provider)
        
        # Configure Python logging to integrate with OpenTelemetry
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Add OTEL log handler
        from opentelemetry._logs import get_logger_provider
        from opentelemetry.sdk._logs._internal import LoggingHandler
        
        logger_provider = get_logger_provider()
        handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
        
        # Add to root logger
        logging.getLogger().addHandler(handler)
    
    def enable_auto_instrumentation(self):
        """Enable automatic instrumentation for common libraries"""
        
        if self.instrumentations_enabled.get("fastapi"):
            FastAPIInstrumentor().instrument()
        
        if self.instrumentations_enabled.get("requests"):
            RequestsInstrumentor().instrument()
        
        if self.instrumentations_enabled.get("redis"):
            RedisInstrumentor().instrument()
        
        if self.instrumentations_enabled.get("postgresql"):
            Psycopg2Instrumentor().instrument()
            SQLAlchemyInstrumentor().instrument()
            AsyncPGInstrumentor().instrument()
        
        if self.instrumentations_enabled.get("mongodb"):
            PymongoInstrumentor().instrument()
        
        if self.instrumentations_enabled.get("celery"):
            CeleryInstrumentor().instrument()
        
        if self.instrumentations_enabled.get("kafka"):
            KafkaInstrumentor().instrument()
        
        # HTTP client instrumentation
        HTTPXClientInstrumentor().instrument()
        
        # System and runtime metrics
        if self.instrumentations_enabled.get("system_metrics"):
            SystemMetricsInstrumentor().instrument()
        
        if self.instrumentations_enabled.get("runtime_metrics"):
            RuntimeMetricsInstrumentor().instrument()
    
    def configure_sampling(self, trace_sample_rate: float = 1.0):
        """Configure trace sampling"""
        from opentelemetry.sdk.trace.sampling import TraceIdRatioBased, ParentBased
        
        # Use parent-based sampling with ratio-based fallback
        sampler = ParentBased(root=TraceIdRatioBased(trace_sample_rate))
        
        if self.tracer_provider:
            # Update sampling configuration
            self.tracer_provider._sampler = sampler
    
    def get_security_metrics_collector(self) -> SecurityMetricsCollector:
        """Get security metrics collector instance"""
        if not self.metrics_collector:
            raise RuntimeError("Metrics not initialized. Call initialize_metrics() first.")
        return self.metrics_collector
    
    def shutdown(self):
        """Gracefully shutdown OpenTelemetry components"""
        if self.tracer_provider:
            self.tracer_provider.shutdown()
        
        if self.meter_provider:
            self.meter_provider.shutdown()
        
        if self.logger_provider:
            self.logger_provider.shutdown()


# Global configurator instance
_configurator: Optional[OpenTelemetryConfigurator] = None


def initialize_observability(service_name: str, service_version: str = "2.0.0", 
                           environment: str = None) -> OpenTelemetryConfigurator:
    """Initialize comprehensive observability"""
    global _configurator
    
    _configurator = OpenTelemetryConfigurator(service_name, service_version, environment)
    
    # Initialize all components
    _configurator.initialize_tracing()
    _configurator.initialize_metrics()
    _configurator.initialize_logging()
    _configurator.enable_auto_instrumentation()
    
    # Configure sampling based on environment
    if environment == "production":
        _configurator.configure_sampling(0.1)  # 10% sampling in production
    elif environment == "staging":
        _configurator.configure_sampling(0.5)  # 50% sampling in staging
    else:
        _configurator.configure_sampling(1.0)  # 100% sampling in development
    
    return _configurator


def get_security_metrics() -> SecurityMetricsCollector:
    """Get security metrics collector"""
    if not _configurator:
        raise RuntimeError("Observability not initialized. Call initialize_observability() first.")
    return _configurator.get_security_metrics_collector()


def get_tracer(name: str = __name__) -> trace.Tracer:
    """Get tracer instance"""
    return trace.get_tracer(name)


def get_meter(name: str = __name__) -> metrics.Meter:
    """Get meter instance"""
    return metrics.get_meter(name)


@asynccontextmanager
async def trace_security_operation(operation_name: str, attributes: Dict[str, Any] = None):
    """Context manager for tracing security operations"""
    tracer = get_tracer("antibot.security")
    
    with tracer.start_as_current_span(f"security/{operation_name}") as span:
        # Add default security attributes
        span.set_attribute("security.operation", operation_name)
        span.set_attribute("security.timestamp", int(time.time()))
        
        # Add custom attributes
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(f"security.{key}", str(value))
        
        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


# Decorators for easy instrumentation
def trace_security_endpoint(operation_name: str = None):
    """Decorator for tracing security endpoints"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__name__}"
            async with trace_security_operation(op_name):
                return await func(*args, **kwargs)
        return wrapper
    return decorator


def measure_security_metric(metric_type: str):
    """Decorator for measuring security metrics"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            metrics_collector = get_security_metrics()
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                # Record metric based on type
                if metric_type == "risk_assessment":
                    # Extract metrics from result (assuming structured result)
                    if hasattr(result, 'riskScore'):
                        metrics_collector.record_risk_assessment(
                            result.riskScore, result.confidence, 
                            duration_ms, result.modelVersion
                        )
                
                return result
                
            except Exception as e:
                # Record error metric
                duration_ms = (time.time() - start_time) * 1000
                # Log error metrics here
                raise
        return wrapper
    return decorator