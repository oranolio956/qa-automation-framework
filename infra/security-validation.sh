#!/bin/bash
# Production Security Validation Script
# Validates all critical security requirements before deployment

set -euo pipefail

echo "🔒 CRITICAL SECURITY VALIDATION - DEPLOYMENT BLOCKER CHECK"
echo "=========================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

VALIDATION_FAILED=false
CRITICAL_ISSUES=0
WARNINGS=0

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    ((WARNINGS++))
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
    ((CRITICAL_ISSUES++))
    VALIDATION_FAILED=true
}

echo
echo "🔍 1. EXPOSED CREDENTIALS SCAN"
echo "=============================="

# Scan for exposed API keys and secrets in code
echo "Scanning for hardcoded credentials..."

# Check for Twilio credentials in code
if grep -r "sk_" . --exclude-dir=node_modules --exclude-dir=.git 2>/dev/null | grep -v ".template" | grep -v "security-validation.sh"; then
    log_error "CRITICAL: Twilio API keys found hardcoded in source code"
else
    log_success "No Twilio API keys found hardcoded in source code"
fi

# Check for AWS credentials
if grep -r "AKIA[0-9A-Z]{16}" . --exclude-dir=node_modules --exclude-dir=.git 2>/dev/null | grep -v ".template" | grep -v "security-validation.sh"; then
    log_error "CRITICAL: AWS access keys found hardcoded in source code"
else
    log_success "No AWS access keys found hardcoded in source code"
fi

# Check for other common secret patterns
SECRET_PATTERNS=(
    "password.*=.*[\"'][^\"']{8,}[\"']"
    "secret.*=.*[\"'][^\"']{16,}[\"']"
    "token.*=.*[\"'][^\"']{20,}[\"']"
    "api_key.*=.*[\"'][^\"']{16,}[\"']"
    "auth_token.*=.*[\"'][^\"']{20,}[\"']"
)

for pattern in "${SECRET_PATTERNS[@]}"; do
    if grep -rE "$pattern" . --exclude-dir=node_modules --exclude-dir=.git --exclude="*.template" --exclude="security-validation.sh" 2>/dev/null; then
        log_error "CRITICAL: Potential hardcoded secrets found matching pattern: $pattern"
    fi
done

# Check docker-compose for environment variable exposure
echo "Checking docker-compose files for credential exposure..."
if grep -E "TWILIO_AUTH_TOKEN=|AWS_SECRET_KEY=|API_KEY=" infra/docker-compose.yml 2>/dev/null; then
    log_error "CRITICAL: Credentials directly exposed in docker-compose.yml"
else
    log_success "Docker-compose using environment variables properly"
fi

# Check for .env files in git
if git ls-files | grep -E "\.env$" 2>/dev/null; then
    log_error "CRITICAL: .env files are tracked in git - secrets may be exposed"
else
    log_success "No .env files tracked in git"
fi

echo
echo "🔄 2. ASYNC VIOLATIONS CHECK"
echo "=========================="

# Check for blocking operations in async functions
echo "Scanning for async violations in Python code..."

# Check for requests.get/post in async functions
if grep -r "async def" . --include="*.py" | while read -r line; do
    file=$(echo "$line" | cut -d: -f1)
    # Get the async function and check next 20 lines for blocking calls
    if grep -A 20 "async def" "$file" | grep -E "(requests\.(get|post)|time\.sleep|sync_)" >/dev/null 2>&1; then
        echo "$file"
    fi
done | head -1 | read -r blocking_file; then
    if [ -n "$blocking_file" ]; then
        log_error "CRITICAL: Blocking operations found in async functions in $blocking_file"
    fi
else
    log_success "No obvious blocking operations in async functions"
fi

# Check for missing await keywords
echo "Checking for missing await keywords..."
if grep -rE "async def.*\(" . --include="*.py" -A 10 | grep -E "(redis_client\.|database\.|http_)" | grep -v "await" >/dev/null 2>&1; then
    log_warning "Potential missing await keywords found - manual review recommended"
else
    log_success "Async patterns look correct"
