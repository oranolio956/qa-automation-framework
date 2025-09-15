#!/bin/bash
# Comprehensive deployment script for Anti-Bot Security Framework
# Supports local, staging, and production environments

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT=${1:-"local"}
NAMESPACE="antibot-security"
DOCKER_REGISTRY=${DOCKER_REGISTRY:-"localhost:5000"}
VERSION=${VERSION:-$(git rev-parse --short HEAD 2>/dev/null || echo "latest")}

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_dependencies() {
    log_info "Checking dependencies..."
    
    local dependencies=("docker" "kubectl" "helm")
    if [ "$ENVIRONMENT" == "local" ]; then
        dependencies+=("docker-compose")
    fi
    
    for cmd in "${dependencies[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "$cmd is not installed"
            exit 1
        fi
    done
    
    log_success "All dependencies are available"
}

validate_environment() {
    case "$ENVIRONMENT" in
        local)
            log_info "Deploying to local environment"
            ;;
        staging)
            log_info "Deploying to staging environment"
            ;;
        production)
            log_info "Deploying to production environment"
            log_warning "Production deployment requires additional confirmation"
            read -p "Are you sure you want to deploy to production? (yes/no): " confirm
            if [ "$confirm" != "yes" ]; then
                log_error "Production deployment cancelled"
                exit 1
            fi
            ;;
        *)
            log_error "Invalid environment: $ENVIRONMENT. Use 'local', 'staging', or 'production'"
            exit 1
            ;;
    esac
}

build_images() {
    log_info "Building Docker images..."
    
    cd "$PROJECT_ROOT"
    
    # Build risk engine
    log_info "Building risk-engine image..."
    docker build -t "$DOCKER_REGISTRY/antibot-security/risk-engine:$VERSION" \
        -f backend/risk-engine/Dockerfile \
        backend/risk-engine/
    
    # Build other services (placeholder for actual implementations)
    log_info "Building additional service images..."
    
    # Tag as latest for local development
    if [ "$ENVIRONMENT" == "local" ]; then
        docker tag "$DOCKER_REGISTRY/antibot-security/risk-engine:$VERSION" \
            "$DOCKER_REGISTRY/antibot-security/risk-engine:latest"
    fi
    
    log_success "Docker images built successfully"
}

push_images() {
    if [ "$ENVIRONMENT" != "local" ]; then
        log_info "Pushing images to registry..."
        
        docker push "$DOCKER_REGISTRY/antibot-security/risk-engine:$VERSION"
        
        log_success "Images pushed to registry"
    else
        log_info "Skipping image push for local environment"
    fi
}

deploy_local() {
    log_info "Deploying to local environment with Docker Compose..."
    
    cd "$PROJECT_ROOT"
    
    # Create necessary directories
    mkdir -p data/redis data/mongodb data/prometheus data/grafana logs
    
    # Set environment variables
    export VERSION
    export DOCKER_REGISTRY
    
    # Deploy with Docker Compose
    docker-compose -f infrastructure/docker-compose.yml down || true
    docker-compose -f infrastructure/docker-compose.yml up -d
    
    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    sleep 30
    
    # Health checks
    check_service_health "http://localhost:8000/api/v1/health" "API Gateway"
    check_service_health "http://localhost:8001/api/v1/health" "Risk Engine"
    check_service_health "http://localhost:9090/-/healthy" "Prometheus"
    check_service_health "http://localhost:3001/api/health" "Grafana"
    
    log_success "Local deployment completed successfully"
    log_info "Services available at:"
    log_info "  - API Gateway: http://localhost:8000"
    log_info "  - Risk Engine: http://localhost:8001"
    log_info "  - Grafana: http://localhost:3001 (admin/grafana123)"
    log_info "  - Prometheus: http://localhost:9090"
}

deploy_kubernetes() {
    log_info "Deploying to Kubernetes environment: $ENVIRONMENT"
    
    # Ensure kubectl is configured for the right cluster
    log_info "Current kubectl context: $(kubectl config current-context)"
    
    if [ "$ENVIRONMENT" == "production" ]; then
        read -p "Confirm kubectl context is correct for production (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            log_error "Deployment cancelled - verify kubectl context"
            exit 1
        fi
    fi
    
    cd "$PROJECT_ROOT/deployment/kubernetes"
    
    # Create namespace and basic resources
    kubectl apply -f antibot-namespace.yaml
    
    # Deploy secrets (in real deployment, use proper secret management)
    create_secrets
    
    # Deploy applications
    kubectl apply -f risk-engine-deployment.yaml
    
    # Wait for deployments
    log_info "Waiting for deployments to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/risk-engine -n "$NAMESPACE"
    
    # Deploy monitoring stack with Helm
    deploy_monitoring_stack
    
    log_success "Kubernetes deployment completed successfully"
    
    # Display service information
    kubectl get services -n "$NAMESPACE"
}

