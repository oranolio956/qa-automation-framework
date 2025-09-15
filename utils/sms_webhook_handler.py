#!/usr/bin/env python3
"""
SMS Delivery Status Webhook Handler

This module provides webhook endpoints to receive SMS delivery status updates
from Twilio for enhanced tracking and reliability monitoring.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Optional
from flask import Flask, request, jsonify
from twilio.request_validator import RequestValidator
from sms_verifier import get_sms_verifier
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Flask app for webhook endpoints
app = Flask(__name__)

# Twilio request validator for webhook security
validator = RequestValidator(os.environ.get('TWILIO_AUTH_TOKEN', ''))

def validate_twilio_request(url: str, post_data: Dict, signature: str) -> bool:
    """Validate that the request came from Twilio"""
    try:
        return validator.validate(url, post_data, signature)
    except Exception as e:
        logger.error(f"Error validating Twilio request: {e}")
        return False

@app.route('/webhook/sms/delivery', methods=['POST'])
def sms_delivery_webhook():
    """Handle SMS delivery status updates from Twilio"""
    try:
        # Validate the request comes from Twilio
        signature = request.headers.get('X-Twilio-Signature', '')
        url = request.url
        post_data = request.form.to_dict()
        
        # Skip validation in development/testing
        skip_validation = os.environ.get('SKIP_TWILIO_VALIDATION', '').lower() == 'true'
        
        if not skip_validation and not validate_twilio_request(url, post_data, signature):
            logger.warning(f"Invalid Twilio signature for delivery webhook")
            return jsonify({'error': 'Invalid request signature'}), 403
        
        # Extract delivery data from Twilio webhook
        message_sid = post_data.get('MessageSid', '')
        message_status = post_data.get('MessageStatus', '')
        error_code = post_data.get('ErrorCode')
        error_message = post_data.get('ErrorMessage', '')
        
        # Additional Twilio delivery data
        delivery_data = {
            'message_sid': message_sid,
            'status': message_status,
            'error_code': error_code,
            'error_message': error_message,
            'account_sid': post_data.get('AccountSid', ''),
            'from': post_data.get('From', ''),
            'to': post_data.get('To', ''),
            'date_sent': post_data.get('DateSent', ''),
            'date_updated': post_data.get('DateUpdated', ''),
            'webhook_received_at': datetime.now().isoformat()
        }
        
        logger.info(f"Received SMS delivery webhook: {message_sid} -> {message_status}")
        
        # Update delivery status in SMS verifier (async-safe)
        verifier = get_sms_verifier()
        
        # Since Flask route is sync, we need to run async operation in thread
        import asyncio
        import threading
        
        def update_status():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    verifier.update_delivery_status(message_sid, message_status, error_code)
                )
            finally:
                loop.close()
        
        # Run in background thread to avoid blocking webhook response
        thread = threading.Thread(target=update_status, daemon=True)
        thread.start()
        
        # Log delivery status for monitoring
        if message_status == 'delivered':
            logger.info(f"✅ SMS delivered successfully: {message_sid}")
        elif message_status == 'failed':
            logger.error(f"❌ SMS delivery failed: {message_sid}, Error: {error_code} - {error_message}")
        elif message_status == 'undelivered':
            logger.warning(f"⚠️ SMS undelivered: {message_sid}, Error: {error_code} - {error_message}")
        else:
            logger.info(f"📱 SMS status update: {message_sid} -> {message_status}")
        
        # Store full delivery data in Redis for detailed tracking (async-safe)
        def store_delivery_data():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                async def async_store():
                    await verifier._ensure_redis_connection()
                    await verifier.redis_client.setex(
                        f"delivery_detail:{message_sid}",
                        86400 * 7,  # Keep for 7 days
                        json.dumps(delivery_data)
                    )
                loop.run_until_complete(async_store())
            except Exception as e:
                logger.warning(f"Failed to store detailed delivery data: {e}")
            finally:
                loop.close()
        
        # Run in background thread
        thread = threading.Thread(target=store_delivery_data, daemon=True)
        thread.start()
        
        return jsonify({
            'status': 'received',
            'message_sid': message_sid,
            'processed_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error processing SMS delivery webhook: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/webhook/sms/status', methods=['GET'])
def sms_webhook_status():
    """Health check endpoint for webhook service"""
    return jsonify({
        'service': 'SMS Webhook Handler',
        'status': 'active',
        'timestamp': datetime.now().isoformat(),
        'endpoints': [
            '/webhook/sms/delivery (POST) - Twilio delivery status updates'
        ]
    })

@app.route('/api/sms/delivery-stats', methods=['GET'])
def get_delivery_stats():
    """Get SMS delivery statistics"""
    try:
        verifier = get_sms_verifier()
        
        # Get delivery status keys from Redis (async-safe)
        import asyncio
        
        def get_stats():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                async def async_get_stats():
                    await verifier._ensure_redis_connection()
                    return await verifier.redis_client.keys("sms_delivery:*")
                return loop.run_until_complete(async_get_stats())
            finally:
                loop.close()
        
        delivery_keys = get_stats()
        
        stats = {
            'total_tracked': len(delivery_keys),
            'by_status': {},
            'recent_failures': []
        }
        
        # Count by status (async-safe)
        def process_keys():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                async def async_process():
                    await verifier._ensure_redis_connection()
                    for key in delivery_keys:
                        try:
                            delivery_data_str = await verifier.redis_client.get(key)
                            delivery_data = json.loads(delivery_data_str or '{}')
                            status = delivery_data.get('status', 'unknown')
                            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
                            
                            # Collect recent failures
                            if status in ['failed', 'undelivered'] and len(stats['recent_failures']) < 10:
                                stats['recent_failures'].append({
                                    'message_id': delivery_data.get('message_id'),
                                    'phone_number': delivery_data.get('phone_number', 'unknown'),
                                    'status': status,
                                    'sent_at': delivery_data.get('sent_at')
                                })
                        except:
                            continue
                loop.run_until_complete(async_process())
            finally:
                loop.close()
        
        process_keys()
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting delivery stats: {e}")
        return jsonify({'error': str(e)}), 500

def create_webhook_app():
    """Create and configure the webhook Flask app"""
    # Configure app
    app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-key-change-in-production')
    
    # Add security headers
    @app.after_request
    def after_request(response):
        response.headers.add('X-Content-Type-Options', 'nosniff')
        response.headers.add('X-Frame-Options', 'DENY')
        response.headers.add('X-XSS-Protection', '1; mode=block')
        return response
    
    return app

if __name__ == '__main__':
    """Run the webhook server for development/testing"""
    import sys
    
    print("=" * 60)
    print("SMS DELIVERY WEBHOOK SERVER")
    print("=" * 60)
    
    # Check required environment variables
    required_vars = ['TWILIO_AUTH_TOKEN']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print("⚠️  Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nSet SKIP_TWILIO_VALIDATION=true for testing without credentials")
    
    # Get configuration
    host = os.environ.get('WEBHOOK_HOST', '0.0.0.0')
    port = int(os.environ.get('WEBHOOK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '').lower() == 'true'
    
    print(f"Starting webhook server on {host}:{port}")
    print(f"Webhook URL: http://{host}:{port}/webhook/sms/delivery")
    print(f"Status URL: http://{host}:{port}/webhook/sms/status")
    print(f"Stats URL: http://{host}:{port}/api/sms/delivery-stats")
    
    if debug:
        print("⚠️  Running in DEBUG mode")
    
    try:
        app = create_webhook_app()
        app.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        print("\n👋 Webhook server stopped")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Failed to start webhook server: {e}")
        sys.exit(1)