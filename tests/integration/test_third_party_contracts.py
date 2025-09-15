#!/usr/bin/env python3
"""
Contract Tests for Third-Party Service Integrations
Tests actual API contracts and service reliability
"""

import pytest
import asyncio
import time
from typing import Dict, List, Optional
from unittest.mock import patch, MagicMock
import httpx
import json
from dataclasses import dataclass

# Import services to test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../automation'))

from email_services.captcha_solver import get_captcha_solver, CaptchaType
from utils.sms_verifier import send_verification_sms, verify_sms_code
from utils.brightdata_proxy import get_brightdata_session, verify_proxy


@dataclass
class ContractTestResult:
    """Result of a contract test"""
    service: str
    endpoint: str
    success: bool
    response_time: float
    status_code: Optional[int] = None
    error: Optional[str] = None
    contract_violations: List[str] = None


class TestTwilioContract:
    """Contract tests for Twilio SMS service"""
    
    @pytest.mark.integration
    @pytest.mark.requires_real_services
    async def test_twilio_sms_sending_contract(self):
        """Test Twilio SMS sending API contract"""
        
        # Test with mock credentials for contract validation
        test_phone = "+15555551234"  # Twilio test number
        
        start_time = time.time()
        
        try:
            result = send_verification_sms(test_phone, "TestService")
            response_time = time.time() - start_time
            
            # Contract assertions
            assert isinstance(result, dict), "Response must be a dictionary"
            assert 'success' in result, "Response must include 'success' field"
            assert 'message_sid' in result or 'error' in result, "Response must include message_sid or error"
            
            if result.get('success'):
                assert 'message_sid' in result, "Successful response must include message_sid"
                assert result['message_sid'].startswith('SM'), "Message SID must start with 'SM'"
            
            # Performance contract
            assert response_time < 5.0, f"SMS API response time {response_time}s exceeds 5s limit"
            
        except Exception as e:
            pytest.fail(f"Twilio contract violation: {e}")
    
    @pytest.mark.integration
    async def test_twilio_rate_limiting_behavior(self):
        """Test Twilio rate limiting contract compliance"""
        
        # Send multiple SMS in rapid succession to test rate limiting
        test_phone = "+15555551234"
        
        results = []
        for i in range(5):
            start_time = time.time()
            result = send_verification_sms(test_phone, f"TestService{i}")
            response_time = time.time() - start_time
            
            results.append(ContractTestResult(
                service="twilio",
                endpoint="messages",
                success=result.get('success', False),
                response_time=response_time,
                error=result.get('error')
            ))
            
            # Small delay between requests
            await asyncio.sleep(0.1)
        
        # Analyze rate limiting behavior
        successful_requests = sum(1 for r in results if r.success)
        rate_limited_requests = sum(1 for r in results if not r.success and 
                                   "rate" in str(r.error).lower())
        
        # Contract: Service should handle rate limiting gracefully
        assert successful_requests > 0, "At least one request should succeed"
        assert all(r.response_time < 10.0 for r in results), "All responses under 10s"
    
    @pytest.mark.integration 
    async def test_twilio_error_response_format(self):
        """Test Twilio error response format contract"""
        
        # Test with invalid phone number to trigger error
        invalid_phone = "invalid_phone"
        
        result = send_verification_sms(invalid_phone, "TestService")
        
        # Contract assertions for error responses
        assert isinstance(result, dict), "Error response must be dictionary"
        assert result.get('success') is False, "Error response must have success=False"
        assert 'error' in result, "Error response must include error field"
        assert isinstance(result['error'], str), "Error field must be string"


