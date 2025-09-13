#!/bin/bash

# Network and Patch Validation Framework
# Validates networking infrastructure, proxy configurations, and application patch pipeline
# For legitimate security testing and development purposes

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/logs/network-validation.log"
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
    log "Checking network validation prerequisites..."
    
    # Check required tools
    local required_tools=("curl" "grep" "find" "openssl" "docker" "jq")
    
    for tool in "${required_tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            info "✓ $tool available"
        else
            warn "⚠ $tool not available (may limit some validations)"
        fi
    done
    
    # Check if Docker is running
    if docker info &> /dev/null; then
        log "✓ Docker service is running"
        add_result "DOCKER_SERVICE" "PASS" "Docker daemon accessible"
    else
        warn "Docker service not running"
        add_result "DOCKER_SERVICE" "WARN" "Docker daemon not accessible"
    fi
    
    log "Prerequisites check completed"
    return 0
}

# Validate proxy configurations
validate_proxy_config() {
    log "Validating proxy configurations..."
    
    # Check for Squid proxy configuration
    local squid_configs=$(find "$REPO_PATH" -name "*squid*" -type f 2>/dev/null || true)
    if [ -n "$squid_configs" ]; then
        log "✓ Squid configuration files found"
        add_result "SQUID_CONFIG" "PASS" "Proxy configuration available"
        
        # Validate squid.conf contents
        for config in $squid_configs; do
            if [ -f "$config" ]; then
                info "Analyzing: $config"
                
                # Check for basic proxy settings
                if grep -q "http_port" "$config"; then
                    log "  ✓ HTTP port configuration found"
                else
                    warn "  ⚠ HTTP port configuration missing"
                fi
                
                if grep -q "access_log" "$config"; then
                    log "  ✓ Access logging configured"
                else
                    warn "  ⚠ Access logging not configured"
                fi
                
                if grep -q "cache_dir" "$config"; then
                    log "  ✓ Cache directory configured"
                else
                    info "  ℹ Cache directory not specified (memory only)"
                fi
            fi
        done
    else
        warn "No Squid configuration files found"
        add_result "SQUID_CONFIG" "WARN" "Proxy configuration not found"
    fi
    
    # Check for Docker Compose proxy services
    local docker_compose_files=$(find "$REPO_PATH" -name "docker-compose*.yml" -o -name "docker-compose*.yaml" 2>/dev/null || true)
    if [ -n "$docker_compose_files" ]; then
        log "✓ Docker Compose files found"
        
        for compose_file in $docker_compose_files; do
            if [ -f "$compose_file" ]; then
                info "Analyzing: $compose_file"
                
                # Check for proxy services
                if grep -q "squid\|proxy" "$compose_file"; then
                    log "  ✓ Proxy service configuration found"
                    add_result "DOCKER_PROXY" "PASS" "Docker proxy service configured"
                else
                    info "  ℹ No proxy service in this compose file"
                fi
                
                # Check for network configuration
                if grep -q "networks:" "$compose_file"; then
                    log "  ✓ Network configuration found"
                else
                    warn "  ⚠ Network configuration missing"
                fi
            fi
        done
    else
        warn "No Docker Compose files found"
        add_result "DOCKER_COMPOSE" "WARN" "No Docker Compose configuration"
    fi
    
    # Check for proxy rotation configuration
    local proxy_configs=$(find "$REPO_PATH" -name "*proxy*" -name "*.json" 2>/dev/null || true)
    if [ -n "$proxy_configs" ]; then
        log "✓ Proxy rotation configuration files found"
        
        for proxy_config in $proxy_configs; do
            if [ -f "$proxy_config" ] && command -v jq &> /dev/null; then
                info "Analyzing: $proxy_config"
                
                # Validate JSON structure
                if jq empty "$proxy_config" &> /dev/null; then
                    log "  ✓ Valid JSON format"
                    
                    # Check for proxy list
                    local proxy_count=$(jq -r '.proxies | length? // 0' "$proxy_config" 2>/dev/null || echo "0")
                    if [ "$proxy_count" -gt 0 ]; then
                        log "  ✓ Proxy rotation list: $proxy_count entries"
                        add_result "PROXY_ROTATION" "PASS" "$proxy_count proxy entries configured"
                    else
                        warn "  ⚠ No proxy entries found"
                        add_result "PROXY_ROTATION" "WARN" "Proxy list empty or malformed"
                    fi
                else
                    error "  ❌ Invalid JSON format"
                    add_result "PROXY_JSON" "FAIL" "Malformed JSON configuration"
                fi
            fi
        done
    else
        info "No proxy rotation configuration found"
        add_result "PROXY_ROTATION" "INFO" "No proxy rotation configuration"
    fi
}

# Validate network infrastructure
validate_network_infrastructure() {
    log "Validating network infrastructure..."
    
    # Check for running proxy services
    if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -i "proxy\|squid" &> /dev/null; then
        log "✓ Proxy containers running"
        add_result "PROXY_RUNNING" "PASS" "Proxy services active"
        
        # List running proxy containers
        docker ps --format "table {{.Names}}\t{{.Status}}" | grep -i "proxy\|squid" | while read -r line; do
            info "  $line"
        done
    else
        warn "No proxy containers currently running"
        add_result "PROXY_RUNNING" "WARN" "No active proxy services"
    fi
    
    # Check network connectivity
    if curl -s --connect-timeout 5 http://example.com &> /dev/null; then
        log "✓ External network connectivity available"
        add_result "NETWORK_ACCESS" "PASS" "Internet connectivity confirmed"
    else
        warn "External network connectivity issues"
        add_result "NETWORK_ACCESS" "WARN" "Internet connectivity problems"
    fi
    
    # Test proxy functionality (if available)
    local proxy_port="3128"
    if netstat -tuln 2>/dev/null | grep ":$proxy_port " &> /dev/null; then
        log "✓ Proxy service listening on port $proxy_port"
        add_result "PROXY_PORT" "PASS" "Proxy service accessible"
        
        # Test proxy connection
        if curl -s --proxy "http://localhost:$proxy_port" --connect-timeout 5 http://httpbin.org/ip &> /dev/null; then
            log "✓ Proxy functionality confirmed"
            add_result "PROXY_FUNCTION" "PASS" "Proxy routing working"
        else
            warn "Proxy not responding to requests"
            add_result "PROXY_FUNCTION" "WARN" "Proxy routing issues"
        fi
    else
        info "No proxy service listening on standard port $proxy_port"
        add_result "PROXY_PORT" "INFO" "Standard proxy port not in use"
    fi
}

# Validate TLS/TCP configuration
validate_tls_tcp_config() {
    log "Validating TLS/TCP configuration..."
    
    # Test TLS handshake capabilities
    local test_host="httpbin.org"
    local test_port="443"
    
    if command -v openssl &> /dev/null; then
        log "Testing TLS handshake with $test_host..."
        
        # Create temporary file for handshake analysis
        local handshake_file="/tmp/tls_handshake_$$.txt"
        
        if timeout 10 openssl s_client -connect "$test_host:$test_port" -tls1_2 </dev/null > "$handshake_file" 2>&1; then
            log "✓ TLS 1.2 handshake successful"
            add_result "TLS_HANDSHAKE" "PASS" "TLS connectivity confirmed"
            
            # Analyze handshake details
            if grep -q "Cipher:" "$handshake_file"; then
                local cipher=$(grep "Cipher:" "$handshake_file" | head -1)
                info "  $cipher"
            fi
            
            if grep -q "Protocol:" "$handshake_file"; then
                local protocol=$(grep "Protocol:" "$handshake_file" | head -1)
                info "  $protocol"
            fi
            
            # Check for certificate validation
            if grep -q "Verification:" "$handshake_file"; then
                local verification=$(grep "Verification:" "$handshake_file" | head -1)
                info "  $verification"
            fi
            
        else
            warn "TLS handshake failed with $test_host"
            add_result "TLS_HANDSHAKE" "WARN" "TLS connectivity issues"
        fi
        
        # Cleanup
        rm -f "$handshake_file"
    else
        warn "OpenSSL not available for TLS testing"
        add_result "OPENSSL_AVAILABLE" "WARN" "TLS testing tools missing"
    fi
    
    # Check for TLS configuration files
    local tls_configs=$(find "$REPO_PATH" -name "*tls*" -o -name "*ssl*" -o -name "*.crt" -o -name "*.key" -o -name "*.pem" 2>/dev/null || true)
    if [ -n "$tls_configs" ]; then
        log "✓ TLS/SSL configuration files found"
        add_result "TLS_CONFIG" "PASS" "TLS configuration available"
        
        # Count different types of files
        local cert_count=$(echo "$tls_configs" | grep -c "\.crt$\|\.pem$" || echo "0")
        local key_count=$(echo "$tls_configs" | grep -c "\.key$" || echo "0")
        
        info "  Certificates: $cert_count, Keys: $key_count"
    else
        info "No TLS/SSL configuration files found"
        add_result "TLS_CONFIG" "INFO" "No custom TLS configuration"
    fi
}

