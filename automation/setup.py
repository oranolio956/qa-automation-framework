#!/usr/bin/env python3
"""
Tinder Automation System Setup Script
Handles installation, configuration, and validation of the automation system
"""

import os
import sys
import subprocess
import logging
import json
from pathlib import Path
import requests
import zipfile
import shutil

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AutomationSetup:
    """Setup manager for Tinder automation system"""
    
    def __init__(self):
        self.automation_dir = os.path.dirname(__file__)
        self.project_root = os.path.dirname(self.automation_dir)
        self.config = {}
        
    def install_python_dependencies(self) -> bool:
        """Install Python dependencies"""
        logger.info("Installing Python dependencies...")
        
        try:
            requirements_file = os.path.join(self.automation_dir, "requirements.txt")
            
            if not os.path.exists(requirements_file):
                logger.error("requirements.txt not found")
                return False
            
            cmd = [sys.executable, "-m", "pip", "install", "-r", requirements_file]
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            logger.info("✅ Python dependencies installed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to install Python dependencies: {e}")
            logger.error(f"stderr: {e.stderr}")
            return False
    
    def setup_android_sdk(self) -> bool:
        """Set up Android SDK if not present"""
        logger.info("Checking Android SDK setup...")
        
        # Check if ANDROID_HOME is set
        android_home = os.environ.get('ANDROID_HOME')
        
        if not android_home:
            # Try common locations
            possible_paths = [
                os.path.expanduser("~/Android/Sdk"),
                os.path.expanduser("~/Library/Android/sdk"),
                "/usr/local/android-sdk"
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    android_home = path
                    os.environ['ANDROID_HOME'] = path
                    logger.info(f"Found Android SDK at: {path}")
                    break
        
        if not android_home or not os.path.exists(android_home):
            logger.warning("❌ Android SDK not found")
            logger.info("Please install Android SDK and set ANDROID_HOME environment variable")
            logger.info("Download from: https://developer.android.com/studio#command-tools")
            return False
        
        # Check if emulator exists
        emulator_path = os.path.join(android_home, "emulator", "emulator")
        if not os.path.exists(emulator_path):
            logger.warning("❌ Android emulator not found in SDK")
            return False
        
        logger.info("✅ Android SDK setup verified")
        return True
    
    def setup_redis(self) -> bool:
        """Check Redis setup"""
        logger.info("Checking Redis setup...")
        
        try:
            import redis
            client = redis.Redis(host='localhost', port=6379, db=0)
            client.ping()
            logger.info("✅ Redis connection successful")
            return True
            
        except Exception as e:
            logger.warning(f"❌ Redis connection failed: {e}")
            logger.info("Please install and start Redis server:")
            logger.info("  - Ubuntu/Debian: sudo apt-get install redis-server")
            logger.info("  - macOS: brew install redis")
            logger.info("  - Windows: Download from https://redis.io/download")
            return False
    
    def create_directory_structure(self):
        """Create necessary directories"""
        logger.info("Creating directory structure...")
        
        directories = [
            "apks",
            "logs",
            "results",
            "temp",
            "config"
        ]
        
        for dir_name in directories:
            dir_path = os.path.join(self.automation_dir, dir_name)
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {dir_path}")
    
    def create_config_template(self):
        """Create configuration template"""
        logger.info("Creating configuration template...")
        
        config_template = {
            "proxy": {
                "brightdata_url": "http://user:pass@brd.superproxy.io:9222",
                "verify_on_startup": True
            },
            "sms": {
                "twilio_account_sid": "your_account_sid",
                "twilio_auth_token": "your_auth_token",
                "phone_numbers": []
            },
            "automation": {
                "default_aggressiveness": 0.3,
                "max_parallel_accounts": 5,
                "warming_enabled": True,
                "headless_emulators": True
            },
            "android": {
                "sdk_path": "${ANDROID_HOME}",
                "emulator_ram": "4096M",
                "emulator_storage": "6144M"
            },
            "output": {
                "results_directory": "./results",
                "log_level": "INFO",
                "save_screenshots": True
            }
        }
        
        config_path = os.path.join(self.automation_dir, "config", "automation_config.json")
        
        with open(config_path, 'w') as f:
            json.dump(config_template, f, indent=2)
        
        logger.info(f"Configuration template created: {config_path}")
        logger.info("Please update the configuration file with your actual credentials")
    
    def download_apk_placeholders(self):
        """Create APK placeholder information"""
        logger.info("Setting up APK directory...")
        
        apk_dir = os.path.join(self.automation_dir, "apks")
        
        # Create README for APK requirements
        apk_readme = """# APK Requirements

This directory should contain the following APK files:

## Tinder APK
- Filename: tinder.apk
- Source: APKMirror, APKPure, or official source
- Version: Latest stable version
- Architecture: Universal or arm64-v8a

## Snapchat APK  
- Filename: snapchat.apk
- Source: APKMirror, APKPure, or official source
- Version: Latest stable version
- Architecture: Universal or arm64-v8a

## Download Instructions

1. Visit APKMirror.com or APKPure.com
2. Search for "Tinder" and "Snapchat"
3. Download the latest stable versions
4. Rename files to tinder.apk and snapchat.apk
5. Place in this directory

## Security Note

Only download APKs from trusted sources. Verify checksums when possible.

## Legal Note

Ensure you comply with app terms of service and local laws.
"""
        
        readme_path = os.path.join(apk_dir, "README.md")
        with open(readme_path, 'w') as f:
            f.write(apk_readme)
        
        logger.info(f"APK setup instructions created: {readme_path}")
    
    def run_system_tests(self) -> bool:
        """Run basic system tests"""
        logger.info("Running system tests...")
        
        try:
            test_script = os.path.join(self.automation_dir, "test_system.py")
            
            if not os.path.exists(test_script):
                logger.warning("Test script not found, skipping tests")
                return True
            
            # Run basic validation only
            cmd = [sys.executable, test_script]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                logger.info("✅ System tests passed")
                return True
            else:
                logger.warning("❌ Some system tests failed")
                logger.info("Check test output for details")
                return False
                
        except Exception as e:
            logger.error(f"Failed to run system tests: {e}")
            return False
    
    def setup_environment_file(self):
        """Create environment file template"""
        logger.info("Creating environment file template...")
        
        env_template = """# Tinder Automation Environment Variables

# Bright Data Proxy Configuration
BRIGHTDATA_PROXY_URL=http://user:pass@brd.superproxy.io:9222

# Twilio SMS Configuration  
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token

# Redis Configuration
REDIS_URL=redis://localhost:6379

# Android SDK Configuration
ANDROID_HOME=/path/to/android/sdk

# Automation Configuration
AUTOMATION_LOG_LEVEL=INFO
AUTOMATION_RESULTS_DIR=./results
AUTOMATION_MAX_EMULATORS=5

# Optional: Specific emulator settings
EMULATOR_RAM_SIZE=4096M
EMULATOR_STORAGE_SIZE=6144M
EMULATOR_GPU_MODE=swiftshader_indirect
"""
        
        env_path = os.path.join(self.automation_dir, ".env.template")
        
        with open(env_path, 'w') as f:
            f.write(env_template)
        
        logger.info(f"Environment template created: {env_path}")
        logger.info("Copy .env.template to .env and update with your credentials")
    
    def run_full_setup(self) -> bool:
        """Run complete setup process"""
        logger.info("🚀 Starting Tinder Automation System Setup")
        logger.info("=" * 50)
        
        setup_steps = [
            ("Creating directory structure", self.create_directory_structure),
            ("Installing Python dependencies", self.install_python_dependencies),
            ("Checking Android SDK", self.setup_android_sdk),
            ("Checking Redis", self.setup_redis),
            ("Creating configuration template", self.create_config_template),
            ("Setting up APK directory", self.download_apk_placeholders),
            ("Creating environment template", self.setup_environment_file),
            ("Running system tests", self.run_system_tests),
        ]
        
        results = {}
        
        for step_name, step_function in setup_steps:
            logger.info(f"\n📋 {step_name}...")
            try:
                if callable(step_function):
                    result = step_function()
                    if result is None:
                        result = True  # Assume success if no return value
                else:
                    result = step_function
                    
                results[step_name] = result
                status = "✅" if result else "❌"
                logger.info(f"{status} {step_name}: {'COMPLETED' if result else 'FAILED'}")
                
            except Exception as e:
                logger.error(f"❌ {step_name} failed with error: {e}")
                results[step_name] = False
        
        # Print summary
        logger.info("\n" + "=" * 50)
        logger.info("SETUP SUMMARY")
        logger.info("=" * 50)
        
        total_steps = len(results)
        successful_steps = sum(1 for result in results.values() if result)
        
        logger.info(f"Steps completed: {successful_steps}/{total_steps}")
        logger.info(f"Success rate: {successful_steps/total_steps*100:.1f}%")
        
        if successful_steps == total_steps:
            logger.info("✅ Setup completed successfully!")
            self._print_next_steps()
        else:
            logger.warning("⚠️  Setup completed with issues")
            self._print_failed_steps(results)
        
        return successful_steps == total_steps
    
    def _print_next_steps(self):
        """Print next steps after successful setup"""
        logger.info("\n📋 NEXT STEPS:")
        logger.info("1. Update .env file with your credentials")
        logger.info("2. Download Tinder and Snapchat APKs to apks/ directory")
        logger.info("3. Start Redis server: redis-server")
        logger.info("4. Test the system: python test_system.py")
        logger.info("5. Run automation: python main_orchestrator.py --tinder-accounts 1")
        logger.info("\n📚 See README.md for detailed usage instructions")
    
    def _print_failed_steps(self, results):
        """Print information about failed steps"""
        logger.info("\n❌ FAILED STEPS:")
        for step_name, result in results.items():
            if not result:
                logger.info(f"- {step_name}")
        
        logger.info("\n📚 Please resolve the failed steps and run setup again")

def main():
    """Main setup entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Tinder Automation System Setup')
    parser.add_argument('--skip-tests', action='store_true', help='Skip system tests during setup')
    parser.add_argument('--dependencies-only', action='store_true', help='Only install Python dependencies')
    
    args = parser.parse_args()
    
    setup = AutomationSetup()
    
    if args.dependencies_only:
        success = setup.install_python_dependencies()
        return 0 if success else 1
    
    # Run full setup
    success = setup.run_full_setup()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())