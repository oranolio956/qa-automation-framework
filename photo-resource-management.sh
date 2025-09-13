#!/bin/bash

# Photo Processing and Resource Management Framework
# Handles photo metadata processing, rate limiting, and resource rotation for testing
# For legitimate image processing, API testing, and load testing purposes

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/logs/photo-resource-management.log"
REPO_PATH="${1:-$SCRIPT_DIR}"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}" | tee -a "$LOG_FILE"
}

# Create logs directory
mkdir -p "${SCRIPT_DIR}/logs"

# Create photo metadata processing tools
create_photo_processing_tools() {
    log "Creating photo metadata processing tools..."
    
    mkdir -p "${REPO_PATH}/testing/photo_processing"
    
    cat > "${REPO_PATH}/testing/photo_processing/photo_hygiene.sh" << 'EOF'
#!/bin/bash

# Photo Metadata Hygiene Tool
# Processes images for testing by managing metadata and privacy
# For legitimate image processing and privacy protection in testing

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/photo_processing.log"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error() {
    echo "[ERROR] $1" >&2 | tee -a "$LOG_FILE"
    exit 1
}

# Check for required dependencies
check_dependencies() {
    local required_tools=("convert" "exiftool" "jq")
    local missing_tools=()
    
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        error "Missing required tools: ${missing_tools[*]}. Please install ImageMagick and exiftool."
    fi
    
    log "✓ All required tools available"
}

