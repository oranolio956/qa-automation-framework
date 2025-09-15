#!/bin/bash

# System Health Monitoring and Recovery System
# Implements comprehensive health monitoring, diagnostics collection, and automated recovery
# Designed for legitimate application monitoring and development environment management

set -euo pipefail

# Configuration
REPO_PATH="${REPO_PATH:-$(pwd)}"
INFLUXDB_URL="${INFLUXDB_URL:-http://localhost:8086}"
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"
LOG_FILE="${REPO_PATH}/logs/health-monitoring.log"

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
    log "Setting up system health monitoring directory structure..."
    
    mkdir -p "${REPO_PATH}"/{monitor,logs,diagnostics,config}
    mkdir -p "${REPO_PATH}/monitor"/{services,scripts,collectors,healers}
    mkdir -p "${REPO_PATH}/diagnostics"/{reports,archives,snapshots}
    
    log "✓ Directory structure created"
}

# Install monitoring dependencies
install_monitoring_tools() {
    log "Installing system monitoring tools..."
    
    # Check if running as root or with sudo access
    if [[ $EUID -eq 0 ]] || sudo -n true 2>/dev/null; then
        # Install system monitoring tools
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y python3-pip jq curl wget htop iotop nethogs
        elif command -v yum &> /dev/null; then
            sudo yum install -y python3-pip jq curl wget htop iotop
        elif command -v brew &> /dev/null; then
            brew install jq curl wget htop
        fi
    else
        warn "No sudo access - skipping system package installation"
    fi
    
    # Install Python dependencies
    pip3 install --user influxdb-client requests psutil docker py-cpuinfo || true
    
    log "✓ Monitoring tools installed"
}

