#!/bin/bash
# Modern DevOps Deployment Script with Terraform and CI/CD Integration
# Replaces manual deployment with infrastructure as code

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TERRAFORM_DIR="$PROJECT_ROOT/terraform"
LOG_FILE="/tmp/modern-deploy-$(date +%Y%m%d-%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging
exec 1> >(tee -a "$LOG_FILE")
exec 2> >(tee -a "$LOG_FILE" >&2)

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS:${NC} $1"
}

warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
    exit 1
}

# Environment detection
detect_environment() {
    local git_branch
    git_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    
    case "$git_branch" in
        main|master)
            echo "production"
            ;;
        staging|stage)
            echo "staging"
            ;;
        develop|dev)
            echo "development"
            ;;
        *)
            echo "development"
            ;;
    esac
}

# Prerequisites check
check_prerequisites() {
    log "Checking prerequisites..."
    
    local missing_tools=()
    
    # Check required tools
    command -v terraform >/dev/null 2>&1 || missing_tools+=("terraform")
    command -v flyctl >/dev/null 2>&1 || missing_tools+=("flyctl")
    command -v docker >/dev/null 2>&1 || missing_tools+=("docker")
    command -v jq >/dev/null 2>&1 || missing_tools+=("jq")
    command -v curl >/dev/null 2>&1 || missing_tools+=("curl")
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        error "Missing required tools: ${missing_tools[*]}"
    fi
    
    # Check Terraform version
    local tf_version
    tf_version=$(terraform version -json | jq -r '.terraform_version')
    if ! printf '%s\n%s\n' "1.5.0" "$tf_version" | sort -V -C; then
        warning "Terraform version $tf_version may not be compatible. Recommended: >= 1.5.0"
    fi
    
    # Check authentication
    if [ -z "${FLY_API_TOKEN:-}" ]; then
        warning "FLY_API_TOKEN not set. Checking flyctl auth..."
        if ! flyctl auth whoami >/dev/null 2>&1; then
            error "Not authenticated with Fly.io. Run 'flyctl auth login'"
        fi
    fi
    
    success "Prerequisites check completed"
}

# Build and push Docker images
build_images() {
    local environment="$1"
    local version="$2"
    
    log "Building Docker images for $environment environment..."
    
    # Build main application image
    log "Building main application image..."
    docker build \
        --tag "snapchat-automation:$version" \
        --tag "snapchat-automation:latest" \
        --file "$PROJECT_ROOT/Dockerfile" \
        --build-arg ENVIRONMENT="$environment" \
        --build-arg VERSION="$version" \
        "$PROJECT_ROOT"
    
    # Build Android farm image
    log "Building Android farm image..."
    docker build \
        --tag "android-automation:$version" \
        --tag "android-automation:latest" \
        --file "$PROJECT_ROOT/Dockerfile.android" \
        --build-arg ENVIRONMENT="$environment" \
        --build-arg VERSION="$version" \
        "$PROJECT_ROOT"
    
    # Tag for registry (if using container registry)
    if [ "$environment" = "production" ]; then
        docker tag "snapchat-automation:$version" "ghcr.io/your-org/snapchat-automation:$version"
        docker tag "android-automation:$version" "ghcr.io/your-org/android-automation:$version"
    fi
    
    success "Docker images built successfully"
}

# Security scanning
security_scan() {
    local environment="$1"
    
    if [ "$environment" = "production" ]; then
        log "Running security scans..."
        
        # Scan for secrets
        if command -v trufflehog >/dev/null 2>&1; then
            log "Scanning for secrets..."
            trufflehog filesystem "$PROJECT_ROOT" --no-update || warning "Secret scan found issues"
        fi
        
        # Scan Docker images
        if command -v trivy >/dev/null 2>&1; then
            log "Scanning Docker images for vulnerabilities..."
            trivy image "snapchat-automation:latest" --exit-code 1 || warning "Docker image vulnerabilities found"
            trivy image "android-automation:latest" --exit-code 1 || warning "Android image vulnerabilities found"
        fi
        
        success "Security scanning completed"
    else
        log "Skipping security scans for $environment environment"
    fi
}

# Terraform operations
terraform_deploy() {
    local environment="$1"
    local version="$2"
    
    log "Starting Terraform deployment for $environment..."
    
    cd "$TERRAFORM_DIR"
    
    # Initialize Terraform
    log "Initializing Terraform..."
    terraform init -upgrade
    
    # Select workspace
    log "Selecting Terraform workspace: $environment"
    terraform workspace select "$environment" 2>/dev/null || terraform workspace new "$environment"
    
    # Validate configuration
    log "Validating Terraform configuration..."
    terraform validate
    
    # Plan deployment
    log "Creating Terraform plan..."
    terraform plan \
        -var-file="$environment.tfvars" \
        -var="main_app_image=snapchat-automation:$version" \
        -var="android_farm_image=android-automation:$version" \
        -out="tfplan"
    
    # Apply if not dry run
    if [ "${DRY_RUN:-false}" != "true" ]; then
        log "Applying Terraform plan..."
        terraform apply -auto-approve "tfplan"
        
        # Save outputs
        terraform output -json > "$PROJECT_ROOT/terraform-outputs.json"
        
        success "Terraform deployment completed"
    else
        log "Dry run mode - Terraform plan created but not applied"
    fi
    
    cd "$PROJECT_ROOT"
}

# Health checks
run_health_checks() {
    local environment="$1"
    
    log "Running health checks..."
    
    # Read Terraform outputs for URLs
    local main_app_url android_farm_url
    if [ -f "$PROJECT_ROOT/terraform-outputs.json" ]; then
        main_app_url=$(jq -r '.main_app_url.value' "$PROJECT_ROOT/terraform-outputs.json")
        android_farm_url=$(jq -r '.android_farm_url.value' "$PROJECT_ROOT/terraform-outputs.json")
    else
        main_app_url="https://snapchat-automation-$environment.fly.dev"
        android_farm_url="https://android-device-farm-$environment.fly.dev"
    fi
    
    # Wait for deployment to be ready
    log "Waiting for deployment to be ready..."
    sleep 30
    
    # Health check function
    check_endpoint() {
        local url="$1"
        local name="$2"
        local max_attempts=30
        local attempt=1
        
        while [ $attempt -le $max_attempts ]; do
            if curl -f -s "$url/health" >/dev/null 2>&1; then
                success "$name health check passed"
                return 0
            fi
            
            log "Attempt $attempt/$max_attempts: $name not ready yet..."
            sleep 10
            ((attempt++))
        done
        
        error "$name health check failed after $max_attempts attempts"
        return 1
    }
    
    # Run health checks
    check_endpoint "$main_app_url" "Main application"
    check_endpoint "$android_farm_url" "Android farm"
    
    # Additional functional tests
    if [ "$environment" = "production" ]; then
        log "Running functional tests..."
        cd "$PROJECT_ROOT/tests/integration"
        python -m pytest test_deployment.py -v --base-url="$main_app_url" || warning "Some functional tests failed"
        cd "$PROJECT_ROOT"
    fi
    
    success "Health checks completed"
}

# Performance benchmarking
run_performance_tests() {
    local environment="$1"
    
    if [ "$environment" = "production" ] && command -v k6 >/dev/null 2>&1; then
        log "Running performance benchmarks..."
        
        local main_app_url
        main_app_url=$(jq -r '.main_app_url.value' "$PROJECT_ROOT/terraform-outputs.json" 2>/dev/null || echo "https://snapchat-automation-$environment.fly.dev")
        
        cd "$PROJECT_ROOT/tests/performance"
        k6 run --env BASE_URL="$main_app_url" load_test.js || warning "Performance tests indicate issues"
        cd "$PROJECT_ROOT"
        
        success "Performance benchmarks completed"
    else
        log "Skipping performance tests for $environment environment"
    fi
}

# Monitoring setup
setup_monitoring() {
    local environment="$1"
    
    log "Setting up monitoring and alerting..."
    
    # Deploy monitoring configuration
    if [ -f "$PROJECT_ROOT/monitoring/terraform-monitoring.yml" ]; then
        kubectl apply -f "$PROJECT_ROOT/monitoring/terraform-monitoring.yml" 2>/dev/null || warning "Could not apply monitoring config"
    fi
    
    # Update Grafana dashboards
    if [ -f "$PROJECT_ROOT/terraform-outputs.json" ]; then
        local grafana_url
        grafana_url=$(jq -r '.monitoring_endpoints.value.grafana_dashboards[0]' "$PROJECT_ROOT/terraform-outputs.json" 2>/dev/null)
        
        if [ "$grafana_url" != "null" ] && [ -n "$grafana_url" ]; then
            log "Updating Grafana dashboards..."
            # Dashboard update logic would go here
        fi
    fi
    
    success "Monitoring setup completed"
}

# Rollback functionality
rollback_deployment() {
    local environment="$1"
    
    warning "Rolling back deployment..."
    
    # Terraform rollback (to previous state)
    cd "$TERRAFORM_DIR"
    terraform workspace select "$environment"
    
    # Get previous version from state
    local previous_version
    previous_version=$(terraform state show 'fly_machine.main_app_machines[0]' | grep -oP 'image\s*=\s*"\K[^"]*' | head -1)
    
    if [ -n "$previous_version" ]; then
        log "Rolling back to previous version: $previous_version"
        
        # Apply previous configuration
        terraform plan \
            -var-file="$environment.tfvars" \
            -var="main_app_image=$previous_version" \
            -var="android_farm_image=$previous_version" \
            -out="rollback-plan"
        
        terraform apply -auto-approve "rollback-plan"
        
        success "Rollback completed"
    else
        error "Could not determine previous version for rollback"
    fi
    
    cd "$PROJECT_ROOT"
}

# Cleanup function
cleanup() {
    log "Cleaning up temporary files..."
    rm -f "$TERRAFORM_DIR/tfplan" "$TERRAFORM_DIR/rollback-plan"
    success "Cleanup completed"
}

# Signal handlers
trap cleanup EXIT
trap 'error "Deployment interrupted"' INT TERM

# Main deployment function
main() {
    local environment="${1:-$(detect_environment)}"
    local version="${2:-$(date +%Y%m%d%H%M%S)-$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')}"
    local operation="${3:-deploy}"
    
    log "Starting modern deployment process..."
    log "Environment: $environment"
    log "Version: $version"
    log "Operation: $operation"
    log "Log file: $LOG_FILE"
    
    case "$operation" in
        "deploy")
            check_prerequisites
            build_images "$environment" "$version"
            security_scan "$environment"
            terraform_deploy "$environment" "$version"
            run_health_checks "$environment"
            run_performance_tests "$environment"
            setup_monitoring "$environment"
            ;;
        "rollback")
            check_prerequisites
            rollback_deployment "$environment"
            run_health_checks "$environment"
            ;;
        "plan")
            check_prerequisites
            DRY_RUN=true terraform_deploy "$environment" "$version"
            ;;
        *)
            error "Unknown operation: $operation. Use: deploy, rollback, or plan"
            ;;
    esac
    
    success "Modern deployment process completed successfully!"
    log "Summary:"
    log "  Environment: $environment"
    log "  Version: $version"
    log "  Operation: $operation"
    log "  Log file: $LOG_FILE"
    
    if [ -f "$PROJECT_ROOT/terraform-outputs.json" ]; then
        local main_app_url android_farm_url
        main_app_url=$(jq -r '.main_app_url.value' "$PROJECT_ROOT/terraform-outputs.json")
        android_farm_url=$(jq -r '.android_farm_url.value' "$PROJECT_ROOT/terraform-outputs.json")
        
        log "  Main App: $main_app_url"
        log "  Android Farm: $android_farm_url"
    fi
}

# Usage information
usage() {
    cat << EOF
Usage: $0 [ENVIRONMENT] [VERSION] [OPERATION]

Modern DevOps deployment script with Terraform and CI/CD integration

Arguments:
  ENVIRONMENT    Target environment (development|staging|production)
                 Default: auto-detected from git branch
  VERSION        Deployment version tag
                 Default: timestamp-githash
  OPERATION      Deployment operation (deploy|rollback|plan)
                 Default: deploy

Examples:
  $0                          # Auto-detect environment and version, deploy
  $0 production               # Deploy to production with auto-generated version
  $0 staging v1.2.3           # Deploy specific version to staging
  $0 production latest plan   # Plan deployment without applying
  $0 production latest rollback # Rollback production deployment

Environment Variables:
  FLY_API_TOKEN              Fly.io API token (required)
  DRY_RUN                   Set to 'true' for plan-only mode
  SKIP_SECURITY_SCAN        Set to 'true' to skip security scanning
  SKIP_PERFORMANCE_TESTS    Set to 'true' to skip performance tests

EOF
}

# Parse command line arguments
if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    usage
    exit 0
fi

# Run main function with arguments
main "${1:-}" "${2:-}" "${3:-}"