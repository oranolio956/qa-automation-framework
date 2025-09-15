#!/usr/bin/env python3
"""
Tenant isolation helpers and namespacing.
"""

import os


def get_tenant_namespace(user_id: int) -> str:
    # Basic namespace by user_id; in production this could map to org/team
    return f"tenant:{user_id}"


def namespace_key(user_id: int, key: str) -> str:
    return f"{get_tenant_namespace(user_id)}:{key}"


