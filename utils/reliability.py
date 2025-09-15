#!/usr/bin/env python3
"""
Reliability utilities: retry with backoff+jitter, simple token bucket rate limiter,
and lightweight circuit breaker.
"""

import time
import random
import threading
from typing import Callable, Any, Optional


def retry_with_backoff(func: Callable, *args, max_attempts: int = 3, base_delay: float = 0.5,
                      max_delay: float = 8.0, jitter: float = 0.25, **kwargs) -> Any:
    """Retry a callable with exponential backoff and jitter.
    Returns the function result or re-raises the last exception.
    """
    attempt = 0
    delay = base_delay
    while True:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            attempt += 1
            if attempt >= max_attempts:
                raise
            sleep_time = min(max_delay, delay * (2 ** (attempt - 1)))
            # Add +/- jitter fraction
            jitter_offset = sleep_time * jitter * (random.random() * 2 - 1)
            time.sleep(max(0.0, sleep_time + jitter_offset))


class TokenBucketRateLimiter:
    """Simple token bucket limiter for rate control.
    tokens refill at refill_rate per second, capacity is max_tokens.
    """
    def __init__(self, max_tokens: int, refill_rate: float):
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self.tokens = max_tokens
        self.last_refill = time.time()
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 1, timeout: float = 10.0) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                self._refill()
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True
            time.sleep(0.01)
        return False

    def _refill(self):
        now = time.time()
        elapsed = now - self.last_refill
        if elapsed <= 0:
            return
        refill = elapsed * self.refill_rate
        if refill > 0:
            self.tokens = min(self.max_tokens, self.tokens + refill)
            self.last_refill = now


class CircuitBreaker:
    """Basic circuit breaker: opens after failure_threshold within window_seconds,
    half-open after reset_timeout, closes on next success.
    """
    def __init__(self, failure_threshold: int = 5, window_seconds: float = 60.0,
                 reset_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.window_seconds = window_seconds
        self.reset_timeout = reset_timeout
        self._failures: list[float] = []
        self._state = 'closed'  # closed, open, half-open
        self._opened_at: Optional[float] = None
        self._lock = threading.Lock()

    def allow(self) -> bool:
        with self._lock:
            self._prune()
            if self._state == 'open':
                if self._opened_at and (time.time() - self._opened_at) >= self.reset_timeout:
                    self._state = 'half-open'
                    return True
                return False
            return True

    def record_success(self):
        with self._lock:
            self._failures.clear()
            self._state = 'closed'
            self._opened_at = None

    def record_failure(self):
        with self._lock:
            now = time.time()
            self._failures.append(now)
            self._prune()
            if len(self._failures) >= self.failure_threshold:
                self._state = 'open'
                self._opened_at = now

    def _prune(self):
        cutoff = time.time() - self.window_seconds
        self._failures = [t for t in self._failures if t >= cutoff]


