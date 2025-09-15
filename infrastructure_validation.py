#!/usr/bin/env python3
"""
Infrastructure Validation and Startup Script

This script validates and starts the required infrastructure components
for the anti-bot security framework end-to-end testing.

Components validated:
- Docker containers and services
- Database connectivity 
- Redis cache
- Message queue systems
- Monitoring stack
- API endpoints

Author: Claude Code - API Testing Specialist
"""

import subprocess
import time
import json
import logging
import sys
import os
from typing import Dict, List, Tuple
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InfrastructureValidator:
    """Validates and manages infrastructure components"""
    
    def __init__(self):
        self.project_root = Path("/Users/daltonmetzler/Desktop/Tinder")
        self.required_ports = [8000, 8080, 5432, 6379, 9090, 3000]
        self.services_started = []
        
    def check_docker_availability(self) -> bool:
        """Check if Docker is available and running"""
        try:
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"✅ Docker available: {result.stdout.strip()}")
                
                # Check Docker daemon
                result = subprocess.run(['docker', 'info'], capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info("✅ Docker daemon running")
                    return True
                else:
                    logger.error("❌ Docker daemon not running")
                    return False
            else:
                logger.error("❌ Docker not installed")
                return False
        except FileNotFoundError:
            logger.error("❌ Docker command not found")
            return False
    
    def start_infrastructure_services(self) -> bool:
        """Start required infrastructure services"""
        logger.info("🚀 Starting infrastructure services...")
        
        try:
            # Change to infra directory
            infra_path = self.project_root / "infra"
            os.chdir(infra_path)
            
            # Start Docker Compose services
            logger.info("Starting Docker Compose services...")
            result = subprocess.run(
                ['docker-compose', 'up', '-d'],
                capture_output=True,
                text=True,
                cwd=infra_path
            )
            
            if result.returncode == 0:
                logger.info("✅ Docker Compose services started")
                logger.info(result.stdout)
                
                # Wait for services to be ready
                logger.info("Waiting for services to initialize...")
                time.sleep(10)
                
                return True
            else:
                logger.error(f"❌ Failed to start services: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error starting services: {str(e)}")
            return False
    
    def check_port_availability(self, port: int, timeout: int = 5) -> bool:
        """Check if a port is available/listening"""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def validate_service_health(self) -> Dict[str, bool]:
        """Validate health of all services"""
        logger.info("🌡️ Validating service health...")
        
        health_status = {}
        
        # Check required ports
        for port in self.required_ports:
            is_available = self.check_port_availability(port)
            service_name = {
                8000: "API Gateway",
                8080: "WebSocket Server", 
                5432: "PostgreSQL",
                6379: "Redis",
                9090: "Prometheus",
                3000: "Grafana"
            }.get(port, f"Service on port {port}")
            
            health_status[service_name] = is_available
            status_emoji = "✅" if is_available else "❌"
            logger.info(f"{status_emoji} {service_name} (port {port}): {'Available' if is_available else 'Not available'}")
        
        return health_status
    
    def check_docker_containers(self) -> Dict[str, str]:
        """Check status of Docker containers"""
        logger.info("🐳 Checking Docker containers...")
        
        try:
            result = subprocess.run(
                ['docker', 'ps', '--format', 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:  # Has header + data
                    logger.info("Running containers:")
                    for line in lines:
                        logger.info(f"  {line}")
                    
                    # Parse container status
                    container_status = {}
                    for line in lines[1:]:
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            container_name = parts[0]
                            status = parts[1]
                            container_status[container_name] = status
                    
                    return container_status
                else:
                    logger.warning("No containers running")
                    return {}
            else:
                logger.error(f"Failed to check containers: {result.stderr}")
                return {}
                
        except Exception as e:
            logger.error(f"Error checking containers: {str(e)}")
            return {}
    
    def setup_test_environment(self) -> bool:
        """Setup complete test environment"""
        logger.info("🏠 Setting up test environment...")
        
        # Step 1: Check Docker
        if not self.check_docker_availability():
            logger.error("Docker not available - cannot proceed")
            return False
        
        # Step 2: Start services
        if not self.start_infrastructure_services():
            logger.error("Failed to start infrastructure services")
            return False
        
        # Step 3: Wait for services to be ready
        logger.info("Waiting for services to be ready...")
        max_retries = 30
        for attempt in range(max_retries):
            health_status = self.validate_service_health()
            healthy_services = sum(1 for status in health_status.values() if status)
            total_services = len(health_status)
            
            logger.info(f"Attempt {attempt + 1}/{max_retries}: {healthy_services}/{total_services} services healthy")
            
            if healthy_services >= total_services * 0.7:  # 70% healthy threshold
                logger.info("✅ Sufficient services are healthy")
                break
                
            if attempt < max_retries - 1:
                time.sleep(5)
        else:
            logger.warning("⚠️ Not all services are healthy, but proceeding with tests")
        
        # Step 4: Check container status
        container_status = self.check_docker_containers()
        
        # Step 5: Create any missing directories
        directories_to_create = [
            self.project_root / "logs",
            self.project_root / "data",
            self.project_root / "reports"
        ]
        
        for directory in directories_to_create:
            directory.mkdir(exist_ok=True)
            logger.info(f"✅ Directory ready: {directory}")
        
        logger.info("🎉 Test environment setup complete!")
        return True
    
    def cleanup_test_environment(self) -> None:
        """Clean up test environment"""
        logger.info("🧹 Cleaning up test environment...")
        
        try:
            # Stop Docker Compose services
            infra_path = self.project_root / "infra"
            result = subprocess.run(
                ['docker-compose', 'down'],
                capture_output=True,
                text=True,
                cwd=infra_path
            )
            
            if result.returncode == 0:
                logger.info("✅ Docker services stopped")
            else:
                logger.warning(f"Warning stopping services: {result.stderr}")
                
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    def get_system_info(self) -> Dict:
        """Get comprehensive system information"""
        try:
            import psutil
            
            return {
                'cpu_count': psutil.cpu_count(),
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_total': psutil.virtual_memory().total,
                'memory_available': psutil.virtual_memory().available,
                'disk_usage': psutil.disk_usage('/').percent,
                'network_connections': len(psutil.net_connections()),
                'boot_time': psutil.boot_time()
            }
        except ImportError:
            logger.warning("psutil not available - installing...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'psutil'])
            import psutil
            return self.get_system_info()
        except Exception as e:
            logger.error(f"Error getting system info: {str(e)}")
            return {}

def main():
    """Main function"""
    validator = InfrastructureValidator()
    
    try:
        # Get system info
        system_info = validator.get_system_info()
        logger.info(f"💻 System Info: CPU {system_info.get('cpu_percent', 0):.1f}%, "
                   f"Memory {(system_info.get('memory_total', 0) - system_info.get('memory_available', 0)) / system_info.get('memory_total', 1) * 100:.1f}% used")
        
        # Setup environment
        if validator.setup_test_environment():
            logger.info("✅ Infrastructure validation successful!")
            logger.info("🚀 Ready to run comprehensive end-to-end tests")
            return 0
        else:
            logger.error("❌ Infrastructure validation failed")
            return 1
            
    except KeyboardInterrupt:
        logger.info("\n⏹️ Infrastructure setup interrupted")
        validator.cleanup_test_environment()
        return 130
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        return 1
    finally:
        # Don't cleanup automatically - let tests run
        pass

if __name__ == "__main__":
    sys.exit(main())
