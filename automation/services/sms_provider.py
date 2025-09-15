"""
Twilio-only SMS Provider

Provides a minimal interface for acquiring a phone number and polling for
verification codes via Twilio. Designed to integrate with existing flows
that expect a simple pool/get/release and code polling.

Environment variables used:
  - TWILIO_ACCOUNT_SID
  - TWILIO_AUTH_TOKEN
  - TWILIO_NUMBER_POOL           (comma-separated list of E.164 numbers)
  - TWILIO_FROM_NUMBER           (optional, for sending; not required here)
  - METRICS_ENABLED              (optional)
  - REDIS_URL                    (optional; not required for basic use)
  - TWILIO_AUTOBUY_ENABLED       (optional; 'true' to enable auto-purchase)
  - TWILIO_BUY_COUNTRY           (default: 'US')
  - TWILIO_BUY_TYPE              (default: 'local', options: local, mobile, tollfree)
  - TWILIO_BUY_AREA_CODE         (optional; prefer this area code if available)
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from twilio.rest import Client

try:
    from utils.metrics import counter, histogram
except Exception:  # metrics are optional
    def counter(*args, **kwargs):
        class _Nop:
            def inc(self, *a, **k):
                return None
        return _Nop()

    def histogram(*args, **kwargs):
        class _Nop:
            def observe(self, *a, **k):
                return None
        return _Nop()


_acquire_counter = counter("sms_numbers_acquired_total", "Total SMS numbers acquired (Twilio)")
_acquire_fail_counter = counter("sms_number_acquire_failures_total", "Total SMS number acquire failures (Twilio)")
_code_wait_hist = histogram("sms_code_wait_seconds", "Seconds spent waiting for SMS verification code")
_code_parse_counter = counter("sms_codes_parsed_total", "Total verification codes parsed from SMS")


CODE_REGEX = re.compile(r"\b(\d{4,8})\b")


@dataclass
class SMSNumber:
    phone_number: str
    provider: str = "twilio"


class TwilioSMSProvider:
    def __init__(self):
        sid = os.environ.get("TWILIO_ACCOUNT_SID")
        token = os.environ.get("TWILIO_AUTH_TOKEN")
        if not sid or not token:
            raise RuntimeError("Twilio credentials not configured (TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN)")
        self.client = Client(sid, token)

        pool_env = os.environ.get("TWILIO_NUMBER_POOL", "").strip()
        self.number_pool: List[str] = [n.strip() for n in pool_env.split(",") if n.strip()]
        self._leased: Dict[str, float] = {}
        self._autopurchased_sid: Dict[str, str] = {}

        # Auto-purchase config
        self.autobuy_enabled: bool = (os.environ.get("TWILIO_AUTOBUY_ENABLED", "false").lower() in {"1", "true", "yes"})
        self.buy_country: str = os.environ.get("TWILIO_BUY_COUNTRY", "US").upper()
        self.buy_type: str = os.environ.get("TWILIO_BUY_TYPE", "local").lower()
        self.buy_area_code: Optional[str] = os.environ.get("TWILIO_BUY_AREA_CODE")

    def get_number(self) -> Dict[str, object]:
        """Return {'success': bool, 'phone_number': str, 'message': str}.

        Strategy:
          1) Use TWILIO_NUMBER_POOL if provided, choose a number not leased.
          2) Otherwise, list incoming Twilio numbers and return the first SMS-capable number.
        """
        try:
            # 1) Preferred path: configured pool
            for num in self.number_pool:
                if num not in self._leased:
                    self._leased[num] = time.time()
                    _acquire_counter.inc()
                    return {"success": True, "phone_number": num, "message": "from configured pool"}

            # 2) Fallback: discover existing incoming numbers on account
            incoming = self.client.incoming_phone_numbers.list(limit=20)
            for rec in incoming:
                num = rec.phone_number
                # Simple lease protection
                if num not in self._leased:
                    self._leased[num] = time.time()
                    _acquire_counter.inc()
                    return {"success": True, "phone_number": num, "message": "from Twilio incoming numbers"}

            # 3) Auto-purchase if enabled
            if self.autobuy_enabled:
                purchased = self._auto_purchase_number()
                if purchased:
                    phone_number, sid = purchased
                    self._leased[phone_number] = time.time()
                    self._autopurchased_sid[phone_number] = sid
                    _acquire_counter.inc()
                    return {"success": True, "phone_number": phone_number, "message": "autopurchased"}

            _acquire_fail_counter.inc()
            return {"success": False, "message": "no available numbers"}
        except Exception as e:
            _acquire_fail_counter.inc()
            return {"success": False, "message": f"error acquiring number: {e}"}

    def release_number(self, phone_number: str) -> bool:
        self._leased.pop(phone_number, None)
        # If the number was purchased by us, release it from Twilio to avoid recurring charges
        sid = self._autopurchased_sid.pop(phone_number, None)
        if sid:
            try:
                self.client.incoming_phone_numbers(sid).delete()
                return True
            except Exception:
                # If delete by SID failed, try best-effort lookup by number
                try:
                    matches = self.client.incoming_phone_numbers.list(phone_number=phone_number, limit=1)
                    if matches:
                        self.client.incoming_phone_numbers(matches[0].sid).delete()
                        return True
                except Exception:
                    return False
        return True

    def wait_for_code(self, phone_number: str, timeout_seconds: int = 180, poll_seconds: int = 4) -> Optional[str]:
        """Poll Twilio inbound messages to the given phone number and parse a verification code."""
        start = time.time()
        try:
            while (time.time() - start) < timeout_seconds:
                # Fetch recent inbound messages to this number
                msgs = self.client.messages.list(to=phone_number, limit=20)
                for m in msgs:
                    body = (m.body or "").strip()
                    if not body:
                        continue
                    match = CODE_REGEX.search(body)
                    if match:
                        code = match.group(1)
                        _code_parse_counter.inc()
                        _code_wait_hist.observe(time.time() - start)
                        return code
                time.sleep(poll_seconds)
        except Exception:
            pass
        _code_wait_hist.observe(time.time() - start)
        return None


    def _auto_purchase_number(self) -> Optional[tuple[str, str]]:
        """Attempt to search and purchase an SMS-capable number.

        Returns (phone_number, sid) on success, None on failure.
        """
        try:
            # Select the number search collection based on type
            search = self.client.available_phone_numbers(self.buy_country)
            if self.buy_type == "mobile":
                collection = search.mobile
            elif self.buy_type == "tollfree":
                collection = search.toll_free
            else:
                collection = search.local

            kwargs = {"sms_enabled": True}
            if self.buy_area_code:
                # Twilio expects int for area_code for local numbers
                try:
                    kwargs["area_code"] = int(self.buy_area_code)
                except Exception:
                    pass
            # Fetch one candidate
            candidates = collection.list(limit=1, **kwargs)
            if not candidates:
                return None
            candidate = candidates[0]
            purchased = self.client.incoming_phone_numbers.create(phone_number=candidate.phone_number)
            return purchased.phone_number, purchased.sid
        except Exception:
            return None


_singleton: Optional[TwilioSMSProvider] = None


def get_twilio_sms_provider() -> TwilioSMSProvider:
    global _singleton
    if _singleton is None:
        _singleton = TwilioSMSProvider()
    return _singleton