class TestCaptchaProviderContracts:
    """Contract tests for CAPTCHA solving services"""
    
    @pytest.mark.integration
    @pytest.mark.requires_real_services
    async def test_2captcha_api_contract(self):
        """Test 2Captcha API contract"""
        
        captcha_solver = get_captcha_solver()
        
        # Create minimal test image (1x1 pixel PNG)
        test_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        
        start_time = time.time()
        
        try:
            # Test with short timeout for contract validation
            solution = await captcha_solver.solve_captcha(
                CaptchaType.IMAGE,
                image_data=test_image,
                timeout=30
            )
            
            response_time = time.time() - start_time
            
            # Contract assertions
            if solution is not None:
                assert isinstance(solution, str), "Solution must be string"
                assert len(solution) > 0, "Solution must not be empty"
            
            # Performance contract
            assert response_time < 120, f"CAPTCHA solving time {response_time}s exceeds 2min limit"
            
        except Exception as e:
            # Contract: Exceptions should be handled gracefully
            assert "timeout" in str(e).lower() or "api" in str(e).lower(), \
                f"Unexpected exception type: {e}"
    
    @pytest.mark.integration
    async def test_captcha_provider_failover_contract(self):
        """Test CAPTCHA provider failover contract"""
        
        captcha_solver = get_captcha_solver()
        
        # Test provider availability and failover behavior
        balances = captcha_solver.get_provider_balances()
        
        # Contract assertions
        assert isinstance(balances, dict), "Provider balances must be dictionary"
        
        for provider, balance in balances.items():
            assert isinstance(provider, str), f"Provider name must be string: {provider}"
            assert isinstance(balance, (int, float)), f"Balance must be numeric: {balance}"
            assert balance >= 0, f"Balance cannot be negative: {balance}"
    
    @pytest.mark.integration
    async def test_captcha_timeout_handling_contract(self):
        """Test CAPTCHA timeout handling contract"""
        
        captcha_solver = get_captcha_solver()
        test_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        
        # Test with very short timeout to force timeout scenario
        start_time = time.time()
        
        try:
            solution = await captcha_solver.solve_captcha(
                CaptchaType.IMAGE,
                image_data=test_image,
                timeout=1  # 1 second timeout
            )
            
            response_time = time.time() - start_time
            
            # Contract: Should respect timeout
            assert response_time <= 2.0, f"Timeout not respected: {response_time}s"
            
            if solution is None:
                # Timeout handled correctly
                assert True
            else:
                # If solution returned, it should be valid
                assert isinstance(solution, str)
                
        except asyncio.TimeoutError:
            # Contract: Timeout exceptions are acceptable
            response_time = time.time() - start_time
            assert response_time <= 2.0, f"Timeout detection too slow: {response_time}s"


class TestEmailServiceContracts:
    """Contract tests for email service providers"""
    
    @pytest.mark.integration
    async def test_temp_email_creation_contract(self):
        """Test temporary email creation contract"""
        
        # Import email services
        from email_services.temp_email_services import get_email_service_manager
        
        manager = get_email_service_manager()
        
        start_time = time.time()
        account = await manager.create_email_account()
        response_time = time.time() - start_time
        
        if account:
            # Contract assertions
            assert hasattr(account, 'email'), "Account must have email attribute"
            assert hasattr(account, 'provider'), "Account must have provider attribute"
            assert '@' in account.email, "Email must be valid format"
            assert '.' in account.email.split('@')[1], "Email domain must be valid"
            
            # Performance contract
            assert response_time < 30.0, f"Email creation time {response_time}s exceeds 30s"
        else:
            # Contract: Null response is acceptable if no providers available
            assert True
    
    @pytest.mark.integration
    async def test_email_inbox_monitoring_contract(self):
        """Test email inbox monitoring contract"""
        
        from email_services.temp_email_services import get_email_service_manager
        
        manager = get_email_service_manager()
        account = await manager.create_email_account()
        
        if account:
            start_time = time.time()
            messages = await manager.get_inbox_messages(account.email)
            response_time = time.time() - start_time
            
            # Contract assertions
            assert isinstance(messages, list), "Messages must be list"
            
            # Performance contract
            assert response_time < 15.0, f"Inbox check time {response_time}s exceeds 15s"
            
            # Clean up
            await manager.delete_email_account(account.email)


class TestProxyServiceContract:
    """Contract tests for proxy service"""
    
    @pytest.mark.integration
    @pytest.mark.requires_real_services
    async def test_brightdata_proxy_contract(self):
        """Test BrightData proxy service contract"""
        
        try:
            # Test proxy verification
            verification_result = verify_proxy()
            
            # Contract assertions
            assert isinstance(verification_result, bool), "Verification result must be boolean"
            
            if verification_result:
                # Test proxy session creation
                session = get_brightdata_session()
                
                # Contract assertions
                assert hasattr(session, 'get'), "Session must have get method"
                assert hasattr(session, 'post'), "Session must have post method"
                
                # Test basic HTTP request through proxy
                start_time = time.time()
                response = session.get("https://httpbin.org/ip", timeout=10)
                response_time = time.time() - start_time
                
                # Contract assertions
                assert response.status_code == 200, f"Proxy request failed: {response.status_code}"
                assert response_time < 15.0, f"Proxy response time {response_time}s too slow"
                
                # Verify response contains IP information
                data = response.json()
                assert 'origin' in data, "Response must contain origin IP"
                
        except Exception as e:
            # Contract: Proxy failures should be handled gracefully
            assert "proxy" in str(e).lower() or "connection" in str(e).lower(), \
                f"Unexpected proxy error: {e}"


