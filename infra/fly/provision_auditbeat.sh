#!/bin/bash
set -e

# Auditbeat Provisioning Script for Fly.io VMs
# This script installs and configures Auditbeat for security monitoring

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ELASTIC_VERSION=${ELASTIC_VERSION:-8.11.0}

# Security: Get credentials from environment or Vault (NEVER hardcode)
if command -v vault >/dev/null 2>&1 && [[ -n "$VAULT_ADDR" ]]; then
    # Get from Vault if available
    ELK_ENDPOINT=${ELK_ENDPOINT:-$(vault kv get -field=endpoint secret/elk 2>/dev/null)}
    ELK_USERNAME=${ELK_USERNAME:-$(vault kv get -field=username secret/elk 2>/dev/null)}
    ELK_PASSWORD=${ELK_PASSWORD:-$(vault kv get -field=password secret/elk 2>/dev/null)}
fi

# Fallback to environment variables (must be set externally)
ELK_ENDPOINT=${ELK_ENDPOINT:-""}
ELK_USERNAME=${ELK_USERNAME:-""}
ELK_PASSWORD=${ELK_PASSWORD:-""}

# Validate required credentials
if [[ -z "$ELK_ENDPOINT" || -z "$ELK_USERNAME" || -z "$ELK_PASSWORD" ]]; then
    error "Missing required ELK credentials. Set ELK_ENDPOINT, ELK_USERNAME, ELK_PASSWORD or configure Vault"
fi

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1" >&2
    exit 1
}

check_requirements() {
    log "Checking system requirements..."
    
    # Check if running on supported OS
    if [[ ! -f /etc/os-release ]]; then
        error "Unsupported operating system"
    fi
    
    . /etc/os-release
    if [[ "$ID" != "ubuntu" && "$ID" != "debian" ]]; then
        error "This script supports Ubuntu/Debian only"
    fi
    
    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root"
    fi
    
    log "System requirements met"
}

install_auditbeat() {
    log "Installing Auditbeat ${ELASTIC_VERSION}..."
    
    # Download and install Elastic's GPG key
    wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | gpg --dearmor -o /usr/share/keyrings/elastic-keyring.gpg
    
    # Add Elastic repository
    echo "deb [signed-by=/usr/share/keyrings/elastic-keyring.gpg] https://artifacts.elastic.co/packages/8.x/apt stable main" | tee /etc/apt/sources.list.d/elastic-8.x.list
    
    # Update package lists
    apt-get update
    
    # Install Auditbeat
    apt-get install -y auditbeat=${ELASTIC_VERSION}
    
    # Hold the package to prevent automatic updates
    apt-mark hold auditbeat
    
    log "Auditbeat ${ELASTIC_VERSION} installed successfully"
}

