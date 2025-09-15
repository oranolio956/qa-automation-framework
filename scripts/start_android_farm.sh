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

# Prepare AVD (force ARM64 AVD)
AVD_NAME=${AVD_NAME:-snapchat_device_arm}
echo "Preparing AVD $AVD_NAME..."
rm -rf "$HOME/.android/avd/${AVD_NAME}.avd" "$HOME/.android/avd/${AVD_NAME}.ini" || true
yes | avdmanager delete avd -n "$AVD_NAME" >/dev/null 2>&1 || true
yes | avdmanager create avd -n "$AVD_NAME" -k "system-images;android-30;google_apis;arm64-v8a" -d "pixel_4" --abi arm64-v8a --force

# Start ADB server
adb start-server || true

# Boot emulator
echo "Starting Android emulator ($AVD_NAME)..."
cd "$ANDROID_HOME/emulator"
./emulator -avd "$AVD_NAME" -no-window -no-audio -no-boot-anim -accel off -gpu swiftshader_indirect -netfast &

# Wait for device to appear and boot
echo "Waiting for emulator to be detected by ADB..."
for i in $(seq 1 120); do
  if adb devices | grep -q "emulator-"; then break; fi
  sleep 2
done
echo "Waiting for Android to report boot_completed..."
for i in $(seq 1 120); do
  bc=$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r') || true
  if [ "$bc" = "1" ]; then break; fi
  sleep 2
done

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
