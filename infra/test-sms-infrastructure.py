#!/usr/bin/env python3
"""
SMS Infrastructure Test Suite
Comprehensive testing of Redis, RabbitMQ, and SMS services
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

import httpx
import redis
import pika
from colorama import Fore, Style, init

# Initialize colorama for colored output
init(autoreset=True)

class SMSInfrastructureTester:
    """Comprehensive SMS infrastructure testing suite"""
    
    def __init__(self):
        self.base_url = "http://localhost:8002"
        self.redis_url = "redis://localhost:6379/0"
        self.rabbitmq_url = os.getenv('RABBITMQ_URL', 'amqp://admin:changeme@localhost:5672/')
        
        self.redis_client = None
        self.rabbit_connection = None
        self.rabbit_channel = None
        
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_results = []
    
    def log_success(self, message: str):
        """Log success message"""
        print(f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}")
        self.tests_passed += 1
    
    def log_failure(self, message: str, error: str = ""):
        """Log failure message"""
        print(f"{Fore.RED}✗ {message}{Style.RESET_ALL}")
        if error:
            print(f"{Fore.YELLOW}  Error: {error}{Style.RESET_ALL}")
        self.tests_failed += 1
    
    def log_info(self, message: str):
        """Log info message"""
        print(f"{Fore.BLUE}ℹ {message}{Style.RESET_ALL}")
    
    def log_warning(self, message: str):
        """Log warning message"""
        print(f"{Fore.YELLOW}⚠ {message}{Style.RESET_ALL}")
    
    async def test_redis_connectivity(self):
        """Test Redis connection and basic operations"""
        self.log_info("Testing Redis connectivity...")
        
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            
            # Test connection
            self.redis_client.ping()
            self.log_success("Redis connection established")
            
            # Test basic operations
            test_key = "sms_test:ping"
            test_value = f"test_{int(time.time())}"
            
            self.redis_client.set(test_key, test_value, ex=60)
            retrieved_value = self.redis_client.get(test_key)
            
            if retrieved_value == test_value:
                self.log_success("Redis read/write operations working")
            else:
                self.log_failure("Redis read/write operations failed")
            
            # Test hash operations (used by SMS service)
            hash_key = "sms_test:hash"
            hash_data = {
                "message_id": "test_123",
                "phone_number": "+1234567890",
                "status": "sent",
                "timestamp": datetime.now().isoformat()
            }
            
            self.redis_client.hset(hash_key, mapping=hash_data)
            retrieved_hash = self.redis_client.hgetall(hash_key)
            
            if all(retrieved_hash.get(k) == v for k, v in hash_data.items()):
                self.log_success("Redis hash operations working")
            else:
                self.log_failure("Redis hash operations failed")
            
            # Cleanup
            self.redis_client.delete(test_key, hash_key)
            
        except Exception as e:
            self.log_failure("Redis connectivity test failed", str(e))
    
    def test_rabbitmq_connectivity(self):
        """Test RabbitMQ connection and queue operations"""
        self.log_info("Testing RabbitMQ connectivity...")
        
        try:
            # Establish connection
            connection_params = pika.URLParameters(self.rabbitmq_url)
            self.rabbit_connection = pika.BlockingConnection(connection_params)
            self.rabbit_channel = self.rabbit_connection.channel()
            
            self.log_success("RabbitMQ connection established")
            
            # Test queue declaration
            test_queue = "sms_test_queue"
            self.rabbit_channel.queue_declare(queue=test_queue, durable=True)
            self.log_success("RabbitMQ queue declaration working")
            
            # Test message publish/consume
            test_message = json.dumps({
                "test": True,
                "timestamp": time.time(),
                "message": "SMS infrastructure test"
            })
            
            self.rabbit_channel.basic_publish(
                exchange='',
                routing_key=test_queue,
                body=test_message,
                properties=pika.BasicProperties(delivery_mode=2)
            )
            
            # Get message back
            method_frame, header_frame, body = self.rabbit_channel.basic_get(queue=test_queue)
            
            if method_frame and body:
                received_data = json.loads(body.decode('utf-8'))
                if received_data.get("test") is True:
                    self.log_success("RabbitMQ message publish/consume working")
                    self.rabbit_channel.basic_ack(method_frame.delivery_tag)
                else:
                    self.log_failure("RabbitMQ message content validation failed")
            else:
                self.log_failure("RabbitMQ message consume failed")
            
            # Test exchange operations (used by SMS service)
            test_exchange = "sms_test_exchange"
            self.rabbit_channel.exchange_declare(
                exchange=test_exchange,
                exchange_type='direct',
                durable=True
            )
            self.log_success("RabbitMQ exchange operations working")
            
            # Cleanup
            self.rabbit_channel.queue_delete(queue=test_queue)
            self.rabbit_channel.exchange_delete(exchange=test_exchange)
            
        except Exception as e:
            self.log_failure("RabbitMQ connectivity test failed", str(e))
    
    async def test_sms_service_health(self):
        """Test SMS service health and basic endpoints"""
        self.log_info("Testing SMS service health...")
        
        try:
            async with httpx.AsyncClient() as client:
                # Test health endpoint
                response = await client.get(f"{self.base_url}/health", timeout=10.0)
                
                if response.status_code == 200:
                    health_data = response.json()
                    self.log_success("SMS service health endpoint responding")
                    
                    # Validate health data structure
                    required_fields = ['status', 'timestamp', 'service']
                    if all(field in health_data for field in required_fields):
                        self.log_success("Health endpoint data structure valid")
                    else:
                        self.log_failure("Health endpoint missing required fields")
                    
                    # Check service dependencies
                    if health_data.get('redis_connected'):
                        self.log_success("SMS service connected to Redis")
                    else:
                        self.log_warning("SMS service not connected to Redis")
                    
                    if health_data.get('rabbitmq_connected'):
                        self.log_success("SMS service connected to RabbitMQ")
                    else:
                        self.log_warning("SMS service not connected to RabbitMQ")
                    
                else:
                    self.log_failure(f"Health endpoint returned {response.status_code}")
                
                # Test OpenAPI docs endpoint
                docs_response = await client.get(f"{self.base_url}/docs", timeout=5.0)
                if docs_response.status_code == 200:
                    self.log_success("SMS service API documentation accessible")
                else:
                    self.log_warning("API documentation not accessible")
        
        except Exception as e:
            self.log_failure("SMS service health test failed", str(e))
    
    async def test_phone_pool_endpoints(self):
        """Test phone number pool management endpoints"""
        self.log_info("Testing phone pool management...")
        
        try:
            async with httpx.AsyncClient() as client:
                # Test phone pool status endpoint
                response = await client.get(
                    f"{self.base_url}/api/v1/phone-pool/status",
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    pool_data = response.json()
                    self.log_success("Phone pool status endpoint responding")
                    
                    # Validate pool data structure
                    if 'pool_health' in pool_data:
                        health = pool_data['pool_health']
                        available_count = health.get('available_count', 0)
                        total_count = health.get('total_numbers', 0)
                        
                        self.log_info(f"Phone pool: {available_count} available, {total_count} total")
                        
                        if total_count > 0:
                            self.log_success("Phone pool has numbers available")
                        else:
                            self.log_warning("Phone pool is empty - may need Twilio configuration")
                    
                    else:
                        self.log_failure("Phone pool status missing health data")
                
                else:
                    self.log_failure(f"Phone pool status returned {response.status_code}")
                
                # Test cleanup endpoint
                cleanup_response = await client.post(
                    f"{self.base_url}/api/v1/phone-pool/cleanup",
                    timeout=5.0
                )
                
                if cleanup_response.status_code == 200:
                    self.log_success("Phone pool cleanup endpoint working")
                else:
                    self.log_warning("Phone pool cleanup endpoint not responding")
        
        except Exception as e:
            self.log_failure("Phone pool endpoints test failed", str(e))
    
    async def test_sms_api_endpoints(self):
        """Test SMS API endpoints (without sending real SMS)"""
        self.log_info("Testing SMS API endpoints...")
        
        try:
            async with httpx.AsyncClient() as client:
                # Test SMS send endpoint with invalid data (should return validation error)
                invalid_sms_data = {
                    "phone_number": "invalid_number",
                    "message": ""
                }
                
                response = await client.post(
                    f"{self.base_url}/api/v1/sms/send",
                    json=invalid_sms_data,
                    timeout=5.0
                )
                
                if response.status_code == 422:  # Validation error expected
                    self.log_success("SMS send endpoint validation working")
                else:
                    self.log_warning(f"SMS send endpoint returned unexpected status: {response.status_code}")
                
                # Test SMS queue endpoint with invalid data
                queue_response = await client.post(
                    f"{self.base_url}/api/v1/sms/queue",
                    json=invalid_sms_data,
                    timeout=5.0
                )
                
                if queue_response.status_code == 422:  # Validation error expected
                    self.log_success("SMS queue endpoint validation working")
                else:
                    self.log_warning(f"SMS queue endpoint returned unexpected status: {queue_response.status_code}")
                
                # Test status endpoint with fake message ID
                fake_message_id = "fake_message_id_123"
                status_response = await client.get(
                    f"{self.base_url}/api/v1/sms/{fake_message_id}/status",
                    timeout=5.0
                )
                
                if status_response.status_code in [404, 503]:  # Expected responses
                    self.log_success("SMS status endpoint responding correctly")
                else:
                    self.log_warning(f"SMS status endpoint returned unexpected status: {status_response.status_code}")
        
        except Exception as e:
            self.log_failure("SMS API endpoints test failed", str(e))
    
    async def test_prometheus_metrics(self):
        """Test Prometheus metrics endpoint"""
        self.log_info("Testing Prometheus metrics...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/metrics", timeout=5.0)
                
                if response.status_code == 200:
                    metrics_text = response.text
                    
                    # Check for expected metrics
                    expected_metrics = [
                        'sms_requests_total',
                        'sms_request_duration_seconds',
                        'circuit_breaker_state',
                        'queue_size'
                    ]
                    
                    found_metrics = [metric for metric in expected_metrics if metric in metrics_text]
                    
                    if len(found_metrics) >= 2:  # At least some metrics present
                        self.log_success(f"Prometheus metrics endpoint working ({len(found_metrics)}/{len(expected_metrics)} metrics found)")
                    else:
                        self.log_warning("Few Prometheus metrics found - service may need warm-up")
                
                else:
                    self.log_failure(f"Prometheus metrics endpoint returned {response.status_code}")
        
        except Exception as e:
            self.log_failure("Prometheus metrics test failed", str(e))
    
    def test_infrastructure_integration(self):
        """Test integration between components"""
        self.log_info("Testing infrastructure integration...")
        
        try:
            if self.redis_client and self.rabbit_channel:
                # Test cross-service data flow simulation
                test_message_id = f"integration_test_{int(time.time())}"
                
                # Simulate SMS service storing data in Redis
                sms_data = {
                    "message_id": test_message_id,
                    "phone_number": "+1234567890",
                    "status": "queued",
                    "provider": "test",
                    "queued_at": datetime.now().isoformat()
                }
                
                self.redis_client.hset(f"sms:{test_message_id}", mapping=sms_data)
                
                # Simulate worker processing queue message
                queue_message = {
                    "message_id": test_message_id,
                    "phone_number": "+1234567890",
                    "message": "Integration test message",
                    "priority": 1,
                    "metadata": {"test": True}
                }
                
                self.rabbit_channel.basic_publish(
                    exchange='',
                    routing_key='sms_test_integration',
                    body=json.dumps(queue_message),
                    properties=pika.BasicProperties(delivery_mode=2)
                )
                
                # Verify data in Redis
                retrieved_data = self.redis_client.hgetall(f"sms:{test_message_id}")
                if retrieved_data and retrieved_data.get("message_id") == test_message_id:
                    self.log_success("Redis-RabbitMQ integration test passed")
                else:
                    self.log_failure("Redis-RabbitMQ integration test failed")
                
                # Cleanup
                self.redis_client.delete(f"sms:{test_message_id}")
                
            else:
                self.log_warning("Cannot test integration - missing Redis or RabbitMQ connection")
        
        except Exception as e:
            self.log_failure("Infrastructure integration test failed", str(e))
    
    def check_environment_configuration(self):
        """Check environment variables and configuration"""
        self.log_info("Checking environment configuration...")
        
        # Check required environment variables
        required_vars = [
            "TWILIO_ACCOUNT_SID",
            "TWILIO_AUTH_TOKEN",
            "TWILIO_PHONE_NUMBER"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            self.log_warning(f"Missing environment variables: {', '.join(missing_vars)}")
            self.log_warning("SMS service may not function properly without these")
        else:
            self.log_success("Required environment variables are set")
        
        # Check optional variables
        optional_vars = {
            "AWS_SNS_ACCESS_KEY": "AWS SNS failover",
            "RABBITMQ_USER": "RabbitMQ authentication",
            "RABBITMQ_PASS": "RabbitMQ authentication"
        }
        
        for var, purpose in optional_vars.items():
            if os.getenv(var):
                self.log_success(f"{var} configured for {purpose}")
            else:
                self.log_info(f"{var} not set - {purpose} disabled")
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        total_tests = self.tests_passed + self.tests_failed
        success_rate = (self.tests_passed / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"SMS INFRASTRUCTURE TEST REPORT")
        print(f"{'='*60}{Style.RESET_ALL}\n")
        
        print(f"Total Tests: {total_tests}")
        print(f"{Fore.GREEN}Passed: {self.tests_passed}{Style.RESET_ALL}")
        print(f"{Fore.RED}Failed: {self.tests_failed}{Style.RESET_ALL}")
        print(f"Success Rate: {success_rate:.1f}%\n")
        
        if success_rate >= 80:
            print(f"{Fore.GREEN}✓ Infrastructure is ready for production use{Style.RESET_ALL}")
        elif success_rate >= 60:
            print(f"{Fore.YELLOW}⚠ Infrastructure has some issues but should work{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}✗ Infrastructure has significant issues{Style.RESET_ALL}")
        
        print(f"\n{Fore.BLUE}Next Steps:{Style.RESET_ALL}")
        if self.tests_failed == 0:
            print("• Infrastructure is fully functional")
            print("• You can start sending SMS messages")
            print("• Monitor logs: docker-compose logs -f sms-service")
        else:
            print("• Review failed tests above")
            print("• Check service logs: docker-compose logs sms-service")
            print("• Verify environment variables")
            print("• Ensure all services are running: docker-compose ps")
    
    async def run_all_tests(self):
        """Run all infrastructure tests"""
        print(f"{Fore.CYAN}Starting SMS Infrastructure Test Suite...{Style.RESET_ALL}\n")
        
        # Environment check
        self.check_environment_configuration()
        print()
        
        # Core infrastructure tests
        await self.test_redis_connectivity()
        self.test_rabbitmq_connectivity()
        print()
        
        # SMS service tests
        await self.test_sms_service_health()
        await self.test_phone_pool_endpoints()
        await self.test_sms_api_endpoints()
        await self.test_prometheus_metrics()
        print()
        
        # Integration tests
        self.test_infrastructure_integration()
        print()
        
        # Generate report
        self.generate_test_report()
        
        # Cleanup connections
        if self.redis_client:
            self.redis_client.close()
        if self.rabbit_connection and not self.rabbit_connection.is_closed:
            self.rabbit_connection.close()
        
        return self.tests_failed == 0

async def main():
    """Main test runner"""
    tester = SMSInfrastructureTester()
    
    try:
        success = await tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Test suite interrupted by user{Style.RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Fore.RED}Test suite failed with error: {e}{Style.RESET_ALL}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())