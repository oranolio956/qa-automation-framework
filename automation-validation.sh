#!/bin/bash

# Automation Validation Framework
# Validates automation scripts, testing configurations, and behavioral patterns
# For legitimate software testing and quality assurance purposes

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/logs/automation-validation.log"
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
    log "Checking automation validation prerequisites..."
    
    # Check required tools
    local required_tools=("curl" "grep" "find" "jq" "python3")
    
    for tool in "${required_tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            info "✓ $tool available"
        else
            warn "⚠ $tool not available (may limit some validations)"
        fi
    done
    
    # Check for Node.js (often used with Appium)
    if command -v node &> /dev/null; then
        local node_version=$(node --version)
        log "✓ Node.js available: $node_version"
        add_result "NODE_JS" "PASS" "Node.js runtime available"
    else
        warn "Node.js not available (may limit Appium validation)"
        add_result "NODE_JS" "WARN" "Node.js runtime missing"
    fi
    
    # Check for Python (common for automation scripts)
    if command -v python3 &> /dev/null; then
        local python_version=$(python3 --version)
        log "✓ Python available: $python_version"
        add_result "PYTHON" "PASS" "Python runtime available"
    else
        warn "Python not available (may limit automation validation)"
        add_result "PYTHON" "WARN" "Python runtime missing"
    fi
    
    log "Prerequisites check completed"
    return 0
}

# Validate Appium configurations and scripts
validate_appium_automation() {
    log "Validating Appium automation setup..."
    
    # Search for Appium-related files
    local appium_files=$(find "$REPO_PATH" -type f \( -name "*appium*" -o -name "*webdriver*" -o -name "*selenium*" \) 2>/dev/null || true)
    if [ -n "$appium_files" ]; then
        log "✓ Appium-related files found"
        add_result "APPIUM_FILES" "PASS" "Automation framework files detected"
        
        # Analyze each file
        while IFS= read -r file; do
            if [ -f "$file" ]; then
                info "Analyzing: $file"
                
                # Check file type and contents
                case "$file" in
                    *.py)
                        log "  ✓ Python automation script"
                        # Check for Appium imports
                        if grep -q "from appium\|import appium\|webdriver.Remote" "$file"; then
                            log "    ✓ Appium WebDriver imports found"
                        fi
                        # Check for proper error handling
                        if grep -q "try:\|except\|finally:" "$file"; then
                            log "    ✓ Error handling implemented"
                        else
                            warn "    ⚠ Limited error handling"
                        fi
                        ;;
                    *.js|*.ts)
                        log "  ✓ JavaScript/TypeScript automation script"
                        # Check for WebDriver imports
                        if grep -q "webdriver\|appium" "$file"; then
                            log "    ✓ WebDriver imports found"
                        fi
                        ;;
                    *.json)
                        log "  ✓ Configuration file"
                        # Validate JSON syntax
                        if command -v jq &> /dev/null && jq empty "$file" &> /dev/null; then
                            log "    ✓ Valid JSON format"
                        else
                            warn "    ⚠ Invalid JSON or jq not available"
                        fi
                        ;;
                    *.yml|*.yaml)
                        log "  ✓ YAML configuration file"
                        ;;
                esac
            fi
        done <<< "$appium_files"
    else
        warn "No Appium-related files found"
        add_result "APPIUM_FILES" "WARN" "No automation framework detected"
    fi
    
    # Check for Appium configuration files
    local config_files=$(find "$REPO_PATH" -name "*config*" -name "*.json" 2>/dev/null || true)
    if [ -n "$config_files" ]; then
        log "✓ Configuration files found"
        
        for config_file in $config_files; do
            if [ -f "$config_file" ] && command -v jq &> /dev/null; then
                info "Analyzing config: $config_file"
                
                # Check for retry/backoff configurations
                if jq -e '.retry_backoff // .retryBackoff // .retry // .backoff' "$config_file" &> /dev/null; then
                    log "  ✓ Retry/backoff configuration found"
                    add_result "RETRY_CONFIG" "PASS" "Resilience configuration present"
                    
                    # Extract retry settings
                    local retry_settings=$(jq -r '.retry_backoff // .retryBackoff // .retry // .backoff' "$config_file" 2>/dev/null || echo "null")
                    if [ "$retry_settings" != "null" ]; then
                        info "    Settings: $retry_settings"
                    fi
                else
                    info "  ℹ No retry/backoff configuration in this file"
                fi
                
                # Check for timing configurations
                if jq -e '.timeout // .delay // .wait' "$config_file" &> /dev/null; then
                    log "  ✓ Timing configuration found"
                    add_result "TIMING_CONFIG" "PASS" "Timing configuration present"
                else
                    info "  ℹ No timing configuration in this file"
                fi
                
                # Check for device/capability configurations
                if jq -e '.capabilities // .desiredCapabilities // .device' "$config_file" &> /dev/null; then
                    log "  ✓ Device/capability configuration found"
                    add_result "DEVICE_CONFIG" "PASS" "Device configuration present"
                else
                    info "  ℹ No device configuration in this file"
                fi
            fi
        done
    else
        info "No JSON configuration files found"
        add_result "CONFIG_FILES" "INFO" "No JSON configuration files"
    fi
    
    # Check for automation directories
    local automation_dirs=$(find "$REPO_PATH" -type d -name "*automation*" -o -name "*test*" -o -name "*spec*" 2>/dev/null || true)
    if [ -n "$automation_dirs" ]; then
        log "✓ Automation directories found"
        add_result "AUTOMATION_DIRS" "PASS" "Test organization structure present"
        
        while IFS= read -r dir; do
            if [ -d "$dir" ]; then
                local script_count=$(find "$dir" -type f \( -name "*.py" -o -name "*.js" -o -name "*.ts" \) 2>/dev/null | wc -l)
                info "  $dir: $script_count automation scripts"
            fi
        done <<< "$automation_dirs"
    else
        info "No dedicated automation directories found"
        add_result "AUTOMATION_DIRS" "INFO" "No dedicated automation directories"
    fi
}

