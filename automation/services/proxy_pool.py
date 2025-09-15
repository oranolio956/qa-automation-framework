"""
Proxy Pool: Keep-alive sessions, health scoring, simple rotation.
Integrates with requests via session factories and supports Bright Data or any HTTP proxy URL(s).
"""

from __future__ import annotations

import os
import random
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import requests


@dataclass
class ProxyEndpoint:
    url: str
    failures: int = 0
    last_latency_ms: float = -1.0
    last_checked: float = 0.0
    score: float = 0.0


class ProxyPool:
    def __init__(self, proxy_urls: Optional[List[str]] = None, keepalive: bool = True):
        self.proxy_urls = proxy_urls or self._load_from_env()
        self.keepalive = keepalive
        self._lock = threading.Lock()
        self._endpoints: List[ProxyEndpoint] = [ProxyEndpoint(url=u) for u in self.proxy_urls]
        self._sessions: Dict[str, requests.Session] = {}

    def _load_from_env(self) -> List[str]:
        urls: List[str] = []
        # Support multiple comma-separated proxies or single BRIGHTDATA_PROXY_URL
        env_multi = os.environ.get("PROXY_URLS", "").strip()
        if env_multi:
            urls.extend([u.strip() for u in env_multi.split(",") if u.strip()])
        env_single = os.environ.get("BRIGHTDATA_PROXY_URL", "").strip()
        if env_single:
            urls.append(env_single)
        return urls

    def _get_or_create_session(self, ep: ProxyEndpoint) -> requests.Session:
        if not self.keepalive:
            sess = requests.Session()
        else:
            with self._lock:
                sess = self._sessions.get(ep.url)
                if not sess:
                    sess = requests.Session()
                    self._sessions[ep.url] = sess
        if ep.url:
            sess.proxies = {"http": ep.url, "https": ep.url}
        sess.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari'
        })
        return sess

    def choose(self) -> Optional[ProxyEndpoint]:
        with self._lock:
            if not self._endpoints:
                return None
            # Sort by (failures, latency) and randomize within similar scores to avoid stickiness
            candidates = list(self._endpoints)
            random.shuffle(candidates)
            candidates.sort(key=lambda e: (e.failures, e.last_latency_ms if e.last_latency_ms > 0 else 1e9))
            return candidates[0]

    def session(self) -> Optional[requests.Session]:
        ep = self.choose()
        if not ep:
            return None
        return self._get_or_create_session(ep)

    def record_result(self, ep: ProxyEndpoint, ok: bool, latency_ms: float):
        with self._lock:
            ep.last_latency_ms = latency_ms
            ep.last_checked = time.time()
            if ok:
                ep.failures = max(0, ep.failures - 1)
            else:
                ep.failures += 1


_singleton: Optional[ProxyPool] = None


def get_proxy_pool() -> ProxyPool:
    global _singleton
    if _singleton is None:
        _singleton = ProxyPool()
    return _singleton


