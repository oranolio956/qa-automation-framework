#!/usr/bin/env python3
"""
Utils package initialization
Provides utility functions for the automation system
"""

__version__ = "1.0.0"
__author__ = "Automation System"

# Import main utility functions
try:
    from .brightdata_proxy import get_brightdata_session, verify_proxy, get_proxy_info
    from .sms_verifier import get_sms_verifier
    from .twilio_pool import TwilioPhonePool as TwilioPool
except ImportError as e:
    # Handle import errors gracefully
    print(f"Warning: Some utils modules could not be imported: {e}")

__all__ = [
    'get_brightdata_session',
    'verify_proxy', 
    'get_proxy_info',
    'get_sms_verifier',
    'TwilioPool'
]