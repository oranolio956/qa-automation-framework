"""
CAPTCHA Solver Interface with 2Captcha implementation (optional).
"""

from __future__ import annotations

import os
import time
from typing import Optional, Dict, Any

import requests


class CaptchaSolver:
    def solve_recaptcha_v2(self, site_key: str, page_url: str, timeout: int = 180) -> Optional[str]:
        raise NotImplementedError


class TwoCaptchaSolver(CaptchaSolver):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get('TWOCAPTCHA_API_KEY')
        if not self.api_key:
            raise RuntimeError('2Captcha API key not configured (TWOCAPTCHA_API_KEY)')

    def solve_recaptcha_v2(self, site_key: str, page_url: str, timeout: int = 180) -> Optional[str]:
        # Submit
        in_url = 'http://2captcha.com/in.php'
        params = {
            'key': self.api_key,
            'method': 'userrecaptcha',
            'googlekey': site_key,
            'pageurl': page_url,
            'json': 1,
        }
        r = requests.get(in_url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        if data.get('status') != 1:
            return None
        req_id = data.get('request')

        # Poll
        res_url = 'http://2captcha.com/res.php'
        start = time.time()
        while (time.time() - start) < timeout:
            rr = requests.get(res_url, params={'key': self.api_key, 'action': 'get', 'id': req_id, 'json': 1}, timeout=30)
            rr.raise_for_status()
            rd = rr.json()
            if rd.get('status') == 1:
                return rd.get('request')  # g-recaptcha-response token
            time.sleep(5)
        return None


_captcha_singleton: Optional[CaptchaSolver] = None


def get_captcha_solver() -> Optional[CaptchaSolver]:
    global _captcha_singleton
    if _captcha_singleton is not None:
        return _captcha_singleton
    # Enable only if API key present
    if os.environ.get('TWOCAPTCHA_API_KEY'):
        _captcha_singleton = TwoCaptchaSolver()
    else:
        _captcha_singleton = None
    return _captcha_singleton


