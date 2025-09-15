#!/usr/bin/env python3
"""
Email Creation Microservice
FastAPI service for email account creation and management
"""

import os
import asyncio
import logging
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
import redis.asyncio as redis
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

# Import our email components
from .temp_email_services import EmailProviderType, get_email_service_manager
from .email_pool_manager import get_email_pool_manager
from .captcha_solver import get_captcha_solver, CaptchaType

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Prometheus metrics
email_requests_total = Counter('email_requests_total', 'Total email requests', ['service', 'status'])
email_creation_duration = Histogram('email_creation_duration_seconds', 'Email creation duration')
active_emails_gauge = Gauge('active_emails_total', 'Number of active email accounts')
provider_success_rate = Gauge('provider_success_rate', 'Provider success rate', ['provider'])

# Pydantic models
class EmailRequest(BaseModel):
    service: str = Field(..., description="Service requesting the email")
    purpose: str = Field(default="general", description="Purpose of the email")
    preferred_provider: Optional[str] = Field(None, description="Preferred email provider")
    expires_in_minutes: Optional[int] = Field(60, description="Email expiry in minutes")

class EmailResponse(BaseModel):
    email: str
    provider: str
    expires_at: datetime
    created_at: datetime

class EmailReturnRequest(BaseModel):
    email: str
    success: bool = True
    spam_reported: bool = False
    bounced: bool = False
    notes: Optional[str] = None

class EmailMessage(BaseModel):
    id: str
    from_address: str
    subject: str
    body: str
    received_at: datetime
    verification_codes: List[str] = []

class InboxResponse(BaseModel):
    email: str
    message_count: int
    messages: List[EmailMessage]
    last_checked: datetime

class CaptchaSolveRequest(BaseModel):
    captcha_type: str = Field(..., description="Type of CAPTCHA (image, recaptcha_v2, etc.)")
    image_data: Optional[str] = Field(None, description="Base64 encoded image data")
    site_key: Optional[str] = Field(None, description="Site key for reCAPTCHA/hCAPTCHA")
    page_url: Optional[str] = Field(None, description="Page URL for reCAPTCHA/hCAPTCHA")
    timeout: int = Field(300, description="Timeout in seconds")

class CaptchaResponse(BaseModel):
    solution: Optional[str]
    solved: bool
    provider_used: Optional[str] = None
    solve_time: float = 0.0

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str = "1.0.0"
    services: Dict[str, bool]

# Global instances
redis_client = None
email_manager = None
pool_manager = None
captcha_solver = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting Email Creation Service...")
    
    global redis_client, email_manager, pool_manager, captcha_solver
    
    # Initialize Redis
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    redis_client = redis.from_url(redis_url)
    
    # Initialize email services
    email_manager = get_email_service_manager()
    pool_manager = get_email_pool_manager()
    captcha_solver = get_captcha_solver()
    
    # Initialize email pool
    await pool_manager.initialize_pool(initial_size=20)
    
    # Start background tasks
    asyncio.create_task(pool_cleanup_task())
    asyncio.create_task(metrics_update_task())
    
    logger.info("Email Creation Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Email Creation Service...")
    if redis_client:
        await redis_client.close()

app = FastAPI(
    title="Email Creation Service",
    description="Production-ready email account creation and management service",
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

# Dependency to get Redis client
async def get_redis():
    return redis_client

# API Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Service health check"""
    services = {
        "redis": await _check_redis_health(),
        "email_providers": await _check_email_providers_health(),
        "captcha_providers": await _check_captcha_providers_health()
    }
    
    all_healthy = all(services.values())
    
    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        timestamp=datetime.now(),
        services=services
    )

@app.post("/email/create", response_model=EmailResponse)
async def create_email_account(request: EmailRequest, background_tasks: BackgroundTasks):
    """Create a new temporary email account"""
    start_time = datetime.now()
    
    try:
        # Get email from pool
        preferred_provider = None
        if request.preferred_provider:
            try:
                preferred_provider = EmailProviderType(request.preferred_provider.lower())
            except ValueError:
                logger.warning(f"Invalid provider: {request.preferred_provider}")
        
        account = await pool_manager.get_email_account(request.service, request.purpose)
        
        if not account:
            email_requests_total.labels(service=request.service, status="failed").inc()
            raise HTTPException(status_code=503, detail="No email accounts available")
        
        # Record metrics
        duration = (datetime.now() - start_time).total_seconds()
        email_creation_duration.observe(duration)
        email_requests_total.labels(service=request.service, status="success").inc()
        
        logger.info(f"Created email {account.email} for {request.service}")
        
        return EmailResponse(
            email=account.email,
            provider=account.provider.value,
            expires_at=account.expires_at,
            created_at=account.created_at
        )
        
    except Exception as e:
        email_requests_total.labels(service=request.service, status="error").inc()
        logger.error(f"Failed to create email account: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/email/return")
async def return_email_account(request: EmailReturnRequest):
    """Return email account to pool"""
    try:
        success = await pool_manager.return_email_account(
            request.email,
            request.success,
            request.spam_reported,
            request.bounced
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Email account not found")
        
        logger.info(f"Returned email {request.email} to pool (success: {request.success})")
        
        return {"status": "success", "message": "Email returned to pool"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to return email account: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/email/{email}/inbox", response_model=InboxResponse)
async def get_inbox_messages(email: str):
    """Get messages from email inbox"""
    try:
        messages = await email_manager.get_inbox_messages(email)
        
        # Convert to response format
        message_objects = []
        for msg in messages:
            message_objects.append(EmailMessage(
                id=msg.id,
                from_address=msg.from_address,
                subject=msg.subject,
                body=msg.body,
                received_at=msg.received_at,
                verification_codes=msg.verification_codes or []
            ))
        
        return InboxResponse(
            email=email,
            message_count=len(message_objects),
            messages=message_objects,
            last_checked=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Failed to get inbox messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/email/{email}/wait-for-verification")
async def wait_for_verification_code(email: str, timeout: int = 300):
    """Wait for verification email and return code"""
    try:
        from .temp_email_services import wait_for_verification_email
        
        code = await wait_for_verification_email(email, timeout)
        
        if code:
            return {
                "found": True,
                "verification_code": code,
                "email": email
            }
        else:
            return {
                "found": False,
                "message": f"No verification email received within {timeout} seconds",
                "email": email
            }
            
    except Exception as e:
        logger.error(f"Failed to wait for verification email: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/captcha/solve", response_model=CaptchaResponse)
async def solve_captcha(request: CaptchaSolveRequest):
    """Solve CAPTCHA using available providers"""
    start_time = datetime.now()
    
    try:
        # Convert string to enum
        try:
            captcha_type = CaptchaType(request.captcha_type.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid CAPTCHA type: {request.captcha_type}")
        
        # Solve CAPTCHA
        solution = await captcha_solver.solve_captcha(
            captcha_type=captcha_type,
            image_data=request.image_data,
            site_key=request.site_key,
            page_url=request.page_url,
            timeout=request.timeout
        )
        
        solve_time = (datetime.now() - start_time).total_seconds()
        
        return CaptchaResponse(
            solution=solution,
            solved=solution is not None,
            solve_time=solve_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to solve CAPTCHA: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats/pool")
async def get_pool_statistics():
    """Get email pool statistics"""
    try:
        stats = await pool_manager.get_pool_statistics()
        return stats
    except Exception as e:
        logger.error(f"Failed to get pool statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats/providers")
async def get_provider_statistics():
    """Get email provider statistics"""
    try:
        stats = email_manager.get_provider_statistics()
        return stats
    except Exception as e:
        logger.error(f"Failed to get provider statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats/captcha")
async def get_captcha_statistics():
    """Get CAPTCHA solver statistics"""
    try:
        stats = captcha_solver.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Failed to get CAPTCHA statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/admin/pool/refill")
async def refill_pool(target_size: int = 20):
    """Manually trigger pool refill"""
    try:
        current_size = await pool_manager.get_pool_size()
        if current_size >= target_size:
            return {"message": f"Pool already has {current_size} accounts"}
        
        # Trigger background refill
        asyncio.create_task(pool_manager._refill_pool())
        
        return {"message": f"Pool refill triggered (current: {current_size}, target: {target_size})"}
        
    except Exception as e:
        logger.error(f"Failed to trigger pool refill: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/pool/cleanup")
async def cleanup_pool():
    """Manually trigger pool cleanup"""
    try:
        removed = await pool_manager.cleanup_expired_accounts()
        return {"message": f"Cleanup complete: removed {removed} expired accounts"}
    except Exception as e:
        logger.error(f"Failed to cleanup pool: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Background tasks
async def pool_cleanup_task():
    """Background task for pool cleanup"""
    while True:
        try:
            await asyncio.sleep(300)  # Run every 5 minutes
            removed = await pool_manager.cleanup_expired_accounts()
            if removed > 0:
                logger.info(f"Background cleanup: removed {removed} expired accounts")
        except Exception as e:
            logger.error(f"Pool cleanup task error: {e}")

async def metrics_update_task():
    """Background task to update metrics"""
    while True:
        try:
            await asyncio.sleep(60)  # Update every minute
            
            # Update active emails gauge
            stats = await pool_manager.get_pool_statistics()
            active_emails_gauge.set(stats.get('available', 0))
            
            # Update provider success rates
            provider_stats = email_manager.get_provider_statistics()
            for provider, provider_data in provider_stats.get('provider_stats', {}).items():
                success_rate = provider_data.get('success_rate', 0)
                provider_success_rate.labels(provider=provider).set(success_rate)
                
        except Exception as e:
            logger.error(f"Metrics update task error: {e}")

# Health check helpers
async def _check_redis_health() -> bool:
    """Check Redis connection health"""
    try:
        await redis_client.ping()
        return True
    except Exception:
        return False

async def _check_email_providers_health() -> bool:
    """Check email providers health"""
    try:
        # Try to create a test account
        account = await email_manager.create_email_account()
        if account:
            # Clean up test account
            await email_manager.delete_email_account(account.email)
            return True
        return False
    except Exception:
        return False

async def _check_captcha_providers_health() -> bool:
    """Check CAPTCHA providers health"""
    try:
        balances = captcha_solver.get_provider_balances()
        # Consider healthy if at least one provider has balance > 0
        return any(balance > 0 for balance in balances.values())
    except Exception:
        return False

if __name__ == "__main__":
    # Run the service
    uvicorn.run(
        "email_creation_service:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8003)),
        log_level="info",
        reload=False
    )