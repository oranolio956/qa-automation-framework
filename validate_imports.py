#!/usr/bin/env python3
"""
Import Path Validation Script
Tests all imports in the automation system to identify and fix issues
"""

import os
import sys
import importlib
import importlib.util
import traceback
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

class ImportValidator:
    """Validates all imports in the automation system"""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.failed_imports = []
        self.successful_imports = []
        self.circular_dependencies = []
        self.missing_modules = set()
        
    def test_core_imports(self) -> Dict[str, bool]:
        """Test core automation system imports"""
        print("🔍 Testing core automation system imports...")
        results = {}
        
        # Test utils imports
        test_modules = [
            ('utils.brightdata_proxy', 'get_brightdata_session'),
            ('utils.sms_verifier', 'get_sms_verifier'), 
            ('utils.twilio_pool', 'TwilioPool'),
            ('automation.core.anti_detection', 'get_anti_detection_system'),
            ('automation.email.captcha_solver', 'CaptchaSolver'),
            ('automation.snapchat.stealth_creator', 'SnapchatStealthCreator'),
        ]
        
        for module_name, class_name in test_modules:
            try:
                print(f"  Testing {module_name}.{class_name}...")
                
                # Import module
                module = importlib.import_module(module_name)
                
                # Check if class/function exists
                if hasattr(module, class_name):
                    results[f"{module_name}.{class_name}"] = True
                    self.successful_imports.append(f"{module_name}.{class_name}")
                    print(f"    ✅ {module_name}.{class_name}")
                else:
                    results[f"{module_name}.{class_name}"] = False
                    self.failed_imports.append(f"{module_name}.{class_name} - Class not found")
                    print(f"    ❌ {module_name}.{class_name} - Class not found")
                    
            except ImportError as e:
                results[f"{module_name}.{class_name}"] = False
                self.failed_imports.append(f"{module_name}.{class_name} - {str(e)}")
                print(f"    ❌ {module_name}.{class_name} - ImportError: {e}")
                
                # Track missing modules
                if "No module named" in str(e):
                    missing_module = str(e).split("'")[1] if "'" in str(e) else str(e)
                    self.missing_modules.add(missing_module)
                    
            except Exception as e:
                results[f"{module_name}.{class_name}"] = False
                self.failed_imports.append(f"{module_name}.{class_name} - {str(e)}")
                print(f"    ❌ {module_name}.{class_name} - Error: {e}")
        
        return results
    
    def test_dependency_imports(self) -> Dict[str, bool]:
        """Test external dependencies"""
        print("\n🔍 Testing external dependencies...")
        results = {}
        
        dependencies = [
            'numpy',
            'requests',
            'beautifulsoup4',
            'uiautomator2',
            'selenium',
            'opencv-python',
            'Pillow',
            'scipy',
            'scikit-learn',
            'tensorflow',
            'pytesseract',
            'easyocr',
            'aiohttp',
            'redis',
            'psycopg2',
            'twilio',
            'python-telegram-bot',
            'fastapi',
            'uvicorn',
            'pydantic'
        ]
        
        # Map package names to import names
        import_mapping = {
            'opencv-python': 'cv2',
            'Pillow': 'PIL',
            'beautifulsoup4': 'bs4',
            'python-telegram-bot': 'telegram',
            'scikit-learn': 'sklearn'
        }
        
        for package in dependencies:
            import_name = import_mapping.get(package, package.replace('-', '_'))
            
            try:
                print(f"  Testing {package} (import as '{import_name}')...")
                importlib.import_module(import_name)
                results[package] = True
                self.successful_imports.append(package)
                print(f"    ✅ {package}")
                
            except ImportError as e:
                results[package] = False
                self.failed_imports.append(f"{package} - {str(e)}")
                print(f"    ❌ {package} - {e}")
                self.missing_modules.add(import_name)
                
        return results
    
    def test_package_structure(self) -> Dict[str, bool]:
        """Test package structure and __init__.py files"""
        print("\n🔍 Testing package structure...")
        results = {}
        
        required_packages = [
            'utils',
            'automation',
            'automation.core',
            'automation.email',
            'automation.snapchat', 
            'automation.tinder',
            'automation.android',
            'automation.telegram_bot',
            'automation.config',
            'automation.tests',
            'automation.scripts',
            'automation.templates'
        ]
        
        for package in required_packages:
            try:
                print(f"  Testing package {package}...")
                
                # Check if package directory exists
                package_path = self.project_root / package.replace('.', '/')
                if not package_path.exists():
                    results[package] = False
                    self.failed_imports.append(f"{package} - Directory not found")
                    print(f"    ❌ {package} - Directory not found")
                    continue
                
                # Check if __init__.py exists
                init_file = package_path / '__init__.py'
                if not init_file.exists():
                    results[package] = False
                    self.failed_imports.append(f"{package} - Missing __init__.py")
                    print(f"    ❌ {package} - Missing __init__.py")
                    continue
                
                # Try to import package
                importlib.import_module(package)
                results[package] = True
                self.successful_imports.append(package)
                print(f"    ✅ {package}")
                
            except ImportError as e:
                results[package] = False
                self.failed_imports.append(f"{package} - {str(e)}")
                print(f"    ❌ {package} - ImportError: {e}")
                
        return results
    
    def detect_circular_imports(self) -> List[str]:
        """Detect potential circular import issues"""
        print("\n🔍 Detecting circular imports...")
        circular_issues = []
        
        # Test combinations that might have circular dependencies
        test_combinations = [
            ('automation.core.anti_detection', 'automation.email.captcha_solver'),
            ('automation.snapchat.stealth_creator', 'automation.core.anti_detection'),
            ('automation.tinder.account_creator', 'automation.core.anti_detection'),
            ('utils.sms_verifier', 'automation.telegram_bot.main_bot'),
        ]
        
        for module1, module2 in test_combinations:
            try:
                print(f"  Testing circular dependency: {module1} ↔ {module2}")
                
                # Import both modules
                importlib.import_module(module1)
                importlib.import_module(module2)
                
                print(f"    ✅ No circular dependency detected")
                
            except ImportError as e:
                if "circular import" in str(e).lower():
                    circular_issues.append(f"{module1} ↔ {module2}: {e}")
                    print(f"    ❌ Circular dependency: {e}")
                else:
                    print(f"    ⚠️  Import error (not circular): {e}")
                    
            except Exception as e:
                print(f"    ⚠️  Other error: {e}")
        
        self.circular_dependencies = circular_issues
        return circular_issues
    
    def generate_missing_requirements(self) -> str:
        """Generate requirements.txt entries for missing modules"""
        print("\n📦 Generating missing requirements...")
        
        # Map missing modules to PyPI package names
        module_to_package = {
            'cv2': 'opencv-python==4.8.1.78',
            'uiautomator2': 'uiautomator2==2.16.23',
            'sklearn': 'scikit-learn==1.3.2',
            'bs4': 'beautifulsoup4==4.12.2',
            'telegram': 'python-telegram-bot==20.7',
            'pytesseract': 'pytesseract==0.3.10',
            'easyocr': 'easyocr==1.7.0',
            'tensorflow': 'tensorflow==2.13.0',
            'psycopg2': 'psycopg2-binary==2.9.7',
        }
        
        missing_requirements = []
        for module in self.missing_modules:
            if module in module_to_package:
                missing_requirements.append(module_to_package[module])
                print(f"  📦 {module} → {module_to_package[module]}")
            else:
                missing_requirements.append(f"{module}")
                print(f"  📦 {module} (version unknown)")
        
        return "\\n".join(missing_requirements)
    
    def generate_report(self) -> str:
        """Generate a comprehensive validation report"""
        report = []
        report.append("# Import Validation Report")
        report.append("=" * 50)
        report.append("")
        
        # Summary
        total_tests = len(self.successful_imports) + len(self.failed_imports)
        success_rate = len(self.successful_imports) / total_tests * 100 if total_tests > 0 else 0
        
        report.append(f"## Summary")
        report.append(f"- Total imports tested: {total_tests}")
        report.append(f"- Successful imports: {len(self.successful_imports)}")
        report.append(f"- Failed imports: {len(self.failed_imports)}")
        report.append(f"- Success rate: {success_rate:.1f}%")
        report.append(f"- Circular dependencies: {len(self.circular_dependencies)}")
        report.append(f"- Missing modules: {len(self.missing_modules)}")
        report.append("")
        
        # Failed imports
        if self.failed_imports:
            report.append("## Failed Imports")
            for failure in self.failed_imports:
                report.append(f"- ❌ {failure}")
            report.append("")
        
        # Missing modules
        if self.missing_modules:
            report.append("## Missing Modules")
            for module in sorted(self.missing_modules):
                report.append(f"- 📦 {module}")
            report.append("")
        
        # Circular dependencies
        if self.circular_dependencies:
            report.append("## Circular Dependencies")
            for circular in self.circular_dependencies:
                report.append(f"- 🔄 {circular}")
            report.append("")
        
        # Successful imports
        report.append("## Successful Imports")
        for success in self.successful_imports:
            report.append(f"- ✅ {success}")
        
        return "\\n".join(report)

