#!/usr/bin/env python3
"""
Lightweight health server for Fly.io/containers.
Exposes /healthz on HEALTH_PORT (default 8080).
Checks: env presence, Redis ping (optional), APK file presence.
"""

import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
def _payments_ok() -> bool:
    # Consider OK if in free mode or Coinbase API key present
    try:
        import os
        free = str(os.environ.get('FREE_TEST_MODE', '0')).strip() in ('1','true','yes','on')
        return free or bool(os.environ.get('COINBASE_COMMERCE_API_KEY'))
    except Exception:
        return False


def _redis_ping_ok() -> bool:
    try:
        import redis
        url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
        r = redis.from_url(url)
        return bool(r.ping())
    except Exception:
        return False


def _apk_present_ok() -> bool:
    try:
        apk_path = Path('artifacts/apks/snapchat.apk')
        return apk_path.exists() and apk_path.stat().st_size > 1024 * 1024
    except Exception:
        return False

def _risk_status_line() -> str:
    try:
        from utils.risk_guard import get_risk_guard
        s = get_risk_guard().get_status()
        return f"kill={s.kill_switch} anomaly={s.anomaly_score:.2f} errs={s.last_minute_errors} reqs={s.last_minute_requests}"
    except Exception:
        return "kill=False anomaly=0.00 errs=0 reqs=0"

def _farm_ok() -> bool:
    try:
        from automation.android.ui_automator_manager import UIAutomatorManager
        mgr = UIAutomatorManager()
        # Attempt a lightweight discovery without connecting
        devices = mgr.discover_devices()
        return any((':5555' in d) or ('fly.dev' in d) for d in devices)
    except Exception:
        return False


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/healthz'):
            # Basic checks
            telegram_ok = bool(os.environ.get('TELEGRAM_BOT_TOKEN'))
            twilio_ok = bool(os.environ.get('TWILIO_ACCOUNT_SID')) and bool(os.environ.get('TWILIO_AUTH_TOKEN'))
            redis_ok = _redis_ping_ok()
            apk_ok = _apk_present_ok()
            pay_ok = _payments_ok()

            farm_ok = _farm_ok() if os.environ.get('FLY_MODE') else True
            overall = telegram_ok and twilio_ok and redis_ok and apk_ok and pay_ok and farm_ok
            status = 200 if overall else 503
            body = (
                f"telegram:{telegram_ok} twilio:{twilio_ok} redis:{redis_ok} apk:{apk_ok} payments:{pay_ok} farm:{farm_ok} risk:[{_risk_status_line()}]\n"
            ).encode()

            self.send_response(status)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path.startswith('/webhook/payments/coinbase'):
            # Expect Coinbase Commerce webhook
            try:
                length = int(self.headers.get('Content-Length', '0'))
                body = self.rfile.read(length)
                signature = self.headers.get('X-CC-Webhook-Signature', '')
                from utils.crypto_payments import handle_webhook
                ok, msg = handle_webhook(signature, body)
                self.send_response(200 if ok else 400)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write((msg + "\n").encode())
            except Exception:
                self.send_response(500)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()


def start_health_server():
    try:
        port = int(os.environ.get('HEALTH_PORT', '8080'))
        server = HTTPServer(('0.0.0.0', port), _Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
    except Exception:
        # Health server is optional; fail open
        pass