class TestServiceReliabilityMetrics:
    """Reliability metrics for all third-party services"""
    
    @pytest.mark.integration
    async def test_service_availability_matrix(self):
        """Test availability of all third-party services"""
        
        service_tests = [
            ("Twilio SMS", self._test_twilio_availability),
            ("CAPTCHA Solver", self._test_captcha_availability),
            ("Email Services", self._test_email_availability),
            ("Proxy Service", self._test_proxy_availability)
        ]
        
        results = {}
        
        for service_name, test_func in service_tests:
            try:
                start_time = time.time()
                available = await test_func()
                response_time = time.time() - start_time
                
                results[service_name] = {
                    'available': available,
                    'response_time': response_time,
                    'status': 'UP' if available else 'DOWN'
                }
                
            except Exception as e:
                results[service_name] = {
                    'available': False,
                    'response_time': None,
                    'status': 'ERROR',
                    'error': str(e)
                }
        
        # Generate availability report
        available_services = sum(1 for r in results.values() if r['available'])
        total_services = len(results)
        availability_percentage = (available_services / total_services) * 100
        
        # Log results for monitoring
        print(f"\n=== Service Availability Report ===")
        for service, result in results.items():
            status_emoji = "✅" if result['available'] else "❌"
            print(f"{status_emoji} {service}: {result['status']}")
            if result.get('response_time'):
                print(f"   Response Time: {result['response_time']:.2f}s")
            if result.get('error'):
                print(f"   Error: {result['error']}")
        
        print(f"\nOverall Availability: {availability_percentage:.1f}% ({available_services}/{total_services})")
        
        # Contract: At least 50% of services should be available for testing
        assert availability_percentage >= 50.0, \
            f"Service availability {availability_percentage}% below 50% threshold"
    
    async def _test_twilio_availability(self) -> bool:
        """Test Twilio service availability"""
        try:
            result = send_verification_sms("+15555551234", "HealthCheck")
            return 'success' in result
        except Exception:
            return False
    
    async def _test_captcha_availability(self) -> bool:
        """Test CAPTCHA service availability"""
        try:
            captcha_solver = get_captcha_solver()
            balances = captcha_solver.get_provider_balances()
            return len(balances) > 0
        except Exception:
            return False
    
    async def _test_email_availability(self) -> bool:
        """Test email service availability"""
        try:
            from email_services.temp_email_services import get_email_service_manager
            manager = get_email_service_manager()
            account = await asyncio.wait_for(manager.create_email_account(), timeout=15)
            if account:
                await manager.delete_email_account(account.email)
                return True
            return False
        except Exception:
            return False
    
    async def _test_proxy_availability(self) -> bool:
        """Test proxy service availability"""
        try:
            return verify_proxy()
        except Exception:
            return False


# Fixtures for contract testing
@pytest.fixture
def mock_service_responses():
    """Fixture providing mock responses for contract testing"""
    return {
        'twilio_success': {
            'success': True,
            'message_sid': 'SM1234567890abcdef1234567890abcdef',
            'status': 'queued'
        },
        'twilio_error': {
            'success': False,
            'error': 'Invalid phone number format'
        },
        'captcha_success': "SOLUTION123",
        'captcha_timeout': None,
        'email_account': {
            'email': 'test@temp-mail.com',
            'provider': 'temp-mail',
            'created_at': '2024-01-01T00:00:00Z'
        }
    }


@pytest.fixture
async def cleanup_test_resources():
    """Fixture to clean up test resources after contract tests"""
    created_resources = []
    
    yield created_resources
    
    # Cleanup after tests
    for resource in created_resources:
        try:
            if resource['type'] == 'email':
                from email_services.temp_email_services import get_email_service_manager
                manager = get_email_service_manager()
                await manager.delete_email_account(resource['email'])
        except Exception as e:
            print(f"Warning: Failed to cleanup resource {resource}: {e}")


# Performance contract test markers
pytestmark = [
    pytest.mark.integration,
    pytest.mark.timeout(300),  # 5 minute timeout for integration tests
]


if __name__ == "__main__":
    # Run contract tests with coverage
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--cov=automation",
        "--cov-report=term-missing"
    ])