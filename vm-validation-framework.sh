#!/bin/bash

# VM and Module Validation Framework
# Validates Android VM configuration and security testing modules
# For legitimate security research and application testing

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/logs/vm-validation.log"
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

# Validation results tracking
VALIDATION_RESULTS=()
add_result() {
    local test_name="$1"
    local status="$2"
    local details="$3"
    VALIDATION_RESULTS+=("$test_name|$status|$details")
}

# Check prerequisites
check_prerequisites() {
    log "Checking validation prerequisites..."
    
    # Check if libvirt is available
    if ! command -v virsh &> /dev/null; then
        error "virsh (libvirt) is required but not installed"
        return 1
    fi
    
    # Check if ADB is available
    if ! command -v adb &> /dev/null; then
        error "adb (Android Debug Bridge) is required but not installed"
        return 1
    fi
    
    # Check if grep is available
    if ! command -v grep &> /dev/null; then
        error "grep is required but not installed"
        return 1
    fi
    
    log "All prerequisites satisfied"
    return 0
}

# Validate VM specifications
validate_vm_specs() {
    log "Validating VM specifications..."
    
    local vm_name="android-emulator"
    local validation_passed=true
    
    # Check if VM exists
    if ! virsh list --all | grep -q "$vm_name"; then
        error "VM '$vm_name' not found"
        add_result "VM_EXISTS" "FAIL" "VM not found in libvirt"
        return 1
    fi
    
    # Get VM XML configuration
    local vm_xml
    if ! vm_xml=$(virsh dumpxml "$vm_name" 2>/dev/null); then
        error "Failed to get VM configuration"
        add_result "VM_CONFIG" "FAIL" "Cannot retrieve VM XML"
        return 1
    fi
    
    # Validate machine type (Q35 chipset)
    if echo "$vm_xml" | grep -q "machine.*q35"; then
        log "✓ Q35 chipset confirmed"
        add_result "CHIPSET_Q35" "PASS" "Q35 machine type detected"
    else
        warn "Q35 chipset not detected"
        add_result "CHIPSET_Q35" "WARN" "Q35 machine type not found"
        validation_passed=false
    fi
    
    # Validate CPU count (4 vCPU)
    local cpu_count
    cpu_count=$(echo "$vm_xml" | grep -o '<vcpu[^>]*>[0-9]*</vcpu>' | grep -o '[0-9]*' || echo "0")
    if [ "$cpu_count" -eq 4 ]; then
        log "✓ CPU count: $cpu_count vCPUs"
        add_result "CPU_COUNT" "PASS" "4 vCPUs configured"
    else
        warn "Expected 4 vCPUs, found: $cpu_count"
        add_result "CPU_COUNT" "WARN" "Found $cpu_count vCPUs instead of 4"
        validation_passed=false
    fi
    
    # Validate memory (8 GiB)
    local memory_kb
    memory_kb=$(echo "$vm_xml" | grep -o '<memory[^>]*>[0-9]*</memory>' | grep -o '[0-9]*' || echo "0")
    local memory_gb=$((memory_kb / 1024 / 1024))
    if [ "$memory_gb" -eq 8 ]; then
        log "✓ Memory: ${memory_gb} GiB"
        add_result "MEMORY_SIZE" "PASS" "8 GiB RAM configured"
    else
        warn "Expected 8 GiB RAM, found: ${memory_gb} GiB"
        add_result "MEMORY_SIZE" "WARN" "Found ${memory_gb} GiB instead of 8 GiB"
        validation_passed=false
    fi
    
    # Validate disk size (32 GiB)
    if echo "$vm_xml" | grep -q 'capacity.*32'; then
        log "✓ Disk size: ~32 GiB detected"
        add_result "DISK_SIZE" "PASS" "32 GiB disk detected"
    else
        warn "32 GiB disk size not clearly detected"
        add_result "DISK_SIZE" "WARN" "Disk size validation inconclusive"
    fi
    
    # Validate graphics (SPICE+QXL)
    if echo "$vm_xml" | grep -q "type='spice'" && echo "$vm_xml" | grep -q "type='qxl'"; then
        log "✓ Graphics: SPICE with QXL"
        add_result "GRAPHICS_SPICE" "PASS" "SPICE+QXL graphics configured"
    else
        warn "SPICE+QXL graphics configuration not detected"
        add_result "GRAPHICS_SPICE" "WARN" "Graphics configuration unclear"
    fi
    
    return 0
}