def main():
    """Run complete import validation"""
    print("🚀 Starting comprehensive import validation...")
    print("=" * 60)
    
    validator = ImportValidator()
    
    # Run all tests
    core_results = validator.test_core_imports()
    dependency_results = validator.test_dependency_imports()
    package_results = validator.test_package_structure()
    circular_imports = validator.detect_circular_imports()
    
    # Generate missing requirements
    missing_reqs = validator.generate_missing_requirements()
    
    # Generate and save report
    report = validator.generate_report()
    
    report_file = PROJECT_ROOT / "import_validation_report.txt"
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\\n📊 Report saved to: {report_file}")
    
    # Print summary
    print("\\n" + "=" * 60)
    print("🎯 VALIDATION SUMMARY")
    print("=" * 60)
    
    total_successful = len(validator.successful_imports)
    total_failed = len(validator.failed_imports)
    total_tests = total_successful + total_failed
    
    if total_tests > 0:
        success_rate = total_successful / total_tests * 100
        print(f"✅ Successful imports: {total_successful}")
        print(f"❌ Failed imports: {total_failed}")
        print(f"📊 Success rate: {success_rate:.1f}%")
    
    if validator.missing_modules:
        print(f"📦 Missing modules: {len(validator.missing_modules)}")
        print("   Install with: pip install " + " ".join(validator.missing_modules))
    
    if validator.circular_dependencies:
        print(f"🔄 Circular dependencies: {len(validator.circular_dependencies)}")
    
    # Exit code
    if total_failed == 0 and len(validator.circular_dependencies) == 0:
        print("\\n🎉 All imports validated successfully!")
        return 0
    else:
        print(f"\\n⚠️  {total_failed} import issues need to be fixed")
        return 1

if __name__ == "__main__":
    exit(main())