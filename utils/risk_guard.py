#!/usr/bin/env python3
"""
Risk scoring, anomaly guard, and global kill switch.

- Records key events and computes simple anomaly/risk scores
- Exposes a kill switch backed by Redis with in-memory fallback
"""

import os
import time
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

import redis


logger = logging.getLogger(__name__)


@dataclass
class RiskStatus:
    kill_switch: bool
    anomaly_score: float
    last_minute_errors: int
    last_minute_requests: int


class RiskGuard:
    def __init__(self, redis_url: Optional[str] = None, ns: str = "risk"):
        self.ns = ns
        self.redis_url = redis_url or os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        self.r = None
        self._kill_switch_mem = False
        self._connect()

        # thresholds (tunable)
        self.error_rate_threshold = 0.35  # 35% failures in last minute
        self.min_events_window = 10
        self.canary_min_success = 0.6

    def _connect(self):
        try:
            self.r = redis.from_url(self.redis_url, decode_responses=True, max_connections=20, socket_keepalive=True, retry_on_timeout=True)
            self.r.ping()
        except Exception as e:
            logger.warning(f"RiskGuard Redis degraded: {e}")
            self.r = None

    def _k(self, suffix: str) -> str:
        return f"{self.ns}:{suffix}"

    def record_event(self, event_name: str, attributes: Dict[str, Any]):
        ts_bucket = int(time.time() // 60)  # minute bucket
        try:
            if self.r:
                self.r.hincrby(self._k(f"events:{ts_bucket}"), f"count:{event_name}", 1)
                if attributes.get('error'):
                    self.r.hincrby(self._k(f"events:{ts_bucket}"), f"error:{event_name}", 1)
                # Keep only last 10 buckets
                self.r.expire(self._k(f"events:{ts_bucket}"), 900)
        except Exception:
            pass

    def compute_anomaly_score(self) -> float:
        if not self.r:
            return 0.0
        try:
            now_bucket = int(time.time() // 60)
            buckets = [self._k(f"events:{b}") for b in range(now_bucket - 1, now_bucket + 1)]
            total = 0
            errors = 0
            for k in buckets:
                data = self.r.hgetall(k)
                for field, val in data.items():
                    if field.startswith('count:'):
                        total += int(val)
                    elif field.startswith('error:'):
                        errors += int(val)
            if total == 0:
                return 0.0
            return min(1.0, errors / max(1, total))
        except Exception:
            return 0.0

    def should_pause_for_canary(self, success_ratio: float) -> bool:
        return success_ratio < self.canary_min_success

    def check_kill_switch(self) -> bool:
        try:
            if self.r:
                v = self.r.get(self._k('kill_switch'))
                return v == '1'
        except Exception:
            pass
        return self._kill_switch_mem

    def set_kill_switch(self, on: bool):
        self._kill_switch_mem = bool(on)
        try:
            if self.r:
                self.r.set(self._k('kill_switch'), '1' if on else '0', ex=3600 if on else 600)
        except Exception:
            pass

    def get_status(self) -> RiskStatus:
        score = self.compute_anomaly_score()
        if not self.r:
            return RiskStatus(self._kill_switch_mem, score, 0, 0)
        try:
            now_bucket = int(time.time() // 60)
            data = self.r.hgetall(self._k(f"events:{now_bucket}"))
            total = sum(int(v) for f, v in data.items() if f.startswith('count:'))
            errs = sum(int(v) for f, v in data.items() if f.startswith('error:'))
            return RiskStatus(self.check_kill_switch(), score, errs, total)
        except Exception:
            return RiskStatus(self.check_kill_switch(), score, 0, 0)

    def compute_account_risk(self, context: Dict[str, Any]) -> float:
        # Simple heuristic: SMS retries, emulator failures, verification failures, proxy anomalies
        risk = 0.0
        sms_retries = int(context.get('sms_retries', 0))
        emulator_fail = 1 if context.get('emulator_failed') else 0
        verify_fail = 1 if (context.get('verified') is False) else 0
        proxy_flag = 1 if context.get('proxy_datacenter') else 0

        risk += min(0.4, sms_retries * 0.1)
        risk += emulator_fail * 0.2
        risk += verify_fail * 0.3
        risk += proxy_flag * 0.1
        return max(0.0, min(1.0, risk))


_rg: Optional[RiskGuard] = None


def get_risk_guard() -> RiskGuard:
    global _rg
    if _rg is None:
        _rg = RiskGuard()
    return _rg


