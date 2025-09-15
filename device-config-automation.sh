#!/bin/bash

# Android Device Configuration Automation
# Configures Android devices/emulators for optimal testing environment

set -e

# Configuration
DEVELOPER_APP_URL="https://github.com/example/android-dev-tools/releases/download/v1.0/dev-tools.apk"
TESTING_APPS_DIR="testing-apps"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_section() {
    echo -e "${BLUE}[SECTION]${NC} $1"
}

check_adb_connection() {
    log_section "Checking ADB Connection"
    
    if ! command -v adb &> /dev/null; then
        log_error "ADB not found. Please install Android SDK"
        exit 1
    fi
    
    # Check if device is connected
    if ! adb devices | grep -q "device$"; then
        log_error "No Android device connected"
        echo "Please connect a device and enable USB debugging"
        exit 1
    fi
    
    # Get device info
    DEVICE_MODEL=$(adb shell getprop ro.product.model 2>/dev/null || echo "Unknown")
    ANDROID_VERSION=$(adb shell getprop ro.build.version.release 2>/dev/null || echo "Unknown")
    
    log_info "Connected device: $DEVICE_MODEL (Android $ANDROID_VERSION)"
}

enable_developer_options() {
    log_section "Enabling Developer Options"
    
    # Enable developer options
    log_info "Enabling developer settings..."
    adb shell settings put global development_settings_enabled 1
    
    # Enable USB debugging (should already be enabled)
    log_info "Ensuring USB debugging is enabled..."
    adb shell settings put global adb_enabled 1
    
    # Stay awake while charging
    log_info "Setting stay awake while charging..."
    adb shell settings put global stay_on_while_plugged_in 3
    
    # Disable lock screen
    log_info "Disabling lock screen..."
    adb shell settings put secure lockscreen_disabled 1 2>/dev/null || log_warn "Could not disable lock screen"
    
    log_info "Developer options configured"
}

optimize_for_testing() {
    log_section "Optimizing Device for Testing"
    
    # Disable animations for faster testing
    log_info "Disabling animations..."
    adb shell settings put global window_animation_scale 0
    adb shell settings put global transition_animation_scale 0 
    adb shell settings put global animator_duration_scale 0
    
    # Set shorter screen timeout
    log_info "Setting screen timeout..."
    adb shell settings put system screen_off_timeout 1800000  # 30 minutes
    
    # Disable auto-rotate
    log_info "Disabling auto-rotate..."
    adb shell settings put system accelerometer_rotation 0
    
    # Set brightness to medium
    log_info "Setting screen brightness..."
    adb shell settings put system screen_brightness 128
    adb shell settings put system screen_brightness_mode 0
    
    # Disable keyboard sounds
    log_info "Disabling system sounds..."
    adb shell settings put system sound_effects_enabled 0
    adb shell settings put system dtmf_tone_enabled 0
    
    log_info "Device optimized for testing"
}

configure_locale_timezone() {
    log_section "Configuring Locale and Timezone"
    
    # Set timezone to EST (good for US testing)
    log_info "Setting timezone..."
    adb shell setprop persist.sys.timezone "America/New_York"
    
    # Set locale to US English
    log_info "Setting locale..."
    adb shell setprop persist.sys.locale "en-US"
    adb shell setprop persist.sys.language "en"
    adb shell setprop persist.sys.country "US"
    
    # Set date format
    adb shell settings put system date_format "MM/dd/yyyy"
    
    log_info "Locale and timezone configured"
}

setup_testing_directories() {
    log_section "Setting Up Testing Directories"
    
    # Create testing directories
    log_info "Creating testing directories..."
    adb shell mkdir -p /sdcard/testing/apps
    adb shell mkdir -p /sdcard/testing/logs
    adb shell mkdir -p /sdcard/testing/screenshots
    adb shell mkdir -p /sdcard/testing/data
    adb shell mkdir -p /sdcard/testing/reports
    
    # Set permissions
    log_info "Setting directory permissions..."
    adb shell chmod 777 /sdcard/testing
    adb shell chmod 777 /sdcard/testing/apps
    adb shell chmod 777 /sdcard/testing/logs
    adb shell chmod 777 /sdcard/testing/screenshots
    adb shell chmod 777 /sdcard/testing/data
    adb shell chmod 777 /sdcard/testing/reports
    
    log_info "Testing directories created"
}

