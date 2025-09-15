#!/usr/bin/env python3
"""
Shim module to provide get_android_orchestrator for code expecting
automation.android.automation_orchestrator while the implementation lives in
automation_orchestrator_fixed.py.
"""

from .automation_orchestrator_fixed import AndroidAutomationOrchestrator


def get_android_orchestrator(max_concurrent_sessions: int = 3) -> AndroidAutomationOrchestrator:
    return AndroidAutomationOrchestrator(max_concurrent_sessions=max_concurrent_sessions)