# Validate behavioral logging and monitoring
validate_behavioral_logging() {
    log "Validating behavioral logging and monitoring..."
    
    # Check for common log directories
    local log_locations=(
        "/var/log"
        "/opt/*/logs"
        "${REPO_PATH}/logs"
        "${REPO_PATH}/log"
        "/tmp"
    )
    
    local logs_found=false
    
    for log_location in "${log_locations[@]}"; do
        # Use find to handle glob patterns safely
        if [ "$log_location" = "/opt/*/logs" ]; then
            local opt_logs=$(find /opt -type d -name "logs" 2>/dev/null || true)
            if [ -n "$opt_logs" ]; then
                while IFS= read -r log_dir; do
                    check_log_directory "$log_dir"
                    logs_found=true
                done <<< "$opt_logs"
            fi
        elif [ -d "$log_location" ]; then
            check_log_directory "$log_location"
            logs_found=true
        fi
    done
    
    if [ "$logs_found" = true ]; then
        add_result "LOG_DIRECTORIES" "PASS" "Log directories accessible"
    else
        add_result "LOG_DIRECTORIES" "WARN" "No accessible log directories"
    fi
    
    # Check for specific automation log patterns
    check_automation_logs
    
    # Check for behavioral analysis logs
    check_behavioral_patterns
}

# Helper function to check log directory
check_log_directory() {
    local log_dir="$1"
    info "Checking log directory: $log_dir"
    
    # Check for automation-related logs
    local automation_logs=$(find "$log_dir" -name "*appium*" -o -name "*selenium*" -o -name "*automation*" -o -name "*test*" 2>/dev/null || true)
    if [ -n "$automation_logs" ]; then
        log "  ✓ Automation logs found"
        
        while IFS= read -r log_file; do
            if [ -f "$log_file" ] && [ -r "$log_file" ]; then
                local log_size=$(stat -f%z "$log_file" 2>/dev/null || stat -c%s "$log_file" 2>/dev/null || echo "0")
                info "    $log_file (${log_size} bytes)"
                
                # Analyze recent entries (last 100 lines)
                if [ "$log_size" -gt 0 ]; then
                    analyze_log_content "$log_file"
                fi
            fi
        done <<< "$automation_logs"
    fi
}

# Helper function to analyze log content
analyze_log_content() {
    local log_file="$1"
    
    # Check for action delays (indicating proper timing)
    if tail -100 "$log_file" 2>/dev/null | grep -q "action delay\|delay.*ms\|wait.*seconds"; then
        log "    ✓ Action timing patterns detected"
        add_result "ACTION_TIMING" "PASS" "Proper timing patterns in logs"
    fi
    
    # Check for retry patterns
    if tail -100 "$log_file" 2>/dev/null | grep -q "retry\|attempt\|backoff"; then
        log "    ✓ Retry patterns detected"
        add_result "RETRY_PATTERNS" "PASS" "Retry logic evidence in logs"
    fi
    
    # Check for error handling
    if tail -100 "$log_file" 2>/dev/null | grep -q "error\|exception\|failed"; then
        log "    ✓ Error handling evidence detected"
        add_result "ERROR_HANDLING" "PASS" "Error handling evidence in logs"
    fi
    
    # Check for performance metrics
    if tail -100 "$log_file" 2>/dev/null | grep -q "duration\|elapsed\|performance\|timing"; then
        log "    ✓ Performance metrics detected"
        add_result "PERFORMANCE_METRICS" "PASS" "Performance tracking in logs"
    fi
}

