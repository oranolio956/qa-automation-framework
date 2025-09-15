#!/usr/bin/env python3
"""
Fault-Tolerant SMS Verification Service
High-availability SMS processing with multiple provider support and circuit breakers
"""

import asyncio
import json
import os
import time
from datetime import datetime
from typing import Dict, Optional, Any
from enum import Enum

import aioredis
import pika
from concurrent.futures import ThreadPoolExecutor
from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioException
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from pydantic_settings import BaseSettings
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from tenacity import retry, stop_after_attempt, wait_exponential
import prometheus_client
from prometheus_client import Counter, Histogram, Gauge
import structlog

# Secrets/config access with Vault fallback
try:
    from utils.vault_client import get_secret, get_int
except Exception:
    def get_secret(name: str, default=None, **kwargs):
        return os.getenv(name, default)
    def get_int(name: str, default=None, **kwargs):
        try:
            return int(os.getenv(name, default))
        except Exception:
            return default

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
REQUESTS_TOTAL = Counter('sms_requests_total', 'Total SMS requests', ['provider', 'status'])
REQUEST_DURATION = Histogram('sms_request_duration_seconds', 'SMS request duration', ['provider'])
CIRCUIT_BREAKER_STATE = Gauge('circuit_breaker_state', 'Circuit breaker state', ['provider'])
QUEUE_SIZE = Gauge('sms_queue_size', 'SMS queue size')
RATE_LIMIT_HITS = Counter('rate_limit_hits_total', 'Rate limit hits', ['phone_number'])

class SMSProvider(str, Enum):
    TWILIO = "twilio"
    AWS_SNS = "aws_sns"

class SMSStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent" 
    DELIVERED = "delivered"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"

class CircuitBreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class SMSRequest(BaseModel):
    phone_number: str = Field(..., regex=r'^\+[1-9]\d{1,14}$')
    message: str = Field(..., min_length=1, max_length=1600)
    priority: int = Field(default=1, ge=1, le=5)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('phone_number')
    def validate_phone(cls, v):
        # Basic E.164 format validation
        if not v.startswith('+') or len(v) < 8 or len(v) > 16:
            raise ValueError('Invalid phone number format')
        return v

class SMSResponse(BaseModel):
    message_id: str
    status: SMSStatus
    provider: SMSProvider
    phone_number: str
    sent_at: datetime
    estimated_delivery: Optional[datetime] = None
    cost: Optional[float] = None