configure_auditbeat() {
    log "Configuring Auditbeat..."
    
    # Backup original config
    cp /etc/auditbeat/auditbeat.yml /etc/auditbeat/auditbeat.yml.backup
    
    # Create Auditbeat configuration
    cat > /etc/auditbeat/auditbeat.yml << EOF
# Auditbeat Configuration for Fly.io VM Security Monitoring

auditbeat.config.modules:
  path: \${path.config}/modules.d/*.yml
  reload.enabled: false

auditbeat.modules:
- module: auditd
  audit_rule_files: [ '\${path.config}/audit.rules.d/*.conf' ]
  audit_rules: |
    # System call auditing
    -a always,exit -F arch=b64 -S execve -k exec
    -a always,exit -F arch=b32 -S execve -k exec
    
    # File access monitoring
    -w /etc/passwd -p wa -k identity
    -w /etc/group -p wa -k identity
    -w /etc/shadow -p wa -k identity
    -w /etc/sudoers -p wa -k identity
    
    # Authentication logs
    -w /var/log/auth.log -p wa -k auth
    -w /var/log/secure -p wa -k auth
    
    # Network configuration
    -a always,exit -F arch=b64 -S socket -k network
    -a always,exit -F arch=b32 -S socket -k network
    
    # Docker/container monitoring
    -w /var/lib/docker -p wa -k docker
    -w /usr/bin/docker -p x -k docker
    
    # Application-specific monitoring
    -w /opt/app -p wa -k app_changes
    -w /home/app -p wa -k app_user
    
    # Privilege escalation
    -a always,exit -F arch=b64 -S setuid -S setgid -k privilege_escalation
    -a always,exit -F arch=b32 -S setuid -S setgid -k privilege_escalation

- module: file_integrity
  paths:
  - /bin
  - /usr/bin
  - /sbin
  - /usr/sbin
  - /etc
  - /opt/app
  
- module: system
  datasets:
    - package
    - host
    - login
    - process
    - socket
    - user
  period: 10s

# Output configuration
output.elasticsearch:
  hosts: ["${ELK_ENDPOINT}"]
  username: "${ELK_USERNAME}"
  password: "${ELK_PASSWORD}"
  index: "auditbeat-%{[agent.version]}-%{+yyyy.MM.dd}"

# Logging configuration
logging.level: info
logging.to_files: true
logging.files:
  path: /var/log/auditbeat
  name: auditbeat
  keepfiles: 7
  permissions: 0644

# Monitoring
monitoring.enabled: true

# Processors
processors:
  - add_host_metadata:
      when.not.contains.tags: forwarded
  - add_cloud_metadata: ~
  - add_docker_metadata: ~
  - add_kubernetes_metadata: ~

# Tags and fields
tags: ["fly-io", "security", "audit"]
fields:
  environment: "${FLY_REGION:-unknown}"
  app_name: "${FLY_APP_NAME:-unknown}"
  machine_id: "${FLY_MACHINE_ID:-unknown}"

# Setup
setup.template.settings:
  index.number_of_shards: 1
  index.codec: best_compression

setup.ilm.enabled: true
setup.ilm.rollover_alias: "auditbeat"
setup.ilm.pattern: "auditbeat-*"
setup.ilm.policy: "auditbeat-policy"
EOF

    log "Auditbeat configuration created"
}

create_audit_rules() {
    log "Creating audit rules..."
    
    mkdir -p /etc/auditbeat/audit.rules.d
    
    # Create comprehensive audit rules
    cat > /etc/auditbeat/audit.rules.d/security.conf << 'EOF'
# Security-focused audit rules for Fly.io applications

# System integrity
-w /etc/hosts -p wa -k network_config
-w /etc/resolv.conf -p wa -k network_config
-w /etc/hostname -p wa -k system_config

# SSH monitoring
-w /etc/ssh/sshd_config -p wa -k ssh_config
-w /home/.ssh -p wa -k ssh_keys
-w /root/.ssh -p wa -k ssh_keys

# Cron and scheduled tasks
-w /etc/cron.allow -p wa -k cron
-w /etc/cron.deny -p wa -k cron
-w /etc/cron.d/ -p wa -k cron
-w /etc/cron.daily/ -p wa -k cron
-w /etc/cron.hourly/ -p wa -k cron
-w /etc/cron.monthly/ -p wa -k cron
-w /etc/cron.weekly/ -p wa -k cron
-w /var/spool/cron/crontabs/ -p wa -k cron

# System startup
-w /etc/systemd/ -p wa -k systemd
-w /lib/systemd/ -p wa -k systemd

# Application logs
-w /var/log/ -p wa -k app_logs
-w /opt/app/logs/ -p wa -k app_logs

# Package management
-w /usr/bin/apt-get -p x -k package_mgmt
-w /usr/bin/dpkg -p x -k package_mgmt
-w /usr/bin/pip -p x -k package_mgmt
-w /usr/bin/pip3 -p x -k package_mgmt

# Container runtime
-w /usr/bin/containerd -p x -k container
-w /usr/bin/runc -p x -k container

# Network utilities
-w /usr/bin/wget -p x -k network_tools
-w /usr/bin/curl -p x -k network_tools
-w /usr/bin/nc -p x -k network_tools
-w /usr/bin/nmap -p x -k network_tools
EOF

    log "Audit rules created"
}

setup_systemd_service() {
    log "Setting up systemd service..."
    
    # Create systemd override directory
    mkdir -p /etc/systemd/system/auditbeat.service.d
    
    # Create override configuration
    cat > /etc/systemd/system/auditbeat.service.d/override.conf << 'EOF'
[Unit]
Description=Auditbeat Security Monitor for Fly.io
Documentation=https://www.elastic.co/beats/auditbeat
Wants=network-online.target
After=network-online.target

[Service]
Environment=BEATS_CONFIG_PATH=/etc/auditbeat
Environment=BEATS_LOG_PATH=/var/log/auditbeat
Environment=BEATS_DATA_PATH=/var/lib/auditbeat
ExecStartPre=/usr/share/auditbeat/bin/auditbeat test config
ExecStart=/usr/share/auditbeat/bin/auditbeat -c /etc/auditbeat/auditbeat.yml
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal
SyslogIdentifier=auditbeat

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/auditbeat /var/lib/auditbeat

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd
    systemctl daemon-reload
    
    log "Systemd service configured"
}

setup_log_rotation() {
    log "Setting up log rotation..."
    
    cat > /etc/logrotate.d/auditbeat << 'EOF'
/var/log/auditbeat/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
    postrotate
        systemctl reload auditbeat > /dev/null 2>&1 || true
    endscript
}
EOF

    log "Log rotation configured"
}

test_configuration() {
    log "Testing Auditbeat configuration..."
    
    # Test configuration syntax
    /usr/share/auditbeat/bin/auditbeat test config -c /etc/auditbeat/auditbeat.yml
    
    if [[ $? -eq 0 ]]; then
        log "Configuration test passed"
    else
        error "Configuration test failed"
    fi
}

start_services() {
    log "Starting Auditbeat service..."
    
    # Enable and start auditbeat
    systemctl enable auditbeat
    systemctl start auditbeat
    
    # Check status
    sleep 5
    if systemctl is-active --quiet auditbeat; then
        log "Auditbeat started successfully"
    else
        error "Failed to start Auditbeat"
    fi
}

create_health_check() {
    log "Creating health check script..."
    
    cat > /usr/local/bin/auditbeat-health.sh << 'EOF'
#!/bin/bash
# Auditbeat health check script

SERVICE_STATUS=$(systemctl is-active auditbeat)
LOG_ERRORS=$(journalctl -u auditbeat --since="5 minutes ago" | grep -i error | wc -l)

if [[ "$SERVICE_STATUS" != "active" ]]; then
    echo "CRITICAL: Auditbeat service is not running"
    exit 2
fi

if [[ $LOG_ERRORS -gt 5 ]]; then
    echo "WARNING: $LOG_ERRORS errors in the last 5 minutes"
    exit 1
fi

echo "OK: Auditbeat is running normally"
exit 0
EOF

    chmod +x /usr/local/bin/auditbeat-health.sh
    
    log "Health check script created at /usr/local/bin/auditbeat-health.sh"
}

print_summary() {
    log "=== Auditbeat Installation Summary ==="
    log "✅ Auditbeat ${ELASTIC_VERSION} installed and configured"
    log "✅ Security audit rules deployed"
    log "✅ Systemd service enabled and started"
    log "✅ Log rotation configured"
    log "✅ Health check script created"
    log ""
    log "📊 Monitoring Dashboard: ${ELK_ENDPOINT}"
    log "📋 Configuration: /etc/auditbeat/auditbeat.yml"
    log "📝 Logs: /var/log/auditbeat/"
    log "🔍 Health Check: /usr/local/bin/auditbeat-health.sh"
    log ""
    log "🔧 Management Commands:"
    log "  Status: systemctl status auditbeat"
    log "  Restart: systemctl restart auditbeat"
    log "  Logs: journalctl -u auditbeat -f"
    log "  Test: auditbeat test config"
}

main() {
    log "Starting Auditbeat provisioning for Fly.io VM..."
    
    check_requirements
    install_auditbeat
    configure_auditbeat
    create_audit_rules
    setup_systemd_service
    setup_log_rotation
    test_configuration
    start_services
    create_health_check
    print_summary
    
    log "🎉 Auditbeat provisioning completed successfully!"
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi