#!/usr/bin/env python3
"""
API Endpoints for Account Export System
Provides REST API for external systems to access account data
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Depends, Query, Header, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_404_NOT_FOUND
import io
import zipfile
import tempfile
import os
from pathlib import Path

from .account_export_system import (
    ExportableAccount, AccountExportSystem, ExportFormat, SecurityLevel, quick_export_accounts
)
from .database_integration import DatabaseManager, create_sqlite_database
from .bot_integration_interface import IntegrationManager, create_telegram_integration, create_discord_integration

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

# Pydantic models for API
class AccountRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    phone_number: Optional[str] = Field(None, max_length=20)
    birth_date: str = Field(..., regex=r'^\d{4}-\d{2}-\d{2}$')
    password: str = Field(..., min_length=8, max_length=255)
    first_name: str = Field(..., min_length=1, max_length=255)
    last_name: str = Field(..., min_length=1, max_length=255)
    bio: Optional[str] = Field(None, max_length=500)
    status: str = Field(default="ACTIVE")
    verification_status: str = Field(default="UNVERIFIED")
    trust_score: int = Field(default=0, ge=0, le=100)

class ExportRequest(BaseModel):
    format: str = Field(..., regex=r'^(txt|json|csv|xml|telegram_bot|discord_bot)$')
    security_level: str = Field(default="sanitized", regex=r'^(full|sanitized|minimal)$')
    filters: Optional[Dict[str, Any]] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)

class BulkAccountRequest(BaseModel):
    accounts: List[AccountRequest]
    export_format: str = Field(default="json")
    security_level: str = Field(default="sanitized")
    notify_webhook: Optional[str] = None

class WebhookConfig(BaseModel):
    webhook_url: str = Field(..., regex=r'^https?://')
    bot_type: str = Field(..., regex=r'^(telegram|discord|api|websocket)$')
    security_level: str = Field(default="sanitized")
    api_key: Optional[str] = None
    secret_key: Optional[str] = None

class AccountResponse(BaseModel):
    username: str
    display_name: str
    email: str
    status: str
    verification_status: str
    trust_score: int
    export_id: str
    registration_time: str
    snapchat_user_id: Optional[str] = None

class ExportResponse(BaseModel):
    export_id: str
    format: str
    security_level: str
    total_accounts: int
    file_path: Optional[str] = None
    download_url: Optional[str] = None
    created_at: str

class APIStats(BaseModel):
    total_accounts: int
    active_accounts: int
    verified_accounts: int
    avg_trust_score: float
    recent_exports: int
    api_version: str = "1.0"

# Initialize FastAPI app
app = FastAPI(
    title="Account Export API",
    description="REST API for account data export and bot integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
export_system = AccountExportSystem()
db_manager = DatabaseManager()
integration_manager = IntegrationManager()

# Initialize SQLite database for API
sqlite_db = create_sqlite_database("api_accounts.db")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Simple authentication - replace with proper auth in production"""
    # For demo purposes, accept any bearer token
    # In production, validate JWT tokens or API keys
    if not credentials.token:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    return credentials.token

@app.on_event("startup")
async def startup_event():
    """Initialize database and integrations on startup"""
    try:
        await sqlite_db.initialize_database()
        db_manager.add_sqlite_integration("main", "api_accounts.db")
        await db_manager.initialize_all()
        logger.info("API startup completed successfully")
    except Exception as e:
        logger.error(f"API startup failed: {e}")
        raise

# Account management endpoints
@app.post("/api/v1/accounts", response_model=AccountResponse, status_code=HTTP_201_CREATED)
async def create_account(
    account: AccountRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user)
):
    """Create a new account and export it"""
    try:
        # Convert to ExportableAccount
        exportable_account = ExportableAccount(
            username=account.username,
            display_name=account.display_name,
            email=account.email,
            phone_number=account.phone_number,
            birth_date=account.birth_date,
            password=account.password,
            first_name=account.first_name,
            last_name=account.last_name,
            bio=account.bio,
            status=account.status,
            verification_status=account.verification_status,
            trust_score=account.trust_score
        )
        
        # Store in database
        success = await sqlite_db.insert_account(exportable_account)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to create account")
        
        # Add background task to notify integrations
        background_tasks.add_task(notify_integrations, exportable_account)
        
        # Return response
        return AccountResponse(
            username=exportable_account.username,
            display_name=exportable_account.display_name,
            email=exportable_account.email,
            status=exportable_account.status,
            verification_status=exportable_account.verification_status,
            trust_score=exportable_account.trust_score,
            export_id=exportable_account.export_id,
            registration_time=exportable_account.registration_time,
            snapchat_user_id=exportable_account.snapchat_user_id
        )
        
    except Exception as e:
        logger.error(f"Account creation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/accounts/bulk", response_model=Dict[str, Any])
