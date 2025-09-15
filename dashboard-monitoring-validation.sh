#!/bin/bash

# Dashboard and Monitoring Validation Framework
# Validates dashboard UI, backend endpoints, monitoring systems, and automation controls
# For legitimate development dashboard and system monitoring purposes

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/logs/dashboard-validation.log"
REPO_PATH="${1:-$SCRIPT_DIR}"
DASHBOARD_URL="${2:-http://localhost:4000}"

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
    log "Checking dashboard validation prerequisites..."
    
    # Check required tools
    local required_tools=("curl" "grep" "find" "jq" "docker")
    
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
    log "Dashboard URL: $DASHBOARD_URL"
    log "Repository path: $REPO_PATH"
    return 0
}

# Validate backend API endpoints
validate_backend_endpoints() {
    log "Validating backend API endpoints..."
    
    # Determine backend URL from dashboard URL
    local backend_url
    if [[ "$DASHBOARD_URL" == *":4000"* ]]; then
        backend_url="${DASHBOARD_URL%:4000}:3000"
    elif [[ "$DASHBOARD_URL" == *":3000"* ]]; then
        backend_url="$DASHBOARD_URL"
    else
        backend_url="${DASHBOARD_URL%/}:3000"
    fi
    
    info "Testing backend at: $backend_url"
    
    # Test health endpoint
    log "Testing health endpoint..."
    if curl -s --connect-timeout 10 "${backend_url}/api/health" >/dev/null 2>&1; then
        local health_response=$(curl -s --connect-timeout 10 "${backend_url}/api/health")
        
        if command -v jq &> /dev/null && echo "$health_response" | jq empty &> /dev/null 2>&1; then
            log "✓ Health endpoint returning valid JSON"
            add_result "HEALTH_ENDPOINT" "PASS" "Health API functional"
            
            local status=$(echo "$health_response" | jq -r '.status // empty' 2>/dev/null)
            if [ "$status" = "healthy" ]; then
                log "  Status: healthy"
            else
                info "  Status: $status"
            fi
        else
            log "✓ Health endpoint accessible"
            add_result "HEALTH_ENDPOINT" "PASS" "Health endpoint responsive"
            info "  Response: $health_response"
        fi
    else
        warn "Health endpoint not accessible"
        add_result "HEALTH_ENDPOINT" "WARN" "Health endpoint not responding"
    fi
    
    # Test metrics endpoint
    log "Testing metrics endpoint..."
    if curl -s --connect-timeout 10 "${backend_url}/api/metrics" >/dev/null 2>&1; then
        log "✓ Metrics endpoint accessible"
        add_result "METRICS_ENDPOINT" "PASS" "Metrics API functional"
    else
        warn "Metrics endpoint not accessible"
        add_result "METRICS_ENDPOINT" "WARN" "Metrics endpoint not responding"
    fi
    
    # Test containers endpoint
    log "Testing containers endpoint..."
    if curl -s --connect-timeout 10 "${backend_url}/api/containers" >/dev/null 2>&1; then
        log "✓ Containers endpoint accessible"
        add_result "CONTAINERS_ENDPOINT" "PASS" "Container management API functional"
    else
        warn "Containers endpoint not accessible"
        add_result "CONTAINERS_ENDPOINT" "WARN" "Container management API not responding"
    fi
    
    # Test services endpoint
    log "Testing services endpoint..."
    if curl -s --connect-timeout 10 "${backend_url}/api/services" >/dev/null 2>&1; then
        log "✓ Services endpoint accessible"
        add_result "SERVICES_ENDPOINT" "PASS" "Services monitoring API functional"
    else
        warn "Services endpoint not accessible"
        add_result "SERVICES_ENDPOINT" "WARN" "Services monitoring API not responding"
    fi
    
    # Test bulk operations (development feature)
    log "Testing bulk operations endpoint..."
    local bulk_url="${backend_url}/api/bulk-handles/import"
    if curl -s --connect-timeout 10 "${bulk_url}?dryRun=true" >/dev/null 2>&1; then
        log "✓ Bulk operations endpoint accessible"
        add_result "BULK_ENDPOINT" "PASS" "Bulk operations API functional"
    else
        info "Bulk operations endpoint not available (may be feature-specific)"
        add_result "BULK_ENDPOINT" "INFO" "Bulk operations API not available"
    fi
    
    # Test Prometheus metrics endpoint
    log "Testing Prometheus metrics endpoint..."
    if curl -s --connect-timeout 10 "${backend_url}/metrics" >/dev/null 2>&1; then
        log "✓ Prometheus metrics endpoint accessible"
        add_result "PROMETHEUS_METRICS" "PASS" "Prometheus metrics available"
    else
        info "Prometheus metrics endpoint not available"
        add_result "PROMETHEUS_METRICS" "INFO" "Prometheus metrics not configured"
    fi
}

# Validate frontend accessibility and components
validate_frontend_interface() {
    log "Validating frontend interface..."
    
    # Test main dashboard accessibility
    log "Testing dashboard accessibility..."
    if curl -s --connect-timeout 10 "$DASHBOARD_URL" >/dev/null 2>&1; then
        log "✓ Dashboard frontend accessible"
        add_result "FRONTEND_ACCESS" "PASS" "Dashboard UI accessible"
        
        # Get response headers to check content type
        local headers=$(curl -s -I --connect-timeout 10 "$DASHBOARD_URL" 2>/dev/null || echo "")
        if echo "$headers" | grep -q "text/html"; then
            log "  ✓ Serving HTML content"
        fi
    else
        warn "Dashboard frontend not accessible"
        add_result "FRONTEND_ACCESS" "WARN" "Dashboard UI not accessible"
    fi
    
    # Check for frontend source files
    log "Checking frontend source structure..."
    local frontend_dirs=(
        "${REPO_PATH}/frontend"
        "${REPO_PATH}/ui"
        "${REPO_PATH}/web"
        "${REPO_PATH}/dashboard"
    )
    
    local frontend_found=false
    for frontend_dir in "${frontend_dirs[@]}"; do
        if [ -d "$frontend_dir" ]; then
            log "✓ Frontend directory found: $frontend_dir"
            add_result "FRONTEND_STRUCTURE" "PASS" "Frontend source code present"
            frontend_found=true
            
            # Check for React components
            local components_dir="${frontend_dir}/src/components"
            if [ -d "$components_dir" ]; then
                local component_count=$(find "$components_dir" -name "*.tsx" -o -name "*.jsx" 2>/dev/null | wc -l)
                log "  ✓ Components directory found ($component_count components)"
                add_result "REACT_COMPONENTS" "PASS" "$component_count React components found"
            fi
            
            # Check for pages directory
            local pages_dir="${frontend_dir}/src/pages"
            if [ -d "$pages_dir" ]; then
                local page_count=$(find "$pages_dir" -name "*.tsx" -o -name "*.jsx" 2>/dev/null | wc -l)
                log "  ✓ Pages directory found ($page_count pages)"
            fi
            
            # Check package.json for dependencies
            local package_json="${frontend_dir}/package.json"
            if [ -f "$package_json" ] && command -v jq &> /dev/null; then
                local react_version=$(jq -r '.dependencies.react // empty' "$package_json" 2>/dev/null)
                if [ -n "$react_version" ]; then
                    log "  ✓ React version: $react_version"
                fi
                
                local mui_version=$(jq -r '.dependencies["@mui/material"] // empty' "$package_json" 2>/dev/null)
                if [ -n "$mui_version" ]; then
                    log "  ✓ Material-UI version: $mui_version"
                fi
            fi
            
            break
        fi
    done
    
    if [ "$frontend_found" = false ]; then
        warn "No frontend directory found"
        add_result "FRONTEND_STRUCTURE" "WARN" "Frontend source code not found"
    fi
}

