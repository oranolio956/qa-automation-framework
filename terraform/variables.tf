# Variables for Terraform Configuration

variable "fly_org" {
  description = "Fly.io organization name"
  type        = string
  default     = "snapchat-automation"
}

variable "main_app_machine_count" {
  description = "Number of machines for main application"
  type        = number
  default     = 2
  validation {
    condition     = var.main_app_machine_count >= 1 && var.main_app_machine_count <= 10
    error_message = "Machine count must be between 1 and 10."
  }
}

variable "android_farm_machine_count" {
  description = "Number of machines for Android farm"
  type        = number
  default     = 4
  validation {
    condition     = var.android_farm_machine_count >= 1 && var.android_farm_machine_count <= 20
    error_message = "Android farm machine count must be between 1 and 20."
  }
}

variable "main_app_image" {
  description = "Docker image for main application"
  type        = string
  default     = "snapchat-automation:latest"
}

variable "android_farm_image" {
  description = "Docker image for Android farm"
  type        = string
  default     = "android-automation:latest"
}

# Sensitive Variables (set via environment or terraform.tfvars)
variable "database_url" {
  description = "Database connection URL"
  type        = string
  sensitive   = true
}

variable "redis_url" {
  description = "Redis connection URL"
  type        = string
  sensitive   = true
}

variable "telegram_bot_token" {
  description = "Telegram bot token"
  type        = string
  sensitive   = true
}

variable "jwt_secret" {
  description = "JWT secret key"
  type        = string
  sensitive   = true
}

variable "encryption_key" {
  description = "Encryption key for sensitive data"
  type        = string
  sensitive   = true
}

variable "twilio_auth_token" {
  description = "Twilio authentication token"
  type        = string
  sensitive   = true
  default     = ""
}

variable "brightdata_password" {
  description = "BrightData proxy password"
  type        = string
  sensitive   = true
  default     = ""
}

# Environment Configuration
variable "environment" {
  description = "Environment name (development, staging, production)"
  type        = string
  default     = "production"
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be development, staging, or production."
  }
}

variable "enable_monitoring" {
  description = "Enable monitoring and observability features"
  type        = bool
  default     = true
}

variable "enable_auto_scaling" {
  description = "Enable automatic scaling based on metrics"
  type        = bool
  default     = true
}

# Resource Configuration
variable "main_app_vm_size" {
  description = "VM size for main application"
  type        = string
  default     = "shared-cpu-2x"
  validation {
    condition = contains([
      "shared-cpu-1x", "shared-cpu-2x", "shared-cpu-4x", "shared-cpu-8x",
      "performance-1x", "performance-2x", "performance-4x", "performance-8x"
    ], var.main_app_vm_size)
    error_message = "VM size must be a valid Fly.io machine type."
  }
}

variable "android_farm_vm_size" {
  description = "VM size for Android farm"
  type        = string
  default     = "shared-cpu-4x"
  validation {
    condition = contains([
      "shared-cpu-1x", "shared-cpu-2x", "shared-cpu-4x", "shared-cpu-8x",
      "performance-1x", "performance-2x", "performance-4x", "performance-8x"
    ], var.android_farm_vm_size)
    error_message = "VM size must be a valid Fly.io machine type."
  }
}

variable "android_data_volume_size" {
  description = "Size of Android data volumes in GB"
  type        = number
  default     = 40
  validation {
    condition     = var.android_data_volume_size >= 10 && var.android_data_volume_size <= 500
    error_message = "Volume size must be between 10 and 500 GB."
  }
}

# Networking Configuration
variable "primary_region" {
  description = "Primary deployment region"
  type        = string
  default     = "ord"
}

variable "secondary_regions" {
  description = "Secondary deployment regions"
  type        = list(string)
  default     = ["iad", "lax"]
}

# Health Check Configuration
variable "health_check_interval" {
  description = "Health check interval"
  type        = string
  default     = "30s"
}

variable "health_check_timeout" {
  description = "Health check timeout"
  type        = string
  default     = "10s"
}

variable "health_check_grace_period" {
  description = "Health check grace period"
  type        = string
  default     = "30s"
}

# Scaling Configuration
variable "max_machines_per_region" {
  description = "Maximum machines per region"
  type        = number
  default     = 10
}

variable "min_machines_per_region" {
  description = "Minimum machines per region"
  type        = number
  default     = 1
}

variable "target_cpu_percent" {
  description = "Target CPU percentage for auto-scaling"
  type        = number
  default     = 75
  validation {
    condition     = var.target_cpu_percent >= 10 && var.target_cpu_percent <= 95
    error_message = "Target CPU percentage must be between 10 and 95."
  }
}

variable "target_memory_percent" {
  description = "Target memory percentage for auto-scaling"
  type        = number
  default     = 80
  validation {
    condition     = var.target_memory_percent >= 10 && var.target_memory_percent <= 95
    error_message = "Target memory percentage must be between 10 and 95."
  }
}