#!/usr/bin/env python3
"""
Serverless SMS Processing Function
High-performance SMS queue processing with multiple provider support
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import hashlib
import uuid

import aioredis
import pika
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

class SMSProvider(str, Enum):
    TWILIO = "twilio"
    AWS_SNS = "aws_sns"

class SMSProcessingResult(str, Enum):
    SUCCESS = "success"
    RETRY = "retry"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"

class ServerlessSMSProcessor:
    """Serverless function for processing SMS messages from queue"""
    
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER')
        
        self.aws_access_key = os.getenv('AWS_SNS_ACCESS_KEY')
        self.aws_secret_key = os.getenv('AWS_SNS_SECRET_KEY')
        self.aws_region = os.getenv('AWS_SNS_REGION', 'us-east-1')
        
        self.function_timeout = int(os.getenv('FUNCTION_TIMEOUT', '30'))
        self.max_retries = int(os.getenv('MAX_RETRIES', '3'))
    
    async def initialize(self):
        """Initialize Redis connection"""
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        try:
            self.redis = aioredis.from_url(redis_url, decode_responses=True)
            await self.redis.ping()
            logger.info("Connected to Redis", redis_url=redis_url)
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise
    
    async def close(self):
        """Clean up connections"""
        if self.redis:
            await self.redis.close()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def send_twilio_sms(self, phone_number: str, message: str, message_id: str) -> Dict:
        """Send SMS via Twilio API"""
        if not all([self.twilio_account_sid, self.twilio_auth_token, self.twilio_phone_number]):
            raise Exception("Twilio credentials not configured")
        
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_account_sid}/Messages.json"
        
        data = {
            'From': self.twilio_phone_number,
            'To': phone_number,
            'Body': message
        }
        
        auth = (self.twilio_account_sid, self.twilio_auth_token)
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, data=data, auth=auth)
            response.raise_for_status()
            
            result = response.json()
            return {
                'provider_message_id': result['sid'],
                'status': 'sent',
                'provider': 'twilio',
                'cost': float(result.get('price', 0)) if result.get('price') else None
            }
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def send_aws_sns_sms(self, phone_number: str, message: str, message_id: str) -> Dict:
        """Send SMS via AWS SNS (simulated for this example)"""
        if not all([self.aws_access_key, self.aws_secret_key]):
            raise Exception("AWS SNS credentials not configured")
        
        # In a real implementation, this would use boto3
        # For now, simulate the call
        await asyncio.sleep(0.1)  # Simulate network delay
        
        provider_message_id = f"sns-{int(time.time())}-{hash(message_id) % 10000}"
        
        return {
            'provider_message_id': provider_message_id,
            'status': 'sent',
            'provider': 'aws_sns',
            'cost': 0.00645
        }
    
    async def process_sms_message(self, message_data: Dict) -> Dict:
        """Process a single SMS message"""
        start_time = time.time()
        message_id = message_data.get('message_id', str(uuid.uuid4()))
        
        try:
            phone_number = message_data['phone_number']
            message_text = message_data['message']
            priority = message_data.get('priority', 1)
            metadata = message_data.get('metadata', {})
            retry_count = message_data.get('retry_count', 0)
            
            logger.info("Processing SMS message", 
                       message_id=message_id,
                       phone=phone_number[:5] + "***",
                       retry_count=retry_count)
            
            # Check rate limiting
            rate_limit_key = f"sms_rate_limit:{hashlib.sha256(phone_number.encode()).hexdigest()[:16]}"
            current_count = await self.redis.get(rate_limit_key) or 0
            
            if int(current_count) >= 5:  # Max 5 SMS per hour per phone
                logger.warning("Rate limit exceeded", phone=phone_number[:5] + "***")
                return {
                    'result': SMSProcessingResult.RATE_LIMITED,
                    'message_id': message_id,
                    'error': 'Rate limit exceeded'
                }
            
            # Try providers in order
            providers = [
                ('twilio', self.send_twilio_sms),
                ('aws_sns', self.send_aws_sns_sms)
            ]
            
            last_error = None
            
            for provider_name, provider_func in providers:
                try:
                    # Check if provider is available (circuit breaker simulation)
                    circuit_key = f"circuit_breaker:{provider_name}"
                    circuit_state = await self.redis.get(circuit_key)
                    
                    if circuit_state == 'open':
                        circuit_timeout = await self.redis.ttl(circuit_key)
                        if circuit_timeout > 0:
                            logger.info(f"Circuit breaker open for {provider_name}, trying next provider")
                            continue
                        else:
                            # Reset circuit breaker
                            await self.redis.delete(circuit_key)
                    
                    # Send SMS
                    result = await provider_func(phone_number, message_text, message_id)
                    
                    # Update rate limiting
                    pipe = self.redis.pipeline()
                    pipe.incr(rate_limit_key)
                    pipe.expire(rate_limit_key, 3600)  # 1 hour
                    await pipe.execute()
                    
                    # Store result
                    result_data = {
                        'message_id': message_id,
                        'provider_message_id': result['provider_message_id'],
                        'phone_number_hash': hashlib.sha256(phone_number.encode()).hexdigest(),
                        'status': result['status'],
                        'provider': provider_name,
                        'cost': result.get('cost', 0),
                        'sent_at': datetime.now().isoformat(),
                        'processing_time_ms': (time.time() - start_time) * 1000,
                        'metadata': json.dumps(metadata)
                    }
                    
                    await self.redis.hset(f"sms_result:{message_id}", mapping=result_data)
                    await self.redis.expire(f"sms_result:{message_id}", 86400 * 7)  # 7 days
                    
                    logger.info("SMS sent successfully",
                               message_id=message_id,
                               provider=provider_name,
                               processing_time=result_data['processing_time_ms'])
                    
                    return {
                        'result': SMSProcessingResult.SUCCESS,
                        'message_id': message_id,
                        'provider': provider_name,
                        'provider_message_id': result['provider_message_id'],
                        'cost': result.get('cost'),
                        'processing_time_ms': result_data['processing_time_ms']
                    }
                    
                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"SMS provider {provider_name} failed",
                                 message_id=message_id,
                                 error=last_error)
                    
                    # Update circuit breaker on repeated failures
                    failure_key = f"failures:{provider_name}"
                    failure_count = await self.redis.incr(failure_key)
                    await self.redis.expire(failure_key, 300)  # 5 minutes
                    
                    if failure_count >= 10:  # Open circuit after 10 failures
                        await self.redis.set(circuit_key, 'open', ex=60)  # 1 minute timeout
                        await self.redis.delete(failure_key)
                        logger.warning(f"Circuit breaker opened for {provider_name}")
                    
                    continue
            
            # All providers failed
            if retry_count < self.max_retries:
                logger.info("All providers failed, will retry",
                           message_id=message_id,
                           retry_count=retry_count)
                return {
                    'result': SMSProcessingResult.RETRY,
                    'message_id': message_id,
                    'error': last_error,
                    'retry_count': retry_count + 1
                }
            else:
                logger.error("All providers failed, max retries exceeded",
                           message_id=message_id,
                           retry_count=retry_count)
                return {
                    'result': SMSProcessingResult.FAILED,
                    'message_id': message_id,
                    'error': f"All providers failed: {last_error}",
                    'retry_count': retry_count
                }
                
        except Exception as e:
            logger.error("SMS processing failed",
                        message_id=message_id,
                        error=str(e))
            return {
                'result': SMSProcessingResult.FAILED,
                'message_id': message_id,
                'error': str(e)
            }
    
    async def process_message_batch(self, messages: List[Dict]) -> List[Dict]:
        """Process a batch of SMS messages concurrently"""
        if not messages:
            return []
        
        logger.info("Processing message batch", batch_size=len(messages))
        
        # Process messages concurrently with semaphore to limit concurrency
        semaphore = asyncio.Semaphore(10)  # Max 10 concurrent SMS sends
        
        async def process_with_semaphore(message):
            async with semaphore:
                return await self.process_sms_message(message)
        
        tasks = [process_with_semaphore(msg) for msg in messages]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions in results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    'result': SMSProcessingResult.FAILED,
                    'message_id': messages[i].get('message_id', str(uuid.uuid4())),
                    'error': str(result)
                })
            else:
                processed_results.append(result)
        
        # Log batch summary
        success_count = sum(1 for r in processed_results if r['result'] == SMSProcessingResult.SUCCESS)
        retry_count = sum(1 for r in processed_results if r['result'] == SMSProcessingResult.RETRY)
        failed_count = sum(1 for r in processed_results if r['result'] == SMSProcessingResult.FAILED)
        
        logger.info("Batch processing complete",
                   batch_size=len(messages),
                   success_count=success_count,
                   retry_count=retry_count,
                   failed_count=failed_count)
        
        return processed_results

def lambda_handler(event, context):
    """AWS Lambda handler function"""
    async def async_handler():
        processor = ServerlessSMSProcessor()
        
        try:
            await processor.initialize()
            
            # Parse event data
            if 'Records' in event:
                # SQS event format
                messages = []
                for record in event['Records']:
                    body = json.loads(record['body'])
                    messages.append(body)
            else:
                # Direct invocation format
                messages = event.get('messages', [event])
            
            # Process messages
            results = await processor.process_message_batch(messages)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'processed': len(results),
                    'results': results
                })
            }
            
        except Exception as e:
            logger.error("Lambda function failed", error=str(e))
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': str(e)
                })
            }
        finally:
            await processor.close()
    
    # Run async handler
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(async_handler())
    finally:
        loop.close()

def rabbitmq_consumer():
    """RabbitMQ consumer for containerized deployment"""
    async def async_consumer():
        processor = ServerlessSMSProcessor()
        
        try:
            await processor.initialize()
            
            # RabbitMQ connection
            rabbitmq_url = os.getenv('RABBITMQ_URL', 'amqp://guest:guest@localhost:5672/')
            connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
            channel = connection.channel()
            
            # Declare queues
            channel.queue_declare(queue='sms_queue', durable=True)
            channel.queue_declare(queue='sms_dlq', durable=True)
            
            # Set QoS to process one message at a time
            channel.basic_qos(prefetch_count=1)
            
            def callback(ch, method, properties, body):
                """Process SMS message from queue"""
                try:
                    message_data = json.loads(body)
                    
                    # Run async processing
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    try:
                        result = loop.run_until_complete(
                            processor.process_sms_message(message_data)
                        )
                        
                        if result['result'] == SMSProcessingResult.SUCCESS:
                            # Acknowledge successful processing
                            ch.basic_ack(delivery_tag=method.delivery_tag)
                            logger.info("Message processed successfully",
                                       message_id=result.get('message_id'))
                            
                        elif result['result'] == SMSProcessingResult.RETRY:
                            # Reject and requeue for retry
                            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                            logger.info("Message queued for retry",
                                       message_id=result.get('message_id'))
                            
                        else:
                            # Move to dead letter queue
                            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                            
                            # Publish to DLQ
                            ch.basic_publish(
                                exchange='',
                                routing_key='sms_dlq',
                                body=json.dumps({
                                    'original_message': message_data,
                                    'error': result.get('error'),
                                    'failed_at': datetime.now().isoformat()
                                })
                            )
                            
                            logger.error("Message moved to DLQ",
                                        message_id=result.get('message_id'),
                                        error=result.get('error'))
                    finally:
                        loop.close()
                        
                except Exception as e:
                    # Reject message on processing error
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                    logger.error("Message processing failed", error=str(e))
            
            # Start consuming
            channel.basic_consume(queue='sms_queue', on_message_callback=callback)
            
            logger.info("SMS processor started, waiting for messages...")
            channel.start_consuming()
            
        except KeyboardInterrupt:
            logger.info("SMS processor stopping...")
            channel.stop_consuming()
            connection.close()
        except Exception as e:
            logger.error("SMS processor failed", error=str(e))
            raise
        finally:
            await processor.close()
    
    # Run async consumer
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(async_consumer())
    finally:
        loop.close()

if __name__ == "__main__":
    # Run as RabbitMQ consumer
    rabbitmq_consumer()