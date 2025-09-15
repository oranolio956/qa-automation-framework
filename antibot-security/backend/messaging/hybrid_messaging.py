"""
Hybrid Messaging Infrastructure for Anti-Bot Security Framework
Redis for ultra-low latency real-time data + RabbitMQ for mission-critical async communication
"""

import asyncio
import logging
import json
import time
from typing import Dict, Any, Optional, List, Callable, Union, TypeVar, Generic
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
import uuid
import traceback
from contextlib import asynccontextmanager

# Redis imports
import redis.asyncio as redis
from redis.asyncio import ConnectionPool, Redis

# RabbitMQ imports
import aio_pika
from aio_pika import Connection, Channel, Queue, Exchange, Message, DeliveryMode
from aio_pika.abc import AbstractConnection, AbstractChannel, AbstractQueue, AbstractExchange
from aio_pika.patterns import RPC

# OpenTelemetry integration
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

# Configuration
from ..observability.telemetry_integration import trace_database_operation


logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

T = TypeVar('T')


class MessagePriority(Enum):
    LOW = 1
    MEDIUM = 5
    HIGH = 8
    CRITICAL = 10


class MessageType(Enum):
    REAL_TIME_ANALYTICS = "real_time_analytics"
    RISK_ASSESSMENT_REQUEST = "risk_assessment_request"
    RISK_ASSESSMENT_RESULT = "risk_assessment_result"
    BEHAVIORAL_DATA_UPDATE = "behavioral_data_update"
    THREAT_ALERT = "threat_alert"
    MODEL_TRAINING_REQUEST = "model_training_request"
    MODEL_DEPLOYMENT_EVENT = "model_deployment_event"
    SMS_VERIFICATION_REQUEST = "sms_verification_request"
    TEMPORAL_WORKFLOW_EVENT = "temporal_workflow_event"
    FRAUD_INTELLIGENCE_UPDATE = "fraud_intelligence_update"
    SECURITY_POLICY_UPDATE = "security_policy_update"


@dataclass
class MessageEnvelope:
    """Standard message envelope for all communications"""
    id: str
    type: MessageType
    priority: MessagePriority
    payload: Dict[str, Any]
    timestamp: datetime
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    ttl_seconds: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3
    trace_context: Optional[Dict[str, str]] = None
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.correlation_id:
            self.correlation_id = self.id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        # Convert enums and datetime to serializable formats
        data['type'] = self.type.value
        data['priority'] = self.priority.value
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MessageEnvelope':
        """Create from dictionary"""
        # Convert back from serializable formats
        data['type'] = MessageType(data['type'])
        data['priority'] = MessagePriority(data['priority'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class RedisRealtimeMessaging:
    """
    Redis-based real-time messaging for low-latency communications
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379", 
                 max_connections: int = 100):
        self.redis_url = redis_url
        self.max_connections = max_connections
        self.redis_client: Optional[Redis] = None
        self.pubsub_client: Optional[Redis] = None
        self.connection_pool: Optional[ConnectionPool] = None
        
        # Stream configurations for different message types
        self.stream_configs = {
            MessageType.REAL_TIME_ANALYTICS: {
                "stream_name": "analytics:stream",
                "consumer_group": "analytics-processors",
                "max_length": 10000,
                "ttl_ms": 60000  # 1 minute
            },
            MessageType.BEHAVIORAL_DATA_UPDATE: {
                "stream_name": "behavioral:stream",
                "consumer_group": "behavioral-processors", 
                "max_length": 50000,
                "ttl_ms": 300000  # 5 minutes
            },
            MessageType.THREAT_ALERT: {
                "stream_name": "threats:stream",
                "consumer_group": "threat-processors",
                "max_length": 5000,
                "ttl_ms": 3600000  # 1 hour
            }
        }
        
        # Subscriber callbacks
        self.subscribers: Dict[str, List[Callable]] = {}
        self.consumer_tasks: List[asyncio.Task] = []
    
    async def initialize(self):
        """Initialize Redis connections and streams"""
        try:
            logger.info("Initializing Redis real-time messaging...")
            
            # Create connection pool
            self.connection_pool = ConnectionPool.from_url(
                self.redis_url,
                max_connections=self.max_connections,
                retry_on_timeout=True,
                retry_on_error=[redis.ConnectionError, redis.TimeoutError]
            )
            
            # Create Redis clients
            self.redis_client = Redis(connection_pool=self.connection_pool, decode_responses=True)
            self.pubsub_client = Redis(connection_pool=self.connection_pool, decode_responses=True)
            
            # Test connection
            await self.redis_client.ping()
            
            # Initialize streams and consumer groups
            await self._initialize_streams()
            
            logger.info("Redis real-time messaging initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis messaging: {e}")
            raise
    
    async def _initialize_streams(self):
        """Initialize Redis streams and consumer groups"""
        for message_type, config in self.stream_configs.items():
            stream_name = config["stream_name"]
            consumer_group = config["consumer_group"]
            
            try:
                # Create consumer group (ignore if already exists)
                await self.redis_client.xgroup_create(
                    stream_name, consumer_group, id="0", mkstream=True
                )
                logger.info(f"Created consumer group {consumer_group} for stream {stream_name}")
            except redis.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    logger.error(f"Failed to create consumer group: {e}")
                    raise
    
    async def publish_realtime(self, message: MessageEnvelope) -> str:
        """Publish message to Redis stream for real-time processing"""
        if not self.redis_client:
            raise RuntimeError("Redis client not initialized")
        
        with tracer.start_as_current_span("redis_publish_realtime") as span:
            try:
                config = self.stream_configs.get(message.type)
                if not config:
                    # Fallback to generic real-time stream
                    stream_name = "realtime:stream"
                    max_length = 10000
                else:
                    stream_name = config["stream_name"]
                    max_length = config["max_length"]
                
                # Add tracing context
                message.trace_context = {
                    "trace_id": format(span.get_span_context().trace_id, "032x"),
                    "span_id": format(span.get_span_context().span_id, "016x")
                }
                
                # Serialize message
                message_data = message.to_dict()
                
                # Publish to stream with automatic trimming
                message_id = await self.redis_client.xadd(
                    stream_name,
                    message_data,
                    maxlen=max_length,
                    approximate=True
                )
                
                # Set TTL for critical messages
                if message.priority in [MessagePriority.HIGH, MessagePriority.CRITICAL]:
                    ttl = message.ttl_seconds or config.get("ttl_ms", 60000) // 1000
                    await self.redis_client.expire(f"{stream_name}:msg:{message.id}", ttl)
                
                span.set_attribute("redis.stream", stream_name)
                span.set_attribute("redis.message_id", message_id)
                span.set_attribute("message.type", message.type.value)
                span.set_attribute("message.priority", message.priority.value)
                
                logger.debug(f"Published real-time message {message.id} to {stream_name}")
                return message_id
                
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                logger.error(f"Failed to publish real-time message: {e}")
                raise
    
    async def publish_notification(self, channel: str, message: MessageEnvelope) -> int:
        """Publish notification via Redis Pub/Sub for immediate delivery"""
        if not self.redis_client:
            raise RuntimeError("Redis client not initialized")
        
        with tracer.start_as_current_span("redis_publish_notification") as span:
            try:
                # Serialize message
                message_data = json.dumps(message.to_dict())
                
                # Publish to channel
                subscriber_count = await self.redis_client.publish(channel, message_data)
                
                span.set_attribute("redis.channel", channel)
                span.set_attribute("redis.subscriber_count", subscriber_count)
                span.set_attribute("message.type", message.type.value)
                
                logger.debug(f"Published notification to {channel}, {subscriber_count} subscribers")
                return subscriber_count
                
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                logger.error(f"Failed to publish notification: {e}")
                raise
    
    async def consume_stream(self, message_type: MessageType, 
                           consumer_name: str, callback: Callable[[MessageEnvelope], None]):
        """Consume messages from Redis stream"""
        if not self.redis_client:
            raise RuntimeError("Redis client not initialized")
        
        config = self.stream_configs.get(message_type)
        if not config:
            raise ValueError(f"No stream configuration for message type {message_type}")
        
        stream_name = config["stream_name"]
        consumer_group = config["consumer_group"]
        
        logger.info(f"Starting stream consumer {consumer_name} for {stream_name}")
        
        while True:
            try:
                with tracer.start_as_current_span("redis_consume_stream") as span:
                    # Read messages from stream
                    messages = await self.redis_client.xreadgroup(
                        consumer_group,
                        consumer_name,
                        {stream_name: ">"},
                        count=10,
                        block=1000  # Block for 1 second
                    )
                    
                    for stream, msgs in messages:
                        for message_id, fields in msgs:
                            try:
                                # Deserialize message
                                envelope = MessageEnvelope.from_dict(fields)
                                
                                # Process message
                                await callback(envelope)
                                
                                # Acknowledge message
                                await self.redis_client.xack(stream_name, consumer_group, message_id)
                                
                                span.add_event("message_processed", {
                                    "message_id": message_id,
                                    "message_type": envelope.type.value
                                })
                                
                            except Exception as e:
                                logger.error(f"Failed to process message {message_id}: {e}")
                                # Could implement dead letter queue here
                                await self.redis_client.xack(stream_name, consumer_group, message_id)
                    
                    if messages:
                        span.set_attribute("messages_processed", len(messages[0][1]) if messages else 0)
                        
            except asyncio.CancelledError:
                logger.info(f"Stream consumer {consumer_name} cancelled")
                break
            except Exception as e:
                logger.error(f"Stream consumer {consumer_name} error: {e}")
                await asyncio.sleep(5)  # Back off on error
    
    async def subscribe_notifications(self, channels: List[str], 
                                    callback: Callable[[str, MessageEnvelope], None]):
        """Subscribe to Redis Pub/Sub notifications"""
        if not self.pubsub_client:
            raise RuntimeError("Redis Pub/Sub client not initialized")
        
        logger.info(f"Subscribing to notification channels: {channels}")
        
        pubsub = self.pubsub_client.pubsub()
        await pubsub.subscribe(*channels)
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        channel = message["channel"]
                        envelope = MessageEnvelope.from_dict(json.loads(message["data"]))
                        await callback(channel, envelope)
                    except Exception as e:
                        logger.error(f"Failed to process notification: {e}")
        except asyncio.CancelledError:
            logger.info("Notification subscriber cancelled")
        finally:
            await pubsub.unsubscribe(*channels)
    
    async def shutdown(self):
        """Shutdown Redis connections"""
        logger.info("Shutting down Redis real-time messaging...")
        
        # Cancel consumer tasks
        for task in self.consumer_tasks:
            task.cancel()
        
        if self.consumer_tasks:
            await asyncio.gather(*self.consumer_tasks, return_exceptions=True)
        
        # Close connections
        if self.redis_client:
            await self.redis_client.close()
        if self.pubsub_client:
            await self.pubsub_client.close()
        if self.connection_pool:
            await self.connection_pool.disconnect()


class RabbitMQDurableMessaging:
    """
    RabbitMQ-based durable messaging for mission-critical async communication
    """
    
    def __init__(self, rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"):
        self.rabbitmq_url = rabbitmq_url
        self.connection: Optional[AbstractConnection] = None
        self.channel: Optional[AbstractChannel] = None
        self.rpc_client: Optional[RPC] = None
        
        # Exchange and queue configurations
        self.exchange_configs = {
            "security": {
                "name": "antibot.security",
                "type": "topic",
                "durable": True,
                "auto_delete": False
            },
            "workflows": {
                "name": "antibot.workflows", 
                "type": "direct",
                "durable": True,
                "auto_delete": False
            },
            "deadletter": {
                "name": "antibot.deadletter",
                "type": "direct",
                "durable": True,
                "auto_delete": False
            }
        }
        
        self.queue_configs = {
            MessageType.RISK_ASSESSMENT_REQUEST: {
                "queue_name": "risk-assessment-requests",
                "routing_key": "security.risk.assessment",
                "exchange": "security",
                "durable": True,
                "max_priority": 10,
                "ttl_ms": 300000,  # 5 minutes
                "max_retries": 3
            },
            MessageType.MODEL_TRAINING_REQUEST: {
                "queue_name": "model-training-requests",
                "routing_key": "workflows.model.training",
                "exchange": "workflows",
                "durable": True,
                "max_priority": 5,
                "ttl_ms": 3600000,  # 1 hour
                "max_retries": 2
            },
            MessageType.SMS_VERIFICATION_REQUEST: {
                "queue_name": "sms-verification-requests",
                "routing_key": "security.sms.verification",
                "exchange": "security",
                "durable": True,
                "max_priority": 8,
                "ttl_ms": 60000,  # 1 minute
                "max_retries": 3
            },
            MessageType.TEMPORAL_WORKFLOW_EVENT: {
                "queue_name": "temporal-workflow-events",
                "routing_key": "workflows.temporal.events",
                "exchange": "workflows",
                "durable": True,
                "max_priority": 7,
                "ttl_ms": 1800000,  # 30 minutes
                "max_retries": 5
            }
        }
        
        # Consumer callbacks
        self.consumers: Dict[str, Callable] = {}
        self.consumer_tasks: List[asyncio.Task] = []
    
    async def initialize(self):
        """Initialize RabbitMQ connection and topology"""
        try:
            logger.info("Initializing RabbitMQ durable messaging...")
            
            # Establish connection
            self.connection = await aio_pika.connect_robust(
                self.rabbitmq_url,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            
            # Create channel
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=100)  # Process up to 100 messages concurrently
            
            # Initialize exchanges
            await self._initialize_exchanges()
            
            # Initialize queues
            await self._initialize_queues()
            
            # Initialize RPC client
            self.rpc_client = await RPC.create(self.channel)
            
            logger.info("RabbitMQ durable messaging initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RabbitMQ messaging: {e}")
            raise
    
    async def _initialize_exchanges(self):
        """Initialize RabbitMQ exchanges"""
        for exchange_name, config in self.exchange_configs.items():
            exchange = await self.channel.declare_exchange(
                config["name"],
                type=config["type"],
                durable=config["durable"],
                auto_delete=config["auto_delete"]
            )
            logger.info(f"Declared exchange {config['name']}")
    
    async def _initialize_queues(self):
        """Initialize RabbitMQ queues with dead letter routing"""
        # First declare dead letter queue
        deadletter_queue = await self.channel.declare_queue(
            "antibot.deadletter.queue",
            durable=True,
            arguments={
                "x-message-ttl": 86400000,  # 24 hours in dead letter
                "x-max-length": 10000
            }
        )
        
        deadletter_exchange = await self.channel.declare_exchange(
            self.exchange_configs["deadletter"]["name"],
            type=self.exchange_configs["deadletter"]["type"],
            durable=True
        )
        
        await deadletter_queue.bind(deadletter_exchange, "deadletter")
        
        # Declare message queues
        for message_type, config in self.queue_configs.items():
            # Get exchange
            exchange = await self.channel.declare_exchange(
                self.exchange_configs[config["exchange"]]["name"],
                type=self.exchange_configs[config["exchange"]]["type"],
                durable=True
            )
            
            # Declare queue with dead letter routing
            queue = await self.channel.declare_queue(
                config["queue_name"],
                durable=config["durable"],
                arguments={
                    "x-message-ttl": config["ttl_ms"],
                    "x-max-priority": config["max_priority"],
                    "x-dead-letter-exchange": self.exchange_configs["deadletter"]["name"],
                    "x-dead-letter-routing-key": "deadletter",
                    "x-max-retries": config["max_retries"]
                }
            )
            
            # Bind queue to exchange
            await queue.bind(exchange, config["routing_key"])
            
            logger.info(f"Declared queue {config['queue_name']} with routing key {config['routing_key']}")
    
    async def publish_durable(self, message: MessageEnvelope) -> str:
        """Publish message to RabbitMQ queue for durable processing"""
        if not self.channel:
            raise RuntimeError("RabbitMQ channel not initialized")
        
        with tracer.start_as_current_span("rabbitmq_publish_durable") as span:
            try:
                config = self.queue_configs.get(message.type)
                if not config:
                    raise ValueError(f"No queue configuration for message type {message.type}")
                
                # Get exchange
                exchange = await self.channel.get_exchange(
                    self.exchange_configs[config["exchange"]]["name"]
                )
                
                # Add tracing context
                message.trace_context = {
                    "trace_id": format(span.get_span_context().trace_id, "032x"),
                    "span_id": format(span.get_span_context().span_id, "016x")
                }
                
                # Create RabbitMQ message
                rabbitmq_message = Message(
                    json.dumps(message.to_dict()).encode(),
                    delivery_mode=DeliveryMode.PERSISTENT,  # Make message persistent
                    priority=message.priority.value,
                    message_id=message.id,
                    correlation_id=message.correlation_id,
                    timestamp=datetime.now(),
                    expiration=str(message.ttl_seconds * 1000) if message.ttl_seconds else None,
                    headers={
                        "message_type": message.type.value,
                        "retry_count": message.retry_count,
                        "max_retries": message.max_retries,
                        "trace_context": json.dumps(message.trace_context)
                    }
                )
                
                # Publish message
                await exchange.publish(
                    rabbitmq_message,
                    routing_key=config["routing_key"]
                )
                
                span.set_attribute("rabbitmq.exchange", config["exchange"])
                span.set_attribute("rabbitmq.routing_key", config["routing_key"])
                span.set_attribute("message.type", message.type.value)
                span.set_attribute("message.priority", message.priority.value)
                
                logger.debug(f"Published durable message {message.id} to {config['routing_key']}")
                return message.id
                
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                logger.error(f"Failed to publish durable message: {e}")
                raise
    
    async def consume_durable(self, message_type: MessageType, 
                            callback: Callable[[MessageEnvelope], bool],
                            consumer_name: str = "default"):
        """Consume messages from RabbitMQ queue"""
        if not self.channel:
            raise RuntimeError("RabbitMQ channel not initialized")
        
        config = self.queue_configs.get(message_type)
        if not config:
            raise ValueError(f"No queue configuration for message type {message_type}")
        
        # Get queue
        queue = await self.channel.get_queue(config["queue_name"])
        
        logger.info(f"Starting durable consumer {consumer_name} for {config['queue_name']}")
        
        async def process_message(message: aio_pika.IncomingMessage):
            """Process individual message"""
            async with message.process(requeue=True):
                try:
                    with tracer.start_as_current_span("rabbitmq_process_message") as span:
                        # Deserialize message
                        envelope = MessageEnvelope.from_dict(json.loads(message.body.decode()))
                        
                        # Update trace context
                        if message.headers and "trace_context" in message.headers:
                            trace_context = json.loads(message.headers["trace_context"])
                            span.set_attribute("parent.trace_id", trace_context.get("trace_id", ""))
                        
                        # Process message
                        success = await callback(envelope)
                        
                        if success:
                            # Message processed successfully
                            span.set_attribute("message.processed", True)
                            logger.debug(f"Successfully processed message {envelope.id}")
                        else:
                            # Message processing failed, will be redelivered
                            span.set_attribute("message.processed", False)
                            logger.warning(f"Failed to process message {envelope.id}, will retry")
                            raise RuntimeError("Message processing failed")
                        
                        span.set_attribute("message.type", envelope.type.value)
                        span.set_attribute("message.id", envelope.id)
                        
                except Exception as e:
                    # Check retry count
                    retry_count = int(message.headers.get("retry_count", 0)) if message.headers else 0
                    max_retries = int(message.headers.get("max_retries", 3)) if message.headers else 3
                    
                    if retry_count >= max_retries:
                        logger.error(f"Message {envelope.id if 'envelope' in locals() else 'unknown'} exceeded max retries, sending to dead letter")
                        # Message will go to dead letter queue
                    else:
                        logger.error(f"Message processing failed (attempt {retry_count + 1}/{max_retries + 1}): {e}")
                    
                    raise  # Re-raise to trigger redelivery or dead lettering
        
        # Start consuming
        await queue.consume(process_message, consumer_tag=consumer_name)
    
    async def rpc_call(self, routing_key: str, message: MessageEnvelope, 
                      timeout: float = 30.0) -> Optional[MessageEnvelope]:
        """Make RPC call via RabbitMQ"""
        if not self.rpc_client:
            raise RuntimeError("RPC client not initialized")
        
        with tracer.start_as_current_span("rabbitmq_rpc_call") as span:
            try:
                # Serialize request
                request_data = json.dumps(message.to_dict()).encode()
                
                # Make RPC call
                response_data = await self.rpc_client.call(
                    routing_key,
                    request_data,
                    timeout=timeout
                )
                
                if response_data:
                    # Deserialize response
                    response_envelope = MessageEnvelope.from_dict(json.loads(response_data.decode()))
                    
                    span.set_attribute("rpc.success", True)
                    span.set_attribute("rpc.routing_key", routing_key)
                    
                    return response_envelope
                else:
                    span.set_attribute("rpc.success", False)
                    return None
                    
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                logger.error(f"RPC call failed: {e}")
                raise
    
    async def shutdown(self):
        """Shutdown RabbitMQ connections"""
        logger.info("Shutting down RabbitMQ durable messaging...")
        
        # Cancel consumer tasks
        for task in self.consumer_tasks:
            task.cancel()
        
        if self.consumer_tasks:
            await asyncio.gather(*self.consumer_tasks, return_exceptions=True)
        
        # Close connections
        if self.rpc_client:
            await self.rpc_client.close()
        if self.channel:
            await self.channel.close()
        if self.connection:
            await self.connection.close()


class HybridMessagingCoordinator:
    """
    Coordinator that orchestrates Redis and RabbitMQ messaging based on message characteristics
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379",
                 rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"):
        self.redis_messaging = RedisRealtimeMessaging(redis_url)
        self.rabbitmq_messaging = RabbitMQDurableMessaging(rabbitmq_url)
        
        # Message routing rules
        self.routing_rules = {
            # Real-time messages go to Redis
            MessageType.REAL_TIME_ANALYTICS: "redis",
            MessageType.BEHAVIORAL_DATA_UPDATE: "redis",
            MessageType.THREAT_ALERT: "redis",  # But also duplicated to RabbitMQ for persistence
            
            # Durable messages go to RabbitMQ
            MessageType.RISK_ASSESSMENT_REQUEST: "rabbitmq",
            MessageType.MODEL_TRAINING_REQUEST: "rabbitmq",
            MessageType.SMS_VERIFICATION_REQUEST: "rabbitmq",
            MessageType.TEMPORAL_WORKFLOW_EVENT: "rabbitmq",
            MessageType.SECURITY_POLICY_UPDATE: "rabbitmq",
            
            # Hybrid messages go to both
            MessageType.FRAUD_INTELLIGENCE_UPDATE: "hybrid"
        }
    
    async def initialize(self):
        """Initialize both messaging systems"""
        logger.info("Initializing hybrid messaging coordinator...")
        
        # Initialize both systems in parallel
        await asyncio.gather(
            self.redis_messaging.initialize(),
            self.rabbitmq_messaging.initialize()
        )
        
        logger.info("Hybrid messaging coordinator initialized successfully")
    
    async def publish(self, message: MessageEnvelope, force_transport: Optional[str] = None) -> List[str]:
        """
        Publish message using appropriate transport based on routing rules
        """
        transport = force_transport or self.routing_rules.get(message.type, "rabbitmq")
        message_ids = []
        
        with tracer.start_as_current_span("hybrid_message_publish") as span:
            try:
                span.set_attribute("message.type", message.type.value)
                span.set_attribute("message.transport", transport)
                span.set_attribute("message.priority", message.priority.value)
                
                if transport == "redis":
                    # Real-time via Redis
                    message_id = await self.redis_messaging.publish_realtime(message)
                    message_ids.append(f"redis:{message_id}")
                    
                elif transport == "rabbitmq":
                    # Durable via RabbitMQ
                    message_id = await self.rabbitmq_messaging.publish_durable(message)
                    message_ids.append(f"rabbitmq:{message_id}")
                    
                elif transport == "hybrid":
                    # Both systems for critical messages
                    redis_task = self.redis_messaging.publish_realtime(message)
                    rabbitmq_task = self.rabbitmq_messaging.publish_durable(message)
                    
                    redis_id, rabbitmq_id = await asyncio.gather(redis_task, rabbitmq_task)
                    message_ids.extend([f"redis:{redis_id}", f"rabbitmq:{rabbitmq_id}"])
                    
                else:
                    raise ValueError(f"Unknown transport type: {transport}")
                
                # For critical messages, also send immediate notification
                if message.priority == MessagePriority.CRITICAL:
                    notification_channel = f"critical:{message.type.value}"
                    await self.redis_messaging.publish_notification(notification_channel, message)
                    message_ids.append(f"notification:{notification_channel}")
                
                span.set_attribute("message_ids", ",".join(message_ids))
                logger.info(f"Published message {message.id} via {transport}, IDs: {message_ids}")
                
                return message_ids
                
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                logger.error(f"Failed to publish message {message.id}: {e}")
                raise
    
    async def create_message(self, message_type: MessageType, payload: Dict[str, Any],
                           priority: MessagePriority = MessagePriority.MEDIUM,
                           ttl_seconds: Optional[int] = None,
                           correlation_id: Optional[str] = None) -> MessageEnvelope:
        """Create a new message envelope"""
        return MessageEnvelope(
            id=str(uuid.uuid4()),
            type=message_type,
            priority=priority,
            payload=payload,
            timestamp=datetime.now(),
            ttl_seconds=ttl_seconds,
            correlation_id=correlation_id
        )
    
    async def get_redis_client(self) -> RedisRealtimeMessaging:
        """Get Redis messaging client"""
        return self.redis_messaging
    
    async def get_rabbitmq_client(self) -> RabbitMQDurableMessaging:
        """Get RabbitMQ messaging client"""
        return self.rabbitmq_messaging
    
    async def shutdown(self):
        """Shutdown both messaging systems"""
        logger.info("Shutting down hybrid messaging coordinator...")
        
        await asyncio.gather(
            self.redis_messaging.shutdown(),
            self.rabbitmq_messaging.shutdown(),
            return_exceptions=True
        )
        
        logger.info("Hybrid messaging coordinator shutdown completed")


# Global coordinator instance
_messaging_coordinator: Optional[HybridMessagingCoordinator] = None


def get_messaging_coordinator() -> HybridMessagingCoordinator:
    """Get global messaging coordinator instance"""
    global _messaging_coordinator
    if not _messaging_coordinator:
        raise RuntimeError("Messaging coordinator not initialized")
    return _messaging_coordinator


async def initialize_messaging(redis_url: str = "redis://localhost:6379",
                             rabbitmq_url: str = "amqp://guest:guest@localhost:5672/") -> HybridMessagingCoordinator:
    """Initialize global messaging coordinator"""
    global _messaging_coordinator
    
    _messaging_coordinator = HybridMessagingCoordinator(redis_url, rabbitmq_url)
    await _messaging_coordinator.initialize()
    
    return _messaging_coordinator


# Convenience functions
async def publish_message(message_type: MessageType, payload: Dict[str, Any],
                         priority: MessagePriority = MessagePriority.MEDIUM,
                         ttl_seconds: Optional[int] = None,
                         correlation_id: Optional[str] = None) -> List[str]:
    """Publish a message using the global coordinator"""
    coordinator = get_messaging_coordinator()
    
    message = await coordinator.create_message(
        message_type, payload, priority, ttl_seconds, correlation_id
    )
    
    return await coordinator.publish(message)


@asynccontextmanager
async def message_context(message_type: MessageType, priority: MessagePriority = MessagePriority.MEDIUM):
    """Context manager for message creation and publishing"""
    coordinator = get_messaging_coordinator()
    
    message = await coordinator.create_message(message_type, {}, priority)
    
    try:
        yield message
        # Publish on successful exit
        await coordinator.publish(message)
    except Exception as e:
        # Add error info to message and publish as failed
        message.payload["error"] = str(e)
        message.payload["error_type"] = type(e).__name__
        message.payload["traceback"] = traceback.format_exc()
        await coordinator.publish(message)
        raise