create_secrets() {
    log_info "Creating Kubernetes secrets..."
    
    # MongoDB connection string (in production, use proper secret management)
    kubectl create secret generic mongodb-secret \
        --from-literal=connection-string="mongodb://antibot:antibotpass@mongodb:27017/antibot_security" \
        -n "$NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # API keys and certificates
    kubectl create secret generic api-keys \
        --from-literal=risk-engine-key="$(openssl rand -hex 32)" \
        --from-literal=sms-service-key="$(openssl rand -hex 32)" \
        -n "$NAMESPACE" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    log_success "Secrets created"
}

deploy_monitoring_stack() {
    log_info "Deploying monitoring stack with Helm..."
    
    # Add Helm repositories
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo add grafana https://grafana.github.io/helm-charts
    helm repo update
    
    # Deploy Prometheus
    helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
        --namespace "$NAMESPACE" \
        --values "../monitoring/prometheus/helm-values.yaml" \
        --version "^45.0.0" \
        --timeout 10m \
        --wait
    
    log_success "Monitoring stack deployed"
}

check_service_health() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1
    
    log_info "Checking health of $service_name..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            log_success "$service_name is healthy"
            return 0
        fi
        
        log_info "Attempt $attempt/$max_attempts - $service_name not ready yet..."
        sleep 5
        ((attempt++))
    done
    
    log_error "$service_name failed health check after $max_attempts attempts"
    return 1
}

run_performance_tests() {
    if [ "$ENVIRONMENT" == "local" ]; then
        log_info "Running performance validation tests..."
        
        cd "$PROJECT_ROOT/testing"
        
        # Install test dependencies
        pip install -r performance-test-requirements.txt 2>/dev/null || log_warning "Could not install test dependencies"
        
        # Run quick performance validation
        python performance-validation.py --quick --url "http://localhost:8000"
        
        log_success "Performance tests completed"
    else
        log_info "Skipping performance tests for $ENVIRONMENT environment"
    fi
}

cleanup_failed_deployment() {
    log_warning "Cleaning up failed deployment..."
    
    if [ "$ENVIRONMENT" == "local" ]; then
        docker-compose -f "$PROJECT_ROOT/infrastructure/docker-compose.yml" down
    else
        kubectl delete namespace "$NAMESPACE" || true
    fi
}

show_deployment_info() {
    log_info "Deployment Information:"
    log_info "  Environment: $ENVIRONMENT"
    log_info "  Version: $VERSION"
    log_info "  Registry: $DOCKER_REGISTRY"
    log_info "  Namespace: $NAMESPACE"
    
    if [ "$ENVIRONMENT" != "local" ]; then
        log_info "  Cluster: $(kubectl config current-context)"
    fi
}

main() {
    log_info "Starting Anti-Bot Security Framework deployment"
    
    # Trap to cleanup on failure
    trap cleanup_failed_deployment ERR
    
    show_deployment_info
    check_dependencies
    validate_environment
    
    build_images
    push_images
    
    if [ "$ENVIRONMENT" == "local" ]; then
        deploy_local
        run_performance_tests
    else
        deploy_kubernetes
    fi
    
    log_success "Deployment completed successfully!"
    
    # Display next steps
    log_info "Next steps:"
    log_info "  1. Verify all services are running correctly"
    log_info "  2. Run comprehensive tests: ./test.sh"
    log_info "  3. Monitor system performance and logs"
    
    if [ "$ENVIRONMENT" != "local" ]; then
        log_info "  4. Configure DNS and load balancer"
        log_info "  5. Set up backup and disaster recovery"
    fi
}

# Show help
if [ "${1:-}" == "--help" ] || [ "${1:-}" == "-h" ]; then
    echo "Anti-Bot Security Framework Deployment Script"
    echo ""
    echo "Usage: $0 [ENVIRONMENT]"
    echo ""
    echo "ENVIRONMENT:"
    echo "  local      - Deploy with Docker Compose (default)"
    echo "  staging    - Deploy to Kubernetes staging"
    echo "  production - Deploy to Kubernetes production"
    echo ""
    echo "Environment Variables:"
    echo "  DOCKER_REGISTRY - Docker registry URL (default: localhost:5000)"
    echo "  VERSION         - Image version tag (default: git commit hash)"
    echo ""
    echo "Examples:"
    echo "  $0 local"
    echo "  VERSION=v1.0.0 $0 production"
    echo "  DOCKER_REGISTRY=myregistry.com $0 staging"
    exit 0
fi

# Run main function
main "$@"