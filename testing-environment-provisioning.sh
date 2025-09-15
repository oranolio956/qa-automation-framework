#!/bin/bash

# Testing Environment Provisioning System
# Creates isolated testing environments for development workflows
# Integrates with event-driven automation for legitimate development testing

set -euo pipefail

# Configuration
REPO_PATH="${REPO_PATH:-$(pwd)}"
LOG_FILE="${REPO_PATH}/logs/testing-provisioning.log"
DOCKER_NETWORK="test-network"
TEST_ENV_PREFIX="testenv"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"
}

# Create directory structure
setup_directories() {
    log "Setting up testing environment directories..."
    
    mkdir -p "${REPO_PATH}"/{testing,logs,configs}
    mkdir -p "${REPO_PATH}/testing"/{environments,templates,scripts,data}
    mkdir -p "${REPO_PATH}/testing/environments"/{active,archived,templates}
    
    log "✓ Directory structure created"
}

# Create Docker network for test isolation
setup_docker_network() {
    log "Setting up Docker network for test isolation..."
    
    if ! docker network ls | grep -q "$DOCKER_NETWORK"; then
        docker network create --driver bridge "$DOCKER_NETWORK"
        log "✓ Created Docker network: $DOCKER_NETWORK"
    else
        log "✓ Docker network already exists: $DOCKER_NETWORK"
    fi
}

