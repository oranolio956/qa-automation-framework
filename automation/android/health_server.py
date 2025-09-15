#!/usr/bin/env python3
from fastapi import FastAPI
import subprocess
import os

app = FastAPI(title="Android Farm Health")

def adb_devices():
    try:
        out = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=10)
        if out.returncode != 0:
            return {"ok": False, "error": out.stderr.strip()}
        lines = [l for l in out.stdout.strip().split("\n")[1:] if l.strip()]
        devices = [l.split("\t")[0] for l in lines if "\tdevice" in l]
        return {"ok": True, "count": len(devices), "devices": devices}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/health")
def health():
    farm_host = os.getenv("FLY_ANDROID_HOST", "android-device-farm-prod.fly.dev")
    adb = adb_devices()
    return {
        "status": "healthy" if adb.get("ok") and adb.get("count", 0) >= 1 else "degraded",
        "adb": adb,
        "farm_host": farm_host,
    }
