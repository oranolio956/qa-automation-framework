#!/usr/bin/env python3
"""
Farm Connector: Multi-host Android farm connectivity with exponential backoff and simple
circuit-breaking. Provides a CLI for quick validation and a Python API for integrations.
"""

from __future__ import annotations

import argparse
import logging
import os
import random
import socket
import time
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s")


@dataclass
class Endpoint:
    host: str
    port: int = 5555
    failures: int = 0
    last_latency_ms: float = -1.0

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"


class CircuitBreaker:
    def __init__(self, fail_threshold: int = 3, cool_down_seconds: int = 60):
        self.fail_threshold = fail_threshold
        self.cool_down_seconds = cool_down_seconds
        self.opened_at: Optional[float] = None

    def allow(self, failures: int) -> bool:
        if failures < self.fail_threshold:
            return True
        if self.opened_at is None:
            self.opened_at = time.time()
            return False
        return (time.time() - self.opened_at) > self.cool_down_seconds

    def reset(self):
        self.opened_at = None


def parse_hosts(hosts: Iterable[str]) -> List[Endpoint]:
    eps: List[Endpoint] = []
    for h in hosts:
        h = h.strip()
        if not h:
            continue
        if ":" in h:
            host, port = h.split(":", 1)
            try:
                eps.append(Endpoint(host=host, port=int(port)))
            except ValueError:
                eps.append(Endpoint(host=host, port=5555))
        else:
            eps.append(Endpoint(host=h, port=5555))
    return eps


def tcp_connect(host: str, port: int, timeout: float = 3.0) -> Tuple[bool, float, str]:
    start = time.time()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            ms = (time.time() - start) * 1000.0
            return True, ms, "ok"
    except Exception as e:
        ms = (time.time() - start) * 1000.0
        return False, ms, str(e)


class FarmConnector:
    def __init__(self, endpoints: List[Endpoint], breaker: Optional[CircuitBreaker] = None):
        self.endpoints = endpoints
        self.breaker = breaker or CircuitBreaker()

    def choose_endpoint(self) -> Optional[Endpoint]:
        # Prefer lower failures and lower latency; shuffle to avoid stickiness
        candidates = [e for e in self.endpoints if self.breaker.allow(e.failures)]
        if not candidates:
            return None
        random.shuffle(candidates)
        candidates.sort(key=lambda e: (e.failures, e.last_latency_ms if e.last_latency_ms > 0 else 1e9))
        return candidates[0]

    def connect_any(self, attempts: int = 5, base_backoff: float = 0.5, max_backoff: float = 8.0) -> Optional[Endpoint]:
        delay = base_backoff
        for _ in range(attempts):
            ep = self.choose_endpoint()
            if ep is None:
                logger.warning("No available endpoints (circuit open). Cooling down…")
                time.sleep(min(delay, max_backoff))
                delay = min(delay * 2, max_backoff)
                continue
            ok, ms, msg = tcp_connect(ep.host, ep.port, timeout=3.0)
            ep.last_latency_ms = ms
            if ok:
                ep.failures = 0
                self.breaker.reset()
                logger.info("Connected to %s in %.1fms", ep.address, ms)
                return ep
            ep.failures += 1
            logger.warning("Connect failed %s (%.1fms): %s", ep.address, ms, msg)
            time.sleep(delay + random.uniform(0, delay))
            delay = min(delay * 2, max_backoff)
        return None


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Android farm connector CLI")
    parser.add_argument("--hosts", default=os.environ.get("FLY_ANDROID_HOSTS", ""), help="Comma-separated host:port list")
    parser.add_argument("--attempts", type=int, default=5)
    args = parser.parse_args(argv)

    hosts = [h for h in (args.hosts or os.environ.get("FLY_ANDROID_HOST", "")).split(",") if h]
    eps = parse_hosts(hosts)
    if not eps:
        logger.error("No hosts provided via --hosts or FLY_ANDROID_HOSTS/FLY_ANDROID_HOST")
        return 1
    fc = FarmConnector(eps)
    ep = fc.connect_any(attempts=args.attempts)
    return 0 if ep else 1


if __name__ == "__main__":
    raise SystemExit(main())


