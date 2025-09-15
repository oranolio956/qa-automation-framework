#!/usr/bin/env python3
"""
Boot-time health checks for critical automation dependencies and configuration.

Usage:
  python automation/boot_checks.py --hosts android-farm-1.example.com:5555,android-farm-2.example.com:5555 \
    --require uiautomator2,adbutils --check sms,redis,adb

Exit codes:
  0  All checks passed
  1  Some checks failed

This tool avoids third-party imports (except optional detection) to remain runnable
in minimal environments.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse


LOGGER = logging.getLogger("boot_checks")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
)


@dataclass
class CheckResult:
    name: str
    ok: bool
    details: str = ""
    metadata: Dict[str, str] = None  # type: ignore[assignment]

    def to_dict(self) -> Dict[str, object]:
        d = asdict(self)
        # Ensure metadata is always a dict for stable JSON
        d["metadata"] = d.get("metadata") or {}
        return d


def _check_python_module(module_name: str) -> CheckResult:
    try:
        __import__(module_name)
        return CheckResult(name=f"python_module:{module_name}", ok=True, details="import ok")
    except Exception as e:
        return CheckResult(name=f"python_module:{module_name}", ok=False, details=f"import failed: {e}")


def _check_adb_available() -> CheckResult:
    adb_path = shutil.which("adb")
    if not adb_path:
        return CheckResult(name="adb", ok=False, details="adb not found in PATH")
    try:
        proc = subprocess.run([adb_path, "version"], capture_output=True, text=True, timeout=10)
        if proc.returncode != 0:
            return CheckResult(name="adb", ok=False, details=f"adb version failed: {proc.stderr.strip()}")
        return CheckResult(name="adb", ok=True, details=proc.stdout.splitlines()[0] if proc.stdout else "ok")
    except Exception as e:
        return CheckResult(name="adb", ok=False, details=f"adb invocation error: {e}")


def _resolve_host(host: str) -> Tuple[bool, str]:
    try:
        socket.getaddrinfo(host, None)
        return True, "resolved"
    except Exception as e:
        return False, f"dns error: {e}"


def _tcp_check(host: str, port: int, timeout: float = 3.0) -> Tuple[bool, str, float]:
    start = time.time()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            elapsed = (time.time() - start) * 1000.0
            return True, "connect ok", elapsed
    except Exception as e:
        elapsed = (time.time() - start) * 1000.0
        return False, f"connect error: {e}", elapsed


def _check_farm_endpoints(endpoints: List[str]) -> List[CheckResult]:
    results: List[CheckResult] = []
    for ep in endpoints:
        ep = ep.strip()
        if not ep:
            continue
        host, port = (ep.split(":", 1) + ["5555"])[:2]
        try:
            port_i = int(port)
        except Exception:
            port_i = 5555

        ok_dns, dns_msg = _resolve_host(host)
        ok_tcp, tcp_msg, ms = _tcp_check(host, port_i)
        results.append(
            CheckResult(
                name=f"farm:{host}:{port_i}",
                ok=ok_dns and ok_tcp,
                details=f"dns={dns_msg}, tcp={tcp_msg}, latency_ms={ms:.1f}",
                metadata={"host": host, "port": str(port_i), "latency_ms": f"{ms:.1f}"},
            )
        )
    return results


def _check_env_vars(required: List[str]) -> List[CheckResult]:
    results: List[CheckResult] = []
    for key in required:
        val = os.environ.get(key)
        ok = bool(val)
        details = "present" if ok else "missing"
        masked = (val[:4] + "…" + val[-2:]) if (val and len(val) > 8) else (val or "")
        results.append(CheckResult(name=f"env:{key}", ok=ok, details=details, metadata={"value": masked}))
    return results


def _check_redis_connectivity(url: Optional[str]) -> CheckResult:
    if not url:
        return CheckResult(name="redis", ok=False, details="REDIS_URL not set")
    try:
        u = urlparse(url)
        host = u.hostname or "localhost"
        port = int(u.port or 6379)
        ok, msg, ms = _tcp_check(host, port, timeout=2.0)
        return CheckResult(name="redis", ok=ok, details=f"{msg}, latency_ms={ms:.1f}", metadata={"host": host, "port": str(port)})
    except Exception as e:
        return CheckResult(name="redis", ok=False, details=f"parse/connect error: {e}")


def run_checks(
    hosts: List[str],
    required_modules: List[str],
    include_checks: List[str],
) -> Dict[str, object]:
    results: List[CheckResult] = []

    # Python modules
    for mod in required_modules:
        results.append(_check_python_module(mod))

    # ADB
    if "adb" in include_checks:
        results.append(_check_adb_available())

    # Farm endpoints
    farm_eps = hosts
    if not farm_eps:
        env_hosts = os.environ.get("FLY_ANDROID_HOSTS") or os.environ.get("FLY_ANDROID_HOST")
        if env_hosts:
            farm_eps = [h.strip() for h in env_hosts.split(",") if h.strip()]
    if "adb" in include_checks and farm_eps:
        results.extend(_check_farm_endpoints(farm_eps))

    # Env vars and services
    if "sms" in include_checks:
        results.extend(_check_env_vars(["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"]))
    if "redis" in include_checks:
        results.extend(_check_env_vars(["REDIS_URL"]))
        results.append(_check_redis_connectivity(os.environ.get("REDIS_URL")))

    # Aggregate
    ok = all(r.ok for r in results)
    summary = {
        "ok": ok,
        "failures": len([r for r in results if not r.ok]),
        "checks": [r.to_dict() for r in results],
    }
    return summary


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Boot-time health checks for automation system")
    parser.add_argument(
        "--hosts",
        help="Comma-separated list of farm hosts (host:port). Falls back to FLY_ANDROID_HOSTS/FLY_ANDROID_HOST",
        default="",
    )
    parser.add_argument(
        "--require",
        help="Comma-separated python modules to require/import (e.g., uiautomator2,adbutils)",
        default="uiautomator2,adbutils",
    )
    parser.add_argument(
        "--check",
        help="Comma-separated checks to include (choices: adb,sms,redis)",
        default="adb,sms,redis",
    )
    parser.add_argument(
        "--json", action="store_true", help="Output machine-readable JSON in addition to human-readable logs"
    )

    args = parser.parse_args(argv)
    hosts = [h.strip() for h in (args.hosts or "").split(",") if h.strip()]
    required = [m.strip() for m in (args.require or "").split(",") if m.strip()]
    checks = [c.strip() for c in (args.check or "").split(",") if c.strip()]

    summary = run_checks(hosts=hosts, required_modules=required, include_checks=checks)

    # Human-readable output
    failures = 0
    for c in summary["checks"]:  # type: ignore[index]
        status = "OK" if c["ok"] else "FAIL"
        if c["ok"] is False:
            failures += 1
        LOGGER.info("%-6s %-32s %s", status, c["name"], c["details"])  # type: ignore[index]

    if args.json:
        print(json.dumps(summary, indent=2))

    return 0 if summary["ok"] else 1  # type: ignore[index]


if __name__ == "__main__":
    sys.exit(main())


