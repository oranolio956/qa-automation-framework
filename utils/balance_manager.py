#!/usr/bin/env python3
"""
Redis-backed per-user balance manager with optional FREE_TEST_MODE bypass.

Amounts are tracked in integer cents to avoid floating-point precision issues.
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

import redis


logger = logging.getLogger(__name__)


def _to_cents(amount_usd: float) -> int:
    try:
        return int(round(float(amount_usd) * 100))
    except Exception:
        return 0


def _from_cents(amount_cents: int) -> float:
    return round((amount_cents or 0) / 100.0, 2)


class BalanceManager:
    """Manages user balances and a simple ledger in Redis."""

    def __init__(self, redis_url: Optional[str] = None, namespace: str = "user_balance"):
        self.redis_url = redis_url or os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        self.ns = namespace
        self.r = None
        self._connect()

    def _connect(self):
        try:
            client_kwargs = dict(decode_responses=True, max_connections=20, socket_keepalive=True, retry_on_timeout=True)
            # Let rediss:// implicitly enable TLS without custom kwargs to avoid platform issues
            self.r = redis.from_url(self.redis_url, **client_kwargs)
            self.r.ping()
        except Exception as e:
            logger.warning(f"BalanceManager Redis degraded: {e}")
            self.r = None

    def _key_balance(self, user_id: int) -> str:
        return f"{self.ns}:balance:{user_id}"

    def _key_ledger(self, user_id: int) -> str:
        return f"{self.ns}:ledger:{user_id}"

    def get_balance_cents(self, user_id: int) -> int:
        if not self.r:
            # Degraded: report 0 but FREE_TEST_MODE may bypass
            return 0
        try:
            val = self.r.get(self._key_balance(user_id))
            return int(val or 0)
        except Exception as e:
            logger.warning(f"get_balance_cents error: {e}")
            return 0

    def get_balance(self, user_id: int) -> float:
        return _from_cents(self.get_balance_cents(user_id))

    def _append_ledger(self, user_id: int, entry: Dict[str, Any]):
        if not self.r:
            return
        try:
            self.r.lpush(self._key_ledger(user_id), json.dumps(entry))
            self.r.ltrim(self._key_ledger(user_id), 0, 499)  # keep last 500 entries
        except Exception as e:
            logger.debug(f"ledger append error: {e}")

    def add_funds(self, user_id: int, amount_usd: float, source: str, reference: Optional[str] = None) -> bool:
        amount_cents = _to_cents(amount_usd)
        if amount_cents <= 0:
            return False
        if not self.r:
            return False
        try:
            pipe = self.r.pipeline()
            pipe.incrby(self._key_balance(user_id), amount_cents)
            pipe.execute()
            self._append_ledger(user_id, {
                'ts': datetime.utcnow().isoformat(),
                'type': 'credit',
                'amount_cents': amount_cents,
                'amount_usd': _from_cents(amount_cents),
                'source': source,
                'ref': reference,
            })
            return True
        except Exception as e:
            logger.error(f"add_funds error: {e}")
            return False

    def deduct(self, user_id: int, amount_usd: float, reason: str, allow_negative: bool = False) -> bool:
        amount_cents = _to_cents(amount_usd)
        if amount_cents <= 0:
            return True
        if not self.r:
            return allow_negative  # degraded
        try:
            key = self._key_balance(user_id)
            with self.r.pipeline() as pipe:
                while True:
                    try:
                        pipe.watch(key)
                        current = int(pipe.get(key) or 0)
                        new_val = current - amount_cents
                        if new_val < 0 and not allow_negative:
                            pipe.unwatch()
                            return False
                        pipe.multi()
                        pipe.set(key, new_val)
                        pipe.execute()
                        break
                    except redis.WatchError:
                        continue
            self._append_ledger(user_id, {
                'ts': datetime.utcnow().isoformat(),
                'type': 'debit',
                'amount_cents': amount_cents,
                'amount_usd': _from_cents(amount_cents),
                'reason': reason,
            })
            return True
        except Exception as e:
            logger.error(f"deduct error: {e}")
            return False

    def get_ledger(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        if not self.r:
            return []
        try:
            raw = self.r.lrange(self._key_ledger(user_id), 0, max(0, limit - 1))
            return [json.loads(x) for x in raw]
        except Exception as e:
            logger.debug(f"get_ledger error: {e}")
            return []

    @staticmethod
    def is_free_mode() -> bool:
        return str(os.environ.get('FREE_TEST_MODE', '0')).strip() in ('1', 'true', 'yes', 'on')


_global_balance_manager: Optional[BalanceManager] = None


def get_balance_manager() -> BalanceManager:
    global _global_balance_manager
    if _global_balance_manager is None:
        _global_balance_manager = BalanceManager()
    return _global_balance_manager


