#!/usr/bin/env python3
"""
Test package initialization
Provides test utilities and configuration
"""

__version__ = "1.0.0"

# Test configuration
import os
import sys

# Add parent directories to path for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(PARENT_DIR)

if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

__all__ = []