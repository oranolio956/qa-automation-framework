#!/usr/bin/env python3
"""
SMS Worker for Queue Processing
Processes SMS messages from RabbitMQ queues with fault tolerance and monitoring
"""

import os
import json
import time
import signal
import sys
import logging
from datetime import datetime
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor
import threading

import pika
import redis
import structlog
from prometheus_client import Counter, Histogram, Gauge, push_to_gateway
from tenacity import retry, stop_after_attempt, wait_exponential

# Import SMS providers
from main import TwilioProvider, AWSSNSProvider, SMSProvider, CircuitBreaker

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
MESSAGES_PROCESSED = Counter('sms_worker_messages_processed_total', 'Total messages processed', ['status', 'provider'])
PROCESSING_DURATION = Histogram('sms_worker_processing_duration_seconds', 'Message processing duration', ['provider'])
QUEUE_LAG = Gauge('sms_worker_queue_lag_seconds', 'Queue processing lag')
WORKER_STATUS = Gauge('sms_worker_status', 'Worker status (1=running, 0=stopped)')
CIRCUIT_BREAKER_FAILURES = Counter('sms_worker_circuit_breaker_failures_total', 'Circuit breaker failures', ['provider'])

class SMSWorker:
    """SMS Worker for processing queued messages"""
    
    def __init__(self):
        self.redis_client = None
        self.rabbit_connection = None
        self.rabbit_channel = None
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # SMS providers with circuit breakers
        self.providers = {
            SMSProvider.TWILIO: TwilioProvider(),
            SMSProvider.AWS_SNS: AWSSNSProvider()
        }
        
        self.circuit_breakers = {
            provider: CircuitBreaker(
                failure_threshold=int(os.getenv('CIRCUIT_BREAKER_THRESHOLD', '5')),
                timeout_duration=int(os.getenv('CIRCUIT_BREAKER_TIMEOUT', '30'))
            ) for provider in self.providers.keys()
        }
        
        # Configuration
        self.worker_concurrency = int(os.getenv('WORKER_CONCURRENCY', '4'))
        self.worker_prefetch = int(os.getenv('WORKER_PREFETCH', '10'))
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        self.rabbitmq_url = os.getenv('RABBITMQ_URL', 'amqp://admin:changeme@localhost:5672/')
        self.prometheus_gateway = os.getenv('PROMETHEUS_PUSHGATEWAY_URL')
        
        # Signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown")
        self.running = False
    
    def initialize(self):
        """Initialize Redis and RabbitMQ connections"""
        try:
            # Redis connection
            self.redis_client = redis.from_url(
                self.redis_url, 
                decode_responses=True,
                socket_keepalive=True,
                socket_keepalive_options={1: 1, 2: 3, 3: 5},
                retry_on_timeout=True
            )
            self.redis_client.ping()
            logger.info("Worker connected to Redis", redis_url=self.redis_url)
            
            # RabbitMQ connection
            connection_params = pika.URLParameters(self.rabbitmq_url)
            connection_params.heartbeat = 600
            connection_params.blocked_connection_timeout = 300
            
            self.rabbit_connection = pika.BlockingConnection(connection_params)
            self.rabbit_channel = self.rabbit_connection.channel()
            
            # Configure QoS
            self.rabbit_channel.basic_qos(
                prefetch_count=self.worker_prefetch, 
                global_qos=True
            )
            
            logger.info("Worker connected to RabbitMQ", 
                       rabbitmq_url=self.rabbitmq_url.split('@')[0] + '@***')
            
        except Exception as e:
            logger.error("Failed to initialize worker connections", error=str(e))
            raise
    
    def select_provider(self) -> SMSProvider:
        """Select the best available SMS provider based on circuit breaker status"""
        for provider in [SMSProvider.TWILIO, SMSProvider.AWS_SNS]:
            circuit_breaker = self.circuit_breakers[provider]
            if circuit_breaker.state.value != 'open':
                return provider
        
        # All circuit breakers are open, try the first one anyway
        logger.warning("All SMS providers have open circuit breakers, trying Twilio as fallback")
        return SMSProvider.TWILIO
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def send_sms_with_provider(self, provider: SMSProvider, phone_number: str, message: str, metadata: Dict) -> Dict:
        """Send SMS with specific provider and circuit breaker protection"""
        circuit_breaker = self.circuit_breakers[provider]
        provider_instance = self.providers[provider]
        
        try:
            # This is a synchronous call in the worker thread
            if provider == SMSProvider.TWILIO:
                # Direct Twilio SDK call
                if not provider_instance.client:
                    raise Exception("Twilio client not initialized")
                
                from_number = metadata.get('from_phone_number', provider_instance.phone_number)
                if not from_number:
                    # Try to get from phone pool
                    try:
                        from utils.twilio_pool import get_number
                        from_number = get_number()
                        if not from_number:
                            raise Exception("No Twilio phone number available")
                    except Exception:
                        raise Exception("No Twilio phone number available")
                
                message_instance = provider_instance.client.messages.create(
                    body=message,
                    from_=from_number,
                    to=phone_number
                )
                
                return {
                    'message_id': message_instance.sid,
                    'status': message_instance.status,
                    'provider': 'twilio',
                    'cost': float(message_instance.price) if message_instance.price else None,
                    'from_number': from_number
                }
                
            elif provider == SMSProvider.AWS_SNS:
                # Direct AWS SNS call
                if not provider_instance.sns_client:
                    raise Exception("AWS SNS client not initialized")
                
                response = provider_instance.sns_client.publish(
                    PhoneNumber=phone_number,
                    Message=message
                )
                
                return {
                    'message_id': response['MessageId'],
                    'status': 'sent',
                    'provider': 'aws_sns',
                    'cost': 0.00645,
                    'response_metadata': response.get('ResponseMetadata', {})
                }
            
            else:
                raise Exception(f"Unknown provider: {provider}")
                
        except Exception as e:
            circuit_breaker.record_failure()
            CIRCUIT_BREAKER_FAILURES.labels(provider=provider.value).inc()
            raise e
    
    def process_message(self, channel, method, properties, body):
        """Process a single SMS message from the queue"""
        start_time = time.time()
        
        try:
            # Parse message
            message_data = json.loads(body.decode('utf-8'))
            phone_number = message_data['phone_number']
            message_text = message_data['message']
            priority = message_data.get('priority', 1)
            metadata = message_data.get('metadata', {})
            queued_at = message_data.get('queued_at')
            retry_count = message_data.get('retry_count', 0)
            max_retries = message_data.get('max_retries', 3)
            
            # Calculate queue lag
            if queued_at:
                queued_time = datetime.fromisoformat(queued_at)
                queue_lag = (datetime.now() - queued_time).total_seconds()
                QUEUE_LAG.set(queue_lag)
            
            logger.info("Processing SMS message", 
                       phone=phone_number[:5] + "***",
                       priority=priority,
                       retry_count=retry_count)
            
            # Select provider
            provider = self.select_provider()
            
            # Send SMS
            result = self.send_sms_with_provider(provider, phone_number, message_text, metadata)
            
            # Store result in Redis for status tracking
            if self.redis_client:
                try:
                    message_record = {
                        'message_id': result['message_id'],
                        'phone_number': phone_number,
                        'provider': provider.value,
                        'status': result['status'],
                        'sent_at': datetime.now().isoformat(),
                        'metadata': json.dumps(metadata),
                        'cost': result.get('cost', 0),
                        'processed_by': 'worker'
                    }
                    
                    self.redis_client.hset(
                        f"sms:{result['message_id']}", 
                        mapping=message_record
                    )
                    self.redis_client.expire(f"sms:{result['message_id']}", 86400 * 7)  # 7 days
                    
                except Exception as e:
                    logger.warning(f"Failed to store SMS result in Redis: {e}")
            
            # Record metrics
            processing_time = time.time() - start_time
            PROCESSING_DURATION.labels(provider=provider.value).observe(processing_time)
            MESSAGES_PROCESSED.labels(status='success', provider=provider.value).inc()
            
            # Acknowledge message
            channel.basic_ack(delivery_tag=method.delivery_tag)
            
            logger.info("SMS processed successfully",
                       message_id=result['message_id'],
                       provider=provider.value,
                       processing_time=processing_time,
                       phone=phone_number[:5] + "***")
            
        except Exception as e:
            logger.error("Failed to process SMS message", error=str(e))
            
            # Record failure metrics
            MESSAGES_PROCESSED.labels(status='failed', provider='unknown').inc()
            
            # Handle retry logic
            try:
                message_data = json.loads(body.decode('utf-8'))
                retry_count = message_data.get('retry_count', 0)
                max_retries = message_data.get('max_retries', 3)
                
                if retry_count < max_retries:
                    # Requeue with incremented retry count
                    message_data['retry_count'] = retry_count + 1
                    message_data['last_error'] = str(e)
                    message_data['retry_at'] = datetime.now().isoformat()
                    
                    # Publish to retry queue with delay
                    channel.basic_publish(
                        exchange='sms_exchange',
                        routing_key='retry',
                        body=json.dumps(message_data),
                        properties=pika.BasicProperties(
                            delivery_mode=2,
                            priority=1,  # Lower priority for retries
                            headers={'retry_count': retry_count + 1}
                        )
                    )
                    
                    logger.info(f"Message requeued for retry {retry_count + 1}/{max_retries}")
                    
                else:
                    # Send to dead letter queue
                    logger.error(f"Message exceeded max retries ({max_retries}), sending to DLQ")
                
                # Acknowledge original message in any case
                channel.basic_ack(delivery_tag=method.delivery_tag)
                
            except Exception as retry_error:
                logger.error(f"Failed to handle retry logic: {retry_error}")
                # Reject message without requeue (sends to DLQ if configured)
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    def start_consuming(self):
        """Start consuming messages from priority queues"""
        logger.info("Starting SMS worker", 
                   concurrency=self.worker_concurrency,
                   prefetch=self.worker_prefetch)
        
        self.running = True
        WORKER_STATUS.set(1)
        
        try:
            # Set up consumers for priority queues
            for priority in range(1, 6):  # Priority 1-5
                queue_name = f'sms_queue_p{priority}'
                
                # Start consuming from each priority queue
                self.rabbit_channel.basic_consume(
                    queue=queue_name,
                    on_message_callback=self.process_message,
                    auto_ack=False  # Manual acknowledgment for reliability
                )
            
            logger.info("SMS worker started, waiting for messages")
            
            # Start consuming
            while self.running:
                try:
                    self.rabbit_connection.process_data_events(time_limit=1.0)
                    
                    # Push metrics periodically
                    if self.prometheus_gateway and time.time() % 30 < 1:  # Every 30 seconds
                        try:
                            push_to_gateway(
                                self.prometheus_gateway, 
                                job='sms-worker',
                                registry=None
                            )
                        except Exception as e:
                            logger.warning(f"Failed to push metrics: {e}")
                            
                except Exception as e:
                    if self.running:  # Only log if we're supposed to be running
                        logger.error(f"Error in message processing loop: {e}")
                        time.sleep(1)  # Brief pause before retrying
        
        except Exception as e:
            logger.error(f"Fatal error in worker: {e}")
            raise
        
        finally:
            WORKER_STATUS.set(0)
            logger.info("SMS worker stopped")
    
    def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down SMS worker")
        
        self.running = False
        
        # Close RabbitMQ connection
        if self.rabbit_channel and not self.rabbit_channel.is_closed:
            self.rabbit_channel.stop_consuming()
            self.rabbit_channel.close()
        
        if self.rabbit_connection and not self.rabbit_connection.is_closed:
            self.rabbit_connection.close()
        
        # Close Redis connection
        if self.redis_client:
            self.redis_client.close()
        
        # Shutdown thread pool
        self.executor.shutdown(wait=True, timeout=30)
        
        logger.info("SMS worker shutdown complete")

def main():
    """Main worker entry point"""
    worker = SMSWorker()
    
    try:
        worker.initialize()
        worker.start_consuming()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Worker failed: {e}")
        sys.exit(1)
    finally:
        worker.shutdown()

if __name__ == "__main__":
    main()