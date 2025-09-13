#!/usr/bin/env python3
"""
Chatbot Orchestrator Service
Manages job submission and status tracking for the QA testing framework
"""

from flask import Flask, request, abort, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis
import os
import json
import time
import logging
from datetime import datetime
import uuid
import requests

# Import proxy utilities
try:
    from utils.proxy import create_proxied_session, verify_proxy, get_proxy_info
except ImportError:
    # Fallback if proxy utils not available
    def create_proxied_session():
        return requests.Session()
    def verify_proxy():
        return True
    def get_proxy_info():
        return {}

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Rate limiting configuration
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=[f"{os.environ.get('RATE_LIMIT_PER_MIN', '100')} per minute"]
)

# Redis connection
try:
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    r = redis.from_url(redis_url, decode_responses=True)
    r.ping()  # Test connection
    logger.info(f"Connected to Redis: {redis_url}")
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")
    r = None

# Configuration
CHAT_API_TOKEN = os.environ.get('CHAT_API_TOKEN', 'default-token-change-me')
VALID_JOB_TYPES = ['touch_test', 'network_test', 'image_test', 'full_suite', 'load_test']

def authenticate_request():
    """Validate API token from request headers"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return False
    
    token = auth_header.split(' ', 1)[1] if len(auth_header.split(' ')) > 1 else ''
    return token == CHAT_API_TOKEN

@app.before_request
def before_request():
    """Global request validation"""
    if request.endpoint in ['health', 'metrics']:
        return  # Skip auth for health/metrics endpoints
    
    if not authenticate_request():
        abort(401)

@app.route('/submit', methods=['POST'])
@limiter.limit("50 per minute")
def submit_job():
    """Submit a new test job to the queue"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON payload'}), 400
        
        job_type = data.get('job')
        if not job_type or job_type not in VALID_JOB_TYPES:
            return jsonify({
                'error': 'Invalid job type',
                'valid_types': VALID_JOB_TYPES
            }), 400
        
        # Generate unique job ID
        job_id = f"job_{int(time.time())}_{str(uuid.uuid4())[:8]}"
        
        # Create job payload
        job_payload = {
            'id': job_id,
            'type': job_type,
            'submitted_at': datetime.now().isoformat(),
            'status': 'queued',
            'priority': data.get('priority', 'normal'),
            'parameters': data.get('parameters', {}),
            'requester': get_remote_address()
        }
        
        if r:
            # Add to Redis queue
            r.rpush('test_queue', json.dumps(job_payload))
            
            # Store job status
            r.hset(f"job:{job_id}", mapping={
                'status': 'queued',
                'submitted_at': job_payload['submitted_at'],
                'type': job_type,
                'payload': json.dumps(job_payload)
            })
            
            # Set expiration (24 hours)
            r.expire(f"job:{job_id}", 86400)
            
            logger.info(f"Job submitted: {job_id} ({job_type})")
        else:
            logger.warning(f"Redis unavailable, job {job_id} not queued")
        
        return jsonify({
            'status': 'queued',
            'job_id': job_id,
            'type': job_type,
            'estimated_completion': '5-15 minutes'
        }), 201
        
    except Exception as e:
        logger.error(f"Error submitting job: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/status/<job_id>')
@limiter.limit("200 per minute")
def get_job_status(job_id):
    """Get status of a specific job"""
    try:
        if not r:
            return jsonify({'error': 'Service temporarily unavailable'}), 503
        
        job_data = r.hgetall(f"job:{job_id}")
        
        if not job_data:
            return jsonify({'error': 'Job not found'}), 404
        
        # Get queue position if still queued
        queue_position = None
        if job_data.get('status') == 'queued':
            try:
                queue_items = r.lrange('test_queue', 0, -1)
                for i, item in enumerate(queue_items):
                    item_data = json.loads(item)
                    if item_data.get('id') == job_id:
                        queue_position = i + 1
                        break
            except Exception as e:
                logger.warning(f"Could not determine queue position: {e}")
        
        response = {
            'job_id': job_id,
            'status': job_data.get('status', 'unknown'),
            'type': job_data.get('type'),
            'submitted_at': job_data.get('submitted_at'),
            'started_at': job_data.get('started_at'),
            'completed_at': job_data.get('completed_at'),
            'progress': job_data.get('progress', '0%'),
            'results': json.loads(job_data.get('results', '{}')) if job_data.get('results') else None,
            'error': job_data.get('error')
        }
        
        if queue_position:
            response['queue_position'] = queue_position
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/jobs')
@limiter.limit("100 per minute")
def list_jobs():
    """List recent jobs (admin endpoint)"""
    try:
        if not r:
            return jsonify({'error': 'Service temporarily unavailable'}), 503
        
        # Get job keys (last 50)
        job_keys = []
        for key in r.scan_iter(match="job:*", count=100):
            job_keys.append(key)
        
        # Sort by creation time (newest first)
        job_keys = sorted(job_keys, reverse=True)[:50]
        
        jobs = []
        for key in job_keys:
            job_data = r.hgetall(key)
            if job_data:
                jobs.append({
                    'job_id': key.split(':', 1)[1],
                    'type': job_data.get('type'),
                    'status': job_data.get('status'),
                    'submitted_at': job_data.get('submitted_at')
                })
        
        return jsonify({
            'jobs': jobs,
            'total': len(jobs)
        })
        
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/queue/status')
def queue_status():
    """Get current queue status"""
    try:
        if not r:
            return jsonify({'error': 'Service temporarily unavailable'}), 503
        
        queue_length = r.llen('test_queue')
        
        # Get job type distribution in queue
        job_types = {}
        try:
            queue_items = r.lrange('test_queue', 0, 100)  # Sample first 100
            for item in queue_items:
                job_data = json.loads(item)
                job_type = job_data.get('type', 'unknown')
                job_types[job_type] = job_types.get(job_type, 0) + 1
        except Exception as e:
            logger.warning(f"Could not analyze queue: {e}")
        
        return jsonify({
            'queue_length': queue_length,
            'job_types': job_types,
            'estimated_wait_time_minutes': queue_length * 2  # Rough estimate
        })
        
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/cancel/<job_id>', methods=['POST'])
@limiter.limit("50 per minute")
def cancel_job(job_id):
    """Cancel a queued job"""
    try:
        if not r:
            return jsonify({'error': 'Service temporarily unavailable'}), 503
        
        job_data = r.hgetall(f"job:{job_id}")
        if not job_data:
            return jsonify({'error': 'Job not found'}), 404
        
        current_status = job_data.get('status')
        
        if current_status in ['completed', 'failed', 'cancelled']:
            return jsonify({
                'error': f'Cannot cancel job with status: {current_status}'
            }), 400
        
        if current_status == 'queued':
            # Remove from queue
            queue_items = r.lrange('test_queue', 0, -1)
            for item in queue_items:
                item_data = json.loads(item)
                if item_data.get('id') == job_id:
                    r.lrem('test_queue', 1, item)
                    break
        
        # Update job status
        r.hset(f"job:{job_id}", mapping={
            'status': 'cancelled',
            'cancelled_at': datetime.now().isoformat()
        })
        
        logger.info(f"Job cancelled: {job_id}")
        
        return jsonify({
            'status': 'cancelled',
            'job_id': job_id
        })
        
    except Exception as e:
        logger.error(f"Error cancelling job: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/health')
def health():
    """Health check endpoint with proxy status"""
    health_data = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'redis_connected': r is not None
    }
    
    if r:
        try:
            r.ping()
            health_data['redis_status'] = 'connected'
        except:
            health_data['redis_status'] = 'disconnected'
            health_data['status'] = 'degraded'
    
    # Check proxy status
    try:
        proxy_info = get_proxy_info()
        if proxy_info.get('is_residential'):
            health_data['proxy_status'] = 'active'
            health_data['proxy_info'] = {
                'ip_address': proxy_info.get('ip_address'),
                'country': proxy_info.get('country'),
                'city': proxy_info.get('city'),
                'verified_at': proxy_info.get('verified_at')
            }
        else:
            health_data['proxy_status'] = 'unverified'
    except Exception as e:
        logger.warning(f"Could not check proxy status: {e}")
        health_data['proxy_status'] = 'unavailable'
    
    status_code = 200 if health_data['status'] == 'healthy' else 503
    return jsonify(health_data), status_code

@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint"""
    try:
        metrics_data = []
        
        if r:
            queue_length = r.llen('test_queue')
            metrics_data.append(f"chatbot_queue_length {queue_length}")
            
            # Count jobs by status
            job_statuses = {'queued': 0, 'running': 0, 'completed': 0, 'failed': 0}
            for key in r.scan_iter(match="job:*", count=1000):
                job_data = r.hgetall(key)
                status = job_data.get('status', 'unknown')
                if status in job_statuses:
                    job_statuses[status] += 1
            
            for status, count in job_statuses.items():
                metrics_data.append(f"chatbot_jobs_by_status{{status=\"{status}\"}} {count}")
        
        return '\n'.join(metrics_data), 200, {'Content-Type': 'text/plain'}
    
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        return "# Error generating metrics\n", 500, {'Content-Type': 'text/plain'}

@app.errorhandler(401)
def unauthorized(e):
    return jsonify({'error': 'Unauthorized - invalid API token'}), 401

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({'error': 'Rate limit exceeded', 'retry_after': str(e.retry_after)}), 429

if __name__ == '__main__':
    logger.info("Starting Chatbot Orchestrator Service...")
    logger.info(f"Valid job types: {VALID_JOB_TYPES}")
    
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    app.run(host='0.0.0.0', port=port, debug=debug)