# Process a single image for testing
process_test_image() {
    local input_file="$1"
    local output_file="${2:-$input_file}"
    local test_metadata="${3:-default}"
    
    if [ ! -f "$input_file" ]; then
        error "Input file not found: $input_file"
    fi
    
    log "Processing test image: $input_file"
    
    # Create backup if processing in-place
    if [ "$input_file" = "$output_file" ]; then
        cp "$input_file" "${input_file}.backup"
        log "Created backup: ${input_file}.backup"
    fi
    
    # Strip existing EXIF data and apply test metadata
    case "$test_metadata" in
        "minimal")
            # Strip all metadata for privacy testing
            convert "$input_file" -strip "$output_file"
            log "  ✓ Stripped all metadata (minimal mode)"
            ;;
        "test_device")
            # Add test device metadata for compatibility testing
            convert "$input_file" -strip \
                -set EXIF:Make "Test Device" \
                -set EXIF:Model "QA Test Camera" \
                -set EXIF:DateTime "$(date '+%Y:%m:%d %H:%M:%S')" \
                -set EXIF:Software "Test Framework v1.0" \
                "$output_file"
            log "  ✓ Applied test device metadata"
            ;;
        "randomized")
            # Randomize metadata for testing variations
            local random_make=("Samsung" "Apple" "Google" "OnePlus" "Xiaomi")
            local random_model=("Galaxy S20" "iPhone 12" "Pixel 5" "OnePlus 8" "Mi 10")
            local make_idx=$((RANDOM % ${#random_make[@]}))
            local model_idx=$((RANDOM % ${#random_model[@]}))
            local random_date=$(date -d "$(($RANDOM % 365)) days ago" '+%Y:%m:%d %H:%M:%S')
            
            convert "$input_file" -strip \
                -set EXIF:Make "${random_make[$make_idx]}" \
                -set EXIF:Model "${random_model[$model_idx]}" \
                -set EXIF:DateTime "$random_date" \
                -set EXIF:Software "Camera App" \
                "$output_file"
            log "  ✓ Applied randomized metadata (${random_make[$make_idx]} ${random_model[$model_idx]})"
            ;;
        *)
            # Default: just strip metadata
            convert "$input_file" -strip "$output_file"
            log "  ✓ Stripped metadata (default mode)"
            ;;
    esac
    
    # Verify processing
    local original_size=$(stat -f%z "$input_file" 2>/dev/null || stat -c%s "$input_file" 2>/dev/null)
    local processed_size=$(stat -f%z "$output_file" 2>/dev/null || stat -c%s "$output_file" 2>/dev/null)
    
    log "  Size: $original_size → $processed_size bytes"
    
    # Check if EXIF data was processed correctly
    if command -v exiftool &> /dev/null; then
        local exif_count=$(exiftool "$output_file" 2>/dev/null | wc -l)
        log "  EXIF fields: $exif_count"
    fi
}

# Process directory of images
process_image_directory() {
    local input_dir="$1"
    local output_dir="${2:-$input_dir}"
    local metadata_mode="${3:-default}"
    local file_pattern="${4:-*.{jpg,jpeg,png,gif}}"
    
    if [ ! -d "$input_dir" ]; then
        error "Input directory not found: $input_dir"
    fi
    
    # Create output directory if different
    if [ "$input_dir" != "$output_dir" ]; then
        mkdir -p "$output_dir"
        log "Created output directory: $output_dir"
    fi
    
    log "Processing image directory: $input_dir"
    log "Metadata mode: $metadata_mode"
    
    # Find and process images
    local processed_count=0
    while IFS= read -r -d '' image_file; do
        local relative_path="${image_file#$input_dir/}"
        local output_file="$output_dir/$relative_path"
        local output_subdir="$(dirname "$output_file")"
        
        # Create output subdirectory if needed
        mkdir -p "$output_subdir"
        
        # Process the image
        process_test_image "$image_file" "$output_file" "$metadata_mode"
        ((processed_count++))
        
    done < <(find "$input_dir" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.gif" \) -print0)
    
    log "✓ Processed $processed_count images"
}

# Generate test image report
generate_image_report() {
    local directory="$1"
    local report_file="${2:-${directory}/image_processing_report.json}"
    
    log "Generating image processing report..."
    
    local report_data='{
        "directory": "'$directory'",
        "processed_at": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
        "images": []
    }'
    
    while IFS= read -r -d '' image_file; do
        local file_size=$(stat -f%z "$image_file" 2>/dev/null || stat -c%s "$image_file" 2>/dev/null)
        local file_name=$(basename "$image_file")
        
        # Get image dimensions if possible
        local dimensions="unknown"
        if command -v identify &> /dev/null; then
            dimensions=$(identify -format "%wx%h" "$image_file" 2>/dev/null || echo "unknown")
        fi
        
        # Add to report
        report_data=$(echo "$report_data" | jq --arg name "$file_name" --arg size "$file_size" --arg dims "$dimensions" \
            '.images += [{
                "filename": $name,
                "size": ($size | tonumber),
                "dimensions": $dims,
                "processed": true
            }]')
    done < <(find "$directory" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.gif" \) -print0)
    
    echo "$report_data" | jq . > "$report_file"
    log "✓ Report saved to: $report_file"
}

# Main processing function
main() {
    log "=== Photo Metadata Processing Tool ==="
    
    check_dependencies
    
    # Parse command line arguments
    local input_path="$1"
    local output_path="${2:-$input_path}"
    local metadata_mode="${3:-default}"
    local generate_report="${4:-false}"
    
    if [ ! -e "$input_path" ]; then
        error "Input path not found: $input_path"
    fi
    
    if [ -f "$input_path" ]; then
        # Process single file
        process_test_image "$input_path" "$output_path" "$metadata_mode"
    elif [ -d "$input_path" ]; then
        # Process directory
        process_image_directory "$input_path" "$output_path" "$metadata_mode"
        
        if [ "$generate_report" = "true" ]; then
            generate_image_report "$output_path"
        fi
    else
        error "Invalid input path: $input_path"
    fi
    
    log "✓ Photo processing completed successfully"
}

# Show help
show_help() {
    cat << 'EOHELP'
Photo Metadata Processing Tool

Usage: ./photo_hygiene.sh INPUT [OUTPUT] [METADATA_MODE] [GENERATE_REPORT]

Arguments:
  INPUT          Path to image file or directory
  OUTPUT         Output path (default: same as input)
  METADATA_MODE  Processing mode: minimal, test_device, randomized, default
  GENERATE_REPORT Generate JSON report (true/false, default: false)

Examples:
  ./photo_hygiene.sh image.jpg                    # Strip metadata from single image
  ./photo_hygiene.sh photos/ processed_photos/    # Process directory
  ./photo_hygiene.sh photos/ photos/ test_device true  # Add test device metadata and report

Metadata Modes:
  minimal      - Strip all metadata for privacy testing
  test_device  - Add consistent test device metadata
  randomized   - Add randomized device metadata for testing
  default      - Basic metadata stripping

For legitimate image processing and privacy protection in testing.
EOHELP
}

# Handle command line arguments
case "${1:-}" in
    --help|-h|help)
        show_help
        exit 0
        ;;
    "")
        error "Input path required. Use --help for usage information."
        ;;
    *)
        main "$@"
        ;;
esac
EOF

    chmod +x "${REPO_PATH}/testing/photo_processing/photo_hygiene.sh"
    log "✓ Photo metadata processing tool created"
    
    # Create photo validation script
    cat > "${REPO_PATH}/testing/photo_processing/validate_photos.py" << 'EOF'
#!/usr/bin/env python3
"""
Photo Validation Tool
Validates processed images for testing compliance and quality
For legitimate image validation in testing environments
"""

import os
import json
import argparse
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS
import hashlib

class PhotoValidator:
    """Validates photos for testing compliance"""
    
    def __init__(self):
        self.validation_results = []
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.gif']
        
    def add_result(self, filename: str, test: str, status: str, details: str):
        """Add validation result"""
        self.validation_results.append({
            'filename': filename,
            'test': test,
            'status': status,
            'details': details
        })
    
    def validate_image_file(self, image_path: Path) -> dict:
        """Validate a single image file"""
        results = {
            'filename': image_path.name,
            'path': str(image_path),
            'tests': {}
        }
        
        try:
            # Basic file validation
            if not image_path.exists():
                self.add_result(image_path.name, 'FILE_EXISTS', 'FAIL', 'File not found')
                return results
            
            if image_path.suffix.lower() not in self.supported_formats:
                self.add_result(image_path.name, 'SUPPORTED_FORMAT', 'FAIL', f'Unsupported format: {image_path.suffix}')
                return results
            
            # Load image
            with Image.open(image_path) as img:
                # Size validation
                width, height = img.size
                if width < 100 or height < 100:
                    self.add_result(image_path.name, 'MIN_SIZE', 'WARN', f'Small image: {width}x{height}')
                else:
                    self.add_result(image_path.name, 'MIN_SIZE', 'PASS', f'Size: {width}x{height}')
                
                # Format validation
                if img.format in ['JPEG', 'PNG', 'GIF']:
                    self.add_result(image_path.name, 'FORMAT', 'PASS', f'Format: {img.format}')
                else:
                    self.add_result(image_path.name, 'FORMAT', 'WARN', f'Format: {img.format}')
                
                # EXIF data check
                exif_data = img.getexif()
                if exif_data:
                    exif_tags = [TAGS.get(k, k) for k in exif_data.keys()]
                    self.add_result(image_path.name, 'EXIF_DATA', 'INFO', f'EXIF tags: {len(exif_tags)}')
                    
                    # Check for potentially sensitive EXIF data
                    sensitive_tags = ['GPS', 'GPSInfo', 'UserComment', 'ImageDescription']
                    found_sensitive = [tag for tag in sensitive_tags if tag in exif_tags]
                    if found_sensitive:
                        self.add_result(image_path.name, 'SENSITIVE_EXIF', 'WARN', f'Sensitive tags: {found_sensitive}')
                    else:
                        self.add_result(image_path.name, 'SENSITIVE_EXIF', 'PASS', 'No sensitive EXIF data')
                else:
                    self.add_result(image_path.name, 'EXIF_DATA', 'PASS', 'No EXIF data (clean)')
                
                # File size check
                file_size = image_path.stat().st_size
                if file_size > 10 * 1024 * 1024:  # 10MB
                    self.add_result(image_path.name, 'FILE_SIZE', 'WARN', f'Large file: {file_size/1024/1024:.1f}MB')
                else:
                    self.add_result(image_path.name, 'FILE_SIZE', 'PASS', f'Size: {file_size/1024:.1f}KB')
                
                results['tests'] = {
                    'width': width,
                    'height': height,
                    'format': img.format,
                    'mode': img.mode,
                    'file_size': file_size,
                    'exif_tags': len(exif_data) if exif_data else 0
                }
                
        except Exception as e:
            self.add_result(image_path.name, 'VALIDATION_ERROR', 'FAIL', f'Validation error: {str(e)}')
        
        return results
    
    def validate_directory(self, directory: Path) -> dict:
        """Validate all images in directory"""
        results = {
            'directory': str(directory),
            'total_images': 0,
            'validated_images': 0,
            'images': []
        }
        
        if not directory.exists():
            print(f"Directory not found: {directory}")
            return results
        
        # Find all image files
        image_files = []
        for ext in self.supported_formats:
            image_files.extend(directory.glob(f'*{ext}'))
            image_files.extend(directory.glob(f'*{ext.upper()}'))
        
        results['total_images'] = len(image_files)
        
        for image_file in image_files:
            image_result = self.validate_image_file(image_file)
            results['images'].append(image_result)
            results['validated_images'] += 1
        
        return results
    
    def generate_report(self, results: dict, output_file: Path = None):
        """Generate validation report"""
        report = {
            'validation_summary': {
                'total_tests': len(self.validation_results),
                'passed': len([r for r in self.validation_results if r['status'] == 'PASS']),
                'warnings': len([r for r in self.validation_results if r['status'] == 'WARN']),
                'failed': len([r for r in self.validation_results if r['status'] == 'FAIL']),
                'info': len([r for r in self.validation_results if r['status'] == 'INFO'])
            },
            'results': results,
            'detailed_results': self.validation_results
        }
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"✓ Validation report saved to: {output_file}")
        else:
            print(json.dumps(report, indent=2))
        
        return report

