#!/usr/bin/env python3
"""
Pytest Configuration and Fixtures for Comprehensive Testing
Central configuration for all test categories
"""

import pytest
import asyncio
import tempfile
import os
import sys
import logging
from typing import Dict, List, Generator
from unittest.mock import MagicMock, patch
import redis
import psutil
from datetime import datetime

# Add automation module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../automation'))

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "unit: Unit tests that run quickly without external dependencies"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests that require external services"
    )
    config.addinivalue_line(
        "markers", "performance: Performance and benchmark tests"
    )
    config.addinivalue_line(
        "markers", "load: Load testing scenarios"
    )
    config.addinivalue_line(
        "markers", "monitoring: Monitoring and alerting tests"
    )
    config.addinivalue_line(
        "markers", "anti_detection: Anti-detection technique validation tests"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take longer than 30 seconds"
    )
    config.addinivalue_line(
        "markers", "requires_emulator: Tests that require Android emulator"
    )
    config.addinivalue_line(
        "markers", "requires_real_services: Tests that require real third-party services"
    )
    config.addinivalue_line(
        "markers", "chaos: Chaos engineering and failure injection tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers and skip conditions"""
    
    # Skip real service tests if not in CI or explicitly enabled
    skip_real_services = pytest.mark.skip(
        reason="Real service tests require API keys and are disabled by default"
    )
    
    # Skip emulator tests if Android SDK not available
    skip_emulator = pytest.mark.skip(
        reason="Android SDK/emulator not available"
    )
    
    for item in items:
        # Skip real service tests unless explicitly enabled
        if "requires_real_services" in item.keywords:
            if not config.getoption("--real-services", default=False):
                item.add_marker(skip_real_services)
        
        # Skip emulator tests if SDK not available
        if "requires_emulator" in item.keywords:
            if not _check_android_sdk_available():
                item.add_marker(skip_emulator)
        
        # Add timeout to slow tests
        if "slow" in item.keywords:
            item.add_marker(pytest.mark.timeout(300))  # 5 minute timeout
        
        # Add timeout to load tests
        if "load" in item.keywords:
            item.add_marker(pytest.mark.timeout(1200))  # 20 minute timeout


def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption(
        "--real-services",
        action="store_true",
        default=False,
        help="Run tests that require real third-party services"
    )
    parser.addoption(
        "--load-test",
        action="store_true",
        default=False,
        help="Run load tests (may take significant time)"
    )
    parser.addoption(
        "--benchmark",
        action="store_true",
        default=False,
        help="Run benchmark tests for performance regression"
    )


def _check_android_sdk_available() -> bool:
    """Check if Android SDK is available"""
    try:
        import subprocess
        result = subprocess.run(['adb', 'version'], capture_output=True, text=True)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.SubprocessError):
        return False


# Test Environment Fixtures

@pytest.fixture(scope="session")
def test_environment():
    """Fixture providing test environment information"""
    return {
        'platform': sys.platform,
        'python_version': sys.version,
        'pytest_version': pytest.__version__,
        'test_start_time': datetime.now(),
        'android_sdk_available': _check_android_sdk_available(),
        'redis_available': _check_redis_available(),
        'temp_dir': tempfile.gettempdir()
    }


def _check_redis_available() -> bool:
    """Check if Redis is available for testing"""
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, socket_connect_timeout=1)
        r.ping()
        return True
    except (redis.ConnectionError, redis.TimeoutError):
        return False


@pytest.fixture
def temp_test_dir():
    """Fixture providing temporary directory for test files"""
    with tempfile.TemporaryDirectory(prefix="test_automation_") as temp_dir:
        yield temp_dir


@pytest.fixture
def test_logger():
    """Fixture providing test logger"""
    logger = logging.getLogger("test_automation")
    logger.setLevel(logging.DEBUG)
    return logger


# Mock Service Fixtures

@pytest.fixture
def mock_redis():
    """Fixture providing mock Redis client"""
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = True
    mock_redis.exists.return_value = False
    return mock_redis