# Check for automation-specific logs
check_automation_logs() {
    log "Checking for automation-specific log patterns..."
    
    # Common automation log files
    local automation_log_files=(
        "/opt/signup/appium.log"
        "/var/log/automation.log"
        "/tmp/appium.log"
        "${REPO_PATH}/logs/automation.log"
    )
    
    for log_file in "${automation_log_files[@]}"; do
        if [ -f "$log_file" ] && [ -r "$log_file" ]; then
            log "✓ Found automation log: $log_file"
            add_result "AUTOMATION_LOGS" "PASS" "Automation logging active"
            
            # Analyze specific patterns
            if grep -q "action delay" "$log_file" 2>/dev/null; then
                log "  ✓ Action delay patterns found"
            fi
            
            if grep -q "login_time\|session_duration" "$log_file" 2>/dev/null; then
                log "  ✓ Session timing patterns found"
            fi
            
            if grep -q "error\|exception" "$log_file" 2>/dev/null; then
                log "  ✓ Error tracking patterns found"
            fi
            
            return 0
        fi
    done
    
    warn "No automation log files found in standard locations"
    add_result "AUTOMATION_LOGS" "WARN" "No automation logs detected"
}

# Check for behavioral analysis patterns
check_behavioral_patterns() {
    log "Checking for behavioral analysis patterns..."
    
    # Common persona/behavioral log files
    local behavioral_log_files=(
        "/var/log/persona_modulator.log"
        "/var/log/behavioral.log"
        "/opt/automation/behavioral.log"
        "${REPO_PATH}/logs/behavioral.log"
    )
    
    for log_file in "${behavioral_log_files[@]}"; do
        if [ -f "$log_file" ] && [ -r "$log_file" ]; then
            log "✓ Found behavioral log: $log_file"
            add_result "BEHAVIORAL_LOGS" "PASS" "Behavioral analysis logging active"
            
            # Analyze behavioral patterns
            if grep -q "login_time\|access_pattern\|user_behavior" "$log_file" 2>/dev/null; then
                log "  ✓ User behavior patterns found"
            fi
            
            if grep -q "swipe_count\|tap_pattern\|gesture" "$log_file" 2>/dev/null; then
                log "  ✓ Interaction patterns found"
            fi
            
            if grep -q "session_length\|idle_time\|activity_duration" "$log_file" 2>/dev/null; then
                log "  ✓ Session analysis patterns found"
            fi
            
            return 0
        fi
    done
    
    info "No behavioral analysis logs found"
    add_result "BEHAVIORAL_LOGS" "INFO" "No behavioral analysis logs detected"
}

# Validate content processing service
validate_content_service() {
    log "Validating content processing service..."
    
    # Test content service endpoint
    local content_service_url="http://localhost:5000"
    local test_endpoint="${content_service_url}/process"
    
    # Check if service is accessible
    if curl -s --connect-timeout 5 "${content_service_url}/health" &> /dev/null; then
        log "✓ Content service is accessible"
        add_result "CONTENT_SERVICE" "PASS" "Content processing service online"
    elif curl -s --connect-timeout 5 "$content_service_url" &> /dev/null; then
        log "✓ Content service responding (no health endpoint)"
        add_result "CONTENT_SERVICE" "PASS" "Content service accessible"
    else
        warn "Content service not accessible at $content_service_url"
        add_result "CONTENT_SERVICE" "WARN" "Content service not accessible"
        return 1
    fi
    
    # Test content processing endpoint
    if command -v jq &> /dev/null; then
        log "Testing content processing endpoint..."
        
        local test_payload='{"content":"test message for processing"}'
        local response=$(curl -s -X POST "$test_endpoint" \
            -H "Content-Type: application/json" \
            -d "$test_payload" \
            --connect-timeout 10 || echo "")
        
        if [ -n "$response" ]; then
            # Check if response is valid JSON
            if echo "$response" | jq empty &> /dev/null; then
                log "✓ Content service returning valid JSON"
                add_result "CONTENT_JSON" "PASS" "Valid JSON response from content service"
                
                # Check for result field
                local result=$(echo "$response" | jq -r '.result // .processed // .output // empty' 2>/dev/null || echo "")
                if [ -n "$result" ] && [ "$result" != "null" ]; then
                    log "✓ Content processing successful"
                    info "  Processed result: $result"
                    add_result "CONTENT_PROCESSING" "PASS" "Content processing functional"
                else
                    warn "Content service response missing expected result"
                    add_result "CONTENT_PROCESSING" "WARN" "Content processing response incomplete"
                fi
            else
                warn "Content service returning invalid JSON"
                add_result "CONTENT_JSON" "WARN" "Invalid JSON response"
                info "Raw response: $response"
            fi
        else
            warn "No response from content processing endpoint"
            add_result "CONTENT_PROCESSING" "WARN" "Content processing endpoint not responding"
        fi
    else
        warn "jq not available for content service testing"
        add_result "JQ_AVAILABLE" "WARN" "Cannot validate JSON responses"
    fi
    
    # Check for content service configuration
    local config_files=$(find "$REPO_PATH" -name "*content*" -name "*.json" -o -name "*content*" -name "*.yml" 2>/dev/null || true)
    if [ -n "$config_files" ]; then
        log "✓ Content service configuration files found"
        add_result "CONTENT_CONFIG" "PASS" "Content service configuration present"
        
        while IFS= read -r config_file; do
            if [ -f "$config_file" ]; then
                info "  Config: $config_file"
            fi
        done <<< "$config_files"
    else
        info "No content service configuration files found"
        add_result "CONTENT_CONFIG" "INFO" "No content service configuration detected"
    fi
}

