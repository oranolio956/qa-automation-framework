package app.pii

import rego.v1

# PII Protection and Data Privacy policies

# Define PII fields that require special handling
pii_fields := [
    "email",
    "phone", 
    "address",
    "ssn",
    "payment_info",
    "personal_data"
]

# Check if request involves PII data
involves_pii(path) if {
    field := pii_fields[_]
    contains(path, field)
}

involves_pii(path) if {
    # Check query parameters for PII
    contains(path, "personal")
}

# PII access control
allow_pii_access(user_id, customer_id, path) if {
    # Users can access their own PII
    user_id == customer_id
}

allow_pii_access(user_id, customer_id, path) if {
    # Admin users can access PII with audit logging
    user_id == "admin"
    log_pii_access(user_id, customer_id, path)
}

allow_pii_access(user_id, customer_id, path) if {
    # Support users can access limited PII
    user_id == "support"
    limited_pii_path(path)
}

# Define limited PII paths for support
limited_pii_path(path) if {
    # Support can only access order-related PII, not payment info
    startswith(path, "/orders")
    not contains(path, "payment")
    not contains(path, "ssn")
}

# Data retention compliance
retention_period_days := 90

data_retention_compliant(timestamp) if {
    # Check if data is within retention period
    now := time.now_ns()
    parsed_time := time.parse_rfc3339_ns(timestamp)
    days_old := (now - parsed_time) / (24 * 60 * 60 * 1000000000)
    days_old <= retention_period_days
}

# GDPR compliance checks
gdpr_compliant(user_id, method, path) if {
    # Right to access - users can read their own data
    method == "GET"
    user_owns_data(user_id, path)
}

gdpr_compliant(user_id, method, path) if {
    # Right to deletion - users can delete their own data
    method == "DELETE"
    user_owns_data(user_id, path)
}

gdpr_compliant(user_id, method, path) if {
    # Right to rectification - users can update their own data
    method in ["PUT", "PATCH"]
    user_owns_data(user_id, path)
}

# Check if user owns the data being accessed
user_owns_data(user_id, path) if {
    # Extract order ID from path for ownership verification
    regex.match("^/orders/([A-Za-z0-9-]+)", path)
    order_id := regex.find_n("^/orders/([A-Za-z0-9-]+)", path, 1)[0][1]
    
    # Query external data source for ownership verification
    # This would integrate with your database/Redis to verify ownership
    http.send({
        "method": "GET",
        "url": sprintf("http://localhost:8000/internal/orders/%s/owner", [order_id]),
        "headers": {"X-Internal-Auth": "opa-verification"}
    }).body.customer_id == input.customer_id
}

# Fallback ownership check for non-order paths
user_owns_data(user_id, path) if {
    # For customer profile paths, verify user matches
    regex.match("^/customers/([A-Za-z0-9-]+)", path)
    customer_id := regex.find_n("^/customers/([A-Za-z0-9-]+)", path, 1)[0][1]
    customer_id == input.customer_id
}

# Admin override for ownership (with audit logging)
user_owns_data(user_id, path) if {
    input.user_id == "admin"
    # This should trigger additional audit logging in the application
    true
}

# Audit logging for PII access
log_pii_access(user_id, customer_id, path) if {
    # This would log to an external audit system
    # For now, just ensure the function exists
    true
}

# Data anonymization requirements
requires_anonymization(field) if {
    field in pii_fields
}

# Encryption requirements for PII
requires_encryption(field) if {
    field in ["ssn", "payment_info", "personal_data"]
}