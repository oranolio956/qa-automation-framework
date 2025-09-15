#!/usr/bin/env python3
"""
CAPTCHA Integration Interface for Snapchat Automation

Provides a clean interface to integrate with existing anti-detection CAPTCHA handlers.
"""

import logging
from typing import Dict, Any, Optional, Protocol
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class CaptchaHandlerProtocol(Protocol):
    """Protocol for CAPTCHA handler implementations"""
    
    def detect_captcha(self, screenshot_path: str) -> Dict[str, Any]:
        """Detect if CAPTCHA is present in screenshot"""
        ...
    
    def detect_arkose_challenge(self, screenshot_path: str) -> Dict[str, Any]:
        """Detect Arkose challenge in screenshot"""
        ...


class CaptchaIntegrationManager:
    """Manages CAPTCHA detection and integration with automation flows"""
    
    def __init__(self, captcha_handler: Optional[CaptchaHandlerProtocol] = None):
        self.captcha_handler = captcha_handler
        self._detection_enabled = captcha_handler is not None
        
        if self._detection_enabled:
            logger.info("CAPTCHA detection enabled")
        else:
            logger.warning("CAPTCHA detection disabled - no handler provided")
    
    def detect_challenges(self, screenshot_path: str) -> Dict[str, Any]:
        """Comprehensive CAPTCHA/challenge detection"""
        if not self._detection_enabled:
            return {'detected': False, 'reason': 'CAPTCHA detection disabled'}
        
        try:
            # Check for regular CAPTCHA
            captcha_result = self.captcha_handler.detect_captcha(screenshot_path)
            if captcha_result.get('detected'):
                return {
                    'detected': True,
                    'type': 'captcha',
                    'confidence': captcha_result.get('confidence', 0.5),
                    'requires_manual': True,
                    'details': captcha_result,
                    'screenshot_path': screenshot_path
                }
            
            # Check for Arkose challenge
            arkose_result = self.captcha_handler.detect_arkose_challenge(screenshot_path)
            if arkose_result.get('detected'):
                return {
                    'detected': True,
                    'type': 'arkose',
                    'confidence': arkose_result.get('confidence', 0.5),
                    'requires_manual': True,
                    'details': arkose_result,
                    'screenshot_path': screenshot_path
                }
            
            return {'detected': False, 'screenshot_analyzed': True}
            
        except Exception as e:
            logger.error(f"CAPTCHA detection error: {e}")
            return {
                'detected': False,
                'error': str(e),
                'screenshot_path': screenshot_path
            }
    
    def should_check_for_captcha(self, context: str, attempt_count: int = 0) -> bool:
        """Determine if CAPTCHA check should be performed based on context"""
        if not self._detection_enabled:
            return False
        
        # Define contexts where CAPTCHA is more likely
        high_risk_contexts = [
            'sign_up',
            'username_entry',
            'phone_verification',
            'multiple_failures'
        ]
        
        # Check on first attempt for high-risk contexts
        if context in high_risk_contexts and attempt_count == 0:
            return True
        
        # Check after multiple failures
        if attempt_count >= 2:
            return True
        
        return False
    
    def handle_detected_captcha(self, detection_result: Dict[str, Any]) -> Dict[str, Any]:
        """Handle detected CAPTCHA/challenge"""
        if not detection_result.get('detected'):
            return {'action': 'continue', 'message': 'No CAPTCHA detected'}
        
        captcha_type = detection_result.get('type', 'unknown')
        confidence = detection_result.get('confidence', 0.0)
        
        logger.warning(f"CAPTCHA detected: {captcha_type} (confidence: {confidence:.2f})")
        
        # For now, all CAPTCHAs require manual intervention
        # This could be extended to support automated solvers
        if detection_result.get('requires_manual', True):
            return {
                'action': 'manual_intervention',
                'message': f'{captcha_type.title()} challenge detected - manual intervention required',
                'details': detection_result,
                'next_steps': [
                    'Pause automation',
                    'Notify operator',
                    'Wait for manual resolution',
                    'Resume automation'
                ]
            }
        
        # Future: automated solving logic would go here
        return {
            'action': 'automated_solve',
            'message': f'Attempting automated {captcha_type} solving',
            'details': detection_result
        }
    
    def get_detection_stats(self) -> Dict[str, Any]:
        """Get CAPTCHA detection statistics"""
        # This would be implemented with actual tracking
        return {
            'detection_enabled': self._detection_enabled,
            'handler_available': self.captcha_handler is not None,
            'total_checks': 0,  # Would track actual usage
            'captchas_detected': 0,  # Would track detections
            'manual_interventions': 0  # Would track manual cases
        }


def create_captcha_integration(anti_detection_system=None) -> CaptchaIntegrationManager:
    """Create CAPTCHA integration from existing anti-detection system"""
    try:
        if anti_detection_system and hasattr(anti_detection_system, 'captcha_handler'):
            captcha_handler = anti_detection_system.captcha_handler
            return CaptchaIntegrationManager(captcha_handler)
        else:
            logger.warning("No CAPTCHA handler found in anti-detection system")
            return CaptchaIntegrationManager(None)
    except Exception as e:
        logger.error(f"Failed to create CAPTCHA integration: {e}")
        return CaptchaIntegrationManager(None)


def get_captcha_integration(anti_detection_system=None) -> CaptchaIntegrationManager:
    """Get or create CAPTCHA integration instance"""
    # Global instance could be cached here if needed
    return create_captcha_integration(anti_detection_system)


if __name__ == "__main__":
    # Test CAPTCHA integration
    integration = CaptchaIntegrationManager(None)
    
    print("CAPTCHA Integration Test:")
    print(f"Detection enabled: {integration._detection_enabled}")
    
    # Test detection logic using configuration
    try:
        from .config import get_config
    except ImportError:
        from config import get_config
    config = get_config()
    fake_screenshot = config.get_temp_file_path("test_screenshot.png")
    result = integration.detect_challenges(fake_screenshot)
    print(f"Detection result: {result}")
    
    # Test context logic
    contexts = ['sign_up', 'username_entry', 'normal_flow']
    for context in contexts:
        should_check = integration.should_check_for_captcha(context, 0)
        print(f"Should check CAPTCHA for '{context}': {should_check}")
    
    # Test stats
    stats = integration.get_detection_stats()
    print(f"Detection stats: {stats}")