# Create test environment management service
create_environment_manager() {
    log "Creating test environment management service..."
    
    mkdir -p "${REPO_PATH}/testing/services"
    
    cat > "${REPO_PATH}/testing/services/environment_manager.py" << 'EOF'
"""
Test Environment Management Service
Provisions and manages isolated testing environments for development workflows
Designed for legitimate development testing and CI/CD processes
"""

import docker
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
import subprocess
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestEnvironmentManager:
    """Manages isolated test environments"""
    
    def __init__(self, base_path: str = "/opt/testing"):
        self.docker_client = docker.from_env()
        self.base_path = base_path
        self.network_name = "test-network"
        self.environments = {}
        self.load_existing_environments()
    
    def load_existing_environments(self):
        """Load existing environment configurations"""
        config_file = os.path.join(self.base_path, "environments.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    self.environments = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load environments: {e}")
                self.environments = {}
    
    def save_environments(self):
        """Save environment configurations"""
        config_file = os.path.join(self.base_path, "environments.json")
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        try:
            with open(config_file, 'w') as f:
                json.dump(self.environments, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save environments: {e}")
    
    def create_test_environment(self, config: Dict[str, Any]) -> str:
        """Create new isolated test environment"""
        env_id = f"testenv-{str(uuid.uuid4())[:8]}"
        
        environment = {
            'id': env_id,
            'name': config.get('name', f'Test Environment {env_id}'),
            'type': config.get('type', 'web'),
            'created_at': datetime.utcnow().isoformat(),
            'status': 'creating',
            'containers': [],
            'networks': [self.network_name],
            'volumes': [],
            'config': config
        }
        
        try:
            # Create environment-specific network
            env_network = f"{env_id}-network"
            try:
                self.docker_client.networks.create(
                    name=env_network,
                    driver="bridge",
                    labels={"environment": env_id, "type": "test"}
                )
                environment['networks'].append(env_network)
                logger.info(f"Created network: {env_network}")
            except docker.errors.APIError as e:
                if "already exists" not in str(e):
                    raise
            
            # Create containers based on environment type
            containers = self._create_environment_containers(env_id, config)
            environment['containers'] = [c.id for c in containers]
            environment['status'] = 'running'
            
            self.environments[env_id] = environment
            self.save_environments()
            
            logger.info(f"Created test environment: {env_id}")
            return env_id
            
        except Exception as e:
            logger.error(f"Failed to create environment {env_id}: {e}")
            environment['status'] = 'failed'
            environment['error'] = str(e)
            raise
    
    def _create_environment_containers(self, env_id: str, config: Dict[str, Any]) -> List:
        """Create containers for test environment"""
        containers = []
        env_type = config.get('type', 'web')
        
        if env_type == 'web':
            # Web application testing environment
            containers.extend(self._create_web_containers(env_id, config))
        elif env_type == 'api':
            # API testing environment
            containers.extend(self._create_api_containers(env_id, config))
        elif env_type == 'mobile':
            # Mobile app testing environment
            containers.extend(self._create_mobile_containers(env_id, config))
        else:
            # Default testing environment
            containers.extend(self._create_default_containers(env_id, config))
        
        return containers
    
    def _create_web_containers(self, env_id: str, config: Dict[str, Any]) -> List:
        """Create web testing containers"""
        containers = []
        
        # Database container
        db_container = self.docker_client.containers.run(
            image="postgres:13-alpine",
            name=f"{env_id}-postgres",
            environment={
                'POSTGRES_DB': 'testdb',
                'POSTGRES_USER': 'testuser',
                'POSTGRES_PASSWORD': 'testpass123'
            },
            network=f"{env_id}-network",
            labels={"environment": env_id, "service": "database"},
            detach=True,
            remove=True
        )
        containers.append(db_container)
        
        # Redis cache container
        redis_container = self.docker_client.containers.run(
            image="redis:6-alpine",
            name=f"{env_id}-redis",
            network=f"{env_id}-network",
            labels={"environment": env_id, "service": "cache"},
            detach=True,
            remove=True
        )
        containers.append(redis_container)
        
        # Web application container
        web_container = self.docker_client.containers.run(
            image="nginx:alpine",
            name=f"{env_id}-web",
            ports={'80/tcp': None},
            network=f"{env_id}-network",
            labels={"environment": env_id, "service": "web"},
            detach=True,
            remove=True
        )
        containers.append(web_container)
        
        return containers
    
    def _create_api_containers(self, env_id: str, config: Dict[str, Any]) -> List:
        """Create API testing containers"""
        containers = []
        
        # API server container
        api_container = self.docker_client.containers.run(
            image="python:3.9-slim",
            name=f"{env_id}-api",
            command="python -m http.server 8000",
            ports={'8000/tcp': None},
            network=f"{env_id}-network",
            labels={"environment": env_id, "service": "api"},
            detach=True,
            remove=True
        )
        containers.append(api_container)
        
        return containers
    
    def _create_mobile_containers(self, env_id: str, config: Dict[str, Any]) -> List:
        """Create mobile testing containers"""
        containers = []
        
        # Mobile testing simulator
        simulator_container = self.docker_client.containers.run(
            image="budtmo/docker-android:emulator_11.0",
            name=f"{env_id}-android",
            privileged=True,
            ports={'6080/tcp': None, '5555/tcp': None},
            network=f"{env_id}-network",
            labels={"environment": env_id, "service": "mobile"},
            detach=True,
            remove=True
        )
        containers.append(simulator_container)
        
        return containers
    
    def _create_default_containers(self, env_id: str, config: Dict[str, Any]) -> List:
        """Create default testing containers"""
        containers = []
        
        # Basic testing container
        test_container = self.docker_client.containers.run(
            image="ubuntu:20.04",
            name=f"{env_id}-test",
            command="sleep infinity",
            network=f"{env_id}-network",
            labels={"environment": env_id, "service": "test"},
            detach=True,
            remove=True
        )
        containers.append(test_container)
        
        return containers
    
    def get_environment_status(self, env_id: str) -> Dict[str, Any]:
        """Get environment status and details"""
        if env_id not in self.environments:
            raise ValueError(f"Environment {env_id} not found")
        
        environment = self.environments[env_id].copy()
        
        # Check container status
        container_statuses = []
        for container_id in environment.get('containers', []):
            try:
                container = self.docker_client.containers.get(container_id)
                container_statuses.append({
                    'id': container.id,
                    'name': container.name,
                    'status': container.status,
                    'ports': container.ports
                })
            except docker.errors.NotFound:
                container_statuses.append({
                    'id': container_id,
                    'status': 'not_found'
                })
        
        environment['container_statuses'] = container_statuses
        return environment
    
    def destroy_environment(self, env_id: str) -> bool:
        """Clean up test environment"""
        if env_id not in self.environments:
            raise ValueError(f"Environment {env_id} not found")
        
        try:
            environment = self.environments[env_id]
            
            # Stop and remove containers
            for container_id in environment.get('containers', []):
                try:
                    container = self.docker_client.containers.get(container_id)
                    container.stop(timeout=10)
                    container.remove()
                except docker.errors.NotFound:
                    pass
            
            # Remove networks
            for network_name in environment.get('networks', []):
                if network_name != self.network_name:  # Don't remove main network
                    try:
                        network = self.docker_client.networks.get(network_name)
                        network.remove()
                    except docker.errors.NotFound:
                        pass
            
            # Remove from tracking
            del self.environments[env_id]
            self.save_environments()
            
            logger.info(f"Destroyed environment: {env_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to destroy environment {env_id}: {e}")
            return False
    
    def list_environments(self) -> List[Dict[str, Any]]:
        """List all test environments"""
        environments = []
        for env_id, env_data in self.environments.items():
            env_summary = {
                'id': env_id,
                'name': env_data.get('name'),
                'type': env_data.get('type'),
                'status': env_data.get('status'),
                'created_at': env_data.get('created_at'),
                'container_count': len(env_data.get('containers', []))
            }
            environments.append(env_summary)
        
        return environments
    
    def cleanup_stale_environments(self, max_age_hours: int = 24):
        """Clean up environments older than specified hours"""
        current_time = datetime.utcnow()
        stale_environments = []
        
        for env_id, env_data in self.environments.items():
            created_at = datetime.fromisoformat(env_data['created_at'])
            age_hours = (current_time - created_at).total_seconds() / 3600
            
            if age_hours > max_age_hours:
                stale_environments.append(env_id)
        
        for env_id in stale_environments:
            logger.info(f"Cleaning up stale environment: {env_id}")
            self.destroy_environment(env_id)
        
        return len(stale_environments)

EOF

    log "✓ Environment manager service created"
}

# Create Flask API for environment management
create_environment_api() {
    log "Creating environment management API..."
    
    mkdir -p "${REPO_PATH}/testing/api"
    
    cat > "${REPO_PATH}/testing/api/environment_api.py" << 'EOF'
"""
Test Environment API
RESTful API for managing test environments
For legitimate development testing workflows
"""

from flask import Flask, Blueprint, request, jsonify
from flask_restful import Api, Resource
import logging
from datetime import datetime
import json
import sys
import os

# Add the services directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services'))
from environment_manager import TestEnvironmentManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
environment_bp = Blueprint('environment', __name__)
environment_api = Api(environment_bp)

# Initialize environment manager
env_manager = TestEnvironmentManager()

class EnvironmentListResource(Resource):
    """Handle environment listing and creation"""
    
    def get(self):
        """List all environments"""
        try:
            environments = env_manager.list_environments()
            return {
                'success': True,
                'environments': environments,
                'count': len(environments)
            }, 200
        except Exception as e:
            logger.error(f"Failed to list environments: {e}")
            return {'success': False, 'error': str(e)}, 500
    
    def post(self):
        """Create new test environment"""
        try:
            data = request.get_json() or {}
            
            # Validate required fields
            env_type = data.get('type', 'web')
            name = data.get('name', f'Test Environment {datetime.utcnow().strftime("%Y%m%d-%H%M%S")}')
            
            config = {
                'name': name,
                'type': env_type,
                'description': data.get('description', ''),
                'settings': data.get('settings', {})
            }
            
            env_id = env_manager.create_test_environment(config)
            environment = env_manager.get_environment_status(env_id)
            
            return {
                'success': True,
                'environment': environment,
                'message': f'Environment {env_id} created successfully'
            }, 201
            
        except Exception as e:
            logger.error(f"Failed to create environment: {e}")
            return {'success': False, 'error': str(e)}, 500

class EnvironmentResource(Resource):
    """Handle individual environment operations"""
    
    def get(self, env_id):
        """Get environment details"""
        try:
            environment = env_manager.get_environment_status(env_id)
            return {
                'success': True,
                'environment': environment
            }, 200
        except ValueError as e:
            return {'success': False, 'error': str(e)}, 404
        except Exception as e:
            logger.error(f"Failed to get environment {env_id}: {e}")
            return {'success': False, 'error': str(e)}, 500
    
    def delete(self, env_id):
        """Destroy test environment"""
        try:
            success = env_manager.destroy_environment(env_id)
            if success:
                return {
                    'success': True,
                    'message': f'Environment {env_id} destroyed successfully'
                }, 200
            else:
                return {'success': False, 'error': 'Failed to destroy environment'}, 500
        except ValueError as e:
            return {'success': False, 'error': str(e)}, 404
        except Exception as e:
            logger.error(f"Failed to destroy environment {env_id}: {e}")
            return {'success': False, 'error': str(e)}, 500

class CleanupResource(Resource):
    """Handle environment cleanup operations"""
    
    def post(self):
        """Clean up stale environments"""
        try:
            data = request.get_json() or {}
            max_age_hours = data.get('max_age_hours', 24)
            
            cleaned_count = env_manager.cleanup_stale_environments(max_age_hours)
            
            return {
                'success': True,
                'cleaned_count': cleaned_count,
                'message': f'Cleaned up {cleaned_count} stale environments'
            }, 200
            
        except Exception as e:
            logger.error(f"Failed to cleanup environments: {e}")
            return {'success': False, 'error': str(e)}, 500

# Register API resources
environment_api.add_resource(EnvironmentListResource, '/environments')
environment_api.add_resource(EnvironmentResource, '/environments/<string:env_id>')
environment_api.add_resource(CleanupResource, '/environments/cleanup')

# Health check endpoint
@environment_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'test-environment-api'
    }), 200

if __name__ == '__main__':
    app = Flask(__name__)
    app.register_blueprint(environment_bp, url_prefix='/api/v1')
    app.run(host='0.0.0.0', port=5001, debug=False)

EOF

    log "✓ Environment API created"
}

# Create environment templates
create_environment_templates() {
    log "Creating environment templates..."
    
    mkdir -p "${REPO_PATH}/testing/templates"
    
    # Web application template
    cat > "${REPO_PATH}/testing/templates/web_app_template.json" << 'EOF'
{
  "name": "Web Application Test Environment",
  "type": "web",
  "description": "Full-stack web application testing environment with database and cache",
  "services": [
    {
      "name": "database",
      "image": "postgres:13-alpine",
      "environment": {
        "POSTGRES_DB": "testdb",
        "POSTGRES_USER": "testuser",
        "POSTGRES_PASSWORD": "testpass123"
      },
      "ports": ["5432:5432"]
    },
    {
      "name": "cache",
      "image": "redis:6-alpine",
      "ports": ["6379:6379"]
    },
    {
      "name": "web",
      "image": "nginx:alpine",
      "ports": ["80:80"],
      "depends_on": ["database", "cache"]
    }
  ],
  "volumes": [
    {
      "name": "postgres_data",
      "mount_point": "/var/lib/postgresql/data"
    }
  ],
  "networks": ["test-network"],
  "health_checks": [
    {
      "service": "database",
      "command": "pg_isready -U testuser -d testdb",
      "interval": "30s",
      "timeout": "10s",
      "retries": 3
    }
  ]
}
EOF

    # API testing template
    cat > "${REPO_PATH}/testing/templates/api_test_template.json" << 'EOF'
{
  "name": "API Test Environment",
  "type": "api",
  "description": "API testing environment with mock services",
  "services": [
    {
      "name": "api_server",
      "image": "python:3.9-slim",
      "command": "python -m http.server 8000",
      "ports": ["8000:8000"],
      "environment": {
        "FLASK_ENV": "testing",
        "API_DEBUG": "true"
      }
    },
    {
      "name": "mock_service",
      "image": "wiremock/wiremock:latest",
      "ports": ["8080:8080"],
      "command": "--global-response-templating"
    }
  ],
  "networks": ["test-network"],
  "test_data": {
    "endpoints": [
      "/api/health",
      "/api/users",
      "/api/products"
    ]
  }
}
EOF

    # Mobile testing template
    cat > "${REPO_PATH}/testing/templates/mobile_test_template.json" << 'EOF'
{
  "name": "Mobile App Test Environment",
  "type": "mobile",
  "description": "Mobile application testing with Android emulator",
  "services": [
    {
      "name": "android_emulator",
      "image": "budtmo/docker-android:emulator_11.0",
      "ports": ["6080:6080", "5555:5555"],
      "privileged": true,
      "environment": {
        "DEVICE": "Samsung Galaxy S10",
        "APPIUM": "true"
      }
    },
    {
      "name": "appium_server",
      "image": "appium/appium:latest",
      "ports": ["4723:4723"],
      "depends_on": ["android_emulator"]
    }
  ],
  "networks": ["test-network"],
  "capabilities": [
    "SYS_ADMIN"
  ]
}
EOF

    log "✓ Environment templates created"
}