class CircuitBreaker:
    """Circuit breaker implementation for SMS providers"""
    
    def __init__(self, failure_threshold: int = 10, timeout_duration: int = 30):
        self.failure_threshold = failure_threshold
        self.timeout_duration = timeout_duration
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
    
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time < self.timeout_duration:
                raise HTTPException(status_code=503, detail="Circuit breaker is OPEN")
            else:
                self.state = CircuitBreakerState.HALF_OPEN
        
        try:
            result = await func(*args, **kwargs)
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.reset()
            return result
        except Exception as e:
            self.record_failure()
            raise e
    
    def record_failure(self):
        """Record a failure and potentially open the circuit"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker OPENED after {self.failure_count} failures")
    
    def reset(self):
        """Reset the circuit breaker"""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
        logger.info("Circuit breaker CLOSED - service recovered")

class SMSProviderInterface:
    """Base interface for SMS providers"""
    
    async def send_sms(self, phone_number: str, message: str, metadata: Dict) -> Dict[str, Any]:
        raise NotImplementedError
    
    async def get_delivery_status(self, message_id: str) -> Dict[str, Any]:
        raise NotImplementedError

class TwilioProvider(SMSProviderInterface):
    """Twilio SMS provider implementation with phone number pool integration"""
    
    def __init__(self):
        self.account_sid = get_secret('TWILIO_ACCOUNT_SID')
        self.auth_token = get_secret('TWILIO_AUTH_TOKEN')
        self.phone_number = get_secret('TWILIO_PHONE_NUMBER')
        self.area_code = get_secret('TWILIO_AREA_CODE', '720')
        self.client = None
        
        if not all([self.account_sid, self.auth_token]):
            logger.warning("Twilio credentials not fully configured")
        else:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Twilio client"""
        try:
            self.client = TwilioClient(self.account_sid, self.auth_token)
            logger.info("Twilio client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {e}")
    
    async def _get_phone_number(self, metadata: Dict) -> str:
        """Get phone number from pool or use default"""
        # Try to get from phone pool if available
        pool_number = metadata.get('from_phone_number')
        if pool_number:
            return pool_number
        
        # Use default phone number
        if self.phone_number:
            return self.phone_number
            
        # Try to get from phone pool management
        try:
            # Import here to avoid circular imports
            from utils.twilio_pool import get_number
            pool_number = get_number()
            if pool_number:
                return pool_number
        except Exception as e:
            logger.warning(f"Failed to get number from pool: {e}")
        
        raise HTTPException(status_code=503, detail="No Twilio phone number available")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def send_sms(self, phone_number: str, message: str, metadata: Dict) -> Dict[str, Any]:
        """Send SMS via Twilio API with real client"""
        if not self.client:
            raise HTTPException(status_code=503, detail="Twilio client not initialized")
        
        try:
            from_number = await self._get_phone_number(metadata)
            
            # Use thread pool for synchronous Twilio call
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                message_instance = await loop.run_in_executor(
                    executor,
                    lambda: self.client.messages.create(
                        body=message,
                        from_=from_number,
                        to=phone_number
                    )
                )
            
            return {
                'message_id': message_instance.sid,
                'status': message_instance.status,
                'provider': 'twilio',
                'cost': float(message_instance.price) if message_instance.price else None,
                'from_number': from_number
            }
            
        except TwilioException as e:
            logger.error(f"Twilio error: {e}")
            raise HTTPException(status_code=503, detail=f"Twilio error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in Twilio send: {e}")
            raise
    
    async def get_delivery_status(self, message_id: str) -> Dict[str, Any]:
        """Get delivery status from Twilio with real API call"""
        if not self.client:
            raise HTTPException(status_code=503, detail="Twilio client not initialized")
        
        try:
            # Use thread pool for synchronous Twilio call
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                message_instance = await loop.run_in_executor(
                    executor,
                    lambda: self.client.messages(message_id).fetch()
                )
            
            return {
                'message_id': message_id,
                'status': message_instance.status,
                'error_code': message_instance.error_code,
                'error_message': message_instance.error_message,
                'date_sent': message_instance.date_sent.isoformat() if message_instance.date_sent else None,
                'date_updated': message_instance.date_updated.isoformat() if message_instance.date_updated else None
            }
            
        except TwilioException as e:
            logger.error(f"Twilio status check error: {e}")
            return {
                'message_id': message_id,
                'status': 'unknown',
                'error_code': 'STATUS_CHECK_FAILED',
                'error_message': str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error in Twilio status check: {e}")
            return {
                'message_id': message_id,
                'status': 'unknown',
                'error_code': 'STATUS_CHECK_FAILED',
                'error_message': str(e)
            }

class AWSSNSProvider(SMSProviderInterface):
    """AWS SNS SMS provider implementation with real API integration"""
    
    def __init__(self):
        self.access_key = get_secret('AWS_SNS_ACCESS_KEY')
        self.secret_key = get_secret('AWS_SNS_SECRET_KEY')
        self.region = get_secret('AWS_SNS_REGION', 'us-east-1')
        self.sns_client = None
        
        if not all([self.access_key, self.secret_key]):
            logger.warning("AWS SNS credentials not configured")
        else:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize AWS SNS client"""
        try:
            self.sns_client = boto3.client(
                'sns',
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region
            )
            logger.info(f"AWS SNS client initialized for region {self.region}")
        except Exception as e:
            logger.error(f"Failed to initialize AWS SNS client: {e}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def send_sms(self, phone_number: str, message: str, metadata: Dict) -> Dict[str, Any]:
        """Send SMS via AWS SNS with real API call"""
        if not self.sns_client:
            raise HTTPException(status_code=503, detail="AWS SNS client not initialized")
        
        try:
            # Use thread pool for synchronous boto3 call
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                response = await loop.run_in_executor(
                    executor,
                    self.sns_client.publish,
                    phone_number,  # PhoneNumber
                    message,       # Message
                )
            
            message_id = response['MessageId']
            
            return {
                'message_id': message_id,
                'status': 'sent',
                'provider': 'aws_sns',
                'cost': 0.00645,  # Approximate AWS SMS cost
                'response_metadata': response.get('ResponseMetadata', {})
            }
        
        except (BotoCoreError, ClientError) as e:
            logger.error(f"AWS SNS error: {e}")
            raise HTTPException(status_code=503, detail=f"AWS SNS error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in AWS SNS send: {e}")
            raise
    
    async def get_delivery_status(self, message_id: str) -> Dict[str, Any]:
        """Get delivery status from AWS SNS"""
        # AWS SNS doesn't provide delivery receipts by default
        # This would require setting up SNS delivery status logging
        # For now, return optimistic status
        
        try:
            # In production, you'd query CloudWatch or delivery receipts
            return {
                'message_id': message_id,
                'status': 'delivered',  # Optimistic assumption
                'error_code': None,
                'error_message': None,
                'note': 'AWS SNS delivery status requires additional setup'
            }
        except Exception as e:
            logger.error(f"Error getting AWS SNS delivery status: {e}")
            return {
                'message_id': message_id,
                'status': 'unknown',
                'error_code': 'STATUS_CHECK_FAILED',
                'error_message': str(e)
            }

class SMSService:
    """Main SMS service with fault tolerance and load balancing"""
    
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.rabbit_connection = None
        self.rabbit_channel = None
        
        # Initialize providers with circuit breakers
        self.providers = {
            SMSProvider.TWILIO: TwilioProvider(),
            SMSProvider.AWS_SNS: AWSSNSProvider()
        }
        
        self.circuit_breakers = {
            provider: CircuitBreaker(
                failure_threshold=get_int('CIRCUIT_BREAKER_THRESHOLD', 10),
                timeout_duration=get_int('CIRCUIT_BREAKER_TIMEOUT', 30)
            ) for provider in self.providers.keys()
        }
        
        self.rate_limit_per_phone = get_int('RATE_LIMIT_PER_PHONE', 5)
        self.rate_limit_window = get_int('RATE_LIMIT_WINDOW', 300)  # 5 minutes
    
    async def initialize(self):
        """Initialize Redis and RabbitMQ connections with enhanced configuration"""
        # Redis connection with enhanced configuration
        redis_url = get_secret('REDIS_URL', 'redis://localhost:6379/0')
        max_connections = get_int('REDIS_MAX_CONNECTIONS', 100)
        
        try:
            self.redis = aioredis.from_url(
                redis_url, 
                decode_responses=True,
                max_connections=max_connections,
                socket_keepalive=True,
                socket_keepalive_options={1: 1, 2: 3, 3: 5},
                retry_on_timeout=True,
                health_check_interval=30
            )
            await self.redis.ping()
            logger.info("Connected to Redis", redis_url=redis_url, max_connections=max_connections)
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise
        
        # RabbitMQ connection with production settings
        rabbitmq_url = get_secret('RABBITMQ_URL', 'amqp://admin:changeme@localhost:5672/')
        exchange_name = get_secret('RABBITMQ_EXCHANGE', 'sms_exchange')
        
        try:
            # Connection parameters with better configuration
            connection_params = pika.URLParameters(rabbitmq_url)
            connection_params.heartbeat = 600
            connection_params.blocked_connection_timeout = 300
            
            self.rabbit_connection = pika.BlockingConnection(connection_params)
            self.rabbit_channel = self.rabbit_connection.channel()
            
            # Configure QoS for better performance
            self.rabbit_channel.basic_qos(prefetch_count=10, global_qos=True)
            
            # Declare exchange
            self.rabbit_channel.exchange_declare(
                exchange=exchange_name,
                exchange_type='direct',
                durable=True
            )
            
            # Declare priority queues for different message priorities
            for priority in range(1, 6):  # Priority 1-5
                queue_name = f'sms_queue_p{priority}'
                self.rabbit_channel.queue_declare(
                    queue=queue_name,
                    durable=True,
                    arguments={
                        'x-message-ttl': 3600000,  # 1 hour TTL
                        'x-dead-letter-exchange': 'sms_dlx',
                        'x-dead-letter-routing-key': f'failed.p{priority}',
                        'x-max-priority': 10
                    }
                )
                
                # Bind queue to exchange
                self.rabbit_channel.queue_bind(
                    exchange=exchange_name,
                    queue=queue_name,
                    routing_key=f'sms.p{priority}'
                )
            
            # Declare dead letter queue
            self.rabbit_channel.queue_declare(queue='sms_failed_dlq', durable=True)
            
            # Declare dead letter exchange
            self.rabbit_channel.exchange_declare(
                exchange='sms_dlx',
                exchange_type='direct',
                durable=True
            )
            
            # Bind DLQ to dead letter exchange
            self.rabbit_channel.queue_bind(
                exchange='sms_dlx',
                queue='sms_failed_dlq',
                routing_key='failed.*'
            )
            
            logger.info("Connected to RabbitMQ", rabbitmq_url=rabbitmq_url.split('@')[0] + '@***')
        except Exception as e:
            logger.error("Failed to connect to RabbitMQ", error=str(e))
            # Continue without RabbitMQ for degraded service
    
    async def check_rate_limit(self, phone_number: str) -> bool:
        """Check if phone number is rate limited"""
        if not self.redis:
            return False  # Skip rate limiting if Redis unavailable
        
        key = f"rate_limit:sms:{phone_number}"
        current = await self.redis.get(key)
        
        if current and int(current) >= self.rate_limit_per_phone:
            RATE_LIMIT_HITS.labels(phone_number=phone_number[:5] + "***").inc()
            return True
        
        # Increment counter
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, self.rate_limit_window)
        await pipe.execute()
        
        return False
    
    async def select_provider(self) -> SMSProvider:
        """Select the best available SMS provider"""
        for provider in [SMSProvider.TWILIO, SMSProvider.AWS_SNS]:
            circuit_breaker = self.circuit_breakers[provider]
            if circuit_breaker.state != CircuitBreakerState.OPEN:
                return provider
        
        # All circuit breakers are open, try the first one
        logger.warning("All SMS providers have open circuit breakers, trying fallback")
        return SMSProvider.TWILIO
    
    async def send_sms_with_fallback(self, request: SMSRequest) -> SMSResponse:
        """Send SMS with automatic provider fallback"""
        # Check rate limiting
        if await self.check_rate_limit(request.phone_number):
            raise HTTPException(status_code=429, detail="Rate limit exceeded for phone number")
        
        providers_to_try = [SMSProvider.TWILIO, SMSProvider.AWS_SNS]
        last_exception = None
        
        for provider in providers_to_try:
            try:
                circuit_breaker = self.circuit_breakers[provider]
                provider_instance = self.providers[provider]
                
                start_time = time.time()
                
                # Update circuit breaker metrics
                CIRCUIT_BREAKER_STATE.labels(provider=provider.value).set(
                    1 if circuit_breaker.state == CircuitBreakerState.OPEN else 0
                )
                
                result = await circuit_breaker.call(
                    provider_instance.send_sms,
                    request.phone_number,
                    request.message,
                    request.metadata
                )
                
                # Record success metrics
                duration = time.time() - start_time
                REQUEST_DURATION.labels(provider=provider.value).observe(duration)
                REQUESTS_TOTAL.labels(provider=provider.value, status='success').inc()
                
                # Store message in Redis for status tracking
                if self.redis:
                    message_data = {
                        'message_id': result['message_id'],
                        'phone_number': request.phone_number,
                        'provider': provider.value,
                        'status': result['status'],
                        'sent_at': datetime.now().isoformat(),
                        'metadata': json.dumps(request.metadata)
                    }
                    await self.redis.hset(f"sms:{result['message_id']}", mapping=message_data)
                    await self.redis.expire(f"sms:{result['message_id']}", 86400 * 7)  # 7 days
                
                logger.info("SMS sent successfully", 
                          message_id=result['message_id'],
                          provider=provider.value,
                          phone=request.phone_number[:5] + "***")
                
                return SMSResponse(
                    message_id=result['message_id'],
                    status=SMSStatus(result['status']),
                    provider=provider,
                    phone_number=request.phone_number,
                    sent_at=datetime.now(),
                    cost=result.get('cost')
                )
                
            except Exception as e:
                last_exception = e
                REQUESTS_TOTAL.labels(provider=provider.value, status='error').inc()
                logger.warning(f"SMS provider {provider.value} failed", error=str(e))
                continue
        
        # All providers failed
        REQUESTS_TOTAL.labels(provider='all', status='failed').inc()
        raise HTTPException(status_code=503, detail=f"All SMS providers failed: {str(last_exception)}")
    
    async def queue_sms(self, request: SMSRequest):
        """Queue SMS for asynchronous processing with enhanced routing"""
        if not self.rabbit_channel:
            # Fallback to direct processing if queue unavailable
            logger.warning("RabbitMQ unavailable, processing SMS directly")
            return await self.send_sms_with_fallback(request)
        
        try:
            message_body = json.dumps({
                'phone_number': request.phone_number,
                'message': request.message,
                'priority': request.priority,
                'metadata': request.metadata,
                'queued_at': datetime.now().isoformat(),
                'retry_count': 0,
                'max_retries': 3
            })
            
            # Use exchange routing for better message distribution
            exchange_name = get_secret('RABBITMQ_EXCHANGE', 'sms_exchange')
            routing_key = f'sms.p{request.priority}'
            
            self.rabbit_channel.basic_publish(
                exchange=exchange_name,
                routing_key=routing_key,
                body=message_body,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    priority=request.priority,
                    message_id=f"sms_{int(time.time())}_{hash(request.phone_number) % 10000}",
                    timestamp=int(time.time()),
                    headers={
                        'phone_number_hash': hash(request.phone_number) % 10000,
                        'message_length': len(request.message),
                        'queued_by': 'sms-service'
                    }
                )
            )
            
            # Update queue metrics
            try:
                queue_name = f'sms_queue_p{request.priority}'
                queue_info = self.rabbit_channel.queue_declare(queue=queue_name, passive=True)
                QUEUE_SIZE.set(queue_info.method.message_count)
            except Exception as e:
                logger.warning(f"Failed to update queue metrics: {e}")
            
            logger.info("SMS queued for processing", 
                       phone=request.phone_number[:5] + "***",
                       priority=request.priority,
                       routing_key=routing_key)
            
            return {
                'status': 'queued',
                'message': 'SMS queued for processing',
                'priority': request.priority,
                'routing_key': routing_key
            }
            
        except Exception as e:
            logger.error(f"Failed to queue SMS: {e}")
            # Fallback to direct processing
            logger.info("Falling back to direct SMS processing")
            return await self.send_sms_with_fallback(request)
    
    async def get_message_status(self, message_id: str) -> Dict[str, Any]:
        """Get SMS delivery status"""
        if not self.redis:
            raise HTTPException(status_code=503, detail="Status service unavailable")
        
        message_data = await self.redis.hgetall(f"sms:{message_id}")
        if not message_data:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Try to get updated status from provider
        provider_name = message_data.get('provider')
        if provider_name in [p.value for p in SMSProvider]:
            provider = SMSProvider(provider_name)
            try:
                provider_instance = self.providers[provider]
                status_update = await provider_instance.get_delivery_status(message_id)
                
                # Update Redis with latest status
                await self.redis.hset(f"sms:{message_id}", 'status', status_update['status'])
                message_data['status'] = status_update['status']
                
            except Exception as e:
                logger.warning(f"Failed to get status update from {provider_name}", error=str(e))
        
        return {
            'message_id': message_id,
            'status': message_data.get('status'),
            'provider': message_data.get('provider'),
            'sent_at': message_data.get('sent_at'),
            'phone_number': message_data.get('phone_number', '')[:5] + "***"
        }

# Initialize service
sms_service = SMSService()

# FastAPI application
app = FastAPI(
    title="SMS Verification Service",
    description="Fault-tolerant SMS service with multiple provider support",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    await sms_service.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up connections on shutdown"""
    if sms_service.redis:
        await sms_service.redis.close()
    if sms_service.rabbit_connection and not sms_service.rabbit_connection.is_closed:
        sms_service.rabbit_connection.close()

@app.post("/api/v1/sms/send", response_model=SMSResponse)
async def send_sms(request: SMSRequest, background_tasks: BackgroundTasks):
    """Send SMS with immediate response"""
    try:
        return await sms_service.send_sms_with_fallback(request)
    except Exception as e:
        logger.error("Failed to send SMS", error=str(e))
        raise

@app.post("/api/v1/sms/queue")
async def queue_sms(request: SMSRequest):
    """Queue SMS for asynchronous processing"""
    try:
        await sms_service.queue_sms(request)
        return {"status": "queued", "message": "SMS queued for processing"}
    except Exception as e:
        logger.error("Failed to queue SMS", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/sms/{message_id}/status")
async def get_sms_status(message_id: str):
    """Get SMS delivery status"""
    return await sms_service.get_message_status(message_id)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_data = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': get_secret('SERVICE_NAME', 'sms-service'),
        'redis_connected': sms_service.redis is not None,
        'rabbitmq_connected': sms_service.rabbit_connection is not None
    }
    
    # Check provider health
    provider_health = {}
    for provider_name, circuit_breaker in sms_service.circuit_breakers.items():
        provider_health[provider_name.value] = {
            'circuit_breaker_state': circuit_breaker.state.value,
            'failure_count': circuit_breaker.failure_count
        }
    
    health_data['providers'] = provider_health
    
    # Test Redis connection
    if sms_service.redis:
        try:
            await sms_service.redis.ping()
            health_data['redis_status'] = 'connected'
        except:
            health_data['redis_status'] = 'disconnected'
            health_data['status'] = 'degraded'
    
    return health_data

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return prometheus_client.generate_latest().decode()

# Configuration settings
class Settings(BaseSettings):
    service_name: str = "sms-service"
    log_level: str = "INFO"
    redis_url: str = "redis://localhost:6379/0"
    rabbitmq_url: str = "amqp://admin:changeme@localhost:5672/"
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    aws_sns_access_key: str = ""
    aws_sns_secret_key: str = ""
    aws_sns_region: str = "us-east-1"
    
    class Config:
        env_file = ".env"

settings = Settings()

# Phone number pool status endpoint
@app.get("/api/v1/phone-pool/status")
async def get_phone_pool_status():
    """Get Twilio phone number pool status"""
    try:
        from utils.twilio_pool import get_pool_status, cleanup_cooldown
        # Clean up expired cooldown numbers
        cleanup_cooldown()
        status = get_pool_status()
        return status
    except Exception as e:
        logger.error(f"Failed to get phone pool status: {e}")
        return {"error": str(e), "pool_available": False}

@app.post("/api/v1/phone-pool/cleanup")
async def cleanup_phone_pool():
    """Manually trigger phone pool cooldown cleanup"""
    try:
        from utils.twilio_pool import cleanup_cooldown
        cleanup_cooldown()
        return {"status": "success", "message": "Phone pool cleanup completed"}
    except Exception as e:
        logger.error(f"Failed to cleanup phone pool: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    
    # Configure logging level
    log_level = settings.log_level.lower()
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        log_level=log_level,
        log_config=None,  # Use structlog instead
        access_log=False,
        workers=1,  # Single worker for development, scale with env var
        reload=False
    )