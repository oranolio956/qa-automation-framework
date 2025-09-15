#!/bin/bash

# Phase 13: Deployment and Maintenance Automation
# Production-ready deployment script with comprehensive automation

set -euo pipefail

# Configuration
PROJECT_NAME="telegram-engagement-bot"
VERSION="v2.0.0"
DOCKER_REGISTRY="your-registry.com"
K8S_NAMESPACE="telegram-engagement"
BACKUP_RETENTION_DAYS=30
HEALTH_CHECK_TIMEOUT=300

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    local missing_tools=()
    
    for tool in docker docker-compose kubectl helm node npm; do
        if ! command -v $tool &> /dev/null; then
            missing_tools+=($tool)
        fi
    done
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        error "Missing required tools: ${missing_tools[*]}"
        error "Please install the missing tools and try again."
        exit 1
    fi
    
    success "All prerequisites check passed"
}

# Environment validation
validate_environment() {
    log "Validating environment configuration..."
    
    if [ ! -f ".env.production" ]; then
        error "Environment file .env.production not found"
        exit 1
    fi
    
    # Load environment variables
    source .env.production
    
    # Check required variables
    local required_vars=(
        "BOT_TOKEN"
        "MONGODB_PASSWORD"
        "REDIS_PASSWORD"
        "JWT_SECRET"
        "ENCRYPTION_KEY"
        "HASH_SALT"
    )
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    success "Environment validation passed"
}

# Build Docker images
build_images() {
    log "Building Docker images..."
    
    # Build main application
    docker build -t ${PROJECT_NAME}:${VERSION} -f ./phase13-autonomous-system/telegram-bot/Dockerfile ./phase13-autonomous-system/telegram-bot/
    docker tag ${PROJECT_NAME}:${VERSION} ${PROJECT_NAME}:latest
    
    # Build engagement engine
    docker build -t engagement-engine:${VERSION} -f ./phase13-autonomous-system/engagement-engine/Dockerfile ./phase13-autonomous-system/engagement-engine/
    docker tag engagement-engine:${VERSION} engagement-engine:latest
    
    # Build supporting services
    build_supporting_services
    
    success "Docker images built successfully"
}

# Build supporting services
build_supporting_services() {
    log "Building supporting services..."
    
    # Health checker
    create_health_checker_dockerfile
    docker build -t health-checker:${VERSION} -f ./health-checker/Dockerfile ./health-checker/
    
    # Backup service
    create_backup_service_dockerfile
    docker build -t backup-service:${VERSION} -f ./backup/Dockerfile ./backup/
    
    # Compliance monitor
    create_compliance_service_dockerfile
    docker build -t compliance-monitor:${VERSION} -f ./compliance/Dockerfile ./compliance/
    
    success "Supporting services built"
}

# Create health checker service
create_health_checker_dockerfile() {
    mkdir -p health-checker
    
    cat > health-checker/Dockerfile << 'EOF'
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
EXPOSE 8090
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD node healthcheck.js
USER node
CMD ["node", "server.js"]
EOF

    cat > health-checker/package.json << 'EOF'
{
  "name": "health-checker",
  "version": "1.0.0",
  "main": "server.js",
  "dependencies": {
    "express": "^4.18.2",
    "axios": "^1.6.2",
    "node-cron": "^3.0.3"
  }
}
EOF

    cat > health-checker/server.js << 'EOF'
const express = require('express');
const axios = require('axios');
const cron = require('node-cron');

const app = express();
const port = process.env.PORT || 8090;

const services = [
    { name: 'telegram-bot', url: 'http://telegram-bot:3000/health', critical: true },
    { name: 'redis', url: 'http://redis:6379', critical: true },
    { name: 'mongodb', url: 'http://mongodb:27017', critical: true },
    { name: 'grafana', url: 'http://grafana:3000/api/health', critical: false },
    { name: 'prometheus', url: 'http://prometheus:9090/-/healthy', critical: false }
];

let lastHealthCheck = {};

async function checkService(service) {
    try {
        const response = await axios.get(service.url, { timeout: 10000 });
        return { 
            name: service.name, 
            status: 'healthy', 
            responseTime: response.duration,
            statusCode: response.status 
        };
    } catch (error) {
        return { 
            name: service.name, 
            status: 'unhealthy', 
            error: error.message,
            critical: service.critical
        };
    }
}

async function performHealthCheck() {
    const results = await Promise.all(services.map(checkService));
    lastHealthCheck = {
        timestamp: new Date().toISOString(),
        results,
        overallStatus: results.every(r => r.status === 'healthy') ? 'healthy' : 'degraded'
    };
    
    // Send alerts for critical service failures
    const criticalFailures = results.filter(r => r.status === 'unhealthy' && r.critical);
    if (criticalFailures.length > 0 && process.env.ALERT_WEBHOOK) {
        await sendAlert(criticalFailures);
    }
    
    console.log(`Health check completed: ${lastHealthCheck.overallStatus}`);
}

async function sendAlert(failures) {
    try {
        await axios.post(process.env.ALERT_WEBHOOK, {
            alert: 'Critical Service Failure',
            failures: failures.map(f => ({ name: f.name, error: f.error })),
            timestamp: new Date().toISOString()
        });
    } catch (error) {
        console.error('Failed to send alert:', error.message);
    }
}

app.get('/health', (req, res) => {
    res.json(lastHealthCheck);
});

// Schedule health checks every minute
cron.schedule('* * * * *', performHealthCheck);

// Initial health check
performHealthCheck();

app.listen(port, () => {
    console.log(`Health checker running on port ${port}`);
});
EOF
}

# Create backup service
create_backup_service_dockerfile() {
    mkdir -p backup
    
    cat > backup/Dockerfile << 'EOF'
FROM node:18-alpine
RUN apk add --no-cache mongodb-tools redis
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
USER node
CMD ["node", "backup.js"]
EOF

    cat > backup/package.json << 'EOF'
{
  "name": "backup-service",
  "version": "1.0.0",
  "main": "backup.js",
  "dependencies": {
    "node-cron": "^3.0.3",
    "aws-sdk": "^2.1502.0",
    "tar": "^6.2.0"
  }
}
EOF

    cat > backup/backup.js << 'EOF'
const cron = require('node-cron');
const { exec } = require('child_process');
const AWS = require('aws-sdk');
const fs = require('fs');
const path = require('path');

const s3 = new AWS.S3({
    accessKeyId: process.env.AWS_ACCESS_KEY_ID,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
    region: process.env.AWS_REGION
});

async function backupMongoDB() {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const backupPath = `/tmp/mongodb-backup-${timestamp}`;
    
    return new Promise((resolve, reject) => {
        exec(`mongodump --uri="${process.env.MONGODB_URL}" --out=${backupPath}`, (error, stdout, stderr) => {
            if (error) {
                reject(error);
            } else {
                resolve(backupPath);
            }
        });
    });
}

async function backupRedis() {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const backupPath = `/tmp/redis-backup-${timestamp}.rdb`;
    
    return new Promise((resolve, reject) => {
        exec(`redis-cli --rdb ${backupPath}`, (error, stdout, stderr) => {
            if (error) {
                reject(error);
            } else {
                resolve(backupPath);
            }
        });
    });
}

async function uploadToS3(filePath, key) {
    const fileStream = fs.createReadStream(filePath);
    
    const uploadParams = {
        Bucket: process.env.S3_BUCKET,
        Key: key,
        Body: fileStream,
        ServerSideEncryption: 'AES256'
    };
    
    return s3.upload(uploadParams).promise();
}

async function performBackup() {
    try {
        console.log('Starting backup process...');
        
        // Backup MongoDB
        const mongoBackupPath = await backupMongoDB();
        const mongoS3Key = `mongodb/${path.basename(mongoBackupPath)}.tar.gz`;
        
        // Compress and upload MongoDB backup
        exec(`tar -czf ${mongoBackupPath}.tar.gz -C ${path.dirname(mongoBackupPath)} ${path.basename(mongoBackupPath)}`, async (error) => {
            if (!error) {
                await uploadToS3(`${mongoBackupPath}.tar.gz`, mongoS3Key);
                console.log(`MongoDB backup uploaded: ${mongoS3Key}`);
            }
        });
        
        // Backup Redis
        const redisBackupPath = await backupRedis();
        const redisS3Key = `redis/${path.basename(redisBackupPath)}`;
        await uploadToS3(redisBackupPath, redisS3Key);
        console.log(`Redis backup uploaded: ${redisS3Key}`);
        
        // Cleanup old backups
        await cleanupOldBackups();
        
        console.log('Backup process completed successfully');
    } catch (error) {
        console.error('Backup failed:', error);
    }
}

async function cleanupOldBackups() {
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - parseInt(process.env.BACKUP_RETENTION_DAYS || '30'));
    
    // List and delete old backups from S3
    const listParams = { Bucket: process.env.S3_BUCKET };
    const objects = await s3.listObjects(listParams).promise();
    
    const oldObjects = objects.Contents.filter(obj => new Date(obj.LastModified) < cutoffDate);
    
    if (oldObjects.length > 0) {
        const deleteParams = {
            Bucket: process.env.S3_BUCKET,
            Delete: {
                Objects: oldObjects.map(obj => ({ Key: obj.Key }))
            }
        };
        
        await s3.deleteObjects(deleteParams).promise();
        console.log(`Cleaned up ${oldObjects.length} old backups`);
    }
}

// Schedule daily backups at 2 AM
cron.schedule('0 2 * * *', performBackup);

console.log('Backup service started. Scheduled for daily execution at 2 AM UTC.');

// Perform initial backup
if (process.argv.includes('--immediate')) {
    performBackup();
}
EOF
}

# Create compliance monitoring service
create_compliance_service_dockerfile() {
    mkdir -p compliance
    
    cat > compliance/Dockerfile << 'EOF'
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
USER node
CMD ["node", "compliance.js"]
EOF

    cat > compliance/package.json << 'EOF'
{
  "name": "compliance-monitor",
  "version": "1.0.0",
  "main": "compliance.js",
  "dependencies": {
    "node-cron": "^3.0.3",
    "mongodb": "^6.3.0",
    "redis": "^4.6.10"
  }
}
EOF

    cat > compliance/compliance.js << 'EOF'
const cron = require('node-cron');
const { MongoClient } = require('mongodb');
const Redis = require('redis');

class ComplianceMonitor {
    constructor() {
        this.mongoClient = new MongoClient(process.env.MONGODB_URL);
        this.redisClient = Redis.createClient({ url: process.env.REDIS_URL });
    }

    async initialize() {
        await this.mongoClient.connect();
        await this.redisClient.connect();
        console.log('Compliance monitor initialized');
    }

    async generateGDPRReport() {
        console.log('Generating GDPR compliance report...');
        
        const db = this.mongoClient.db();
        const auditCollection = db.collection('audit_logs');
        
        const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
        
        const report = {
            reportType: 'GDPR',
            generatedAt: new Date().toISOString(),
            period: {
                from: thirtyDaysAgo.toISOString(),
                to: new Date().toISOString()
            },
            metrics: {
                totalDataSubjects: await this.getUniqueUsersCount(thirtyDaysAgo),
                dataAccessRequests: await auditCollection.countDocuments({
                    action: 'data_access_request',
                    timestamp: { $gte: thirtyDaysAgo }
                }),
                dataDeletionRequests: await auditCollection.countDocuments({
                    action: 'data_deletion_request',
                    timestamp: { $gte: thirtyDaysAgo }
                }),
                consentGiven: await auditCollection.countDocuments({
                    action: 'consent_given',
                    timestamp: { $gte: thirtyDaysAgo }
                }),
                consentWithdrawn: await auditCollection.countDocuments({
                    action: 'consent_withdrawn',
                    timestamp: { $gte: thirtyDaysAgo }
                })
            },
            violations: await this.checkGDPRViolations(thirtyDaysAgo),
            recommendations: []
        };
        
        // Store report
        await db.collection('compliance_reports').insertOne(report);
        
        console.log('GDPR compliance report generated');
        return report;
    }

    async getUniqueUsersCount(since) {
        const db = this.mongoClient.db();
        const pipeline = [
            { $match: { timestamp: { $gte: since } } },
            { $group: { _id: '$userId' } },
            { $count: 'uniqueUsers' }
        ];
        
        const result = await db.collection('audit_logs').aggregate(pipeline).toArray();
        return result.length > 0 ? result[0].uniqueUsers : 0;
    }

    async checkGDPRViolations(since) {
        const violations = [];
        
        // Check for data retention violations
        const retentionDays = parseInt(process.env.GDPR_RETENTION_DAYS || '1095');
        const retentionCutoff = new Date(Date.now() - retentionDays * 24 * 60 * 60 * 1000);
        
        const oldRecords = await this.mongoClient.db().collection('users').countDocuments({
            createdAt: { $lt: retentionCutoff },
            deletedAt: { $exists: false }
        });
        
        if (oldRecords > 0) {
            violations.push({
                type: 'data_retention_violation',
                severity: 'high',
                count: oldRecords,
                description: 'Personal data retained beyond GDPR limits'
            });
        }
        
        return violations;
    }

    async performDataCleanup() {
        console.log('Performing automated data cleanup...');
        
        const retentionDays = parseInt(process.env.AUDIT_RETENTION_DAYS || '365');
        const cutoffDate = new Date(Date.now() - retentionDays * 24 * 60 * 60 * 1000);
        
        // Clean old audit logs
        const auditResult = await this.mongoClient.db().collection('audit_logs').deleteMany({
            timestamp: { $lt: cutoffDate }
        });
        
        // Clean old Redis keys
        const keys = await this.redisClient.keys('audit:*');
        let redisCleanupCount = 0;
        
        for (const key of keys) {
            const ttl = await this.redisClient.ttl(key);
            if (ttl <= 0) {
                await this.redisClient.del(key);
                redisCleanupCount++;
            }
        }
        
        console.log(`Cleanup completed: ${auditResult.deletedCount} MongoDB records, ${redisCleanupCount} Redis keys`);
    }

    async monitorDataProcessing() {
        // Monitor ongoing data processing activities
        const activeProcessing = await this.redisClient.keys('processing:*');
        
        for (const key of activeProcessing) {
            const data = await this.redisClient.get(key);
            const processing = JSON.parse(data);
            
            // Check if processing has consent
            if (!processing.hasConsent) {
                console.warn(`Data processing without consent detected: ${key}`);
                // Log compliance violation
                await this.logComplianceEvent('consent_violation', {
                    processingKey: key,
                    details: processing
                });
            }
        }
    }

    async logComplianceEvent(eventType, details) {
        const event = {
            eventType,
            details,
            timestamp: new Date().toISOString(),
            severity: this.getEventSeverity(eventType)
        };
        
        await this.mongoClient.db().collection('compliance_events').insertOne(event);
    }

    getEventSeverity(eventType) {
        const severityMap = {
            'consent_violation': 'critical',
            'data_retention_violation': 'high',
            'unauthorized_access': 'critical',
            'data_export': 'medium'
        };
        
        return severityMap[eventType] || 'low';
    }
}

async function main() {
    const monitor = new ComplianceMonitor();
    await monitor.initialize();
    
    // Schedule compliance reports (weekly)
    cron.schedule('0 2 * * 0', async () => {
        await monitor.generateGDPRReport();
    });
    
    // Schedule data cleanup (daily)
    cron.schedule('0 3 * * *', async () => {
        await monitor.performDataCleanup();
    });
    
    // Schedule data processing monitoring (every hour)
    cron.schedule('0 * * * *', async () => {
        await monitor.monitorDataProcessing();
    });
    
    console.log('Compliance monitoring scheduled');
    
    // Generate initial report
    await monitor.generateGDPRReport();
}

main().catch(console.error);
EOF
}

# Deploy with Docker Compose
deploy_docker_compose() {
    log "Deploying with Docker Compose..."
    
    # Create necessary directories
    mkdir -p logs mongodb-init nginx/ssl nginx/logs api-docs performance-tests security-reports
    mkdir -p monitoring/{prometheus,grafana/dashboards,grafana/datasources,alertmanager,logstash,filebeat}
    mkdir -p vault-config backups maintenance-logs compliance-reports performance-reports
    
    # Copy environment file
    cp phase13-env-config.env .env.production
    
    # Generate nginx configuration
    create_nginx_config
    
    # Generate monitoring configurations
    create_monitoring_configs
    
    # Deploy the stack
    docker-compose -f phase13-docker-monitoring.yml up -d
    
    # Wait for services to start
    log "Waiting for services to start..."
    sleep 30
    
    # Verify deployment
    verify_deployment
    
    success "Docker Compose deployment completed"
}

# Create NGINX configuration
create_nginx_config() {
    mkdir -p nginx
    
    cat > nginx/nginx.conf << 'EOF'
upstream telegram_bot {
    server telegram-bot:3000;
}

upstream grafana {
    server grafana:3000;
}

server {
    listen 80;
    server_name _;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=dashboard:10m rate=5r/s;
    
    location /webhook/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://telegram_bot;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /api/ {
        limit_req zone=api burst=50 nodelay;
        proxy_pass http://telegram_bot;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /dashboard/ {
        limit_req zone=dashboard burst=10 nodelay;
        proxy_pass http://grafana/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /health {
        proxy_pass http://telegram_bot;
        access_log off;
    }
}
EOF
}

# Create monitoring configurations
create_monitoring_configs() {
    # Prometheus configuration
    cat > monitoring/prometheus/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "rules/*.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  - job_name: 'telegram-bot'
    static_configs:
      - targets: ['telegram-bot:9090']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

  - job_name: 'mongodb'
    static_configs:
      - targets: ['mongodb:27017']
EOF

    # Grafana datasource configuration
    mkdir -p monitoring/grafana/datasources
    cat > monitoring/grafana/datasources/prometheus.yml << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF

    # AlertManager configuration
    cat > monitoring/alertmanager/alertmanager.yml << 'EOF'
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@your-domain.com'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
  - name: 'web.hook'
    webhook_configs:
      - url: 'http://notification-service:5000/webhook/alert'
        send_resolved: true

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'dev', 'instance']
EOF

    # Filebeat configuration
    cat > monitoring/filebeat/filebeat.yml << 'EOF'
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/telegram-bot/*.log
  fields:
    service: telegram-bot
  fields_under_root: true

- type: docker
  containers.ids:
    - "*"

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "telegram-bot-%{+yyyy.MM.dd}"

processors:
  - add_host_metadata: ~
  - add_docker_metadata: ~
EOF
}

# Verify deployment
verify_deployment() {
    log "Verifying deployment..."
    
    local services=(
        "telegram-bot:3000/health"
        "grafana:3000/api/health" 
        "prometheus:9090/-/healthy"
        "elasticsearch:9200/_cluster/health"
    )
    
    for service in "${services[@]}"; do
        local name=$(echo $service | cut -d: -f1)
        local endpoint="http://$service"
        
        log "Checking $name..."
        
        local retries=0
        local max_retries=10
        
        while [ $retries -lt $max_retries ]; do
            if curl -f -s "$endpoint" > /dev/null 2>&1; then
                success "$name is healthy"
                break
            else
                warning "$name not ready, retrying... ($((retries + 1))/$max_retries)"
                sleep 10
                ((retries++))
            fi
        done
        
        if [ $retries -eq $max_retries ]; then
            error "$name failed health check"
        fi
    done
}

# Deploy to Kubernetes
deploy_kubernetes() {
    log "Deploying to Kubernetes..."
    
    # Create namespace
    kubectl create namespace $K8S_NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
    
    # Apply configurations
    kubectl apply -f phase13-kubernetes-infrastructure.yaml
    
    # Wait for deployment
    kubectl rollout status deployment/telegram-engagement-bot -n $K8S_NAMESPACE --timeout=600s
    
    # Verify pods are running
    kubectl get pods -n $K8S_NAMESPACE
    
    success "Kubernetes deployment completed"
}

# Run security scan
security_scan() {
    log "Running security scan..."
    
    # Scan Docker images
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
        aquasec/trivy:latest image telegram-engagement-bot:latest \
        --format json --output /tmp/security-report.json
    
    # Check for vulnerabilities
    if [ -f /tmp/security-report.json ]; then
        local critical_vulns=$(jq '.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL") | length' /tmp/security-report.json 2>/dev/null | wc -l)
        
        if [ "$critical_vulns" -gt 0 ]; then
            warning "Found $critical_vulns critical vulnerabilities"
        else
            success "No critical vulnerabilities found"
        fi
    fi
}

# Performance testing
performance_test() {
    log "Running performance tests..."
    
    # Create basic performance test
    mkdir -p performance-tests
    cat > performance-tests/load-test.js << 'EOF'
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  vus: 10, // 10 virtual users
  duration: '30s',
};

export default function () {
  let response = http.get('http://nginx/health');
  check(response, { 'status was 200': (r) => r.status == 200 });
  sleep(1);
}
EOF
    
    # Run performance test
    docker run --rm -i --network="$(basename $PWD)_telegram-network" \
        -v $(pwd)/performance-tests:/scripts \
        loadimpact/k6:latest run /scripts/load-test.js
    
    success "Performance tests completed"
}

# Backup data
backup_data() {
    log "Creating backup..."
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_dir="./backups/$timestamp"
    
    mkdir -p "$backup_dir"
    
    # Backup MongoDB
    docker exec mongodb-primary mongodump --out "/tmp/backup-$timestamp"
    docker cp mongodb-primary:"/tmp/backup-$timestamp" "$backup_dir/mongodb"
    
    # Backup Redis
    docker exec redis-cache redis-cli --rdb "/tmp/backup-$timestamp.rdb"
    docker cp redis-cache:"/tmp/backup-$timestamp.rdb" "$backup_dir/redis.rdb"
    
    # Compress backup
    tar -czf "$backup_dir.tar.gz" -C "./backups" "$timestamp"
    rm -rf "$backup_dir"
    
    success "Backup created: $backup_dir.tar.gz"
}

# Restore from backup
restore_data() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ] || [ ! -f "$backup_file" ]; then
        error "Backup file not found: $backup_file"
        exit 1
    fi
    
    log "Restoring from backup: $backup_file"
    
    # Extract backup
    local restore_dir="/tmp/restore-$(date +%s)"
    mkdir -p "$restore_dir"
    tar -xzf "$backup_file" -C "$restore_dir"
    
    # Stop services
    docker-compose -f phase13-docker-monitoring.yml stop telegram-bot engagement-engine
    
    # Restore MongoDB
    docker cp "$restore_dir/mongodb" mongodb-primary:/tmp/restore
    docker exec mongodb-primary mongorestore --drop /tmp/restore
    
    # Restore Redis
    docker cp "$restore_dir/redis.rdb" redis-cache:/data/dump.rdb
    docker-compose -f phase13-docker-monitoring.yml restart redis
    
    # Start services
    docker-compose -f phase13-docker-monitoring.yml start telegram-bot engagement-engine
    
    # Cleanup
    rm -rf "$restore_dir"
    
    success "Data restored successfully"
}

# Cleanup old data
cleanup() {
    log "Cleaning up old data..."
    
    # Remove old backups
    find ./backups -name "*.tar.gz" -mtime +$BACKUP_RETENTION_DAYS -delete 2>/dev/null || true
    
    # Remove old logs
    find ./logs -name "*.log" -mtime +7 -delete 2>/dev/null || true
    
    # Clean Docker system
    docker system prune -f --volumes
    
    success "Cleanup completed"
}

# Show system status
status() {
    log "System Status"
    echo "=============="
    
    # Docker Compose services
    echo -e "\n${BLUE}Docker Services:${NC}"
    docker-compose -f phase13-docker-monitoring.yml ps
    
    # System resources
    echo -e "\n${BLUE}System Resources:${NC}"
    echo "Memory: $(free -h | grep Mem | awk '{print $3 "/" $2}')"
    echo "Disk: $(df -h / | tail -1 | awk '{print $3 "/" $2 " (" $5 " used)"}')"
    echo "CPU Load: $(uptime | awk -F'load average:' '{print $2}')"
    
    # Service health
    echo -e "\n${BLUE}Service Health:${NC}"
    curl -s http://localhost:8090/health | jq '.' 2>/dev/null || echo "Health checker not available"
}

# Main function
main() {
    local command="${1:-help}"
    
    case "$command" in
        "deploy")
            check_prerequisites
            validate_environment
            build_images
            deploy_docker_compose
            ;;
        "k8s-deploy")
            check_prerequisites
            validate_environment
            build_images
            deploy_kubernetes
            ;;
        "backup")
            backup_data
            ;;
        "restore")
            restore_data "$2"
            ;;
        "security-scan")
            security_scan
            ;;
        "performance-test")
            performance_test
            ;;
        "status")
            status
            ;;
        "cleanup")
            cleanup
            ;;
        "help"|*)
            echo "Usage: $0 {deploy|k8s-deploy|backup|restore|security-scan|performance-test|status|cleanup}"
            echo ""
            echo "Commands:"
            echo "  deploy           - Deploy using Docker Compose"
            echo "  k8s-deploy       - Deploy to Kubernetes"
            echo "  backup           - Create data backup"
            echo "  restore <file>   - Restore from backup"
            echo "  security-scan    - Run security vulnerability scan"
            echo "  performance-test - Run performance tests"
            echo "  status           - Show system status"
            echo "  cleanup          - Clean up old data and containers"
            echo "  help             - Show this help message"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"