async def create_accounts_bulk(
    request: BulkAccountRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user)
):
    """Create multiple accounts in bulk"""
    try:
        exportable_accounts = []
        for account_data in request.accounts:
            exportable_account = ExportableAccount(
                username=account_data.username,
                display_name=account_data.display_name,
                email=account_data.email,
                phone_number=account_data.phone_number,
                birth_date=account_data.birth_date,
                password=account_data.password,
                first_name=account_data.first_name,
                last_name=account_data.last_name,
                bio=account_data.bio,
                status=account_data.status,
                verification_status=account_data.verification_status,
                trust_score=account_data.trust_score
            )
            exportable_accounts.append(exportable_account)
        
        # Store in database
        db_result = await sqlite_db.insert_accounts_batch(exportable_accounts)
        
        # Export accounts
        export_file = quick_export_accounts(
            [asdict(acc) for acc in exportable_accounts],
            ExportFormat(request.export_format),
            SecurityLevel(request.security_level)
        )
        
        # Add background task for webhook notification
        if request.notify_webhook:
            background_tasks.add_task(send_webhook_notification, request.notify_webhook, exportable_accounts)
        
        return {
            "total_requested": len(request.accounts),
            "successful": db_result["successful"],
            "failed": db_result["failed"],
            "export_file": export_file,
            "export_format": request.export_format,
            "security_level": request.security_level,
            "webhook_notified": bool(request.notify_webhook)
        }
        
    except Exception as e:
        logger.error(f"Bulk account creation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/accounts", response_model=List[AccountResponse])
async def get_accounts(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = Query(default=None),
    verification_status: Optional[str] = Query(default=None),
    min_trust_score: Optional[int] = Query(default=None, ge=0, le=100),
    current_user: str = Depends(get_current_user)
):
    """Get list of accounts with optional filtering"""
    try:
        filters = {}
        if status:
            filters["status"] = status
        if verification_status:
            filters["verification_status"] = verification_status
        if min_trust_score is not None:
            filters["trust_score_min"] = min_trust_score
        
        accounts = await sqlite_db.get_accounts(
            limit=limit,
            offset=offset,
            filters=filters if filters else None
        )
        
        return [
            AccountResponse(
                username=acc.username,
                display_name=acc.display_name,
                email=acc.email,
                status=acc.status,
                verification_status=acc.verification_status,
                trust_score=acc.trust_score,
                export_id=acc.export_id,
                registration_time=acc.registration_time,
                snapchat_user_id=acc.snapchat_user_id
            )
            for acc in accounts
        ]
        
    except Exception as e:
        logger.error(f"Get accounts failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/accounts/{username}", response_model=AccountResponse)
async def get_account(
    username: str,
    current_user: str = Depends(get_current_user)
):
    """Get specific account by username"""
    try:
        account = await sqlite_db.get_account_by_username(username)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        return AccountResponse(
            username=account.username,
            display_name=account.display_name,
            email=account.email,
            status=account.status,
            verification_status=account.verification_status,
            trust_score=account.trust_score,
            export_id=account.export_id,
            registration_time=account.registration_time,
            snapchat_user_id=account.snapchat_user_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get account failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/v1/accounts/{username}/status")
async def update_account_status(
    username: str,
    status: str = Query(..., regex=r'^(ACTIVE|INACTIVE|SUSPENDED|BANNED)$'),
    verification_status: Optional[str] = Query(default=None, regex=r'^(UNVERIFIED|PENDING|VERIFIED|FAILED)$'),
    current_user: str = Depends(get_current_user)
):
    """Update account status"""
    try:
        success = await sqlite_db.update_account_status(username, status, verification_status)
        if not success:
            raise HTTPException(status_code=404, detail="Account not found")
        
        return {"message": "Account status updated successfully", "username": username, "status": status}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update account status failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# Export endpoints
@app.post("/api/v1/export", response_model=ExportResponse)
async def export_accounts(
    request: ExportRequest,
    current_user: str = Depends(get_current_user)
):
    """Export accounts in specified format"""
    try:
        # Get accounts from database
        accounts = await sqlite_db.get_accounts(
            limit=request.limit,
            offset=request.offset,
            filters=request.filters
        )
        
        if not accounts:
            raise HTTPException(status_code=404, detail="No accounts found")
        
        # Export accounts
        if request.format == "txt":
            file_path = export_system.export_to_txt(accounts, SecurityLevel(request.security_level))
        elif request.format == "json":
            file_path = export_system.export_to_json(accounts, SecurityLevel(request.security_level))
        elif request.format == "csv":
            file_path = export_system.export_to_csv(accounts, SecurityLevel(request.security_level))
        elif request.format == "xml":
            file_path = export_system.export_to_xml(accounts, SecurityLevel(request.security_level))
        elif request.format == "telegram_bot":
            telegram_data = export_system.export_for_telegram_bot(accounts)
            file_path = export_system.output_dir / f"telegram_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(file_path, 'w') as f:
                json.dump(telegram_data, f, indent=2)
            file_path = str(file_path)
        else:
            raise HTTPException(status_code=400, detail="Unsupported export format")
        
        export_id = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        return ExportResponse(
            export_id=export_id,
            format=request.format,
            security_level=request.security_level,
            total_accounts=len(accounts),
            file_path=file_path,
            download_url=f"/api/v1/exports/{export_id}/download",
            created_at=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/exports/{export_id}/download")
async def download_export(
    export_id: str,
    current_user: str = Depends(get_current_user)
):
    """Download exported file"""
    try:
        # In production, you'd store export metadata and validate export_id
        # For now, find the most recent export file
        export_dir = Path("exports")
        if not export_dir.exists():
            raise HTTPException(status_code=404, detail="Export not found")
        
        # Find matching export file (simplified logic)
        export_files = list(export_dir.glob("*export*.json"))
        export_files.extend(list(export_dir.glob("*export*.txt")))
        export_files.extend(list(export_dir.glob("*export*.csv")))
        export_files.extend(list(export_dir.glob("*export*.xml")))
        export_files.extend(list(export_dir.glob("*export*.zip")))
        
        if not export_files:
            raise HTTPException(status_code=404, detail="Export file not found")
        
        # Get the most recent file
        latest_file = max(export_files, key=os.path.getctime)
        
        return FileResponse(
            path=latest_file,
            filename=latest_file.name,
            media_type="application/octet-stream"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/export/bulk-bundle")
async def create_bulk_export_bundle(
    current_user: str = Depends(get_current_user)
):
    """Create comprehensive export bundle with multiple formats"""
    try:
        # Get all accounts
        accounts = await sqlite_db.get_accounts(limit=1000)
        
        if not accounts:
            raise HTTPException(status_code=404, detail="No accounts found")
        
        # Create bundle
        bundle_path = export_system.create_bulk_import_file(accounts, ExportFormat.JSON)
        
        return {
            "bundle_path": bundle_path,
            "total_accounts": len(accounts),
            "formats_included": ["json", "csv", "metadata"],
            "download_url": "/api/v1/exports/latest-bundle/download",
            "created_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Bulk bundle creation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# Integration management endpoints
@app.post("/api/v1/integrations/{integration_name}")
async def add_integration(
    integration_name: str,
    config: WebhookConfig,
    current_user: str = Depends(get_current_user)
):
    """Add bot integration"""
    try:
        if config.bot_type == "telegram":
            integration = create_telegram_integration(
                config.webhook_url, 
                config.security_level
            )
        elif config.bot_type == "discord":
            integration = create_discord_integration(
                config.webhook_url,
                config.security_level
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported bot type")
        
        integration_manager.add_integration(integration_name, integration)
        
        return {
            "message": f"Integration '{integration_name}' added successfully",
            "bot_type": config.bot_type,
            "security_level": config.security_level
        }
        
    except Exception as e:
        logger.error(f"Add integration failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/v1/integrations/{integration_name}")
async def remove_integration(
    integration_name: str,
    current_user: str = Depends(get_current_user)
):
    """Remove bot integration"""
    try:
        integration_manager.remove_integration(integration_name)
        return {"message": f"Integration '{integration_name}' removed successfully"}
        
    except Exception as e:
        logger.error(f"Remove integration failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/integrations/test/{integration_name}")
async def test_integration(
    integration_name: str,
    current_user: str = Depends(get_current_user)
):
    """Test integration with sample account"""
    try:
        if integration_name not in integration_manager.integrations:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        # Create test account
        test_account = ExportableAccount(
            username="test_integration",
            display_name="Test Integration",
            email="test@integration.com",
            phone_number="+1234567890",
            birth_date="1995-01-01",
            password="TestPass123!",
            first_name="Test",
            last_name="Integration",
            status="ACTIVE",
            verification_status="VERIFIED",
            trust_score=100
        )
        
        # Test delivery
        integration = integration_manager.integrations[integration_name]
        success = await integration.deliver_account(test_account)
        
        return {
            "integration_name": integration_name,
            "test_successful": success,
            "test_account": test_account.username,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Test integration failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# Statistics endpoints
@app.get("/api/v1/stats", response_model=APIStats)
async def get_statistics(current_user: str = Depends(get_current_user)):
    """Get API and database statistics"""
    try:
        db_stats = await sqlite_db.get_statistics()
        
        return APIStats(
            total_accounts=db_stats["total_accounts"],
            active_accounts=db_stats["active_accounts"],
            verified_accounts=db_stats["verified_accounts"],
            avg_trust_score=round(db_stats["avg_trust_score"] or 0, 2),
            recent_exports=0,  # Would be tracked separately
            api_version="1.0"
        )
        
    except Exception as e:
        logger.error(f"Get statistics failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "api_version": "1.0",
        "integrations": len(integration_manager.integrations),
        "database_connected": True  # Would check actual DB connection
    }

# Webhook endpoints
@app.post("/api/v1/webhook/account-created")
async def account_created_webhook(
    account_data: AccountRequest,
    x_signature: Optional[str] = Header(None),
    current_user: str = Depends(get_current_user)
):
    """Webhook endpoint for external systems to notify of new accounts"""
    try:
        # Convert to exportable account
        exportable_account = ExportableAccount(
            username=account_data.username,
            display_name=account_data.display_name,
            email=account_data.email,
            phone_number=account_data.phone_number,
            birth_date=account_data.birth_date,
            password=account_data.password,
            first_name=account_data.first_name,
            last_name=account_data.last_name,
            bio=account_data.bio,
            status=account_data.status,
            verification_status=account_data.verification_status,
            trust_score=account_data.trust_score
        )
        
        # Store in database
        await sqlite_db.insert_account(exportable_account)
        
        # Notify all integrations
        results = await integration_manager.deliver_to_all(exportable_account)
        
        return {
            "message": "Account processed successfully",
            "username": exportable_account.username,
            "integrations_notified": len(results),
            "notification_results": results
        }
        
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# Background tasks
async def notify_integrations(account: ExportableAccount):
    """Background task to notify all integrations"""
    try:
        results = await integration_manager.deliver_to_all(account)
        logger.info(f"Notified integrations for {account.username}: {results}")
    except Exception as e:
        logger.error(f"Integration notification failed: {e}")

async def send_webhook_notification(webhook_url: str, accounts: List[ExportableAccount]):
    """Background task to send webhook notification"""
    try:
        import aiohttp
        
        payload = {
            "event": "bulk_accounts_created",
            "timestamp": datetime.now().isoformat(),
            "total_accounts": len(accounts),
            "accounts": [
                {
                    "username": acc.username,
                    "email": acc.email,
                    "status": acc.status,
                    "export_id": acc.export_id
                }
                for acc in accounts
            ]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as response:
                if response.status == 200:
                    logger.info(f"Webhook notification sent successfully to {webhook_url}")
                else:
                    logger.warning(f"Webhook notification failed: {response.status}")
                    
    except Exception as e:
        logger.error(f"Webhook notification failed: {e}")

# Additional utility endpoints
@app.get("/api/v1/formats")
async def get_supported_formats():
    """Get list of supported export formats"""
    return {
        "export_formats": [
            {
                "format": "json",
                "description": "JSON format for API integration",
                "mime_type": "application/json"
            },
            {
                "format": "csv",
                "description": "CSV format for spreadsheet import",
                "mime_type": "text/csv"
            },
            {
                "format": "xml",
                "description": "XML format for enterprise systems",
                "mime_type": "application/xml"
            },
            {
                "format": "txt",
                "description": "Human-readable text format",
                "mime_type": "text/plain"
            },
            {
                "format": "telegram_bot",
                "description": "Telegram bot compatible format",
                "mime_type": "application/json"
            }
        ],
        "security_levels": [
            {
                "level": "full",
                "description": "All data including passwords"
            },
            {
                "level": "sanitized",
                "description": "Passwords masked, sensitive data hashed"
            },
            {
                "level": "minimal",
                "description": "Only essential data for integration"
            }
        ]
    }

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {"detail": "Resource not found", "status_code": 404}

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return {"detail": "Internal server error", "status_code": 500}

# Run server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api_endpoints:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )