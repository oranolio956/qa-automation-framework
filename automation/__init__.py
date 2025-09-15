#!/usr/bin/env python3
"""
Automation Package
Main package for the Tinder automation system
"""

__version__ = "1.0.0"
__author__ = "Automation System"

# Import core components
try:
    from .core.anti_detection import get_anti_detection_system, AntiDetectionSystem
    from .email.captcha_solver import CaptchaSolver
    from .snapchat.stealth_creator import SnapchatStealthCreator
except ImportError as e:
    print(f"Warning: Some automation modules could not be imported: {e}")

__all__ = [
    'get_anti_detection_system',
    'AntiDetectionSystem', 
    'CaptchaSolver',
    'SnapchatStealthCreator'
]