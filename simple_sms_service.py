#!/usr/bin/env python3
"""
Simple SMS Service Launcher
"""

import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SMS Verification Service", version="1.0.0")

class SMSRequest(BaseModel):
    phone_number: str
    message: str
    country: str = "US"

class SMSResponse(BaseModel):
    success: bool
    message_id: str
    status: str

class VerificationRequest(BaseModel):
    phone_number: str = None  # Optional - will generate if not provided
    service: str = "snapchat"

# Mock SMS database
sms_database = {}
verification_codes = {}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "sms-verification"}

@app.post("/api/v1/sms/send")
async def send_sms(request: SMSRequest):
    """Send SMS message"""
    try:
        # Mock SMS sending
        message_id = f"msg_{hash(request.phone_number)}_{len(sms_database)}"
        
        sms_database[message_id] = {
            "phone_number": request.phone_number,
            "message": request.message,
            "status": "sent",
            "timestamp": "2025-09-14T06:45:00Z"
        }
        
        logger.info(f"SMS sent to {request.phone_number}: {request.message}")
        
        return SMSResponse(
            success=True,
            message_id=message_id,
            status="sent"
        )
    except Exception as e:
        logger.error(f"SMS sending failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/sms/verify")
async def request_verification(request: VerificationRequest):
    """Request SMS verification code"""
    try:
        import random
        
        # Generate random phone number if not provided or use provided one
        if not request.phone_number:
            # Generate random US phone numbers
            area_codes = [555, 617, 718, 212, 213, 310, 415, 646, 202, 404, 312, 702]
            phone_number = f"+1{random.choice(area_codes)}{random.randint(1000000, 9999999)}"
        else:
            phone_number = request.phone_number
            
        # Generate realistic verification code
        verification_code = f"{random.randint(100000, 999999)}"
        verification_codes[phone_number] = verification_code
        
        # Mock sending verification SMS
        sms_message = f"Your {request.service} verification code is: {verification_code}"
        
        message_id = f"verify_{random.randint(100000, 999999)}_{len(verification_codes)}"
        
        logger.info(f"Verification code sent to {phone_number}: {verification_code}")
        
        return {
            "success": True,
            "message_id": message_id,
            "phone_number": phone_number,
            "service": request.service,
            "verification_code": verification_code,
            "status": "verification_sent"
        }
    except Exception as e:
        logger.error(f"Verification request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/sms/verify/{phone_number}")
async def get_verification_code(phone_number: str):
    """Get verification code for phone number"""
    try:
        if phone_number in verification_codes:
            code = verification_codes[phone_number]
            return {
                "success": True,
                "phone_number": phone_number,
                "verification_code": code,
                "status": "code_available"
            }
        else:
            return {
                "success": False,
                "phone_number": phone_number,
                "status": "no_code_found"
            }
    except Exception as e:
        logger.error(f"Verification retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/phone-pool/status")
async def phone_pool_status():
    """Get phone number pool status"""
    return {
        "total_numbers": 25,
        "available": 18,
        "in_use": 7,
        "cooldown": 0,
        "status": "operational"
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return {
        "sms_sent_total": len(sms_database),
        "verifications_requested": len(verification_codes),
        "phone_pool_size": 25,
        "service_uptime_seconds": 3600
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8002))
    logger.info(f"🚀 Starting SMS Verification Service on port {port}")
    logger.info("📱 Endpoints available:")
    logger.info("  - POST /api/v1/sms/send - Send SMS messages")
    logger.info("  - POST /api/v1/sms/verify - Request verification codes")
    logger.info("  - GET /api/v1/sms/verify/{phone} - Get verification code")
    logger.info("  - GET /api/v1/phone-pool/status - Phone pool status")
    logger.info("  - GET /health - Health check")
    logger.info("  - GET /metrics - Service metrics")
    
    uvicorn.run(app, host="0.0.0.0", port=port)