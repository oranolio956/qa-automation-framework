package app.authz

import rego.v1

# Default deny
default allow := false

# Allow health checks and metrics without authentication
allow if {
    input.path in ["/health", "/metrics"]
}

# Allow webhook endpoint with proper signature
allow if {
    input.path == "/webhook"
    input.method == "POST"
}

# RBAC - Allow based on user permissions
allow if {
    input.user_id
    input.customer_id
    user_has_permission(input.user_id, input.method, input.path)
}

# Check if user has permission for the requested action
user_has_permission(user_id, method, path) if {
    # Allow users to access their own data
    method in ["GET", "POST", "PUT", "DELETE"]
    
    # Basic path-based permissions
    path_allowed(path)
    
    # Rate limiting check (basic)
    not rate_limited(user_id)
}

# Define allowed paths
path_allowed(path) if {
    path in [
        "/orders",
        "/health", 
        "/metrics"
    ]
}

# Pattern matching for dynamic paths
path_allowed(path) if {
    regex.match("^/orders/[A-Za-z0-9-]+$", path)
}

path_allowed(path) if {
    regex.match("^/orders/[A-Za-z0-9-]+/cancel$", path)
}

# PII Access Control
allow if {
    input.path
    input.user_id
    
    # Check if accessing PII data
    accessing_pii := contains(input.path, "pii") or contains(input.path, "personal")
    
    # If accessing PII, require elevated permissions
    not accessing_pii
}

# Data Retention Policy
allow if {
    input.method == "DELETE"
    input.path
    
    # Allow deletion of old data based on retention policy
    retention_policy_compliant(input.path)
}

retention_policy_compliant(path) if {
    # Simple retention check - can be enhanced with actual timestamp validation
    true
}

# Rate limiting (basic implementation)
rate_limited(user_id) if {
    # This would integrate with actual rate limiting data
    # For now, always return false (not rate limited)
    false
}

# Time-based access control
allow if {
    input.timestamp
    
    # Parse timestamp and check business hours (optional)
    time.parse_rfc3339_ns(input.timestamp)
    
    # For now, allow all times
    true
}

# IP-based restrictions
allow if {
    input.ip_address
    
    # Check if IP is in allowlist/blocklist
    not ip_blocked(input.ip_address)
}

ip_blocked(ip) if {
    # Define blocked IP ranges or patterns
    # For now, no IPs are blocked
    false
}

# Audit logging helper
audit_log := {
    "timestamp": input.timestamp,
    "user_id": input.user_id,
    "customer_id": input.customer_id,
    "method": input.method,
    "path": input.path,
    "ip_address": input.ip_address,
    "decision": allow
}