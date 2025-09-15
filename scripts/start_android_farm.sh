#!/bin/bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
export DISPLAY=:99

# Start virtual display
Xvfb :99 -screen 0 1024x768x24 -ac &

# Start lightweight window manager and VNC for optional debugging
fluxbox &>/dev/null &
x11vnc -display :99 -nopw -forever -shared -bg

# Start Redis (used by health checks/tools)
redis-server --daemonize yes || true

# Ensure Android SDK env
export ANDROID_HOME=${ANDROID_HOME:-/opt/android-sdk}
export ANDROID_SDK_ROOT=${ANDROID_SDK_ROOT:-/opt/android-sdk}
export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator

# Boot emulator
echo "Starting Android emulator..."
cd "$ANDROID_HOME/emulator"
./emulator -avd snapchat_device -no-window -no-audio -no-boot-anim -accel off -gpu swiftshader_indirect -netfast &

# Wait for device
echo "Waiting for emulator to boot..."
adb wait-for-device
sleep 30

# Configure device for automation
adb shell settings put global development_settings_enabled 1 || true
adb shell settings put global adb_enabled 1 || true
adb shell settings put global stay_on_while_plugged_in 3 || true

# Enable ADB over TCP
adb tcpip 5555 || true
adb shell setprop service.adb.tcp.port 5555 || true

# Basic readiness
echo "Android emulator ready!"
adb devices || true

# Start orchestrator (optional; safe if module exists)
cd /app
python3 -m automation.android.automation_orchestrator_fixed &

# Health server (used by Fly checks)
uvicorn automation.android.health_server:app --host 0.0.0.0 --port 5000 &

# Keep alive
tail -f /dev/null
