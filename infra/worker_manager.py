#!/usr/bin/env python3
"""
Worker Manager Service
Monitors and manages the worker pool, handles scaling and health checks
"""

import os
import sys
import time
import redis
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import threading
import signal

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WorkerManager:
    def __init__(self):
        self.redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
        self.orchestrator_url = os.environ.get('ORCHESTRATOR_URL', 'http://orchestrator:5000')
        self.redis_client = self._setup_redis()
        self.running = True
        self.check_interval = 60  # seconds
        self.cleanup_interval = 300  # 5 minutes
        
    def _setup_redis(self):
        """Initialize Redis connection"""
        try:
            client = redis.from_url(self.redis_url, decode_responses=True)
            client.ping()
            logger.info("Connected to Redis successfully")
            return client
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return None
    
    def get_active_workers(self) -> List[Dict]:
        """Get list of active workers"""
        if not self.redis_client:
            return []
        
        try:
            worker_ids = self.redis_client.smembers('workers')
            workers = []
            
            for worker_id in worker_ids:
                worker_data = self.redis_client.hgetall(f"worker:{worker_id}")
                if worker_data:
                    workers.append({
                        'id': worker_id,
                        **worker_data
                    })
            
            return workers
        except Exception as e:
            logger.error(f"Failed to get active workers: {e}")
            return []
    
    def check_worker_health(self, worker: Dict) -> bool:
        """Check if a worker is healthy"""
        try:
            last_heartbeat = worker.get('last_heartbeat')
            if not last_heartbeat:
                return False
            
            # Parse timestamp
            heartbeat_time = datetime.fromisoformat(last_heartbeat.replace('Z', '+00:00'))
            time_since_heartbeat = datetime.now(heartbeat_time.tzinfo) - heartbeat_time
            
            # Consider worker unhealthy if no heartbeat for 5 minutes
            return time_since_heartbeat < timedelta(minutes=5)
            
        except Exception as e:
            logger.warning(f"Failed to check worker {worker.get('id')} health: {e}")
            return False
    
    def cleanup_stale_workers(self) -> int:
        """Remove stale workers from the registry"""
        workers = self.get_active_workers()
        cleaned_count = 0
        
        for worker in workers:
            if not self.check_worker_health(worker):
                worker_id = worker['id']
                logger.info(f"Cleaning up stale worker: {worker_id}")
                
                try:
                    # Remove from workers set
                    self.redis_client.srem('workers', worker_id)
                    
                    # Update worker status
                    self.redis_client.hset(f"worker:{worker_id}", 
                                         'status', 'stale',
                                         'cleaned_at', datetime.now().isoformat())
                    
                    cleaned_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to cleanup worker {worker_id}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} stale workers")
        
        return cleaned_count
    
    def get_queue_stats(self) -> Dict:
        """Get current queue statistics"""
        try:
            if not self.redis_client:
                return {}
            
            queue_length = self.redis_client.llen('test_queue')
            
            # Count jobs by status
            job_statuses = {'queued': 0, 'running': 0, 'completed': 0, 'failed': 0}
            
            # Sample recent jobs for status distribution
            for key in self.redis_client.scan_iter(match="job:*", count=100):
                job_data = self.redis_client.hgetall(key)
                status = job_data.get('status', 'unknown')
                if status in job_statuses:
                    job_statuses[status] += 1
            
            return {
                'queue_length': queue_length,
                'job_statuses': job_statuses,
                'total_jobs': sum(job_statuses.values())
            }
            
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {}
    
    def calculate_scaling_recommendation(self, workers: List[Dict], queue_stats: Dict) -> str:
        """Calculate if workers should be scaled up or down"""
        active_workers = len([w for w in workers if self.check_worker_health(w)])
        queue_length = queue_stats.get('queue_length', 0)
        
        # Simple scaling logic
        if queue_length > active_workers * 5:  # More than 5 jobs per worker
            return "scale_up"
        elif queue_length == 0 and active_workers > 1:  # No jobs and more than 1 worker
            return "scale_down"
        else:
            return "maintain"
    
    def generate_worker_report(self) -> Dict:
        """Generate comprehensive worker status report"""
        workers = self.get_active_workers()
        queue_stats = self.get_queue_stats()
        
        healthy_workers = [w for w in workers if self.check_worker_health(w)]
        stale_workers = [w for w in workers if not self.check_worker_health(w)]
        
        # Calculate utilization
        total_capacity = len(healthy_workers) * 3  # Assuming 3 concurrent jobs per worker
        current_load = queue_stats.get('queue_length', 0)
        utilization = (current_load / total_capacity * 100) if total_capacity > 0 else 0
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'worker_stats': {
                'total': len(workers),
                'healthy': len(healthy_workers),
                'stale': len(stale_workers),
                'utilization_percent': round(utilization, 1)
            },
            'queue_stats': queue_stats,
            'scaling_recommendation': self.calculate_scaling_recommendation(workers, queue_stats),
            'workers': [
                {
                    'id': w['id'],
                    'status': w.get('status', 'unknown'),
                    'healthy': self.check_worker_health(w),
                    'capabilities': w.get('capabilities', '').split(','),
                    'last_heartbeat': w.get('last_heartbeat'),
                    'cpu_cores': w.get('cpu_cores'),
                    'memory_gb': w.get('memory_gb')
                } for w in workers
            ]
        }
        
        return report
    
    def store_report(self, report: Dict):
        """Store worker report in Redis"""
        try:
            if self.redis_client:
                # Store latest report
                self.redis_client.set('worker_manager:latest_report', 
                                    json.dumps(report), ex=3600)  # 1 hour expiry
                
                # Store in time series (keep last 24 reports)
                timestamp = int(time.time())
                self.redis_client.zadd('worker_manager:reports', {json.dumps(report): timestamp})
                
                # Clean old reports (keep last 24 hours)
                cutoff = timestamp - 86400
                self.redis_client.zremrangebyscore('worker_manager:reports', 0, cutoff)
                
        except Exception as e:
            logger.error(f"Failed to store report: {e}")
    
    def monitor_loop(self):
        """Main monitoring loop"""
        logger.info("Starting worker monitoring loop...")
        
        last_cleanup = time.time()
        
        while self.running:
            try:
                # Generate worker report
                report = self.generate_worker_report()
                
                # Log summary
                stats = report['worker_stats']
                queue_stats = report['queue_stats']
                logger.info(f"Worker status: {stats['healthy']}/{stats['total']} healthy, "
                           f"Queue: {queue_stats.get('queue_length', 0)} jobs, "
                           f"Utilization: {stats['utilization_percent']}%")
                
                # Store report
                self.store_report(report)
                
                # Periodic cleanup
                current_time = time.time()
                if current_time - last_cleanup > self.cleanup_interval:
                    self.cleanup_stale_workers()
                    last_cleanup = current_time
                
                # Wait before next check
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                logger.info("Received interrupt, stopping monitoring...")
                self.running = False
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(30)  # Wait longer on error
    
    def stop(self):
        """Stop the worker manager"""
        logger.info("Stopping worker manager...")
        self.running = False

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    global worker_manager
    if worker_manager:
        worker_manager.stop()

def main():
    """Main function"""
    global worker_manager
    
    # Set up signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Initialize worker manager
    worker_manager = WorkerManager()
    
    logger.info("Worker Manager starting...")
    logger.info(f"Redis URL: {worker_manager.redis_url}")
    logger.info(f"Orchestrator URL: {worker_manager.orchestrator_url}")
    
    try:
        # Run monitoring loop
        worker_manager.monitor_loop()
        
    except Exception as e:
        logger.error(f"Worker manager failed: {e}")
        return 1
    
    logger.info("Worker Manager stopped")
    return 0

if __name__ == "__main__":
    sys.exit(main())