install_testing_utilities() {
    log_section "Installing Testing Utilities"
    
    # Create local testing apps directory
    mkdir -p "$TESTING_APPS_DIR"
    
    # Install useful testing apps
    install_test_app() {
        local app_name="$1"
        local package_name="$2"
        local download_url="$3"
        local apk_file="$TESTING_APPS_DIR/${app_name}.apk"
        
        log_info "Installing $app_name..."
        
        # Check if already installed
        if adb shell pm list packages | grep -q "$package_name"; then
            log_info "$app_name already installed"
            return 0
        fi
        
        # Download if needed
        if [[ ! -f "$apk_file" ]] && [[ -n "$download_url" ]]; then
            log_info "Downloading $app_name..."
            if command -v wget &> /dev/null; then
                wget -O "$apk_file" "$download_url" 2>/dev/null || log_warn "Download failed for $app_name"
            elif command -v curl &> /dev/null; then
                curl -L -o "$apk_file" "$download_url" 2>/dev/null || log_warn "Download failed for $app_name"
            else
                log_warn "No download tool available (wget/curl)"
                return 1
            fi
        fi
        
        # Install if APK exists
        if [[ -f "$apk_file" ]]; then
            if adb install -r "$apk_file" 2>/dev/null; then
                log_info "$app_name installed successfully"
            else
                log_warn "Failed to install $app_name"
            fi
        else
            log_warn "APK file not found for $app_name"
        fi
    }
    
    # Install developer tools (if available)
    # install_test_app "DevTools" "com.developer.tools" "$DEVELOPER_APP_URL"
    
    log_info "Testing utilities installation completed"
}

configure_permissions() {
    log_section "Configuring App Permissions"
    
    # Grant common permissions to shell (for testing tools)
    log_info "Granting shell permissions..."
    
    PERMISSIONS=(
        "android.permission.READ_EXTERNAL_STORAGE"
        "android.permission.WRITE_EXTERNAL_STORAGE"
        "android.permission.CAMERA"
        "android.permission.RECORD_AUDIO"
        "android.permission.ACCESS_FINE_LOCATION"
        "android.permission.ACCESS_COARSE_LOCATION"
    )
    
    for permission in "${PERMISSIONS[@]}"; do
        adb shell pm grant com.android.shell "$permission" 2>/dev/null || true
    done
    
    log_info "Shell permissions configured"
}

setup_logging() {
    log_section "Setting Up Logging Configuration"
    
    # Configure logcat buffer sizes
    log_info "Configuring logcat buffers..."
    adb shell setprop log.tag.TestRunner DEBUG
    adb shell setprop log.tag.Appium DEBUG
    adb shell setprop persist.log.tag.DEFAULT_MAX_BUFFER_SIZE 262144
    
    # Clear existing logs
    log_info "Clearing existing logs..."
    adb logcat -c 2>/dev/null || true
    
    log_info "Logging configured"
}

install_network_tools() {
    log_section "Installing Network Testing Tools"
    
    # Check if curl is available
    if adb shell which curl >/dev/null 2>&1; then
        log_info "curl already available"
    else
        log_warn "curl not available on device"
    fi
    
    # Check if ping is available
    if adb shell which ping >/dev/null 2>&1; then
        log_info "ping available for network testing"
    else
        log_warn "ping not available on device"
    fi
    
    # Test network connectivity
    log_info "Testing network connectivity..."
    if adb shell ping -c 1 8.8.8.8 >/dev/null 2>&1; then
        log_info "✓ Network connectivity confirmed"
    else
        log_warn "✗ Network connectivity issue detected"
    fi
}

create_test_data() {
    log_section "Creating Test Data"
    
    # Create sample test data file
    cat > /tmp/test_data.json << 'EOF'
{
  "test_users": [
    {
      "username": "testuser1",
      "email": "test1@example.com",
      "phone": "+1-555-0001"
    },
    {
      "username": "testuser2", 
      "email": "test2@example.com",
      "phone": "+1-555-0002"
    }
  ],
  "test_locations": [
    {
      "name": "New York",
      "latitude": 40.7128,
      "longitude": -74.0060
    },
    {
      "name": "San Francisco",
      "latitude": 37.7749,
      "longitude": -122.4194
    }
  ],
  "device_info": {
    "configured_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "android_version": "$(adb shell getprop ro.build.version.release)",
    "device_model": "$(adb shell getprop ro.product.model)"
  }
}
EOF

    # Push test data to device
    log_info "Uploading test data..."
    adb push /tmp/test_data.json /sdcard/testing/data/
    
    # Create sample images for testing
    if command -v convert &> /dev/null; then
        log_info "Creating sample test images..."
        convert -size 800x600 xc:blue /tmp/test_image_blue.png
        convert -size 800x600 xc:red /tmp/test_image_red.png
        
        adb push /tmp/test_image_blue.png /sdcard/testing/data/
        adb push /tmp/test_image_red.png /sdcard/testing/data/
        
        rm -f /tmp/test_image_*.png
    fi
    
    rm -f /tmp/test_data.json
    
    log_info "Test data created"
}

verify_configuration() {
    log_section "Verifying Configuration"
    
    echo "Device Configuration Summary:"
    echo "────────────────────────────────"
    
    # Developer options
    DEV_ENABLED=$(adb shell settings get global development_settings_enabled 2>/dev/null || echo "unknown")
    echo "Developer Options: $DEV_ENABLED"
    
    # USB debugging
    ADB_ENABLED=$(adb shell settings get global adb_enabled 2>/dev/null || echo "unknown")
    echo "USB Debugging: $ADB_ENABLED"
    
    # Animations
    WINDOW_ANIM=$(adb shell settings get global window_animation_scale 2>/dev/null || echo "unknown")
    echo "Window Animation Scale: $WINDOW_ANIM"
    
    # Screen timeout
    SCREEN_TIMEOUT=$(adb shell settings get system screen_off_timeout 2>/dev/null || echo "unknown")
    echo "Screen Timeout: $SCREEN_TIMEOUT ms"
    
    # Timezone
    TIMEZONE=$(adb shell getprop persist.sys.timezone 2>/dev/null || echo "unknown")
    echo "Timezone: $TIMEZONE"
    
    # Locale
    LOCALE=$(adb shell getprop persist.sys.locale 2>/dev/null || echo "unknown")
    echo "Locale: $LOCALE"
    
    # Available space
    AVAILABLE_SPACE=$(adb shell df /sdcard | tail -1 | awk '{print $4}' 2>/dev/null || echo "unknown")
    echo "Available Storage: $AVAILABLE_SPACE KB"
    
    # Installed packages count
    PACKAGE_COUNT=$(adb shell pm list packages | wc -l 2>/dev/null || echo "unknown")
    echo "Installed Packages: $PACKAGE_COUNT"
    
    echo "────────────────────────────────"
    
    # Test basic functionality
    log_info "Testing basic functionality..."
    
    # Screenshot test
    if adb exec-out screencap -p > /tmp/test_screenshot.png 2>/dev/null; then
        log_info "✓ Screenshot capability working"
        rm -f /tmp/test_screenshot.png
    else
        log_warn "✗ Screenshot capability failed"
    fi
    
    # Input test
    if adb shell input tap 100 100 2>/dev/null; then
        log_info "✓ Input injection working"
    else
        log_warn "✗ Input injection failed"
    fi
    
    # File system access
    if adb shell ls /sdcard/testing/ >/dev/null 2>&1; then
        log_info "✓ Testing directories accessible"
    else
        log_warn "✗ Testing directories not accessible"
    fi
    
    log_info "Configuration verification completed"
}

