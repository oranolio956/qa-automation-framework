#!/bin/bash

# Android Testing Framework Setup
# Installs and configures testing frameworks for Android app development

set -e

# Configuration
APPIUM_VERSION="2.0.0"
PYTHON_REQUIREMENTS_FILE="/tmp/testing-requirements.txt"
TEST_WORKSPACE="$HOME/AndroidTesting"

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

check_prerequisites() {
    log_section "Checking Prerequisites"
    
    # Check if Android environment is set up
    if [[ -z "$ANDROID_HOME" ]]; then
        log_error "ANDROID_HOME not set. Run development-tools.sh first"
        exit 1
    fi
    
    # Check if ADB is available
    if ! command -v adb &> /dev/null; then
        log_error "ADB not found. Install Android SDK first"
        exit 1
    fi
    
    # Check if Node.js is available
    if ! command -v node &> /dev/null; then
        log_error "Node.js not found. Install Node.js first"
        exit 1
    fi
    
    # Check if Python3 is available
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 not found. Install Python3 first"
        exit 1
    fi
    
    log_info "Prerequisites check passed"
}

install_appium_framework() {
    log_section "Installing Appium Framework"
    
    # Install Appium globally
    log_info "Installing Appium server..."
    npm install -g appium@${APPIUM_VERSION}
    
    # Install Appium drivers
    log_info "Installing Appium drivers..."
    appium driver install uiautomator2
    appium driver install xcuitest 2>/dev/null || log_warn "XCUITest driver not available on this platform"
    
    # Install Appium plugins
    log_info "Installing Appium plugins..."
    appium plugin install images
    appium plugin install element-wait
    
    # Verify installation
    appium --version
    log_info "Appium framework installed successfully"
}

install_python_testing_tools() {
    log_section "Installing Python Testing Tools"
    
    # Create requirements file
    cat > "$PYTHON_REQUIREMENTS_FILE" << 'EOF'
# Core testing frameworks
Appium-Python-Client==2.11.1
selenium==4.15.2
pytest==7.4.3
pytest-html==4.1.1
pytest-xdist==3.3.1

# HTTP and API testing
requests==2.31.0
urllib3==2.0.7

# Data handling
pandas==2.1.3
openpyxl==3.1.2

# Image and screenshot comparison
Pillow==10.1.0
opencv-python==4.8.1.78

# Reporting and logging
allure-pytest==2.13.2
structlog==23.2.0

# Device interaction
ppadb==0.3.0
frida-tools==12.2.2

# Test data generation
faker==20.1.0
factory-boy==3.3.0

# Performance testing
locust==2.17.0
EOF

    # Install Python packages
    log_info "Installing Python testing packages..."
    pip3 install --user -r "$PYTHON_REQUIREMENTS_FILE"
    
    log_info "Python testing tools installed"
}

install_node_testing_tools() {
    log_section "Installing Node.js Testing Tools"
    
    # Create package.json for testing tools
    mkdir -p "$TEST_WORKSPACE"
    cd "$TEST_WORKSPACE"
    
    cat > package.json << 'EOF'
{
  "name": "android-testing-tools",
  "version": "1.0.0",
  "description": "Android testing framework tools",
  "scripts": {
    "test": "jest",
    "test:watch": "jest --watch",
    "appium": "appium",
    "doctor": "appium doctor"
  },
  "dependencies": {
    "appium": "^2.0.0",
    "webdriverio": "^8.24.12",
    "@wdio/cli": "^8.24.12",
    "@wdio/local-runner": "^8.24.12",
    "@wdio/mocha-framework": "^8.24.12",
    "@wdio/spec-reporter": "^8.24.12",
    "chai": "^4.3.10",
    "mocha": "^10.2.0"
  },
  "devDependencies": {
    "jest": "^29.7.0",
    "@types/jest": "^29.5.8",
    "typescript": "^5.2.2"
  }
}
EOF

    # Install Node.js testing packages
    log_info "Installing Node.js testing packages..."
    npm install
    
    log_info "Node.js testing tools installed"
}

create_test_workspace() {
    log_section "Creating Test Workspace"
    
    mkdir -p "$TEST_WORKSPACE"/{projects,reports,scripts,config,resources}
    
    # Create directory structure
    log_info "Creating test workspace structure..."
    cat > "$TEST_WORKSPACE/README.md" << 'EOF'
# Android Testing Workspace

This workspace contains testing frameworks and utilities for Android app testing.

## Structure

- `projects/` - Test project directories
- `reports/` - Test execution reports
- `scripts/` - Helper scripts and utilities
- `config/` - Configuration files
- `resources/` - Test resources (APKs, test data, etc.)

## Quick Start

1. Place your APK files in `resources/`
2. Configure test settings in `config/`
3. Run tests from `projects/` directories
4. View reports in `reports/`

EOF

    log_info "Test workspace created at $TEST_WORKSPACE"
}

setup_appium_config() {
    log_section "Setting up Appium Configuration"
    
    # Create Appium configuration
    cat > "$TEST_WORKSPACE/config/appium-config.json" << 'EOF'
{
  "server": {
    "address": "127.0.0.1",
    "port": 4723,
    "basePath": "/wd/hub",
    "allow-cors": true,
    "allow-insecure": ["adb_shell"],
    "relaxed-security": true
  },
  "android": {
    "platformName": "Android",
    "automationName": "UiAutomator2",
    "deviceName": "AndroidTestDevice",
    "platformVersion": "9.0",
    "newCommandTimeout": 300,
    "uiautomator2ServerInstallTimeout": 120000
  }
}
EOF

    # Create capabilities template
    cat > "$TEST_WORKSPACE/config/capabilities.py" << 'EOF'
"""
Android testing capabilities for Appium
"""

def get_android_capabilities(app_path=None, device_name="AndroidTestDevice"):
    """Get Android capabilities for Appium testing"""
    
    caps = {
        "platformName": "Android",
        "automationName": "UiAutomator2",
        "deviceName": device_name,
        "platformVersion": "9.0",
        "newCommandTimeout": 300,
        "uiautomator2ServerInstallTimeout": 120000,
        "autoGrantPermissions": True,
        "noReset": False,
        "fullReset": False
    }
    
    if app_path:
        caps["app"] = app_path
    
    return caps

def get_web_capabilities():
    """Get web testing capabilities"""
    
    return {
        "platformName": "Android",
        "automationName": "UiAutomator2",
        "deviceName": "AndroidTestDevice",
        "browserName": "Chrome",
        "chromedriverExecutable": "/usr/local/bin/chromedriver"
    }
EOF

    log_info "Appium configuration created"
}