# Verify snapshot existence
verify_vm_snapshot() {
    log "Verifying VM snapshot..."
    
    local vm_name="android-emulator"
    local snapshot_name="base-snap"
    
    # Check if snapshot exists
    if virsh snapshot-list "$vm_name" 2>/dev/null | grep -q "$snapshot_name"; then
        log "✓ Snapshot '$snapshot_name' found"
        add_result "SNAPSHOT_EXISTS" "PASS" "Base snapshot available"
        
        # Get snapshot info
        local snapshot_info
        snapshot_info=$(virsh snapshot-info "$vm_name" "$snapshot_name" 2>/dev/null || echo "Info unavailable")
        info "Snapshot details: $snapshot_info"
        
        return 0
    else
        warn "Snapshot '$snapshot_name' not found"
        add_result "SNAPSHOT_EXISTS" "WARN" "Base snapshot missing"
        
        # List available snapshots
        local available_snapshots
        available_snapshots=$(virsh snapshot-list "$vm_name" 2>/dev/null | tail -n +3 | awk '{print $1}' | tr '\n' ', ' || echo "none")
        info "Available snapshots: $available_snapshots"
        
        return 1
    fi
}

# Test ADB connectivity
test_adb_connectivity() {
    log "Testing ADB connectivity..."
    
    local adb_port="5900"
    local adb_host="127.0.0.1"
    
    # Try to connect to ADB
    if adb connect "${adb_host}:${adb_port}" &>/dev/null; then
        log "✓ ADB connection established"
        add_result "ADB_CONNECT" "PASS" "Connected to ${adb_host}:${adb_port}"
        
        # Test device responsiveness
        if adb shell echo "test" &>/dev/null; then
            log "✓ ADB shell responsive"
            add_result "ADB_SHELL" "PASS" "Shell commands working"
            return 0
        else
            warn "ADB connected but shell not responsive"
            add_result "ADB_SHELL" "WARN" "Shell not responding"
            return 1
        fi
    else
        warn "Failed to connect to ADB at ${adb_host}:${adb_port}"
        add_result "ADB_CONNECT" "FAIL" "Connection failed"
        return 1
    fi
}

# Validate security testing modules
validate_security_modules() {
    log "Validating security testing modules..."
    
    # Check for Magisk (root management)
    if adb shell pm list packages 2>/dev/null | grep -q "com.topjohnwu.magisk"; then
        log "✓ Magisk detected"
        add_result "MAGISK_INSTALLED" "PASS" "Root management available"
        
        # Check Magisk version
        local magisk_version
        magisk_version=$(adb shell magisk -V 2>/dev/null || echo "unknown")
        info "Magisk version: $magisk_version"
    else
        warn "Magisk not detected"
        add_result "MAGISK_INSTALLED" "WARN" "Root management not available"
    fi
    
    # Check for Xposed Framework (for testing instrumentation)
    if adb shell pm list packages 2>/dev/null | grep -q "xposed"; then
        log "✓ Xposed Framework detected"
        add_result "XPOSED_INSTALLED" "PASS" "Instrumentation framework available"
    else
        warn "Xposed Framework not detected"
        add_result "XPOSED_INSTALLED" "WARN" "Instrumentation framework not available"
    fi
    
    # Check build tags for testing indicators
    local build_tags
    build_tags=$(adb shell getprop ro.build.tags 2>/dev/null || echo "unknown")
    if [[ "$build_tags" == *"test-keys"* ]]; then
        log "✓ Test build detected (test-keys)"
        add_result "TEST_BUILD" "PASS" "Development build confirmed"
    else
        info "Build tags: $build_tags"
        add_result "TEST_BUILD" "INFO" "Build type: $build_tags"
    fi
}

# Validate development repositories
validate_repositories() {
    log "Validating development repositories..."
    
    local repo_checks=(
        "sensor-thermal-emulator:Thermal sensor testing"
        "gps-mock-service:GPS testing service"
        "app-instrumentation:Application testing framework"
    )
    
    for check in "${repo_checks[@]}"; do
        local repo_name="${check%%:*}"
        local description="${check##*:}"
        
        if find "$REPO_PATH" -name "*${repo_name}*" -type d 2>/dev/null | head -1 | grep -q .; then
            log "✓ Found repository: $repo_name"
            add_result "REPO_${repo_name^^}" "PASS" "$description available"
        else
            warn "Repository not found: $repo_name"
            add_result "REPO_${repo_name^^}" "WARN" "$description not available"
        fi
    done
    
    # Check for configuration files
    local config_files=(
        "android-dev-config.json"
        "testing-framework.yaml"
        "security-test-suite.conf"
    )
    
    for config_file in "${config_files[@]}"; do
        if find "$REPO_PATH" -name "$config_file" -type f 2>/dev/null | head -1 | grep -q .; then
            log "✓ Configuration found: $config_file"
            add_result "CONFIG_${config_file^^}" "PASS" "Configuration available"
        else
            info "Configuration not found: $config_file"
            add_result "CONFIG_${config_file^^}" "INFO" "Optional configuration missing"
        fi
    done
}

# Test system capabilities
test_system_capabilities() {
    log "Testing system capabilities..."
    
    # Test battery information access
    if adb shell dumpsys battery 2>/dev/null | grep -q "level:"; then
        log "✓ Battery information accessible"
        add_result "BATTERY_ACCESS" "PASS" "Battery telemetry available"
    else
        warn "Battery information not accessible"
        add_result "BATTERY_ACCESS" "WARN" "Battery telemetry unavailable"
    fi
    
    # Test location services
    if adb shell dumpsys location 2>/dev/null | grep -q "LocationManager"; then
        log "✓ Location services accessible"
        add_result "LOCATION_ACCESS" "PASS" "Location services available"
    else
        warn "Location services not accessible"
        add_result "LOCATION_ACCESS" "WARN" "Location services unavailable"
    fi
    
    # Test sensors
    if adb shell dumpsys sensorservice 2>/dev/null | grep -q "Sensor"; then
        log "✓ Sensor services accessible"
        add_result "SENSOR_ACCESS" "PASS" "Sensor data available"
    else
        warn "Sensor services not accessible"
        add_result "SENSOR_ACCESS" "WARN" "Sensor data unavailable"
    fi
    
    # Test package manager
    if adb shell pm list packages 2>/dev/null | wc -l | grep -q "[0-9]"; then
        local package_count
        package_count=$(adb shell pm list packages 2>/dev/null | wc -l)
        log "✓ Package manager accessible ($package_count packages)"
        add_result "PACKAGE_MANAGER" "PASS" "$package_count packages listed"
    else
        warn "Package manager not accessible"
        add_result "PACKAGE_MANAGER" "WARN" "Package enumeration failed"
    fi
}

# Generate validation report
generate_report() {
    log "Generating validation report..."
    
    local report_file="${SCRIPT_DIR}/logs/vm-validation-report-$(date +%Y%m%d-%H%M%S).txt"
    
    cat > "$report_file" << EOF
# VM and Module Validation Report
Generated: $(date)
Repository Path: $REPO_PATH

## Summary
Total Tests: ${#VALIDATION_RESULTS[@]}

EOF

    # Count results by status
    local pass_count=0
    local warn_count=0
    local fail_count=0
    local info_count=0
    
    for result in "${VALIDATION_RESULTS[@]}"; do
        local status=$(echo "$result" | cut -d'|' -f2)
        case "$status" in
            "PASS") ((pass_count++)) ;;
            "WARN") ((warn_count++)) ;;
            "FAIL") ((fail_count++)) ;;
            "INFO") ((info_count++)) ;;
        esac
    done
    
    cat >> "$report_file" << EOF
PASS: $pass_count
WARN: $warn_count
FAIL: $fail_count
INFO: $info_count

## Detailed Results

EOF

    # Add detailed results
    for result in "${VALIDATION_RESULTS[@]}"; do
        local test_name=$(echo "$result" | cut -d'|' -f1)
        local status=$(echo "$result" | cut -d'|' -f2)
        local details=$(echo "$result" | cut -d'|' -f3)
        
        printf "%-25s | %-4s | %s\n" "$test_name" "$status" "$details" >> "$report_file"
    done
    
    cat >> "$report_file" << EOF

## Recommendations

EOF

    # Add recommendations based on results
    if [ "$fail_count" -gt 0 ]; then
        echo "- Address FAILED validations before proceeding with testing" >> "$report_file"
    fi
    
    if [ "$warn_count" -gt 0 ]; then
        echo "- Review WARNING items for optimal testing environment" >> "$report_file"
    fi
    
    echo "- Ensure all security testing is conducted ethically and legally" >> "$report_file"
    echo "- Document test procedures and maintain audit trails" >> "$report_file"
    echo "- Regular validation recommended for consistency" >> "$report_file"
    
    log "Report generated: $report_file"
    
    # Display summary
    echo ""
    log "=== VALIDATION SUMMARY ==="
    log "✅ PASS: $pass_count"
    log "⚠️  WARN: $warn_count"
    log "❌ FAIL: $fail_count"
    log "ℹ️  INFO: $info_count"
    echo ""
    
    if [ "$fail_count" -eq 0 ]; then
        log "🎉 Validation completed successfully!"
        return 0
    else
        warn "⚠️ Some validations failed. Review the report for details."
        return 1
    fi
}

# Cleanup function
cleanup() {
    log "Cleaning up validation environment..."
    
    # Disconnect ADB if connected
    adb disconnect &>/dev/null || true
    
    log "Cleanup completed"
}

# Main execution function
main() {
    log "=== VM and Module Validation Framework ==="
    log "Starting comprehensive validation..."
    log "Repository path: $REPO_PATH"
    
    # Set trap for cleanup
    trap cleanup EXIT
    
    # Run validation phases
    local overall_success=true
    
    if ! check_prerequisites; then
        error "Prerequisites check failed"
        exit 1
    fi
    
    # VM Configuration Validation
    log "Phase 1: VM Configuration Validation"
    if ! validate_vm_specs; then
        overall_success=false
    fi
    
    if ! verify_vm_snapshot; then
        overall_success=false
    fi
    
    # Connectivity Testing
    log "Phase 2: Connectivity Testing"
    if ! test_adb_connectivity; then
        overall_success=false
    fi
    
    # Security Module Validation
    log "Phase 3: Security Module Validation"
    if ! validate_security_modules; then
        overall_success=false
    fi
    
    # Repository Validation
    log "Phase 4: Repository Validation"
    if ! validate_repositories; then
        overall_success=false
    fi
    
    # System Capabilities Testing
    log "Phase 5: System Capabilities Testing"
    if ! test_system_capabilities; then
        overall_success=false
    fi
    
    # Generate final report
    log "Phase 6: Report Generation"
    if ! generate_report; then
        overall_success=false
    fi
    
    if [ "$overall_success" = true ]; then
        log "🏆 All validations completed successfully!"
        exit 0
    else
        warn "⚠️ Some validations had issues. Check the report for details."
        exit 1
    fi
}

# Help function
show_help() {
    cat << EOF
VM and Module Validation Framework

Usage: $0 [REPO_PATH]

Arguments:
  REPO_PATH    Path to project repository (default: current directory)

Examples:
  $0                          # Validate using current directory
  $0 /path/to/project         # Validate using specific repository path
  $0 --help                   # Show this help message

This script validates:
- VM configuration and specifications
- Android emulator connectivity
- Security testing module availability
- Development repository structure
- System capability access

For legitimate security testing and development purposes only.
EOF
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        show_help
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac