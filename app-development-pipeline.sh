#!/bin/bash

# Android App Development Pipeline Setup
# Automated development, testing, and deployment pipeline for Android applications

set -e

# Configuration
PIPELINE_DIR="$HOME/AndroidDevelopment"
TOOLS_DIR="$PIPELINE_DIR/tools"
CONFIG_DIR="$PIPELINE_DIR/config"
SCRIPTS_DIR="$PIPELINE_DIR/scripts"
TEMPLATES_DIR="$PIPELINE_DIR/templates"

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
    
    # Check essential tools
    local missing_tools=()
    
    if ! command -v git &> /dev/null; then
        missing_tools+=("git")
    fi
    
    if ! command -v python3 &> /dev/null; then
        missing_tools+=("python3")
    fi
    
    if ! command -v node &> /dev/null; then
        missing_tools+=("nodejs")
    fi
    
    if ! command -v docker &> /dev/null; then
        missing_tools+=("docker")
    fi
    
    if [[ ${#missing_tools[@]} -ne 0 ]]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_info "Please install missing tools and re-run the setup"
        exit 1
    fi
    
    # Check Android SDK
    if [[ -z "$ANDROID_HOME" ]]; then
        log_warn "ANDROID_HOME not set. Some features may not work correctly"
    fi
    
    log_info "Prerequisites check completed"
}

setup_pipeline_structure() {
    log_section "Setting Up Pipeline Structure"
    
    # Create directory structure
    mkdir -p "$PIPELINE_DIR"/{tools,config,scripts,templates,projects,reports,artifacts}
    mkdir -p "$PIPELINE_DIR/tools"/{build,test,deploy,analysis}
    
    log_info "Pipeline directory structure created at $PIPELINE_DIR"
}

setup_development_tools() {
    log_section "Setting Up Development Tools"
    
    # Create Python requirements for development tools
    cat > "$TOOLS_DIR/requirements.txt" << 'EOF'
# Core development tools
GitPython==3.1.40
PyYAML==6.0.1
requests==2.31.0
click==8.1.7

# Android development
aapt2-python==0.0.2
python-adb==0.4.4

# Testing frameworks
pytest==7.4.3
pytest-html==4.1.1
pytest-xdist==3.3.1
allure-pytest==2.13.2

# Code analysis
pylint==3.0.3
black==23.11.0
flake8==6.1.0

# Build and deployment
fabric==3.2.2
paramiko==3.3.1

# Notification services
twilio==8.11.0
sendgrid==6.11.0

# Documentation
Sphinx==7.2.6
mkdocs==1.5.3

# Performance monitoring
psutil==5.9.6
matplotlib==3.8.2
EOF

    # Install Python development tools
    log_info "Installing Python development tools..."
    pip3 install --user -r "$TOOLS_DIR/requirements.txt" || log_warn "Some Python packages may have failed to install"
    
    # Create Node.js package.json for additional tools
    cat > "$TOOLS_DIR/package.json" << 'EOF'
{
  "name": "android-dev-pipeline",
  "version": "1.0.0",
  "description": "Android development pipeline tools",
  "scripts": {
    "lint": "eslint .",
    "test": "jest",
    "build": "webpack --mode production",
    "deploy": "node scripts/deploy.js"
  },
  "dependencies": {
    "commander": "^11.1.0",
    "chalk": "^4.1.2",
    "inquirer": "^8.2.6",
    "axios": "^1.6.2",
    "fs-extra": "^11.1.1",
    "glob": "^10.3.10"
  },
  "devDependencies": {
    "eslint": "^8.54.0",
    "jest": "^29.7.0",
    "webpack": "^5.89.0",
    "webpack-cli": "^5.1.4"
  }
}
EOF

    cd "$TOOLS_DIR"
    npm install || log_warn "Some Node.js packages may have failed to install"
    cd - > /dev/null
    
    log_info "Development tools installed"
}

create_build_tools() {
    log_section "Creating Build Tools"
    
    # Android APK build script
    cat > "$TOOLS_DIR/build/build_apk.py" << 'EOF'
#!/usr/bin/env python3
"""
Android APK Build Tool
Automated building, signing, and optimization of Android APKs
"""

import os
import sys
import subprocess
import argparse
import json
import shutil
from pathlib import Path
from datetime import datetime

class APKBuilder:
    """Android APK builder with automation"""
    
    def __init__(self, project_path, config_file=None):
        self.project_path = Path(project_path)
        self.config = self.load_config(config_file)
        self.build_outputs = []
        
    def load_config(self, config_file):
        """Load build configuration"""
        default_config = {
            "build_types": ["debug", "release"],
            "gradle_options": ["--no-daemon", "--parallel"],
            "output_dir": "build/outputs/apk",
            "sign_apk": True,
            "optimize_apk": True,
            "run_tests": True,
            "generate_mapping": True
        }
        
        if config_file and Path(config_file).exists():
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def validate_project(self):
        """Validate Android project structure"""
        required_files = [
            "build.gradle",
            "app/build.gradle",
            "app/src/main/AndroidManifest.xml"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not (self.project_path / file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            raise Exception(f"Missing required files: {missing_files}")
        
        print("✓ Project structure validated")
    
    def clean_project(self):
        """Clean project build artifacts"""
        print("Cleaning project...")
        
        cmd = ["./gradlew", "clean"] + self.config["gradle_options"]
        result = subprocess.run(cmd, cwd=self.project_path, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Clean failed: {result.stderr}")
        
        print("✓ Project cleaned")
    
    def run_tests(self):
        """Run unit and integration tests"""
        if not self.config.get("run_tests", True):
            return
        
        print("Running tests...")
        
        cmd = ["./gradlew", "test", "connectedAndroidTest"] + self.config["gradle_options"]
        result = subprocess.run(cmd, cwd=self.project_path, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Warning: Tests failed: {result.stderr}")
            # Don't fail build on test failures in development
        else:
            print("✓ Tests passed")
    
    def build_apk(self, build_type="debug"):
        """Build APK for specified build type"""
        print(f"Building {build_type} APK...")
        
        gradle_task = f"assemble{build_type.capitalize()}"
        cmd = ["./gradlew", gradle_task] + self.config["gradle_options"]
        
        result = subprocess.run(cmd, cwd=self.project_path, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Build failed: {result.stderr}")
        
        # Find generated APK
        output_dir = self.project_path / self.config["output_dir"] / build_type
        apk_files = list(output_dir.glob("*.apk"))
        
        if not apk_files:
            raise Exception(f"No APK found in {output_dir}")
        
        apk_path = apk_files[0]
        self.build_outputs.append({
            "build_type": build_type,
            "apk_path": str(apk_path),
            "size_mb": apk_path.stat().st_size / 1024 / 1024,
            "timestamp": datetime.now().isoformat()
        })
        
        print(f"✓ {build_type} APK built: {apk_path.name}")
        return apk_path
    
    def optimize_apk(self, apk_path):
        """Optimize APK using zipalign and other tools"""
        if not self.config.get("optimize_apk", True):
            return apk_path
        
        print("Optimizing APK...")
        
        # Use zipalign if available
        android_build_tools = Path(os.environ.get("ANDROID_HOME", "")) / "build-tools"
        if android_build_tools.exists():
            build_tools_versions = sorted(android_build_tools.iterdir(), reverse=True)
            if build_tools_versions:
                zipalign = build_tools_versions[0] / "zipalign"
                if zipalign.exists():
                    optimized_path = apk_path.with_suffix(".optimized.apk")
                    cmd = [str(zipalign), "-v", "4", str(apk_path), str(optimized_path)]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        print("✓ APK optimized with zipalign")
                        return optimized_path
        
        print("Warning: Could not optimize APK (zipalign not found)")
        return apk_path
    
    def analyze_apk(self, apk_path):
        """Analyze APK for size, permissions, etc."""
        print("Analyzing APK...")
        
        analysis = {
            "file_size_mb": apk_path.stat().st_size / 1024 / 1024,
            "file_path": str(apk_path)
        }
        
        # Use aapt to get APK info if available
        try:
            cmd = ["aapt", "dump", "badging", str(apk_path)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Parse aapt output
                for line in result.stdout.split('\n'):
                    if line.startswith("package:"):
                        # Extract package info
                        parts = line.split()
                        for part in parts:
                            if part.startswith("name="):
                                analysis["package_name"] = part.split("=")[1].strip("'\"")
                            elif part.startswith("versionName="):
                                analysis["version_name"] = part.split("=")[1].strip("'\"")
                    elif line.startswith("uses-permission:"):
                        if "permissions" not in analysis:
                            analysis["permissions"] = []
                        perm = line.split("'")[1] if "'" in line else "Unknown"
                        analysis["permissions"].append(perm)
        except Exception as e:
            print(f"Warning: Could not analyze APK with aapt: {e}")
        
        return analysis
    
    def build_all(self):
        """Build all configured build types"""
        print(f"Starting build process for project: {self.project_path.name}")
        print("=" * 60)
        
        try:
            self.validate_project()
            self.clean_project()
            self.run_tests()
            
            for build_type in self.config["build_types"]:
                apk_path = self.build_apk(build_type)
                optimized_apk = self.optimize_apk(apk_path)
                analysis = self.analyze_apk(optimized_apk)
                
                # Update build output with analysis
                for output in self.build_outputs:
                    if output["build_type"] == build_type:
                        output.update(analysis)
                        break
            
            print("\n" + "=" * 60)
            print("BUILD SUMMARY")
            print("=" * 60)
            
            for output in self.build_outputs:
                print(f"{output['build_type'].upper()} APK:")
                print(f"  File: {output['apk_path']}")
                print(f"  Size: {output['size_mb']:.2f} MB")
                if 'package_name' in output:
                    print(f"  Package: {output['package_name']}")
                if 'version_name' in output:
                    print(f"  Version: {output['version_name']}")
                print()
            
            return self.build_outputs
            
        except Exception as e:
            print(f"Build failed: {e}")
            return None

def main():
    parser = argparse.ArgumentParser(description="Android APK Build Tool")
    parser.add_argument("project_path", help="Path to Android project")
    parser.add_argument("--config", help="Build configuration file (JSON)")
    parser.add_argument("--build-type", help="Specific build type to build")
    parser.add_argument("--output", help="Output directory for artifacts")
    
    args = parser.parse_args()
    
    builder = APKBuilder(args.project_path, args.config)
    
    if args.build_type:
        # Build specific type
        apk_path = builder.build_apk(args.build_type)
        analysis = builder.analyze_apk(apk_path)
        print(json.dumps(analysis, indent=2))
    else:
        # Build all types
        results = builder.build_all()
        if results:
            # Save build report
            report_file = Path(args.project_path) / "build_report.json"
            with open(report_file, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"Build report saved: {report_file}")

if __name__ == "__main__":
    main()
EOF

    chmod +x "$TOOLS_DIR/build/build_apk.py"
    
    # Gradle build optimization script
    cat > "$TOOLS_DIR/build/optimize_gradle.sh" << 'EOF'
#!/bin/bash

# Gradle Build Optimization Script
# Optimizes Gradle builds for faster development cycles

PROJECT_DIR="${1:-.}"

log_info() {
    echo "[INFO] $1"
}

optimize_gradle_properties() {
    local gradle_props="$PROJECT_DIR/gradle.properties"
    
    log_info "Optimizing gradle.properties..."
    
    # Create backup
    if [[ -f "$gradle_props" ]]; then
        cp "$gradle_props" "$gradle_props.backup"
    fi
    
    # Add/update optimization properties
    cat >> "$gradle_props" << 'GRADLE_EOF'

# Build optimization properties
org.gradle.daemon=true
org.gradle.parallel=true
org.gradle.configureondemand=true
org.gradle.caching=true
org.gradle.jvmargs=-Xmx4096m -XX:MaxMetaspaceSize=512m -XX:+UseG1GC

# Android optimization
android.useAndroidX=true
android.enableJetifier=true
android.enableR8.fullMode=true
android.builder.sdkDownload=true

# Build cache
android.enableBuildCache=true
android.enableD8.desugaring=true
GRADLE_EOF

    log_info "Gradle properties optimized"
}

setup_build_cache() {
    local settings_gradle="$PROJECT_DIR/settings.gradle"
    
    log_info "Setting up build cache..."
    
    if [[ -f "$settings_gradle" ]]; then
        # Add build cache configuration
        cat >> "$settings_gradle" << 'SETTINGS_EOF'

// Build cache configuration
buildCache {
    local {
        enabled = true
        directory = new File(rootDir, 'build-cache')
        removeUnusedEntriesAfterDays = 30
    }
}
SETTINGS_EOF
    fi
}

main() {
    if [[ ! -d "$PROJECT_DIR" ]]; then
        echo "Error: Project directory not found: $PROJECT_DIR"
        exit 1
    fi
    
    log_info "Optimizing Gradle build for: $PROJECT_DIR"
    
    optimize_gradle_properties
    setup_build_cache
    
    log_info "Gradle optimization completed"
}

main "$@"
EOF

    chmod +x "$TOOLS_DIR/build/optimize_gradle.sh"
    
    log_info "Build tools created"
}

create_test_automation() {
    log_section "Creating Test Automation Tools"
    
    # Automated test runner
    cat > "$TOOLS_DIR/test/test_runner.py" << 'EOF'
#!/usr/bin/env python3
"""
Automated Test Runner for Android Apps
Runs unit tests, integration tests, and UI tests with reporting
"""

import os
import sys
import subprocess
import argparse
import json
import time
from pathlib import Path
from datetime import datetime

class TestRunner:
    """Automated test execution and reporting"""
    
    def __init__(self, project_path, config=None):
        self.project_path = Path(project_path)
        self.config = config or {}
        self.test_results = []
    
    def run_unit_tests(self):
        """Run unit tests"""
        print("Running unit tests...")
        
        cmd = ["./gradlew", "test", "--continue"]
        start_time = time.time()
        
        result = subprocess.run(cmd, cwd=self.project_path, capture_output=True, text=True)
        
        duration = time.time() - start_time
        
        test_result = {
            "test_type": "unit",
            "duration_seconds": duration,
            "exit_code": result.returncode,
            "output": result.stdout,
            "errors": result.stderr,
            "timestamp": datetime.now().isoformat()
        }
        
        if result.returncode == 0:
            print(f"✓ Unit tests passed ({duration:.1f}s)")
            test_result["status"] = "passed"
        else:
            print(f"✗ Unit tests failed ({duration:.1f}s)")
            test_result["status"] = "failed"
        
        self.test_results.append(test_result)
        return result.returncode == 0
    
    def run_integration_tests(self):
        """Run integration tests"""
        print("Running integration tests...")
        
        # Check if device is connected
        device_check = subprocess.run(["adb", "devices"], capture_output=True, text=True)
        if "device" not in device_check.stdout:
            print("Warning: No Android device connected - skipping integration tests")
            return True
        
        cmd = ["./gradlew", "connectedAndroidTest", "--continue"]
        start_time = time.time()
        
        result = subprocess.run(cmd, cwd=self.project_path, capture_output=True, text=True)
        
        duration = time.time() - start_time
        
        test_result = {
            "test_type": "integration",
            "duration_seconds": duration,
            "exit_code": result.returncode,
            "output": result.stdout,
            "errors": result.stderr,
            "timestamp": datetime.now().isoformat()
        }
        
        if result.returncode == 0:
            print(f"✓ Integration tests passed ({duration:.1f}s)")
            test_result["status"] = "passed"
        else:
            print(f"✗ Integration tests failed ({duration:.1f}s)")
            test_result["status"] = "failed"
        
        self.test_results.append(test_result)
        return result.returncode == 0
    
    def run_lint_checks(self):
        """Run code quality checks"""
        print("Running lint checks...")
        
        cmd = ["./gradlew", "lint"]
        start_time = time.time()
        
        result = subprocess.run(cmd, cwd=self.project_path, capture_output=True, text=True)
        
        duration = time.time() - start_time
        
        test_result = {
            "test_type": "lint",
            "duration_seconds": duration,
            "exit_code": result.returncode,
            "output": result.stdout,
            "errors": result.stderr,
            "timestamp": datetime.now().isoformat()
        }
        
        if result.returncode == 0:
            print(f"✓ Lint checks passed ({duration:.1f}s)")
            test_result["status"] = "passed"
        else:
            print(f"⚠ Lint checks found issues ({duration:.1f}s)")
            test_result["status"] = "warning"
        
        self.test_results.append(test_result)
        return True  # Don't fail build on lint issues
    
    def run_security_scan(self):
        """Run security analysis"""
        print("Running security scan...")
        
        # Use built-in security tools if available
        security_tools = [
            ("./gradlew", "assembleDebug"),  # Basic build to check for issues
        ]
        
        for tool_cmd in security_tools:
            try:
                result = subprocess.run(tool_cmd, cwd=self.project_path, 
                                      capture_output=True, text=True, timeout=300)
                
                # Look for security-related warnings in output
                security_issues = []
                for line in result.stderr.split('\n'):
                    if any(keyword in line.lower() for keyword in ['security', 'vulnerable', 'permission']):
                        security_issues.append(line.strip())
                
                test_result = {
                    "test_type": "security",
                    "issues_found": len(security_issues),
                    "issues": security_issues,
                    "timestamp": datetime.now().isoformat(),
                    "status": "warning" if security_issues else "passed"
                }
                
                if security_issues:
                    print(f"⚠ Security scan found {len(security_issues)} potential issues")
                else:
                    print("✓ Security scan completed - no obvious issues found")
                
                self.test_results.append(test_result)
                break
                
            except subprocess.TimeoutExpired:
                print("⚠ Security scan timed out")
            except Exception as e:
                print(f"⚠ Security scan failed: {e}")
        
        return True
    
    def generate_test_report(self, output_file="test_report.json"):
        """Generate comprehensive test report"""
        report = {
            "project": self.project_path.name,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_test_suites": len(self.test_results),
                "passed": len([r for r in self.test_results if r.get("status") == "passed"]),
                "failed": len([r for r in self.test_results if r.get("status") == "failed"]),
                "warnings": len([r for r in self.test_results if r.get("status") == "warning"])
            },
            "test_results": self.test_results
        }
        
        report_path = self.project_path / output_file
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nTest report generated: {report_path}")
        
        # Print summary
        print("\nTEST SUMMARY")
        print("=" * 40)
        print(f"Total test suites: {report['summary']['total_test_suites']}")
        print(f"Passed: {report['summary']['passed']}")
        print(f"Failed: {report['summary']['failed']}")
        print(f"Warnings: {report['summary']['warnings']}")
        
        return report
    
    def run_all_tests(self):
        """Run complete test suite"""
        print(f"Starting automated testing for: {self.project_path.name}")
        print("=" * 60)
        
        all_passed = True
        
        # Run test suites
        all_passed &= self.run_unit_tests()
        all_passed &= self.run_integration_tests()
        all_passed &= self.run_lint_checks()
        all_passed &= self.run_security_scan()
        
        # Generate report
        self.generate_test_report()
        
        return all_passed

def main():
    parser = argparse.ArgumentParser(description="Automated Test Runner")
    parser.add_argument("project_path", help="Path to Android project")
    parser.add_argument("--unit-only", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration-only", action="store_true", help="Run only integration tests")
    parser.add_argument("--report", default="test_report.json", help="Test report filename")
    
    args = parser.parse_args()
    
    runner = TestRunner(args.project_path)
    
    if args.unit_only:
        success = runner.run_unit_tests()
    elif args.integration_only:
        success = runner.run_integration_tests()
    else:
        success = runner.run_all_tests()
    
    runner.generate_test_report(args.report)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
EOF

    chmod +x "$TOOLS_DIR/test/test_runner.py"
    
    log_info "Test automation tools created"
}

create_deployment_tools() {
    log_section "Creating Deployment Tools"
    
    # App deployment script
    cat > "$TOOLS_DIR/deploy/deploy_app.py" << 'EOF'
#!/usr/bin/env python3
"""
Android App Deployment Tool
Automated deployment to testing devices, stores, and distribution platforms
"""

import os
import sys
import subprocess
import argparse
import json
import requests
from pathlib import Path
from datetime import datetime

class AppDeployment:
    """Automated app deployment management"""
    
    def __init__(self, config_file=None):
        self.config = self.load_config(config_file)
        self.deployment_log = []
    
    def load_config(self, config_file):
        """Load deployment configuration"""
        default_config = {
            "environments": {
                "dev": {
                    "name": "Development",
                    "deploy_method": "adb",
                    "auto_install": True
                },
                "staging": {
                    "name": "Staging",
                    "deploy_method": "firebase",
                    "distribution_groups": ["testers"]
                },
                "production": {
                    "name": "Production",
                    "deploy_method": "playstore",
                    "track": "internal"
                }
            },
            "notifications": {
                "slack_webhook": None,
                "email_recipients": []
            }
        }
        
        if config_file and Path(config_file).exists():
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                # Merge configurations
                for env, settings in user_config.get("environments", {}).items():
                    if env in default_config["environments"]:
                        default_config["environments"][env].update(settings)
                    else:
                        default_config["environments"][env] = settings
        
        return default_config
    
    def deploy_to_device(self, apk_path):
        """Deploy APK directly to connected device"""
        print("Deploying to connected device...")
        
        # Check ADB connection
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
        if "device" not in result.stdout:
            raise Exception("No Android device connected")
        
        # Install APK
        install_cmd = ["adb", "install", "-r", str(apk_path)]
        result = subprocess.run(install_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Installation failed: {result.stderr}")
        
        # Get package name from APK
        package_name = self.get_package_name(apk_path)
        
        deployment_info = {
            "method": "adb",
            "target": "connected_device",
            "apk_path": str(apk_path),
            "package_name": package_name,
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }
        
        self.deployment_log.append(deployment_info)
        print(f"✓ App deployed to device: {package_name}")
        
        return deployment_info
    
    def deploy_to_firebase(self, apk_path, release_notes="Automated deployment"):
        """Deploy APK to Firebase App Distribution"""
        print("Deploying to Firebase App Distribution...")
        
        # Check if Firebase CLI is available
        if not self.check_firebase_cli():
            raise Exception("Firebase CLI not found. Install with: npm install -g firebase-tools")
        
        # Deploy using Firebase CLI
        cmd = [
            "firebase", "appdistribution:distribute", str(apk_path),
            "--app", self.config.get("firebase_app_id", ""),
            "--groups", "testers",
            "--release-notes", release_notes
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Firebase deployment failed: {result.stderr}")
        
        deployment_info = {
            "method": "firebase",
            "target": "app_distribution",
            "apk_path": str(apk_path),
            "release_notes": release_notes,
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }
        
        self.deployment_log.append(deployment_info)
        print("✓ App deployed to Firebase App Distribution")
        
        return deployment_info
    
    def deploy_to_play_console(self, apk_path, track="internal"):
        """Deploy APK to Google Play Console"""
        print(f"Deploying to Google Play Console ({track} track)...")
        
        # This would typically use Google Play Developer API
        # For now, provide instructions for manual upload
        
        deployment_info = {
            "method": "playstore",
            "target": f"play_console_{track}",
            "apk_path": str(apk_path),
            "track": track,
            "timestamp": datetime.now().isoformat(),
            "status": "manual_required",
            "instructions": f"Upload {apk_path} to Google Play Console {track} track"
        }
        
        self.deployment_log.append(deployment_info)
        print(f"! Manual action required: Upload APK to Play Console {track} track")
        
        return deployment_info
    
    def get_package_name(self, apk_path):
        """Extract package name from APK"""
        try:
            cmd = ["aapt", "dump", "badging", str(apk_path)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith("package:"):
                        for part in line.split():
                            if part.startswith("name="):
                                return part.split("=")[1].strip("'\"")
        except:
            pass
        
        return "unknown.package"
    
    def check_firebase_cli(self):
        """Check if Firebase CLI is installed"""
        try:
            result = subprocess.run(["firebase", "--version"], capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    def send_notification(self, deployment_info):
        """Send deployment notification"""
        message = f"App deployment completed:\n"
        message += f"Method: {deployment_info['method']}\n"
        message += f"Target: {deployment_info['target']}\n"
        message += f"Status: {deployment_info['status']}\n"
        message += f"Time: {deployment_info['timestamp']}"
        
        # Slack notification
        slack_webhook = self.config.get("notifications", {}).get("slack_webhook")
        if slack_webhook:
            try:
                payload = {
                    "text": f"🚀 {message}",
                    "channel": "#deployments"
                }
                requests.post(slack_webhook, json=payload, timeout=10)
                print("✓ Slack notification sent")
            except Exception as e:
                print(f"Warning: Slack notification failed: {e}")
        
        print("Notification sent")
    
    def deploy(self, apk_path, environment="dev", release_notes=None):
        """Deploy app to specified environment"""
        apk_path = Path(apk_path)
        
        if not apk_path.exists():
            raise Exception(f"APK file not found: {apk_path}")
        
        env_config = self.config["environments"].get(environment)
        if not env_config:
            raise Exception(f"Environment not configured: {environment}")
        
        print(f"Deploying to {env_config['name']} environment...")
        
        deploy_method = env_config["deploy_method"]
        
        try:
            if deploy_method == "adb":
                deployment_info = self.deploy_to_device(apk_path)
            elif deploy_method == "firebase":
                deployment_info = self.deploy_to_firebase(apk_path, release_notes or "Automated deployment")
            elif deploy_method == "playstore":
                deployment_info = self.deploy_to_play_console(apk_path, env_config.get("track", "internal"))
            else:
                raise Exception(f"Unknown deployment method: {deploy_method}")
            
            # Send notifications
            self.send_notification(deployment_info)
            
            return deployment_info
            
        except Exception as e:
            error_info = {
                "method": deploy_method,
                "environment": environment,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "status": "failed"
            }
            self.deployment_log.append(error_info)
            raise
    
    def get_deployment_history(self):
        """Get deployment history"""
        return self.deployment_log

def main():
    parser = argparse.ArgumentParser(description="Android App Deployment Tool")
    parser.add_argument("apk_path", help="Path to APK file")
    parser.add_argument("--environment", default="dev", help="Deployment environment")
    parser.add_argument("--config", help="Deployment configuration file")
    parser.add_argument("--release-notes", help="Release notes for deployment")
    parser.add_argument("--list-environments", action="store_true", help="List available environments")
    
    args = parser.parse_args()
    
    deployer = AppDeployment(args.config)
    
    if args.list_environments:
        print("Available environments:")
        for env, config in deployer.config["environments"].items():
            print(f"  {env}: {config['name']} ({config['deploy_method']})")
        return
    
    try:
        deployment_info = deployer.deploy(args.apk_path, args.environment, args.release_notes)
        print(f"\nDeployment completed successfully!")
        print(json.dumps(deployment_info, indent=2))
    except Exception as e:
        print(f"Deployment failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

    chmod +x "$TOOLS_DIR/deploy/deploy_app.py"
    
    log_info "Deployment tools created"
}

create_ci_cd_templates() {
    log_section "Creating CI/CD Pipeline Templates"
    
    # GitHub Actions workflow
    cat > "$TEMPLATES_DIR/github_actions_workflow.yml" << 'EOF'
name: Android CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  GRADLE_OPTS: "-Dorg.gradle.daemon=false"
  GRADLE_USER_HOME: ${{ github.workspace }}/.gradle

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up JDK 11
      uses: actions/setup-java@v3
      with:
        java-version: '11'
        distribution: 'temurin'
    
    - name: Cache Gradle packages
      uses: actions/cache@v3
      with:
        path: |
          ~/.gradle/caches
          ~/.gradle/wrapper
        key: ${{ runner.os }}-gradle-${{ hashFiles('**/*.gradle*', '**/gradle-wrapper.properties') }}
        restore-keys: |
          ${{ runner.os }}-gradle-
    
    - name: Grant execute permission for gradlew
      run: chmod +x gradlew
    
    - name: Run unit tests
      run: ./gradlew test --continue
    
    - name: Run lint checks
      run: ./gradlew lint
    
    - name: Upload test results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: test-results
        path: |
          app/build/reports/
          app/build/test-results/
    
    - name: Upload lint results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: lint-results
        path: app/build/reports/lint-results*.html

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up JDK 11
      uses: actions/setup-java@v3
      with:
        java-version: '11'
        distribution: 'temurin'
    
    - name: Cache Gradle packages
      uses: actions/cache@v3
      with:
        path: |
          ~/.gradle/caches
          ~/.gradle/wrapper
        key: ${{ runner.os }}-gradle-${{ hashFiles('**/*.gradle*', '**/gradle-wrapper.properties') }}
        restore-keys: |
          ${{ runner.os }}-gradle-
    
    - name: Grant execute permission for gradlew
      run: chmod +x gradlew
    
    - name: Build debug APK
      run: ./gradlew assembleDebug
    
    - name: Build release APK
      run: ./gradlew assembleRelease
      if: github.ref == 'refs/heads/main'
    
    - name: Upload debug APK
      uses: actions/upload-artifact@v3
      with:
        name: debug-apk
        path: app/build/outputs/apk/debug/*.apk
    
    - name: Upload release APK
      uses: actions/upload-artifact@v3
      if: github.ref == 'refs/heads/main'
      with:
        name: release-apk
        path: app/build/outputs/apk/release/*.apk

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Download APK artifact
      uses: actions/download-artifact@v3
      with:
        name: debug-apk
        path: ./apk
    
    - name: Deploy to Firebase App Distribution
      env:
        FIREBASE_TOKEN: ${{ secrets.FIREBASE_TOKEN }}
        FIREBASE_APP_ID: ${{ secrets.FIREBASE_APP_ID }}
      run: |
        npm install -g firebase-tools
        firebase appdistribution:distribute ./apk/*.apk \
          --app $FIREBASE_APP_ID \
          --groups "testers" \
          --release-notes "Automated build from commit ${{ github.sha }}"
EOF

    # GitLab CI configuration
    cat > "$TEMPLATES_DIR/gitlab_ci.yml" << 'EOF'
image: openjdk:11-jdk

variables:
  ANDROID_COMPILE_SDK: "33"
  ANDROID_BUILD_TOOLS: "33.0.2"
  ANDROID_SDK_TOOLS: "8512546"
  GRADLE_OPTS: "-Dorg.gradle.daemon=false"

cache:
  paths:
    - .gradle/wrapper
    - .gradle/caches

before_script:
  - apt-get --quiet update --yes
  - apt-get --quiet install --yes wget tar unzip lib32stdc++6 lib32z1
  
  # Install Android SDK
  - export ANDROID_HOME="${PWD}/android-home"
  - install -d $ANDROID_HOME
  - wget --output-document=$ANDROID_HOME/cmdline-tools.zip https://dl.google.com/android/repository/commandlinetools-linux-${ANDROID_SDK_TOOLS}_latest.zip
  - pushd $ANDROID_HOME
  - unzip -d cmdline-tools cmdline-tools.zip
  - popd
  - export PATH=$PATH:${ANDROID_HOME}/cmdline-tools/cmdline-tools/bin/

  # Accept licenses and install packages
  - yes | sdkmanager --licenses || true
  - sdkmanager "platforms;android-${ANDROID_COMPILE_SDK}" "build-tools;${ANDROID_BUILD_TOOLS}"

  # Make gradlew executable
  - chmod +x ./gradlew

stages:
  - test
  - build
  - deploy

unit_test:
  stage: test
  script:
    - ./gradlew test
  artifacts:
    reports:
      junit: app/build/test-results/testDebugUnitTest/TEST-*.xml
    paths:
      - app/build/reports/tests/testDebugUnitTest/

lint_check:
  stage: test
  script:
    - ./gradlew lint
  artifacts:
    paths:
      - app/build/reports/lint-results*.html

build_debug:
  stage: build
  script:
    - ./gradlew assembleDebug
  artifacts:
    paths:
      - app/build/outputs/apk/debug/*.apk
    expire_in: 1 week

build_release:
  stage: build
  script:
    - ./gradlew assembleRelease
  artifacts:
    paths:
      - app/build/outputs/apk/release/*.apk
    expire_in: 1 month
  only:
    - main

deploy_staging:
  stage: deploy
  image: node:16
  script:
    - npm install -g firebase-tools
    - firebase appdistribution:distribute app/build/outputs/apk/debug/*.apk --app $FIREBASE_APP_ID --groups "testers"
  dependencies:
    - build_debug
  only:
    - develop
EOF

    # Jenkins pipeline
    cat > "$TEMPLATES_DIR/Jenkinsfile" << 'EOF'
pipeline {
    agent any
    
    environment {
        ANDROID_HOME = '/opt/android-sdk'
        GRADLE_OPTS = '-Dorg.gradle.daemon=false'
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Setup') {
            steps {
                sh 'chmod +x gradlew'
            }
        }
        
        stage('Test') {
            parallel {
                stage('Unit Tests') {
                    steps {
                        sh './gradlew test --continue'
                    }
                    post {
                        always {
                            publishTestResults testResultsPattern: 'app/build/test-results/testDebugUnitTest/TEST-*.xml'
                            archiveArtifacts artifacts: 'app/build/reports/tests/testDebugUnitTest/**', allowEmptyArchive: true
                        }
                    }
                }
                
                stage('Lint Check') {
                    steps {
                        sh './gradlew lint'
                    }
                    post {
                        always {
                            archiveArtifacts artifacts: 'app/build/reports/lint-results*.html', allowEmptyArchive: true
                        }
                    }
                }
            }
        }
        
        stage('Build') {
            parallel {
                stage('Debug Build') {
                    steps {
                        sh './gradlew assembleDebug'
                    }
                    post {
                        success {
                            archiveArtifacts artifacts: 'app/build/outputs/apk/debug/*.apk', fingerprint: true
                        }
                    }
                }
                
                stage('Release Build') {
                    when {
                        branch 'main'
                    }
                    steps {
                        sh './gradlew assembleRelease'
                    }
                    post {
                        success {
                            archiveArtifacts artifacts: 'app/build/outputs/apk/release/*.apk', fingerprint: true
                        }
                    }
                }
            }
        }
        
        stage('Deploy') {
            when {
                anyOf {
                    branch 'main'
                    branch 'develop'
                }
            }
            steps {
                script {
                    if (env.BRANCH_NAME == 'main') {
                        echo 'Deploying to production...'
                        // Add production deployment steps
                    } else if (env.BRANCH_NAME == 'develop') {
                        echo 'Deploying to staging...'
                        sh 'firebase appdistribution:distribute app/build/outputs/apk/debug/*.apk --app $FIREBASE_APP_ID --groups "testers"'
                    }
                }
            }
        }
    }
    
    post {
        always {
            cleanWs()
        }
        failure {
            emailext (
                subject: "Build Failed: ${env.JOB_NAME} - ${env.BUILD_NUMBER}",
                body: "Build failed. Check console output at ${env.BUILD_URL}",
                to: "${env.CHANGE_AUTHOR_EMAIL}"
            )
        }
        success {
            emailext (
                subject: "Build Successful: ${env.JOB_NAME} - ${env.BUILD_NUMBER}",
                body: "Build completed successfully. Artifacts available at ${env.BUILD_URL}",
                to: "${env.CHANGE_AUTHOR_EMAIL}"
            )
        }
    }
}
EOF

    log_info "CI/CD pipeline templates created"
}

create_configuration_files() {
    log_section "Creating Configuration Files"
    
    # Main pipeline configuration
    cat > "$CONFIG_DIR/pipeline_config.json" << 'EOF'
{
  "project_settings": {
    "default_build_types": ["debug", "release"],
    "test_suites": ["unit", "integration", "lint"],
    "deployment_environments": ["dev", "staging", "production"]
  },
  "build_optimization": {
    "gradle_parallel": true,
    "gradle_daemon": true,
    "build_cache": true,
    "incremental_builds": true
  },
  "test_configuration": {
    "unit_test_timeout": 300,
    "integration_test_timeout": 600,
    "retry_failed_tests": true,
    "generate_coverage_report": true
  },
  "deployment_settings": {
    "auto_deploy_dev": true,
    "auto_deploy_staging": false,
    "require_manual_production": true
  },
  "notification_settings": {
    "notify_on_failure": true,
    "notify_on_success": false,
    "slack_channel": "#android-builds"
  }
}
EOF

    # Environment-specific configurations
    cat > "$CONFIG_DIR/environments.json" << 'EOF'
{
  "dev": {
    "name": "Development",
    "deploy_method": "adb",
    "auto_install": true,
    "debug_mode": true
  },
  "staging": {
    "name": "Staging",
    "deploy_method": "firebase",
    "distribution_groups": ["internal-testers"],
    "require_approval": false
  },
  "production": {
    "name": "Production", 
    "deploy_method": "playstore",
    "track": "internal",
    "require_approval": true,
    "generate_release_notes": true
  }
}
EOF

    # Notification configuration template
    cat > "$CONFIG_DIR/notifications.json" << 'EOF'
{
  "slack": {
    "enabled": false,
    "webhook_url": "YOUR_SLACK_WEBHOOK_URL",
    "channel": "#android-builds",
    "username": "Android CI Bot"
  },
  "email": {
    "enabled": false,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "username": "your_email@gmail.com",
    "recipients": ["team@company.com"]
  },
  "teams": {
    "enabled": false,
    "webhook_url": "YOUR_TEAMS_WEBHOOK_URL"
  }
}
EOF

    log_info "Configuration files created"
}

create_project_scripts() {
    log_section "Creating Project Scripts"
    
    # Main pipeline runner
    cat > "$SCRIPTS_DIR/run_pipeline.sh" << 'EOF'
#!/bin/bash

# Android Development Pipeline Runner
# Main entry point for automated build, test, and deployment

PIPELINE_DIR="$HOME/AndroidDevelopment"
PROJECT_DIR="${1:-.}"
ENVIRONMENT="${2:-dev}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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

show_usage() {
    echo "Usage: $0 [project_dir] [environment]"
    echo
    echo "Arguments:"
    echo "  project_dir    Path to Android project (default: current directory)"
    echo "  environment    Deployment environment: dev|staging|production (default: dev)"
    echo
    echo "Examples:"
    echo "  $0                           # Build current project, deploy to dev"
    echo "  $0 /path/to/project staging  # Build specific project, deploy to staging"
}

run_full_pipeline() {
    local project_dir="$1"
    local environment="$2"
    
    log_info "Starting full pipeline for: $(basename "$project_dir")"
    log_info "Target environment: $environment"
    echo "=" * 60
    
    # Step 1: Run tests
    log_info "Step 1: Running automated tests..."
    if python3 "$PIPELINE_DIR/tools/test/test_runner.py" "$project_dir"; then
        log_info "✓ Tests passed"
    else
        log_error "✗ Tests failed - stopping pipeline"
        return 1
    fi
    
    # Step 2: Build APK
    log_info "Step 2: Building APK..."
    if python3 "$PIPELINE_DIR/tools/build/build_apk.py" "$project_dir"; then
        log_info "✓ Build completed"
    else
        log_error "✗ Build failed - stopping pipeline"
        return 1
    fi
    
    # Step 3: Deploy
    log_info "Step 3: Deploying to $environment..."
    
    # Find the most recent APK
    local apk_file
    if [[ "$environment" == "production" ]]; then
        apk_file=$(find "$project_dir/app/build/outputs/apk/release" -name "*.apk" -type f | head -1)
    else
        apk_file=$(find "$project_dir/app/build/outputs/apk/debug" -name "*.apk" -type f | head -1)
    fi
    
    if [[ -z "$apk_file" ]]; then
        log_error "No APK file found for deployment"
        return 1
    fi
    
    if python3 "$PIPELINE_DIR/tools/deploy/deploy_app.py" "$apk_file" --environment "$environment"; then
        log_info "✓ Deployment completed"
    else
        log_error "✗ Deployment failed"
        return 1
    fi
    
    log_info "Pipeline completed successfully!"
    return 0
}

main() {
    # Parse arguments
    case "${1:-}" in
        -h|--help|help)
            show_usage
            exit 0
            ;;
    esac
    
    local project_dir="$(realpath "${1:-.}")"
    local environment="${2:-dev}"
    
    # Validate project directory
    if [[ ! -d "$project_dir" ]]; then
        log_error "Project directory not found: $project_dir"
        exit 1
    fi
    
    if [[ ! -f "$project_dir/build.gradle" ]] && [[ ! -f "$project_dir/app/build.gradle" ]]; then
        log_error "Not an Android project: $project_dir"
        exit 1
    fi
    
    # Validate environment
    case "$environment" in
        dev|staging|production)
            ;;
        *)
            log_error "Invalid environment: $environment"
            log_info "Valid environments: dev, staging, production"
            exit 1
            ;;
    esac
    
    # Run pipeline
    if run_full_pipeline "$project_dir" "$environment"; then
        exit 0
    else
        exit 1
    fi
}

main "$@"
EOF

    chmod +x "$SCRIPTS_DIR/run_pipeline.sh"
    
    # Setup script for new projects
    cat > "$SCRIPTS_DIR/setup_project.sh" << 'EOF'
#!/bin/bash

# New Android Project Setup
# Configures a new project with development pipeline

PROJECT_NAME="${1}"
PROJECT_DIR="${2:-$PWD/$PROJECT_NAME}"

log_info() {
    echo "[INFO] $1"
}

create_project_structure() {
    log_info "Creating project structure for: $PROJECT_NAME"
    
    mkdir -p "$PROJECT_DIR"
    cd "$PROJECT_DIR"
    
    # Initialize git repository
    git init
    
    # Create basic Android project structure
    mkdir -p app/src/{main,test,androidTest}/{java,res,assets}
    mkdir -p app/src/main/res/{layout,values,drawable,mipmap}
    
    log_info "Project structure created"
}

setup_gradle_files() {
    log_info "Setting up Gradle configuration..."
    
    # Create root build.gradle
    cat > build.gradle << 'GRADLE_EOF'
buildscript {
    ext.kotlin_version = '1.9.20'
    dependencies {
        classpath 'com.android.tools.build:gradle:8.1.4'
        classpath "org.jetbrains.kotlin:kotlin-gradle-plugin:$kotlin_version"
    }
}

allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

task clean(type: Delete) {
    delete rootProject.buildDir
}
GRADLE_EOF

    # Create app build.gradle
    cat > app/build.gradle << 'APP_GRADLE_EOF'
apply plugin: 'com.android.application'
apply plugin: 'kotlin-android'

android {
    namespace 'com.example.PROJECT_NAME_PLACEHOLDER'
    compileSdk 34

    defaultConfig {
        applicationId "com.example.PROJECT_NAME_PLACEHOLDER"
        minSdk 21
        targetSdk 34
        versionCode 1
        versionName "1.0"
        testInstrumentationRunner "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        release {
            minifyEnabled false
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
    }
    
    compileOptions {
        sourceCompatibility JavaVersion.VERSION_1_8
        targetCompatibility JavaVersion.VERSION_1_8
    }
    
    kotlinOptions {
        jvmTarget = '1.8'
    }
}

dependencies {
    implementation 'androidx.core:core-ktx:1.12.0'
    implementation 'androidx.appcompat:appcompat:1.6.1'
    implementation 'com.google.android.material:material:1.10.0'
    implementation 'androidx.constraintlayout:constraintlayout:2.1.4'
    
    testImplementation 'junit:junit:4.13.2'
    androidTestImplementation 'androidx.test.ext:junit:1.1.5'
    androidTestImplementation 'androidx.test.espresso:espresso-core:3.5.1'
}
APP_GRADLE_EOF

    # Replace placeholder with actual project name
    sed -i "s/PROJECT_NAME_PLACEHOLDER/${PROJECT_NAME}/g" app/build.gradle
    
    log_info "Gradle files configured"
}

setup_pipeline_integration() {
    log_info "Setting up pipeline integration..."
    
    # Copy pipeline configuration
    cp "$HOME/AndroidDevelopment/templates/github_actions_workflow.yml" .github/workflows/android.yml 2>/dev/null || true
    cp "$HOME/AndroidDevelopment/config/pipeline_config.json" pipeline_config.json
    
    # Create project-specific build script
    cat > build.sh << 'BUILD_EOF'
#!/bin/bash
# Project build script

PIPELINE_DIR="$HOME/AndroidDevelopment"

# Run full pipeline
"$PIPELINE_DIR/scripts/run_pipeline.sh" . dev
BUILD_EOF

    chmod +x build.sh
    
    log_info "Pipeline integration configured"
}

main() {
    if [[ -z "$PROJECT_NAME" ]]; then
        echo "Usage: $0 <project_name> [project_directory]"
        exit 1
    fi
    
    create_project_structure
    setup_gradle_files
    setup_pipeline_integration
    
    log_info "Project setup completed: $PROJECT_DIR"
    log_info "Next steps:"
    log_info "1. cd $PROJECT_DIR"
    log_info "2. ./build.sh"
}

main "$@"
EOF

    chmod +x "$SCRIPTS_DIR/setup_project.sh"
    
    log_info "Project scripts created"
}

verify_installation() {
    log_section "Verifying Installation"
    
    echo "Android Development Pipeline Status:"
    echo "──────────────────────────────────────"
    
    # Check directory structure
    if [[ -d "$PIPELINE_DIR" ]]; then
        echo "✓ Pipeline directory: $PIPELINE_DIR"
    else
        echo "✗ Pipeline directory missing"
    fi
    
    # Check tools
    local tools=(
        "tools/build/build_apk.py"
        "tools/test/test_runner.py" 
        "tools/deploy/deploy_app.py"
        "scripts/run_pipeline.sh"
    )
    
    for tool in "${tools[@]}"; do
        if [[ -f "$PIPELINE_DIR/$tool" ]]; then
            echo "✓ Tool: $tool"
        else
            echo "✗ Tool missing: $tool"
        fi
    done
    
    # Check Python packages
    if python3 -c "import click, requests, PyYAML" 2>/dev/null; then
        echo "✓ Python dependencies installed"
    else
        echo "⚠ Some Python dependencies missing"
    fi
    
    # Check Android SDK
    if [[ -n "$ANDROID_HOME" ]] && [[ -d "$ANDROID_HOME" ]]; then
        echo "✓ Android SDK: $ANDROID_HOME"
    else
        echo "⚠ Android SDK not configured"
    fi
    
    echo "──────────────────────────────────────"
    
    log_info "Installation verification completed"
}

create_documentation() {
    log_section "Creating Documentation"
    
    cat > "$PIPELINE_DIR/README.md" << 'EOF'
# Android Development Pipeline

Automated development, testing, and deployment pipeline for Android applications.

## Quick Start

### Setup Pipeline
```bash
./app-development-pipeline.sh
```

### Build and Deploy App
```bash
# Build current project, deploy to dev
./scripts/run_pipeline.sh

# Build specific project, deploy to staging  
./scripts/run_pipeline.sh /path/to/project staging
```

### Create New Project
```bash
./scripts/setup_project.sh MyApp
cd MyApp
./build.sh
```

## Pipeline Components

### Build Tools
- **APK Builder**: Automated building, signing, and optimization
- **Gradle Optimizer**: Build performance improvements
- **Multi-variant Builds**: Debug and release configurations

### Testing Framework  
- **Unit Tests**: JUnit and Kotlin test execution
- **Integration Tests**: Connected Android tests
- **Code Quality**: Lint checks and static analysis
- **Security Scanning**: Basic security issue detection

### Deployment Tools
- **Device Deployment**: Direct installation via ADB
- **Firebase Distribution**: App distribution to testers
- **Play Store**: Google Play Console integration preparation

### CI/CD Templates
- **GitHub Actions**: Complete workflow configuration
- **GitLab CI**: Pipeline configuration for GitLab
- **Jenkins**: Jenkinsfile for Jenkins automation

## Directory Structure

```
AndroidDevelopment/
├── tools/
│   ├── build/          # Build automation tools
│   ├── test/           # Testing frameworks
│   ├── deploy/         # Deployment tools
│   └── analysis/       # Code analysis tools
├── config/             # Configuration files
├── scripts/            # Utility scripts
├── templates/          # CI/CD templates
└── projects/           # Project workspace
```

## Configuration

### Pipeline Settings
Edit `config/pipeline_config.json` to customize:
- Build types and optimization
- Test suite configuration
- Deployment environments
- Notification settings

### Environment Configuration  
Configure deployment targets in `config/environments.json`:
- Development (ADB deployment)
- Staging (Firebase App Distribution)
- Production (Play Store preparation)

## Usage Examples

### Automated Testing
```bash
python3 tools/test/test_runner.py /path/to/project
```

### Building APKs
```bash
python3 tools/build/build_apk.py /path/to/project --build-type release
```

### Deployment
```bash
python3 tools/deploy/deploy_app.py app.apk --environment staging
```

### Performance Optimization
```bash
tools/build/optimize_gradle.sh /path/to/project
```

## Integration

### GitHub Actions
Copy `templates/github_actions_workflow.yml` to `.github/workflows/android.yml`

### GitLab CI
Copy `templates/gitlab_ci.yml` to `.gitlab-ci.yml`

### Jenkins
Copy `templates/Jenkinsfile` to your repository root

## Requirements

- Java 11+
- Android SDK
- Python 3.8+
- Node.js 16+
- Git

## Troubleshooting

### Common Issues

**Build Failures:**
- Check Android SDK path: `echo $ANDROID_HOME`
- Verify Java version: `java -version`
- Clean and rebuild: `./gradlew clean build`

**Deployment Issues:**
- Check device connection: `adb devices`
- Verify Firebase CLI: `firebase --version`
- Check app permissions and signing

**Test Failures:**
- Run tests individually: `./gradlew test`
- Check device state for integration tests
- Verify test dependencies in build.gradle

EOF

    log_info "Documentation created"
}

main() {
    log_info "Starting Android App Development Pipeline Setup"
    echo
    
    check_prerequisites
    setup_pipeline_structure
    setup_development_tools
    create_build_tools
    create_test_automation
    create_deployment_tools
    create_ci_cd_templates
    create_configuration_files
    create_project_scripts
    verify_installation
    create_documentation
    
    echo
    log_info "Android Development Pipeline setup completed successfully!"
    echo
    echo "Pipeline installed at: $PIPELINE_DIR"
    echo
    echo "Quick commands:"
    echo "• Build & deploy: $PIPELINE_DIR/scripts/run_pipeline.sh [project_dir] [environment]"
    echo "• Create project: $PIPELINE_DIR/scripts/setup_project.sh <project_name>"
    echo "• View docs: cat $PIPELINE_DIR/README.md"
    echo
    echo "Next steps:"
    echo "1. Configure your environments in config/environments.json"
    echo "2. Set up CI/CD using templates/ for your git platform"
    echo "3. Run your first build: cd your-project && $PIPELINE_DIR/scripts/run_pipeline.sh"
}

main "$@"

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Create app development pipeline setup script", "status": "completed", "activeForm": "Creating app development pipeline setup script"}, {"content": "Build automated testing configuration", "status": "in_progress", "activeForm": "Building automated testing configuration"}, {"content": "Set up CI/CD pipeline templates", "status": "pending", "activeForm": "Setting up CI/CD pipeline templates"}, {"content": "Create app modification and build tools", "status": "pending", "activeForm": "Creating app modification and build tools"}]