# Generate validation report
generate_report() {
    log "Generating automation validation report..."
    
    local report_file="${SCRIPT_DIR}/logs/automation-validation-report-$(date +%Y%m%d-%H%M%S).txt"
    
    cat > "$report_file" << EOF
# Automation Validation Report
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

## Automation Framework Status

$(if [ "$pass_count" -gt 6 ]; then
    echo "✅ READY: Automation framework appears well-configured"
elif [ "$pass_count" -gt 3 ]; then
    echo "⚠️ PARTIAL: Some automation components configured, review warnings"
else
    echo "❌ LIMITED: Limited automation capabilities detected"
fi)

## Recommendations

EOF

    # Add recommendations based on results
    if [ "$fail_count" -gt 0 ]; then
        echo "- Address FAILED validations before automation testing" >> "$report_file"
    fi
    
    if [ "$warn_count" -gt 0 ]; then
        echo "- Review WARNING items for optimal automation setup" >> "$report_file"
    fi
    
    echo "- Ensure all automation testing is conducted ethically and legally" >> "$report_file"
    echo "- Use behavioral analysis only for legitimate testing purposes" >> "$report_file"
    echo "- Maintain proper logging and audit trails for test compliance" >> "$report_file"
    echo "- Regular validation recommended for automation infrastructure" >> "$report_file"
    echo "- Implement proper retry logic and error handling in automation scripts" >> "$report_file"
    
    log "Report generated: $report_file"
    
    # Display summary
    echo ""
    log "=== AUTOMATION VALIDATION SUMMARY ==="
    log "✅ PASS: $pass_count"
    log "⚠️  WARN: $warn_count"
    log "❌ FAIL: $fail_count"
    log "ℹ️  INFO: $info_count"
    echo ""
    
    if [ "$fail_count" -eq 0 ]; then
        log "🎉 Automation validation completed successfully!"
        return 0
    else
        warn "⚠️ Some automation validations failed. Review the report for details."
        return 1
    fi
}

# Main execution function
main() {
    log "=== Automation Validation Framework ==="
    log "Starting automation infrastructure validation..."
    log "Repository path: $REPO_PATH"
    
    # Run validation phases
    local overall_success=true
    
    if ! check_prerequisites; then
        warn "Some prerequisites missing, continuing with limited validation"
    fi
    
    # Appium Automation Validation
    log "Phase 1: Appium Automation Validation"
    if ! validate_appium_automation; then
        overall_success=false
    fi
    
    # Behavioral Logging Validation
    log "Phase 2: Behavioral Logging Validation"
    if ! validate_behavioral_logging; then
        overall_success=false
    fi
    
    # Content Service Validation
    log "Phase 3: Content Service Validation"
    if ! validate_content_service; then
        overall_success=false
    fi
    
    # Generate final report
    log "Phase 4: Report Generation"
    if ! generate_report; then
        overall_success=false
    fi
    
    if [ "$overall_success" = true ]; then
        log "🏆 All automation validations completed successfully!"
        exit 0
    else
        warn "⚠️ Some automation validations had issues. Check the report for details."
        exit 1
    fi
}

# Help function
show_help() {
    cat << EOF
Automation Validation Framework

Usage: $0 [REPO_PATH]

Arguments:
  REPO_PATH    Path to project repository (default: current directory)

Examples:
  $0                          # Validate using current directory
  $0 /path/to/project         # Validate using specific repository path
  $0 --help                   # Show this help message

This script validates:
- Appium automation scripts and configurations
- Retry/backoff and timing configurations
- Behavioral logging and monitoring patterns
- Content processing service functionality
- Test automation infrastructure

For legitimate software testing and quality assurance purposes only.
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