#!/usr/bin/env python3
"""
Worker VM Provisioning Script
Automatically provisions and manages worker VMs for the P2P testing system
"""

import os
import sys
import requests
import redis
import json
import time
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
import uuid

# Import Bright Data proxy utilities
try:
    from utils.brightdata_proxy import get_brightdata_session, verify_proxy, get_proxy_info
except ImportError:
    # Fallback if Bright Data proxy utils not available
    def get_brightdata_session():
        return requests.Session()
    def verify_proxy():
        return True
    def get_proxy_info():
        return {}

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class WorkerConfig:
    machine_type: str = "e2-micro"
    disk_size: str = "20GB"
    image_family: str = "ubuntu-2204-lts"
    zone: str = "us-central1-a"
    network: str = "default"
    startup_script: str = "worker_entrypoint.sh"

@dataclass
class CloudProvider:
    name: str
    api_endpoint: str
    auth_header_name: str
    token_env_var: str

class WorkerProvisioner:
    def __init__(self):
        self.redis_client = self._setup_redis()
        self.cloud_providers = self._setup_cloud_providers()
        self.worker_count = int(os.environ.get('WORKER_COUNT', '3'))
        
    def _setup_redis(self):
        """Initialize Redis connection"""
        try:
            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
            client = redis.from_url(redis_url, decode_responses=True)
            client.ping()
            logger.info("Connected to Redis successfully")
            return client
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return None
    
    def _setup_cloud_providers(self) -> List[CloudProvider]:
        """Setup cloud provider configurations"""
        providers = [
            CloudProvider(
                name="gcp",
                api_endpoint="https://compute.googleapis.com/compute/v1",
                auth_header_name="Authorization",
                token_env_var="GCP_ACCESS_TOKEN"
            ),
            CloudProvider(
                name="azure",
                api_endpoint="https://management.azure.com",
                auth_header_name="Authorization",
                token_env_var="AZURE_ACCESS_TOKEN"
            ),
            CloudProvider(
                name="hetzner",
                api_endpoint="https://api.hetzner.cloud/v1",
                auth_header_name="Authorization",
                token_env_var="HETZNER_API_TOKEN"
            ),
            CloudProvider(
                name="generic",
                api_endpoint=os.environ.get('CLOUD_API_ENDPOINT', 'https://api.cloud.example.com/v1'),
                auth_header_name="Authorization",
                token_env_var="CLOUD_API_TOKEN"
            )
        ]
        return providers
    
    def _get_available_provider(self) -> Optional[CloudProvider]:
        """Find the first available cloud provider with valid credentials"""
        for provider in self.cloud_providers:
            token = os.environ.get(provider.token_env_var)
            if token:
                logger.info(f"Using cloud provider: {provider.name}")
                return provider
        
        logger.warning("No cloud provider credentials found")
        return None
    
    def _make_api_request(self, provider: CloudProvider, endpoint: str, method: str = "POST", data: Dict = None) -> Optional[Dict]:
        """Make API request to cloud provider through residential proxy"""
        token = os.environ.get(provider.token_env_var)
        if not token:
            logger.error(f"No token found for provider {provider.name}")
            return None
        
        headers = {
            provider.auth_header_name: f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            # Use proxied session for all cloud provider API calls
            session = get_brightdata_session()
            
            if method.upper() == "POST":
                response = session.post(f"{provider.api_endpoint}{endpoint}", 
                                       headers=headers, json=data, timeout=30)
            elif method.upper() == "GET":
                response = session.get(f"{provider.api_endpoint}{endpoint}", 
                                      headers=headers, timeout=30)
            elif method.upper() == "DELETE":
                response = session.delete(f"{provider.api_endpoint}{endpoint}", 
                                         headers=headers, timeout=30)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None
    
    def _create_worker_vm(self, provider: CloudProvider, worker_id: str, config: WorkerConfig) -> Optional[Dict]:
        """Create a single worker VM"""
        logger.info(f"Creating worker VM: {worker_id}")
        
        # Prepare VM configuration
        vm_data = {
            "name": f"worker-{worker_id}",
            "machineType": config.machine_type,
            "disks": [{
                "initializeParams": {
                    "diskSizeGb": config.disk_size,
                    "sourceImage": f"projects/ubuntu-os-cloud/global/images/family/{config.image_family}"
                },
                "boot": True
            }],
            "networkInterfaces": [{
                "network": f"global/networks/{config.network}",
                "accessConfigs": [{
                    "type": "ONE_TO_ONE_NAT",
                    "name": "External NAT"
                }]
            }],
            "metadata": {
                "items": [{
                    "key": "startup-script",
                    "value": self._get_startup_script()
                }, {
                    "key": "worker-id",
                    "value": worker_id
                }]
            },
            "tags": {
                "items": ["worker", "qa-framework", f"worker-{worker_id}"]
            }
        }
        
        # Generic cloud provider format
        if provider.name == "generic" or provider.name == "hetzner":
            vm_data = {
                "name": f"worker-{worker_id}",
                "server_type": config.machine_type,
                "image": "ubuntu-22.04",
                "user_data": self._get_startup_script(),
                "labels": {
                    "role": "worker",
                    "framework": "qa",
                    "worker_id": worker_id
                }
            }
        
        # Make API request
        endpoint = "/servers" if provider.name in ["generic", "hetzner"] else f"/projects/{os.environ.get('GCP_PROJECT')}/zones/{config.zone}/instances"
        response = self._make_api_request(provider, endpoint, "POST", vm_data)
        
        if response:
            vm_id = response.get('id') or response.get('name') or worker_id
            logger.info(f"Successfully created VM: {vm_id}")
            return {
                'id': vm_id,
                'name': f"worker-{worker_id}",
                'provider': provider.name,
                'created_at': time.time(),
                'status': 'creating'
            }
        
        return None
    
    def _get_startup_script(self) -> str:
        """Generate startup script for worker VMs"""
        script_path = os.path.join(os.path.dirname(__file__), 'worker_entrypoint.sh')
        if os.path.exists(script_path):
            with open(script_path, 'r') as f:
                return f.read()
        
        # Fallback inline script
        return '''#!/bin/bash
set -euo pipefail

# Update system
apt-get update && apt-get install -y python3 python3-pip docker.io redis-tools curl

# Install Python dependencies
pip3 install hvac requests redis

# Load secrets from Vault
python3 -c "
import os
try:
    exec(open('/infra/vault_loader.py').read())
    print('Secrets loaded successfully')
except: 
    print('Using environment fallback')
"

# Run warmup routine
bash /infra/warmup.sh || echo "Warmup script not found"

# Register with orchestrator
bash /infra/register.sh || echo "Registration script not found"

# Start worker process
while true; do
    echo "Worker running at $(date)"
    sleep 300
done
'''
    
    def provision_workers(self) -> List[Dict]:
        """Provision all worker VMs"""
        logger.info(f"Provisioning {self.worker_count} worker VMs...")
        
        provider = self._get_available_provider()
        if not provider:
            logger.error("No available cloud provider found")
            return []
        
        workers = []
        config = WorkerConfig()
        
        for i in range(self.worker_count):
            worker_id = f"{int(time.time())}-{str(uuid.uuid4())[:8]}"
            
            try:
                worker = self._create_worker_vm(provider, worker_id, config)
                if worker:
                    workers.append(worker)
                    
                    # Store in Redis
                    if self.redis_client:
                        self.redis_client.sadd('workers', worker['id'])
                        self.redis_client.hset(f"worker:{worker['id']}", mapping=worker)
                        self.redis_client.expire(f"worker:{worker['id']}", 86400 * 7)  # 7 days
                    
                    # Brief pause between provisions
                    time.sleep(2)
                    
            except Exception as e:
                logger.error(f"Failed to provision worker {worker_id}: {e}")
        
        logger.info(f"Successfully provisioned {len(workers)} out of {self.worker_count} workers")
        return workers
    
    def list_workers(self) -> List[Dict]:
        """List all provisioned workers"""
        if not self.redis_client:
            logger.error("Redis not available")
            return []
        
        try:
            worker_ids = self.redis_client.smembers('workers')
            workers = []
            
            for worker_id in worker_ids:
                worker_data = self.redis_client.hgetall(f"worker:{worker_id}")
                if worker_data:
                    workers.append(worker_data)
            
            return workers
            
        except Exception as e:
            logger.error(f"Failed to list workers: {e}")
            return []
    
    def cleanup_workers(self, max_age_hours: int = 24) -> int:
        """Clean up old or failed workers"""
        logger.info(f"Cleaning up workers older than {max_age_hours} hours...")
        
        workers = self.list_workers()
        cleanup_count = 0
        current_time = time.time()
        
        for worker in workers:
            try:
                created_at = float(worker.get('created_at', 0))
                age_hours = (current_time - created_at) / 3600
                
                if age_hours > max_age_hours:
                    worker_id = worker['id']
                    logger.info(f"Cleaning up old worker: {worker_id}")
                    
                    # Remove from Redis
                    if self.redis_client:
                        self.redis_client.srem('workers', worker_id)
                        self.redis_client.delete(f"worker:{worker_id}")
                    
                    # Note: Actual VM deletion would require provider-specific API calls
                    cleanup_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to cleanup worker: {e}")
        
        logger.info(f"Cleaned up {cleanup_count} workers")
        return cleanup_count

def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Worker VM Provisioner')
    parser.add_argument('--provision', action='store_true', help='Provision new workers')
    parser.add_argument('--list', action='store_true', help='List existing workers')
    parser.add_argument('--cleanup', action='store_true', help='Cleanup old workers')
    parser.add_argument('--count', type=int, help='Number of workers to provision')
    
    args = parser.parse_args()
    
    # Override worker count if specified
    if args.count:
        os.environ['WORKER_COUNT'] = str(args.count)
    
    provisioner = WorkerProvisioner()
    
    try:
        if args.provision:
            workers = provisioner.provision_workers()
            print(f"Provisioned {len(workers)} workers:")
            for worker in workers:
                print(f"  - {worker['id']} ({worker['provider']})")
                
        elif args.list:
            workers = provisioner.list_workers()
            print(f"Found {len(workers)} workers:")
            for worker in workers:
                print(f"  - {worker['id']} (created: {worker.get('created_at', 'unknown')})")
                
        elif args.cleanup:
            count = provisioner.cleanup_workers()
            print(f"Cleaned up {count} workers")
            
        else:
            # Default: provision workers
            workers = provisioner.provision_workers()
            print(f"Provisioned {len(workers)} workers")
        
        return True
        
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)