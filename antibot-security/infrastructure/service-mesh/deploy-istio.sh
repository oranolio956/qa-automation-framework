#!/bin/bash

# Deploy Istio Service Mesh for Anti-Bot Security Framework
# Production-ready deployment script with comprehensive error handling

set -euo pipefail

# Configuration
ISTIO_VERSION="1.20.0"
NAMESPACE_ISTIO="istio-system"
NAMESPACE_SECURITY="antibot-security"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/tmp/istio-deployment-$(date +%Y%m%d-%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "${LOG_FILE}"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✓ $1${NC}" | tee -a "${LOG_FILE}"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠ $1${NC}" | tee -a "${LOG_FILE}"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ✗ $1${NC}" | tee -a "${LOG_FILE}"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    # Check cluster connection
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    # Check cluster version
    K8S_VERSION=$(kubectl version --client=false -o json | jq -r '.serverVersion.gitVersion')
    log "Kubernetes cluster version: ${K8S_VERSION}"
    
    # Check if istioctl is available
    if command -v istioctl &> /dev/null; then
        CURRENT_ISTIO_VERSION=$(istioctl version --remote=false --output json 2>/dev/null | jq -r '.meshVersion[0].info.version' || echo "not-installed")
        log "Current istioctl version: ${CURRENT_ISTIO_VERSION}"
    else
        log_warning "istioctl not found, will download"
        CURRENT_ISTIO_VERSION="not-installed"
    fi
    
    log_success "Prerequisites check completed"
}

# Download and install istioctl
install_istioctl() {
    if [[ "${CURRENT_ISTIO_VERSION}" != "${ISTIO_VERSION}" ]]; then
        log "Installing istioctl ${ISTIO_VERSION}..."
        
        # Download Istio
        curl -L https://istio.io/downloadIstio | ISTIO_VERSION=${ISTIO_VERSION} sh -
        
        # Add to PATH (for this session)
        export PATH="./istio-${ISTIO_VERSION}/bin:$PATH"
        
        # Verify installation
        if istioctl version --remote=false; then
            log_success "istioctl ${ISTIO_VERSION} installed successfully"
        else
            log_error "Failed to install istioctl"
            exit 1
        fi
    else
        log_success "istioctl ${ISTIO_VERSION} already installed"
    fi
}

# Pre-installation validation
pre_installation_validation() {
    log "Running pre-installation validation..."
    
    # Check cluster requirements
    istioctl x precheck
    
    # Verify cluster resources
    log "Checking cluster resources..."
    kubectl top nodes || log_warning "Cannot retrieve node metrics"
    
    log_success "Pre-installation validation completed"
}

# Install Istio control plane
install_istio_control_plane() {
    log "Installing Istio control plane..."
    
    # Create istio-system namespace if it doesn't exist
    kubectl create namespace ${NAMESPACE_ISTIO} --dry-run=client -o yaml | kubectl apply -f -
    
    # Apply Istio configuration
    istioctl install --set values.pilot.env.PILOT_ENABLE_AUTHORIZATION_POLICY=true \
                     --set values.pilot.env.PILOT_ENABLE_TELEMETRY_V2=true \
                     --set values.global.proxy.privileged=false \
                     --set values.pilot.resources.requests.cpu=500m \
                     --set values.pilot.resources.requests.memory=2Gi \
                     --set values.pilot.resources.limits.cpu=2000m \
                     --set values.pilot.resources.limits.memory=4Gi \
                     --set values.pilot.autoscaleMin=2 \
                     --set values.pilot.autoscaleMax=10 \
                     --set values.gateways.istio-ingressgateway.resources.requests.cpu=1000m \
                     --set values.gateways.istio-ingressgateway.resources.requests.memory=512Mi \
                     --set values.gateways.istio-ingressgateway.resources.limits.cpu=4000m \
                     --set values.gateways.istio-ingressgateway.resources.limits.memory=2Gi \
                     --set values.gateways.istio-ingressgateway.replicaCount=3 \
                     --set meshConfig.accessLogFile=/dev/stdout \
                     --set meshConfig.defaultConfig.proxyStatsMatcher.inclusionRegexps[0]=".*circuit_breaker.*" \
                     --set meshConfig.defaultConfig.proxyStatsMatcher.inclusionRegexps[1]=".*outlier_detection.*" \
                     --set meshConfig.defaultConfig.proxyStatsMatcher.inclusionRegexps[2]=".*retry.*" \
                     --set meshConfig.defaultConfig.proxyStatsMatcher.inclusionRegexps[3]=".*_cx_.*" \
                     --set meshConfig.defaultConfig.discoveryRefreshDelay=10s \
                     --set meshConfig.defaultConfig.proxyAdminPort=15000 \
                     --set meshConfig.defaultConfig.statusPort=15020 \
                     -y
    
    # Wait for control plane to be ready
    log "Waiting for Istio control plane to be ready..."
    kubectl wait --for=condition=ready pod -l app=istiod -n ${NAMESPACE_ISTIO} --timeout=600s
    
    # Verify installation
    istioctl verify-install
    
    log_success "Istio control plane installed successfully"
}