@pytest.fixture
def mock_database():
    """Fixture providing mock database connection"""
    mock_db = MagicMock()
    mock_db.execute.return_value = MagicMock()
    mock_db.fetchall.return_value = []
    mock_db.fetchone.return_value = None
    mock_db.commit.return_value = None
    mock_db.rollback.return_value = None
    return mock_db


@pytest.fixture
def mock_email_service():
    """Fixture providing mock email service"""
    mock_service = MagicMock()
    
    # Mock email account creation
    mock_account = MagicMock()
    mock_account.email = "test@temp-mail.com"
    mock_account.provider = "temp-mail"
    mock_account.created_at = datetime.now()
    
    mock_service.create_email_account.return_value = mock_account
    mock_service.get_inbox_messages.return_value = []
    mock_service.delete_email_account.return_value = True
    
    return mock_service


@pytest.fixture
def mock_sms_service():
    """Fixture providing mock SMS service"""
    mock_service = MagicMock()
    
    mock_service.send_sms.return_value = {
        'success': True,
        'message_sid': 'SM1234567890abcdef',
        'status': 'queued'
    }
    
    mock_service.verify_sms_code.return_value = {
        'success': True,
        'verified': True
    }
    
    return mock_service


@pytest.fixture
def mock_captcha_service():
    """Fixture providing mock CAPTCHA service"""
    mock_service = MagicMock()
    
    mock_service.solve_captcha.return_value = "CAPTCHA_SOLUTION_123"
    mock_service.get_provider_balances.return_value = {
        '2captcha': 10.50,
        'anti_captcha': 5.25
    }
    
    return mock_service


@pytest.fixture
def mock_emulator_manager():
    """Fixture providing mock emulator manager"""
    mock_manager = MagicMock()
    
    # Mock emulator instance
    mock_instance = MagicMock()
    mock_instance.device_id = "emulator-5554"
    mock_instance.is_ready = True
    mock_instance.avd_name = "test_avd"
    mock_instance.port = 5554
    
    mock_manager.create_emulator_pool.return_value = [mock_instance]
    mock_manager.start_emulator.return_value = mock_instance
    mock_manager.stop_emulator.return_value = True
    
    return mock_manager


# Performance Testing Fixtures

@pytest.fixture
def performance_monitor():
    """Fixture providing performance monitoring"""
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.start_memory = None
            self.metrics = {}
        
        def start_monitoring(self):
            self.start_time = time.time()
            process = psutil.Process()
            self.start_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        def stop_monitoring(self):
            if self.start_time:
                duration = time.time() - self.start_time
                process = psutil.Process()
                current_memory = process.memory_info().rss / 1024 / 1024
                
                self.metrics = {
                    'duration': duration,
                    'start_memory_mb': self.start_memory,
                    'end_memory_mb': current_memory,
                    'memory_delta_mb': current_memory - self.start_memory,
                    'cpu_percent': process.cpu_percent()
                }
                
                return self.metrics
            return {}
    
    return PerformanceMonitor()


@pytest.fixture
def benchmark_thresholds():
    """Fixture providing performance benchmark thresholds"""
    return {
        'profile_generation': {
            'max_duration': 0.1,
            'max_memory_mb': 50
        },
        'device_fingerprint': {
            'max_duration': 0.5,
            'max_memory_mb': 100
        },
        'email_creation': {
            'max_duration': 30.0,
            'max_memory_mb': 200
        },
        'account_creation': {
            'max_duration': 180.0,
            'max_memory_mb': 1000
        }
    }


# Integration Testing Fixtures

@pytest.fixture
def integration_test_config():
    """Fixture providing integration test configuration"""
    return {
        'email_service_timeout': 30,
        'sms_service_timeout': 60,
        'captcha_service_timeout': 120,
        'emulator_startup_timeout': 180,
        'max_retries': 3,
        'retry_delay': 1.0
    }


@pytest.fixture
def test_account_profiles():
    """Fixture providing test account profiles"""
    from tinder.account_creator import AccountProfile
    from datetime import date
    
    profiles = [
        AccountProfile(
            first_name="TestUser1",
            birth_date=date(1995, 6, 15),
            gender="man",
            interested_in="women",
            phone_number="+15555551234",
            email="testuser1@example.com",
            bio="Test profile for automation testing",
            photos=[],
            location=(40.7128, -74.0060),  # New York
            snapchat_username="testsnap1"
        ),
        AccountProfile(
            first_name="TestUser2",
            birth_date=date(1992, 3, 22),
            gender="woman",
            interested_in="men",
            phone_number="+15555555678",
            email="testuser2@example.com",
            bio="Another test profile",
            photos=[],
            location=(34.0522, -118.2437),  # Los Angeles
            snapchat_username="testsnap2"
        )
    ]
    
    return profiles


# Load Testing Fixtures

@pytest.fixture
def load_test_config():
    """Fixture providing load test configuration"""
    return {
        'concurrency_levels': [1, 2, 5, 10],
        'duration_seconds': 60,
        'ramp_up_seconds': 10,
        'operations_per_thread': 3,
        'target_success_rate': 0.90,
        'max_response_time': 180.0,
        'max_memory_mb': 2000,
        'max_cpu_percent': 80
    }


# Monitoring Fixtures

@pytest.fixture
def mock_prometheus_client():
    """Fixture providing mock Prometheus client"""
    from tests.monitoring.test_system_monitoring import MockPrometheusClient
    return MockPrometheusClient()


@pytest.fixture
def mock_structured_logger():
    """Fixture providing mock structured logger"""
    from tests.monitoring.test_system_monitoring import MockStructuredLogger
    return MockStructuredLogger()


# Cleanup Fixtures

@pytest.fixture(autouse=True)
def cleanup_test_resources():
    """Auto-use fixture for cleaning up test resources"""
    created_resources = []
    
    yield created_resources
    
    # Cleanup any resources created during testing
    for resource in created_resources:
        try:
            if hasattr(resource, 'cleanup'):
                resource.cleanup()
            elif hasattr(resource, 'close'):
                resource.close()
        except Exception as e:
            logging.warning(f"Failed to cleanup resource {resource}: {e}")


@pytest.fixture
def event_loop():
    """Fixture providing event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Test Data Factories

@pytest.fixture
def test_data_factory():
    """Fixture providing test data factory"""
    class TestDataFactory:
        @staticmethod
        def create_device_fingerprint_data():
            return {
                'device_id': 'test_device_123',
                'model': 'Samsung Galaxy S21',
                'android_version': '11',
                'brand': 'Samsung',
                'display_resolution': (1080, 2400),
                'dpi': 420,
                'build_id': 'RP1A.200720.012',
                'timezone': 'America/New_York',
                'language': 'en-US',
                'carrier': 'Verizon',
                'ip_address': '192.168.1.100'
            }
        
        @staticmethod
        def create_behavior_pattern_data():
            return {
                'aggressiveness': 0.3,
                'personality_profile': 'cautious',
                'average_swipe_timing': 2.5,
                'session_duration': 8.2,
                'daily_sessions': 3
            }
        
        @staticmethod
        def create_email_account_data():
            return {
                'email': 'test@temp-mail.com',
                'provider': 'temp-mail',
                'created_at': datetime.now(),
                'verified': False,
                'messages': []
            }
    
    return TestDataFactory()


# Error Injection Fixtures for Chaos Testing

@pytest.fixture
def chaos_injector():
    """Fixture for chaos engineering - inject controlled failures"""
    class ChaosInjector:
        def __init__(self):
            self.failure_rate = 0.0
            self.network_delay = 0.0
            self.memory_pressure = False
        
        def inject_failures(self, rate: float):
            """Inject random failures at specified rate"""
            self.failure_rate = rate
        
        def inject_network_delay(self, delay: float):
            """Inject network delays"""
            self.network_delay = delay
        
        def inject_memory_pressure(self, enabled: bool):
            """Inject memory pressure"""
            self.memory_pressure = enabled
        
        def should_fail(self) -> bool:
            """Determine if operation should fail"""
            import random
            return random.random() < self.failure_rate
    
    return ChaosInjector()


# Import time for performance monitoring
import time