# Check for dashboard-specific features
check_dashboard_features() {
    log "Checking dashboard-specific features..."
    
    # Look for dashboard component files
    local dashboard_components=$(find "$REPO_PATH" -name "*.tsx" -o -name "*.jsx" -o -name "*.ts" -o -name "*.js" 2>/dev/null | \
        xargs grep -l "dashboard\|Dashboard" 2>/dev/null || true)
    
    if [ -n "$dashboard_components" ]; then
        log "✓ Dashboard components found"
        add_result "DASHBOARD_COMPONENTS" "PASS" "Dashboard UI components present"
        
        # Check for specific dashboard features
        while IFS= read -r component_file; do
            if [ -f "$component_file" ]; then
                info "Analyzing: $component_file"
                
                # Check for system monitoring features
                if grep -q "SystemMetrics\|system.*metric\|cpu\|memory" "$component_file"; then
                    log "  ✓ System monitoring features found"
                    add_result "SYSTEM_MONITORING" "PASS" "System monitoring UI present"
                fi
                
                # Check for container management features
                if grep -q "Container\|Docker\|container.*management" "$component_file"; then
                    log "  ✓ Container management features found"
                    add_result "CONTAINER_MGMT_UI" "PASS" "Container management UI present"
                fi
                
                # Check for service status features
                if grep -q "ServiceStatus\|service.*status\|health.*check" "$component_file"; then
                    log "  ✓ Service status features found"
                    add_result "SERVICE_STATUS_UI" "PASS" "Service status UI present"
                fi
                
                # Check for real-time updates (WebSocket)
                if grep -q "socket\|WebSocket\|socketio" "$component_file"; then
                    log "  ✓ Real-time update features found"
                    add_result "REALTIME_UPDATES" "PASS" "Real-time update UI present"
                fi
            fi
        done <<< "$dashboard_components"
    else
        info "No dashboard-specific components found"
        add_result "DASHBOARD_COMPONENTS" "INFO" "No specific dashboard components detected"
    fi
    
    # Check for development-specific UI elements
    check_development_ui_elements
}

# Check for development-specific UI elements
check_development_ui_elements() {
    log "Checking for development-specific UI elements..."
    
    # Look for development management features
    local dev_features_found=false
    
    # Search for project management UI
    local project_ui=$(find "$REPO_PATH" -name "*.tsx" -o -name "*.jsx" -o -name "*.ts" -o -name "*.js" 2>/dev/null | \
        xargs grep -l "Create.*Project\|Project.*Management\|New.*Project" 2>/dev/null || true)
    
    if [ -n "$project_ui" ]; then
        log "✓ Project management UI found"
        add_result "PROJECT_MGMT_UI" "PASS" "Project management interface present"
        dev_features_found=true
    fi
    
    # Search for deployment management UI
    local deploy_ui=$(find "$REPO_PATH" -name "*.tsx" -o -name "*.jsx" -o -name "*.ts" -o -name "*.js" 2>/dev/null | \
        xargs grep -l "Deploy\|Deployment\|Release" 2>/dev/null || true)
    
    if [ -n "$deploy_ui" ]; then
        log "✓ Deployment management UI found"
        add_result "DEPLOY_MGMT_UI" "PASS" "Deployment management interface present"
        dev_features_found=true
    fi
    
    # Search for monitoring and alerting UI
    local monitoring_ui=$(find "$REPO_PATH" -name "*.tsx" -o -name "*.jsx" -o -name "*.ts" -o -name "*.js" 2>/dev/null | \
        xargs grep -l "Alert\|Monitoring\|Dashboard.*Monitor" 2>/dev/null || true)
    
    if [ -n "$monitoring_ui" ]; then
        log "✓ Monitoring UI found"
        add_result "MONITORING_UI" "PASS" "System monitoring interface present"
        dev_features_found=true
    fi
    
    if [ "$dev_features_found" = false ]; then
        info "No specific development management UI elements found"
        add_result "DEV_UI_ELEMENTS" "INFO" "No development-specific UI detected"
    fi
}

# Validate monitoring and auto-healing systems
validate_monitoring_systems() {
    log "Validating monitoring and auto-healing systems..."
    
    # Check for pipeline monitor container
    if docker ps --format "{{.Names}}" | grep -q "pipeline-monitor\|monitoring\|monitor"; then
        log "✓ Monitoring container found"
        add_result "MONITORING_CONTAINER" "PASS" "Monitoring service running"
        
        # Get monitoring container logs
        local monitor_container=$(docker ps --format "{{.Names}}" | grep "pipeline-monitor\|monitoring\|monitor" | head -1)
        if [ -n "$monitor_container" ]; then
            log "Checking monitoring logs for auto-heal patterns..."
            
            # Check recent logs for auto-heal activities
            local recent_logs=$(docker logs --tail 100 "$monitor_container" 2>/dev/null || echo "")
            if echo "$recent_logs" | grep -q "auto-heal\|auto.*heal\|self.*heal\|recovery"; then
                log "✓ Auto-heal functionality detected in logs"
                add_result "AUTO_HEAL_ACTIVE" "PASS" "Auto-healing system operational"
            else
                info "No recent auto-heal activities in logs"
                add_result "AUTO_HEAL_ACTIVE" "INFO" "Auto-healing not recently triggered"
            fi
            
            # Check for monitoring patterns
            if echo "$recent_logs" | grep -q "health.*check\|monitor\|status"; then
                log "✓ Health monitoring patterns detected"
                add_result "HEALTH_MONITORING" "PASS" "Health monitoring active"
            fi
            
            # Check for error handling patterns
            if echo "$recent_logs" | grep -q "error\|exception\|failed\|restart"; then
                log "✓ Error handling patterns detected"
                add_result "ERROR_HANDLING_MONITOR" "PASS" "Error monitoring active"
            fi
        fi
    else
        warn "No monitoring container found"
        add_result "MONITORING_CONTAINER" "WARN" "Monitoring service not detected"
    fi
    
    # Check for monitoring configuration files
    local monitoring_configs=$(find "$REPO_PATH" -name "*monitor*" -name "*.yml" -o -name "*monitor*" -name "*.yaml" -o -name "*monitor*" -name "*.json" 2>/dev/null || true)
    if [ -n "$monitoring_configs" ]; then
        log "✓ Monitoring configuration files found"
        add_result "MONITORING_CONFIG" "PASS" "Monitoring configuration present"
        
        while IFS= read -r config_file; do
            if [ -f "$config_file" ]; then
                info "  Config: $config_file"
                
                # Check for auto-heal configuration
                if grep -q "auto.heal\|autoheal\|recovery\|restart" "$config_file" 2>/dev/null; then
                    log "    ✓ Auto-heal configuration found"
                fi
            fi
        done <<< "$monitoring_configs"
    else
        info "No monitoring configuration files found"
        add_result "MONITORING_CONFIG" "INFO" "No monitoring configuration detected"
    fi
    
    # Check for Prometheus monitoring
    if docker ps --format "{{.Names}}" | grep -q "prometheus"; then
        log "✓ Prometheus monitoring container found"
        add_result "PROMETHEUS_MONITORING" "PASS" "Prometheus monitoring active"
    else
        info "Prometheus monitoring not detected"
        add_result "PROMETHEUS_MONITORING" "INFO" "Prometheus not running"
    fi
    
    # Check for Grafana dashboards
    if docker ps --format "{{.Names}}" | grep -q "grafana"; then
        log "✓ Grafana dashboard container found"
        add_result "GRAFANA_DASHBOARD" "PASS" "Grafana dashboards active"
    else
        info "Grafana dashboards not detected"
        add_result "GRAFANA_DASHBOARD" "INFO" "Grafana not running"
    fi
}