# Apply advanced configuration
apply_advanced_configuration() {
    log "Applying advanced Istio configuration..."
    
    # Apply the comprehensive configuration
    kubectl apply -f "${SCRIPT_DIR}/istio-installation.yaml"
    
    # Wait for gateways to be ready
    log "Waiting for gateways to be ready..."
    kubectl wait --for=condition=ready pod -l istio=ingressgateway -n ${NAMESPACE_ISTIO} --timeout=300s
    
    # Create anti-bot security namespace with automatic injection
    kubectl create namespace ${NAMESPACE_SECURITY} --dry-run=client -o yaml | kubectl apply -f -
    kubectl label namespace ${NAMESPACE_SECURITY} istio-injection=enabled --overwrite
    kubectl label namespace ${NAMESPACE_SECURITY} security-mesh=enabled --overwrite
    
    log_success "Advanced configuration applied successfully"
}

# Install observability addons
install_observability_addons() {
    log "Installing observability addons..."
    
    # Create observability namespace
    kubectl create namespace istio-observability --dry-run=client -o yaml | kubectl apply -f -
    kubectl label namespace istio-observability istio-injection=enabled --overwrite
    
    # Install Jaeger
    log "Installing Jaeger for distributed tracing..."
    kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.20/samples/addons/jaeger.yaml
    
    # Install Kiali
    log "Installing Kiali for service mesh visualization..."
    kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.20/samples/addons/kiali.yaml
    
    # Install Grafana
    log "Installing Grafana for metrics visualization..."
    kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.20/samples/addons/grafana.yaml
    
    # Install Prometheus (if not already present)
    log "Installing Prometheus for metrics collection..."
    kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.20/samples/addons/prometheus.yaml
    
    # Wait for addons to be ready
    log "Waiting for observability addons to be ready..."
    kubectl wait --for=condition=ready pod -l app=jaeger -n istio-system --timeout=300s || log_warning "Jaeger may still be starting"
    kubectl wait --for=condition=ready pod -l app=kiali -n istio-system --timeout=300s || log_warning "Kiali may still be starting"
    kubectl wait --for=condition=ready pod -l app=grafana -n istio-system --timeout=300s || log_warning "Grafana may still be starting"
    kubectl wait --for=condition=ready pod -l app=prometheus -n istio-system --timeout=300s || log_warning "Prometheus may still be starting"
    
    log_success "Observability addons installed successfully"
}

# Setup TLS certificates
setup_tls_certificates() {
    log "Setting up TLS certificates..."
    
    # Create self-signed certificate for development (replace with proper certs in production)
    openssl req -x509 -newkey rsa:4096 -keyout antibot-security-tls.key \
                -out antibot-security-tls.crt -days 365 -nodes \
                -subj "/C=US/ST=CA/L=San Francisco/O=AntiBot Security/OU=Security/CN=security-api.antibot.internal" \
                -addext "subjectAltName=DNS:security-api.antibot.internal,DNS:*.antibot.internal"
    
    # Create Kubernetes TLS secret
    kubectl create secret tls antibot-security-tls \
            --key antibot-security-tls.key \
            --cert antibot-security-tls.crt \
            -n ${NAMESPACE_ISTIO} \
            --dry-run=client -o yaml | kubectl apply -f -
    
    # Clean up certificate files
    rm -f antibot-security-tls.key antibot-security-tls.crt
    
    log_success "TLS certificates configured successfully"
}

