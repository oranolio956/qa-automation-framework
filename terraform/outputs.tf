# Terraform Outputs

output "main_app_url" {
  description = "Main application URL"
  value       = "https://${fly_app.main_app.name}.fly.dev"
}

output "android_farm_url" {
  description = "Android farm URL"
  value       = "https://${fly_app.android_farm.name}.fly.dev"
}

output "main_app_id" {
  description = "Main application ID"
  value       = fly_app.main_app.id
}

output "android_farm_id" {
  description = "Android farm application ID"
  value       = fly_app.android_farm.id
}

output "deployed_regions" {
  description = "Regions where applications are deployed"
  value = {
    main_app     = [local.primary_region]
    android_farm = concat([local.primary_region], local.secondary_regions)
  }
}

output "volume_ids" {
  description = "Android data volume IDs"
  value       = fly_volume.android_data[*].id
}

output "machine_counts" {
  description = "Number of machines deployed"
  value = {
    main_app     = var.main_app_machine_count
    android_farm = var.android_farm_machine_count
  }
}

output "health_check_urls" {
  description = "Health check URLs for monitoring"
  value = {
    main_app     = "https://${fly_app.main_app.name}.fly.dev/health"
    android_farm = "https://${fly_app.android_farm.name}.fly.dev/health"
  }
}

# Output for monitoring integration
output "monitoring_endpoints" {
  description = "Monitoring endpoints for external systems"
  value = {
    prometheus_targets = [
      "${fly_app.main_app.name}.fly.dev:8000",
      "${fly_app.android_farm.name}.fly.dev:5000"
    ]
    grafana_dashboards = [
      "https://${fly_app.main_app.name}.fly.dev/metrics",
      "https://${fly_app.android_farm.name}.fly.dev/metrics"
    ]
  }
}

# Infrastructure metadata
output "infrastructure_metadata" {
  description = "Infrastructure metadata for CI/CD and monitoring"
  value = {
    terraform_version = "~> 1.5"
    provider_version  = "~> 0.1"
    environment      = var.environment
    managed_by       = "terraform"
    last_updated     = timestamp()
  }
}

# Resource configuration summary
output "resource_summary" {
  description = "Summary of deployed resources"
  value = {
    applications = {
      main_app = {
        name     = fly_app.main_app.name
        machines = var.main_app_machine_count
        vm_size  = var.main_app_vm_size
        regions  = [local.primary_region]
      }
      android_farm = {
        name     = fly_app.android_farm.name
        machines = var.android_farm_machine_count
        vm_size  = var.android_farm_vm_size
        regions  = concat([local.primary_region], local.secondary_regions)
      }
    }
    volumes = {
      count     = length(fly_volume.android_data)
      size_gb   = var.android_data_volume_size
      encrypted = true
    }
  }
}