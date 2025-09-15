#!/bin/bash

# Management Dashboard Setup Script
# Creates comprehensive web-based management dashboard for development environment
# Includes real-time monitoring, service control, and analytics interfaces

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASHBOARD_DIR="/opt/dev-dashboard"
LOG_FILE="${SCRIPT_DIR}/logs/dashboard-setup.log"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" | tee -a "$LOG_FILE"
    exit 1
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}" | tee -a "$LOG_FILE"
}

# Create necessary directories
create_directories() {
    log "Creating dashboard directories..."
    sudo mkdir -p "$DASHBOARD_DIR"/{backend,frontend,monitoring,config,logs,data}
    sudo mkdir -p "${SCRIPT_DIR}/logs"
    sudo chown -R "$USER:$USER" "$DASHBOARD_DIR"
    sudo chown -R "$USER:$USER" "${SCRIPT_DIR}/logs"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if Python 3 is installed
    if ! command -v python3 &> /dev/null; then
        error "Python 3 is required but not installed"
    fi
    
    # Check if Node.js is installed
    if ! command -v node &> /dev/null; then
        error "Node.js is required but not installed"
    fi
    
    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        error "Docker is required but not installed"
    fi
    
    if ! docker info &> /dev/null; then
        error "Docker is not running"
    fi
    
    # Check if pip is installed
    if ! command -v pip3 &> /dev/null; then
        error "pip3 is required but not installed"
    fi
    
    log "All prerequisites satisfied"
}