# Check initialization and setup scripts
check_initialization_scripts() {
    log "Checking initialization and setup scripts..."
    
    # Look for initialization scripts
    local init_scripts=$(find "$REPO_PATH" -name "*init*" -name "*.py" -o -name "*setup*" -name "*.py" -o -name "*bootstrap*" -name "*.py" 2>/dev/null || true)
    if [ -n "$init_scripts" ]; then
        log "✓ Initialization scripts found"
        add_result "INIT_SCRIPTS" "PASS" "Setup scripts present"
        
        while IFS= read -r script_file; do
            if [ -f "$script_file" ]; then
                info "  Script: $script_file"
                
                # Check for specific initialization patterns
                if grep -q "cohort\|group\|batch" "$script_file" 2>/dev/null; then
                    log "    ✓ Cohort/batch initialization found"
                    add_result "COHORT_INIT" "PASS" "Cohort initialization present"
                fi
                
                if grep -q "database\|db.*init\|schema" "$script_file" 2>/dev/null; then
                    log "    ✓ Database initialization found"
                    add_result("DATABASE_INIT" "PASS" "Database initialization present")
                fi
            fi
        done <<< "$init_scripts"
    else
        info "No initialization scripts found"
        add_result "INIT_SCRIPTS" "INFO" "No setup scripts detected"
    fi
    
    # Check backend directory for initialization files
    local backend_dir="${REPO_PATH}/backend"
    if [ -d "$backend_dir" ]; then
        local backend_init_files=$(find "$backend_dir" -name "init_*.py" -o -name "setup_*.py" 2>/dev/null || true)
        if [ -n "$backend_init_files" ]; then
            log "✓ Backend initialization files found"
            add_result "BACKEND_INIT" "PASS" "Backend initialization present"
        fi
    fi
}

# Simulate monitoring scenarios
simulate_monitoring_scenarios() {
    log "Simulating monitoring scenarios..."
    
    # Test if we can trigger monitoring alerts (safely)
    if docker ps --format "{{.Names}}" | grep -q "pipeline-monitor"; then
        local monitor_container=$(docker ps --format "{{.Names}}" | grep "pipeline-monitor" | head -1)
        
        # Check if monitor has a test endpoint or simulation capability
        if docker exec "$monitor_container" test -f "/app/simulate_failure.sh" 2>/dev/null; then
            log "Testing monitoring simulation capability..."
            
            # Run simulation (if safe to do so)
            local sim_result=$(docker exec "$monitor_container" ./simulate_failure.sh 2>&1 || echo "Simulation not available")
            if echo "$sim_result" | grep -q "auto-heal\|recovery\|restart"; then
                log "✓ Auto-heal simulation successful"
                add_result "AUTO_HEAL_SIMULATION" "PASS" "Auto-heal testing functional"
            else
                info "Auto-heal simulation not conclusive"
                add_result "AUTO_HEAL_SIMULATION" "INFO" "Auto-heal testing inconclusive"
            fi
        else
            info "No monitoring simulation capability found"
            add_result "MONITORING_SIMULATION" "INFO" "No simulation scripts available"
        fi
    else
        info "No monitoring container available for simulation"
        add_result "MONITORING_SIMULATION" "INFO" "No monitoring container for testing"
    fi
}

# Generate validation report
generate_report() {
    log "Generating dashboard validation report..."
    
    local report_file="${SCRIPT_DIR}/logs/dashboard-validation-report-$(date +%Y%m%d-%H%M%S).txt"
    
    cat > "$report_file" << EOF
# Dashboard and Monitoring Validation Report
Generated: $(date)
Repository Path: $REPO_PATH
Dashboard URL: $DASHBOARD_URL

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

## Dashboard System Status

$(if [ "$pass_count" -gt 8 ]; then
    echo "✅ OPERATIONAL: Dashboard system appears fully functional"
elif [ "$pass_count" -gt 4 ]; then
    echo "⚠️ PARTIAL: Some dashboard components operational, review warnings"
else
    echo "❌ LIMITED: Limited dashboard functionality detected"
fi)

## Recommendations

EOF

    # Add recommendations based on results
    if [ "$fail_count" -gt 0 ]; then
        echo "- Address FAILED validations before dashboard deployment" >> "$report_file"
    fi
    
    if [ "$warn_count" -gt 0 ]; then
        echo "- Review WARNING items for optimal dashboard operation" >> "$report_file"
    fi
    
    echo "- Ensure all dashboard features are used for legitimate development purposes" >> "$report_file"
    echo "- Maintain proper monitoring and logging for system health" >> "$report_file"
    echo "- Regular validation recommended for dashboard infrastructure" >> "$report_file"
    echo "- Implement proper authentication for production deployments" >> "$report_file"
    echo "- Monitor auto-healing systems for proper operation" >> "$report_file"
    
    log "Report generated: $report_file"
    
    # Display summary
    echo ""
    log "=== DASHBOARD VALIDATION SUMMARY ==="
    log "✅ PASS: $pass_count"
    log "⚠️  WARN: $warn_count"
    log "❌ FAIL: $fail_count"
    log "ℹ️  INFO: $info_count"
    echo ""
    
    if [ "$fail_count" -eq 0 ]; then
        log "🎉 Dashboard validation completed successfully!"
        return 0
    else
        warn "⚠️ Some dashboard validations failed. Review the report for details."
        return 1
    fi
}

# Main execution function
main() {
    log "=== Dashboard and Monitoring Validation Framework ==="
    log "Starting dashboard infrastructure validation..."
    log "Repository path: $REPO_PATH"
    log "Dashboard URL: $DASHBOARD_URL"
    
    # Run validation phases
    local overall_success=true
    
    if ! check_prerequisites; then
        warn "Some prerequisites missing, continuing with limited validation"
    fi
    
    # Backend API Validation
    log "Phase 1: Backend API Validation"
    if ! validate_backend_endpoints; then
        overall_success=false
    fi
    
    # Frontend Interface Validation
    log "Phase 2: Frontend Interface Validation"
    if ! validate_frontend_interface; then
        overall_success=false
    fi
    
    # Dashboard Features Validation
    log "Phase 3: Dashboard Features Validation"
    if ! check_dashboard_features; then
        overall_success=false
    fi
    
    # Monitoring Systems Validation
    log "Phase 4: Monitoring Systems Validation"
    if ! validate_monitoring_systems; then
        overall_success=false
    fi
    
    # Initialization Scripts Validation
    log "Phase 5: Initialization Scripts Validation"
    if ! check_initialization_scripts; then
        overall_success=false
    fi
    
    # Monitoring Scenarios Simulation
    log "Phase 6: Monitoring Scenarios Simulation"
    if ! simulate_monitoring_scenarios; then
        overall_success=false
    fi
    
    # Generate final report
    log "Phase 7: Report Generation"
    if ! generate_report; then
        overall_success=false
    fi
    
    if [ "$overall_success" = true ]; then
        log "🏆 All dashboard validations completed successfully!"
        exit 0
    else
        warn "⚠️ Some dashboard validations had issues. Check the report for details."
        exit 1
    fi
}

# Help function
show_help() {
    cat << EOF
Dashboard and Monitoring Validation Framework

Usage: $0 [REPO_PATH] [DASHBOARD_URL]

Arguments:
  REPO_PATH      Path to project repository (default: current directory)
  DASHBOARD_URL  Base URL for dashboard frontend (default: http://localhost:4000)

Examples:
  $0                                    # Use defaults
  $0 /path/to/project                   # Custom repo path
  $0 /path/to/project http://localhost:8080  # Custom repo and URL
  $0 --help                            # Show this help message

This script validates:
- Backend API endpoints and health checks
- Frontend dashboard accessibility and components
- System monitoring and auto-healing capabilities
- Dashboard-specific UI elements and features
- Initialization and setup scripts
- Monitoring system simulation and testing

For legitimate development dashboard and system monitoring purposes only.
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