fi

# Check for thread pool usage for blocking operations
if grep -r "ThreadPoolExecutor\|run_in_executor" . --include="*.py" >/dev/null 2>&1; then
    log_success "Thread pools found for handling blocking operations"
else
    log_warning "No thread pools found - ensure blocking operations are handled properly"
fi

echo
echo "🏛️ 3. DATABASE TRANSACTION MANAGEMENT"
echo "==================================="

# Check for transaction usage
echo "Checking database transaction patterns..."

if grep -r "transaction\(\)\|BEGIN.*COMMIT" . --include="*.py" >/dev/null 2>&1; then
    log_success "Database transactions are being used"
else
    log_error "CRITICAL: No database transactions found - data consistency at risk"
fi

# Check for connection pooling
if grep -r "create_pool\|connection_pool" . --include="*.py" >/dev/null 2>&1; then
    log_success "Database connection pooling implemented"
else
    log_error "CRITICAL: No connection pooling found - performance and reliability issues"
fi

# Check for proper error handling in database operations
if grep -r "try:.*except.*Exception" . --include="*.py" | grep -E "(database|postgres|redis)" >/dev/null 2>&1; then
    log_success "Database error handling patterns found"
else
    log_warning "Database error handling may be insufficient"
fi

# Check for ACID compliance patterns
if grep -r "ISOLATION_LEVEL\|SERIALIZABLE\|READ_COMMITTED" . --include="*.py" >/dev/null 2>&1; then
    log_success "Transaction isolation levels configured"
else
    log_warning "Transaction isolation levels not explicitly configured"
fi

echo
echo "🔒 4. INFRASTRUCTURE SECURITY"
echo "=========================="

# Check TLS configuration
echo "Checking TLS configuration..."
if grep -r "TLS_DISABLE.*false\|ssl.*True" infra/ >/dev/null 2>&1; then
    log_success "TLS enabled in configuration"
else
    log_error "CRITICAL: TLS may not be properly enabled"
fi

# Check for security headers
if grep -r "security_opt.*no-new-privileges" infra/ >/dev/null 2>&1; then
    log_success "Container security options configured"
else
    log_warning "Container security hardening may be missing"
fi

# Check for resource limits
if grep -r "limits:" infra/ >/dev/null 2>&1; then
    log_success "Resource limits configured"
else
    log_error "CRITICAL: No resource limits found - DoS risk"
fi

# Check for health checks
if grep -r "healthcheck:" infra/ >/dev/null 2>&1; then
    log_success "Health checks configured"
else
    log_warning "Health checks may be missing"
fi

echo
echo "🔍 5. SECRET MANAGEMENT VALIDATION"
echo "================================"

# Check for Vault integration
if [ -f "infra/secure_config.py" ]; then
    log_success "Secure configuration management module found"
else
    log_error "CRITICAL: No secure configuration management found"
fi

# Check for secret file mounts (Kubernetes style)
if grep -r "/secrets/\|/vault/" infra/ >/dev/null 2>&1; then
    log_success "Secret file mounts configured"
else
    log_warning "Secret file mounts not found - using environment variables"
fi

# Validate environment template exists
if [ -f "infra/.env.production.template" ]; then
    log_success "Production environment template found"
else
    log_error "CRITICAL: No production environment template - deployment guidance missing"
fi

echo
echo "🌐 6. NETWORK SECURITY"
echo "===================="

# Check for network isolation
if grep -r "networks:" infra/ >/dev/null 2>&1; then
    log_success "Docker networks configured for isolation"
else
    log_warning "Network isolation may not be configured"
fi

# Check for exposed ports
EXPOSED_PORTS=$(grep -r "ports:" infra/ | grep -o "[0-9]*:" | wc -l)
if [ "$EXPOSED_PORTS" -gt 10 ]; then
    log_warning "Many ports exposed ($EXPOSED_PORTS) - review necessity"
else
    log_success "Reasonable number of exposed ports ($EXPOSED_PORTS)"
fi

# Check for firewall rules or restrictions
if grep -r "ALLOWED_NETWORKS\|firewall" infra/ >/dev/null 2>&1; then
    log_success "Network access restrictions configured"
else
    log_warning "No network access restrictions found"
fi

echo
echo "⚡ 7. PERFORMANCE & RELIABILITY"
echo "============================="

# Check for circuit breakers
if grep -r "circuit.*breaker\|CircuitBreaker" . --include="*.py" >/dev/null 2>&1; then
    log_success "Circuit breaker patterns found"
else
    log_warning "Circuit breaker patterns not found - reliability at risk"
fi

# Check for rate limiting
if grep -r "rate_limit\|RateLimit" . --include="*.py" >/dev/null 2>&1; then
    log_success "Rate limiting implemented"
else
    log_error "CRITICAL: No rate limiting found - DoS vulnerability"
fi

# Check for retries and timeouts
if grep -r "timeout\|retry\|backoff" . --include="*.py" >/dev/null 2>&1; then
    log_success "Timeout and retry patterns found"
else
    log_warning "Timeout and retry patterns may be insufficient"
fi

echo
echo "📊 8. MONITORING & OBSERVABILITY"
echo "==============================="

# Check for logging configuration
if grep -r "logging\|LOG_LEVEL" . >/dev/null 2>&1; then
    log_success "Logging configuration found"
else
    log_warning "Logging configuration may be insufficient"
fi

# Check for metrics collection
if grep -r "prometheus\|metrics" infra/ >/dev/null 2>&1; then
    log_success "Metrics collection configured"
else
    log_warning "Metrics collection may not be configured"
fi

# Check for alerting
if grep -r "alertmanager\|alert" infra/ >/dev/null 2>&1; then
    log_success "Alerting system configured"
else
    log_warning "Alerting system may not be configured"
fi

echo
echo "🔒 9. COMPLIANCE & AUDIT"
echo "======================="

# Check for audit logging
if grep -r "audit" . --include="*.py" >/dev/null 2>&1; then
    log_success "Audit logging patterns found"
else
    log_warning "Audit logging may be insufficient"
fi

# Check for data retention policies
if grep -r "retention\|cleanup\|expire" . --include="*.py" >/dev/null 2>&1; then
    log_success "Data retention/cleanup patterns found"
else
    log_warning "Data retention policies may be missing"
fi

echo
echo "📋 VALIDATION SUMMARY"
echo "===================="
echo -e "Critical Issues: ${RED}$CRITICAL_ISSUES${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"

if [ "$VALIDATION_FAILED" = true ]; then
    echo
    echo -e "${RED}❌ DEPLOYMENT BLOCKED - CRITICAL SECURITY ISSUES FOUND${NC}"
    echo
    echo "REQUIRED ACTIONS BEFORE DEPLOYMENT:"
    echo "1. Fix all critical security issues listed above"
    echo "2. Implement proper credential management with Vault"
    echo "3. Fix async violations to prevent service deadlocks"
    echo "4. Implement database transaction management"
    echo "5. Configure proper TLS and security headers"
    echo "6. Implement rate limiting and resource controls"
    echo
    echo "Run this script again after fixes to validate."
    echo
    exit 1
else
    if [ "$WARNINGS" -gt 0 ]; then
        echo
        echo -e "${YELLOW}⚠️  DEPLOYMENT ALLOWED WITH WARNINGS${NC}"
        echo
        echo "Consider addressing the warnings for improved security:"
        echo "- Review and implement recommended security enhancements"
        echo "- Add missing monitoring and alerting where applicable"
        echo "- Implement additional hardening measures"
        echo
    else
        echo
        echo -e "${GREEN}✅ ALL SECURITY VALIDATIONS PASSED - DEPLOYMENT APPROVED${NC}"
        echo
    fi
    
    echo "Next steps:"
    echo "1. Copy .env.production.template to .env and configure secrets"
    echo "2. Set up Vault with all required secret paths"
    echo "3. Configure TLS certificates"
    echo "4. Run deployment with: docker-compose --env-file .env up -d"
    echo
    exit 0
fi