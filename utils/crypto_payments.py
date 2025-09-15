#!/usr/bin/env python3
"""
Crypto payments via Coinbase Commerce.

Functions:
- create_charge(user_id, amount_usd, description) -> {hosted_url, charge_id}
- handle_webhook(signature, raw_body) -> (ok: bool, message: str)

In FREE_TEST_MODE, charges are simulated and funds are credited immediately.
"""

import os
import hmac
import json
import logging
from hashlib import sha256
from typing import Optional, Tuple, Dict, Any
from datetime import datetime

import httpx
import redis

from .balance_manager import get_balance_manager, _to_cents, _from_cents


logger = logging.getLogger(__name__)


COINBASE_API_BASE = "https://api.commerce.coinbase.com"


def _get_redis_client() -> Optional[redis.Redis]:
    try:
        url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        return redis.from_url(url, decode_responses=True, max_connections=10, socket_keepalive=True, retry_on_timeout=True)
    except Exception as e:
        logger.warning(f"CryptoPayments Redis degraded: {e}")
        return None


def _charges_key(charge_id: str) -> str:
    return f"crypto:charge:{charge_id}"


async def create_charge(user_id: int, amount_usd: float, description: str = "Account top-up") -> Dict[str, Any]:
    bm = get_balance_manager()
    if bm.is_free_mode():
        # Simulate success and credit immediately
        credited = bm.add_funds(user_id, amount_usd, source="free_mode", reference="test-credit")
        return {
            'simulated': True,
            'credited': bool(credited),
            'hosted_url': "https://example.com/test-mode",
            'charge_id': f"test_{int(datetime.utcnow().timestamp())}",
            'message': f"Free mode: credited ${amount_usd:.2f} to your balance."
        }

    api_key = os.environ.get('COINBASE_COMMERCE_API_KEY')
    if not api_key:
        raise RuntimeError("COINBASE_COMMERCE_API_KEY not set")

    headers = {
        'X-CC-Api-Key': api_key,
        'X-CC-Version': '2018-03-22',
        'Content-Type': 'application/json',
    }

    redirect_url = os.environ.get('PAYMENTS_REDIRECT_URL')
    cancel_url = os.environ.get('PAYMENTS_CANCEL_URL')

    payload = {
        'name': 'Account Top-up',
        'description': description,
        'pricing_type': 'fixed_price',
        'local_price': {
            'amount': f"{amount_usd:.2f}",
            'currency': 'USD'
        },
        'metadata': {
            'user_id': str(user_id)
        }
    }
    if redirect_url:
        payload['redirect_url'] = redirect_url
    if cancel_url:
        payload['cancel_url'] = cancel_url

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(f"{COINBASE_API_BASE}/charges", headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    charge = data.get('data', {})
    charge_id = charge.get('id')
    hosted_url = charge.get('hosted_url')

    # Store pending charge to map back on webhook
    r = _get_redis_client()
    if r and charge_id:
        try:
            r.hset(_charges_key(charge_id), mapping={
                'user_id': str(user_id),
                'amount_cents': str(_to_cents(amount_usd)),
                'created_at': datetime.utcnow().isoformat(),
                'status': 'pending'
            })
            r.expire(_charges_key(charge_id), 86400 * 7)
        except Exception as e:
            logger.warning(f"Failed to store pending charge: {e}")

    return {
        'simulated': False,
        'hosted_url': hosted_url,
        'charge_id': charge_id
    }


def _verify_signature(signature: str, raw_body: bytes) -> bool:
    secret = os.environ.get('COINBASE_COMMERCE_WEBHOOK_SECRET')
    if not secret:
        logger.warning("Webhook secret not configured")
        return False
    try:
        computed = hmac.new(secret.encode('utf-8'), raw_body, sha256).hexdigest()
        return hmac.compare_digest(computed, signature)
    except Exception:
        return False


def handle_webhook(signature: str, raw_body: bytes) -> Tuple[bool, str]:
    if get_balance_manager().is_free_mode():
        return True, "Free mode: webhook ignored"

    if not _verify_signature(signature, raw_body):
        return False, "invalid signature"
    try:
        payload = json.loads(raw_body.decode('utf-8'))
    except Exception:
        return False, "invalid json"

    event = payload.get('event') or payload  # be tolerant
    event_type = event.get('type', '')
    data = event.get('data', {})
    charge_id = data.get('id')

    # Only credit on confirmed/resolved paid events
    should_credit = event_type in ("charge:confirmed", "charge:resolved", "charge:paid")
    if not should_credit or not charge_id:
        return True, f"ignored event {event_type}"

    r = _get_redis_client()
    user_id = None
    amount_cents = None
    if r:
        try:
            info = r.hgetall(_charges_key(charge_id))
            if info:
                user_id = int(info.get('user_id')) if info.get('user_id') else None
                amount_cents = int(info.get('amount_cents')) if info.get('amount_cents') else None
        except Exception as e:
            logger.warning(f"lookup charge error: {e}")

    # Fallback to metadata in webhook
    if not user_id:
        meta = data.get('metadata') or {}
        try:
            user_id = int(meta.get('user_id')) if meta.get('user_id') else None
        except Exception:
            user_id = None

    # Fallback amount from pricing.local if not stored
    if amount_cents is None:
        try:
            local = (data.get('pricing') or {}).get('local') or {}
            amount_cents = _to_cents(float(local.get('amount', '0')))
        except Exception:
            amount_cents = 0

    if not user_id or amount_cents <= 0:
        return False, "missing user or amount"

    amount = _from_cents(amount_cents)
    bm = get_balance_manager()
    ok = bm.add_funds(user_id, amount, source="coinbase", reference=charge_id)
    if ok and r:
        try:
            r.hset(_charges_key(charge_id), mapping={'status': 'credited', 'credited_at': datetime.utcnow().isoformat()})
        except Exception:
            pass
    return ok, ("credited" if ok else "credit failed")


