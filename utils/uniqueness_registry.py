#!/usr/bin/env python3
"""
Registry to avoid reusing the same avatars/bitmoji/display names across tenants.
Backed by Redis set with TTLs.
"""

import os
import redis
import logging
from typing import Optional
from datetime import datetime


logger = logging.getLogger(__name__)


class UniquenessRegistry:
    def __init__(self, redis_url: Optional[str] = None, ns: str = "uniq"):
        self.ns = ns
        self.redis_url = redis_url or os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        self.r = None
        try:
            self.r = redis.from_url(self.redis_url, decode_responses=True, max_connections=10, socket_keepalive=True, retry_on_timeout=True)
            self.r.ping()
        except Exception as e:
            logger.warning(f"UniquenessRegistry degraded: {e}")
            self.r = None

    def _k(self, kind: str) -> str:
        return f"{self.ns}:{kind}"

    def claim(self, kind: str, value: str, ttl_seconds: int = 86400 * 90) -> bool:
        if not self.r:
            return True
        key = self._k(kind)
        try:
            added = self.r.sadd(key, value)
            if added == 1:
                self.r.expire(key, ttl_seconds)
                return True
            return False
        except Exception:
            return True


_ur: Optional[UniquenessRegistry] = None


def get_uniqueness_registry() -> UniquenessRegistry:
    global _ur
    if _ur is None:
        _ur = UniquenessRegistry()
    return _ur