# Create CLI tools for environment management
create_cli_tools() {
    log "Creating CLI management tools..."
    
    mkdir -p "${REPO_PATH}/testing/cli"
    
    cat > "${REPO_PATH}/testing/cli/testenv" << 'EOF'
#!/bin/bash

# Test Environment CLI Tool
# Command-line interface for managing test environments

set -euo pipefail

API_BASE_URL="http://localhost:5001/api/v1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

usage() {
    echo "Test Environment CLI Tool"
    echo ""
    echo "Usage: testenv [command] [options]"
    echo ""
    echo "Commands:"
    echo "  list                     List all test environments"
    echo "  create [type] [name]     Create new test environment"
    echo "  status [env_id]          Get environment status"
    echo "  destroy [env_id]         Destroy test environment"
    echo "  cleanup [hours]          Clean up environments older than hours"
    echo "  templates                List available templates"
    echo "  health                   Check API health"
    echo ""
    echo "Environment Types:"
    echo "  web                      Web application environment"
    echo "  api                      API testing environment"  
    echo "  mobile                   Mobile app testing environment"
    echo ""
    echo "Examples:"
    echo "  testenv list"
    echo "  testenv create web 'My Test App'"
    echo "  testenv status testenv-12345678"
    echo "  testenv destroy testenv-12345678"
    echo "  testenv cleanup 48"
}

make_request() {
    local method=$1
    local endpoint=$2
    local data=${3:-}
    
    local curl_cmd="curl -s -X $method"
    
    if [[ -n "$data" ]]; then
        curl_cmd="$curl_cmd -H 'Content-Type: application/json' -d '$data'"
    fi
    
    curl_cmd="$curl_cmd $API_BASE_URL$endpoint"
    
    eval $curl_cmd
}

list_environments() {
    echo -e "${BLUE}Listing test environments...${NC}"
    
    response=$(make_request GET "/environments")
    
    if echo "$response" | jq -e '.success' > /dev/null; then
        echo "$response" | jq -r '.environments[] | "\(.id) - \(.name) (\(.type)) - \(.status)"' | while read line; do
            echo -e "${GREEN}✓${NC} $line"
        done
        
        count=$(echo "$response" | jq -r '.count')
        echo -e "\n${BLUE}Total environments: $count${NC}"
    else
        error=$(echo "$response" | jq -r '.error // "Unknown error"')
        echo -e "${RED}Failed to list environments: $error${NC}"
        exit 1
    fi
}

create_environment() {
    local env_type=${1:-web}
    local env_name=${2:-"Test Environment $(date +%Y%m%d-%H%M%S)"}
    
    echo -e "${BLUE}Creating $env_type environment: $env_name${NC}"
    
    local data=$(jq -n \
        --arg type "$env_type" \
        --arg name "$env_name" \
        '{type: $type, name: $name}')
    
    response=$(make_request POST "/environments" "$data")
    
    if echo "$response" | jq -e '.success' > /dev/null; then
        env_id=$(echo "$response" | jq -r '.environment.id')
        echo -e "${GREEN}✓ Environment created: $env_id${NC}"
        echo -e "${BLUE}Use 'testenv status $env_id' to check status${NC}"
    else
        error=$(echo "$response" | jq -r '.error // "Unknown error"')
        echo -e "${RED}Failed to create environment: $error${NC}"
        exit 1
    fi
}

get_status() {
    local env_id=$1
    
    echo -e "${BLUE}Getting status for environment: $env_id${NC}"
    
    response=$(make_request GET "/environments/$env_id")
    
    if echo "$response" | jq -e '.success' > /dev/null; then
        echo "$response" | jq -r '.environment | "ID: \(.id)\nName: \(.name)\nType: \(.type)\nStatus: \(.status)\nCreated: \(.created_at)"'
        
        echo -e "\n${BLUE}Containers:${NC}"
        echo "$response" | jq -r '.environment.container_statuses[]? | "  - \(.name): \(.status)"'
    else
        error=$(echo "$response" | jq -r '.error // "Unknown error"')
        echo -e "${RED}Failed to get environment status: $error${NC}"
        exit 1
    fi
}

destroy_environment() {
    local env_id=$1
    
    echo -e "${YELLOW}Destroying environment: $env_id${NC}"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        response=$(make_request DELETE "/environments/$env_id")
        
        if echo "$response" | jq -e '.success' > /dev/null; then
            echo -e "${GREEN}✓ Environment destroyed: $env_id${NC}"
        else
            error=$(echo "$response" | jq -r '.error // "Unknown error"')
            echo -e "${RED}Failed to destroy environment: $error${NC}"
            exit 1
        fi
    else
        echo "Operation cancelled"
    fi
}

cleanup_environments() {
    local max_age_hours=${1:-24}
    
    echo -e "${BLUE}Cleaning up environments older than $max_age_hours hours...${NC}"
    
    local data=$(jq -n --argjson hours "$max_age_hours" '{max_age_hours: $hours}')
    response=$(make_request POST "/environments/cleanup" "$data")
    
    if echo "$response" | jq -e '.success' > /dev/null; then
        count=$(echo "$response" | jq -r '.cleaned_count')
        echo -e "${GREEN}✓ Cleaned up $count environments${NC}"
    else
        error=$(echo "$response" | jq -r '.error // "Unknown error"')
        echo -e "${RED}Failed to cleanup environments: $error${NC}"
        exit 1
    fi
}

list_templates() {
    echo -e "${BLUE}Available environment templates:${NC}"
    
    templates_dir="$SCRIPT_DIR/../templates"
    if [[ -d "$templates_dir" ]]; then
        for template in "$templates_dir"/*.json; do
            if [[ -f "$template" ]]; then
                name=$(jq -r '.name' "$template")
                type=$(jq -r '.type' "$template")
                description=$(jq -r '.description' "$template")
                echo -e "${GREEN}✓${NC} $type: $name"
                echo "   $description"
            fi
        done
    else
        echo -e "${YELLOW}No templates directory found${NC}"
    fi
}

check_health() {
    echo -e "${BLUE}Checking API health...${NC}"
    
    response=$(make_request GET "/health")
    
    if echo "$response" | jq -e '.status' > /dev/null; then
        status=$(echo "$response" | jq -r '.status')
        timestamp=$(echo "$response" | jq -r '.timestamp')
        echo -e "${GREEN}✓ API Status: $status${NC}"
        echo "  Timestamp: $timestamp"
    else
        echo -e "${RED}API is not responding${NC}"
        exit 1
    fi
}

# Main command handling
case "${1:-}" in
    "list")
        list_environments
        ;;
    "create")
        create_environment "${2:-}" "${3:-}"
        ;;
    "status")
        if [[ -z "${2:-}" ]]; then
            echo -e "${RED}Environment ID required${NC}"
            usage
            exit 1
        fi
        get_status "$2"
        ;;
    "destroy")
        if [[ -z "${2:-}" ]]; then
            echo -e "${RED}Environment ID required${NC}"
            usage
            exit 1
        fi
        destroy_environment "$2"
        ;;
    "cleanup")
        cleanup_environments "${2:-24}"
        ;;
    "templates")
        list_templates
        ;;
    "health")
        check_health
        ;;
    "help"|"--help"|"-h")
        usage
        ;;
    *)
        echo -e "${RED}Unknown command: ${1:-}${NC}"
        usage
        exit 1
        ;;
esac
EOF

    chmod +x "${REPO_PATH}/testing/cli/testenv"
    
    log "✓ CLI tools created"
}

# Create monitoring and logging
create_monitoring() {
    log "Setting up monitoring and logging..."
    
    mkdir -p "${REPO_PATH}/testing/monitoring"
    
    cat > "${REPO_PATH}/testing/monitoring/environment_monitor.py" << 'EOF'
"""
Test Environment Monitoring
Monitors health and resource usage of test environments
For legitimate development testing workflows
"""

import docker
import psutil
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnvironmentMonitor:
    """Monitors test environment health and resources"""
    
    def __init__(self, check_interval: int = 60):
        self.docker_client = docker.from_env()
        self.check_interval = check_interval
        self.monitoring_active = False
        self.metrics_history = []
        
    def start_monitoring(self):
        """Start monitoring thread"""
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return
            
        self.monitoring_active = True
        monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        monitor_thread.start()
        logger.info("Environment monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring_active = False
        logger.info("Environment monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                metrics = self.collect_metrics()
                self.metrics_history.append(metrics)
                
                # Keep only last 24 hours of data
                cutoff_time = datetime.utcnow().timestamp() - (24 * 3600)
                self.metrics_history = [
                    m for m in self.metrics_history 
                    if m['timestamp'] > cutoff_time
                ]
                
                # Check for issues
                self.check_environment_health(metrics)
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
            
            time.sleep(self.check_interval)
    
    def collect_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics"""
        timestamp = datetime.utcnow().timestamp()
        
        # System metrics
        system_metrics = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
        }
        
        # Docker metrics
        docker_metrics = self.collect_docker_metrics()
        
        metrics = {
            'timestamp': timestamp,
            'system': system_metrics,
            'docker': docker_metrics
        }
        
        return metrics
    
    def collect_docker_metrics(self) -> Dict[str, Any]:
        """Collect Docker container metrics"""
        containers = []
        
        try:
            for container in self.docker_client.containers.list():
                # Get container stats
                stats = container.stats(stream=False)
                
                # Calculate CPU percentage
                cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                           stats['precpu_stats']['cpu_usage']['total_usage']
                system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                              stats['precpu_stats']['system_cpu_usage']
                
                cpu_percent = 0
                if system_delta > 0 and cpu_delta > 0:
                    cpu_count = stats['cpu_stats']['online_cpus']
                    cpu_percent = (cpu_delta / system_delta) * cpu_count * 100
                
                # Calculate memory usage
                memory_usage = stats['memory_stats'].get('usage', 0)
                memory_limit = stats['memory_stats'].get('limit', 0)
                memory_percent = 0
                if memory_limit > 0:
                    memory_percent = (memory_usage / memory_limit) * 100
                
                container_info = {
                    'id': container.id[:12],
                    'name': container.name,
                    'status': container.status,
                    'cpu_percent': round(cpu_percent, 2),
                    'memory_usage_mb': round(memory_usage / (1024 * 1024), 2),
                    'memory_percent': round(memory_percent, 2),
                    'labels': container.labels
                }
                
                containers.append(container_info)
                
        except Exception as e:
            logger.error(f"Failed to collect Docker metrics: {e}")
        
        return {
            'containers': containers,
            'container_count': len(containers)
        }
    
    def check_environment_health(self, metrics: Dict[str, Any]):
        """Check for environment health issues"""
        issues = []
        
        # Check system resources
        if metrics['system']['cpu_percent'] > 90:
            issues.append("High CPU usage detected")
        
        if metrics['system']['memory_percent'] > 90:
            issues.append("High memory usage detected")
        
        if metrics['system']['disk_percent'] > 90:
            issues.append("Low disk space detected")
        
        # Check container health
        for container in metrics['docker']['containers']:
            if container['status'] != 'running':
                issues.append(f"Container {container['name']} is not running")
            
            if container['cpu_percent'] > 80:
                issues.append(f"Container {container['name']} has high CPU usage")
            
            if container['memory_percent'] > 90:
                issues.append(f"Container {container['name']} has high memory usage")
        
        # Log issues
        if issues:
            for issue in issues:
                logger.warning(f"Health check: {issue}")
    
    def get_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get metrics summary for specified time period"""
        cutoff_time = datetime.utcnow().timestamp() - (hours * 3600)
        recent_metrics = [
            m for m in self.metrics_history 
            if m['timestamp'] > cutoff_time
        ]
        
        if not recent_metrics:
            return {'message': 'No metrics available for specified period'}
        
        # Calculate averages
        avg_cpu = sum(m['system']['cpu_percent'] for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m['system']['memory_percent'] for m in recent_metrics) / len(recent_metrics)
        
        return {
            'period_hours': hours,
            'sample_count': len(recent_metrics),
            'average_cpu_percent': round(avg_cpu, 2),
            'average_memory_percent': round(avg_memory, 2),
            'current_containers': recent_metrics[-1]['docker']['container_count'] if recent_metrics else 0
        }

if __name__ == '__main__':
    monitor = EnvironmentMonitor()
    monitor.start_monitoring()
    
    try:
        while True:
            time.sleep(60)
            summary = monitor.get_metrics_summary()
            print(f"Metrics: {summary}")
    except KeyboardInterrupt:
        monitor.stop_monitoring()
        print("Monitoring stopped")

EOF

    log "✓ Monitoring setup complete"
}

# Create integration with event-driven automation
create_automation_integration() {
    log "Creating integration with event-driven automation..."
    
    cat > "${REPO_PATH}/testing/integrations/automation_webhook.py" << 'EOF'
"""
Automation Integration Webhook
Integrates test environment provisioning with event-driven automation
For legitimate development workflows
"""

import json
import requests
import logging
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutomationWebhook:
    """Handles integration with automation system"""
    
    def __init__(self, automation_url: str = "http://localhost:8080"):
        self.automation_url = automation_url
        self.webhook_secret = "dev-automation-secret"
    
    def notify_environment_created(self, environment: Dict[str, Any]):
        """Notify automation system of new environment"""
        try:
            event_data = {
                'event_type': 'EnvironmentCreated',
                'timestamp': datetime.utcnow().isoformat(),
                'data': {
                    'environment_id': environment.get('id'),
                    'environment_name': environment.get('name'),
                    'environment_type': environment.get('type'),
                    'status': environment.get('status'),
                    'containers': environment.get('containers', [])
                }
            }
            
            response = requests.post(
                f"{self.automation_url}/api/automation/events",
                json=event_data,
                headers={
                    'Content-Type': 'application/json',
                    'X-Webhook-Secret': self.webhook_secret
                },
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Notified automation system of environment creation: {environment.get('id')}")
            else:
                logger.warning(f"Failed to notify automation system: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error notifying automation system: {e}")
    
    def notify_environment_destroyed(self, env_id: str):
        """Notify automation system of environment destruction"""
        try:
            event_data = {
                'event_type': 'EnvironmentDestroyed',
                'timestamp': datetime.utcnow().isoformat(),
                'data': {
                    'environment_id': env_id
                }
            }
            
            response = requests.post(
                f"{self.automation_url}/api/automation/events",
                json=event_data,
                headers={
                    'Content-Type': 'application/json',
                    'X-Webhook-Secret': self.webhook_secret
                },
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Notified automation system of environment destruction: {env_id}")
            else:
                logger.warning(f"Failed to notify automation system: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error notifying automation system: {e}")
    
    def request_environment_for_test(self, test_config: Dict[str, Any]) -> str:
        """Request environment creation for test execution"""
        try:
            request_data = {
                'request_type': 'CreateTestEnvironment',
                'timestamp': datetime.utcnow().isoformat(),
                'config': test_config
            }
            
            response = requests.post(
                f"{self.automation_url}/api/automation/environment-requests",
                json=request_data,
                headers={
                    'Content-Type': 'application/json',
                    'X-Webhook-Secret': self.webhook_secret
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                environment_id = result.get('environment_id')
                logger.info(f"Requested environment for test: {environment_id}")
                return environment_id
            else:
                logger.error(f"Failed to request environment: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error requesting environment: {e}")
            return None

EOF

    log "✓ Automation integration created"
}

# Create deployment and service setup
create_deployment() {
    log "Creating deployment configuration..."
    
    # Create systemd service file
    cat > "${REPO_PATH}/testing/deploy/test-environment-api.service" << 'EOF'
[Unit]
Description=Test Environment Management API
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/testing
Environment=FLASK_ENV=production
Environment=PYTHONPATH=/opt/testing
ExecStart=/usr/bin/python3 api/environment_api.py
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=test-env-api

[Install]
WantedBy=multi-user.target
EOF

    # Create main deployment script
    cat > "${REPO_PATH}/testing/deploy/deploy_testing_system.sh" << 'EOF'
#!/bin/bash

# Deploy Testing Environment System
# Sets up complete testing infrastructure

set -euo pipefail

INSTALL_DIR="/opt/testing"
SERVICE_USER="ubuntu"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Create installation directory
sudo mkdir -p "$INSTALL_DIR"
sudo chown "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"

# Copy application files
log "Installing test environment system..."
cp -r ../services "$INSTALL_DIR/"
cp -r ../api "$INSTALL_DIR/"
cp -r ../templates "$INSTALL_DIR/"
cp -r ../cli "$INSTALL_DIR/"
cp -r ../monitoring "$INSTALL_DIR/"
cp -r ../integrations "$INSTALL_DIR/"

# Set permissions
sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/cli/testenv"

# Install Python dependencies
log "Installing Python dependencies..."
pip3 install docker flask flask-restful psutil requests

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    log "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$SERVICE_USER"
fi

# Create systemd service
log "Setting up systemd service..."
sudo cp test-environment-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable test-environment-api
sudo systemctl start test-environment-api

# Add CLI to PATH
if ! grep -q "/opt/testing/cli" /home/$SERVICE_USER/.bashrc; then
    echo 'export PATH="$PATH:/opt/testing/cli"' >> /home/$SERVICE_USER/.bashrc
fi

log "✓ Test environment system deployed successfully"
log "Use 'testenv help' for CLI usage"
log "API available at: http://localhost:5001/api/v1"

EOF

    chmod +x "${REPO_PATH}/testing/deploy/deploy_testing_system.sh"
    
    log "✓ Deployment configuration created"
}

# Main installation function
main() {
    log "Setting up Testing Environment Provisioning System..."
    log "This creates legitimate development testing infrastructure"
    
    # Check dependencies
    if ! command -v docker &> /dev/null; then
        warn "Docker not found. Please install Docker first."
        exit 1
    fi
    
    if ! command -v python3 &> /dev/null; then
        warn "Python3 not found. Please install Python3 first."
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        warn "jq not found. Installing jq for CLI functionality..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y jq
        elif command -v yum &> /dev/null; then
            sudo yum install -y jq
        elif command -v brew &> /dev/null; then
            brew install jq
        else
            warn "Please install jq manually for full CLI functionality"
        fi
    fi
    
    # Run setup functions
    setup_directories
    setup_docker_network
    create_environment_manager
    create_environment_api
    create_environment_templates
    create_cli_tools
    create_monitoring
    create_automation_integration
    create_deployment
    
    log "✅ Testing Environment Provisioning System setup complete!"
    log ""
    log "🚀 Quick Start:"
    log "   1. Start the API: python3 ${REPO_PATH}/testing/api/environment_api.py"
    log "   2. Use CLI: ${REPO_PATH}/testing/cli/testenv list"
    log "   3. Create environment: ${REPO_PATH}/testing/cli/testenv create web 'My Test'"
    log ""
    log "📚 Available Commands:"
    log "   • testenv list              - List all environments"
    log "   • testenv create [type]     - Create new environment"
    log "   • testenv status [id]       - Check environment status"
    log "   • testenv destroy [id]      - Remove environment"
    log "   • testenv cleanup           - Clean old environments"
    log ""
    log "🔗 Integration:"
    log "   • API: http://localhost:5001/api/v1"
    log "   • Monitoring: Automatic resource tracking"
    log "   • Automation: Event-driven workflow integration"
}

# Run main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi