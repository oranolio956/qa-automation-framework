#!/usr/bin/env python3
"""
Email automation package
Provides email creation and CAPTCHA solving services
"""

__version__ = "1.0.0"

# Import main email services
try:
    from .business_email_service import BusinessEmailService
    from .temp_email_services import TempEmailManager
    from .captcha_solver import CaptchaSolver
except ImportError as e:
    # Handle import errors gracefully
    print(f"Warning: Some email modules could not be imported: {e}")

__all__ = [
    'BusinessEmailService',
    'TempEmailManager',
    'CaptchaSolver'
]