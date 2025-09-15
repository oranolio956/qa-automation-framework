# Terraform Configuration for Fly.io Infrastructure
# Modern Infrastructure as Code implementation

terraform {
  required_version = ">= 1.5"
  required_providers {
    fly = {
      source  = "fly-apps/fly"
      version = "~> 0.1"
    }
  }
  
  # Use Terraform Cloud or S3 for state management in production
  backend "s3" {
    bucket = "snapchat-automation-terraform-state"
    key    = "production/terraform.tfstate"
    region = "us-east-1"
  }
}

# Configure the Fly.io Provider
provider "fly" {
  # fly_api_token is set via FLY_API_TOKEN environment variable
}

# Local values for configuration
locals {
  app_name          = "snapchat-automation-prod"
  android_farm_name = "android-device-farm-prod"
  primary_region    = "ord"
  secondary_regions = ["iad", "lax"]
  
  common_tags = {
    Environment = "production"
    Project     = "snapchat-automation"
    ManagedBy   = "terraform"
  }
}

# Main Application Configuration
resource "fly_app" "main_app" {
  name = local.app_name
  org  = var.fly_org

  regions = [local.primary_region]
}

# Android Device Farm Application
resource "fly_app" "android_farm" {
  name = local.android_farm_name
  org  = var.fly_org

  regions = concat([local.primary_region], local.secondary_regions)
}

# Persistent Volumes for Android Farm
resource "fly_volume" "android_data" {
  count  = length(local.secondary_regions) + 1
  name   = "android_data_${count.index}"
  app    = fly_app.android_farm.id
  size   = 40
  region = count.index == 0 ? local.primary_region : local.secondary_regions[count.index - 1]
}

# Machine Configuration for Main App
resource "fly_machine" "main_app_machines" {
  count = var.main_app_machine_count
  app   = fly_app.main_app.id
  
  region = local.primary_region
  name   = "${local.app_name}-${count.index + 1}"
  
  image = var.main_app_image
  
  vm {
    size      = "shared-cpu-2x"
    memory_mb = 4096
  }
  
  services = [
    {
      internal_port = 8000
      ports = [
        {
          port     = 80
          handlers = ["http"]
        },
        {
          port     = 443
          handlers = ["tls", "http"]
        }
      ]
      
      http_checks = [
        {
          interval      = "30s"
          grace_period  = "10s"
          method        = "GET"
          path          = "/health"
          protocol      = "http"
          timeout       = "5s"
          restart_limit = 3
        }
      ]
      
      concurrency = {
        type       = "requests"
        hard_limit = 1000
        soft_limit = 800
      }
    }
  ]
  
  auto_stop_machines  = false
  auto_start_machines = true
  
  restart = {
    policy = "on-failure"
  }

  env = {
    ENVIRONMENT              = "production"
    LOG_LEVEL               = "INFO"
    FLY_ANDROID_DEPLOYMENT_ONLY = "true"
    DEVICE_FARM_ENDPOINT    = "https://${local.android_farm_name}.fly.dev"
  }
}

# Machine Configuration for Android Farm
resource "fly_machine" "android_farm_machines" {
  count = var.android_farm_machine_count
  app   = fly_app.android_farm.id
  
  region = count.index < 2 ? local.primary_region : local.secondary_regions[(count.index - 2) % length(local.secondary_regions)]
  name   = "${local.android_farm_name}-${count.index + 1}"
  
  image = var.android_farm_image
  
  vm {
    size      = "shared-cpu-4x"
    memory_mb = 8192
    cpu_kind  = "shared"
  }
  
  mounts = [
    {
      volume      = fly_volume.android_data[count.index % length(fly_volume.android_data)].id
      path        = "/opt/android-data"
      auto_backup = true
    }
  ]
  
  services = [
    {
      internal_port = 5000
      ports = [
        {
          port     = 80
          handlers = ["http"]
        },
        {
          port     = 443
          handlers = ["tls", "http"]
        }
      ]
      
      http_checks = [
        {
          interval      = "60s"
          grace_period  = "30s"
          method        = "GET"
          path          = "/health"
          protocol      = "http"
          timeout       = "15s"
          restart_limit = 3
        }
      ]
      
      concurrency = {
        type       = "connections"
        hard_limit = 10
        soft_limit = 8
      }
    },
    {
      internal_port = 5555
      ports = [
        {
          port = 5555
        }
      ]
      protocol = "tcp"
    }
  ]
  
  auto_stop_machines  = false
  auto_start_machines = true
  
  restart = {
    policy = "on-failure"
  }

  env = {
    DISPLAY         = ":99"
    ANDROID_HOME    = "/opt/android-sdk"
    ANDROID_SDK_ROOT = "/opt/android-sdk"
    DEVICE_POOL_SIZE = "5"
    AUTOMATION_USER = "automation"
  }
}

# Secrets Management
resource "fly_secret" "database_url" {
  app   = fly_app.main_app.id
  name  = "DATABASE_URL"
  value = var.database_url
}

resource "fly_secret" "redis_url" {
  app   = fly_app.main_app.id
  name  = "REDIS_URL"
  value = var.redis_url
}

resource "fly_secret" "telegram_bot_token" {
  app   = fly_app.main_app.id
  name  = "TELEGRAM_BOT_TOKEN"
  value = var.telegram_bot_token
}

resource "fly_secret" "jwt_secret" {
  app   = fly_app.main_app.id
  name  = "JWT_SECRET"
  value = var.jwt_secret
}

# Android Farm Secrets
resource "fly_secret" "android_database_url" {
  app   = fly_app.android_farm.id
  name  = "DATABASE_URL"
  value = var.database_url
}

resource "fly_secret" "android_redis_url" {
  app   = fly_app.android_farm.id
  name  = "REDIS_URL"
  value = var.redis_url
}

# Auto-scaling Configuration
resource "fly_scaling" "main_app_scaling" {
  app = fly_app.main_app.id
  
  regions = [
    {
      region = local.primary_region
      count  = var.main_app_machine_count
    }
  ]
}

resource "fly_scaling" "android_farm_scaling" {
  app = fly_app.android_farm.id
  
  regions = [
    {
      region = local.primary_region
      count  = 2
    },
    {
      region = "iad"
      count  = 1
    },
    {
      region = "lax"
      count  = 1
    }
  ]
}