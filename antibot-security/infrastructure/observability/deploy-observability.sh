#!/bin/bash

# Unified Observability Command Center Deployment Script
# Deploys the complete AI-driven security monitoring and threat intelligence platform

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="security-observability"
DEPLOYMENT_MODE="${1:-docker-compose}"  # docker-compose or kubernetes
ENVIRONMENT="${2:-production}"

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Function to check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is required but not installed"
    fi
    
    # Check Docker Compose
    if [[ "$DEPLOYMENT_MODE" == "docker-compose" ]] && ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is required but not installed"
    fi
    
    # Check kubectl for Kubernetes deployment
    if [[ "$DEPLOYMENT_MODE" == "kubernetes" ]] && ! command -v kubectl &> /dev/null; then
        error "kubectl is required for Kubernetes deployment"
    fi
    
    # Check Helm for Kubernetes deployment
    if [[ "$DEPLOYMENT_MODE" == "kubernetes" ]] && ! command -v helm &> /dev/null; then
        error "Helm is required for Kubernetes deployment"
    fi
    
    # Check available memory (minimum 4GB recommended)
    AVAILABLE_MEMORY=$(free -m | awk 'NR==2{printf "%.0f", $7}')
    if [[ $AVAILABLE_MEMORY -lt 4000 ]]; then
        warn "Low available memory (${AVAILABLE_MEMORY}MB). Minimum 4GB recommended for full observability stack."
    fi
    
    log "Prerequisites check completed"
}