# Validate deployment
validate_deployment() {
    log "Validating Istio deployment..."
    
    # Check all components are running
    kubectl get pods -n ${NAMESPACE_ISTIO}
    kubectl get pods -n ${NAMESPACE_SECURITY} || log_warning "No pods in antibot-security namespace yet"
    
    # Check gateway configuration
    kubectl get gateway -n ${NAMESPACE_SECURITY}
    kubectl get virtualservice -n ${NAMESPACE_SECURITY}
    kubectl get destinationrule -n ${NAMESPACE_SECURITY}
    
    # Verify mTLS configuration
    istioctl authn tls-check -n ${NAMESPACE_SECURITY} || log_warning "mTLS check failed - may be expected if no services deployed yet"
    
    # Check ingress gateway external IP
    EXTERNAL_IP=$(kubectl get service istio-ingressgateway -n ${NAMESPACE_ISTIO} -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    if [[ -n "${EXTERNAL_IP}" ]]; then
        log_success "Ingress gateway external IP: ${EXTERNAL_IP}"
    else
        log_warning "Ingress gateway external IP not yet assigned"
    fi
    
    # Performance and configuration analysis
    istioctl analyze -n ${NAMESPACE_SECURITY} || log_warning "Analysis found potential issues"
    
    log_success "Deployment validation completed"
}

# Setup monitoring and alerting
setup_monitoring() {
    log "Setting up advanced monitoring..."
    
    # Create ServiceMonitor for Prometheus scraping
    cat <<EOF | kubectl apply -f -
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: istio-mesh-metrics
  namespace: ${NAMESPACE_ISTIO}
  labels:
    app: istio-mesh
spec:
  selector:
    matchLabels:
      app: istiod
  endpoints:
  - port: http-monitoring
    interval: 15s
    path: /stats/prometheus
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: istio-gateway-metrics
  namespace: ${NAMESPACE_ISTIO}
  labels:
    app: istio-gateway
spec:
  selector:
    matchLabels:
      istio: ingressgateway
  endpoints:
  - port: http-monitoring
    interval: 15s
    path: /stats/prometheus
EOF
    
    log_success "Monitoring configuration applied"
}

# Generate deployment report
generate_deployment_report() {
    log "Generating deployment report..."
    
    REPORT_FILE="/tmp/istio-deployment-report-$(date +%Y%m%d-%H%M%S).json"
    
    # Collect deployment information
    cat > "${REPORT_FILE}" <<EOF
{
  "deployment_timestamp": "$(date -Iseconds)",
  "istio_version": "${ISTIO_VERSION}",
  "kubernetes_version": "${K8S_VERSION}",
  "namespaces": {
    "istio_system": "${NAMESPACE_ISTIO}",
    "antibot_security": "${NAMESPACE_SECURITY}"
  },
  "components": {
    "control_plane": "$(kubectl get pods -n ${NAMESPACE_ISTIO} -l app=istiod --no-headers | wc -l) pods",
    "ingress_gateway": "$(kubectl get pods -n ${NAMESPACE_ISTIO} -l istio=ingressgateway --no-headers | wc -l) pods",
    "observability_addons": {
      "jaeger": "$(kubectl get pods -n ${NAMESPACE_ISTIO} -l app=jaeger --no-headers | wc -l) pods",
      "kiali": "$(kubectl get pods -n ${NAMESPACE_ISTIO} -l app=kiali --no-headers | wc -l) pods",
      "grafana": "$(kubectl get pods -n ${NAMESPACE_ISTIO} -l app=grafana --no-headers | wc -l) pods",
      "prometheus": "$(kubectl get pods -n ${NAMESPACE_ISTIO} -l app=prometheus --no-headers | wc -l) pods"
    }
  },
  "external_access": {
    "ingress_ip": "$(kubectl get service istio-ingressgateway -n ${NAMESPACE_ISTIO} -o jsonpath='{.status.loadBalancer.ingress[0].ip}' || echo 'pending')",
    "ingress_hostname": "$(kubectl get service istio-ingressgateway -n ${NAMESPACE_ISTIO} -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' || echo 'none')"
  },
  "security_configuration": {
    "mtls_enabled": true,
    "authorization_policies": "$(kubectl get authorizationpolicy -n ${NAMESPACE_SECURITY} --no-headers | wc -l)",
    "peer_authentication": "$(kubectl get peerauthentication -n ${NAMESPACE_SECURITY} --no-headers | wc -l)"
  },
  "log_file": "${LOG_FILE}"
}
EOF
    
    log_success "Deployment report generated: ${REPORT_FILE}"
    cat "${REPORT_FILE}"
}

# Cleanup function
cleanup() {
    log "Cleaning up temporary files..."
    # Clean up any temporary files if needed
    log_success "Cleanup completed"
}

# Main execution
main() {
    log "Starting Istio service mesh deployment for Anti-Bot Security Framework"
    log "Deployment log file: ${LOG_FILE}"
    
    # Set trap for cleanup
    trap cleanup EXIT
    
    # Execute deployment steps
    check_prerequisites
    install_istioctl
    pre_installation_validation
    install_istio_control_plane
    apply_advanced_configuration
    install_observability_addons
    setup_tls_certificates
    setup_monitoring
    validate_deployment
    generate_deployment_report
    
    log_success "Istio service mesh deployment completed successfully!"
    log_success "Access points:"
    log_success "  - Kiali Dashboard: kubectl port-forward svc/kiali 20001:20001 -n istio-system"
    log_success "  - Grafana Dashboard: kubectl port-forward svc/grafana 3000:3000 -n istio-system"
    log_success "  - Jaeger UI: kubectl port-forward svc/jaeger 16686:16686 -n istio-system"
    
    # Next steps information
    log "Next steps:"
    log "1. Deploy your anti-bot security services to the 'antibot-security' namespace"
    log "2. Services will automatically get Istio proxy injection"
    log "3. Configure your DNS to point to the ingress gateway IP"
    log "4. Monitor service mesh traffic through Kiali dashboard"
    log "5. View metrics and traces in Grafana and Jaeger"
}

# Execute main function
main "$@"