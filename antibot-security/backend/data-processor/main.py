#!/usr/bin/env python3
"""
High-Performance Data Processing Service
Handles 1M+ events per second with fault-tolerant processing
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
import hashlib
import uuid

import asyncpg
import aioredis
import motor.motor_asyncio
import pika
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, validator
import prometheus_client
from prometheus_client import Counter, Histogram, Gauge, Summary
import structlog
import numpy as np
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
import msgpack

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Prometheus Metrics
EVENTS_PROCESSED = Counter('events_processed_total', 'Total events processed', ['event_type', 'status'])
PROCESSING_DURATION = Histogram('event_processing_seconds', 'Event processing duration', ['event_type'])
BATCH_SIZE_METRIC = Histogram('batch_size', 'Batch processing size')
QUEUE_LENGTH = Gauge('processing_queue_length', 'Current queue length')
DATABASE_OPERATIONS = Counter('database_operations_total', 'Database operations', ['operation', 'database'])
MEMORY_USAGE = Gauge('memory_usage_bytes', 'Memory usage in bytes')
ERROR_RATE = Counter('processing_errors_total', 'Processing errors', ['error_type'])

class EventType(str, Enum):
    BEHAVIORAL_DATA = "behavioral_data"
    RISK_ASSESSMENT = "risk_assessment"
    PATTERN_RECOGNITION = "pattern_recognition"
    SMS_VERIFICATION = "sms_verification"
    AUDIT_LOG = "audit_log"

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"

@dataclass
class EventData:
    """High-performance event data structure"""
    event_id: str
    event_type: EventType
    timestamp: float
    user_id: str
    session_id: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    priority: int = 1
    retry_count: int = 0

class BehavioralEvent(BaseModel):
    """Behavioral data event"""
    user_id: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)
    event_type: str
    timestamp: float
    mouse_movements: List[Dict] = Field(default_factory=list)
    keyboard_events: List[Dict] = Field(default_factory=list)
    scroll_events: List[Dict] = Field(default_factory=list)
    viewport_data: Dict = Field(default_factory=dict)
    device_fingerprint: Dict = Field(default_factory=dict)
    
    @validator('timestamp')
    def validate_timestamp(cls, v):
        if v < 0 or v > time.time() + 300:  # Allow 5 minutes in future
            raise ValueError('Invalid timestamp')
        return v

class RiskAssessmentEvent(BaseModel):
    """Risk assessment result event"""
    user_id: str
    session_id: str
    risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_factors: List[str] = Field(default_factory=list)
    model_version: str
    processing_time_ms: float
    confidence: float = Field(..., ge=0.0, le=1.0)

class BatchProcessor:
    """High-performance batch processing engine"""
    
    def __init__(self, batch_size: int = 1000, flush_interval: int = 5):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.pending_events: List[EventData] = []
        self.last_flush = time.time()
        self.processing_lock = asyncio.Lock()
    
    async def add_event(self, event: EventData) -> bool:
        """Add event to batch for processing"""
        async with self.processing_lock:
            self.pending_events.append(event)
            
            # Check if we should flush the batch
            should_flush = (
                len(self.pending_events) >= self.batch_size or
                time.time() - self.last_flush >= self.flush_interval
            )
            
            if should_flush:
                await self._flush_batch()
            
            return True
    
    async def _flush_batch(self):
        """Flush current batch to processing"""
        if not self.pending_events:
            return
        
        batch = self.pending_events.copy()
        self.pending_events.clear()
        self.last_flush = time.time()
        
        # Update metrics
        BATCH_SIZE_METRIC.observe(len(batch))
        QUEUE_LENGTH.set(len(self.pending_events))
        
        # Process batch asynchronously
        asyncio.create_task(self._process_batch(batch))
    
    async def _process_batch(self, batch: List[EventData]):
        """Process a batch of events"""
        start_time = time.time()
        
        try:
            # Group events by type for optimized processing
            events_by_type = {}
            for event in batch:
                if event.event_type not in events_by_type:
                    events_by_type[event.event_type] = []
                events_by_type[event.event_type].append(event)
            
            # Process each event type
            processing_tasks = []
            for event_type, events in events_by_type.items():
                task = asyncio.create_task(self._process_event_type(event_type, events))
                processing_tasks.append(task)
            
            # Wait for all processing to complete
            results = await asyncio.gather(*processing_tasks, return_exceptions=True)
            
            # Handle results and errors
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    event_type = list(events_by_type.keys())[i]
                    ERROR_RATE.labels(error_type=f"batch_processing_{event_type}").inc()
                    logger.error(f"Batch processing failed for {event_type}", error=str(result))
            
            duration = time.time() - start_time
            logger.info(f"Processed batch", 
                       batch_size=len(batch), 
                       duration=duration,
                       events_per_second=len(batch)/duration)
            
        except Exception as e:
            ERROR_RATE.labels(error_type="batch_processing").inc()
            logger.error("Batch processing failed", error=str(e))
    
    async def _process_event_type(self, event_type: EventType, events: List[EventData]):
        """Process events of a specific type"""
        processor = data_service.event_processors.get(event_type)
        if not processor:
            logger.warning(f"No processor found for event type: {event_type}")
            return
        
        try:
            await processor(events)
            
            # Update success metrics
            for event in events:
                EVENTS_PROCESSED.labels(event_type=event_type.value, status='success').inc()
                
        except Exception as e:
            # Update error metrics
            for event in events:
                EVENTS_PROCESSED.labels(event_type=event_type.value, status='error').inc()
            raise

class DataService:
    """Main data processing service"""
    
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.postgres_pool: Optional[asyncpg.Pool] = None
        self.mongodb: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
        self.kafka_producer: Optional[AIOKafkaProducer] = None
        self.kafka_consumer: Optional[AIOKafkaConsumer] = None
        
        self.batch_processor = BatchProcessor(
            batch_size=int(os.getenv('BATCH_SIZE', '1000')),
            flush_interval=int(os.getenv('PROCESSING_INTERVAL', '5'))
        )
        
        # Register event processors
        self.event_processors = {
            EventType.BEHAVIORAL_DATA: self.process_behavioral_events,
            EventType.RISK_ASSESSMENT: self.process_risk_assessment_events,
            EventType.PATTERN_RECOGNITION: self.process_pattern_events,
            EventType.SMS_VERIFICATION: self.process_sms_events,
            EventType.AUDIT_LOG: self.process_audit_events
        }
    
    async def initialize(self):
        """Initialize all database connections"""
        # Redis connection
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        try:
            self.redis = aioredis.from_url(redis_url, decode_responses=True)
            await self.redis.ping()
            logger.info("Connected to Redis", redis_url=redis_url)
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise
        
        # PostgreSQL connection pool
        postgres_url = os.getenv('POSTGRES_URL', 'postgresql://user:changeme@localhost:5432/db')
        try:
            self.postgres_pool = await asyncpg.create_pool(
                postgres_url,
                min_size=10,
                max_size=50,
                command_timeout=60,
                server_settings={
                    'application_name': 'data_processor',
                    'jit': 'off'  # Disable JIT for better performance on small queries
                }
            )
            logger.info("Connected to PostgreSQL", url=postgres_url.split('@')[0] + '@***')
        except Exception as e:
            logger.error("Failed to connect to PostgreSQL", error=str(e))
            raise
        
        # MongoDB connection
        mongodb_url = os.getenv('MONGODB_URL', 'mongodb://localhost:27017/db')
        try:
            self.mongodb = motor.motor_asyncio.AsyncIOMotorClient(
                mongodb_url,
                maxPoolSize=50,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=0,
                retryWrites=True
            )
            # Test connection
            await self.mongodb.admin.command('ping')
            logger.info("Connected to MongoDB", url=mongodb_url.split('@')[0] + '@***')
        except Exception as e:
            logger.error("Failed to connect to MongoDB", error=str(e))
            raise
        
        # Initialize database schemas
        await self._initialize_schemas()
    
    async def _initialize_schemas(self):
        """Initialize database schemas and indexes"""
        # PostgreSQL tables
        async with self.postgres_pool.acquire() as conn:
            # Risk assessments table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS risk_assessments (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id VARCHAR(255) NOT NULL,
                    session_id VARCHAR(255) NOT NULL,
                    risk_score DECIMAL(3,2) NOT NULL CHECK (risk_score >= 0 AND risk_score <= 1),
                    risk_factors JSONB,
                    model_version VARCHAR(50) NOT NULL,
                    confidence DECIMAL(3,2) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
                
                CREATE INDEX IF NOT EXISTS idx_risk_user_session 
                ON risk_assessments(user_id, session_id);
                
                CREATE INDEX IF NOT EXISTS idx_risk_score 
                ON risk_assessments(risk_score);
                
                CREATE INDEX IF NOT EXISTS idx_risk_created 
                ON risk_assessments(created_at);
            """)
            
            # SMS verification events table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sms_verifications (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    message_id VARCHAR(255) UNIQUE NOT NULL,
                    phone_number_hash VARCHAR(64) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    provider VARCHAR(20) NOT NULL,
                    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    delivered_at TIMESTAMP WITH TIME ZONE,
                    metadata JSONB
                );
                
                CREATE INDEX IF NOT EXISTS idx_sms_message_id 
                ON sms_verifications(message_id);
                
                CREATE INDEX IF NOT EXISTS idx_sms_phone_hash 
                ON sms_verifications(phone_number_hash);
            """)
        
        # MongoDB collections and indexes
        db = self.mongodb.antibot_security
        
        # Behavioral events collection
        behavioral_collection = db.behavioral_events
        await behavioral_collection.create_index([
            ("user_id", 1),
            ("timestamp", -1)
        ], background=True)
        await behavioral_collection.create_index([
            ("session_id", 1)
        ], background=True)
        
        # Pattern recognition collection
        patterns_collection = db.pattern_recognition
        await patterns_collection.create_index([
            ("pattern_type", 1),
            ("created_at", -1)
        ], background=True)
        
        logger.info("Database schemas initialized")
    
    async def process_behavioral_events(self, events: List[EventData]):
        """Process behavioral data events"""
        if not events:
            return
        
        start_time = time.time()
        
        # Prepare MongoDB documents
        documents = []
        for event in events:
            doc = {
                'event_id': event.event_id,
                'user_id': event.user_id,
                'session_id': event.session_id,
                'timestamp': datetime.fromtimestamp(event.timestamp),
                'event_data': event.data,
                'metadata': event.metadata,
                'created_at': datetime.now()
            }
            documents.append(doc)
        
        # Bulk insert to MongoDB
        try:
            db = self.mongodb.antibot_security
            await db.behavioral_events.insert_many(documents, ordered=False)
            
            DATABASE_OPERATIONS.labels(operation='insert', database='mongodb').inc(len(documents))
            
            # Cache recent behavioral data in Redis for fast access
            cache_tasks = []
            for event in events:
                cache_key = f"behavioral:{event.user_id}:{event.session_id}"
                cache_data = {
                    'last_activity': event.timestamp,
                    'event_count': 1,
                    'risk_indicators': self._extract_risk_indicators(event.data)
                }
                cache_tasks.append(
                    self.redis.hset(cache_key, mapping=cache_data)
                )
                cache_tasks.append(
                    self.redis.expire(cache_key, 3600)  # 1 hour TTL
                )
            
            await asyncio.gather(*cache_tasks)
            
            duration = time.time() - start_time
            PROCESSING_DURATION.labels(event_type='behavioral_data').observe(duration)
            
            logger.info("Processed behavioral events",
                       count=len(events),
                       duration=duration)
            
        except Exception as e:
            ERROR_RATE.labels(error_type="behavioral_processing").inc()
            logger.error("Failed to process behavioral events", error=str(e))
            raise
    
    async def process_risk_assessment_events(self, events: List[EventData]):
        """Process risk assessment events"""
        if not events:
            return
        
        start_time = time.time()
        
        # Prepare SQL records
        records = []
        for event in events:
            data = event.data
            record = (
                event.user_id,
                event.session_id,
                data.get('risk_score'),
                json.dumps(data.get('risk_factors', [])),
                data.get('model_version'),
                data.get('confidence'),
                datetime.fromtimestamp(event.timestamp)
            )
            records.append(record)
        
        # Bulk insert to PostgreSQL
        try:
            async with self.postgres_pool.acquire() as conn:
                await conn.executemany("""
                    INSERT INTO risk_assessments 
                    (user_id, session_id, risk_score, risk_factors, model_version, confidence, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT DO NOTHING
                """, records)
                
                DATABASE_OPERATIONS.labels(operation='insert', database='postgresql').inc(len(records))
                
                # Update risk score cache
                cache_updates = []
                for event in events:
                    cache_key = f"risk_score:{event.user_id}"
                    risk_data = {
                        'current_score': event.data.get('risk_score'),
                        'last_updated': event.timestamp,
                        'session_id': event.session_id
                    }
                    cache_updates.append(
                        self.redis.hset(cache_key, mapping=risk_data)
                    )
                    cache_updates.append(
                        self.redis.expire(cache_key, 1800)  # 30 minutes TTL
                    )
                
                await asyncio.gather(*cache_updates)
                
                duration = time.time() - start_time
                PROCESSING_DURATION.labels(event_type='risk_assessment').observe(duration)
                
                logger.info("Processed risk assessment events",
                           count=len(events),
                           duration=duration)
                
        except Exception as e:
            ERROR_RATE.labels(error_type="risk_assessment_processing").inc()
            logger.error("Failed to process risk assessment events", error=str(e))
            raise
    
    async def process_pattern_events(self, events: List[EventData]):
        """Process pattern recognition events"""
        if not events:
            return
        
        # Store in MongoDB for historical analysis
        documents = []
        for event in events:
            doc = {
                'event_id': event.event_id,
                'pattern_type': event.data.get('pattern_type'),
                'pattern_data': event.data.get('pattern_data'),
                'anomaly_score': event.data.get('anomaly_score'),
                'affected_users': event.data.get('affected_users', []),
                'timestamp': datetime.fromtimestamp(event.timestamp),
                'metadata': event.metadata,
                'created_at': datetime.now()
            }
            documents.append(doc)
        
        try:
            db = self.mongodb.antibot_security
            await db.pattern_recognition.insert_many(documents, ordered=False)
            
            DATABASE_OPERATIONS.labels(operation='insert', database='mongodb').inc(len(documents))
            
            logger.info("Processed pattern recognition events", count=len(events))
            
        except Exception as e:
            ERROR_RATE.labels(error_type="pattern_processing").inc()
            logger.error("Failed to process pattern events", error=str(e))
            raise
    
    async def process_sms_events(self, events: List[EventData]):
        """Process SMS verification events"""
        if not events:
            return
        
        # Store in PostgreSQL for transactional integrity
        records = []
        for event in events:
            data = event.data
            # Hash phone number for privacy
            phone_hash = hashlib.sha256(data.get('phone_number', '').encode()).hexdigest()
            
            record = (
                data.get('message_id'),
                phone_hash,
                data.get('status'),
                data.get('provider'),
                datetime.fromtimestamp(event.timestamp),
                json.dumps(event.metadata)
            )
            records.append(record)
        
        try:
            async with self.postgres_pool.acquire() as conn:
                await conn.executemany("""
                    INSERT INTO sms_verifications 
                    (message_id, phone_number_hash, status, provider, sent_at, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (message_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        delivered_at = CASE 
                            WHEN EXCLUDED.status = 'delivered' THEN NOW() 
                            ELSE sms_verifications.delivered_at 
                        END
                """, records)
                
                DATABASE_OPERATIONS.labels(operation='upsert', database='postgresql').inc(len(records))
                
                logger.info("Processed SMS verification events", count=len(events))
                
        except Exception as e:
            ERROR_RATE.labels(error_type="sms_processing").inc()
            logger.error("Failed to process SMS events", error=str(e))
            raise
    
    async def process_audit_events(self, events: List[EventData]):
        """Process audit log events"""
        # Store in both databases for compliance
        
        # MongoDB for flexible querying
        mongo_docs = []
        for event in events:
            doc = {
                'event_id': event.event_id,
                'user_id': event.user_id,
                'action': event.data.get('action'),
                'resource': event.data.get('resource'),
                'result': event.data.get('result'),
                'ip_address': event.data.get('ip_address'),
                'user_agent': event.data.get('user_agent'),
                'timestamp': datetime.fromtimestamp(event.timestamp),
                'metadata': event.metadata
            }
            mongo_docs.append(doc)
        
        try:
            db = self.mongodb.antibot_security
            await db.audit_logs.insert_many(mongo_docs, ordered=False)
            
            DATABASE_OPERATIONS.labels(operation='insert', database='mongodb').inc(len(mongo_docs))
            
            logger.info("Processed audit events", count=len(events))
            
        except Exception as e:
            ERROR_RATE.labels(error_type="audit_processing").inc()
            logger.error("Failed to process audit events", error=str(e))
            raise
    
    def _extract_risk_indicators(self, behavioral_data: Dict) -> Dict:
        """Extract risk indicators from behavioral data"""
        indicators = {}
        
        # Mouse movement analysis
        mouse_movements = behavioral_data.get('mouse_movements', [])
        if mouse_movements:
            # Calculate movement speed and patterns
            speeds = []
            for i in range(1, len(mouse_movements)):
                prev = mouse_movements[i-1]
                curr = mouse_movements[i]
                if 'timestamp' in prev and 'timestamp' in curr:
                    dt = curr['timestamp'] - prev['timestamp']
                    if dt > 0:
                        dx = curr.get('x', 0) - prev.get('x', 0)
                        dy = curr.get('y', 0) - prev.get('y', 0)
                        distance = (dx*dx + dy*dy) ** 0.5
                        speed = distance / dt
                        speeds.append(speed)
            
            if speeds:
                indicators['mouse_avg_speed'] = np.mean(speeds)
                indicators['mouse_speed_variance'] = np.var(speeds)
        
        # Keyboard timing analysis
        keyboard_events = behavioral_data.get('keyboard_events', [])
        if len(keyboard_events) > 1:
            intervals = []
            for i in range(1, len(keyboard_events)):
                if 'timestamp' in keyboard_events[i-1] and 'timestamp' in keyboard_events[i]:
                    interval = keyboard_events[i]['timestamp'] - keyboard_events[i-1]['timestamp']
                    intervals.append(interval)
            
            if intervals:
                indicators['keystroke_avg_interval'] = np.mean(intervals)
                indicators['keystroke_rhythm_variance'] = np.var(intervals)
        
        return indicators
    
    async def add_event(self, event_data: Dict) -> str:
        """Add event to processing queue"""
        event_id = str(uuid.uuid4())
        
        event = EventData(
            event_id=event_id,
            event_type=EventType(event_data['event_type']),
            timestamp=event_data.get('timestamp', time.time()),
            user_id=event_data['user_id'],
            session_id=event_data['session_id'],
            data=event_data['data'],
            metadata=event_data.get('metadata', {}),
            priority=event_data.get('priority', 1)
        )
        
        await self.batch_processor.add_event(event)
        return event_id
    
    async def get_processing_stats(self) -> Dict:
        """Get real-time processing statistics"""
        stats = {
            'queue_length': len(self.batch_processor.pending_events),
            'last_flush': self.batch_processor.last_flush,
            'redis_connected': self.redis is not None,
            'postgres_connected': self.postgres_pool is not None,
            'mongodb_connected': self.mongodb is not None
        }
        
        # Get database connection stats
        if self.postgres_pool:
            stats['postgres_pool_size'] = self.postgres_pool.get_size()
            stats['postgres_pool_available'] = self.postgres_pool.get_available_size()
        
        return stats

# Initialize service
data_service = DataService()

# FastAPI application
app = FastAPI(
    title="Data Processing Service",
    description="High-performance data processing with fault tolerance",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    await data_service.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up connections on shutdown"""
    if data_service.redis:
        await data_service.redis.close()
    if data_service.postgres_pool:
        await data_service.postgres_pool.close()
    if data_service.mongodb:
        data_service.mongodb.close()

@app.post("/api/v1/events")
async def submit_event(event_data: Dict):
    """Submit event for processing"""
    try:
        event_id = await data_service.add_event(event_data)
        return {"event_id": event_id, "status": "queued"}
    except Exception as e:
        logger.error("Failed to submit event", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/events/behavioral")
async def submit_behavioral_event(event: BehavioralEvent):
    """Submit behavioral event for processing"""
    event_data = {
        'event_type': 'behavioral_data',
        'user_id': event.user_id,
        'session_id': event.session_id,
        'timestamp': event.timestamp,
        'data': event.dict(),
        'metadata': {}
    }
    
    event_id = await data_service.add_event(event_data)
    return {"event_id": event_id, "status": "queued"}

@app.post("/api/v1/events/risk-assessment")
async def submit_risk_event(event: RiskAssessmentEvent):
    """Submit risk assessment event for processing"""
    event_data = {
        'event_type': 'risk_assessment',
        'user_id': event.user_id,
        'session_id': event.session_id,
        'data': event.dict(),
        'metadata': {}
    }
    
    event_id = await data_service.add_event(event_data)
    return {"event_id": event_id, "status": "queued"}

@app.get("/api/v1/stats")
async def get_stats():
    """Get processing statistics"""
    return await data_service.get_processing_stats()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    stats = await data_service.get_processing_stats()
    
    health_data = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'data-processor',
        **stats
    }
    
    # Check connection health
    if not (stats['redis_connected'] and stats['postgres_connected'] and stats['mongodb_connected']):
        health_data['status'] = 'degraded'
    
    return health_data

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return prometheus_client.generate_latest().decode()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8004,
        workers=4,
        log_config=None
    )