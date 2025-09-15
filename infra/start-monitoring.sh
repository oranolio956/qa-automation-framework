#!/bin/bash

# Anti-Bot Security - Comprehensive Monitoring Stack Startup Script
# This script starts the complete observability platform

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"

# Default environment variables
export GRAFANA_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:-"admin123!"}
export KIBANA_PASSWORD=${KIBANA_PASSWORD:-"kibana123!"}
export ALERT_WEBHOOK_URL=${ALERT_WEBHOOK_URL:-"http://localhost:9093/api/v1/alerts"}
export SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL:-""}
export ML_ALERT_WEBHOOK_URL=${ML_ALERT_WEBHOOK_URL:-"http://localhost:9093/api/v1/alerts"}

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if required tools are installed
check_dependencies() {
    print_status "Checking dependencies..."
    
    local missing_deps=()
    
    if ! command -v docker &> /dev/null; then
        missing_deps+=("docker")
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        missing_deps+=("docker-compose")
    fi
    
    if ! command -v curl &> /dev/null; then
        missing_deps+=("curl")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        print_error "Missing required dependencies: ${missing_deps[*]}"
        print_error "Please install the missing dependencies and try again."
        exit 1
    fi
    
    print_success "All dependencies are installed"
}

# Function to check Docker daemon
check_docker() {
    print_status "Checking Docker daemon..."
    
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker and try again."
        exit 1
    fi
    
    print_success "Docker daemon is running"
}

# Function to create required directories
create_directories() {
    print_status "Creating required directories..."
    
    local dirs=(
        "$SCRIPT_DIR/data/prometheus"
        "$SCRIPT_DIR/data/grafana"
        "$SCRIPT_DIR/data/elasticsearch"
        "$SCRIPT_DIR/data/alertmanager"
        "$SCRIPT_DIR/logs"
        "$PROJECT_ROOT/models"
    )
    
    for dir in "${dirs[@]}"; do
        mkdir -p "$dir"
        print_status "Created directory: $dir"
    done
    
    print_success "Required directories created"
}

# Function to set proper permissions
set_permissions() {
    print_status "Setting proper permissions..."
    
    # Elasticsearch requires specific ownership
    if [ -d "$SCRIPT_DIR/data/elasticsearch" ]; then
        sudo chown -R 1000:1000 "$SCRIPT_DIR/data/elasticsearch" 2>/dev/null || {
            print_warning "Could not set Elasticsearch permissions. You may need to run 'sudo chown -R 1000:1000 $SCRIPT_DIR/data/elasticsearch'"
        }
    fi
    
    # Grafana permissions
    if [ -d "$SCRIPT_DIR/data/grafana" ]; then
        sudo chown -R 472:472 "$SCRIPT_DIR/data/grafana" 2>/dev/null || {
            print_warning "Could not set Grafana permissions. You may need to run 'sudo chown -R 472:472 $SCRIPT_DIR/data/grafana'"
        }
    fi
    
    print_success "Permissions configured"
}

# Function to validate configuration files
validate_configs() {
    print_status "Validating configuration files..."
    
    local config_files=(
        "$SCRIPT_DIR/config/prometheus.yml"
        "$SCRIPT_DIR/config/alert_rules.yml"
        "$SCRIPT_DIR/config/alertmanager.yml"
        "$SCRIPT_DIR/config/logstash/config/logstash.yml"
        "$SCRIPT_DIR/config/kibana/kibana.yml"
    )
    
    for config in "${config_files[@]}"; do
        if [ ! -f "$config" ]; then
            print_error "Missing configuration file: $config"
            exit 1
        fi
        print_status "✓ $config"
    done
    
    print_success "All configuration files found"
}

# Function to pull Docker images
pull_images() {
    print_status "Pulling Docker images (this may take a while)..."
    
    docker-compose -f "$DOCKER_COMPOSE_FILE" pull
    
    print_success "Docker images pulled successfully"
}

# Function to start core services first
start_core_services() {
    print_status "Starting core infrastructure services..."
    
    # Start Redis and Vault first
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d redis vault
    
    print_status "Waiting for core services to be ready..."
    sleep 10
    
    # Check if Redis is ready
    local redis_ready=false
    for i in {1..30}; do
        if docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T redis redis-cli ping &> /dev/null; then
            redis_ready=true
            break
        fi
        sleep 2
        echo -n "."
    done
    
    if [ "$redis_ready" = false ]; then
        print_error "Redis failed to start properly"
        exit 1
    fi
    
    print_success "Core services are ready"
}

# Function to start monitoring stack
start_monitoring_stack() {
    print_status "Starting monitoring and observability stack..."
    
    # Start Prometheus and Elasticsearch
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d prometheus elasticsearch node-exporter redis-exporter
    
    print_status "Waiting for Prometheus and Elasticsearch..."
    sleep 20
    
    # Start Grafana, Kibana, and Logstash
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d grafana kibana logstash alertmanager
    
    print_status "Waiting for web interfaces to be ready..."
    sleep 15
    
    print_success "Monitoring stack started"
}

# Function to start application monitoring services
start_app_monitoring() {
    print_status "Starting application monitoring services..."
    
    # Build and start custom monitoring services
    docker-compose -f "$DOCKER_COMPOSE_FILE" build security-monitor ml-monitor
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d security-monitor ml-monitor
    
    print_status "Waiting for monitoring services..."
    sleep 10
    
    print_success "Application monitoring services started"
}

# Function to check service health
check_health() {
    print_status "Checking service health..."
    
    local services=(
        "Prometheus:http://localhost:9090/-/ready"
        "Grafana:http://localhost:3000/api/health"
        "Elasticsearch:http://localhost:9200/_cluster/health"
        "Kibana:http://localhost:5601/api/status"
        "Alertmanager:http://localhost:9093/-/ready"
    )
    
    for service_info in "${services[@]}"; do
        local name="${service_info%:*}"
        local url="${service_info#*:}"
        
        if curl -s "$url" &> /dev/null; then
            print_success "$name is healthy"
        else
            print_warning "$name may not be ready yet (this is normal during startup)"
        fi
    done
}

# Function to initialize Grafana dashboards
initialize_grafana() {
    print_status "Initializing Grafana dashboards..."
    
    # Wait for Grafana to be fully ready
    local grafana_ready=false
    for i in {1..60}; do
        if curl -s http://localhost:3000/api/health &> /dev/null; then
            grafana_ready=true
            break
        fi
        sleep 2
        echo -n "."
    done
    echo
    
    if [ "$grafana_ready" = false ]; then
        print_warning "Grafana is not ready for dashboard initialization"
        return
    fi
    
    print_success "Grafana dashboards will be automatically provisioned"
}

# Function to show service URLs
show_urls() {
    print_success "Monitoring stack is running! Access the following services:"
    echo
    echo -e "${BLUE}Web Interfaces:${NC}"
    echo -e "  • Grafana Dashboard:     ${GREEN}http://localhost:3000${NC} (admin / $GRAFANA_ADMIN_PASSWORD)"
    echo -e "  • Prometheus:            ${GREEN}http://localhost:9090${NC}"
    echo -e "  • Kibana:               ${GREEN}http://localhost:5601${NC}"
    echo -e "  • Alertmanager:         ${GREEN}http://localhost:9093${NC}"
    echo
    echo -e "${BLUE}APIs:${NC}"
    echo -e "  • Prometheus API:        ${GREEN}http://localhost:9090/api/v1${NC}"
    echo -e "  • Elasticsearch API:     ${GREEN}http://localhost:9200${NC}"
    echo -e "  • Grafana API:          ${GREEN}http://localhost:3000/api${NC}"
    echo
    echo -e "${BLUE}Monitoring Services:${NC}"
    echo -e "  • Security Monitor:      ${GREEN}Internal (port 8004)${NC}"
    echo -e "  • ML Monitor:           ${GREEN}Internal (port 8005)${NC}"
    echo
    echo -e "${YELLOW}Note: It may take a few minutes for all services to be fully operational${NC}"
}

# Function to show logs
show_logs() {
    print_status "Showing recent logs from all services..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" logs --tail=50 -f
}

# Function to stop all services
stop_services() {
    print_status "Stopping all monitoring services..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" down
    print_success "All services stopped"
}

# Function to cleanup
cleanup() {
    print_status "Cleaning up (removing containers, volumes, and images)..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" down -v --rmi all
    print_success "Cleanup completed"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [COMMAND]"
    echo
    echo "Commands:"
    echo "  start     Start the complete monitoring stack (default)"
    echo "  stop      Stop all monitoring services"
    echo "  restart   Restart all monitoring services"
    echo "  status    Show status of all services"
    echo "  logs      Show logs from all services"
    echo "  cleanup   Stop and remove all containers, volumes, and images"
    echo "  health    Check health of all services"
    echo "  urls      Show service URLs"
    echo "  help      Show this help message"
    echo
    echo "Environment Variables:"
    echo "  GRAFANA_ADMIN_PASSWORD    Grafana admin password (default: admin123!)"
    echo "  KIBANA_PASSWORD          Kibana password (default: kibana123!)"
    echo "  ALERT_WEBHOOK_URL        Webhook URL for alerts"
    echo "  SLACK_WEBHOOK_URL        Slack webhook URL"
}

# Main execution
main() {
    local command="${1:-start}"
    
    case "$command" in
        "start")
            print_status "Starting Anti-Bot Security Monitoring Stack..."
            check_dependencies
            check_docker
            create_directories
            set_permissions
            validate_configs
            pull_images
            start_core_services
            start_monitoring_stack
            start_app_monitoring
            sleep 30  # Give services time to start
            check_health
            initialize_grafana
            show_urls
            ;;
        "stop")
            stop_services
            ;;
        "restart")
            stop_services
            sleep 5
            main "start"
            ;;
        "status")
            docker-compose -f "$DOCKER_COMPOSE_FILE" ps
            ;;
        "logs")
            show_logs
            ;;
        "cleanup")
            cleanup
            ;;
        "health")
            check_health
            ;;
        "urls")
            show_urls
            ;;
        "help"|"--help"|"-h")
            show_usage
            ;;
        *)
            print_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"