def main():
    parser = argparse.ArgumentParser(description='Validate photos for testing compliance')
    parser.add_argument('input_path', help='Path to image file or directory')
    parser.add_argument('--output-report', help='Output report file path')
    parser.add_argument('--format', choices=['json', 'summary'], default='summary', help='Output format')
    
    args = parser.parse_args()
    
    input_path = Path(args.input_path)
    validator = PhotoValidator()
    
    if input_path.is_file():
        print(f"Validating single image: {input_path}")
        results = validator.validate_image_file(input_path)
        summary = {'images': [results]}
    elif input_path.is_dir():
        print(f"Validating directory: {input_path}")
        summary = validator.validate_directory(input_path)
    else:
        print(f"Error: Path not found or invalid: {input_path}")
        return 1
    
    # Generate report
    if args.format == 'json' or args.output_report:
        output_file = Path(args.output_report) if args.output_report else None
        validator.generate_report(summary, output_file)
    else:
        # Print summary
        total = len(validator.validation_results)
        passed = len([r for r in validator.validation_results if r['status'] == 'PASS'])
        warnings = len([r for r in validator.validation_results if r['status'] == 'WARN'])
        failed = len([r for r in validator.validation_results if r['status'] == 'FAIL'])
        
        print(f"\n=== Validation Summary ===")
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"⚠️  Warnings: {warnings}")
        print(f"❌ Failed: {failed}")
        
        if failed > 0:
            print(f"\nFailed tests:")
            for result in validator.validation_results:
                if result['status'] == 'FAIL':
                    print(f"  - {result['filename']}: {result['test']} - {result['details']}")
    
    return 0

if __name__ == '__main__':
    exit(main())
EOF

    chmod +x "${REPO_PATH}/testing/photo_processing/validate_photos.py"
    log "✓ Photo validation tool created"
}

# Create rate limiting and retry configuration tools
create_rate_limiting_tools() {
    log "Creating rate limiting and retry configuration tools..."
    
    mkdir -p "${REPO_PATH}/testing/config_management"
    
    cat > "${REPO_PATH}/testing/config_management/config_manager.py" << 'EOF'
#!/usr/bin/env python3
"""
Configuration Management Tool
Manages retry/backoff settings and resource pools for testing
For legitimate API testing, rate limiting, and load testing configuration
"""

import json
import argparse
import os
from pathlib import Path
from typing import Dict, Any, List
import copy

class ConfigManager:
    """Manages testing configuration with retry logic and resource pools"""
    
    def __init__(self, config_path: str = None):
        self.config_path = Path(config_path) if config_path else Path('config.json')
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        else:
            # Return default configuration
            return {
                "testing": {
                    "environment": "development",
                    "debug": True
                },
                "retry_backoff": {
                    "min": 5,
                    "max": 30,
                    "multiplier": 2,
                    "max_attempts": 3
                },
                "rate_limiting": {
                    "requests_per_second": 1,
                    "burst_limit": 5,
                    "cooldown_period": 60
                },
                "resource_pools": {
                    "proxy_pool": [],
                    "sms_pool": [],
                    "rotation_interval": 3600
                }
            }
    
    def save_config(self):
        """Save configuration to file"""
        # Create directory if it doesn't exist
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
        
        print(f"✓ Configuration saved to: {self.config_path}")
    
    def configure_retry_backoff(self, min_seconds: int = 30, max_seconds: int = 90, 
                               multiplier: float = 2.0, max_attempts: int = 3):
        """Configure retry and backoff settings for API resilience"""
        
        self.config["retry_backoff"] = {
            "min": min_seconds,
            "max": max_seconds,
            "multiplier": multiplier,
            "max_attempts": max_attempts,
            "jitter": True  # Add randomness to prevent thundering herd
        }
        
        print(f"✓ Configured retry backoff: {min_seconds}-{max_seconds}s, max {max_attempts} attempts")
        return self
    
    def configure_rate_limiting(self, rps: float = 1.0, burst: int = 5, cooldown: int = 60):
        """Configure rate limiting for API testing"""
        
        self.config["rate_limiting"] = {
            "requests_per_second": rps,
            "burst_limit": burst,
            "cooldown_period": cooldown,
            "strategy": "token_bucket"
        }
        
        print(f"✓ Configured rate limiting: {rps} RPS, burst {burst}, cooldown {cooldown}s")
        return self
    
    def add_proxy_pool(self, proxies: List[str]):
        """Add proxy pool for load testing"""
        
        # Validate proxy format (basic validation)
        valid_proxies = []
        for proxy in proxies:
            if self._validate_proxy_format(proxy):
                # Sanitize proxy string for logging
                sanitized = self._sanitize_proxy_for_logging(proxy)
                valid_proxies.append(proxy)
                print(f"  ✓ Added proxy: {sanitized}")
            else:
                print(f"  ⚠ Invalid proxy format: {proxy}")
        
        self.config.setdefault("resource_pools", {})["proxy_pool"] = valid_proxies
        print(f"✓ Configured proxy pool with {len(valid_proxies)} proxies")
        return self
    
    def add_sms_pool(self, sms_resources: List[str]):
        """Add SMS resource pool for testing"""
        
        # Basic validation for SMS resources
        valid_resources = []
        for resource in sms_resources:
            # For testing, accept API keys or phone numbers
            if len(resource) > 5:  # Basic length check
                sanitized = self._sanitize_sms_for_logging(resource)
                valid_resources.append(resource)
                print(f"  ✓ Added SMS resource: {sanitized}")
            else:
                print(f"  ⚠ Invalid SMS resource: {resource}")
        
        self.config.setdefault("resource_pools", {})["sms_pool"] = valid_resources
        print(f"✓ Configured SMS pool with {len(valid_resources)} resources")
        return self
    
    def configure_rotation(self, interval_seconds: int = 3600):
        """Configure resource rotation interval"""
        
        self.config.setdefault("resource_pools", {})["rotation_interval"] = interval_seconds
        print(f"✓ Configured rotation interval: {interval_seconds}s ({interval_seconds/3600:.1f}h)")
        return self
    
    def validate_configuration(self) -> bool:
        """Validate current configuration"""
        
        print("Validating configuration...")
        valid = True
        
        # Validate retry backoff settings
        retry_config = self.config.get("retry_backoff", {})
        if retry_config.get("min", 0) >= retry_config.get("max", 0):
            print("  ❌ Retry backoff: min must be less than max")
            valid = False
        else:
            print("  ✓ Retry backoff settings valid")
        
        # Validate rate limiting
        rate_config = self.config.get("rate_limiting", {})
        if rate_config.get("requests_per_second", 0) <= 0:
            print("  ❌ Rate limiting: requests_per_second must be positive")
            valid = False
        else:
            print("  ✓ Rate limiting settings valid")
        
        # Validate resource pools
        pools = self.config.get("resource_pools", {})
        proxy_count = len(pools.get("proxy_pool", []))
        sms_count = len(pools.get("sms_pool", []))
        
        print(f"  ✓ Resource pools: {proxy_count} proxies, {sms_count} SMS resources")
        
        return valid
    
    def generate_test_config(self, test_type: str = "load_test") -> Dict[str, Any]:
        """Generate configuration for specific test type"""
        
        base_config = copy.deepcopy(self.config)
        
        if test_type == "load_test":
            # More aggressive settings for load testing
            base_config["retry_backoff"]["min"] = 10
            base_config["retry_backoff"]["max"] = 60
            base_config["rate_limiting"]["requests_per_second"] = 5
            
        elif test_type == "stress_test":
            # Even more aggressive for stress testing
            base_config["retry_backoff"]["min"] = 5
            base_config["retry_backoff"]["max"] = 30
            base_config["rate_limiting"]["requests_per_second"] = 10
            
        elif test_type == "stability_test":
            # Conservative settings for stability testing
            base_config["retry_backoff"]["min"] = 30
            base_config["retry_backoff"]["max"] = 120
            base_config["rate_limiting"]["requests_per_second"] = 0.5
        
        base_config["test_metadata"] = {
            "test_type": test_type,
            "generated_at": "2024-01-01T00:00:00Z",
            "purpose": "Automated testing configuration"
        }
        
        return base_config
    
    def _validate_proxy_format(self, proxy: str) -> bool:
        """Basic proxy format validation"""
        # Check for basic proxy format (simplified)
        if ':' in proxy and len(proxy.split(':')) >= 2:
            return True
        return False
    
    def _sanitize_proxy_for_logging(self, proxy: str) -> str:
        """Sanitize proxy string for safe logging"""
        if '@' in proxy:
            # Format: user:pass@host:port
            parts = proxy.split('@')
            if len(parts) == 2:
                return f"***:***@{parts[1]}"
        return f"{proxy.split(':')[0]}:***"
    
    def _sanitize_sms_for_logging(self, sms_resource: str) -> str:
        """Sanitize SMS resource for safe logging"""
        if len(sms_resource) > 8:
            return f"{sms_resource[:4]}***{sms_resource[-4:]}"
        return "***"
    
    def print_summary(self):
        """Print configuration summary"""
        
        print("\n=== Configuration Summary ===")
        
        retry = self.config.get("retry_backoff", {})
        print(f"Retry/Backoff: {retry.get('min', 0)}-{retry.get('max', 0)}s, {retry.get('max_attempts', 0)} attempts")
        
        rate = self.config.get("rate_limiting", {})
        print(f"Rate Limiting: {rate.get('requests_per_second', 0)} RPS, burst {rate.get('burst_limit', 0)}")
        
        pools = self.config.get("resource_pools", {})
        proxy_count = len(pools.get("proxy_pool", []))
        sms_count = len(pools.get("sms_pool", []))
        rotation = pools.get("rotation_interval", 0)
        
        print(f"Resource Pools: {proxy_count} proxies, {sms_count} SMS resources")
        print(f"Rotation: every {rotation}s ({rotation/3600:.1f}h)")

def main():
    parser = argparse.ArgumentParser(description='Manage testing configuration')
    parser.add_argument('--config', default='config.json', help='Configuration file path')
    parser.add_argument('--retry-min', type=int, default=30, help='Minimum retry backoff (seconds)')
    parser.add_argument('--retry-max', type=int, default=90, help='Maximum retry backoff (seconds)')
    parser.add_argument('--rate-limit', type=float, default=1.0, help='Requests per second')
    parser.add_argument('--proxy-pool', nargs='*', help='Proxy pool entries')
    parser.add_argument('--sms-pool', nargs='*', help='SMS pool entries')
    parser.add_argument('--rotation-interval', type=int, default=3600, help='Rotation interval (seconds)')
    parser.add_argument('--validate-only', action='store_true', help='Only validate existing config')
    parser.add_argument('--generate-test-config', choices=['load_test', 'stress_test', 'stability_test'], help='Generate test-specific config')
    
    args = parser.parse_args()
    
    manager = ConfigManager(args.config)
    
    if args.validate_only:
        if manager.validate_configuration():
            print("✅ Configuration is valid")
            return 0
        else:
            print("❌ Configuration has errors")
            return 1
    
    if args.generate_test_config:
        test_config = manager.generate_test_config(args.generate_test_config)
        output_file = f"{args.generate_test_config}_config.json"
        with open(output_file, 'w') as f:
            json.dump(test_config, f, indent=2)
        print(f"✓ Generated {args.generate_test_config} configuration: {output_file}")
        return 0
    
    # Configure settings
    manager.configure_retry_backoff(args.retry_min, args.retry_max)
    manager.configure_rate_limiting(args.rate_limit)
    manager.configure_rotation(args.rotation_interval)
    
    if args.proxy_pool:
        manager.add_proxy_pool(args.proxy_pool)
    
    if args.sms_pool:
        manager.add_sms_pool(args.sms_pool)
    
    # Validate and save
    if manager.validate_configuration():
        manager.save_config()
        manager.print_summary()
        return 0
    else:
        print("❌ Configuration validation failed")
        return 1

if __name__ == '__main__':
    exit(main())
EOF

    chmod +x "${REPO_PATH}/testing/config_management/config_manager.py"
    log "✓ Configuration management tool created"
}

# Create resource rotation system
create_resource_rotation_system() {
    log "Creating resource rotation management system..."
    
    cat > "${REPO_PATH}/testing/config_management/resource_rotator.py" << 'EOF'
#!/usr/bin/env python3
"""
Resource Rotation System
Manages proxy and SMS resource rotation for load testing
For legitimate load testing and API testing resource management
"""

import json
import time
import random
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class ResourceUsage:
    """Track resource usage statistics"""
    resource_id: str
    first_used: datetime
    last_used: datetime
    use_count: int
    success_count: int
    failure_count: int
    
    @property
    def success_rate(self) -> float:
        if self.use_count == 0:
            return 0.0
        return self.success_count / self.use_count
    
    @property
    def is_healthy(self) -> bool:
        return self.success_rate >= 0.7  # 70% success rate threshold

class ResourceRotator:
    """Manages rotation of testing resources (proxies, SMS, etc.)"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.config = self.load_config()
        self.usage_stats: Dict[str, ResourceUsage] = {}
        self.current_indices = {"proxy": 0, "sms": 0}
        self.lock = threading.Lock()
        self.last_rotation = {"proxy": datetime.now(), "sms": datetime.now()}
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {"resource_pools": {"proxy_pool": [], "sms_pool": [], "rotation_interval": 3600}}
    
    def get_next_proxy(self) -> Optional[str]:
        """Get next proxy from rotation pool"""
        return self._get_next_resource("proxy", "proxy_pool")
    
    def get_next_sms_resource(self) -> Optional[str]:
        """Get next SMS resource from rotation pool"""
        return self._get_next_resource("sms", "sms_pool")
    
    def _get_next_resource(self, resource_type: str, pool_key: str) -> Optional[str]:
        """Generic method to get next resource from pool"""
        with self.lock:
            pool = self.config.get("resource_pools", {}).get(pool_key, [])
            
            if not pool:
                return None
            
            # Check if rotation interval has passed
            rotation_interval = self.config.get("resource_pools", {}).get("rotation_interval", 3600)
            time_since_rotation = (datetime.now() - self.last_rotation[resource_type]).total_seconds()
            
            if time_since_rotation >= rotation_interval:
                # Time for rotation - move to next resource
                self.current_indices[resource_type] = (self.current_indices[resource_type] + 1) % len(pool)
                self.last_rotation[resource_type] = datetime.now()
                print(f"🔄 Rotated to next {resource_type} resource (index {self.current_indices[resource_type]})")
            
            current_resource = pool[self.current_indices[resource_type]]
            
            # Update usage statistics
            resource_id = f"{resource_type}_{self.current_indices[resource_type]}"
            if resource_id not in self.usage_stats:
                self.usage_stats[resource_id] = ResourceUsage(
                    resource_id=resource_id,
                    first_used=datetime.now(),
                    last_used=datetime.now(),
                    use_count=0,
                    success_count=0,
                    failure_count=0
                )
            
            self.usage_stats[resource_id].last_used = datetime.now()
            self.usage_stats[resource_id].use_count += 1
            
            return current_resource
    
    def report_success(self, resource_type: str):
        """Report successful use of current resource"""
        with self.lock:
            resource_id = f"{resource_type}_{self.current_indices[resource_type]}"
            if resource_id in self.usage_stats:
                self.usage_stats[resource_id].success_count += 1
    
    def report_failure(self, resource_type: str):
        """Report failed use of current resource"""
        with self.lock:
            resource_id = f"{resource_type}_{self.current_indices[resource_type]}"
            if resource_id in self.usage_stats:
                self.usage_stats[resource_id].failure_count += 1
                
                # If resource has too many failures, skip to next
                if self.usage_stats[resource_id].failure_count >= 3:
                    print(f"⚠️ Resource {resource_id} has too many failures, rotating...")
                    self._force_rotate(resource_type)
    
    def _force_rotate(self, resource_type: str):
        """Force rotation to next resource due to failures"""
        pool_key = f"{resource_type}_pool"
        pool = self.config.get("resource_pools", {}).get(pool_key, [])
        
        if len(pool) > 1:
            self.current_indices[resource_type] = (self.current_indices[resource_type] + 1) % len(pool)
            self.last_rotation[resource_type] = datetime.now()
            print(f"🚫 Force rotated {resource_type} to index {self.current_indices[resource_type]}")
    
    def get_healthy_resources(self, resource_type: str) -> List[int]:
        """Get indices of healthy resources"""
        healthy_indices = []
        
        for resource_id, stats in self.usage_stats.items():
            if resource_id.startswith(resource_type) and stats.is_healthy:
                index = int(resource_id.split('_')[-1])
                healthy_indices.append(index)
        
        return healthy_indices
    
    def get_resource_statistics(self) -> Dict[str, Any]:
        """Get comprehensive resource usage statistics"""
        stats = {
            "rotation_status": {
                "proxy_index": self.current_indices["proxy"],
                "sms_index": self.current_indices["sms"],
                "last_proxy_rotation": self.last_rotation["proxy"].isoformat(),
                "last_sms_rotation": self.last_rotation["sms"].isoformat()
            },
            "pool_sizes": {
                "proxy_pool": len(self.config.get("resource_pools", {}).get("proxy_pool", [])),
                "sms_pool": len(self.config.get("resource_pools", {}).get("sms_pool", []))
            },
            "usage_statistics": {}
        }
        
        for resource_id, usage in self.usage_stats.items():
            stats["usage_statistics"][resource_id] = {
                "first_used": usage.first_used.isoformat(),
                "last_used": usage.last_used.isoformat(),
                "use_count": usage.use_count,
                "success_count": usage.success_count,
                "failure_count": usage.failure_count,
                "success_rate": usage.success_rate,
                "is_healthy": usage.is_healthy
            }
        
        return stats
    
    def save_statistics(self, output_file: str = "resource_usage_stats.json"):
        """Save usage statistics to file"""
        stats = self.get_resource_statistics()
        
        with open(output_file, 'w') as f:
            json.dump(stats, f, indent=2)
        
        print(f"✓ Resource statistics saved to: {output_file}")
    
    def print_status(self):
        """Print current rotation status"""
        print("\n=== Resource Rotation Status ===")
        
        proxy_pool_size = len(self.config.get("resource_pools", {}).get("proxy_pool", []))
        sms_pool_size = len(self.config.get("resource_pools", {}).get("sms_pool", []))
        
        print(f"Proxy Pool: {proxy_pool_size} resources (current: {self.current_indices['proxy']})")
        print(f"SMS Pool: {sms_pool_size} resources (current: {self.current_indices['sms']})")
        
        rotation_interval = self.config.get("resource_pools", {}).get("rotation_interval", 3600)
        print(f"Rotation Interval: {rotation_interval}s ({rotation_interval/3600:.1f}h)")
        
        # Show usage statistics
        if self.usage_stats:
            print("\nUsage Statistics:")
            for resource_id, stats in self.usage_stats.items():
                status = "✅" if stats.is_healthy else "⚠️"
                print(f"  {status} {resource_id}: {stats.use_count} uses, {stats.success_rate:.1%} success")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Resource rotation management')
    parser.add_argument('--config', default='config.json', help='Configuration file path')
    parser.add_argument('--test-rotation', action='store_true', help='Test resource rotation')
    parser.add_argument('--show-stats', action='store_true', help='Show current statistics')
    parser.add_argument('--save-stats', help='Save statistics to file')
    
    args = parser.parse_args()
    
    rotator = ResourceRotator(args.config)
    
    if args.show_stats:
        rotator.print_status()
        return 0
    
    if args.save_stats:
        rotator.save_statistics(args.save_stats)
        return 0
    
    if args.test_rotation:
        print("Testing resource rotation...")
        
        # Test proxy rotation
        for i in range(5):
            proxy = rotator.get_next_proxy()
            if proxy:
                sanitized = rotator._sanitize_proxy_for_logging(proxy) if hasattr(rotator, '_sanitize_proxy_for_logging') else "***"
                print(f"  Proxy {i+1}: {sanitized}")
                # Simulate success/failure
                if random.random() > 0.2:  # 80% success rate
                    rotator.report_success("proxy")
                else:
                    rotator.report_failure("proxy")
            else:
                print("  No proxy available")
            
            time.sleep(1)
        
        # Test SMS rotation
        for i in range(3):
            sms = rotator.get_next_sms_resource()
            if sms:
                sanitized = sms[:4] + "***" if len(sms) > 4 else "***"
                print(f"  SMS {i+1}: {sanitized}")
                rotator.report_success("sms")
            else:
                print("  No SMS resource available")
        
        rotator.print_status()
        return 0
    
    rotator.print_status()
    return 0

if __name__ == '__main__':
    exit(main())
EOF

    chmod +x "${REPO_PATH}/testing/config_management/resource_rotator.py"
    log "✓ Resource rotation system created"
}

# Create validation framework
create_validation_framework() {
    log "Creating comprehensive validation framework..."
    
    cat > "${REPO_PATH}/testing/validate_photo_resource_config.py" << 'EOF'
#!/usr/bin/env python3
"""
Photo and Resource Configuration Validator
Validates photo processing, rate limiting, and resource rotation setup
For legitimate testing infrastructure validation
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Any
import argparse

class PhotoResourceValidator:
    """Validates photo processing and resource management configuration"""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.validation_results = []
    
    def add_result(self, test_name: str, status: str, details: str):
        """Add validation result"""
        self.validation_results.append({
            'test': test_name,
            'status': status,
            'details': details
        })
    
    def validate_photo_processing_setup(self) -> bool:
        """Validate photo metadata processing setup"""
        print("Validating photo processing setup...")
        
        photo_script = self.repo_path / "testing" / "photo_processing" / "photo_hygiene.sh"
        if photo_script.exists():
            print("✓ Photo hygiene script found")
            self.add_result("PHOTO_SCRIPT", "PASS", "Photo processing script available")
            
            # Check script contents for key functions
            with open(photo_script, 'r') as f:
                content = f.read()
            
            if 'convert.*-strip' in content:
                print("✓ EXIF stripping functionality found")
                self.add_result("EXIF_STRIPPING", "PASS", "EXIF metadata stripping available")
            else:
                print("⚠ EXIF stripping functionality not found")
                self.add_result("EXIF_STRIPPING", "WARN", "EXIF stripping not detected")
            
            # Check for ImageMagick dependency
            try:
                result = subprocess.run(['which', 'convert'], capture_output=True)
                if result.returncode == 0:
                    print("✓ ImageMagick (convert) available")
                    self.add_result("IMAGEMAGICK", "PASS", "ImageMagick installed")
                else:
                    print("⚠ ImageMagick not found")
                    self.add_result("IMAGEMAGICK", "WARN", "ImageMagick not available")
            except:
                print("⚠ Could not check ImageMagick availability")
                self.add_result("IMAGEMAGICK", "WARN", "ImageMagick check failed")
                
        else:
            print("⚠ Photo hygiene script not found")
            self.add_result("PHOTO_SCRIPT", "WARN", "Photo processing script missing")
            return False
        
        return True
    
    def validate_config_management(self) -> bool:
        """Validate configuration management setup"""
        print("Validating configuration management...")
        
        config_script = self.repo_path / "testing" / "config_management" / "config_manager.py"
        if config_script.exists():
            print("✓ Configuration manager found")
            self.add_result("CONFIG_MANAGER", "PASS", "Configuration management available")
            
            # Test configuration validation
            try:
                result = subprocess.run([
                    'python3', str(config_script),
                    '--validate-only',
                    '--config', '/tmp/test_config.json'
                ], capture_output=True, text=True, timeout=30)
                
                # Even if config doesn't exist, the validator should handle it gracefully
                if result.returncode == 0 or "Configuration is valid" in result.stdout:
                    print("✓ Configuration validation functional")
                    self.add_result("CONFIG_VALIDATION", "PASS", "Config validation working")
                else:
                    print("⚠ Configuration validation issues")
                    self.add_result("CONFIG_VALIDATION", "WARN", f"Validation issues: {result.stderr}")
                    
            except Exception as e:
                print(f"⚠ Configuration validation error: {e}")
                self.add_result("CONFIG_VALIDATION", "WARN", f"Validation error: {e}")
                
        else:
            print("⚠ Configuration manager not found")
            self.add_result("CONFIG_MANAGER", "WARN", "Configuration manager missing")
            return False
        
        return True
    
    def validate_resource_rotation(self) -> bool:
        """Validate resource rotation system"""
        print("Validating resource rotation system...")
        
        rotation_script = self.repo_path / "testing" / "config_management" / "resource_rotator.py"
        if rotation_script.exists():
            print("✓ Resource rotator found")
            self.add_result("RESOURCE_ROTATOR", "PASS", "Resource rotation system available")
            
            # Test basic functionality
            try:
                result = subprocess.run([
                    'python3', str(rotation_script),
                    '--show-stats',
                    '--config', '/tmp/test_config.json'
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    print("✓ Resource rotation functional")
                    self.add_result("ROTATION_FUNCTION", "PASS", "Rotation system working")
                else:
                    print("⚠ Resource rotation issues")
                    self.add_result("ROTATION_FUNCTION", "WARN", f"Rotation issues: {result.stderr}")
                    
            except Exception as e:
                print(f"⚠ Resource rotation error: {e}")
                self.add_result("ROTATION_FUNCTION", "WARN", f"Rotation error: {e}")
                
        else:
            print("⚠ Resource rotator not found")
            self.add_result("RESOURCE_ROTATOR", "WARN", "Resource rotation system missing")
            return False
        
        return True
    
    def validate_configuration_file(self, config_file: Path) -> bool:
        """Validate specific configuration file"""
        print(f"Validating configuration file: {config_file}")
        
        if not config_file.exists():
            print("⚠ Configuration file not found")
            self.add_result("CONFIG_FILE_EXISTS", "WARN", f"Config file missing: {config_file}")
            return False
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            print("✓ Configuration file is valid JSON")
            self.add_result("CONFIG_JSON_VALID", "PASS", "Valid JSON configuration")
            
            # Check for retry/backoff configuration
            retry_config = config.get("retry_backoff", {})
            if retry_config:
                min_val = retry_config.get("min", 0)
                max_val = retry_config.get("max", 0)
                
                if min_val == 30 and max_val == 90:
                    print("✓ Retry backoff configured correctly (30-90s)")
                    self.add_result("RETRY_BACKOFF_CONFIG", "PASS", "Optimal retry/backoff settings")
                elif min_val > 0 and max_val > min_val:
                    print(f"✓ Retry backoff configured ({min_val}-{max_val}s)")
                    self.add_result("RETRY_BACKOFF_CONFIG", "PASS", f"Retry/backoff: {min_val}-{max_val}s")
                else:
                    print("⚠ Retry backoff misconfigured")
                    self.add_result("RETRY_BACKOFF_CONFIG", "WARN", "Retry/backoff needs adjustment")
            else:
                print("ℹ No retry backoff configuration")
                self.add_result("RETRY_BACKOFF_CONFIG", "INFO", "No retry/backoff config")
            
            # Check for resource pools
            pools = config.get("resource_pools", {})
            if pools:
                proxy_count = len(pools.get("proxy_pool", []))
                sms_count = len(pools.get("sms_pool", []))
                
                print(f"✓ Resource pools configured: {proxy_count} proxies, {sms_count} SMS")
                self.add_result("RESOURCE_POOLS", "PASS", f"{proxy_count} proxies, {sms_count} SMS resources")
            else:
                print("ℹ No resource pools configured")
                self.add_result("RESOURCE_POOLS", "INFO", "No resource pools")
                
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in configuration file: {e}")
            self.add_result("CONFIG_JSON_VALID", "FAIL", f"JSON error: {e}")
            return False
        except Exception as e:
            print(f"❌ Error reading configuration file: {e}")
            self.add_result("CONFIG_FILE_READ", "FAIL", f"Read error: {e}")
            return False
        
        return True
    
    def validate_directory_structure(self) -> bool:
        """Validate expected directory structure"""
        print("Validating directory structure...")
        
        expected_dirs = [
            "testing/photo_processing",
            "testing/config_management"
        ]
        
        all_present = True
        for dir_path in expected_dirs:
            full_path = self.repo_path / dir_path
            if full_path.exists():
                print(f"✓ {dir_path} directory exists")
                self.add_result(f"DIR_{dir_path.upper().replace('/', '_')}", "PASS", f"{dir_path} available")
            else:
                print(f"⚠ {dir_path} directory missing")
                self.add_result(f"DIR_{dir_path.upper().replace('/', '_')}", "WARN", f"{dir_path} missing")
                all_present = False
        
        return all_present
    
    def generate_report(self) -> str:
        """Generate comprehensive validation report"""
        report = "# Photo and Resource Configuration Validation Report\n\n"
        report += f"Repository Path: {self.repo_path}\n"
        report += f"Total Tests: {len(self.validation_results)}\n\n"
        
        # Count by status
        status_counts = {}
        for result in self.validation_results:
            status = result['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        report += "## Summary\n"
        for status, count in status_counts.items():
            report += f"- {status}: {count}\n"
        
        report += "\n## Detailed Results\n\n"
        for result in self.validation_results:
            status_icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌", "INFO": "ℹ️"}.get(result['status'], "")
            report += f"- {status_icon} **{result['test']}**: {result['status']} - {result['details']}\n"
        
        return report
    
    def run_full_validation(self, config_file: str = None) -> bool:
        """Run complete validation suite"""
        print("=== Photo and Resource Configuration Validation ===")
        
        all_passed = True
        
        # Validate directory structure
        all_passed &= self.validate_directory_structure()
        
        # Validate photo processing
        all_passed &= self.validate_photo_processing_setup()
        
        # Validate configuration management
        all_passed &= self.validate_config_management()
        
        # Validate resource rotation
        all_passed &= self.validate_resource_rotation()
        
        # Validate specific config file if provided
        if config_file:
            config_path = Path(config_file)
            all_passed &= self.validate_configuration_file(config_path)
        
        # Generate and save report
        report = self.generate_report()
        report_file = self.repo_path / "testing" / "photo_resource_validation_report.md"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(f"\n✓ Validation report saved to {report_file}")
        
        # Print summary
        pass_count = sum(1 for r in self.validation_results if r['status'] == 'PASS')
        warn_count = sum(1 for r in self.validation_results if r['status'] == 'WARN')
        fail_count = sum(1 for r in self.validation_results if r['status'] == 'FAIL')
        total_count = len(self.validation_results)
        
        print(f"\nValidation Summary: {pass_count}/{total_count} passed, {warn_count} warnings, {fail_count} failures")
        
        return fail_count == 0

def main():
    parser = argparse.ArgumentParser(description='Validate photo processing and resource management setup')
    parser.add_argument('--repo-path', default='.', help='Repository path')
    parser.add_argument('--config-file', help='Specific configuration file to validate')
    parser.add_argument('--report-only', action='store_true', help='Generate report only')
    
    args = parser.parse_args()
    
    validator = PhotoResourceValidator(args.repo_path)
    
    if args.report_only:
        # Generate basic report
        validator.validate_directory_structure()
        report = validator.generate_report()
        print(report)
    else:
        # Run full validation
        success = validator.run_full_validation(args.config_file)
        exit(0 if success else 1)

if __name__ == '__main__':
    main()
EOF

    chmod +x "${REPO_PATH}/testing/validate_photo_resource_config.py"
    log "✓ Validation framework created"
}

# Main execution function
main() {
    log "=== Photo Processing and Resource Management Framework Setup ==="
    log "Creating comprehensive infrastructure for image processing and resource management..."
    log "Repository path: $REPO_PATH"
    
    # Create directory structure
    mkdir -p "${REPO_PATH}/testing"/{photo_processing,config_management}
    
    # Setup components
    create_photo_processing_tools
    create_rate_limiting_tools
    create_resource_rotation_system
    create_validation_framework
    
    log "=== Setup Complete ==="
    log ""
    log "📸 Photo Processing Tools:"
    log "  • Metadata Hygiene: testing/photo_processing/photo_hygiene.sh"
    log "  • Photo Validation: testing/photo_processing/validate_photos.py"
    log ""
    log "⚙️  Configuration Management:"
    log "  • Config Manager: testing/config_management/config_manager.py"
    log "  • Resource Rotator: testing/config_management/resource_rotator.py"
    log ""
    log "✅ Validation Framework:"
    log "  • Full Validator: testing/validate_photo_resource_config.py"
    log ""
    log "🚀 Quick Start Examples:"
    log ""
    log "  # Process photos (strip metadata)"
    log "  ./testing/photo_processing/photo_hygiene.sh /path/to/photos/"
    log ""
    log "  # Configure retry/backoff (30-90s)"
    log "  python3 testing/config_management/config_manager.py --retry-min 30 --retry-max 90"
    log ""
    log "  # Setup resource rotation"
    log "  python3 testing/config_management/resource_rotator.py --test-rotation"
    log ""
    log "  # Validate complete setup"
    log "  python3 testing/validate_photo_resource_config.py --config-file config.json"
    log ""
    log "For legitimate image processing, API rate limiting, and load testing resource management."
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        cat << 'EOHELP'
Photo Processing and Resource Management Framework

Usage: ./photo-resource-management.sh [REPO_PATH]

Arguments:
  REPO_PATH    Path to project repository (default: current directory)

This script creates:
- Photo metadata processing tools with EXIF stripping
- Rate limiting and retry/backoff configuration management
- Resource rotation system for proxy and SMS pools
- Comprehensive validation framework

For legitimate image processing, API testing, and load testing purposes.
EOHELP
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac