#!/usr/bin/env python3
"""
Inbox Monitoring Service
Real-time email inbox monitoring with message parsing and notifications
"""

import os
import asyncio
import logging
import json
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import re

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
import redis.asyncio as redis
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import aiohttp
import hashlib

# Import our components
from .temp_email_services import get_email_service_manager, EmailMessage
from .email_pool_manager import get_email_pool_manager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Prometheus metrics
messages_processed_total = Counter('messages_processed_total', 'Total messages processed', ['email_provider'])
verification_codes_found = Counter('verification_codes_found_total', 'Verification codes found', ['service'])
monitoring_sessions_active = Gauge('monitoring_sessions_active', 'Active monitoring sessions')
inbox_check_duration = Histogram('inbox_check_duration_seconds', 'Inbox check duration')

# Pydantic models
class MonitorRequest(BaseModel):
    email: str
    service: str = Field(..., description="Service that owns this email")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for notifications")
    poll_interval: int = Field(10, description="Polling interval in seconds")
    timeout: int = Field(3600, description="Monitoring timeout in seconds")
    filters: Optional[Dict] = Field(None, description="Message filters")

class MessageNotification(BaseModel):
    email: str
    service: str
    message: Dict
    verification_codes: List[str] = []
    timestamp: datetime
    webhook_sent: bool = False

class MonitorStatus(BaseModel):
    email: str
    service: str
    status: str  # active, paused, completed, failed
    messages_found: int
    verification_codes_found: int
    started_at: datetime
    last_check: Optional[datetime] = None
    next_check: Optional[datetime] = None

class WebhookDelivery(BaseModel):
    url: str
    payload: Dict
    attempts: int = 0
    max_attempts: int = 3
    last_attempt: Optional[datetime] = None
    success: bool = False
    error_message: Optional[str] = None

# Global instances
redis_client = None
email_manager = None
pool_manager = None
active_monitors: Dict[str, Dict] = {}
websocket_connections: Dict[str, WebSocket] = {}
webhook_queue: List[WebhookDelivery] = []

class MessageFilter:
    """Message filtering and pattern matching"""
    
    def __init__(self, filters: Dict = None):
        self.filters = filters or {}
        
        # Common verification patterns
        self.verification_patterns = [
            r'\b(\d{4,8})\b',                    # 4-8 digit codes
            r'\b([A-Z0-9]{6,8})\b',              # Alphanumeric codes
            r'code[:\s]*(\d{4,8})',              # "Code: 123456"
            r'verification[:\s]*(\d{4,8})',       # "Verification: 123456"
            r'pin[:\s]*(\d{4,6})',               # "PIN: 1234"
            r'otp[:\s]*(\d{4,8})',               # "OTP: 123456"
            r'confirm[:\s]*(\d{4,8})',           # "Confirm: 123456"
            r'activate[:\s]*(\d{4,8})',          # "Activate: 123456"
            r'security\s+code[:\s]*(\d{4,8})',   # "Security code: 123456"
        ]
        
        # Service-specific patterns
        self.service_patterns = {
            'snapchat': [
                r'snapchat.*?(\d{6})',
                r'snap.*?verification.*?(\d{6})',
                r'your\s+snapchat\s+code\s+is[:\s]*(\d{6})'
            ],
            'tinder': [
                r'tinder.*?(\d{4,6})',
                r'your\s+tinder\s+code\s+is[:\s]*(\d{4,6})',
                r'tinder\s+verification[:\s]*(\d{4,6})'
            ],
            'instagram': [
                r'instagram.*?(\d{6})',
                r'your\s+instagram\s+code\s+is[:\s]*(\d{6})',
                r'confirmation\s+code[:\s]*(\d{6})'
            ],
            'facebook': [
                r'facebook.*?(\d{6,8})',
                r'your\s+facebook\s+code\s+is[:\s]*(\d{6,8})',
                r'fb.*?code[:\s]*(\d{6,8})'
            ]
        }
    
    def extract_verification_codes(self, message: EmailMessage, service: str = None) -> List[str]:
        """Extract verification codes from message"""
        codes = set()
        content = f"{message.subject} {message.body}".lower()
        
        # Use service-specific patterns first
        if service and service.lower() in self.service_patterns:
            patterns = self.service_patterns[service.lower()]
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                codes.update(matches)
        
        # Use general patterns
        for pattern in self.verification_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            codes.update(matches)
        
        # Filter and validate codes
        valid_codes = []
        for code in codes:
            if self.is_valid_verification_code(code):
                valid_codes.append(code)
        
        return list(set(valid_codes))  # Remove duplicates
    
    def is_valid_verification_code(self, code: str) -> bool:
        """Validate if code looks like a verification code"""
        if not code or len(code) < 4 or len(code) > 8:
            return False
        
        # Must be numeric or alphanumeric
        if not (code.isdigit() or code.isalnum()):
            return False
        
        # Avoid common false positives
        false_positives = [
            '1234', '0000', '9999', '1111', '2222', '3333', 
            '4444', '5555', '6666', '7777', '8888'
        ]
        
        if code in false_positives:
            return False
        
        return True
    
    def matches_filter(self, message: EmailMessage) -> bool:
        """Check if message matches filters"""
        if not self.filters:
            return True
        
        # Subject filter
        subject_filter = self.filters.get('subject')
        if subject_filter:
            if not re.search(subject_filter, message.subject, re.IGNORECASE):
                return False
        
        # From address filter
        from_filter = self.filters.get('from')
        if from_filter:
            if not re.search(from_filter, message.from_address, re.IGNORECASE):
                return False
        
        # Body content filter
        body_filter = self.filters.get('body')
        if body_filter:
            if not re.search(body_filter, message.body, re.IGNORECASE):
                return False
        
        # Minimum age filter
        min_age = self.filters.get('min_age_seconds')
        if min_age:
            age = (datetime.now() - message.received_at).total_seconds()
            if age < min_age:
                return False
        
        return True

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting Inbox Monitoring Service...")
    
    global redis_client, email_manager, pool_manager
    
    # Initialize Redis
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    redis_client = redis.from_url(redis_url)
    
    # Initialize services
    email_manager = get_email_service_manager()
    pool_manager = get_email_pool_manager()
    
    # Start background tasks
    asyncio.create_task(monitoring_task())
    asyncio.create_task(webhook_delivery_task())
    asyncio.create_task(metrics_update_task())
    
    logger.info("Inbox Monitoring Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Inbox Monitoring Service...")
    if redis_client:
        await redis_client.close()

app = FastAPI(
    title="Inbox Monitoring Service",
    description="Real-time email inbox monitoring and message parsing service",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Service health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_monitors": len(active_monitors),
        "websocket_connections": len(websocket_connections)
    }

@app.post("/monitor/start")
async def start_monitoring(request: MonitorRequest):
    """Start monitoring an email inbox"""
    try:
        monitor_id = f"{request.email}_{request.service}"
        
        if monitor_id in active_monitors:
            raise HTTPException(status_code=409, detail="Monitor already active for this email")
        
        # Create monitor configuration
        monitor_config = {
            'email': request.email,
            'service': request.service,
            'webhook_url': request.webhook_url,
            'poll_interval': request.poll_interval,
            'timeout': request.timeout,
            'filters': MessageFilter(request.filters),
            'status': 'active',
            'messages_found': 0,
            'verification_codes_found': 0,
            'started_at': datetime.now(),
            'last_check': None,
            'next_check': datetime.now(),
            'last_message_count': 0
        }
        
        active_monitors[monitor_id] = monitor_config
        
        # Store in Redis for persistence
        await redis_client.hset(
            "inbox_monitors", 
            monitor_id, 
            json.dumps(monitor_config, default=str)
        )
        
        logger.info(f"Started monitoring {request.email} for {request.service}")
        
        return {
            "monitor_id": monitor_id,
            "status": "started",
            "message": f"Monitoring started for {request.email}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/monitor/{monitor_id}/stop")
async def stop_monitoring(monitor_id: str):
    """Stop monitoring an email inbox"""
    try:
        if monitor_id not in active_monitors:
            raise HTTPException(status_code=404, detail="Monitor not found")
        
        # Update status
        monitor_config = active_monitors[monitor_id]
        monitor_config['status'] = 'stopped'
        monitor_config['stopped_at'] = datetime.now()
        
        # Remove from active monitors
        del active_monitors[monitor_id]
        
        # Remove from Redis
        await redis_client.hdel("inbox_monitors", monitor_id)
        
        logger.info(f"Stopped monitoring {monitor_id}")
        
        return {
            "status": "stopped",
            "message": f"Monitoring stopped for {monitor_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/monitor/{monitor_id}/status", response_model=MonitorStatus)
async def get_monitor_status(monitor_id: str):
    """Get monitor status"""
    try:
        if monitor_id not in active_monitors:
            raise HTTPException(status_code=404, detail="Monitor not found")
        
        config = active_monitors[monitor_id]
        
        return MonitorStatus(
            email=config['email'],
            service=config['service'],
            status=config['status'],
            messages_found=config['messages_found'],
            verification_codes_found=config['verification_codes_found'],
            started_at=config['started_at'],
            last_check=config.get('last_check'),
            next_check=config.get('next_check')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get monitor status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/monitor/list")
async def list_monitors():
    """List all active monitors"""
    try:
        monitors = []
        for monitor_id, config in active_monitors.items():
            monitors.append({
                'monitor_id': monitor_id,
                'email': config['email'],
                'service': config['service'],
                'status': config['status'],
                'messages_found': config['messages_found'],
                'started_at': config['started_at']
            })
        
        return {
            'monitors': monitors,
            'total': len(monitors)
        }
        
    except Exception as e:
        logger.error(f"Failed to list monitors: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/monitor/{monitor_id}/websocket")
async def monitor_websocket(websocket: WebSocket, monitor_id: str):
    """WebSocket connection for real-time monitoring updates"""
    await websocket.accept()
    websocket_connections[monitor_id] = websocket
    
    try:
        while True:
            # Keep connection alive and listen for client messages
            data = await websocket.receive_text()
            
            # Handle client commands
            try:
                command = json.loads(data)
                if command.get('action') == 'ping':
                    await websocket.send_text(json.dumps({'action': 'pong', 'timestamp': datetime.now().isoformat()}))
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for monitor {monitor_id}")
    except Exception as e:
        logger.error(f"WebSocket error for monitor {monitor_id}: {e}")
    finally:
        if monitor_id in websocket_connections:
            del websocket_connections[monitor_id]

@app.get("/monitor/{monitor_id}/messages")
async def get_monitor_messages(monitor_id: str, limit: int = 50):
    """Get recent messages for a monitor"""
    try:
        if monitor_id not in active_monitors:
            raise HTTPException(status_code=404, detail="Monitor not found")
        
        config = active_monitors[monitor_id]
        email = config['email']
        
        # Get messages from email service
        messages = await email_manager.get_inbox_messages(email)
        
        # Apply filters and extract codes
        filtered_messages = []
        message_filter = config['filters']
        
        for message in messages[-limit:]:  # Get recent messages
            if message_filter.matches_filter(message):
                codes = message_filter.extract_verification_codes(message, config['service'])
                
                filtered_messages.append({
                    'id': message.id,
                    'from_address': message.from_address,
                    'subject': message.subject,
                    'body': message.body[:500],  # Truncate body
                    'received_at': message.received_at.isoformat(),
                    'verification_codes': codes
                })
        
        return {
            'email': email,
            'messages': filtered_messages,
            'total': len(filtered_messages)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get monitor messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Background tasks
async def monitoring_task():
    """Main monitoring loop"""
    while True:
        try:
            current_time = datetime.now()
            monitors_to_process = []
            
            # Find monitors ready for checking
            for monitor_id, config in active_monitors.items():
                if (config['status'] == 'active' and 
                    config.get('next_check') and
                    current_time >= config['next_check']):
                    monitors_to_process.append((monitor_id, config))
            
            # Process monitors
            for monitor_id, config in monitors_to_process:
                try:
                    await process_monitor(monitor_id, config)
                except Exception as e:
                    logger.error(f"Error processing monitor {monitor_id}: {e}")
                    config['status'] = 'error'
            
            await asyncio.sleep(5)  # Check every 5 seconds
            
        except Exception as e:
            logger.error(f"Monitoring task error: {e}")
            await asyncio.sleep(10)

async def process_monitor(monitor_id: str, config: Dict):
    """Process a single monitor"""
    try:
        start_time = datetime.now()
        email = config['email']
        service = config['service']
        message_filter = config['filters']
        
        # Check for timeout
        if (datetime.now() - config['started_at']).total_seconds() > config['timeout']:
            config['status'] = 'timeout'
            logger.info(f"Monitor {monitor_id} timed out")
            return
        
        # Get inbox messages
        messages = await email_manager.get_inbox_messages(email)
        
        # Track new messages
        current_count = len(messages)
        last_count = config.get('last_message_count', 0)
        new_messages = messages[last_count:] if current_count > last_count else []
        
        # Process new messages
        for message in new_messages:
            if message_filter.matches_filter(message):
                # Extract verification codes
                codes = message_filter.extract_verification_codes(message, service)
                
                if codes:
                    config['verification_codes_found'] += len(codes)
                    verification_codes_found.labels(service=service).inc(len(codes))
                    
                    logger.info(f"Found verification codes for {email}: {codes}")
                
                # Create notification
                notification = MessageNotification(
                    email=email,
                    service=service,
                    message={
                        'id': message.id,
                        'from_address': message.from_address,
                        'subject': message.subject,
                        'body': message.body,
                        'received_at': message.received_at.isoformat()
                    },
                    verification_codes=codes,
                    timestamp=datetime.now()
                )
                
                # Send WebSocket notification
                await send_websocket_notification(monitor_id, notification)
                
                # Queue webhook if configured
                if config.get('webhook_url'):
                    webhook_delivery = WebhookDelivery(
                        url=config['webhook_url'],
                        payload=notification.dict()
                    )
                    webhook_queue.append(webhook_delivery)
                
                config['messages_found'] += 1
        
        # Update monitor state
        config['last_check'] = datetime.now()
        config['next_check'] = datetime.now() + timedelta(seconds=config['poll_interval'])
        config['last_message_count'] = current_count
        
        # Update metrics
        duration = (datetime.now() - start_time).total_seconds()
        inbox_check_duration.observe(duration)
        messages_processed_total.labels(email_provider='all').inc(len(new_messages))
        
    except Exception as e:
        logger.error(f"Error processing monitor {monitor_id}: {e}")
        config['status'] = 'error'

async def send_websocket_notification(monitor_id: str, notification: MessageNotification):
    """Send notification via WebSocket"""
    try:
        if monitor_id in websocket_connections:
            websocket = websocket_connections[monitor_id]
            message = {
                'type': 'message_notification',
                'data': notification.dict(default=str)
            }
            await websocket.send_text(json.dumps(message))
    except Exception as e:
        logger.error(f"Failed to send WebSocket notification: {e}")

async def webhook_delivery_task():
    """Deliver webhooks in background"""
    while True:
        try:
            if webhook_queue:
                webhook = webhook_queue.pop(0)
                success = await deliver_webhook(webhook)
                
                if not success and webhook.attempts < webhook.max_attempts:
                    # Retry later
                    webhook_queue.append(webhook)
            
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Webhook delivery task error: {e}")

async def deliver_webhook(webhook: WebhookDelivery) -> bool:
    """Deliver a single webhook"""
    try:
        webhook.attempts += 1
        webhook.last_attempt = datetime.now()
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook.url,
                json=webhook.payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    webhook.success = True
                    logger.info(f"Webhook delivered successfully to {webhook.url}")
                    return True
                else:
                    webhook.error_message = f"HTTP {response.status}"
                    logger.warning(f"Webhook delivery failed: HTTP {response.status}")
                    return False
                    
    except Exception as e:
        webhook.error_message = str(e)
        logger.error(f"Webhook delivery failed to {webhook.url}: {e}")
        return False

async def metrics_update_task():
    """Update Prometheus metrics"""
    while True:
        try:
            monitoring_sessions_active.set(len(active_monitors))
            await asyncio.sleep(60)  # Update every minute
        except Exception as e:
            logger.error(f"Metrics update error: {e}")

if __name__ == "__main__":
    uvicorn.run(
        "inbox_monitor_service:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8004)),
        log_level="info",
        reload=False
    )