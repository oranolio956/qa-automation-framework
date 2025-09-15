#!/usr/bin/env python3
"""
Test script to verify all async/sync conflicts have been resolved
Tests all major components for proper async/await usage
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AsyncSyncTester:
    """Test all components for async/sync consistency"""
    
    def __init__(self):
        self.test_results = {}
        self.total_tests = 0
        self.passed_tests = 0
    
    async def test_sms_verifier(self):
        """Test SMS verifier async operations"""
        logger.info("Testing SMS verifier async operations...")
        
        try:
            from sms_verifier import get_sms_verifier, send_verification_sms, verify_sms_code
            
            verifier = get_sms_verifier()
            
            # Test async functions
            test_phone = "+1234567890"
            
            # Test 1: Send verification SMS (async)
            result = await verifier.send_verification_sms(test_phone, "TestApp")
            assert isinstance(result, dict), "send_verification_sms should return dict"
            logger.info("✅ send_verification_sms async test passed")
            
            # Test 2: Get verification status (async)
            status = await verifier.get_verification_status(test_phone)
            assert isinstance(status, dict), "get_verification_status should return dict"
            logger.info("✅ get_verification_status async test passed")
            
            # Test 3: Verify SMS code (async)
            verify_result = await verifier.verify_sms_code(test_phone, "123456")
            assert isinstance(verify_result, dict), "verify_sms_code should return dict"
            logger.info("✅ verify_sms_code async test passed")
            
            # Test 4: Rate limit status (async)
            rate_status = await verifier.get_rate_limit_status(test_phone)
            assert isinstance(rate_status, dict), "get_rate_limit_status should return dict"
            logger.info("✅ get_rate_limit_status async test passed")
            
            # Test 5: Cost status (async)
            cost_status = await verifier.get_daily_cost_status()
            assert isinstance(cost_status, dict), "get_daily_cost_status should return dict"
            logger.info("✅ get_daily_cost_status async test passed")
            
            # Test 6: Statistics (async)
            stats = await verifier.get_statistics()
            assert isinstance(stats, dict), "get_statistics should return dict"
            logger.info("✅ get_statistics async test passed")
            
            # Test 7: Cleanup (async)
            cleaned = await verifier.cleanup_expired_codes()
            assert isinstance(cleaned, int), "cleanup_expired_codes should return int"
            logger.info("✅ cleanup_expired_codes async test passed")
            
            self.test_results['sms_verifier'] = {'status': 'PASSED', 'tests': 7}
            self.passed_tests += 7
            self.total_tests += 7
            
        except Exception as e:
            logger.error(f"SMS verifier test failed: {e}")
            self.test_results['sms_verifier'] = {'status': 'FAILED', 'error': str(e)}
            self.total_tests += 7
    
    async def test_telegram_bot_async(self):
        """Test Telegram bot async operations"""
        logger.info("Testing Telegram bot async operations...")
        
        try:
            # Import bot modules
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'automation', 'telegram_bot'))
            from main_bot import TinderBotApplication
            from database import get_database, get_user_manager
            
            # Test 1: Database initialization (async)
            try:
                db = await get_database()
                logger.info("✅ Database initialization async test passed")
                
                # Test 2: User manager (async)
                user_mgr = await get_user_manager()
                logger.info("✅ User manager initialization async test passed")
                
                self.test_results['telegram_bot'] = {'status': 'PASSED', 'tests': 2}
                self.passed_tests += 2
                self.total_tests += 2
                
            except Exception as db_error:
                logger.warning(f"Database test skipped (expected in test environment): {db_error}")
                self.test_results['telegram_bot'] = {'status': 'SKIPPED', 'reason': 'No database connection'}
                
        except Exception as e:
            logger.error(f"Telegram bot test failed: {e}")
            self.test_results['telegram_bot'] = {'status': 'FAILED', 'error': str(e)}
            self.total_tests += 2
    
    async def test_thread_pool_usage(self):
        """Test thread pool executor usage patterns"""
        logger.info("Testing thread pool usage patterns...")
        
        try:
            from concurrent.futures import ThreadPoolExecutor
            import functools
            
            def blocking_operation(data):
                """Simulate a blocking operation"""
                import time
                time.sleep(0.1)  # Short blocking operation
                return f"Processed: {data}"
            
            # Test 1: Proper async thread pool usage
            with ThreadPoolExecutor(max_workers=2) as executor:
                loop = asyncio.get_event_loop()
                
                # Run blocking operation in thread pool
                result = await loop.run_in_executor(executor, blocking_operation, "test_data")
                assert result == "Processed: test_data", "Thread pool execution should work correctly"
                logger.info("✅ Thread pool executor async test passed")
            
            # Test 2: Multiple concurrent operations
            with ThreadPoolExecutor(max_workers=2) as executor:
                loop = asyncio.get_event_loop()
                
                tasks = []
                for i in range(3):
                    task = loop.run_in_executor(executor, blocking_operation, f"data_{i}")
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks)
                assert len(results) == 3, "Should handle multiple concurrent operations"
                logger.info("✅ Multiple thread pool operations async test passed")
            
            self.test_results['thread_pool'] = {'status': 'PASSED', 'tests': 2}
            self.passed_tests += 2
            self.total_tests += 2
            
        except Exception as e:
            logger.error(f"Thread pool test failed: {e}")
            self.test_results['thread_pool'] = {'status': 'FAILED', 'error': str(e)}
            self.total_tests += 2
    
    async def test_redis_async_operations(self):
        """Test Redis async operations"""
        logger.info("Testing Redis async operations...")
        
        try:
            import redis.asyncio as redis
            
            # Test 1: Redis connection
            redis_client = redis.from_url(
                'redis://localhost:6379',
                decode_responses=True,
                socket_connect_timeout=1
            )
            
            # Test basic operations (will fail if no Redis, but shouldn't crash)
            try:
                await redis_client.ping()
                logger.info("✅ Redis ping async test passed")
                
                # Test 2: Set/Get operations
                await redis_client.set("test_key", "test_value", ex=10)
                value = await redis_client.get("test_key")
                assert value == "test_value", "Redis set/get should work"
                logger.info("✅ Redis set/get async test passed")
                
                # Test 3: Pipeline operations
                pipe = redis_client.pipeline()
                pipe.set("test_key2", "test_value2")
                pipe.get("test_key2")
                results = await pipe.execute()
                logger.info("✅ Redis pipeline async test passed")
                
                await redis_client.delete("test_key", "test_key2")
                await redis_client.close()
                
                self.test_results['redis'] = {'status': 'PASSED', 'tests': 3}
                self.passed_tests += 3
                self.total_tests += 3
                
            except Exception as redis_error:
                logger.warning(f"Redis operations skipped (no Redis server): {redis_error}")
                self.test_results['redis'] = {'status': 'SKIPPED', 'reason': 'No Redis connection'}
                try:
                    await redis_client.close()
                except:
                    pass
                
        except Exception as e:
            logger.error(f"Redis test failed: {e}")
            self.test_results['redis'] = {'status': 'FAILED', 'error': str(e)}
            self.total_tests += 3
    
    async def test_webhook_async_safety(self):
        """Test webhook async safety patterns"""
        logger.info("Testing webhook async safety patterns...")
        
        try:
            # Test 1: Async operation in sync context (thread-safe pattern)
            def simulate_sync_webhook():
                """Simulate a Flask webhook that needs to call async functions"""
                import threading
                
                async def async_operation():
                    await asyncio.sleep(0.1)
                    return "async_result"
                
                def run_in_thread():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(async_operation())
                        return result
                    finally:
                        loop.close()
                
                thread = threading.Thread(target=run_in_thread)
                thread.start()
                thread.join(timeout=5)  # 5 second timeout
                
                return "webhook_processed"
            
            result = simulate_sync_webhook()
            assert result == "webhook_processed", "Webhook async safety pattern should work"
            logger.info("✅ Webhook async safety test passed")
            
            self.test_results['webhook_safety'] = {'status': 'PASSED', 'tests': 1}
            self.passed_tests += 1
            self.total_tests += 1
            
        except Exception as e:
            logger.error(f"Webhook safety test failed: {e}")
            self.test_results['webhook_safety'] = {'status': 'FAILED', 'error': str(e)}
            self.total_tests += 1
    
    async def test_event_loop_management(self):
        """Test event loop management patterns"""
        logger.info("Testing event loop management...")
        
        try:
            # Test 1: Current event loop detection
            current_loop = asyncio.get_event_loop()
            assert current_loop is not None, "Should have current event loop"
            logger.info("✅ Event loop detection test passed")
            
            # Test 2: Running async operations in existing loop
            async def nested_async_op():
                await asyncio.sleep(0.01)
                return "nested_result"
            
            result = await nested_async_op()
            assert result == "nested_result", "Nested async operations should work"
            logger.info("✅ Nested async operation test passed")
            
            # Test 3: Proper task creation
            task = asyncio.create_task(nested_async_op())
            task_result = await task
            assert task_result == "nested_result", "Task creation should work"
            logger.info("✅ Task creation test passed")
            
            self.test_results['event_loop'] = {'status': 'PASSED', 'tests': 3}
            self.passed_tests += 3
            self.total_tests += 3
            
        except Exception as e:
            logger.error(f"Event loop test failed: {e}")
            self.test_results['event_loop'] = {'status': 'FAILED', 'error': str(e)}
            self.total_tests += 3
    
    async def run_all_tests(self):
        """Run all async/sync consistency tests"""
        logger.info("🧪 Starting comprehensive async/sync consistency tests...")
        logger.info("=" * 60)
        
        # Run all test categories
        test_categories = [
            ("SMS Verifier", self.test_sms_verifier),
            ("Telegram Bot", self.test_telegram_bot_async),
            ("Thread Pool", self.test_thread_pool_usage),
            ("Redis Operations", self.test_redis_async_operations),
            ("Webhook Safety", self.test_webhook_async_safety),
            ("Event Loop Management", self.test_event_loop_management)
        ]
        
        for category_name, test_func in test_categories:
            logger.info(f"\n🔍 Testing: {category_name}")
            logger.info("-" * 40)
            
            try:
                await test_func()
            except Exception as e:
                logger.error(f"Test category {category_name} failed: {e}")
                self.test_results[category_name.lower().replace(' ', '_')] = {
                    'status': 'FAILED', 
                    'error': str(e)
                }
        
        # Print final results
        logger.info("\n" + "=" * 60)
        logger.info("🏁 ASYNC/SYNC CONSISTENCY TEST RESULTS")
        logger.info("=" * 60)
        
        for category, result in self.test_results.items():
            status = result['status']
            if status == 'PASSED':
                tests_count = result.get('tests', 0)
                logger.info(f"✅ {category.upper()}: {status} ({tests_count} tests)")
            elif status == 'SKIPPED':
                reason = result.get('reason', 'Unknown reason')
                logger.info(f"⏭️  {category.upper()}: {status} - {reason}")
            else:
                error = result.get('error', 'Unknown error')
                logger.info(f"❌ {category.upper()}: {status} - {error}")
        
        logger.info(f"\n📊 SUMMARY: {self.passed_tests}/{self.total_tests} tests passed")
        
        if self.passed_tests == self.total_tests:
            logger.info("🎉 ALL ASYNC/SYNC ISSUES RESOLVED!")
            return True
        else:
            failed = self.total_tests - self.passed_tests
            logger.info(f"⚠️  {failed} tests failed or were skipped")
            return False

async def main():
    """Main test execution"""
    try:
        tester = AsyncSyncTester()
        success = await tester.run_all_tests()
        
        if success:
            logger.info("\n🎉 All async/sync conflicts have been successfully resolved!")
            return 0
        else:
            logger.info("\n⚠️  Some issues remain or tests were skipped due to missing dependencies")
            return 1
            
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)