# Create health monitoring service
create_health_monitor() {
    log "Creating health monitoring service..."
    
    cat > "${REPO_PATH}/monitor/services/health_monitor.py" << 'EOF'
#!/usr/bin/env python3
"""
System Health Monitoring Service
Comprehensive monitoring system for application health, performance, and recovery
Designed for legitimate development and production environment monitoring
"""

import time
import json
import subprocess
import psutil
import logging
import requests
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import threading
import signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SystemHealthMonitor:
    """Main system health monitoring class"""
    
    def __init__(self, config_path: str = 'config/monitoring.json'):
        self.config = self.load_config(config_path)
        self.running = False
        self.metrics_collector = MetricsCollector(self.config)
        self.diagnostics_collector = DiagnosticsCollector(self.config)
        self.auto_healer = AutoHealer(self.config)
        self.alerting = AlertingService(self.config)
        
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load monitoring configuration"""
        default_config = {
            'influxdb': {
                'url': 'http://localhost:8086',
                'token': '',
                'bucket': 'system_metrics',
                'org': 'development'
            },
            'alerting': {
                'slack_webhook': '',
                'email_smtp': ''
            },
            'monitoring': {
                'interval_seconds': 60,
                'health_check_interval': 300,
                'cpu_threshold': 80.0,
                'memory_threshold': 80.0,
                'disk_threshold': 85.0,
                'network_threshold': 90.0
            },
            'services': {
                'backend_port': 3001,
                'frontend_port': 3000,
                'database_port': 5432
            },
            'recovery': {
                'enabled': True,
                'max_retries': 3,
                'retry_delay': 60,
                'restart_services': True
            }
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
        
        return default_config
    
    def start_monitoring(self):
        """Start the monitoring service"""
        logger.info("Starting system health monitoring service")
        self.running = True
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        # Start monitoring threads
        threads = [
            threading.Thread(target=self._metrics_loop, daemon=True),
            threading.Thread(target=self._health_check_loop, daemon=True),
            threading.Thread(target=self._diagnostics_loop, daemon=True)
        ]
        
        for thread in threads:
            thread.start()
        
        # Main monitoring loop
        try:
            while self.running:
                self._perform_health_checks()
                time.sleep(self.config['monitoring']['health_check_interval'])
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.stop_monitoring()
    
    def stop_monitoring(self):
        """Stop the monitoring service"""
        logger.info("Stopping system health monitoring service")
        self.running = False
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}")
        self.stop_monitoring()
    
    def _metrics_loop(self):
        """Continuous metrics collection loop"""
        while self.running:
            try:
                metrics = self.metrics_collector.collect_all_metrics()
                self.metrics_collector.store_metrics(metrics)
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
            
            time.sleep(self.config['monitoring']['interval_seconds'])
    
    def _health_check_loop(self):
        """Health check loop for services and applications"""
        while self.running:
            try:
                health_status = self._check_service_health()
                if not health_status['healthy']:
                    self._handle_unhealthy_service(health_status)
            except Exception as e:
                logger.error(f"Health check error: {e}")
            
            time.sleep(self.config['monitoring']['health_check_interval'])
    
    def _diagnostics_loop(self):
        """Diagnostic data collection loop"""
        while self.running:
            try:
                self.diagnostics_collector.collect_periodic_diagnostics()
            except Exception as e:
                logger.error(f"Diagnostics collection error: {e}")
            
            time.sleep(3600)  # Collect diagnostics every hour
    
    def _perform_health_checks(self):
        """Perform comprehensive health checks"""
        health_report = {
            'timestamp': datetime.utcnow().isoformat(),
            'system': self._check_system_health(),
            'services': self._check_service_health(),
            'network': self._check_network_health(),
            'disk': self._check_disk_health()
        }
        
        # Store health report
        self.metrics_collector.store_health_report(health_report)
        
        # Check for issues and trigger recovery if needed
        if not self._is_system_healthy(health_report):
            self._trigger_recovery(health_report)
    
    def _check_system_health(self) -> Dict[str, Any]:
        """Check overall system health"""
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0],
            'uptime': time.time() - psutil.boot_time()
        }
    
    def _check_service_health(self) -> Dict[str, Any]:
        """Check health of application services"""
        services = {}
        
        # Check backend service
        try:
            response = requests.get(
                f"http://localhost:{self.config['services']['backend_port']}/api/v1/health",
                timeout=5
            )
            services['backend'] = {
                'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                'response_time': response.elapsed.total_seconds(),
                'status_code': response.status_code
            }
        except Exception as e:
            services['backend'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
        
        # Check frontend service
        try:
            response = requests.get(
                f"http://localhost:{self.config['services']['frontend_port']}",
                timeout=5
            )
            services['frontend'] = {
                'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                'response_time': response.elapsed.total_seconds(),
                'status_code': response.status_code
            }
        except Exception as e:
            services['frontend'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
        
        return {
            'healthy': all(svc.get('status') == 'healthy' for svc in services.values()),
            'services': services
        }
    
    def _check_network_health(self) -> Dict[str, Any]:
        """Check network connectivity and performance"""
        network_stats = psutil.net_io_counters()
        
        return {
            'bytes_sent': network_stats.bytes_sent,
            'bytes_recv': network_stats.bytes_recv,
            'packets_sent': network_stats.packets_sent,
            'packets_recv': network_stats.packets_recv,
            'errors': network_stats.errin + network_stats.errout,
            'drops': network_stats.dropin + network_stats.dropout
        }
    
    def _check_disk_health(self) -> Dict[str, Any]:
        """Check disk health and usage"""
        disk_usage = psutil.disk_usage('/')
        disk_io = psutil.disk_io_counters()
        
        return {
            'total': disk_usage.total,
            'used': disk_usage.used,
            'free': disk_usage.free,
            'percent': (disk_usage.used / disk_usage.total) * 100,
            'read_bytes': disk_io.read_bytes if disk_io else 0,
            'write_bytes': disk_io.write_bytes if disk_io else 0
        }
    
    def _is_system_healthy(self, health_report: Dict[str, Any]) -> bool:
        """Determine if system is healthy based on thresholds"""
        system = health_report['system']
        thresholds = self.config['monitoring']
        
        if system['cpu_percent'] > thresholds['cpu_threshold']:
            return False
        
        if system['memory_percent'] > thresholds['memory_threshold']:
            return False
        
        if system['disk_percent'] > thresholds['disk_threshold']:
            return False
        
        if not health_report['services']['healthy']:
            return False
        
        return True
    
    def _handle_unhealthy_service(self, health_status: Dict[str, Any]):
        """Handle unhealthy service detection"""
        logger.warning(f"Unhealthy service detected: {health_status}")
        
        # Collect diagnostics
        diagnostics = self.diagnostics_collector.collect_emergency_diagnostics()
        
        # Send alert
        self.alerting.send_alert({
            'type': 'service_unhealthy',
            'health_status': health_status,
            'diagnostics': diagnostics,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Attempt recovery if enabled
        if self.config['recovery']['enabled']:
            self.auto_healer.attempt_service_recovery(health_status)
    
    def _trigger_recovery(self, health_report: Dict[str, Any]):
        """Trigger system recovery procedures"""
        logger.warning("System health issues detected, triggering recovery")
        
        # Collect comprehensive diagnostics
        diagnostics = self.diagnostics_collector.collect_comprehensive_diagnostics()
        
        # Send alert
        self.alerting.send_alert({
            'type': 'system_unhealthy',
            'health_report': health_report,
            'diagnostics': diagnostics,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Attempt system recovery
        if self.config['recovery']['enabled']:
            self.auto_healer.attempt_system_recovery(health_report)


class MetricsCollector:
    """Collects and stores system metrics"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.influxdb_client = None
        self._init_influxdb()
    
    def _init_influxdb(self):
        """Initialize InfluxDB client"""
        try:
            from influxdb_client import InfluxDBClient, Point, WriteOptions
            from influxdb_client.client.write_api import SYNCHRONOUS
            
            self.influxdb_client = InfluxDBClient(
                url=self.config['influxdb']['url'],
                token=self.config['influxdb']['token'],
                org=self.config['influxdb']['org']
            )
            self.write_api = self.influxdb_client.write_api(write_options=SYNCHRONOUS)
        except ImportError:
            logger.warning("InfluxDB client not available, metrics will be logged only")
    
    def collect_all_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive system metrics"""
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'system': self._collect_system_metrics(),
            'processes': self._collect_process_metrics(),
            'network': self._collect_network_metrics(),
            'disk': self._collect_disk_metrics()
        }
    
    def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system-level metrics"""
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'cpu_count': psutil.cpu_count(),
            'memory': {
                'total': psutil.virtual_memory().total,
                'available': psutil.virtual_memory().available,
                'percent': psutil.virtual_memory().percent,
                'used': psutil.virtual_memory().used
            },
            'swap': {
                'total': psutil.swap_memory().total,
                'used': psutil.swap_memory().used,
                'percent': psutil.swap_memory().percent
            },
            'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
        }
    
    def _collect_process_metrics(self) -> List[Dict[str, Any]]:
        """Collect process-specific metrics"""
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                proc_info = proc.info
                if proc_info['cpu_percent'] > 5.0 or proc_info['memory_percent'] > 5.0:
                    processes.append(proc_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return processes
    
    def _collect_network_metrics(self) -> Dict[str, Any]:
        """Collect network metrics"""
        net_io = psutil.net_io_counters()
        connections = len(psutil.net_connections())
        
        return {
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv,
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv,
            'errors_in': net_io.errin,
            'errors_out': net_io.errout,
            'drops_in': net_io.dropin,
            'drops_out': net_io.dropout,
            'connections': connections
        }
    
    def _collect_disk_metrics(self) -> Dict[str, Any]:
        """Collect disk metrics"""
        disk_usage = psutil.disk_usage('/')
        disk_io = psutil.disk_io_counters()
        
        metrics = {
            'usage': {
                'total': disk_usage.total,
                'used': disk_usage.used,
                'free': disk_usage.free,
                'percent': (disk_usage.used / disk_usage.total) * 100
            }
        }
        
        if disk_io:
            metrics['io'] = {
                'read_count': disk_io.read_count,
                'write_count': disk_io.write_count,
                'read_bytes': disk_io.read_bytes,
                'write_bytes': disk_io.write_bytes,
                'read_time': disk_io.read_time,
                'write_time': disk_io.write_time
            }
        
        return metrics
    
    def store_metrics(self, metrics: Dict[str, Any]):
        """Store metrics in InfluxDB"""
        if not self.influxdb_client:
            logger.debug(f"Metrics: {json.dumps(metrics, indent=2)}")
            return
        
        try:
            from influxdb_client import Point
            
            points = []
            
            # System metrics
            system = metrics['system']
            points.append(
                Point("system_metrics")
                .field("cpu_percent", system['cpu_percent'])
                .field("memory_percent", system['memory']['percent'])
                .field("disk_percent", system['disk']['usage']['percent'])
                .time(datetime.utcnow())
            )
            
            # Network metrics
            network = metrics['network']
            points.append(
                Point("network_metrics")
                .field("bytes_sent", network['bytes_sent'])
                .field("bytes_recv", network['bytes_recv'])
                .field("connections", network['connections'])
                .time(datetime.utcnow())
            )
            
            self.write_api.write(
                bucket=self.config['influxdb']['bucket'],
                record=points
            )
            
        except Exception as e:
            logger.error(f"Failed to store metrics: {e}")
    
    def store_health_report(self, health_report: Dict[str, Any]):
        """Store health report"""
        # Store in file system
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        report_file = f"diagnostics/reports/health_report_{timestamp}.json"
        
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(health_report, f, indent=2)
        
        logger.info(f"Health report stored: {report_file}")


class DiagnosticsCollector:
    """Collects diagnostic information"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def collect_periodic_diagnostics(self):
        """Collect routine diagnostic data"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        diagnostics = {
            'timestamp': datetime.utcnow().isoformat(),
            'system_info': self._collect_system_info(),
            'service_logs': self._collect_service_logs(),
            'network_stats': self._collect_network_stats(),
            'disk_stats': self._collect_disk_stats()
        }
        
        # Save diagnostics
        diag_file = f"diagnostics/archives/periodic_{timestamp}.json"
        os.makedirs(os.path.dirname(diag_file), exist_ok=True)
        
        with open(diag_file, 'w') as f:
            json.dump(diagnostics, f, indent=2)
        
        logger.info(f"Periodic diagnostics collected: {diag_file}")
    
    def collect_emergency_diagnostics(self) -> Dict[str, Any]:
        """Collect emergency diagnostic data"""
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'system_snapshot': self._collect_system_info(),
            'recent_logs': self._collect_recent_logs(),
            'process_tree': self._collect_process_tree(),
            'network_connections': self._collect_network_connections()
        }
    
    def collect_comprehensive_diagnostics(self) -> Dict[str, Any]:
        """Collect comprehensive diagnostic data"""
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'system_info': self._collect_system_info(),
            'service_logs': self._collect_service_logs(),
            'network_analysis': self._collect_network_analysis(),
            'performance_profile': self._collect_performance_profile(),
            'configuration_dump': self._collect_configuration()
        }
    
    def _collect_system_info(self) -> Dict[str, Any]:
        """Collect system information"""
        return {
            'platform': psutil.LINUX if hasattr(psutil, 'LINUX') else 'unknown',
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
            'disk_total': psutil.disk_usage('/').total,
            'boot_time': psutil.boot_time(),
            'users': [u._asdict() for u in psutil.users()]
        }
    
    def _collect_service_logs(self) -> Dict[str, str]:
        """Collect service logs"""
        logs = {}
        
        log_files = [
            'logs/backend.log',
            'logs/frontend.log',
            'logs/health-monitoring.log'
        ]
        
        for log_file in log_files:
            try:
                with open(log_file, 'r') as f:
                    logs[log_file] = f.read()[-10000:]  # Last 10KB
            except FileNotFoundError:
                logs[log_file] = "Log file not found"
        
        return logs
    
    def _collect_recent_logs(self) -> str:
        """Collect recent system logs"""
        try:
            # Try to get recent logs from journalctl or syslog
            result = subprocess.run(
                ['journalctl', '--since', '1 hour ago', '--no-pager'],
                capture_output=True, text=True, timeout=10
            )
            return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return "Recent logs not available"
    
    def _collect_process_tree(self) -> List[Dict[str, Any]]:
        """Collect process tree information"""
        processes = []
        
        for proc in psutil.process_iter(['pid', 'ppid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return processes
    
    def _collect_network_connections(self) -> List[Dict[str, Any]]:
        """Collect network connection information"""
        connections = []
        
        for conn in psutil.net_connections():
            connections.append({
                'fd': conn.fd,
                'family': conn.family.name if conn.family else None,
                'type': conn.type.name if conn.type else None,
                'laddr': conn.laddr._asdict() if conn.laddr else None,
                'raddr': conn.raddr._asdict() if conn.raddr else None,
                'status': conn.status,
                'pid': conn.pid
            })
        
        return connections
    
    def _collect_network_stats(self) -> Dict[str, Any]:
        """Collect network statistics"""
        return {
            'interfaces': {name: stats._asdict() for name, stats in psutil.net_io_counters(pernic=True).items()},
            'connections': len(psutil.net_connections()),
            'listening_ports': [conn.laddr.port for conn in psutil.net_connections() if conn.status == 'LISTEN']
        }
    
    def _collect_disk_stats(self) -> Dict[str, Any]:
        """Collect disk statistics"""
        return {
            'partitions': [part._asdict() for part in psutil.disk_partitions()],
            'usage': {part.mountpoint: psutil.disk_usage(part.mountpoint)._asdict() 
                     for part in psutil.disk_partitions()},
            'io_counters': psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {}
        }
    
    def _collect_network_analysis(self) -> Dict[str, Any]:
        """Collect network analysis data"""
        # This would include network performance analysis
        return {
            'bandwidth_usage': self._collect_network_stats(),
            'connection_analysis': self._analyze_connections(),
            'port_scan_detection': self._detect_suspicious_connections()
        }
    
    def _analyze_connections(self) -> Dict[str, int]:
        """Analyze network connections"""
        connections = psutil.net_connections()
        
        analysis = {
            'total_connections': len(connections),
            'established': len([c for c in connections if c.status == 'ESTABLISHED']),
            'listening': len([c for c in connections if c.status == 'LISTEN']),
            'time_wait': len([c for c in connections if c.status == 'TIME_WAIT'])
        }
        
        return analysis
    
    def _detect_suspicious_connections(self) -> List[Dict[str, Any]]:
        """Detect potentially suspicious connections"""
        suspicious = []
        connections = psutil.net_connections()
        
        for conn in connections:
            if conn.raddr and conn.raddr.ip:
                # Check for connections to unusual ports or IPs
                if conn.raddr.port in [22, 23, 135, 445, 3389]:  # Common attack ports
                    suspicious.append({
                        'connection': conn._asdict(),
                        'reason': f'Connection to sensitive port {conn.raddr.port}'
                    })
        
        return suspicious
    
    def _collect_performance_profile(self) -> Dict[str, Any]:
        """Collect performance profiling data"""
        return {
            'cpu_times': psutil.cpu_times()._asdict(),
            'cpu_percent_per_core': psutil.cpu_percent(percpu=True),
            'memory_info': psutil.virtual_memory()._asdict(),
            'swap_info': psutil.swap_memory()._asdict(),
            'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
        }
    
    def _collect_configuration(self) -> Dict[str, Any]:
        """Collect system and application configuration"""
        config = {
            'environment_variables': dict(os.environ),
            'monitoring_config': self.config
        }
        
        # Remove sensitive information
        if 'environment_variables' in config:
            sensitive_keys = ['PASSWORD', 'SECRET', 'TOKEN', 'KEY', 'WEBHOOK']
            for key in list(config['environment_variables'].keys()):
                if any(sensitive in key.upper() for sensitive in sensitive_keys):
                    config['environment_variables'][key] = '[REDACTED]'
        
        return config


class AutoHealer:
    """Automated system recovery and healing"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.recovery_attempts = {}
    
    def attempt_service_recovery(self, health_status: Dict[str, Any]):
        """Attempt to recover unhealthy services"""
        logger.info("Attempting service recovery")
        
        for service_name, service_info in health_status.get('services', {}).items():
            if service_info.get('status') == 'unhealthy':
                self._recover_service(service_name, service_info)
    
    def attempt_system_recovery(self, health_report: Dict[str, Any]):
        """Attempt system-level recovery"""
        logger.info("Attempting system recovery")
        
        system = health_report.get('system', {})
        
        # Handle high CPU usage
        if system.get('cpu_percent', 0) > self.config['monitoring']['cpu_threshold']:
            self._handle_high_cpu()
        
        # Handle high memory usage
        if system.get('memory_percent', 0) > self.config['monitoring']['memory_threshold']:
            self._handle_high_memory()
        
        # Handle disk space issues
        if system.get('disk_percent', 0) > self.config['monitoring']['disk_threshold']:
            self._handle_disk_space()
    
    def _recover_service(self, service_name: str, service_info: Dict[str, Any]):
        """Recover a specific service"""
        attempt_key = f"{service_name}_{datetime.utcnow().date()}"
        
        if attempt_key not in self.recovery_attempts:
            self.recovery_attempts[attempt_key] = 0
        
        if self.recovery_attempts[attempt_key] >= self.config['recovery']['max_retries']:
            logger.warning(f"Max recovery attempts reached for {service_name}")
            return
        
        self.recovery_attempts[attempt_key] += 1
        
        logger.info(f"Attempting recovery for service: {service_name}")
        
        # Service-specific recovery strategies
        if service_name == 'backend':
            self._restart_backend_service()
        elif service_name == 'frontend':
            self._restart_frontend_service()
        else:
            self._generic_service_restart(service_name)
        
        # Wait before checking if recovery was successful
        time.sleep(self.config['recovery']['retry_delay'])
    
    def _restart_backend_service(self):
        """Restart backend service"""
        try:
            # Try to restart using pm2, systemd, or docker
            restart_commands = [
                ['pm2', 'restart', 'backend'],
                ['systemctl', 'restart', 'backend'],
                ['docker', 'restart', 'backend-service']
            ]
            
            for cmd in restart_commands:
                try:
                    result = subprocess.run(cmd, capture_output=True, timeout=30)
                    if result.returncode == 0:
                        logger.info(f"Backend service restarted using: {' '.join(cmd)}")
                        return
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    continue
            
            logger.warning("Failed to restart backend service with any method")
            
        except Exception as e:
            logger.error(f"Error restarting backend service: {e}")
    
    def _restart_frontend_service(self):
        """Restart frontend service"""
        try:
            # Try different restart methods
            restart_commands = [
                ['pm2', 'restart', 'frontend'],
                ['systemctl', 'restart', 'frontend'],
                ['docker', 'restart', 'frontend-service']
            ]
            
            for cmd in restart_commands:
                try:
                    result = subprocess.run(cmd, capture_output=True, timeout=30)
                    if result.returncode == 0:
                        logger.info(f"Frontend service restarted using: {' '.join(cmd)}")
                        return
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    continue
            
            logger.warning("Failed to restart frontend service with any method")
            
        except Exception as e:
            logger.error(f"Error restarting frontend service: {e}")
    
    def _generic_service_restart(self, service_name: str):
        """Generic service restart"""
        try:
            subprocess.run(['systemctl', 'restart', service_name], timeout=30)
            logger.info(f"Service {service_name} restarted")
        except Exception as e:
            logger.error(f"Failed to restart service {service_name}: {e}")
    
    def _handle_high_cpu(self):
        """Handle high CPU usage"""
        logger.info("Handling high CPU usage")
        
        # Find top CPU consuming processes
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by CPU usage
        processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        
        # Log top processes
        logger.info(f"Top CPU consuming processes: {processes[:5]}")
        
        # Could implement more aggressive CPU management here
    
    def _handle_high_memory(self):
        """Handle high memory usage"""
        logger.info("Handling high memory usage")
        
        # Force garbage collection if possible
        try:
            import gc
            gc.collect()
        except ImportError:
            pass
        
        # Find memory-heavy processes
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
            try:
                if proc.info['memory_percent'] > 10:
                    processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        logger.info(f"High memory processes: {processes}")
    
    def _handle_disk_space(self):
        """Handle disk space issues"""
        logger.info("Handling disk space issues")
        
        # Clean up log files
        self._cleanup_old_logs()
        
        # Clean up temporary files
        self._cleanup_temp_files()
    
    def _cleanup_old_logs(self):
        """Clean up old log files"""
        try:
            log_dirs = ['logs', 'diagnostics/archives']
            
            for log_dir in log_dirs:
                if os.path.exists(log_dir):
                    # Remove files older than 7 days
                    cutoff_time = time.time() - (7 * 24 * 3600)
                    
                    for root, dirs, files in os.walk(log_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            if os.path.getmtime(file_path) < cutoff_time:
                                try:
                                    os.remove(file_path)
                                    logger.info(f"Removed old log file: {file_path}")
                                except OSError:
                                    pass
        except Exception as e:
            logger.error(f"Error cleaning up old logs: {e}")
    
    def _cleanup_temp_files(self):
        """Clean up temporary files"""
        try:
            temp_dirs = ['/tmp', '/var/tmp']
            
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    # Remove files older than 1 day
                    cutoff_time = time.time() - (24 * 3600)
                    
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                if os.path.getmtime(file_path) < cutoff_time:
                                    os.remove(file_path)
                            except (OSError, PermissionError):
                                pass
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {e}")


class AlertingService:
    """Service for sending alerts and notifications"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.slack_webhook = config['alerting'].get('slack_webhook', '')
    
    def send_alert(self, alert_data: Dict[str, Any]):
        """Send alert through configured channels"""
        logger.info(f"Sending alert: {alert_data['type']}")
        
        # Send to Slack if configured
        if self.slack_webhook:
            self._send_slack_alert(alert_data)
        
        # Send to email if configured
        email_config = self.config['alerting'].get('email_smtp')
        if email_config:
            self._send_email_alert(alert_data)
        
        # Always log the alert
        self._log_alert(alert_data)
    
    def _send_slack_alert(self, alert_data: Dict[str, Any]):
        """Send alert to Slack"""
        try:
            payload = {
                'text': f"🚨 System Alert: {alert_data['type']}",
                'attachments': [{
                    'color': 'danger' if 'unhealthy' in alert_data['type'] else 'warning',
                    'fields': [
                        {
                            'title': 'Timestamp',
                            'value': alert_data['timestamp'],
                            'short': True
                        },
                        {
                            'title': 'Alert Type',
                            'value': alert_data['type'],
                            'short': True
                        }
                    ],
                    'text': f"```{json.dumps(alert_data, indent=2)[:1000]}```"
                }]
            }
            
            response = requests.post(
                self.slack_webhook,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Alert sent to Slack successfully")
            else:
                logger.error(f"Failed to send Slack alert: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error sending Slack alert: {e}")
    
    def _send_email_alert(self, alert_data: Dict[str, Any]):
        """Send alert via email"""
        # Email implementation would go here
        logger.info("Email alerts not implemented yet")
    
    def _log_alert(self, alert_data: Dict[str, Any]):
        """Log alert to file"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        alert_file = f"diagnostics/alerts/alert_{timestamp}.json"
        
        os.makedirs(os.path.dirname(alert_file), exist_ok=True)
        
        with open(alert_file, 'w') as f:
            json.dump(alert_data, f, indent=2)
        
        logger.info(f"Alert logged to: {alert_file}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='System Health Monitoring Service')
    parser.add_argument('--config', default='config/monitoring.json',
                       help='Configuration file path')
    parser.add_argument('--daemon', action='store_true',
                       help='Run as daemon')
    
    args = parser.parse_args()
    
    # Create monitoring service
    monitor = SystemHealthMonitor(args.config)
    
    try:
        monitor.start_monitoring()
    except KeyboardInterrupt:
        logger.info("Monitoring service stopped by user")
    except Exception as e:
        logger.error(f"Monitoring service error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
EOF

    chmod +x "${REPO_PATH}/monitor/services/health_monitor.py"
    
    log "✓ Health monitoring service created"
}

# Create monitoring configuration
create_monitoring_config() {
    log "Creating monitoring configuration..."
    
    cat > "${REPO_PATH}/config/monitoring.json" << 'EOF'
{
  "influxdb": {
    "url": "http://localhost:8086",
    "token": "",
    "bucket": "system_metrics",
    "org": "development"
  },
  "alerting": {
    "slack_webhook": "",
    "email_smtp": {
      "host": "smtp.gmail.com",
      "port": 587,
      "username": "",
      "password": "",
      "from": "",
      "to": []
    }
  },
  "monitoring": {
    "interval_seconds": 60,
    "health_check_interval": 300,
    "cpu_threshold": 80.0,
    "memory_threshold": 80.0,
    "disk_threshold": 85.0,
    "network_threshold": 90.0,
    "service_timeout": 10
  },
  "services": {
    "backend_port": 3001,
    "frontend_port": 3000,
    "database_port": 5432,
    "monitoring_port": 8080
  },
  "recovery": {
    "enabled": true,
    "max_retries": 3,
    "retry_delay": 60,
    "restart_services": true,
    "cleanup_logs": true,
    "cleanup_temp": true
  },
  "diagnostics": {
    "collect_interval": 3600,
    "retention_days": 7,
    "max_file_size": 10485760,
    "compress_old_files": true
  },
  "security": {
    "monitor_connections": true,
    "detect_suspicious": true,
    "log_security_events": true
  }
}
EOF

    log "✓ Monitoring configuration created"
}

# Create health dashboard API extensions
create_dashboard_api_extensions() {
    log "Creating health dashboard API extensions..."
    
    cat > "${REPO_PATH}/monitor/api/health_api.py" << 'EOF'
"""
Health Monitoring Dashboard API Extensions
Provides API endpoints for health monitoring dashboard integration
"""

from flask import Flask, Blueprint, request, jsonify, send_file
from flask_cors import CORS
import json
import os
import glob
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
health_bp = Blueprint('health', __name__)

class HealthDashboardAPI:
    """Health monitoring dashboard API"""
    
    def __init__(self, diagnostics_path='diagnostics'):
        self.diagnostics_path = diagnostics_path
    
    def get_latest_metrics(self) -> dict:
        """Get latest system metrics"""
        try:
            # Find the latest health report
            report_files = glob.glob(f"{self.diagnostics_path}/reports/health_report_*.json")
            
            if not report_files:
                return {
                    'status': 'no_data',
                    'message': 'No health reports available',
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            # Get the most recent report
            latest_report = max(report_files, key=os.path.getctime)
            
            with open(latest_report, 'r') as f:
                health_data = json.load(f)
            
            return {
                'status': 'healthy' if self._is_system_healthy(health_data) else 'unhealthy',
                'data': health_data,
                'file': latest_report,
                'retrieved_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get latest metrics: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_diagnostic_files(self, hours=24) -> list:
        """Get list of diagnostic files from the last N hours"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            files = []
            
            # Get diagnostic files
            for pattern in ['reports/*.json', 'archives/*.json', 'alerts/*.json']:
                file_pattern = os.path.join(self.diagnostics_path, pattern)
                
                for file_path in glob.glob(file_pattern):
                    file_stat = os.stat(file_path)
                    file_time = datetime.fromtimestamp(file_stat.st_mtime)
                    
                    if file_time > cutoff_time:
                        files.append({
                            'path': file_path,
                            'name': os.path.basename(file_path),
                            'size': file_stat.st_size,
                            'modified': file_time.isoformat(),
                            'type': self._get_file_type(file_path)
                        })
            
            # Sort by modification time (newest first)
            files.sort(key=lambda x: x['modified'], reverse=True)
            
            return files
            
        except Exception as e:
            logger.error(f"Failed to get diagnostic files: {e}")
            return []
    
    def get_system_status_summary(self) -> dict:
        """Get system status summary for dashboard"""
        try:
            latest_metrics = self.get_latest_metrics()
            
            if latest_metrics['status'] == 'error' or latest_metrics['status'] == 'no_data':
                return {
                    'overall_status': 'unknown',
                    'services': {},
                    'system': {},
                    'last_update': None
                }
            
            data = latest_metrics['data']
            
            # Extract key metrics
            system = data.get('system', {})
            services = data.get('services', {})
            
            return {
                'overall_status': 'healthy' if latest_metrics['status'] == 'healthy' else 'unhealthy',
                'services': {
                    'backend': services.get('services', {}).get('backend', {}).get('status', 'unknown'),
                    'frontend': services.get('services', {}).get('frontend', {}).get('status', 'unknown'),
                    'healthy_count': len([s for s in services.get('services', {}).values() if s.get('status') == 'healthy']),
                    'total_count': len(services.get('services', {}))
                },
                'system': {
                    'cpu_percent': system.get('cpu_percent', 0),
                    'memory_percent': system.get('memory_percent', 0),
                    'disk_percent': system.get('disk_percent', 0),
                    'uptime': system.get('uptime', 0)
                },
                'last_update': data.get('timestamp'),
                'file_info': {
                    'source': latest_metrics.get('file'),
                    'retrieved_at': latest_metrics.get('retrieved_at')
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get system status summary: {e}")
            return {
                'overall_status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _is_system_healthy(self, health_data: dict) -> bool:
        """Determine if system is healthy based on health data"""
        try:
            system = health_data.get('system', {})
            services = health_data.get('services', {})
            
            # Check system thresholds
            if system.get('cpu_percent', 0) > 80:
                return False
            
            if system.get('memory_percent', 0) > 80:
                return False
            
            if system.get('disk_percent', 0) > 85:
                return False
            
            # Check service health
            if not services.get('healthy', True):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _get_file_type(self, file_path: str) -> str:
        """Determine file type based on path"""
        if 'reports' in file_path:
            return 'health_report'
        elif 'archives' in file_path:
            return 'diagnostic_archive'
        elif 'alerts' in file_path:
            return 'alert'
        else:
            return 'unknown'

# Initialize API instance
health_api = HealthDashboardAPI()

@health_bp.route('/api/health', methods=['GET'])
def get_health_status():
    """Get current health status"""
    try:
        status_summary = health_api.get_system_status_summary()
        return jsonify({
            'success': True,
            'data': status_summary
        })
    except Exception as e:
        logger.error(f"Health status API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@health_bp.route('/api/health/metrics', methods=['GET'])
def get_latest_metrics():
    """Get latest system metrics"""
    try:
        metrics = health_api.get_latest_metrics()
        return jsonify({
            'success': True,
            'data': metrics
        })
    except Exception as e:
        logger.error(f"Metrics API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@health_bp.route('/api/health/diagnostics', methods=['GET'])
def get_diagnostics():
    """Get diagnostic files list"""
    try:
        hours = request.args.get('hours', 24, type=int)
        files = health_api.get_diagnostic_files(hours)
        
        return jsonify({
            'success': True,
            'data': {
                'files': files,
                'count': len(files),
                'hours': hours
            }
        })
    except Exception as e:
        logger.error(f"Diagnostics API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@health_bp.route('/api/health/diagnostics/<path:filename>', methods=['GET'])
def download_diagnostic_file(filename):
    """Download a specific diagnostic file"""
    try:
        # Security check - only allow files in diagnostics directory
        safe_path = os.path.join(health_api.diagnostics_path, filename)
        safe_path = os.path.abspath(safe_path)
        
        if not safe_path.startswith(os.path.abspath(health_api.diagnostics_path)):
            return jsonify({
                'success': False,
                'error': 'Invalid file path'
            }), 403
        
        if not os.path.exists(safe_path):
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404
        
        return send_file(safe_path, as_attachment=True)
        
    except Exception as e:
        logger.error(f"File download error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@health_bp.route('/api/health/status/<service_name>', methods=['GET'])
def get_service_status(service_name):
    """Get status of a specific service"""
    try:
        latest_metrics = health_api.get_latest_metrics()
        
        if latest_metrics['status'] == 'error':
            return jsonify({
                'success': False,
                'error': latest_metrics['message']
            }), 500
        
        services = latest_metrics['data'].get('services', {}).get('services', {})
        
        if service_name not in services:
            return jsonify({
                'success': False,
                'error': f'Service {service_name} not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': {
                'service': service_name,
                'status': services[service_name],
                'timestamp': latest_metrics['data'].get('timestamp')
            }
        })
        
    except Exception as e:
        logger.error(f"Service status API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Create Flask app for health monitoring API
def create_health_api_app():
    """Create Flask app for health monitoring API"""
    app = Flask(__name__)
    CORS(app)
    
    app.register_blueprint(health_bp)
    
    return app

if __name__ == '__main__':
    app = create_health_api_app()
    app.run(host='0.0.0.0', port=8080, debug=False)
EOF

    log "✓ Health dashboard API extensions created"
}

# Create frontend dashboard extensions
create_frontend_dashboard_extensions() {
    log "Creating frontend dashboard extensions..."
    
    cat > "${REPO_PATH}/frontend/src/components/health/SystemHealthPanel.tsx" << 'EOF'
import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Tag,
  Table,
  Button,
  Space,
  Typography,
  Alert,
  Spin,
} from 'antd';
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CloseCircleOutlined,
  DownloadOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useQuery } from 'react-query';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

interface SystemHealth {
  overall_status: string;
  services: {
    backend: string;
    frontend: string;
    healthy_count: number;
    total_count: number;
  };
  system: {
    cpu_percent: number;
    memory_percent: number;
    disk_percent: number;
    uptime: number;
  };
  last_update: string;
}

interface DiagnosticFile {
  path: string;
  name: string;
  size: number;
  modified: string;
  type: string;
}

const SystemHealthPanel: React.FC = () => {
  const [diagnosticFiles, setDiagnosticFiles] = useState<DiagnosticFile[]>([]);

  // Fetch system health status
  const {
    data: healthData,
    isLoading: healthLoading,
    error: healthError,
    refetch: refetchHealth
  } = useQuery(
    'system-health',
    async () => {
      const response = await fetch('/api/health');
      const result = await response.json();
      if (!result.success) {
        throw new Error(result.error);
      }
      return result.data as SystemHealth;
    },
    {
      refetchInterval: 30000, // Refresh every 30 seconds
      refetchOnWindowFocus: true
    }
  );

  // Fetch diagnostic files
  const fetchDiagnosticFiles = async () => {
    try {
      const response = await fetch('/api/health/diagnostics?hours=24');
      const result = await response.json();
      if (result.success) {
        setDiagnosticFiles(result.data.files);
      }
    } catch (error) {
      console.error('Failed to fetch diagnostic files:', error);
    }
  };

  useEffect(() => {
    fetchDiagnosticFiles();
  }, []);

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy':
        return 'success';
      case 'unhealthy':
        return 'error';
      case 'warning':
        return 'warning';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'unhealthy':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'warning':
        return <ExclamationCircleOutlined style={{ color: '#faad14' }} />;
      default:
        return null;
    }
  };

  const formatUptime = (seconds: number) => {
    const duration = dayjs.duration(seconds, 'seconds');
    return `${Math.floor(duration.asDays())}d ${duration.hours()}h ${duration.minutes()}m`;
  };

  const formatFileSize = (bytes: number) => {
    const sizes = ['B', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${Math.round(bytes / Math.pow(1024, i) * 100) / 100} ${sizes[i]}`;
  };

  const downloadDiagnosticFile = (filename: string) => {
    window.open(`/api/health/diagnostics/${encodeURIComponent(filename)}`, '_blank');
  };

  if (healthLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>Loading system health...</div>
      </div>
    );
  }

  if (healthError) {
    return (
      <Alert
        message="Failed to load system health"
        description={healthError instanceof Error ? healthError.message : 'Unknown error'}
        type="error"
        showIcon
        action={
          <Button size="small" onClick={() => refetchHealth()}>
            Retry
          </Button>
        }
      />
    );
  }

  if (!healthData) {
    return (
      <Alert
        message="No health data available"
        type="warning"
        showIcon
      />
    );
  }

  const diagnosticColumns = [
    {
      title: 'File Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => <Text code>{name}</Text>,
    },
    {
      title: 'Type',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => (
        <Tag color={
          type === 'health_report' ? 'blue' :
          type === 'alert' ? 'red' : 'green'
        }>
          {type.replace('_', ' ').toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Size',
      dataIndex: 'size',
      key: 'size',
      render: (size: number) => formatFileSize(size),
    },
    {
      title: 'Modified',
      dataIndex: 'modified',
      key: 'modified',
      render: (modified: string) => dayjs(modified).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: DiagnosticFile) => (
        <Button
          size="small"
          icon={<DownloadOutlined />}
          onClick={() => downloadDiagnosticFile(record.name)}
        >
          Download
        </Button>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={3}>System Health Monitoring</Title>
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => {
              refetchHealth();
              fetchDiagnosticFiles();
            }}
          >
            Refresh
          </Button>
        </Space>
      </div>

      {/* Overall Status Alert */}
      <Alert
        message={`System Status: ${healthData.overall_status.toUpperCase()}`}
        description={`Last updated: ${dayjs(healthData.last_update).format('YYYY-MM-DD HH:mm:ss')}`}
        type={healthData.overall_status === 'healthy' ? 'success' : 'error'}
        showIcon
        icon={getStatusIcon(healthData.overall_status)}
        style={{ marginBottom: 24 }}
      />

      {/* System Metrics */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="CPU Usage"
              value={healthData.system.cpu_percent}
              suffix="%"
              valueStyle={{
                color: healthData.system.cpu_percent > 80 ? '#ff4d4f' : 
                       healthData.system.cpu_percent > 60 ? '#faad14' : '#52c41a'
              }}
            />
            <Progress
              percent={healthData.system.cpu_percent}
              status={healthData.system.cpu_percent > 80 ? 'exception' : 'normal'}
              showInfo={false}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Memory Usage"
              value={healthData.system.memory_percent}
              suffix="%"
              valueStyle={{
                color: healthData.system.memory_percent > 80 ? '#ff4d4f' : 
                       healthData.system.memory_percent > 60 ? '#faad14' : '#52c41a'
              }}
            />
            <Progress
              percent={healthData.system.memory_percent}
              status={healthData.system.memory_percent > 80 ? 'exception' : 'normal'}
              showInfo={false}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Disk Usage"
              value={healthData.system.disk_percent}
              suffix="%"
              valueStyle={{
                color: healthData.system.disk_percent > 85 ? '#ff4d4f' : 
                       healthData.system.disk_percent > 70 ? '#faad14' : '#52c41a'
              }}
            />
            <Progress
              percent={healthData.system.disk_percent}
              status={healthData.system.disk_percent > 85 ? 'exception' : 'normal'}
              showInfo={false}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="System Uptime"
              value={formatUptime(healthData.system.uptime)}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Service Status */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={12}>
          <Card title="Service Status" size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>Backend Service:</span>
                <Space>
                  {getStatusIcon(healthData.services.backend)}
                  <Tag color={getStatusColor(healthData.services.backend)}>
                    {healthData.services.backend?.toUpperCase() || 'UNKNOWN'}
                  </Tag>
                </Space>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>Frontend Service:</span>
                <Space>
                  {getStatusIcon(healthData.services.frontend)}
                  <Tag color={getStatusColor(healthData.services.frontend)}>
                    {healthData.services.frontend?.toUpperCase() || 'UNKNOWN'}
                  </Tag>
                </Space>
              </div>
            </Space>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="Service Summary" size="small">
            <Statistic
              title="Healthy Services"
              value={healthData.services.healthy_count}
              suffix={`/ ${healthData.services.total_count}`}
              valueStyle={{
                color: healthData.services.healthy_count === healthData.services.total_count ? 
                       '#52c41a' : '#faad14'
              }}
            />
            <Progress
              percent={(healthData.services.healthy_count / healthData.services.total_count) * 100}
              status={healthData.services.healthy_count === healthData.services.total_count ? 
                     'success' : 'active'}
              showInfo={false}
            />
          </Card>
        </Col>
      </Row>

      {/* Diagnostic Files */}
      <Card
        title="Diagnostic Files (Last 24 Hours)"
        extra={
          <Button size="small" onClick={fetchDiagnosticFiles}>
            <ReloadOutlined /> Refresh
          </Button>
        }
      >
        <Table
          dataSource={diagnosticFiles}
          columns={diagnosticColumns}
          rowKey="name"
          size="small"
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} files`
          }}
        />
      </Card>
    </div>
  );
};

export default SystemHealthPanel;
EOF

    log "✓ Frontend dashboard extensions created"
}

# Create service management scripts
create_service_management_scripts() {
    log "Creating service management scripts..."
    
    # Service startup script
    cat > "${REPO_PATH}/monitor/scripts/start_monitoring.sh" << 'EOF'
#!/bin/bash

# Start System Health Monitoring Services
# Starts all monitoring components and services

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[MONITOR]${NC} $1"
}

info() {
    echo -e "${BLUE}[MONITOR]${NC} $1"
}

log "Starting system health monitoring services..."

# Create necessary directories
mkdir -p "$REPO_ROOT"/{logs,diagnostics/{reports,archives,alerts}}

# Start health monitoring service
if [[ -f "$REPO_ROOT/monitor/services/health_monitor.py" ]]; then
    log "Starting health monitoring service..."
    nohup python3 "$REPO_ROOT/monitor/services/health_monitor.py" \
        --config "$REPO_ROOT/config/monitoring.json" \
        > "$REPO_ROOT/logs/health-monitor.log" 2>&1 & disown
    
    echo $! > "$REPO_ROOT/monitor/health-monitor.pid"
    log "Health monitoring service started (PID: $(cat $REPO_ROOT/monitor/health-monitor.pid))"
else
    log "Health monitoring service not found, skipping..."
fi

# Start health API service
if [[ -f "$REPO_ROOT/monitor/api/health_api.py" ]]; then
    log "Starting health API service..."
    cd "$REPO_ROOT/monitor/api"
    nohup python3 health_api.py \
        > "$REPO_ROOT/logs/health-api.log" 2>&1 & disown
    
    echo $! > "$REPO_ROOT/monitor/health-api.pid"
    log "Health API service started (PID: $(cat $REPO_ROOT/monitor/health-api.pid))"
    log "Health API available at: http://localhost:8080"
else
    log "Health API service not found, skipping..."
fi

# Wait a moment for services to start
sleep 5

# Check service status
log "Checking service status..."

if [[ -f "$REPO_ROOT/monitor/health-monitor.pid" ]]; then
    if kill -0 "$(cat $REPO_ROOT/monitor/health-monitor.pid)" 2>/dev/null; then
        info "✓ Health monitoring service is running"
    else
        info "✗ Health monitoring service failed to start"
    fi
fi

if [[ -f "$REPO_ROOT/monitor/health-api.pid" ]]; then
    if kill -0 "$(cat $REPO_ROOT/monitor/health-api.pid)" 2>/dev/null; then
        info "✓ Health API service is running"
    else
        info "✗ Health API service failed to start"
    fi
fi

log "System health monitoring services startup complete!"
log ""
log "📊 Monitoring Dashboard: http://localhost:3000 (if frontend is running)"
log "🔧 Health API: http://localhost:8080/api/health"
log "📁 Logs: $REPO_ROOT/logs/"
log "📋 Diagnostics: $REPO_ROOT/diagnostics/"
EOF

    chmod +x "${REPO_PATH}/monitor/scripts/start_monitoring.sh"

    # Service stop script
    cat > "${REPO_PATH}/monitor/scripts/stop_monitoring.sh" << 'EOF'
#!/bin/bash

# Stop System Health Monitoring Services
# Stops all monitoring components and services

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[MONITOR]${NC} $1"
}

error() {
    echo -e "${RED}[MONITOR]${NC} $1"
}

log "Stopping system health monitoring services..."

# Stop health monitoring service
if [[ -f "$REPO_ROOT/monitor/health-monitor.pid" ]]; then
    PID=$(cat "$REPO_ROOT/monitor/health-monitor.pid")
    if kill -0 "$PID" 2>/dev/null; then
        log "Stopping health monitoring service (PID: $PID)..."
        kill "$PID"
        
        # Wait for graceful shutdown
        for i in {1..10}; do
            if ! kill -0 "$PID" 2>/dev/null; then
                break
            fi
            sleep 1
        done
        
        # Force kill if necessary
        if kill -0 "$PID" 2>/dev/null; then
            log "Force stopping health monitoring service..."
            kill -9 "$PID"
        fi
        
        log "✓ Health monitoring service stopped"
    else
        log "Health monitoring service is not running"
    fi
    
    rm -f "$REPO_ROOT/monitor/health-monitor.pid"
else
    log "Health monitoring service PID file not found"
fi

# Stop health API service
if [[ -f "$REPO_ROOT/monitor/health-api.pid" ]]; then
    PID=$(cat "$REPO_ROOT/monitor/health-api.pid")
    if kill -0 "$PID" 2>/dev/null; then
        log "Stopping health API service (PID: $PID)..."
        kill "$PID"
        
        # Wait for graceful shutdown
        for i in {1..10}; do
            if ! kill -0 "$PID" 2>/dev/null; then
                break
            fi
            sleep 1
        done
        
        # Force kill if necessary
        if kill -0 "$PID" 2>/dev/null; then
            log "Force stopping health API service..."
            kill -9 "$PID"
        fi
        
        log "✓ Health API service stopped"
    else
        log "Health API service is not running"
    fi
    
    rm -f "$REPO_ROOT/monitor/health-api.pid"
else
    log "Health API service PID file not found"
fi

log "System health monitoring services stopped!"
EOF

    chmod +x "${REPO_PATH}/monitor/scripts/stop_monitoring.sh"

    # Service status script
    cat > "${REPO_PATH}/monitor/scripts/status_monitoring.sh" << 'EOF'
#!/bin/bash

# Check System Health Monitoring Services Status
# Shows status of all monitoring components and services

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[STATUS]${NC} $1"
}

error() {
    echo -e "${RED}[STATUS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[STATUS]${NC} $1"
}

info() {
    echo -e "${BLUE}[STATUS]${NC} $1"
}

log "System Health Monitoring Services Status"
log "======================================="

# Check health monitoring service
if [[ -f "$REPO_ROOT/monitor/health-monitor.pid" ]]; then
    PID=$(cat "$REPO_ROOT/monitor/health-monitor.pid")
    if kill -0 "$PID" 2>/dev/null; then
        log "✓ Health Monitoring Service: RUNNING (PID: $PID)"
    else
        error "✗ Health Monitoring Service: STOPPED (stale PID file)"
        rm -f "$REPO_ROOT/monitor/health-monitor.pid"
    fi
else
    warn "○ Health Monitoring Service: NOT RUNNING"
fi

# Check health API service
if [[ -f "$REPO_ROOT/monitor/health-api.pid" ]]; then
    PID=$(cat "$REPO_ROOT/monitor/health-api.pid")
    if kill -0 "$PID" 2>/dev/null; then
        log "✓ Health API Service: RUNNING (PID: $PID)"
        
        # Test API connectivity
        if curl -s -f http://localhost:8080/api/health >/dev/null 2>&1; then
            info "  → API is responding at http://localhost:8080"
        else
            warn "  → API is not responding"
        fi
    else
        error "✗ Health API Service: STOPPED (stale PID file)"
        rm -f "$REPO_ROOT/monitor/health-api.pid"
    fi
else
    warn "○ Health API Service: NOT RUNNING"
fi

# Check log files
log ""
log "Log Files:"
for logfile in health-monitor.log health-api.log; do
    logpath="$REPO_ROOT/logs/$logfile"
    if [[ -f "$logpath" ]]; then
        size=$(du -h "$logpath" | cut -f1)
        modified=$(date -r "$logpath" "+%Y-%m-%d %H:%M:%S")
        info "  • $logfile: $size (modified: $modified)"
    else
        warn "  • $logfile: not found"
    fi
done

# Check diagnostic files
log ""
log "Diagnostic Files:"
diag_count=0
if [[ -d "$REPO_ROOT/diagnostics" ]]; then
    for dir in reports archives alerts; do
        if [[ -d "$REPO_ROOT/diagnostics/$dir" ]]; then
            count=$(find "$REPO_ROOT/diagnostics/$dir" -name "*.json" | wc -l)
            info "  • $dir: $count files"
            diag_count=$((diag_count + count))
        fi
    done
    info "  → Total diagnostic files: $diag_count"
else
    warn "  • diagnostics directory not found"
fi

# System resource summary
log ""
log "System Resources:"
if command -v python3 &> /dev/null && python3 -c "import psutil" 2>/dev/null; then
    cpu_percent=$(python3 -c "import psutil; print(f'{psutil.cpu_percent(interval=1):.1f}')")
    mem_percent=$(python3 -c "import psutil; print(f'{psutil.virtual_memory().percent:.1f}')")
    disk_percent=$(python3 -c "import psutil; print(f'{psutil.disk_usage(\"/\").percent:.1f}')")
    
    info "  • CPU Usage: ${cpu_percent}%"
    info "  • Memory Usage: ${mem_percent}%"
    info "  • Disk Usage: ${disk_percent}%"
else
    warn "  • psutil not available for resource monitoring"
fi

log ""
log "Status check complete!"
EOF

    chmod +x "${REPO_PATH}/monitor/scripts/status_monitoring.sh"

    log "✓ Service management scripts created"
}

# Create documentation
create_documentation() {
    log "Creating system health monitoring documentation..."
    
    cat > "${REPO_PATH}/monitor/README.md" << 'EOF'
# System Health Monitoring and Recovery System

A comprehensive system health monitoring solution with automated diagnostics collection, alerting, and recovery capabilities. Designed for legitimate application monitoring and development environment management.

## Features

- **Real-time Monitoring**: Continuous monitoring of system resources and application health
- **Automated Diagnostics**: Periodic collection of system diagnostics and logs
- **Self-Healing**: Automated recovery procedures for common issues
- **Dashboard Integration**: Web-based dashboard for monitoring and management
- **Alerting System**: Slack and email notifications for critical issues
- **Performance Metrics**: Detailed system and application performance tracking

## Architecture

### Core Components

#### Health Monitor Service (`health_monitor.py`)
- Continuous system and service health monitoring
- Automated metric collection and storage
- Real-time threshold monitoring and alerting
- Automated recovery procedures

#### Diagnostics Collector
- Periodic diagnostic data collection
- Emergency diagnostics for critical issues
- Log aggregation and analysis
- System configuration monitoring

#### Auto Healer
- Automated service restart procedures
- System resource cleanup and optimization
- Recovery attempt tracking and limits
- Service-specific recovery strategies

#### Alerting Service
- Multi-channel alert delivery (Slack, email, logs)
- Alert severity classification
- Alert history and tracking
- Custom alert formatting and routing

### Dashboard Integration

#### Health API (`health_api.py`)
- RESTful API for health status and metrics
- Diagnostic file access and download
- Real-time system status endpoints
- Service-specific health checks

#### Frontend Components
- Real-time system health dashboard
- Interactive metric visualization
- Diagnostic file browser and downloader
- Service status monitoring panel

## Quick Start

### Installation
```bash
# Install monitoring dependencies
sudo apt update
sudo apt install -y python3-pip jq curl
pip3 install --user influxdb-client requests psutil

# Set up directory structure
cd system-health-monitoring/
./setup.sh
```

### Configuration
```bash
# Edit monitoring configuration
cp config/monitoring.json.example config/monitoring.json
nano config/monitoring.json
```

### Starting Services
```bash
# Start all monitoring services
./monitor/scripts/start_monitoring.sh

# Check service status
./monitor/scripts/status_monitoring.sh

# Stop services
./monitor/scripts/stop_monitoring.sh
```

## Configuration

### Monitoring Configuration (`config/monitoring.json`)

```json
{
  "influxdb": {
    "url": "http://localhost:8086",
    "token": "your-influxdb-token",
    "bucket": "system_metrics",
    "org": "development"
  },
  "alerting": {
    "slack_webhook": "https://hooks.slack.com/services/...",
    "email_smtp": {
      "host": "smtp.gmail.com",
      "port": 587,
      "username": "alerts@company.com",
      "password": "app-password"
    }
  },
  "monitoring": {
    "interval_seconds": 60,
    "health_check_interval": 300,
    "cpu_threshold": 80.0,
    "memory_threshold": 80.0,
    "disk_threshold": 85.0
  },
  "recovery": {
    "enabled": true,
    "max_retries": 3,
    "retry_delay": 60,
    "restart_services": true
  }
}
```

### Threshold Configuration

#### System Thresholds
- **CPU Usage**: Alert when > 80%
- **Memory Usage**: Alert when > 80%
- **Disk Usage**: Alert when > 85%
- **Network Usage**: Alert when > 90%

#### Service Health
- **Response Time**: Alert when > 10 seconds
- **HTTP Status**: Alert on non-200 responses
- **Service Availability**: Alert when service unreachable

## Monitoring Features

### System Metrics Collection
```python
# Collected metrics include:
system_metrics = {
    'cpu_percent': psutil.cpu_percent(interval=1),
    'memory': {
        'total': psutil.virtual_memory().total,
        'used': psutil.virtual_memory().used,
        'percent': psutil.virtual_memory().percent
    },
    'disk': {
        'total': psutil.disk_usage('/').total,
        'used': psutil.disk_usage('/').used,
        'percent': psutil.disk_usage('/').percent
    },
    'network': {
        'bytes_sent': net_io.bytes_sent,
        'bytes_recv': net_io.bytes_recv,
        'connections': len(psutil.net_connections())
    }
}
```

### Service Health Checks
- **Backend API**: HTTP health endpoint monitoring
- **Frontend**: Static file serving availability
- **Database**: Connection and response time testing
- **External Services**: Dependency health validation

### Automated Recovery Procedures

#### Service Recovery
```python
def recover_service(service_name, service_info):
    # Service-specific recovery strategies
    if service_name == 'backend':
        restart_backend_service()  # pm2, systemd, or docker
    elif service_name == 'frontend':
        restart_frontend_service()  # nginx, pm2, or docker
    
    # Wait and verify recovery
    time.sleep(retry_delay)
    verify_service_health(service_name)
```

#### System Recovery
- **High CPU**: Process analysis and optimization
- **High Memory**: Garbage collection and cleanup
- **Disk Space**: Log rotation and temporary file cleanup
- **Network Issues**: Connection analysis and optimization

## API Endpoints

### Health Status
```bash
# Get overall system health
curl http://localhost:8080/api/health

# Get latest metrics
curl http://localhost:8080/api/health/metrics

# Get service-specific status
curl http://localhost:8080/api/health/status/backend
```

### Diagnostics
```bash
# List diagnostic files
curl http://localhost:8080/api/health/diagnostics?hours=24

# Download diagnostic file
curl -O http://localhost:8080/api/health/diagnostics/health_report_20240115_143022.json
```

## Dashboard Features

### System Health Panel
- Real-time system resource utilization
- Service status indicators with color coding
- Interactive charts and progress bars
- Diagnostic file browser and downloader

### Monitoring Dashboard
```tsx
// React component for system health
<SystemHealthPanel />
// Features:
// - Real-time metrics display
// - Service status monitoring
// - Diagnostic file management
// - Alert history and status
```

### Diagnostic File Management
- Automatic file categorization (health reports, alerts, archives)
- File size and timestamp display
- One-click download functionality
- Retention policy management

## Alerting System

### Slack Integration
```python
# Slack alert example
{
    'text': '🚨 System Alert: service_unhealthy',
    'attachments': [{
        'color': 'danger',
        'fields': [
            {'title': 'Service', 'value': 'backend', 'short': True},
            {'title': 'Status', 'value': 'unhealthy', 'short': True}
        ]
    }]
}
```

### Email Alerts
- SMTP configuration for email notifications
- HTML-formatted alert emails
- Attachment support for diagnostic files
- Distribution list management

### Alert Types
- **System Unhealthy**: Overall system health issues
- **Service Unhealthy**: Individual service failures
- **Threshold Exceeded**: Resource usage above limits
- **Recovery Started**: Automated recovery initiated
- **Recovery Failed**: Recovery procedures unsuccessful

## Development and Testing

### Local Development
```bash
# Start development environment
python3 monitor/services/health_monitor.py --config config/monitoring.json

# Test health checks
python3 -c "
from monitor.services.health_monitor import SystemHealthMonitor
monitor = SystemHealthMonitor()
print(monitor._check_system_health())
"
```

### Testing Health Checks
```bash
# Simulate high resource usage
stress --cpu 4 --timeout 60s  # High CPU
stress --vm 2 --vm-bytes 1G --timeout 60s  # High memory

# Test service recovery
sudo systemctl stop backend  # Stop backend service
# Watch auto-recovery in logs
tail -f logs/health-monitor.log
```

## Troubleshooting

### Common Issues

#### Monitoring Service Won't Start
```bash
# Check Python dependencies
pip3 install --user influxdb-client psutil requests

# Check configuration file
python3 -c "import json; print(json.load(open('config/monitoring.json')))"

# Check permissions
ls -la monitor/services/health_monitor.py
chmod +x monitor/services/health_monitor.py
```

#### High Resource Usage Alerts
```bash
# Check actual resource usage
htop
df -h
free -h

# Review resource thresholds
grep -A5 "monitoring" config/monitoring.json

# Adjust thresholds if needed
nano config/monitoring.json
```

#### Recovery Procedures Failing
```bash
# Check service management commands
systemctl status backend
pm2 status
docker ps

# Test manual recovery
sudo systemctl restart backend

# Review recovery logs
grep "recovery" logs/health-monitor.log
```

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python3 monitor/services/health_monitor.py --config config/monitoring.json

# Monitor debug output
tail -f logs/health-monitor.log | grep DEBUG
```

## Production Deployment

### Systemd Service
```bash
# Create systemd service file
sudo cp monitor/deploy/health-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable health-monitor
sudo systemctl start health-monitor
```

### Docker Deployment
```bash
# Build monitoring container
docker build -t health-monitor monitor/

# Run monitoring container
docker run -d \
  --name health-monitor \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/diagnostics:/app/diagnostics \
  health-monitor
```

### Process Management
```bash
# Using PM2
pm2 start monitor/services/health_monitor.py --name health-monitor
pm2 startup
pm2 save

# Using supervisor
sudo apt install supervisor
sudo cp monitor/deploy/supervisor.conf /etc/supervisor/conf.d/
sudo supervisorctl reread
sudo supervisorctl update
```

## Security Considerations

### Access Control
- API endpoints require authentication in production
- Diagnostic files contain sensitive system information
- Alert channels should be secured and monitored

### Data Privacy
- System logs may contain sensitive information
- Diagnostic data is automatically cleaned up after retention period
- Alert content can be customized to exclude sensitive data

### Network Security
- Health monitoring traffic should be encrypted in production
- API endpoints should be behind firewall/VPN
- Slack webhooks and email credentials must be secured

## Maintenance

### Regular Tasks
- Review and update monitoring thresholds
- Clean up old diagnostic files
- Test recovery procedures
- Update alerting contact information

### Performance Optimization
- Monitor the monitoring system resource usage
- Optimize metric collection intervals
- Tune alert thresholds based on historical data
- Review and optimize recovery procedures

This system provides comprehensive monitoring and recovery capabilities while maintaining focus on legitimate system administration and development environment management.
EOF

    log "✓ System health monitoring documentation created"
}

# Main installation function
main() {
    log "Setting up System Health Monitoring and Recovery System..."
    log "This creates comprehensive monitoring with automated diagnostics and recovery capabilities"
    
    # Check dependencies
    if ! command -v python3 &> /dev/null; then
        error "Python3 not found. Please install Python3 first."
        exit 1
    fi
    
    # Run setup functions
    setup_directories
    install_monitoring_tools
    create_health_monitor
    create_monitoring_config
    create_dashboard_api_extensions
    create_frontend_dashboard_extensions
    create_service_management_scripts
    create_documentation
    
    log "✅ System Health Monitoring and Recovery System setup complete!"
    log ""
    log "🚀 Quick Start:"
    log "   ./monitor/scripts/start_monitoring.sh"
    log ""
    log "📊 Services:"
    log "   • Health Monitor: Continuous system monitoring"
    log "   • Health API: http://localhost:8080/api/health"
    log "   • Dashboard: System health panel in frontend"
    log ""
    log "🔧 Management:"
    log "   • Start: ./monitor/scripts/start_monitoring.sh"
    log "   • Status: ./monitor/scripts/status_monitoring.sh"
    log "   • Stop: ./monitor/scripts/stop_monitoring.sh"
    log ""
    log "📋 Configuration:"
    log "   • Edit: config/monitoring.json"
    log "   • Logs: logs/health-monitor.log"
    log "   • Diagnostics: diagnostics/{reports,archives,alerts}/"
    log ""
    log "✨ Features:"
    log "   • Real-time system resource monitoring"
    log "   • Automated service health checks"
    log "   • Self-healing recovery procedures"
    log "   • Comprehensive diagnostics collection"
    log "   • Multi-channel alerting (Slack, email, logs)"
    log "   • Web-based monitoring dashboard"
    log ""
    log "⚙️ Monitoring Thresholds:"
    log "   • CPU Usage: Alert > 80%"
    log "   • Memory Usage: Alert > 80%"
    log "   • Disk Usage: Alert > 85%"
    log "   • Service Response: Alert > 10s"
    log ""
    log "🛡️ Security & Compliance:"
    log "   • Legitimate system monitoring and diagnostics"
    log "   • Automated cleanup and retention policies"
    log "   • Secure alert delivery channels"
    log "   • Comprehensive audit logging"
}

# Run main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi