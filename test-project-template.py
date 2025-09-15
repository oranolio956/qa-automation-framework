#!/usr/bin/env python3
"""
Android Test Project Template Generator
Creates structured test projects for Android app testing
"""

import os
import sys
import argparse
from pathlib import Path
import json

class TestProjectTemplate:
    def __init__(self, project_name, workspace_dir):
        self.project_name = project_name
        self.workspace_dir = Path(workspace_dir)
        self.project_dir = self.workspace_dir / "projects" / project_name
        
    def create_project_structure(self):
        """Create basic project directory structure"""
        directories = [
            self.project_dir,
            self.project_dir / "tests",
            self.project_dir / "pages",
            self.project_dir / "utils", 
            self.project_dir / "data",
            self.project_dir / "reports"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        print(f"✓ Created project structure for {self.project_name}")
    
    def create_conftest_py(self):
        """Create pytest configuration file"""
        content = '''"""
Pytest configuration for Android app testing
"""

import pytest
import os
from appium import webdriver
from appium.options.android import UiAutomator2Options
from utils.device_manager import DeviceManager
from utils.app_manager import AppManager

@pytest.fixture(scope="session")
def device_manager():
    """Device management fixture"""
    manager = DeviceManager()
    yield manager
    manager.cleanup()

@pytest.fixture(scope="session") 
def app_manager():
    """App management fixture"""
    manager = AppManager()
    yield manager
    manager.cleanup()

@pytest.fixture
def driver(device_manager, app_manager):
    """Appium WebDriver fixture"""
    
    options = UiAutomator2Options()
    capabilities = {
        "platformName": "Android",
        "automationName": "UiAutomator2", 
        "deviceName": device_manager.get_device_name(),
        "platformVersion": device_manager.get_platform_version(),
        "newCommandTimeout": 300,
        "uiautomator2ServerInstallTimeout": 120000,
        "autoGrantPermissions": True,
        "noReset": False
    }
    
    # Add app path if specified
    app_path = app_manager.get_app_path()
    if app_path:
        capabilities["app"] = app_path
    
    options.load_capabilities(capabilities)
    
    driver = webdriver.Remote('http://127.0.0.1:4723/wd/hub', options=options)
    driver.implicitly_wait(10)
    
    yield driver
    
    driver.quit()

@pytest.fixture
def test_data():
    """Test data fixture"""
    data_file = os.path.join(os.path.dirname(__file__), "data", "test_data.json")
    if os.path.exists(data_file):
        with open(data_file, 'r') as f:
            return json.load(f)
    return {}

def pytest_configure(config):
    """Pytest configuration hook"""
    # Create reports directory if it doesn't exist
    reports_dir = os.path.join(os.path.dirname(__file__), "reports")
    os.makedirs(reports_dir, exist_ok=True)

def pytest_html_report_title(report):
    """Customize HTML report title"""
    report.title = f"Android Test Report - {os.path.basename(os.path.dirname(__file__))}"
'''
        
        with open(self.project_dir / "conftest.py", "w") as f:
            f.write(content)
        
        print("✓ Created conftest.py")
    
    def create_page_objects(self):
        """Create page object pattern examples"""
        
        # Base page object
        base_page_content = '''"""
Base Page Object for Android app testing
"""

from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

class BasePage:
    """Base page object with common functionality"""
    
    def __init__(self, driver, timeout=30):
        self.driver = driver
        self.timeout = timeout
        self.wait = WebDriverWait(driver, timeout)
    
    def find_element(self, locator):
        """Find element with wait"""
        return self.wait.until(EC.presence_of_element_located(locator))
    
    def find_elements(self, locator):
        """Find multiple elements"""
        return self.driver.find_elements(*locator)
    
    def click_element(self, locator):
        """Click element with wait"""
        element = self.wait.until(EC.element_to_be_clickable(locator))
        element.click()
    
    def enter_text(self, locator, text):
        """Enter text in element"""
        element = self.find_element(locator)
        element.clear()
        element.send_keys(text)
    
    def get_text(self, locator):
        """Get text from element"""
        element = self.find_element(locator)
        return element.text
    
    def is_element_present(self, locator):
        """Check if element is present"""
        try:
            self.driver.find_element(*locator)
            return True
        except:
            return False
    
    def wait_for_element(self, locator, timeout=None):
        """Wait for element to be present"""
        wait_time = timeout or self.timeout
        wait = WebDriverWait(self.driver, wait_time)
        return wait.until(EC.presence_of_element_located(locator))
    
    def take_screenshot(self, name="screenshot"):
        """Take screenshot"""
        screenshot_path = f"reports/{name}.png"
        self.driver.save_screenshot(screenshot_path)
        return screenshot_path
    
    def scroll_to_element(self, locator):
        """Scroll to element"""
        element = self.find_element(locator)
        self.driver.execute_script("arguments[0].scrollIntoView();", element)
    
    def get_current_activity(self):
        """Get current Android activity"""
        return self.driver.current_activity
    
    def go_back(self):
        """Press back button"""
        self.driver.back()
    
    def get_device_size(self):
        """Get device screen size"""
        return self.driver.get_window_size()
'''
        
        with open(self.project_dir / "pages" / "base_page.py", "w") as f:
            f.write(base_page_content)
        
        # Example page object
        example_page_content = '''"""
Example Page Object
Customize this for your specific app
"""

from appium.webdriver.common.appiumby import AppiumBy
from pages.base_page import BasePage

class MainPage(BasePage):
    """Main page of the app"""
    
    # Locators
    MAIN_BUTTON = (AppiumBy.ID, "com.example.app:id/main_button")
    TITLE_TEXT = (AppiumBy.ID, "com.example.app:id/title")
    MENU_BUTTON = (AppiumBy.ACCESSIBILITY_ID, "Menu")
    SEARCH_FIELD = (AppiumBy.CLASS_NAME, "android.widget.EditText")
    
    def __init__(self, driver):
        super().__init__(driver)
    
    def click_main_button(self):
        """Click the main button"""
        self.click_element(self.MAIN_BUTTON)
    
    def get_title(self):
        """Get page title"""
        return self.get_text(self.TITLE_TEXT)
    
    def open_menu(self):
        """Open navigation menu"""
        self.click_element(self.MENU_BUTTON)
    
    def search(self, query):
        """Perform search"""
        self.enter_text(self.SEARCH_FIELD, query)
    
    def verify_page_loaded(self):
        """Verify page is loaded"""
        return self.is_element_present(self.TITLE_TEXT)

class LoginPage(BasePage):
    """Login page example"""
    
    # Locators
    USERNAME_FIELD = (AppiumBy.ID, "username")
    PASSWORD_FIELD = (AppiumBy.ID, "password") 
    LOGIN_BUTTON = (AppiumBy.ID, "login_button")
    ERROR_MESSAGE = (AppiumBy.ID, "error_message")
    
    def __init__(self, driver):
        super().__init__(driver)
    
    def login(self, username, password):
        """Perform login"""
        self.enter_text(self.USERNAME_FIELD, username)
        self.enter_text(self.PASSWORD_FIELD, password)
        self.click_element(self.LOGIN_BUTTON)
    
    def get_error_message(self):
        """Get login error message"""
        if self.is_element_present(self.ERROR_MESSAGE):
            return self.get_text(self.ERROR_MESSAGE)
        return None
'''
        
        with open(self.project_dir / "pages" / "example_pages.py", "w") as f:
            f.write(example_page_content)
        
        # Create __init__.py files
        (self.project_dir / "pages" / "__init__.py").touch()
        
        print("✓ Created page objects")
    
    def create_utility_modules(self):
        """Create utility modules"""
        
        # Device manager
        device_manager_content = '''"""
Device Management Utilities
"""

import subprocess
import json

class DeviceManager:
    """Manage Android device/emulator"""
    
    def __init__(self):
        self.device_info = self._get_device_info()
    
    def _get_device_info(self):
        """Get connected device information"""
        try:
            result = subprocess.run(['adb', 'devices', '-l'], 
                                  capture_output=True, text=True)
            lines = result.stdout.strip().split('\\n')[1:]  # Skip header
            
            for line in lines:
                if 'device' in line:
                    return {'connected': True, 'details': line}
            
            return {'connected': False}
        except Exception as e:
            return {'connected': False, 'error': str(e)}
    
    def get_device_name(self):
        """Get device name"""
        try:
            result = subprocess.run(['adb', 'shell', 'getprop', 'ro.product.model'],
                                  capture_output=True, text=True)
            return result.stdout.strip() or "AndroidDevice"
        except:
            return "AndroidDevice"
    
    def get_platform_version(self):
        """Get Android version"""
        try:
            result = subprocess.run(['adb', 'shell', 'getprop', 'ro.build.version.release'],
                                  capture_output=True, text=True)
            return result.stdout.strip() or "9.0"
        except:
            return "9.0"
    
    def install_app(self, apk_path):
        """Install APK on device"""
        try:
            result = subprocess.run(['adb', 'install', '-r', apk_path],
                                  capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    def uninstall_app(self, package_name):
        """Uninstall app from device"""
        try:
            result = subprocess.run(['adb', 'uninstall', package_name],
                                  capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    def clear_app_data(self, package_name):
        """Clear app data"""
        try:
            subprocess.run(['adb', 'shell', 'pm', 'clear', package_name])
            return True
        except:
            return False
    
    def take_screenshot(self, path):
        """Take device screenshot"""
        try:
            subprocess.run(['adb', 'exec-out', 'screencap', '-p'], 
                         stdout=open(path, 'wb'))
            return True
        except:
            return False
    
    def get_logcat(self, filter_tag=None):
        """Get device logs"""
        try:
            cmd = ['adb', 'logcat', '-d']
            if filter_tag:
                cmd.extend(['-s', filter_tag])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.stdout
        except:
            return ""
    
    def cleanup(self):
        """Cleanup device manager"""
        pass
'''
        
        with open(self.project_dir / "utils" / "device_manager.py", "w") as f:
            f.write(device_manager_content)
        
        # App manager
        app_manager_content = '''"""
App Management Utilities
"""

import os
from pathlib import Path

class AppManager:
    """Manage app installation and configuration"""
    
    def __init__(self, app_path=None):
        self.app_path = app_path
        self.package_name = None
    
    def set_app_path(self, path):
        """Set path to APK file"""
        if os.path.exists(path):
            self.app_path = path
            return True
        return False
    
    def get_app_path(self):
        """Get current app path"""
        return self.app_path
    
    def set_package_name(self, package):
        """Set app package name"""
        self.package_name = package
    
    def get_package_name(self):
        """Get app package name"""
        return self.package_name
    
    def verify_app_installed(self, device_manager):
        """Verify app is installed on device"""
        if not self.package_name:
            return False
        
        try:
            import subprocess
            result = subprocess.run(['adb', 'shell', 'pm', 'list', 'packages', 
                                   self.package_name], capture_output=True, text=True)
            return self.package_name in result.stdout
        except:
            return False
    
    def launch_app(self, driver):
        """Launch app using driver"""
        if self.package_name:
            driver.activate_app(self.package_name)
    
    def close_app(self, driver):
        """Close app using driver"""
        if self.package_name:
            driver.terminate_app(self.package_name)
    
    def cleanup(self):
        """Cleanup app manager"""
        pass
'''
        
        with open(self.project_dir / "utils" / "app_manager.py", "w") as f:
            f.write(app_manager_content)
        
        # Test helpers
        test_helpers_content = '''"""
Test Helper Utilities
"""

import time
import random
import string
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class TestHelpers:
    """Common test helper functions"""
    
    @staticmethod
    def generate_random_string(length=10):
        """Generate random string"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    @staticmethod
    def generate_random_email():
        """Generate random email address"""
        username = TestHelpers.generate_random_string(8)
        return f"{username}@test.com"
    
    @staticmethod
    def wait_and_retry(func, max_attempts=3, delay=1):
        """Retry function with delay"""
        for attempt in range(max_attempts):
            try:
                return func()
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise e
                time.sleep(delay)
    
    @staticmethod
    def scroll_to_find_element(driver, locator, max_scrolls=5):
        """Scroll to find element"""
        for _ in range(max_scrolls):
            try:
                element = driver.find_element(*locator)
                return element
            except:
                # Scroll down
                driver.swipe(500, 1500, 500, 500, 1000)
                time.sleep(1)
        return None
    
    @staticmethod
    def wait_for_element_to_disappear(driver, locator, timeout=10):
        """Wait for element to disappear"""
        wait = WebDriverWait(driver, timeout)
        return wait.until_not(EC.presence_of_element_located(locator))
    
    @staticmethod
    def take_screenshot_on_failure(driver, test_name):
        """Take screenshot when test fails"""
        timestamp = int(time.time())
        filename = f"reports/{test_name}_failure_{timestamp}.png"
        driver.save_screenshot(filename)
        return filename
'''
        
        with open(self.project_dir / "utils" / "test_helpers.py", "w") as f:
            f.write(test_helpers_content)
        
        # Create __init__.py files
        (self.project_dir / "utils" / "__init__.py").touch()
        
        print("✓ Created utility modules")
    
    def create_sample_tests(self):
        """Create sample test files"""
        
        # Basic functionality test
        basic_test_content = '''"""
Basic App Functionality Tests
"""

import pytest
import time
from pages.example_pages import MainPage, LoginPage
from utils.test_helpers import TestHelpers

class TestBasicFunctionality:
    """Test basic app functionality"""
    
    def test_app_launch(self, driver):
        """Test app launches successfully"""
        # Wait for app to load
        time.sleep(3)
        
        # Verify app is running
        current_activity = driver.current_activity
        assert current_activity is not None, "App should be running"
        
        print(f"Current activity: {current_activity}")
        
        # Take screenshot
        driver.save_screenshot("reports/app_launch.png")
    
    def test_main_page_elements(self, driver):
        """Test main page elements are present"""
        main_page = MainPage(driver)
        
        # Wait for page to load
        time.sleep(2)
        
        # Verify page loaded
        assert main_page.verify_page_loaded(), "Main page should load"
        
        # Take screenshot
        main_page.take_screenshot("main_page_loaded")
    
    @pytest.mark.smoke
    def test_navigation(self, driver):
        """Test basic navigation"""
        main_page = MainPage(driver)
        
        # Try navigation if menu exists
        if main_page.is_element_present(main_page.MENU_BUTTON):
            main_page.open_menu()
            time.sleep(1)
            
            # Go back
            main_page.go_back()
            time.sleep(1)
            
            assert main_page.verify_page_loaded(), "Should return to main page"
    
    def test_device_properties(self, driver, device_manager):
        """Test device properties access"""
        device_name = device_manager.get_device_name()
        platform_version = device_manager.get_platform_version()
        
        print(f"Device: {device_name}")
        print(f"Android version: {platform_version}")
        
        assert device_name is not None
        assert platform_version is not None
        
        # Get screen size
        size = driver.get_window_size()
        print(f"Screen size: {size}")
        
        assert size['width'] > 0
        assert size['height'] > 0
'''
        
        with open(self.project_dir / "tests" / "test_basic_functionality.py", "w") as f:
            f.write(basic_test_content)
        
        # Login test example
        login_test_content = '''"""
Login Functionality Tests
"""

import pytest
from pages.example_pages import LoginPage
from utils.test_helpers import TestHelpers

class TestLogin:
    """Test login functionality"""
    
    @pytest.mark.login
    def test_valid_login(self, driver, test_data):
        """Test login with valid credentials"""
        login_page = LoginPage(driver)
        
        # Get test credentials
        username = test_data.get('valid_username', 'testuser')
        password = test_data.get('valid_password', 'testpass')
        
        # Perform login
        login_page.login(username, password)
        
        # Verify login success (customize based on your app)
        # This is a placeholder - adapt to your app's behavior
        time.sleep(2)
        current_activity = driver.current_activity
        print(f"After login activity: {current_activity}")
    
    @pytest.mark.login
    def test_invalid_login(self, driver):
        """Test login with invalid credentials"""
        login_page = LoginPage(driver)
        
        # Use random credentials
        username = TestHelpers.generate_random_string()
        password = TestHelpers.generate_random_string()
        
        # Perform login
        login_page.login(username, password)
        
        # Check for error message
        error_msg = login_page.get_error_message()
        if error_msg:
            print(f"Error message: {error_msg}")
            assert "error" in error_msg.lower() or "invalid" in error_msg.lower()
    
    @pytest.mark.login
    def test_empty_credentials(self, driver):
        """Test login with empty credentials"""
        login_page = LoginPage(driver)
        
        # Try login with empty fields
        login_page.login("", "")
        
        # Should show validation error
        time.sleep(1)
        
        # Take screenshot for verification
        login_page.take_screenshot("empty_credentials_test")
'''
        
        with open(self.project_dir / "tests" / "test_login.py", "w") as f:
            f.write(login_test_content)
        
        # Create __init__.py files
        (self.project_dir / "tests" / "__init__.py").touch()
        
        print("✓ Created sample tests")
    
    def create_test_data(self):
        """Create test data files"""
        
        test_data = {
            "valid_username": "demo_user",
            "valid_password": "demo_pass", 
            "test_emails": [
                "test1@example.com",
                "test2@example.com"
            ],
            "app_config": {
                "package_name": "com.example.testapp",
                "main_activity": ".MainActivity"
            },
            "test_scenarios": {
                "basic_flow": {
                    "steps": [
                        "Launch app",
                        "Verify main screen",
                        "Navigate to feature",
                        "Verify feature works"
                    ]
                }
            }
        }
        
        with open(self.project_dir / "data" / "test_data.json", "w") as f:
            json.dump(test_data, f, indent=2)
        
        print("✓ Created test data")
    
    def create_project_config(self):
        """Create project configuration files"""
        
        # Requirements file
        requirements = [
            "pytest>=7.4.3",
            "Appium-Python-Client>=2.11.1",
            "selenium>=4.15.2",
            "pytest-html>=4.1.1",
            "pytest-xdist>=3.3.1",
            "allure-pytest>=2.13.2"
        ]
        
        with open(self.project_dir / "requirements.txt", "w") as f:
            f.write("\n".join(requirements))
        
        # Pytest configuration
        pytest_ini = '''[tool:pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
python_classes = Test*
addopts = 
    -v
    --tb=short
    --html=reports/report.html
    --self-contained-html
markers =
    smoke: Smoke tests
    regression: Regression tests  
    login: Login related tests
    slow: Slow running tests
'''
        
        with open(self.project_dir / "pytest.ini", "w") as f:
            f.write(pytest_ini)
        
        # Run script
        run_script = '''#!/bin/bash

# Test execution script for ''' + self.project_name + '''

set -e

echo "Starting test execution for ''' + self.project_name + '''"

# Check if virtual environment exists
if [[ ! -d "venv" ]]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check ADB connection
echo "Checking ADB connection..."
if ! adb devices | grep -q "device$"; then
    echo "Error: No Android device connected"
    echo "Please connect a device and enable USB debugging"
    exit 1
fi

# Check if Appium server is running
echo "Checking Appium server..."
if ! curl -s http://127.0.0.1:4723/wd/hub/status > /dev/null; then
    echo "Warning: Appium server not running"
    echo "Please start Appium server: appium"
    exit 1
fi

# Run tests based on arguments
case "${1:-all}" in
    smoke)
        echo "Running smoke tests..."
        python -m pytest -m smoke
        ;;
    login)
        echo "Running login tests..."
        python -m pytest -m login
        ;;
    basic)
        echo "Running basic functionality tests..."
        python -m pytest tests/test_basic_functionality.py
        ;;
    all|*)
        echo "Running all tests..."
        python -m pytest
        ;;
esac

echo "Test execution completed!"
echo "Report available at: reports/report.html"
'''
        
        with open(self.project_dir / "run_tests.sh", "w") as f:
            f.write(run_script)
        
        os.chmod(self.project_dir / "run_tests.sh", 0o755)
        
        print("✓ Created project configuration")
    
    def create_readme(self):
        """Create project README"""
        
        readme_content = f'''# {self.project_name} - Android Test Project

Automated testing project for Android app using Appium and pytest.

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure app details:**
   - Update `data/test_data.json` with your app's package name
   - Modify page objects in `pages/` to match your app's UI

3. **Connect Android device:**
   ```bash
   adb devices
   ```

4. **Start Appium server:**
   ```bash
   appium
   ```

## Running Tests

```bash
# Run all tests
./run_tests.sh

# Run specific test types
./run_tests.sh smoke
./run_tests.sh login
./run_tests.sh basic

# Run specific test file
python -m pytest tests/test_basic_functionality.py -v
```

## Project Structure

```
{self.project_name}/
├── tests/                 # Test files
├── pages/                 # Page object models
├── utils/                 # Utility modules
├── data/                  # Test data files
├── reports/               # Test reports
├── conftest.py           # Pytest configuration
├── requirements.txt      # Python dependencies
└── run_tests.sh         # Test execution script
```

## Page Objects

- `pages/base_page.py` - Base page object with common methods
- `pages/example_pages.py` - Example page objects (customize for your app)

## Test Categories

- **Smoke tests**: Basic functionality verification
- **Login tests**: Authentication and login flows
- **Regression tests**: Full feature verification

## Customization

1. **Update page objects** to match your app's UI elements
2. **Modify test data** in `data/test_data.json`
3. **Add new test files** in `tests/` directory
4. **Extend utility functions** in `utils/` modules

## Reports

Test reports are generated in `reports/` directory:
- HTML report: `reports/report.html`
- Screenshots: `reports/*.png`

## Tips

- Use `pytest -k "test_name"` to run specific tests
- Add `@pytest.mark.slow` for long-running tests
- Take screenshots on failures for debugging
- Use page object pattern for maintainable tests
'''
        
        with open(self.project_dir / "README.md", "w") as f:
            f.write(readme_content)
        
        print("✓ Created project README")
    
    def generate_project(self):
        """Generate complete test project"""
        print(f"Generating test project: {self.project_name}")
        
        self.create_project_structure()
        self.create_conftest_py()
        self.create_page_objects()
        self.create_utility_modules() 
        self.create_sample_tests()
        self.create_test_data()
        self.create_project_config()
        self.create_readme()
        
        print(f"\n✓ Project '{self.project_name}' created successfully!")
        print(f"Location: {self.project_dir}")
        print("\nNext steps:")
        print(f"1. cd {self.project_dir}")
        print("2. Customize page objects for your app")
        print("3. Update test data with your app details")
        print("4. Run tests: ./run_tests.sh")

def main():
    parser = argparse.ArgumentParser(description="Generate Android test project template")
    parser.add_argument("project_name", help="Name of the test project")
    parser.add_argument("--workspace", default="~/AndroidTesting", 
                       help="Workspace directory (default: ~/AndroidTesting)")
    
    args = parser.parse_args()
    
    workspace_dir = os.path.expanduser(args.workspace)
    
    if not os.path.exists(workspace_dir):
        print(f"Error: Workspace directory not found: {workspace_dir}")
        print("Please run testing-framework-setup.sh first")
        sys.exit(1)
    
    template = TestProjectTemplate(args.project_name, workspace_dir)
    template.generate_project()

if __name__ == "__main__":
    main()