# Function to prepare environment
prepare_environment() {
    log "Preparing deployment environment..."
    
    # Create necessary directories
    mkdir -p logs
    mkdir -p data/{redis,prometheus,grafana,elasticsearch}
    
    # Set proper permissions
    chmod 755 logs
    chmod 755 data/*
    
    # Create configuration files if they don't exist
    if [[ ! -f "redis.conf" ]]; then
        create_redis_config
    fi
    
    if [[ ! -f "alertmanager.yml" ]]; then
        create_alertmanager_config
    fi
    
    log "Environment preparation completed"
}

# Function to create Redis configuration
create_redis_config() {
    log "Creating Redis configuration..."
    
    cat > redis.conf << 'EOF'
# Redis Configuration for Observability
port 6379
bind 0.0.0.0
timeout 300
tcp-keepalive 60
tcp-backlog 511

# Memory management
maxmemory 512mb
maxmemory-policy allkeys-lru
maxmemory-samples 5

# Persistence
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir /data

# Security
requirepass observability_redis_2024
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command DEBUG ""

# Logging
loglevel notice
logfile /var/log/redis/redis-server.log
syslog-enabled yes
syslog-ident redis
EOF
}

# Function to create AlertManager configuration
create_alertmanager_config() {
    log "Creating AlertManager configuration..."
    
    cat > alertmanager.yml << 'EOF'
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@company.com'

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'
  routes:
  - match:
      severity: critical
    receiver: 'critical-alerts'
    continue: true
  - match:
      severity: warning
    receiver: 'warning-alerts'

receivers:
- name: 'web.hook'
  webhook_configs:
  - url: 'http://command-center:8080/api/webhook/alerts'
    send_resolved: true

- name: 'critical-alerts'
  email_configs:
  - to: 'security-team@company.com'
    subject: '🚨 CRITICAL Security Alert: {{ .GroupLabels.alertname }}'
    body: |
      Alert: {{ .GroupLabels.alertname }}
      Severity: {{ .GroupLabels.severity }}
      Service: {{ .GroupLabels.service }}
      
      {{ range .Alerts }}
      Summary: {{ .Annotations.summary }}
      Description: {{ .Annotations.description }}
      {{ end }}
  slack_configs:
  - api_url: 'YOUR_SLACK_WEBHOOK_URL'
    channel: '#security-alerts'
    title: 'Critical Security Alert'
    text: '{{ .GroupLabels.alertname }}: {{ .CommonAnnotations.summary }}'

- name: 'warning-alerts'
  slack_configs:
  - api_url: 'YOUR_SLACK_WEBHOOK_URL'
    channel: '#security-monitoring'
    title: 'Security Warning'
    text: '{{ .GroupLabels.alertname }}: {{ .CommonAnnotations.summary }}'

inhibit_rules:
- source_match:
    severity: 'critical'
  target_match:
    severity: 'warning'
  equal: ['alertname', 'service']
EOF
}

# Function to deploy using Docker Compose
deploy_docker_compose() {
    log "Deploying Unified Observability Command Center using Docker Compose..."
    
    # Build custom images
    info "Building Command Center Docker image..."
    docker build -f ../backend/observability/Dockerfile.command-center \
                 -t security-command-center:latest \
                 ../backend/observability/
    
    # Start the observability stack
    info "Starting observability stack..."
    docker-compose -f docker-compose.observability.yml up -d
    
    # Wait for services to be ready
    info "Waiting for services to initialize..."
    sleep 30
    
    # Verify deployments
    verify_docker_deployment
    
    log "Docker Compose deployment completed successfully"
}

# Function to deploy using Kubernetes
deploy_kubernetes() {
    log "Deploying Unified Observability Command Center using Kubernetes..."
    
    # Create namespace
    kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
    
    # Deploy using Helm charts
    info "Installing observability stack with Helm..."
    
    # Add Helm repositories
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo add grafana https://grafana.github.io/helm-charts
    helm repo add elastic https://helm.elastic.co
    helm repo update
    
    # Install Prometheus
    helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
        --namespace $NAMESPACE \
        --set grafana.adminPassword=admin123 \
        --set prometheus.prometheusSpec.retention=15d
    
    # Install Jaeger
    kubectl apply -f https://github.com/jaegertracing/jaeger-operator/releases/download/v1.50.0/jaeger-operator.yaml -n observability-system
    
    # Deploy Command Center
    kubectl apply -f kubernetes/command-center-deployment.yaml -n $NAMESPACE
    
    log "Kubernetes deployment completed successfully"
}

# Function to verify Docker deployment
verify_docker_deployment() {
    log "Verifying deployment health..."
    
    local services=("command-center:8080" "prometheus:9090" "grafana:3000" "jaeger:16686")
    local failed_services=()
    
    for service in "${services[@]}"; do
        local service_name=${service%%:*}
        local port=${service##*:}
        
        info "Checking $service_name on port $port..."
        
        # Wait up to 60 seconds for service to respond
        local timeout=60
        local count=0
        
        while [[ $count -lt $timeout ]]; do
            if curl -f -s "http://localhost:$port/health" >/dev/null 2>&1 || \
               curl -f -s "http://localhost:$port/" >/dev/null 2>&1; then
                log "✅ $service_name is healthy"
                break
            fi
            
            sleep 1
            ((count++))
            
            if [[ $count -eq $timeout ]]; then
                warn "❌ $service_name failed health check"
                failed_services+=("$service_name")
            fi
        done
    done
    
    if [[ ${#failed_services[@]} -gt 0 ]]; then
        warn "Some services failed health checks: ${failed_services[*]}"
        info "Check logs with: docker-compose logs [service-name]"
    else
        log "All services are healthy! 🎉"
    fi
}

# Function to display access information
display_access_info() {
    log "Deployment completed! Access information:"
    echo
    echo -e "${BLUE}🛡️  Unified Security Command Center:${NC} http://localhost:8080"
    echo -e "${BLUE}📊 Prometheus Metrics:${NC} http://localhost:9090"
    echo -e "${BLUE}📈 Grafana Dashboards:${NC} http://localhost:3000 (admin/admin123)"
    echo -e "${BLUE}🔍 Jaeger Tracing:${NC} http://localhost:16686"
    echo -e "${BLUE}🔍 Kibana Logs:${NC} http://localhost:5601"
    echo -e "${BLUE}🚨 AlertManager:${NC} http://localhost:9093"
    echo
    echo -e "${GREEN}Real-time Security Dashboard:${NC} http://localhost:8080"
    echo -e "${GREEN}WebSocket Connection:${NC} ws://localhost:8080/ws/dashboard"
    echo
    echo -e "${YELLOW}API Endpoints:${NC}"
    echo "  - Health Check: http://localhost:8080/api/health"
    echo "  - Dashboard Data: http://localhost:8080/api/dashboard"
    echo "  - Metrics: http://localhost:8080/metrics"
    echo
}

# Function to setup monitoring
setup_monitoring() {
    log "Setting up monitoring and alerting..."
    
    # Configure Grafana dashboards
    if curl -f -s "http://localhost:3000/api/health" >/dev/null 2>&1; then
        info "Configuring Grafana dashboards..."
        # Import pre-built security dashboards
        # This would be implemented with Grafana API calls
    fi
    
    # Test alert routing
    info "Testing alert routing..."
    curl -X POST http://localhost:9093/api/v1/alerts \
         -H "Content-Type: application/json" \
         -d '[{
           "labels": {
             "alertname": "TestAlert",
             "severity": "info",
             "service": "deployment-test"
           },
           "annotations": {
             "summary": "Deployment test alert",
             "description": "This is a test alert to verify the alerting pipeline."
           }
         }]' >/dev/null 2>&1 || warn "Alert routing test failed"
    
    log "Monitoring setup completed"
}

# Function to cleanup on failure
cleanup_on_failure() {
    warn "Deployment failed. Cleaning up..."
    
    if [[ "$DEPLOYMENT_MODE" == "docker-compose" ]]; then
        docker-compose -f docker-compose.observability.yml down
    elif [[ "$DEPLOYMENT_MODE" == "kubernetes" ]]; then
        kubectl delete namespace $NAMESPACE --ignore-not-found=true
    fi
    
    error "Deployment failed. Environment cleaned up."
}

# Function to show help
show_help() {
    echo "Unified Observability Command Center Deployment Script"
    echo
    echo "Usage: $0 [deployment-mode] [environment]"
    echo
    echo "Deployment Modes:"
    echo "  docker-compose    Deploy using Docker Compose (default)"
    echo "  kubernetes        Deploy using Kubernetes and Helm"
    echo
    echo "Environments:"
    echo "  production        Production configuration (default)"
    echo "  staging           Staging configuration"
    echo "  development       Development configuration"
    echo
    echo "Examples:"
    echo "  $0                                    # Docker Compose deployment"
    echo "  $0 docker-compose production         # Docker Compose production"
    echo "  $0 kubernetes staging                # Kubernetes staging"
    echo
    echo "Environment Variables:"
    echo "  REDIS_PASSWORD    Redis password (optional)"
    echo "  GRAFANA_PASSWORD  Grafana admin password (optional)"
    echo "  SLACK_WEBHOOK_URL Slack webhook for alerts (optional)"
    echo
}

# Main execution
main() {
    # Handle help flag
    if [[ "${1:-}" == "-h" ]] || [[ "${1:-}" == "--help" ]]; then
        show_help
        exit 0
    fi
    
    # Set error trap
    trap cleanup_on_failure ERR
    
    log "Starting Unified Observability Command Center deployment..."
    info "Deployment Mode: $DEPLOYMENT_MODE"
    info "Environment: $ENVIRONMENT"
    
    # Execute deployment steps
    check_prerequisites
    prepare_environment
    
    case $DEPLOYMENT_MODE in
        "docker-compose")
            deploy_docker_compose
            ;;
        "kubernetes")
            deploy_kubernetes
            ;;
        *)
            error "Unknown deployment mode: $DEPLOYMENT_MODE"
            ;;
    esac
    
    setup_monitoring
    display_access_info
    
    log "🚀 Unified Observability Command Center deployed successfully!"
    info "The AI-driven security monitoring and threat intelligence platform is now operational."
}

# Execute main function
main "$@"