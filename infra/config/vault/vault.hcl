# HashiCorp Vault Production Configuration
# This replaces the insecure -dev mode configuration

# Storage Backend - File storage for single-node deployment
# For production clusters, consider Consul or cloud-native backends
storage "file" {
  path = "/vault/data"
}

# Network listener configuration
listener "tcp" {
  address       = "0.0.0.0:8200"
  tls_cert_file = "/vault/tls/vault.crt"
  tls_key_file  = "/vault/tls/vault.key"
  tls_disable   = false
  
  # Security headers
  tls_min_version = "tls12"
  tls_cipher_suites = "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256,TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384"
  
  # Client certificate authentication (optional)
  tls_require_and_verify_client_cert = false
  tls_client_ca_file = "/vault/tls/ca.crt"
}

# Disable mlock for containers (handled by cap_add: IPC_LOCK)
disable_mlock = true

# API address for inter-node communication
api_addr = "https://127.0.0.1:8200"

# Cluster address (for HA deployments)
cluster_addr = "https://127.0.0.1:8201"

# UI configuration
ui = true

# Logging configuration
log_level = "INFO"
log_format = "json"

# Plugin directory
plugin_directory = "/vault/plugins"

# Maximum lease TTL
max_lease_ttl = "8760h"  # 1 year
default_lease_ttl = "24h"  # 1 day

# Enable raw endpoint (disable in high-security environments)
raw_storage_endpoint = false

# Telemetry configuration
telemetry {
  prometheus_retention_time = "30s"
  disable_hostname = true
}

# Entropy configuration for better random number generation
entropy "seal" {
  mode = "augmentation"
}

# Seal configuration (auto-unseal with cloud KMS in production)
# Uncomment and configure for cloud-based auto-unsealing:

# seal "awskms" {
#   region = "us-east-1" 
#   kms_key_id = "alias/vault-unseal-key"
# }

# seal "azurekeyvault" {
#   tenant_id      = "46646709-b63e-4747-be42-516edeaf1e14"
#   client_id      = "03dc33fc-16d9-4b77-8152-3ec568f8af6e"
#   client_secret  = "REPLACE_WITH_CLIENT_SECRET"
#   vault_name     = "hc-vault"
#   key_name       = "vault_key"
# }

# seal "gcpckms" {
#   project    = "vault-project"
#   region     = "global"
#   key_ring   = "vault-keyring"
#   crypto_key = "vault-key"
# }

# Cache configuration
cache {
  # Use in-memory cache for performance
  type = "memory"
  size = "128MB"
}

# Performance configuration
performance {
  # Maximum number of concurrent requests
  max_request_size = "32MB"
  
  # Request timeout
  max_request_duration = "90s"
  
  # Number of workers
  num_workers = 4
}

# Enterprise features (if using Vault Enterprise)
# license_path = "/vault/license/vault.hclic"

# Audit logging
audit {
  type = "file"
  options {
    file_path = "/vault/logs/audit.log"
    log_raw = false
    format = "json"
  }
}

# High availability configuration (for cluster deployments)
ha_storage "consul" {
  address = "127.0.0.1:8500"
  path    = "vault/"
  
  # Consul authentication
  scheme = "https"
  tls_ca_file = "/vault/tls/consul-ca.crt"
  tls_cert_file = "/vault/tls/consul.crt" 
  tls_key_file = "/vault/tls/consul.key"
}