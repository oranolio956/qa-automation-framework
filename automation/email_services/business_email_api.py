#!/usr/bin/env python3
"""
Business Email Service API
Comprehensive FastAPI service for legitimate business email operations
"""

import os
import uuid
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, EmailStr
import uvicorn

# Import our business email components
from business_email_service import (
    get_business_email_manager,
    BusinessEmailManager,
    EmailProviderType,
    EmailAccountType
)
from email_template_manager import (
    get_template_manager,
    EmailTemplateManager,
    EmailTemplate,
    TemplateType,
    TemplateStatus
)
from secure_credentials_manager import (
    get_credentials_manager,
    SecureCredentialsManager,
    CredentialType
)
from email_analytics import (
    get_email_analytics,
    EmailAnalytics,
    EmailEvent,
    EventType
)
from inbox_monitor_service import get_email_integrator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

# Pydantic models for API
class CreateAccountRequest(BaseModel):
    email: EmailStr = Field(..., description="Email address for the account")
    provider: EmailProviderType = Field(..., description="Email provider type")
    account_type: EmailAccountType = Field(..., description="Account type")
    display_name: Optional[str] = Field(None, description="Display name for the account")
    credentials: Optional[Dict] = Field(None, description="Provider-specific credentials")

class SendEmailRequest(BaseModel):
    from_email: EmailStr = Field(..., description="Sender email address")
    to_emails: List[EmailStr] = Field(..., description="Recipient email addresses")
    subject: str = Field(..., description="Email subject")
    body_text: str = Field(..., description="Plain text body")
    body_html: Optional[str] = Field(None, description="HTML body")
    cc_emails: Optional[List[EmailStr]] = Field(None, description="CC recipients")
    bcc_emails: Optional[List[EmailStr]] = Field(None, description="BCC recipients")
    template_id: Optional[str] = Field(None, description="Template ID to use")
    template_variables: Optional[Dict] = Field(None, description="Variables for template")
    attachments: Optional[List[Dict]] = Field(None, description="Email attachments")
    priority: Optional[str] = Field("normal", description="Email priority (low, normal, high)")
    tracking_enabled: bool = Field(True, description="Enable email tracking")

class CreateTemplateRequest(BaseModel):
    name: str = Field(..., description="Template name")
    template_type: TemplateType = Field(..., description="Template type")
    subject: str = Field(..., description="Email subject template")
    body_text: str = Field(..., description="Plain text body template")
    body_html: Optional[str] = Field(None, description="HTML body template")
    description: Optional[str] = Field(None, description="Template description")
    tags: Optional[List[str]] = Field(None, description="Template tags")

class UpdateTemplateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Template name")
    subject: Optional[str] = Field(None, description="Email subject template")
    body_text: Optional[str] = Field(None, description="Plain text body template")
    body_html: Optional[str] = Field(None, description="HTML body template")
    description: Optional[str] = Field(None, description="Template description")
    tags: Optional[List[str]] = Field(None, description="Template tags")
    status: Optional[TemplateStatus] = Field(None, description="Template status")

class MonitorInboxRequest(BaseModel):
    email: EmailStr = Field(..., description="Email address to monitor")
    timeout_seconds: int = Field(300, description="Monitoring timeout in seconds")
    check_interval: int = Field(10, description="Check interval in seconds")
    verification_patterns: Optional[List[str]] = Field(None, description="Custom verification patterns")

class StoreCredentialRequest(BaseModel):
    email_address: EmailStr = Field(..., description="Email address")
    provider: str = Field(..., description="Provider name")
    credential_type: CredentialType = Field(..., description="Credential type")
    value: str = Field(..., description="Credential value")
    expires_at: Optional[datetime] = Field(None, description="Expiration time")
    metadata: Optional[Dict] = Field(None, description="Additional metadata")

class EmailAccountResponse(BaseModel):
    email: str
    provider: str
    account_type: str
    display_name: Optional[str]
    is_verified: bool
    is_active: bool
    created_at: datetime
    usage_stats: Dict

class SendEmailResponse(BaseModel):
    success: bool
    message_id: Optional[str] = None
    tracking_id: Optional[str] = None
    error_message: Optional[str] = None
    processing_time: float = 0.0

class TemplateResponse(BaseModel):
    id: str
    name: str
    template_type: str
    subject: str
    variables: List[str]
    status: str
    created_at: datetime
    updated_at: datetime
    usage_count: int

class InboxMonitorResponse(BaseModel):
    success: bool
    verification_code: Optional[str] = None
    messages_found: int = 0
    time_taken: float = 0.0
    error_message: Optional[str] = None

class AnalyticsResponse(BaseModel):
    period_start: datetime
    period_end: datetime
    emails_sent: int
    emails_received: int
    delivery_rate: float
    bounce_rate: float
    avg_processing_time: float
    provider_performance: Dict
    recommendations: List[str]

# Global service instances
email_manager: BusinessEmailManager = None
template_manager: EmailTemplateManager = None
credentials_manager: SecureCredentialsManager = None
analytics: EmailAnalytics = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting Business Email Service API...")
    
    global email_manager, template_manager, credentials_manager, analytics
    
    # Initialize services
    email_manager = get_business_email_manager({
        'gmail': {'enabled': True},
        'outlook': {'enabled': True},
        'custom_smtp': {'enabled': True}
    })
    
    template_manager = get_template_manager({
        'db_path': 'business_email_templates.db'
    })
    
    credentials_manager = get_credentials_manager({
        'db_path': 'business_email_credentials.db'
    })
    
    analytics = get_email_analytics({
        'db_path': 'business_email_analytics.db'
    })
    
    # Create default templates
    template_manager.create_default_templates()
    
    # Start background tasks
    asyncio.create_task(cleanup_task())
    asyncio.create_task(analytics_aggregation_task())
    
    logger.info("Business Email Service API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Business Email Service API...")

app = FastAPI(
    title="Business Email Service API",
    description="Professional email service for legitimate business communications",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to verify API key
async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API key for authentication"""
    # In production, implement proper API key verification
    api_key = credentials.credentials
    expected_key = os.getenv('BUSINESS_EMAIL_API_KEY', 'your-secure-api-key')
    
    if api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return api_key

# Exception handler for better error responses
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Service health check"""
    try:
        # Check service components
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "components": {
                "email_manager": bool(email_manager),
                "template_manager": bool(template_manager),
                "credentials_manager": bool(credentials_manager),
                "analytics": bool(analytics)
            }
        }
        
        # Add analytics summary
        if analytics:
            realtime_metrics = analytics.get_realtime_metrics()
            health_status["metrics"] = {
                "emails_per_hour": realtime_metrics.get("emails_per_hour", 0),
                "avg_processing_time": realtime_metrics.get("avg_processing_time", 0),
                "provider_health": realtime_metrics.get("provider_health", {})
            }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

# Account management endpoints
@app.post("/accounts", response_model=EmailAccountResponse)
async def create_email_account(
    request: CreateAccountRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """Create a new business email account"""
    try:
        start_time = datetime.now()
        
        # Create account
        account = await email_manager.create_business_email_account(
            email=str(request.email),
            provider=request.provider,
            account_type=request.account_type
        )
        
        # Store credentials if provided
        if request.credentials:
            for cred_type, value in request.credentials.items():
                try:
                    credential_type = CredentialType(cred_type)
                    credentials_manager.store_credential(
                        email_address=str(request.email),
                        provider=request.provider.value,
                        credential_type=credential_type,
                        value=str(value)
                    )
                except ValueError:
                    logger.warning(f"Unknown credential type: {cred_type}")
        
        # Track event
        event = EmailEvent(
            id=str(uuid.uuid4()),
            event_type=EventType.CREDENTIAL_ACCESSED,
            timestamp=start_time,
            email_address=str(request.email),
            provider=request.provider.value,
            processing_time=(datetime.now() - start_time).total_seconds(),
            metadata={"action": "account_created"}
        )
        analytics.track_event(event)
        
        return EmailAccountResponse(
            email=account.email,
            provider=account.provider.value,
            account_type=account.account_type.value,
            display_name=account.display_name,
            is_verified=account.is_verified,
            is_active=account.is_active,
            created_at=account.created_at,
            usage_stats=account.usage_stats
        )
        
    except Exception as e:
        logger.error(f"Failed to create email account: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/accounts", response_model=List[EmailAccountResponse])
async def list_email_accounts(api_key: str = Depends(verify_api_key)):
    """List all email accounts"""
    try:
        accounts = email_manager.get_all_accounts()
        
        return [
            EmailAccountResponse(
                email=acc["email"],
                provider=acc["provider"],
                account_type=acc["account_type"],
                display_name=acc.get("display_name"),
                is_verified=acc["is_verified"],
                is_active=acc["is_active"],
                created_at=datetime.fromisoformat(acc["created_at"]),
                usage_stats=email_manager.get_account_statistics(acc["email"]).get("usage_stats", {})
            )
            for acc in accounts
        ]
        
    except Exception as e:
        logger.error(f"Failed to list email accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/accounts/{email}/stats")
async def get_account_statistics(
    email: str,
    api_key: str = Depends(verify_api_key)
):
    """Get account usage statistics"""
    try:
        stats = email_manager.get_account_statistics(email)
        
        if not stats:
            raise HTTPException(status_code=404, detail="Account not found")
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get account statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Email sending endpoints
@app.post("/send", response_model=SendEmailResponse)
async def send_email(
    request: SendEmailRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """Send business email"""
    try:
        start_time = datetime.now()
        tracking_id = str(uuid.uuid4())
        
        # Use template if specified
        if request.template_id:
            render_result = template_manager.render_template(
                request.template_id,
                request.template_variables or {}
            )
            
            if not render_result.success:
                raise HTTPException(
                    status_code=400,
                    detail=f"Template rendering failed: {render_result.error_message}"
                )
            
            subject = render_result.subject
            body_text = render_result.body_text
            body_html = render_result.body_html
            
            # Track template usage
            template_event = EmailEvent(
                id=str(uuid.uuid4()),
                event_type=EventType.TEMPLATE_RENDERED,
                timestamp=datetime.now(),
                email_address=str(request.from_email),
                provider="template_engine",
                template_id=request.template_id,
                processing_time=render_result.render_time
            )
            analytics.track_event(template_event)
        else:
            subject = request.subject
            body_text = request.body_text
            body_html = request.body_html
        
        # Send email
        success = await email_manager.send_business_email(
            from_email=str(request.from_email),
            to_emails=[str(email) for email in request.to_emails],
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            cc_emails=[str(email) for email in (request.cc_emails or [])],
            attachments=request.attachments or []
        )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Track sending event
        send_event = EmailEvent(
            id=tracking_id,
            event_type=EventType.EMAIL_SENT,
            timestamp=start_time,
            email_address=str(request.from_email),
            provider="business_email",  # Will be updated with actual provider
            subject=subject,
            recipient_count=len(request.to_emails),
            processing_time=processing_time,
            template_id=request.template_id,
            error_message=None if success else "Email sending failed"
        )
        analytics.track_event(send_event)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send email")
        
        return SendEmailResponse(
            success=success,
            tracking_id=tracking_id,
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Template management endpoints
@app.post("/templates", response_model=TemplateResponse)
async def create_template(
    request: CreateTemplateRequest,
    api_key: str = Depends(verify_api_key)
):
    """Create email template"""
    try:
        template_id = str(uuid.uuid4())
        
        template = EmailTemplate(
            id=template_id,
            name=request.name,
            template_type=request.template_type,
            subject=request.subject,
            body_text=request.body_text,
            body_html=request.body_html,
            description=request.description,
            tags=request.tags or [],
            status=TemplateStatus.ACTIVE
        )
        
        if not template_manager.create_template(template):
            raise HTTPException(status_code=500, detail="Failed to create template")
        
        return TemplateResponse(
            id=template.id,
            name=template.name,
            template_type=template.template_type.value,
            subject=template.subject,
            variables=template.variables,
            status=template.status.value,
            created_at=template.created_at,
            updated_at=template.updated_at,
            usage_count=template.usage_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/templates", response_model=List[TemplateResponse])
async def list_templates(
    template_type: Optional[TemplateType] = None,
    status: Optional[TemplateStatus] = None,
    api_key: str = Depends(verify_api_key)
):
    """List email templates"""
    try:
        templates = template_manager.list_templates(
            template_type=template_type,
            status=status
        )
        
        return [
            TemplateResponse(
                id=template.id,
                name=template.name,
                template_type=template.template_type.value,
                subject=template.subject,
                variables=template.variables,
                status=template.status.value,
                created_at=template.created_at,
                updated_at=template.updated_at,
                usage_count=template.usage_count
            )
            for template in templates
        ]
        
    except Exception as e:
        logger.error(f"Failed to list templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get template by ID"""
    try:
        template = template_manager.get_template(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return TemplateResponse(
            id=template.id,
            name=template.name,
            template_type=template.template_type.value,
            subject=template.subject,
            variables=template.variables,
            status=template.status.value,
            created_at=template.created_at,
            updated_at=template.updated_at,
            usage_count=template.usage_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/templates/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    request: UpdateTemplateRequest,
    api_key: str = Depends(verify_api_key)
):
    """Update template"""
    try:
        # Get existing template
        template = template_manager.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Prepare updates
        updates = {}
        if request.name is not None:
            updates['name'] = request.name
        if request.subject is not None:
            updates['subject'] = request.subject
        if request.body_text is not None:
            updates['body_text'] = request.body_text
        if request.body_html is not None:
            updates['body_html'] = request.body_html
        if request.description is not None:
            updates['description'] = request.description
        if request.tags is not None:
            updates['tags'] = request.tags
        if request.status is not None:
            updates['status'] = request.status
        
        if not template_manager.update_template(template_id, updates):
            raise HTTPException(status_code=500, detail="Failed to update template")
        
        # Get updated template
        updated_template = template_manager.get_template(template_id)
        
        return TemplateResponse(
            id=updated_template.id,
            name=updated_template.name,
            template_type=updated_template.template_type.value,
            subject=updated_template.subject,
            variables=updated_template.variables,
            status=updated_template.status.value,
            created_at=updated_template.created_at,
            updated_at=updated_template.updated_at,
            usage_count=updated_template.usage_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/templates/{template_id}")
async def delete_template(
    template_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Delete template"""
    try:
        if not template_manager.delete_template(template_id):
            raise HTTPException(status_code=404, detail="Template not found")
        
        return {"message": "Template deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Inbox monitoring endpoints
@app.post("/monitor/inbox", response_model=InboxMonitorResponse)
async def monitor_inbox_for_verification(
    request: MonitorInboxRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """Monitor inbox for verification codes"""
    try:
        start_time = datetime.now()
        
        verification_code = await email_manager.monitor_inbox_for_verification_codes(
            email=str(request.email),
            timeout=request.timeout_seconds
        )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Track event
        if verification_code:
            event = EmailEvent(
                id=str(uuid.uuid4()),
                event_type=EventType.VERIFICATION_CODE_EXTRACTED,
                timestamp=datetime.now(),
                email_address=str(request.email),
                provider="inbox_monitor",
                processing_time=processing_time,
                metadata={"code_length": len(verification_code)}
            )
        else:
            event = EmailEvent(
                id=str(uuid.uuid4()),
                event_type=EventType.EMAIL_RECEIVED,
                timestamp=datetime.now(),
                email_address=str(request.email),
                provider="inbox_monitor",
                processing_time=processing_time,
                error_message="No verification code found"
            )
        
        analytics.track_event(event)
        
        return InboxMonitorResponse(
            success=bool(verification_code),
            verification_code=verification_code,
            messages_found=1 if verification_code else 0,
            time_taken=processing_time,
            error_message=None if verification_code else "No verification code found within timeout"
        )
        
    except Exception as e:
        logger.error(f"Failed to monitor inbox: {e}")
        return InboxMonitorResponse(
            success=False,
            error_message=str(e),
            time_taken=(datetime.now() - start_time).total_seconds()
        )

@app.get("/inbox/{email}/messages")
async def get_inbox_messages(
    email: str,
    limit: int = 50,
    api_key: str = Depends(verify_api_key)
):
    """Get inbox messages for email account"""
    try:
        messages = await email_manager.get_inbox_messages(email, limit)
        
        return {
            "email": email,
            "messages": [
                {
                    "id": msg.id,
                    "from_address": msg.from_address,
                    "subject": msg.subject,
                    "body_preview": msg.body_text[:200],
                    "received_at": msg.received_at.isoformat(),
                    "verification_codes": msg.verification_codes,
                    "is_read": msg.is_read
                }
                for msg in messages
            ],
            "total": len(messages)
        }
        
    except Exception as e:
        logger.error(f"Failed to get inbox messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Credentials management endpoints
@app.post("/credentials")
async def store_credential(
    request: StoreCredentialRequest,
    api_key: str = Depends(verify_api_key)
):
    """Store email credential securely"""
    try:
        credential_id = credentials_manager.store_credential(
            email_address=str(request.email_address),
            provider=request.provider,
            credential_type=request.credential_type,
            value=request.value,
            expires_at=request.expires_at,
            metadata=request.metadata
        )
        
        return {
            "credential_id": credential_id,
            "message": "Credential stored securely"
        }
        
    except Exception as e:
        logger.error(f"Failed to store credential: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/credentials")
async def list_credentials(
    email_address: Optional[str] = None,
    provider: Optional[str] = None,
    api_key: str = Depends(verify_api_key)
):
    """List stored credentials (without values)"""
    try:
        credentials = credentials_manager.list_credentials(
            email_address=email_address,
            provider=provider
        )
        
        return {
            "credentials": credentials,
            "total": len(credentials)
        }
        
    except Exception as e:
        logger.error(f"Failed to list credentials: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/credentials/{credential_id}")
async def delete_credential(
    credential_id: str,
    reason: str = "User requested",
    api_key: str = Depends(verify_api_key)
):
    """Delete credential securely"""
    try:
        if not credentials_manager.delete_credential(credential_id, reason):
            raise HTTPException(status_code=404, detail="Credential not found")
        
        return {"message": "Credential deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete credential: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Analytics endpoints
@app.get("/analytics/report", response_model=AnalyticsResponse)
async def get_analytics_report(
    hours: int = 24,
    api_key: str = Depends(verify_api_key)
):
    """Get analytics report for specified time period"""
    try:
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        metrics = analytics.get_performance_metrics(start_time, end_time)
        
        return AnalyticsResponse(
            period_start=metrics.period_start,
            period_end=metrics.period_end,
            emails_sent=metrics.total_emails_sent,
            emails_received=metrics.total_emails_received,
            delivery_rate=metrics.delivery_rate,
            bounce_rate=metrics.bounce_rate,
            avg_processing_time=metrics.avg_processing_time,
            provider_performance=metrics.provider_performance,
            recommendations=analytics._generate_recommendations(metrics)
        )
        
    except Exception as e:
        logger.error(f"Failed to get analytics report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/realtime")
async def get_realtime_metrics(api_key: str = Depends(verify_api_key)):
    """Get real-time performance metrics"""
    try:
        metrics = analytics.get_realtime_metrics()
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to get real-time metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    try:
        from fastapi.responses import PlainTextResponse
        metrics_data = analytics.export_metrics_for_grafana()
        return PlainTextResponse(content=metrics_data, media_type="text/plain")
    except Exception as e:
        logger.error(f"Failed to export metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Background tasks
async def cleanup_task():
    """Background cleanup task"""
    while True:
        try:
            # Cleanup expired credentials
            expired = credentials_manager.cleanup_expired_credentials()
            if expired > 0:
                logger.info(f"Cleaned up {expired} expired credentials")
            
            # Cleanup old analytics data (90 days)
            analytics.cleanup_old_data(90)
            
            # Sleep for 1 hour
            await asyncio.sleep(3600)
            
        except Exception as e:
            logger.error(f"Cleanup task error: {e}")
            await asyncio.sleep(300)  # Retry in 5 minutes

async def analytics_aggregation_task():
    """Background analytics aggregation task"""
    while True:
        try:
            # Generate hourly reports
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=1)
            
            report = analytics.generate_report(start_time, end_time, "hourly")
            
            if report:
                logger.debug("Generated hourly analytics report")
            
            # Sleep for 1 hour
            await asyncio.sleep(3600)
            
        except Exception as e:
            logger.error(f"Analytics aggregation task error: {e}")
            await asyncio.sleep(300)  # Retry in 5 minutes

if __name__ == "__main__":
    # Run the service
    uvicorn.run(
        "business_email_api:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8005)),
        log_level="info",
        reload=False
    )