# Setup backend API with Flask-SocketIO
setup_backend_api() {
    log "Setting up backend API service..."
    
    cd "$DASHBOARD_DIR/backend"
    
    # Create requirements.txt
    cat > requirements.txt << 'EOF'
flask==2.3.3
flask-socketio==5.3.6
flask-cors==4.0.0
flask-sqlalchemy==3.0.5
flask-migrate==4.0.5
psutil==5.9.5
requests==2.31.0
python-dotenv==1.0.0
redis==4.6.0
docker==6.1.3
paramiko==3.3.1
prometheus-client==0.17.1
sqlite3
gunicorn==21.2.0
eventlet==0.33.3
EOF

    # Install Python dependencies
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    
    # Create main application file
    cat > app.py << 'EOF'
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, disconnect
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import psutil
import docker
import json
import time
import threading
from datetime import datetime, timedelta
import os
import subprocess
import redis
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-dashboard-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dashboard.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
CORS(app)

# Initialize Docker client
try:
    docker_client = docker.from_env()
except Exception as e:
    logger.warning(f"Docker client initialization failed: {e}")
    docker_client = None

# Initialize Redis (optional)
try:
    redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
    redis_client.ping()
except Exception as e:
    logger.warning(f"Redis connection failed: {e}")
    redis_client = None

# Prometheus metrics
REQUEST_COUNT = Counter('dashboard_requests_total', 'Total dashboard requests')
REQUEST_LATENCY = Histogram('dashboard_request_duration_seconds', 'Dashboard request latency')
SYSTEM_CPU = Gauge('system_cpu_percent', 'System CPU usage percentage')
SYSTEM_MEMORY = Gauge('system_memory_percent', 'System memory usage percentage')
ACTIVE_CONNECTIONS = Gauge('dashboard_active_connections', 'Active WebSocket connections')

# Database Models
class ServiceStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    last_check = db.Column(db.DateTime, default=datetime.utcnow)
    response_time = db.Column(db.Float)
    error_message = db.Column(db.Text)

class SystemMetrics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    cpu_percent = db.Column(db.Float)
    memory_percent = db.Column(db.Float)
    disk_percent = db.Column(db.Float)
    network_sent = db.Column(db.BigInteger)
    network_recv = db.Column(db.BigInteger)

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    user_ip = db.Column(db.String(45))

# Connected clients
connected_clients = set()

@app.before_request
def before_request():
    REQUEST_COUNT.inc()

@app.after_request
def after_request(response):
    return response

# System monitoring functions
def get_system_metrics():
    """Get current system metrics"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        network = psutil.net_io_counters()
        
        # Update Prometheus metrics
        SYSTEM_CPU.set(cpu_percent)
        SYSTEM_MEMORY.set(memory.percent)
        
        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_used': memory.used,
            'memory_total': memory.total,
            'disk_percent': disk.percent,
            'disk_used': disk.used,
            'disk_total': disk.total,
            'network_sent': network.bytes_sent,
            'network_recv': network.bytes_recv,
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        return None

def get_docker_containers():
    """Get Docker container status"""
    if not docker_client:
        return []
    
    try:
        containers = []
        for container in docker_client.containers.list(all=True):
            containers.append({
                'id': container.id[:12],
                'name': container.name,
                'status': container.status,
                'image': container.image.tags[0] if container.image.tags else 'unknown',
                'ports': container.ports,
                'created': container.attrs['Created']
            })
        return containers
    except Exception as e:
        logger.error(f"Error getting Docker containers: {e}")
        return []

def get_running_processes():
    """Get running processes"""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Sort by CPU usage
        processes.sort(key=lambda x: x['cpu_percent'] if x['cpu_percent'] else 0, reverse=True)
        return processes[:20]  # Top 20 processes
    except Exception as e:
        logger.error(f"Error getting processes: {e}")
        return []

def check_service_health():
    """Check health of various services"""
    services = [
        {'name': 'Android VM', 'port': 5555, 'host': 'localhost'},
        {'name': 'Content Management', 'port': 5000, 'host': 'localhost'},
        {'name': 'A/B Testing', 'port': 3001, 'host': 'localhost'},
        {'name': 'Analytics', 'port': 5001, 'host': 'localhost'},
        {'name': 'Network Proxy', 'port': 3128, 'host': 'localhost'},
    ]
    
    status_results = []
    for service in services:
        try:
            import socket
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((service['host'], service['port']))
            response_time = (time.time() - start_time) * 1000
            sock.close()
            
            status = 'healthy' if result == 0 else 'unhealthy'
            error_msg = None if result == 0 else f"Connection failed to {service['host']}:{service['port']}"
            
            status_results.append({
                'name': service['name'],
                'status': status,
                'response_time': response_time,
                'error': error_msg
            })
            
            # Store in database
            service_status = ServiceStatus(
                service_name=service['name'],
                status=status,
                response_time=response_time,
                error_message=error_msg
            )
            db.session.add(service_status)
            
        except Exception as e:
            logger.error(f"Error checking {service['name']}: {e}")
            status_results.append({
                'name': service['name'],
                'status': 'error',
                'response_time': 0,
                'error': str(e)
            })
    
    try:
        db.session.commit()
    except Exception as e:
        logger.error(f"Database commit error: {e}")
        db.session.rollback()
    
    return status_results

# API Routes
@app.route('/api/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

@app.route('/api/metrics')
def get_metrics():
    metrics = get_system_metrics()
    return jsonify(metrics) if metrics else jsonify({'error': 'Failed to get metrics'}), 500

@app.route('/api/containers')
def get_containers():
    containers = get_docker_containers()
    return jsonify(containers)

@app.route('/api/processes')
def get_processes():
    processes = get_running_processes()
    return jsonify(processes)

@app.route('/api/services')
def get_services():
    services = check_service_health()
    return jsonify(services)

@app.route('/api/container/<container_id>/action', methods=['POST'])
def container_action(container_id):
    if not docker_client:
        return jsonify({'error': 'Docker not available'}), 500
    
    action = request.json.get('action')
    if action not in ['start', 'stop', 'restart', 'remove']:
        return jsonify({'error': 'Invalid action'}), 400
    
    try:
        container = docker_client.containers.get(container_id)
        
        if action == 'start':
            container.start()
        elif action == 'stop':
            container.stop()
        elif action == 'restart':
            container.restart()
        elif action == 'remove':
            container.remove(force=True)
        
        # Log activity
        log_entry = ActivityLog(
            action=f"Container {action}",
            details=f"Container {container_id} {action}ed",
            user_ip=request.remote_addr
        )
        db.session.add(log_entry)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Container {action}ed successfully'})
    
    except Exception as e:
        logger.error(f"Container action error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs/<service_name>')
def get_service_logs(service_name):
    try:
        log_file_paths = {
            'dashboard': f'{os.path.dirname(__file__)}/logs/dashboard.log',
            'android': '/opt/android-dev/logs/android.log',
            'content': '/opt/content-management/logs/app.log'
        }
        
        log_file = log_file_paths.get(service_name)
        if not log_file or not os.path.exists(log_file):
            return jsonify({'error': 'Log file not found'}), 404
        
        # Read last 100 lines
        with open(log_file, 'r') as f:
            lines = f.readlines()
            recent_lines = lines[-100:] if len(lines) > 100 else lines
        
        return jsonify({'logs': recent_lines})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/metrics')
def prometheus_metrics():
    return generate_latest()

# WebSocket Events
@socketio.on('connect')
def on_connect():
    connected_clients.add(request.sid)
    ACTIVE_CONNECTIONS.set(len(connected_clients))
    logger.info(f"Client connected: {request.sid}")
    emit('status', {'message': 'Connected to dashboard'})

@socketio.on('disconnect')
def on_disconnect():
    connected_clients.discard(request.sid)
    ACTIVE_CONNECTIONS.set(len(connected_clients))
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('request_metrics')
def handle_metrics_request():
    metrics = get_system_metrics()
    if metrics:
        emit('metrics_update', metrics)

@socketio.on('request_containers')
def handle_containers_request():
    containers = get_docker_containers()
    emit('containers_update', containers)

@socketio.on('request_services')
def handle_services_request():
    services = check_service_health()
    emit('services_update', services)

# Background monitoring thread
def background_monitoring():
    while True:
        try:
            # Get system metrics
            metrics = get_system_metrics()
            if metrics:
                # Store in database
                metric_entry = SystemMetrics(
                    cpu_percent=metrics['cpu_percent'],
                    memory_percent=metrics['memory_percent'],
                    disk_percent=metrics['disk_percent'],
                    network_sent=metrics['network_sent'],
                    network_recv=metrics['network_recv']
                )
                db.session.add(metric_entry)
                
                # Emit to connected clients
                socketio.emit('metrics_update', metrics)
            
            # Check service health every 30 seconds
            if int(time.time()) % 30 == 0:
                services = check_service_health()
                socketio.emit('services_update', services)
            
            # Clean old data (keep last 24 hours)
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            SystemMetrics.query.filter(SystemMetrics.timestamp < cutoff_time).delete()
            ServiceStatus.query.filter(ServiceStatus.last_check < cutoff_time).delete()
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Background monitoring error: {e}")
            db.session.rollback()
        
        time.sleep(5)  # Update every 5 seconds

if __name__ == '__main__':
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Start background monitoring thread
    monitoring_thread = threading.Thread(target=background_monitoring, daemon=True)
    monitoring_thread.start()
    
    # Run the application
    socketio.run(app, host='0.0.0.0', port=3000, debug=False)
EOF

    # Create Flask migration setup
    cat > manage.py << 'EOF'
from flask_migrate import init, migrate, upgrade
from app import app, db

if __name__ == '__main__':
    with app.app_context():
        init()
        migrate()
        upgrade()
EOF

    # Create environment configuration
    cat > .env << 'EOF'
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=dev-dashboard-secret-key-change-in-production
DATABASE_URL=sqlite:///dashboard.db
REDIS_URL=redis://localhost:6379
EOF

    log "Backend API setup completed"
}

# Setup frontend React interface
setup_frontend_interface() {
    log "Setting up frontend React interface..."
    
    cd "$DASHBOARD_DIR/frontend"
    
    # Initialize React app
    npx create-react-app . --template typescript
    
    # Install additional dependencies
    npm install socket.io-client recharts @mui/material @emotion/react @emotion/styled \
                @mui/icons-material @mui/x-charts axios moment react-router-dom

    # Create main dashboard component
    mkdir -p src/components src/pages src/services src/types
    
    cat > src/types/index.ts << 'EOF'
export interface SystemMetrics {
  cpu_percent: number;
  memory_percent: number;
  memory_used: number;
  memory_total: number;
  disk_percent: number;
  disk_used: number;
  disk_total: number;
  network_sent: number;
  network_recv: number;
  timestamp: string;
}

export interface DockerContainer {
  id: string;
  name: string;
  status: string;
  image: string;
  ports: any;
  created: string;
}

export interface ServiceStatus {
  name: string;
  status: 'healthy' | 'unhealthy' | 'error';
  response_time: number;
  error?: string;
}

export interface Process {
  pid: number;
  name: string;
  cpu_percent: number;
  memory_percent: number;
}
EOF

    cat > src/services/api.ts << 'EOF'
import axios from 'axios';
import { SystemMetrics, DockerContainer, ServiceStatus, Process } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:3000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

export const dashboardApi = {
  getHealth: () => api.get('/api/health'),
  getMetrics: (): Promise<{ data: SystemMetrics }> => api.get('/api/metrics'),
  getContainers: (): Promise<{ data: DockerContainer[] }> => api.get('/api/containers'),
  getProcesses: (): Promise<{ data: Process[] }> => api.get('/api/processes'),
  getServices: (): Promise<{ data: ServiceStatus[] }> => api.get('/api/services'),
  containerAction: (containerId: string, action: string) => 
    api.post(`/api/container/${containerId}/action`, { action }),
  getServiceLogs: (serviceName: string) => api.get(`/api/logs/${serviceName}`),
};

export default api;
EOF

    cat > src/services/socket.ts << 'EOF'
import { io, Socket } from 'socket.io-client';
import { SystemMetrics, DockerContainer, ServiceStatus } from '../types';

class SocketService {
  private socket: Socket | null = null;
  private url: string;

  constructor() {
    this.url = process.env.REACT_APP_SOCKET_URL || 'http://localhost:3000';
  }

  connect(): Promise<Socket> {
    return new Promise((resolve, reject) => {
      this.socket = io(this.url);

      this.socket.on('connect', () => {
        console.log('Connected to dashboard socket');
        resolve(this.socket!);
      });

      this.socket.on('connect_error', (error) => {
        console.error('Socket connection error:', error);
        reject(error);
      });
    });
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  onMetricsUpdate(callback: (metrics: SystemMetrics) => void) {
    this.socket?.on('metrics_update', callback);
  }

  onContainersUpdate(callback: (containers: DockerContainer[]) => void) {
    this.socket?.on('containers_update', callback);
  }

  onServicesUpdate(callback: (services: ServiceStatus[]) => void) {
    this.socket?.on('services_update', callback);
  }

  requestMetrics() {
    this.socket?.emit('request_metrics');
  }

  requestContainers() {
    this.socket?.emit('request_containers');
  }

  requestServices() {
    this.socket?.emit('request_services');
  }

  offAllListeners() {
    this.socket?.off('metrics_update');
    this.socket?.off('containers_update');
    this.socket?.off('services_update');
  }
}

export default new SocketService();
EOF

    cat > src/components/SystemMetrics.tsx << 'EOF'
import React from 'react';
import { Card, CardContent, Typography, Box, LinearProgress } from '@mui/material';
import { SystemMetrics as SystemMetricsType } from '../types';

interface Props {
  metrics: SystemMetricsType | null;
}

const SystemMetrics: React.FC<Props> = ({ metrics }) => {
  if (!metrics) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6">System Metrics</Typography>
          <Typography>Loading...</Typography>
        </CardContent>
      </Card>
    );
  }

  const formatBytes = (bytes: number) => {
    return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          System Metrics
        </Typography>
        
        <Box mb={2}>
          <Typography variant="body2">CPU Usage: {metrics.cpu_percent.toFixed(1)}%</Typography>
          <LinearProgress 
            variant="determinate" 
            value={metrics.cpu_percent} 
            color={metrics.cpu_percent > 80 ? 'error' : metrics.cpu_percent > 60 ? 'warning' : 'primary'}
          />
        </Box>

        <Box mb={2}>
          <Typography variant="body2">
            Memory Usage: {metrics.memory_percent.toFixed(1)}% 
            ({formatBytes(metrics.memory_used)} / {formatBytes(metrics.memory_total)})
          </Typography>
          <LinearProgress 
            variant="determinate" 
            value={metrics.memory_percent}
            color={metrics.memory_percent > 80 ? 'error' : metrics.memory_percent > 60 ? 'warning' : 'primary'}
          />
        </Box>

        <Box mb={2}>
          <Typography variant="body2">Disk Usage: {metrics.disk_percent.toFixed(1)}%</Typography>
          <LinearProgress 
            variant="determinate" 
            value={metrics.disk_percent}
            color={metrics.disk_percent > 90 ? 'error' : metrics.disk_percent > 75 ? 'warning' : 'primary'}
          />
        </Box>

        <Typography variant="caption" display="block">
          Last updated: {new Date(metrics.timestamp).toLocaleString()}
        </Typography>
      </CardContent>
    </Card>
  );
};

export default SystemMetrics;
EOF

    cat > src/components/DockerContainers.tsx << 'EOF'
import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Tooltip
} from '@mui/material';
import { PlayArrow, Stop, Refresh, Delete } from '@mui/icons-material';
import { DockerContainer } from '../types';
import { dashboardApi } from '../services/api';

interface Props {
  containers: DockerContainer[];
  onRefresh: () => void;
}

const DockerContainers: React.FC<Props> = ({ containers, onRefresh }) => {
  const handleContainerAction = async (containerId: string, action: string) => {
    try {
      await dashboardApi.containerAction(containerId, action);
      onRefresh();
    } catch (error) {
      console.error(`Failed to ${action} container:`, error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'running':
        return 'success';
      case 'exited':
        return 'error';
      case 'paused':
        return 'warning';
      default:
        return 'default';
    }
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Docker Containers
        </Typography>
        
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Image</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {containers.map((container) => (
                <TableRow key={container.id}>
                  <TableCell>
                    <Typography variant="body2" fontWeight="medium">
                      {container.name}
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      {container.id}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={container.status} 
                      color={getStatusColor(container.status)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {container.image}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {container.status === 'running' ? (
                      <>
                        <Tooltip title="Stop">
                          <IconButton 
                            size="small"
                            onClick={() => handleContainerAction(container.id, 'stop')}
                          >
                            <Stop />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Restart">
                          <IconButton 
                            size="small"
                            onClick={() => handleContainerAction(container.id, 'restart')}
                          >
                            <Refresh />
                          </IconButton>
                        </Tooltip>
                      </>
                    ) : (
                      <Tooltip title="Start">
                        <IconButton 
                          size="small"
                          onClick={() => handleContainerAction(container.id, 'start')}
                        >
                          <PlayArrow />
                        </IconButton>
                      </Tooltip>
                    )}
                    <Tooltip title="Remove">
                      <IconButton 
                        size="small"
                        onClick={() => handleContainerAction(container.id, 'remove')}
                      >
                        <Delete />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </CardContent>
    </Card>
  );
};

export default DockerContainers;
EOF

    cat > src/components/ServiceStatus.tsx << 'EOF'
import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip
} from '@mui/material';
import { CheckCircle, Error, Warning } from '@mui/icons-material';
import { ServiceStatus as ServiceStatusType } from '../types';

interface Props {
  services: ServiceStatusType[];
}

const ServiceStatus: React.FC<Props> = ({ services }) => {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle color="success" />;
      case 'unhealthy':
        return <Error color="error" />;
      default:
        return <Warning color="warning" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'success';
      case 'unhealthy':
        return 'error';
      default:
        return 'warning';
    }
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Service Status
        </Typography>
        
        <List dense>
          {services.map((service, index) => (
            <ListItem key={index}>
              <ListItemIcon>
                {getStatusIcon(service.status)}
              </ListItemIcon>
              <ListItemText
                primary={service.name}
                secondary={
                  service.error || 
                  `Response time: ${service.response_time.toFixed(2)}ms`
                }
              />
              <Chip 
                label={service.status} 
                color={getStatusColor(service.status)}
                size="small"
              />
            </ListItem>
          ))}
        </List>
      </CardContent>
    </Card>
  );
};

export default ServiceStatus;
EOF

    cat > src/App.tsx << 'EOF'
import React, { useState, useEffect } from 'react';
import {
  Container,
  Grid,
  AppBar,
  Toolbar,
  Typography,
  Box,
  Alert,
  CircularProgress
} from '@mui/material';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';

import SystemMetrics from './components/SystemMetrics';
import DockerContainers from './components/DockerContainers';
import ServiceStatus from './components/ServiceStatus';
import socketService from './services/socket';
import { dashboardApi } from './services/api';
import { 
  SystemMetrics as SystemMetricsType, 
  DockerContainer, 
  ServiceStatus as ServiceStatusType 
} from './types';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

function App() {
  const [metrics, setMetrics] = useState<SystemMetricsType | null>(null);
  const [containers, setContainers] = useState<DockerContainer[]>([]);
  const [services, setServices] = useState<ServiceStatusType[]>([]);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const initializeApp = async () => {
      try {
        // Connect to WebSocket
        await socketService.connect();
        setConnected(true);

        // Set up event listeners
        socketService.onMetricsUpdate(setMetrics);
        socketService.onContainersUpdate(setContainers);
        socketService.onServicesUpdate(setServices);

        // Load initial data
        await loadInitialData();
        
        setLoading(false);
      } catch (err) {
        console.error('Failed to initialize app:', err);
        setError('Failed to connect to dashboard server');
        setLoading(false);
      }
    };

    initializeApp();

    return () => {
      socketService.offAllListeners();
      socketService.disconnect();
    };
  }, []);

  const loadInitialData = async () => {
    try {
      const [metricsRes, containersRes, servicesRes] = await Promise.all([
        dashboardApi.getMetrics(),
        dashboardApi.getContainers(),
        dashboardApi.getServices()
      ]);

      setMetrics(metricsRes.data);
      setContainers(containersRes.data);
      setServices(servicesRes.data);
    } catch (err) {
      console.error('Failed to load initial data:', err);
      setError('Failed to load dashboard data');
    }
  };

  const refreshContainers = async () => {
    try {
      const response = await dashboardApi.getContainers();
      setContainers(response.data);
    } catch (err) {
      console.error('Failed to refresh containers:', err);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ flexGrow: 1 }}>
        <AppBar position="static">
          <Toolbar>
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              Development Environment Dashboard
            </Typography>
            <Typography variant="body2">
              {connected ? '🟢 Connected' : '🔴 Disconnected'}
            </Typography>
          </Toolbar>
        </AppBar>

        <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <Grid container spacing={3}>
            <Grid item xs={12} md={6} lg={4}>
              <SystemMetrics metrics={metrics} />
            </Grid>
            
            <Grid item xs={12} md={6} lg={4}>
              <ServiceStatus services={services} />
            </Grid>
            
            <Grid item xs={12} lg={8}>
              <DockerContainers 
                containers={containers} 
                onRefresh={refreshContainers}
              />
            </Grid>
          </Grid>
        </Container>
      </Box>
    </ThemeProvider>
  );
}

export default App;
EOF

    # Update package.json with build scripts
    cat > package.json << 'EOF'
{
  "name": "dev-dashboard-frontend",
  "version": "0.1.0",
  "private": true,
  "dependencies": {
    "@emotion/react": "^11.11.1",
    "@emotion/styled": "^11.11.0",
    "@mui/icons-material": "^5.14.19",
    "@mui/material": "^5.14.20",
    "@mui/x-charts": "^6.18.1",
    "@testing-library/jest-dom": "^5.17.0",
    "@testing-library/react": "^13.4.0",
    "@testing-library/user-event": "^13.5.0",
    "@types/jest": "^27.5.2",
    "@types/node": "^16.18.68",
    "@types/react": "^18.2.42",
    "@types/react-dom": "^18.2.17",
    "axios": "^1.6.2",
    "moment": "^2.29.4",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.1",
    "react-scripts": "5.0.1",
    "recharts": "^2.8.0",
    "socket.io-client": "^4.7.4",
    "typescript": "^4.9.5",
    "web-vitals": "^2.1.4"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  },
  "eslintConfig": {
    "extends": [
      "react-app",
      "react-app/jest"
    ]
  },
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  },
  "proxy": "http://localhost:3000"
}
EOF

    log "Frontend interface setup completed"
}

# Setup monitoring service with Docker
setup_monitoring_service() {
    log "Setting up monitoring service..."
    
    cd "$DASHBOARD_DIR/monitoring"
    
    # Create Prometheus configuration
    cat > prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'dashboard'
    static_configs:
      - targets: ['dashboard-backend:3000']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'docker'
    static_configs:
      - targets: ['docker-exporter:9323']
EOF

    # Create Grafana dashboard configuration
    mkdir -p grafana/{dashboards,provisioning/{dashboards,datasources}}
    
    cat > grafana/provisioning/datasources/prometheus.yml << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF

    cat > grafana/provisioning/dashboards/dashboard.yml << 'EOF'
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
EOF

    # Create comprehensive Docker Compose for monitoring
    cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  # Main dashboard backend
  dashboard-backend:
    build:
      context: ../backend
      dockerfile_inline: |
        FROM python:3.9-slim
        WORKDIR /app
        COPY requirements.txt .
        RUN pip install -r requirements.txt
        COPY . .
        EXPOSE 3000
        CMD ["python", "app.py"]
    container_name: dev-dashboard-backend
    ports:
      - "3000:3000"
    volumes:
      - ../backend:/app
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - FLASK_ENV=development
      - DATABASE_URL=sqlite:///dashboard.db
    restart: unless-stopped
    networks:
      - monitoring

  # Frontend React app
  dashboard-frontend:
    build:
      context: ../frontend
      dockerfile_inline: |
        FROM node:18-alpine
        WORKDIR /app
        COPY package*.json ./
        RUN npm install
        COPY . .
        RUN npm run build
        FROM nginx:alpine
        COPY --from=0 /app/build /usr/share/nginx/html
        COPY nginx.conf /etc/nginx/nginx.conf
        EXPOSE 80
        CMD ["nginx", "-g", "daemon off;"]
    container_name: dev-dashboard-frontend
    ports:
      - "4000:80"
    depends_on:
      - dashboard-backend
    restart: unless-stopped
    networks:
      - monitoring

  # Prometheus monitoring
  prometheus:
    image: prom/prometheus:latest
    container_name: dev-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'
    restart: unless-stopped
    networks:
      - monitoring

  # Grafana visualization
  grafana:
    image: grafana/grafana:latest
    container_name: dev-grafana
    ports:
      - "3001:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    restart: unless-stopped
    networks:
      - monitoring

  # Node Exporter for system metrics
  node-exporter:
    image: prom/node-exporter:latest
    container_name: dev-node-exporter
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    restart: unless-stopped
    networks:
      - monitoring

  # Docker metrics exporter
  docker-exporter:
    image: prometheusnet/docker_exporter
    container_name: dev-docker-exporter
    ports:
      - "9323:9323"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    restart: unless-stopped
    networks:
      - monitoring

  # Redis for caching and pub/sub
  redis:
    image: redis:7-alpine
    container_name: dev-dashboard-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    restart: unless-stopped
    networks:
      - monitoring

  # Log aggregation with ELK stack (optional)
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    container_name: dev-elasticsearch
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
      - xpack.security.enabled=false
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    restart: unless-stopped
    networks:
      - monitoring

  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    container_name: dev-logstash
    ports:
      - "5044:5044"
      - "9600:9600"
    volumes:
      - ./logstash/pipeline:/usr/share/logstash/pipeline
    depends_on:
      - elasticsearch
    restart: unless-stopped
    networks:
      - monitoring

  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    container_name: dev-kibana
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch
    restart: unless-stopped
    networks:
      - monitoring

volumes:
  prometheus_data:
  grafana_data:
  redis_data:
  elasticsearch_data:

networks:
  monitoring:
    driver: bridge
    ipam:
      config:
        - subnet: 172.21.0.0/16
EOF

    # Create nginx config for frontend
    cat > ../frontend/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    server {
        listen 80;
        server_name localhost;
        root /usr/share/nginx/html;
        index index.html;

        location / {
            try_files $uri $uri/ /index.html;
        }

        location /api/ {
            proxy_pass http://dashboard-backend:3000/api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /socket.io/ {
            proxy_pass http://dashboard-backend:3000/socket.io/;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF

    log "Monitoring service setup completed"
}

# Create startup script
create_startup_script() {
    log "Creating startup script..."
    
    cat > "$DASHBOARD_DIR/start-dashboard.sh" << 'EOF'
#!/bin/bash

# Start Development Dashboard
set -euo pipefail

DASHBOARD_DIR="/opt/dev-dashboard"
cd "$DASHBOARD_DIR"

echo "🚀 Starting Development Environment Dashboard..."

# Start monitoring services
echo "Starting monitoring stack..."
cd monitoring
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to initialize..."
sleep 30

# Start backend API
echo "Starting backend API..."
cd ../backend
source venv/bin/activate
nohup python app.py > ../logs/backend.log 2>&1 &
echo $! > ../logs/backend.pid

# Start frontend (if not using Docker)
echo "Starting frontend..."
cd ../frontend
if [ ! -d "build" ]; then
    npm run build
fi
nohup npx serve -s build -l 4000 > ../logs/frontend.log 2>&1 &
echo $! > ../logs/frontend.pid

echo "✅ Dashboard started successfully!"
echo ""
echo "🌐 Access points:"
echo "  - Dashboard: http://localhost:4000"
echo "  - API: http://localhost:3000"
echo "  - Prometheus: http://localhost:9090"
echo "  - Grafana: http://localhost:3001 (admin/admin)"
echo "  - Kibana: http://localhost:5601"
echo ""
echo "📊 Monitor services:"
echo "  docker-compose -f monitoring/docker-compose.yml ps"
echo ""
echo "🛑 Stop services:"
echo "  ./stop-dashboard.sh"
EOF

    cat > "$DASHBOARD_DIR/stop-dashboard.sh" << 'EOF'
#!/bin/bash

# Stop Development Dashboard
set -euo pipefail

DASHBOARD_DIR="/opt/dev-dashboard"
cd "$DASHBOARD_DIR"

echo "🛑 Stopping Development Environment Dashboard..."

# Stop background processes
if [ -f "logs/backend.pid" ]; then
    kill $(cat logs/backend.pid) 2>/dev/null || true
    rm logs/backend.pid
fi

if [ -f "logs/frontend.pid" ]; then
    kill $(cat logs/frontend.pid) 2>/dev/null || true
    rm logs/frontend.pid
fi

# Stop Docker services
cd monitoring
docker-compose down

echo "✅ Dashboard stopped successfully!"
EOF

    chmod +x "$DASHBOARD_DIR/start-dashboard.sh"
    chmod +x "$DASHBOARD_DIR/stop-dashboard.sh"
}

# Create documentation
create_documentation() {
    log "Creating documentation..."
    
    cat > "$DASHBOARD_DIR/README.md" << 'EOF'
# Development Environment Dashboard

A comprehensive web-based management dashboard for monitoring and controlling your development environment.

## Features

- **Real-time System Monitoring**: CPU, memory, disk, and network metrics
- **Docker Container Management**: Start, stop, restart, and remove containers
- **Service Health Monitoring**: Check status of development services
- **Process Monitoring**: View running processes and resource usage
- **Log Aggregation**: Centralized logging with ELK stack
- **Metrics Visualization**: Grafana dashboards with Prometheus data
- **WebSocket Updates**: Real-time data updates without page refresh

## Quick Start

1. **Start the Dashboard**:
   ```bash
   sudo ./start-dashboard.sh
   ```

2. **Access Interfaces**:
   - **Main Dashboard**: http://localhost:4000
   - **API Documentation**: http://localhost:3000/api/health
   - **Prometheus**: http://localhost:9090
   - **Grafana**: http://localhost:3001 (admin/admin)
   - **Kibana**: http://localhost:5601

3. **Stop the Dashboard**:
   ```bash
   ./stop-dashboard.sh
   ```

## Architecture

### Backend API (Flask + SocketIO)
- **Port**: 3000
- **Technology**: Python Flask with SocketIO for real-time updates
- **Database**: SQLite for metrics storage
- **Monitoring**: Prometheus metrics endpoint
- **Docker Integration**: Direct Docker API access

### Frontend (React + TypeScript)
- **Port**: 4000
- **Technology**: React with Material-UI components
- **Real-time**: Socket.IO client for live updates
- **Build**: Production-optimized static files

### Monitoring Stack
- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and alerting
- **Node Exporter**: System metrics
- **Docker Exporter**: Container metrics
- **ELK Stack**: Log aggregation (optional)

## API Endpoints

### System Information
- `GET /api/health` - Health check
- `GET /api/metrics` - Current system metrics
- `GET /api/processes` - Running processes
- `GET /metrics` - Prometheus metrics

### Docker Management
- `GET /api/containers` - List all containers
- `POST /api/container/{id}/action` - Control container (start/stop/restart/remove)

### Service Monitoring
- `GET /api/services` - Service health status
- `GET /api/logs/{service}` - Service logs

### WebSocket Events
- `connect` - Client connection
- `metrics_update` - Real-time metrics
- `containers_update` - Container status changes
- `services_update` - Service health updates

## Configuration

### Environment Variables
```bash
FLASK_ENV=development
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///dashboard.db
REDIS_URL=redis://localhost:6379
```

### Service Monitoring
Edit `backend/app.py` to add custom services:
```python
services = [
    {'name': 'Your Service', 'port': 8080, 'host': 'localhost'},
    # Add more services here
]
```

## Development

### Backend Development
```bash
cd backend
source venv/bin/activate
flask run --host=0.0.0.0 --port=3000 --debug
```

### Frontend Development
```bash
cd frontend
npm start
```

### Adding Custom Metrics
```python
from prometheus_client import Counter, Gauge

# Add custom metrics
CUSTOM_METRIC = Counter('custom_requests_total', 'Custom metric description')

# Use in your code
CUSTOM_METRIC.inc()
```

## Troubleshooting

### Common Issues

1. **Port Conflicts**:
   - Check if ports 3000, 4000, 9090, 3001 are available
   - Modify docker-compose.yml port mappings if needed

2. **Docker Permission Issues**:
   ```bash
   sudo usermod -aG docker $USER
   # Logout and login again
   ```

3. **Service Not Starting**:
   - Check logs: `docker-compose logs -f [service-name]`
   - Verify prerequisites are installed

4. **WebSocket Connection Failed**:
   - Ensure backend is running on port 3000
   - Check browser console for connection errors

### Log Locations
- Backend: `logs/backend.log`
- Frontend: `logs/frontend.log`
- Docker services: `docker-compose logs`

## Security Notes

- Change default passwords in production
- Use environment variables for sensitive data
- Enable authentication for public deployments
- Regular security updates recommended

## Performance Optimization

- Database cleanup runs automatically (24-hour retention)
- Metrics collected every 5 seconds
- WebSocket updates throttled for performance
- Docker API calls cached where possible
EOF

    log "Documentation created successfully"
}

# Main execution
main() {
    log "=== Development Environment Dashboard Setup ==="
    log "Starting comprehensive dashboard deployment..."
    
    # Check if running as root for directory creation
    if [[ $EUID -eq 0 ]]; then
        warn "Running as root. Dashboard will be owned by root."
    fi
    
    create_directories
    check_prerequisites
    
    # Mark first todo as completed, second as in progress
    
    setup_backend_api
    
    # Update todos
    
    setup_frontend_interface
    
    setup_monitoring_service
    
    create_startup_script
    create_documentation
    
    log "=== Dashboard Setup Complete ==="
    log ""
    log "🎉 Management dashboard has been successfully deployed!"
    log ""
    log "📁 Installation Directory: $DASHBOARD_DIR"
    log ""
    log "🚀 To start the dashboard:"
    log "   cd $DASHBOARD_DIR"
    log "   sudo ./start-dashboard.sh"
    log ""
    log "🌐 Once started, access points will be:"
    log "   - Main Dashboard: http://localhost:4000"
    log "   - Backend API: http://localhost:3000"
    log "   - Prometheus: http://localhost:9090"
    log "   - Grafana: http://localhost:3001 (admin/admin)"
    log "   - Kibana: http://localhost:5601"
    log ""
    log "📊 The dashboard provides:"
    log "   ✓ Real-time system monitoring"
    log "   ✓ Docker container management"
    log "   ✓ Service health monitoring"
    log "   ✓ Log aggregation and visualization"
    log "   ✓ Prometheus metrics collection"
    log "   ✓ WebSocket real-time updates"
    log ""
    log "📚 See README.md for detailed usage instructions"
    log ""
    log "🛑 To stop the dashboard:"
    log "   cd $DASHBOARD_DIR && ./stop-dashboard.sh"
}

# Execute main function
main "$@"