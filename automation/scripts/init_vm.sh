#!/bin/bash
# VM Initialization Script for QA Android Emulation
# This script sets up an Android VM for automated testing

set -euo pipefail

LOG_FILE="/var/log/qa-framework/vm-init.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Starting VM initialization for QA testing..."

# Wait for system to be ready
sleep 30

# Enable ADB debugging
log "Enabling ADB debugging..."
setprop service.adb.tcp.port 5555
stop adbd
start adbd

# Install required APKs for testing
log "Installing testing utilities..."
if [ -f "/system/test-utilities.apk" ]; then
    pm install -r /system/test-utilities.apk
fi

# Configure display and input settings
log "Configuring display settings..."
wm size 1080x1920
wm density 480

# Set up synthetic sensor providers for testing
log "Setting up sensor simulation..."
setup_sensors() {
    # Enable synthetic sensor providers for testing
    am broadcast -a "whs.USE_SYNTHETIC_PROVIDERS" com.google.android.wearable.healthservices
    am broadcast -a "whs.synthetic.user.START_WALKING" com.google.android.wearable.healthservices
}
setup_sensors

# Configure network settings
log "Configuring network..."
svc wifi enable
svc data enable

# Set up test user profile
log "Setting up test user profile..."
am start -n com.android.settings/.Settings
input keyevent KEYCODE_HOME

# Disable unnecessary services to optimize performance
log "Optimizing performance..."
pm disable com.google.android.gms.ads
pm disable com.android.providers.downloads.ui
pm disable com.google.android.apps.photos

# Enable developer options
log "Enabling developer options..."
settings put global development_settings_enabled 1
settings put global adb_enabled 1
settings put system pointer_location 0

# Configure animation scales for faster testing
settings put global window_animation_scale 0.5
settings put global transition_animation_scale 0.5
settings put global animator_duration_scale 0.5

# Set up screenshot directory
mkdir -p /sdcard/qa-screenshots
chmod 777 /sdcard/qa-screenshots

# Create test data directory
mkdir -p /sdcard/qa-test-data
chmod 777 /sdcard/qa-test-data

log "VM initialization completed successfully"

# Signal that VM is ready
touch /sdcard/vm-ready
chmod 666 /sdcard/vm-ready

log "VM is ready for QA testing"