create_development_scripts() {
    log_section "Creating Development Scripts"
    
    # ADB development helper
    cat > "$TEST_WORKSPACE/scripts/adb-dev-setup.sh" << 'EOF'
#!/bin/bash

# ADB Development Setup Script
# Configures Android device/emulator for testing

set -e

log_info() {
    echo "[INFO] $1"
}

setup_developer_options() {
    log_info "Enabling developer options..."
    
    # Enable developer options
    adb shell settings put global development_settings_enabled 1
    
    # Enable USB debugging
    adb shell settings put global adb_enabled 1
    
    # Disable animations for faster testing
    adb shell settings put global window_animation_scale 0
    adb shell settings put global transition_animation_scale 0
    adb shell settings put global animator_duration_scale 0
    
    # Keep screen on while charging
    adb shell settings put global stay_on_while_plugged_in 2
    
    # Disable screen lock
    adb shell settings put secure lockscreen_disabled 1
    
    log_info "Developer options configured"
}

install_testing_tools() {
    log_info "Installing testing utilities..."
    
    # Create test directories
    adb shell mkdir -p /sdcard/testing/apps
    adb shell mkdir -p /sdcard/testing/logs
    adb shell mkdir -p /sdcard/testing/screenshots
    
    # Set permissions for testing
    adb shell pm grant com.android.shell android.permission.READ_EXTERNAL_STORAGE
    adb shell pm grant com.android.shell android.permission.WRITE_EXTERNAL_STORAGE
    
    log_info "Testing utilities installed"
}

configure_test_environment() {
    log_info "Configuring test environment..."
    
    # Set up timezone
    adb shell setprop persist.sys.timezone "America/New_York"
    
    # Configure locale
    adb shell setprop persist.sys.locale "en-US"
    
    # Increase logcat buffer
    adb shell setprop log.tag.TestRunner DEBUG
    
    log_info "Test environment configured"
}

main() {
    echo "Setting up Android device for testing..."
    
    # Check ADB connection
    if ! adb devices | grep -q "device$"; then
        echo "Error: No Android device connected"
        exit 1
    fi
    
    setup_developer_options
    install_testing_tools
    configure_test_environment
    
    echo "Development setup complete!"
}

main "$@"
EOF

    chmod +x "$TEST_WORKSPACE/scripts/adb-dev-setup.sh"
    
    # Test runner script
    cat > "$TEST_WORKSPACE/scripts/run-tests.py" << 'EOF'
#!/usr/bin/env python3
"""
Android Test Runner
Executes automated tests on Android devices/emulators
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

def check_adb_connection():
    """Check if ADB device is connected"""
    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
        if 'device' in result.stdout:
            print("✓ ADB device connected")
            return True
        else:
            print("✗ No ADB device found")
            return False
    except Exception as e:
        print(f"✗ ADB check failed: {e}")
        return False

def install_app(apk_path):
    """Install APK on connected device"""
    if not Path(apk_path).exists():
        print(f"✗ APK not found: {apk_path}")
        return False
    
    try:
        print(f"Installing {apk_path}...")
        result = subprocess.run(['adb', 'install', '-r', apk_path], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ APK installed successfully")
            return True
        else:
            print(f"✗ Installation failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Installation error: {e}")
        return False

def run_appium_tests(test_dir):
    """Run Appium tests"""
    try:
        print(f"Running tests from {test_dir}...")
        result = subprocess.run(['python3', '-m', 'pytest', test_dir, '-v'], 
                              cwd=test_dir)
        return result.returncode == 0
    except Exception as e:
        print(f"✗ Test execution failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Android Test Runner')
    parser.add_argument('--apk', help='APK file to install and test')
    parser.add_argument('--test-dir', help='Test directory to execute')
    parser.add_argument('--setup-only', action='store_true', 
                       help='Only setup device, don\'t run tests')
    
    args = parser.parse_args()
    
    # Check prerequisites
    if not check_adb_connection():
        sys.exit(1)
    
    # Install APK if provided
    if args.apk:
        if not install_app(args.apk):
            sys.exit(1)
    
    # Setup device
    setup_script = Path(__file__).parent / 'adb-dev-setup.sh'
    if setup_script.exists():
        subprocess.run(['bash', str(setup_script)])
    
    if args.setup_only:
        print("Device setup complete")
        return
    
    # Run tests if test directory provided
    if args.test_dir:
        if not run_appium_tests(args.test_dir):
            sys.exit(1)
    
    print("Test execution complete")

if __name__ == '__main__':
    main()
EOF

    chmod +x "$TEST_WORKSPACE/scripts/run-tests.py"
    
    log_info "Development scripts created"
}

create_sample_test_project() {
    log_section "Creating Sample Test Project"
    
    PROJECT_DIR="$TEST_WORKSPACE/projects/sample-app-test"
    mkdir -p "$PROJECT_DIR"
    
    # Create test configuration
    cat > "$PROJECT_DIR/conftest.py" << 'EOF'
"""
Pytest configuration for Android testing
"""

import pytest
from appium import webdriver
from appium.options.android import UiAutomator2Options
import sys
import os

# Add config path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'config'))
from capabilities import get_android_capabilities

@pytest.fixture(scope="session")
def appium_driver():
    """Create Appium driver for testing"""
    
    # Configure capabilities
    options = UiAutomator2Options()
    caps = get_android_capabilities()
    options.load_capabilities(caps)
    
    # Create driver
    driver = webdriver.Remote('http://127.0.0.1:4723/wd/hub', options=options)
    driver.implicitly_wait(10)
    
    yield driver
    
    # Cleanup
    driver.quit()

@pytest.fixture
def app_context(appium_driver):
    """Provide app context for tests"""
    return {
        'driver': appium_driver,
        'timeout': 30
    }
EOF

    # Create sample test
    cat > "$PROJECT_DIR/test_basic_functionality.py" << 'EOF'
"""
Basic Android app functionality tests
"""

import pytest
import time
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class TestBasicFunctionality:
    """Test basic app functionality"""
    
    def test_app_launch(self, app_context):
        """Test app launches successfully"""
        driver = app_context['driver']
        
        # Wait for app to load
        time.sleep(3)
        
        # Verify app is running
        current_activity = driver.current_activity
        assert current_activity is not None, "App should be running"
        
        print(f"Current activity: {current_activity}")
    
    def test_ui_elements_present(self, app_context):
        """Test basic UI elements are present"""
        driver = app_context['driver']
        timeout = app_context['timeout']
        
        # Look for common UI elements
        wait = WebDriverWait(driver, timeout)
        
        # Try to find at least one interactive element
        try:
            # Look for buttons, text fields, or other interactive elements
            elements = driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.Button")
            if not elements:
                elements = driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.EditText")
            if not elements:
                elements = driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.TextView")
            
            assert len(elements) > 0, "Should find at least one UI element"
            print(f"Found {len(elements)} interactive elements")
            
        except Exception as e:
            print(f"UI element search failed: {e}")
            # Take screenshot for debugging
            driver.save_screenshot("/tmp/ui_test_failure.png")
            raise
    
    def test_device_info(self, app_context):
        """Test device information access"""
        driver = app_context['driver']
        
        # Get device information
        device_info = {
            'platform_version': driver.capabilities.get('platformVersion'),
            'device_name': driver.capabilities.get('deviceName'),
            'automation_name': driver.capabilities.get('automationName')
        }
        
        print(f"Device info: {device_info}")
        
        # Verify basic device info is available
        assert device_info['platform_version'] is not None
        assert device_info['device_name'] is not None
EOF

    # Create requirements for the project
    cat > "$PROJECT_DIR/requirements.txt" << 'EOF'
pytest>=7.4.3
Appium-Python-Client>=2.11.1
selenium>=4.15.2
pytest-html>=4.1.1
EOF

    # Create test runner script
    cat > "$PROJECT_DIR/run_tests.sh" << 'EOF'
#!/bin/bash

# Sample Test Runner
echo "Starting Android app tests..."

# Check if Appium server is running
if ! curl -s http://127.0.0.1:4723/wd/hub/status > /dev/null; then
    echo "Starting Appium server..."
    appium &
    APPIUM_PID=$!
    sleep 5
else
    echo "Appium server already running"
fi

# Run tests
python3 -m pytest . -v --html=../../../reports/test_report.html --self-contained-html

# Cleanup
if [[ -n "$APPIUM_PID" ]]; then
    echo "Stopping Appium server..."
    kill $APPIUM_PID
fi

echo "Tests completed. Report available at reports/test_report.html"
EOF

    chmod +x "$PROJECT_DIR/run_tests.sh"
    
    log_info "Sample test project created at $PROJECT_DIR"
}

verify_installation() {
    log_section "Verifying Installation"
    
    # Check Appium
    if command -v appium &> /dev/null; then
        echo "✓ Appium: $(appium --version)"
    else
        echo "✗ Appium not found"
    fi
    
    # Check Appium doctor
    echo "Running Appium doctor..."
    appium driver doctor uiautomator2 || log_warn "Some Appium doctor checks failed"
    
    # Check Python packages
    echo "Checking Python packages..."
    python3 -c "import appium; print(f'✓ Appium Python Client: {appium.__version__}')" 2>/dev/null || echo "✗ Appium Python Client not found"
    python3 -c "import selenium; print(f'✓ Selenium: {selenium.__version__}')" 2>/dev/null || echo "✗ Selenium not found"
    python3 -c "import pytest; print(f'✓ Pytest: {pytest.__version__}')" 2>/dev/null || echo "✗ Pytest not found"
    
    log_info "Installation verification complete"
}

create_usage_guide() {
    cat > "$TEST_WORKSPACE/TESTING_GUIDE.md" << 'EOF'
# Android Testing Framework Usage Guide

## Quick Start

1. **Setup Device for Testing:**
   ```bash
   cd scripts
   ./adb-dev-setup.sh
   ```

2. **Start Appium Server:**
   ```bash
   appium
   ```

3. **Run Sample Tests:**
   ```bash
   cd projects/sample-app-test
   ./run_tests.sh
   ```

## Test Development Workflow

1. **Create New Test Project:**
   ```bash
   mkdir projects/my-app-test
   cd projects/my-app-test
   cp ../sample-app-test/conftest.py .
   ```

2. **Install App for Testing:**
   ```bash
   python3 scripts/run-tests.py --apk path/to/app.apk --setup-only
   ```

3. **Write Tests:**
   - Use `test_*.py` naming convention
   - Import from `conftest.py` for fixtures
   - Use Appium WebDriver API for interactions

4. **Execute Tests:**
   ```bash
   python3 -m pytest . -v --html=reports/report.html
   ```

## Directory Structure

```
AndroidTesting/
├── config/           # Configuration files
├── projects/         # Test projects
├── reports/         # Test reports
├── scripts/         # Helper scripts
└── resources/       # Test resources
```

## Common Commands

- `appium doctor` - Check Appium setup
- `adb devices` - List connected devices
- `adb logcat` - View device logs
- `pytest --collect-only` - List available tests

EOF

    log_info "Testing guide created"
}

main() {
    log_info "Starting Android Testing Framework Setup"
    
    check_prerequisites
    install_appium_framework
    install_python_testing_tools
    install_node_testing_tools
    create_test_workspace
    setup_appium_config
    create_development_scripts
    create_sample_test_project
    verify_installation
    create_usage_guide
    
    log_info "Testing framework setup completed successfully!"
    echo
    echo "Next steps:"
    echo "1. Connect Android device: adb devices"
    echo "2. Setup device: cd $TEST_WORKSPACE/scripts && ./adb-dev-setup.sh"
    echo "3. Start Appium: appium"
    echo "4. Run sample tests: cd $TEST_WORKSPACE/projects/sample-app-test && ./run_tests.sh"
    echo "5. View guide: cat $TEST_WORKSPACE/TESTING_GUIDE.md"
}

main "$@"