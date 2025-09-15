#!/usr/bin/env python3
"""
Structured metrics and simple in-file telemetry sink.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any


class MetricsLogger:
    def __init__(self, log_dir: str = 'artifacts/metrics', filename_prefix: str = 'metrics'):
        self.dir = Path(log_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        self.path = self.dir / f"{filename_prefix}_{ts}.jsonl"

    def emit(self, name: str, data: Dict[str, Any]):
        event = {
            't': time.time(),
            'name': name,
            'data': data
        }
        with open(self.path, 'a') as f:
            f.write(json.dumps(event) + "\n")


def get_metrics_logger() -> MetricsLogger:
    return MetricsLogger()

"""
Lightweight Prometheus helpers with safe no-op fallbacks when disabled.
"""

from __future__ import annotations

import os
from typing import Any

METRICS_ENABLED = os.environ.get("METRICS_ENABLED", "true").lower() not in {"0", "false", "no"}

try:
    from prometheus_client import Counter as _Counter, Histogram as _Histogram, Gauge as _Gauge
except Exception:
    _Counter = _Histogram = _Gauge = None  # type: ignore[assignment]


def _nop(*args: Any, **kwargs: Any) -> Any:
    class _Obj:
        def inc(self, *a: Any, **k: Any) -> None:
            return None

        def observe(self, *a: Any, **k: Any) -> None:
            return None

        def set(self, *a: Any, **k: Any) -> None:
            return None

    return _Obj()


def counter(name: str, doc: str):
    if METRICS_ENABLED and _Counter is not None:
        return _Counter(name, doc)
    return _nop()


def histogram(name: str, doc: str, buckets: Any = None):
    if METRICS_ENABLED and _Histogram is not None:
        if buckets is not None:
            return _Histogram(name, doc, buckets=buckets)
        return _Histogram(name, doc)
    return _nop()


def gauge(name: str, doc: str):
    if METRICS_ENABLED and _Gauge is not None:
        return _Gauge(name, doc)
    return _nop()