create_configuration_script() {
    log_section "Creating Configuration Scripts"
    
    # Create quick setup script
    cat > /tmp/quick_device_setup.sh << 'EOF'
#!/bin/bash
# Quick Device Setup for Testing

echo "Running quick device setup..."

# Essential settings for testing
adb shell settings put global development_settings_enabled 1
adb shell settings put global adb_enabled 1
adb shell settings put global window_animation_scale 0
adb shell settings put global transition_animation_scale 0
adb shell settings put global animator_duration_scale 0
adb shell settings put global stay_on_while_plugged_in 3
adb shell settings put system screen_off_timeout 1800000

echo "Quick setup completed!"
EOF

    chmod +x /tmp/quick_device_setup.sh
    
    # Create reset script
    cat > /tmp/reset_device_settings.sh << 'EOF'
#!/bin/bash
# Reset Device Settings to Default

echo "Resetting device settings to defaults..."

# Reset animations
adb shell settings put global window_animation_scale 1.0
adb shell settings put global transition_animation_scale 1.0
adb shell settings put global animator_duration_scale 1.0

# Reset screen timeout
adb shell settings put system screen_off_timeout 30000

# Reset other settings
adb shell settings put global stay_on_while_plugged_in 0
adb shell settings put system accelerometer_rotation 1
adb shell settings put system sound_effects_enabled 1

echo "Device settings reset completed!"
EOF

    chmod +x /tmp/reset_device_settings.sh
    
    # Copy scripts to local directory
    cp /tmp/quick_device_setup.sh ./
    cp /tmp/reset_device_settings.sh ./
    
    log_info "Configuration scripts created:"
    log_info "  - quick_device_setup.sh (essential settings)"
    log_info "  - reset_device_settings.sh (restore defaults)"
}

show_usage() {
    echo "Android Device Configuration Automation"
    echo
    echo "Usage: $0 [options]"
    echo
    echo "Options:"
    echo "  --quick       Run quick configuration (essential settings only)"
    echo "  --verify      Only verify current configuration"
    echo "  --reset       Reset settings to defaults"
    echo "  --help        Show this help message"
    echo
    echo "Default: Run full configuration setup"
}

main() {
    local mode="full"
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --quick)
                mode="quick"
                shift
                ;;
            --verify)
                mode="verify"
                shift
                ;;
            --reset)
                mode="reset"
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    log_info "Starting Android Device Configuration"
    log_info "Mode: $mode"
    echo
    
    check_adb_connection
    
    case $mode in
        quick)
            enable_developer_options
            optimize_for_testing
            verify_configuration
            ;;
        verify)
            verify_configuration
            ;;
        reset)
            if [[ -f "reset_device_settings.sh" ]]; then
                ./reset_device_settings.sh
            else
                log_error "Reset script not found. Run full setup first."
                exit 1
            fi
            ;;
        full|*)
            enable_developer_options
            optimize_for_testing
            configure_locale_timezone
            setup_testing_directories
            install_testing_utilities
            configure_permissions
            setup_logging
            install_network_tools
            create_test_data
            create_configuration_script
            verify_configuration
            ;;
    esac
    
    echo
    log_info "Device configuration completed successfully!"
    echo
    echo "Your Android device is now optimized for testing with:"
    echo "• Developer options enabled"
    echo "• Animations disabled for faster testing"
    echo "• Testing directories created"
    echo "• Logging configured"
    echo "• Sample test data available"
    echo
    echo "Next steps:"
    echo "1. Install your test app: adb install -r your-app.apk"
    echo "2. Run Appium server: appium"
    echo "3. Execute tests: python -m pytest"
}

main "$@"