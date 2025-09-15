package app.rbac

import rego.v1

# Role-Based Access Control policies

# Define user roles (in production, this would come from external data)
user_roles := {
    "admin": ["admin"],
    "customer": ["customer"],
    "support": ["support", "customer"]
}

# Define role permissions
role_permissions := {
    "admin": {
        "orders": ["create", "read", "update", "delete", "cancel"],
        "customers": ["read", "update"],
        "system": ["health", "metrics", "webhook"]
    },
    "customer": {
        "orders": ["create", "read", "cancel"],
        "own_data": ["read", "update"]
    },
    "support": {
        "orders": ["read", "update"],
        "customers": ["read"]
    }
}

# Check if user has specific permission
has_permission(user_id, resource, action) if {
    roles := user_roles[user_id]
    role := roles[_]
    permissions := role_permissions[role][resource]
    action in permissions
}

# Map HTTP methods to actions
method_to_action := {
    "GET": "read",
    "POST": "create", 
    "PUT": "update",
    "DELETE": "delete",
    "PATCH": "update"
}

# Map paths to resources
path_to_resource(path) := "orders" if {
    startswith(path, "/orders")
}

path_to_resource(path) := "customers" if {
    startswith(path, "/customers")
}

path_to_resource(path) := "system" if {
    path in ["/health", "/metrics", "/webhook"]
}

# Main authorization rule using RBAC
allow_rbac(user_id, method, path) if {
    resource := path_to_resource(path)
    action := method_to_action[method]
    has_permission(user_id, resource, action)
}

# Special case for order cancellation
allow_rbac(user_id, "POST", path) if {
    endswith(path, "/cancel")
    has_permission(user_id, "orders", "cancel")
}