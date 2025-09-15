#!/usr/bin/env python3
"""
Simple Email Automation Service
"""

import os
import logging
import random
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Email Automation Service", version="1.0.0")

class EmailCreationRequest(BaseModel):
    provider: str = "tempmail"
    domain: str = "gmail.com"
    use_for: str = "snapchat"

class EmailCreationResponse(BaseModel):
    success: bool
    email: str
    provider: str
    expiry_minutes: int
    status: str

class EmailVerificationRequest(BaseModel):
    email: str
    service: str = "snapchat"

# Mock email database
email_database = {}
inbox_messages = {}

# Email domains for rotation
EMAIL_DOMAINS = [
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "icloud.com", "protonmail.com", "aol.com", "zoho.com"
]

# Temporary email providers
TEMP_EMAIL_PROVIDERS = {
    "tempmail": {"expiry": 10, "status": "active"},
    "guerrilla": {"expiry": 60, "status": "active"},
    "10minutemail": {"expiry": 10, "status": "active"},
    "rapidapi": {"expiry": 30, "status": "active"}
}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "email-automation"}

@app.post("/api/v1/email/create")
async def create_email(request: EmailCreationRequest):
    """Create temporary email account"""
    try:
        # Generate realistic female names and email addresses
        female_names = [
            "emma", "olivia", "sophia", "charlotte", "amelia", "harper", "evelyn", "abigail", 
            "emily", "elizabeth", "sofia", "avery", "ella", "scarlett", "grace", "chloe",
            "victoria", "riley", "aria", "lily", "aubrey", "zoey", "penelope", "lillian",
            "addison", "layla", "natalie", "camila", "hannah", "brooklyn", "zoe", "nora",
            "madison", "maya", "alice", "anna", "jasmine", "ruby", "sarah", "luna"
        ]
        
        # Create realistic username variations
        first_name = random.choice(female_names)
        variations = [
            f"{first_name}{random.randint(100, 9999)}",
            f"{first_name}.{random.randint(10, 99)}",
            f"{first_name}_{random.randint(100, 999)}",
            f"{first_name}{random.choice(['xo', 'girl', 'bae', 'cute'])}{random.randint(10, 99)}",
            f"miss_{first_name}{random.randint(10, 999)}"
        ]
        username = random.choice(variations)
        
        if request.provider in TEMP_EMAIL_PROVIDERS:
            domain = f"{request.provider}.com"
        else:
            domain = random.choice(EMAIL_DOMAINS)
        
        email_address = f"{username}@{domain}"
        
        provider_info = TEMP_EMAIL_PROVIDERS.get(request.provider, {"expiry": 10, "status": "active"})
        
        # Store email in database
        email_database[email_address] = {
            "provider": request.provider,
            "domain": domain,
            "use_for": request.use_for,
            "created_at": "2025-09-14T06:45:00Z",
            "expiry_minutes": provider_info["expiry"],
            "status": "active"
        }
        
        # Initialize empty inbox
        inbox_messages[email_address] = []
        
        logger.info(f"Email created: {email_address} via {request.provider}")
        
        return EmailCreationResponse(
            success=True,
            email=email_address,
            provider=request.provider,
            expiry_minutes=provider_info["expiry"],
            status="created"
        )
    except Exception as e:
        logger.error(f"Email creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/email/{email}/inbox")
async def check_inbox(email: str):
    """Check inbox for verification emails"""
    try:
        if email not in inbox_messages:
            return {"success": False, "email": email, "messages": []}
        
        messages = inbox_messages[email]
        
        # Mock some verification messages for demo
        if not messages and email in email_database:
            use_for = email_database[email].get("use_for", "generic")
            
            if use_for == "snapchat":
                verification_code = f"{random.randint(100000, 999999)}"
                messages.append({
                    "id": f"msg_{len(messages) + 1}",
                    "from": "noreply@snapchat.com",
                    "subject": "Snapchat Verification Code",
                    "body": f"Your Snapchat verification code is: {verification_code}",
                    "verification_code": verification_code,
                    "received_at": "2025-09-14T06:46:00Z"
                })
                inbox_messages[email] = messages
                
        return {
            "success": True,
            "email": email,
            "message_count": len(messages),
            "messages": messages
        }
    except Exception as e:
        logger.error(f"Inbox check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/email/verify")
async def request_email_verification(request: EmailVerificationRequest):
    """Request email verification (simulates service sending verification email)"""
    try:
        if request.email not in inbox_messages:
            inbox_messages[request.email] = []
        
        verification_code = f"{random.randint(100000, 999999)}"
        
        # Mock verification email
        verification_email = {
            "id": f"msg_{len(inbox_messages[request.email]) + 1}",
            "from": f"noreply@{request.service}.com",
            "subject": f"{request.service.title()} Verification Code",
            "body": f"Your {request.service} verification code is: {verification_code}",
            "verification_code": verification_code,
            "received_at": "2025-09-14T06:46:30Z"
        }
        
        inbox_messages[request.email].append(verification_email)
        
        logger.info(f"Verification email sent to {request.email} for {request.service}")
        
        return {
            "success": True,
            "email": request.email,
            "service": request.service,
            "verification_code": verification_code,
            "status": "verification_sent"
        }
    except Exception as e:
        logger.error(f"Email verification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/email/pool/status")
async def email_pool_status():
    """Get email pool management status"""
    active_emails = len([e for e in email_database.values() if e["status"] == "active"])
    
    return {
        "total_emails": len(email_database),
        "active": active_emails,
        "expired": len(email_database) - active_emails,
        "providers": list(TEMP_EMAIL_PROVIDERS.keys()),
        "domains_available": len(EMAIL_DOMAINS),
        "status": "operational"
    }

@app.get("/api/v1/captcha/solve")
async def solve_captcha(captcha_type: str = "recaptcha", difficulty: str = "easy"):
    """Mock CAPTCHA solving service"""
    try:
        # Simulate CAPTCHA solving
        solving_times = {"easy": 15, "medium": 30, "hard": 60}
        solve_time = solving_times.get(difficulty, 30)
        
        solution_token = f"captcha_solution_{random.randint(100000, 999999)}"
        
        logger.info(f"CAPTCHA solved: {captcha_type} ({difficulty}) in {solve_time}s")
        
        return {
            "success": True,
            "captcha_type": captcha_type,
            "difficulty": difficulty,
            "solution_token": solution_token,
            "solve_time_seconds": solve_time,
            "status": "solved"
        }
    except Exception as e:
        logger.error(f"CAPTCHA solving failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return {
        "emails_created_total": len(email_database),
        "active_emails": len([e for e in email_database.values() if e["status"] == "active"]),
        "messages_received": sum(len(msgs) for msgs in inbox_messages.values()),
        "captchas_solved": 42,
        "service_uptime_seconds": 3600
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8003))
    logger.info(f"🚀 Starting Email Automation Service on port {port}")
    logger.info("📧 Endpoints available:")
    logger.info("  - POST /api/v1/email/create - Create temporary email")
    logger.info("  - GET /api/v1/email/{email}/inbox - Check inbox")
    logger.info("  - POST /api/v1/email/verify - Request verification email")
    logger.info("  - GET /api/v1/email/pool/status - Email pool status")
    logger.info("  - GET /api/v1/captcha/solve - CAPTCHA solving")
    logger.info("  - GET /health - Health check")
    logger.info("  - GET /metrics - Service metrics")
    
    uvicorn.run(app, host="0.0.0.0", port=port)