# Validate application patch pipeline
validate_patch_pipeline() {
    log "Validating application patch pipeline..."
    
    # Check for patch-related scripts
    local patch_scripts=$(find "$REPO_PATH" -name "*patch*" -name "*.sh" -o -name "*fetch*" -name "*.sh" 2>/dev/null || true)
    if [ -n "$patch_scripts" ]; then
        log "✓ Patch pipeline scripts found"
        add_result "PATCH_SCRIPTS" "PASS" "Patch automation available"
        
        for script in $patch_scripts; do
            if [ -f "$script" ]; then
                info "Analyzing: $script"
                
                # Check script permissions
                if [ -x "$script" ]; then
                    log "  ✓ Script is executable"
                else
                    warn "  ⚠ Script not executable"
                fi
                
                # Check for key patch functions
                if grep -q "fetch.*apk\|download.*apk\|patch.*apk" "$script"; then
                    log "  ✓ APK processing functions found"
                else
                    info "  ℹ No obvious APK processing functions"
                fi
                
                # Check for error handling
                if grep -q "set -e\|trap\|error" "$script"; then
                    log "  ✓ Error handling implemented"
                else
                    warn "  ⚠ Limited error handling"
                fi
            fi
        done
    else
        warn "No patch pipeline scripts found"
        add_result "PATCH_SCRIPTS" "WARN" "Patch automation not found"
    fi
    
    # Check for CI/CD integration
    local ci_configs=$(find "$REPO_PATH" -path "*/.github/workflows/*" -o -path "*/ci/*" -o -name ".gitlab-ci.yml" -o -name "Jenkinsfile" 2>/dev/null || true)
    if [ -n "$ci_configs" ]; then
        log "✓ CI/CD configuration found"
        add_result "CI_CD_CONFIG" "PASS" "Automation pipeline configured"
        
        for ci_config in $ci_configs; do
            if [ -f "$ci_config" ]; then
                info "Analyzing: $ci_config"
                
                # Check for patch-related jobs
                if grep -qi "patch\|apk\|build" "$ci_config"; then
                    log "  ✓ Build/patch jobs configured"
                else
                    info "  ℹ No obvious build/patch jobs"
                fi
            fi
        done
    else
        info "No CI/CD configuration found"
        add_result "CI_CD_CONFIG" "INFO" "No automation pipeline"
    fi
    
    # Check for APK hosting/serving capability
    if curl -I "http://localhost/app-patched.apk" 2>/dev/null | grep -q "200\|404"; then
        if curl -I "http://localhost/app-patched.apk" 2>/dev/null | grep -q "200"; then
            log "✓ APK hosting service accessible (file available)"
            add_result "APK_HOSTING" "PASS" "Patched APK served successfully"
        else
            info "APK hosting service accessible (no file currently)"
            add_result "APK_HOSTING" "INFO" "APK hosting ready, no file present"
        fi
    else
        info "No APK hosting service detected on localhost"
        add_result "APK_HOSTING" "INFO" "No local APK hosting service"
    fi
    
    # Check for build artifacts directory
    local build_dirs=$(find "$REPO_PATH" -type d -name "*build*" -o -name "*dist*" -o -name "*output*" 2>/dev/null || true)
    if [ -n "$build_dirs" ]; then
        log "✓ Build output directories found"
        add_result "BUILD_OUTPUT" "PASS" "Build artifact storage available"
        
        # Check for APK files
        local apk_count=$(find $build_dirs -name "*.apk" 2>/dev/null | wc -l || echo "0")
        info "  APK files found: $apk_count"
    else
        info "No build output directories found"
        add_result "BUILD_OUTPUT" "INFO" "No build artifact directories"
    fi
}

# Test network security tools
test_security_tools() {
    log "Testing network security tools..."
    
    # Check for packet capture capabilities
    if command -v tcpdump &> /dev/null; then
        log "✓ tcpdump available for packet capture"
        add_result "TCPDUMP" "PASS" "Packet capture tool available"
    else
        info "tcpdump not available"
        add_result "TCPDUMP" "INFO" "Packet capture tool missing"
    fi
    
    if command -v tshark &> /dev/null; then
        log "✓ tshark available for packet analysis"
        add_result "TSHARK" "PASS" "Packet analysis tool available"
    else
        info "tshark not available"
        add_result "TSHARK" "INFO" "Packet analysis tool missing"
    fi
    
    # Check for network scanning tools
    if command -v nmap &> /dev/null; then
        log "✓ nmap available for network scanning"
        add_result "NMAP" "PASS" "Network scanning tool available"
    else
        info "nmap not available"
        add_result "NMAP" "INFO" "Network scanning tool missing"
    fi
    
    # Check for JA3 fingerprinting tool
    if command -v ja3er &> /dev/null; then
        log "✓ ja3er available for TLS fingerprinting"
        add_result "JA3_TOOL" "PASS" "TLS fingerprinting tool available"
    else
        info "ja3er not available (TLS fingerprinting limited)"
        add_result "JA3_TOOL" "INFO" "TLS fingerprinting tool missing"
    fi
}

# Generate validation report
generate_report() {
    log "Generating network validation report..."
    
    local report_file="${SCRIPT_DIR}/logs/network-validation-report-$(date +%Y%m%d-%H%M%S).txt"
    
    cat > "$report_file" << EOF
# Network and Patch Validation Report
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

## Network Infrastructure Status

$(if [ "$pass_count" -gt 8 ]; then
    echo "✅ READY: Network infrastructure appears well-configured for testing"
elif [ "$pass_count" -gt 4 ]; then
    echo "⚠️ PARTIAL: Some network components configured, review warnings"
else
    echo "❌ LIMITED: Limited network testing capabilities detected"
fi)

## Recommendations

EOF

    # Add recommendations based on results
    if [ "$fail_count" -gt 0 ]; then
        echo "- Address FAILED validations before network testing" >> "$report_file"
    fi
    
    if [ "$warn_count" -gt 0 ]; then
        echo "- Review WARNING items for optimal network testing setup" >> "$report_file"
    fi
    
    echo "- Ensure all network testing is conducted ethically and legally" >> "$report_file"
    echo "- Use proxy services only for legitimate testing purposes" >> "$report_file"
    echo "- Maintain proper logging and audit trails for compliance" >> "$report_file"
    echo "- Regular validation recommended for network infrastructure" >> "$report_file"
    
    log "Report generated: $report_file"
    
    # Display summary
    echo ""
    log "=== NETWORK VALIDATION SUMMARY ==="
    log "✅ PASS: $pass_count"
    log "⚠️  WARN: $warn_count"
    log "❌ FAIL: $fail_count"
    log "ℹ️  INFO: $info_count"
    echo ""
    
    if [ "$fail_count" -eq 0 ]; then
        log "🎉 Network validation completed successfully!"
        return 0
    else
        warn "⚠️ Some network validations failed. Review the report for details."
        return 1
    fi
}

# Main execution function
main() {
    log "=== Network and Patch Validation Framework ==="
    log "Starting network infrastructure validation..."
    log "Repository path: $REPO_PATH"
    
    # Run validation phases
    local overall_success=true
    
    if ! check_prerequisites; then
        warn "Some prerequisites missing, continuing with limited validation"
    fi
    
    # Proxy Configuration Validation
    log "Phase 1: Proxy Configuration Validation"
    if ! validate_proxy_config; then
        overall_success=false
    fi
    
    # Network Infrastructure Validation
    log "Phase 2: Network Infrastructure Validation"
    if ! validate_network_infrastructure; then
        overall_success=false
    fi
    
    # TLS/TCP Configuration Validation
    log "Phase 3: TLS/TCP Configuration Validation"
    if ! validate_tls_tcp_config; then
        overall_success=false
    fi
    
    # Application Patch Pipeline Validation
    log "Phase 4: Application Patch Pipeline Validation"
    if ! validate_patch_pipeline; then
        overall_success=false
    fi
    
    # Security Tools Testing
    log "Phase 5: Security Tools Testing"
    if ! test_security_tools; then
        overall_success=false
    fi
    
    # Generate final report
    log "Phase 6: Report Generation"
    if ! generate_report; then
        overall_success=false
    fi
    
    if [ "$overall_success" = true ]; then
        log "🏆 All network validations completed successfully!"
        exit 0
    else
        warn "⚠️ Some network validations had issues. Check the report for details."
        exit 1
    fi
}

# Help function
show_help() {
    cat << EOF
Network and Patch Validation Framework

Usage: $0 [REPO_PATH]

Arguments:
  REPO_PATH    Path to project repository (default: current directory)

Examples:
  $0                          # Validate using current directory
  $0 /path/to/project         # Validate using specific repository path
  $0 --help                   # Show this help message

This script validates:
- Proxy configuration and rotation setup
- Network infrastructure and connectivity
- TLS/TCP configuration and capabilities
- Application patch pipeline automation
- Network security testing tools

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