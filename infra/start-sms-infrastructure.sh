#!/bin/bash

# SMS Infrastructure Startup Script
# Deploys Redis, RabbitMQ, and SMS services with proper health checks

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

# Check if docker and docker-compose are available
check_dependencies() {
    log "Checking dependencies..."
    
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    log "Dependencies check passed"
}

# Validate environment variables
validate_environment() {
    log "Validating environment variables..."
    
    # Check for critical environment variables
    REQUIRED_VARS=(
        "TWILIO_ACCOUNT_SID"
        "TWILIO_AUTH_TOKEN"
        "TWILIO_PHONE_NUMBER"
    )
    
    MISSING_VARS=()
    
    for var in "${REQUIRED_VARS[@]}"; do
        if [[ -z "${!var}" ]]; then
            MISSING_VARS+=("$var")
        fi
    done
    
    if [[ ${#MISSING_VARS[@]} -gt 0 ]]; then
        error "Missing required environment variables:"
        for var in "${MISSING_VARS[@]}"; do
            error "  - $var"
        done
        error "Please set these variables before running the script"
        exit 1
    fi
    
    # Warn about optional variables
    OPTIONAL_VARS=(
        "AWS_SNS_ACCESS_KEY"
        "AWS_SNS_SECRET_KEY"
        "RABBITMQ_USER"
        "RABBITMQ_PASS"
    )
    
    for var in "${OPTIONAL_VARS[@]}"; do
        if [[ -z "${!var}" ]]; then
            warn "Optional variable $var is not set"
        fi
    done
    
    log "Environment validation completed"
}

# Create necessary directories
create_directories() {
    log "Creating necessary directories..."
    
    mkdir -p logs/redis
    mkdir -p logs/rabbitmq
    mkdir -p logs/sms-service
    mkdir -p data/redis
    mkdir -p data/rabbitmq
    
    log "Directories created"
}

# Wait for service to be healthy
wait_for_service() {
    local service_name=$1
    local health_url=$2
    local max_attempts=${3:-30}
    local attempt=1
    
    log "Waiting for $service_name to become healthy..."
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -f -s "$health_url" > /dev/null 2>&1; then
            log "$service_name is healthy"
            return 0
        fi
        
        info "Attempt $attempt/$max_attempts: $service_name not ready yet, waiting..."
        sleep 10
        ((attempt++))
    done
    
    error "$service_name failed to become healthy after $max_attempts attempts"
    return 1
}

# Start infrastructure services
start_infrastructure() {
    log "Starting infrastructure services..."
    
    # Start Redis first
    info "Starting Redis..."
    docker-compose up -d redis
    
    # Wait for Redis to be ready
    for i in {1..30}; do
        if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
            log "Redis is ready"
            break
        fi
        if [[ $i -eq 30 ]]; then
            error "Redis failed to start"
            exit 1
        fi
        sleep 2
    done
    
    # Start RabbitMQ
    info "Starting RabbitMQ..."
    docker-compose up -d rabbitmq
    
    # Wait for RabbitMQ to be ready
    for i in {1..60}; do
        if docker-compose exec -T rabbitmq rabbitmq-diagnostics ping > /dev/null 2>&1; then
            log "RabbitMQ is ready"
            break
        fi
        if [[ $i -eq 60 ]]; then
            error "RabbitMQ failed to start"
            exit 1
        fi
        sleep 5
    done
    
    log "Infrastructure services started successfully"
}

# Start SMS services
start_sms_services() {
    log "Starting SMS services..."
    
    # Build SMS service image
    info "Building SMS service..."
    docker-compose build sms-service sms-worker
    
    # Start SMS service
    info "Starting SMS service..."
    docker-compose up -d sms-service
    
    # Wait for SMS service to be healthy
    wait_for_service "SMS Service" "http://localhost:8002/health" 30
    
    # Start SMS workers
    info "Starting SMS workers..."
    docker-compose up -d sms-worker
    
    log "SMS services started successfully"
}

# Display service status
show_status() {
    log "Service Status:"
    echo ""
    
    # Check Redis
    if docker-compose ps redis | grep -q "Up"; then
        echo -e "  ${GREEN}✓${NC} Redis: Running on port 6379"
    else
        echo -e "  ${RED}✗${NC} Redis: Not running"
    fi
    
    # Check RabbitMQ
    if docker-compose ps rabbitmq | grep -q "Up"; then
        echo -e "  ${GREEN}✓${NC} RabbitMQ: Running on port 5672 (Management: 15672)"
    else
        echo -e "  ${RED}✗${NC} RabbitMQ: Not running"
    fi
    
    # Check SMS Service
    if docker-compose ps sms-service | grep -q "Up"; then
        echo -e "  ${GREEN}✓${NC} SMS Service: Running on port 8002"
    else
        echo -e "  ${RED}✗${NC} SMS Service: Not running"
    fi
    
    # Check SMS Workers
    if docker-compose ps sms-worker | grep -q "Up"; then
        echo -e "  ${GREEN}✓${NC} SMS Workers: Running"
    else
        echo -e "  ${RED}✗${NC} SMS Workers: Not running"
    fi
    
    echo ""
    log "Access points:"
    echo "  - SMS Service API: http://localhost:8002"
    echo "  - SMS Service Health: http://localhost:8002/health"
    echo "  - RabbitMQ Management: http://localhost:15672 (admin:admin123)"
    echo "  - Redis: localhost:6379"
    echo ""
}

# Test SMS functionality
test_sms_service() {
    log "Testing SMS service functionality..."
    
    # Test health endpoint
    if ! curl -f -s "http://localhost:8002/health" > /dev/null; then
        error "SMS service health check failed"
        return 1
    fi
    
    # Test phone pool status
    if ! curl -f -s "http://localhost:8002/api/v1/phone-pool/status" > /dev/null; then
        warn "Phone pool status endpoint not responding"
    fi
    
    log "Basic SMS service tests passed"
}

# Cleanup function for graceful shutdown
cleanup() {
    log "Cleaning up..."
    docker-compose down
}

# Set trap for cleanup on exit
trap cleanup EXIT INT TERM

# Main execution
main() {
    log "Starting SMS Infrastructure Deployment"
    
    check_dependencies
    validate_environment
    create_directories
    
    start_infrastructure
    start_sms_services
    
    show_status
    
    # Run tests if requested
    if [[ "$1" == "--test" ]]; then
        test_sms_service
    fi
    
    log "SMS Infrastructure deployment completed successfully!"
    log "Check logs with: docker-compose logs -f [service-name]"
    log "Stop services with: docker-compose down"
}

# Run main function with all arguments
main "$@"