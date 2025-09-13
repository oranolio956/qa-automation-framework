#!/usr/bin/env python3
"""
Order and Billing Pipeline Backend Service
Handles order creation, payment processing, and billing management
"""

from flask import Flask, request, abort, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import jwt
import os
import redis
import time
import requests
import json
import uuid
import logging
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from schemas import (
    OrderRequest, OrderResponse, PaymentWebhook, OrderUpdate, 
    OrderStatus, PaymentStatus, calculate_order_total
)
from typing import Optional, Dict, Any

# Import Bright Data proxy utilities
try:
    from utils.brightdata_proxy import get_brightdata_session, verify_proxy, get_proxy_info
except ImportError:
    # Fallback if Bright Data proxy utils not available
    def get_brightdata_session():
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
    default_limits=[f"{os.environ.get('API_RATE_LIMIT', '200')} per minute"]
)

# Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-jwt-secret-change-me')
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', 'default-webhook-secret')
PAYMENT_PROVIDER_API_KEY = os.environ.get('PAYMENT_PROVIDER_API_KEY')
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')

# Redis connection
try:
    r = redis.from_url(REDIS_URL, decode_responses=True)
    r.ping()
    logger.info(f"Connected to Redis: {REDIS_URL}")
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")
    r = None

def authenticate_request():
    """Validate JWT token from request headers"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return False
    
    try:
        token = auth_header.split(' ', 1)[1]
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.InvalidTokenError as e:
        logger.warning(f"JWT validation failed: {e}")
        return False

@app.before_request
def before_request():
    """Global request validation"""
    # Skip auth for health and webhook endpoints
    if request.endpoint in ['health', 'webhook']:
        return
    
    # Authenticate request
    payload = authenticate_request()
    if not payload:
        abort(401)
    
    # Store user info in request context
    request.user_id = payload.get('user_id', 'anonymous')
    request.customer_id = payload.get('customer_id', request.user_id)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(requests.RequestException)
)
def create_payment_invoice(order_id: str, amount: float, currency: str = "USD") -> str:
    """Create payment invoice with retry logic through residential proxy"""
    logger.info(f"Creating invoice for order {order_id}: {amount} {currency}")
    
    # Mock payment provider integration (replace with actual provider)
    payment_data = {
        'amount': amount,
        'currency': currency,
        'order_id': order_id,
        'description': f'QA Testing Services - Order {order_id}',
        'success_url': f"{request.host_url}orders/{order_id}/success",
        'cancel_url': f"{request.host_url}orders/{order_id}/cancel"
    }
    
    try:
        # Example integration with payment provider through proxy
        if PAYMENT_PROVIDER_API_KEY:
            # Use proxied session for payment provider requests
            session = get_brightdata_session()
            response = session.post(
                'https://api.payment-provider.com/v1/invoices',
                json=payment_data,
                headers={
                    'Authorization': f'Bearer {PAYMENT_PROVIDER_API_KEY}',
                    'Content-Type': 'application/json'
                },
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get('hosted_invoice_url', result.get('invoice_url'))
        else:
            # Fallback to mock invoice URL
            mock_invoice_id = str(uuid.uuid4())
            return f"https://mock-payment.example.com/invoice/{mock_invoice_id}"
            
    except requests.RequestException as e:
        logger.error(f"Payment provider API failed: {e}")
        raise

@app.route('/orders', methods=['POST'])
@limiter.limit("50 per minute")
def create_order():
    """Create a new testing order"""
    try:
        # Validate request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON payload'}), 400
        
        order_request = OrderRequest(**data)
        
        # Generate order ID
        order_id = f"ORD-{int(time.time())}-{str(uuid.uuid4())[:8]}"
        
        # Calculate pricing
        total_amount = calculate_order_total(order_request.job_type, order_request.quantity)
        
        # Create order record
        order_data = {
            'order_id': order_id,
            'customer_id': request.customer_id,
            'job_type': order_request.job_type.value,
            'quantity': order_request.quantity,
            'priority': order_request.priority.value,
            'parameters': json.dumps(order_request.parameters),
            'notification_webhook': order_request.notification_webhook,
            'total_amount': total_amount,
            'currency': 'USD',
            'status': OrderStatus.PENDING.value,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(hours=24)).isoformat(),
            'metadata': json.dumps(order_request.metadata)
        }
        
        # Store in Redis
        if r:
            r.hset(f"order:{order_id}", mapping=order_data)
            r.expire(f"order:{order_id}", 86400 * 7)  # 7 days
            
            # Add to customer's orders
            r.sadd(f"customer:{request.customer_id}:orders", order_id)
        
        # Create payment invoice
        try:
            invoice_url = create_payment_invoice(order_id, total_amount)
            
            # Update order with invoice URL
            if r:
                r.hset(f"order:{order_id}", "invoice_url", invoice_url)
            
        except Exception as e:
            logger.error(f"Failed to create invoice for order {order_id}: {e}")
            invoice_url = None
        
        # Estimate completion time
        base_time_per_test = {
            'touch_test': 2,    # 2 minutes
            'network_test': 3,  # 3 minutes
            'image_test': 1,    # 1 minute
            'full_suite': 10,   # 10 minutes
            'load_test': 15     # 15 minutes
        }
        
        estimated_minutes = base_time_per_test.get(order_request.job_type.value, 5) * order_request.quantity
        estimated_completion = datetime.now() + timedelta(minutes=estimated_minutes)
        
        # Prepare response
        response_data = OrderResponse(
            order_id=order_id,
            status=OrderStatus.PENDING,
            job_type=order_request.job_type,
            quantity=order_request.quantity,
            priority=order_request.priority,
            total_amount=total_amount,
            currency='USD',
            invoice_url=invoice_url,
            estimated_completion_time=estimated_completion.isoformat(),
            created_at=datetime.now()
        )
        
        logger.info(f"Order created: {order_id} for customer {request.customer_id}")
        
        return jsonify(response_data.dict()), 201
        
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/orders/<order_id>')
@limiter.limit("100 per minute")
def get_order(order_id: str):
    """Get order details"""
    try:
        if not r:
            return jsonify({'error': 'Service temporarily unavailable'}), 503
        
        order_data = r.hgetall(f"order:{order_id}")
        if not order_data:
            return jsonify({'error': 'Order not found'}), 404
        
        # Check if customer owns this order
        if order_data.get('customer_id') != request.customer_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Parse stored JSON fields
        try:
            order_data['parameters'] = json.loads(order_data.get('parameters', '{}'))
            order_data['metadata'] = json.loads(order_data.get('metadata', '{}'))
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in order {order_id}")
        
        return jsonify(order_data)
        
    except Exception as e:
        logger.error(f"Error getting order {order_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/orders')
@limiter.limit("100 per minute")
def list_orders():
    """List customer's orders"""
    try:
        if not r:
            return jsonify({'error': 'Service temporarily unavailable'}), 503
        
        # Get pagination parameters
        limit = min(int(request.args.get('limit', 50)), 500)
        offset = int(request.args.get('offset', 0))
        status_filter = request.args.get('status')
        
        # Get customer's order IDs
        order_ids = list(r.smembers(f"customer:{request.customer_id}:orders"))
        
        # Sort by creation time (newest first)
        orders_with_time = []
        for order_id in order_ids:
            order_data = r.hgetall(f"order:{order_id}")
            if order_data:
                # Filter by status if specified
                if status_filter and order_data.get('status') != status_filter:
                    continue
                
                orders_with_time.append({
                    'order_id': order_id,
                    'created_at': order_data.get('created_at'),
                    'status': order_data.get('status'),
                    'job_type': order_data.get('job_type'),
                    'quantity': int(order_data.get('quantity', 0)),
                    'total_amount': float(order_data.get('total_amount', 0))
                })
        
        # Sort by creation time
        orders_with_time.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Apply pagination
        paginated_orders = orders_with_time[offset:offset + limit]
        
        return jsonify({
            'orders': paginated_orders,
            'total': len(orders_with_time),
            'limit': limit,
            'offset': offset,
            'has_more': offset + limit < len(orders_with_time)
        })
        
    except Exception as e:
        logger.error(f"Error listing orders for customer {request.customer_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/orders/<order_id>/cancel', methods=['POST'])
@limiter.limit("20 per minute")
def cancel_order(order_id: str):
    """Cancel a pending order"""
    try:
        if not r:
            return jsonify({'error': 'Service temporarily unavailable'}), 503
        
        order_data = r.hgetall(f"order:{order_id}")
        if not order_data:
            return jsonify({'error': 'Order not found'}), 404
        
        # Check ownership
        if order_data.get('customer_id') != request.customer_id:
            return jsonify({'error': 'Access denied'}), 403
        
        current_status = order_data.get('status')
        
        # Can only cancel pending or paid orders
        if current_status not in [OrderStatus.PENDING.value, OrderStatus.PAID.value]:
            return jsonify({
                'error': f'Cannot cancel order with status: {current_status}'
            }), 400
        
        # Update order status
        r.hset(f"order:{order_id}", mapping={
            'status': OrderStatus.CANCELLED.value,
            'cancelled_at': datetime.now().isoformat(),
            'cancelled_by': request.customer_id
        })
        
        logger.info(f"Order cancelled: {order_id} by customer {request.customer_id}")
        
        return jsonify({
            'order_id': order_id,
            'status': OrderStatus.CANCELLED.value,
            'cancelled_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error cancelling order {order_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle payment provider webhooks"""
    try:
        # Verify webhook signature
        signature = request.headers.get('X-Signature')
        if signature != WEBHOOK_SECRET:
            logger.warning(f"Invalid webhook signature: {signature}")
            abort(403)
        
        payload = request.get_json()
        if not payload:
            return jsonify({'error': 'Invalid payload'}), 400
        
        # Validate webhook data
        webhook_data = PaymentWebhook(**payload)
        order_id = webhook_data.order_id
        
        logger.info(f"Received payment webhook for order {order_id}: {webhook_data.status}")
        
        if not r:
            logger.error("Redis unavailable for webhook processing")
            return jsonify({'error': 'Service unavailable'}), 503
        
        # Get order data
        order_data = r.hgetall(f"order:{order_id}")
        if not order_data:
            logger.error(f"Order not found for webhook: {order_id}")
            return jsonify({'error': 'Order not found'}), 404
        
        # Check if payment was successful
        if webhook_data.status == PaymentStatus.COMPLETED:
            # Update order status to paid
            if not r.sismember('paid_orders', order_id):
                r.hset(f"order:{order_id}", mapping={
                    'status': OrderStatus.PAID.value,
                    'paid_at': datetime.now().isoformat(),
                    'payment_id': webhook_data.payment_id,
                    'transaction_id': webhook_data.transaction_id
                })
                
                # Add to paid orders set
                r.sadd('paid_orders', order_id)
                
                # Queue the job for processing
                job_data = {
                    'order_id': order_id,
                    'job_type': order_data.get('job_type'),
                    'quantity': int(order_data.get('quantity', 1)),
                    'priority': order_data.get('priority', 'normal'),
                    'parameters': order_data.get('parameters', '{}'),
                    'customer_id': order_data.get('customer_id'),
                    'submitted_at': datetime.now().isoformat()
                }
                
                r.rpush('test_queue', json.dumps(job_data))
                
                logger.info(f"Order {order_id} paid and queued for processing")
        
        elif webhook_data.status == PaymentStatus.FAILED:
            # Update order status
            r.hset(f"order:{order_id}", mapping={
                'status': OrderStatus.FAILED.value,
                'payment_failed_at': datetime.now().isoformat(),
                'failure_reason': 'Payment failed'
            })
            
            logger.info(f"Payment failed for order {order_id}")
        
        return ('', 204)  # No content response
        
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        return jsonify({'error': 'Webhook processing failed'}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    health_data = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'redis_connected': r is not None,
        'version': '1.0.0'
    }
    
    # Check Redis connection
    if r:
        try:
            r.ping()
            health_data['redis_status'] = 'connected'
        except:
            health_data['redis_status'] = 'disconnected'
            health_data['status'] = 'degraded'
    
    # Check payment provider availability (if configured)
    if PAYMENT_PROVIDER_API_KEY:
        try:
            # Simple connectivity test through proxy
            session = get_brightdata_session()
            response = session.get('https://api.payment-provider.com/v1/health', timeout=5)
            health_data['payment_provider_status'] = 'available' if response.status_code == 200 else 'unavailable'
        except:
            health_data['payment_provider_status'] = 'unavailable'
    
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
            # Count orders by status
            order_statuses = {}
            for key in r.scan_iter(match="order:*", count=1000):
                order_data = r.hgetall(key)
                status = order_data.get('status', 'unknown')
                order_statuses[status] = order_statuses.get(status, 0) + 1
            
            for status, count in order_statuses.items():
                metrics_data.append(f'orders_by_status{{status="{status}"}} {count}')
            
            # Queue length
            queue_length = r.llen('test_queue')
            metrics_data.append(f'test_queue_length {queue_length}')
            
            # Paid orders count
            paid_orders_count = r.scard('paid_orders')
            metrics_data.append(f'paid_orders_total {paid_orders_count}')
        
        return '\n'.join(metrics_data), 200, {'Content-Type': 'text/plain'}
    
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        return "# Error generating metrics\n", 500, {'Content-Type': 'text/plain'}

@app.errorhandler(401)
def unauthorized(e):
    return jsonify({'error': 'Unauthorized - invalid JWT token'}), 401

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({'error': 'Rate limit exceeded', 'retry_after': str(e.retry_after)}), 429

if __name__ == '__main__':
    logger.info("Starting Order and Billing Service...")
    logger.info(f"Redis URL: {REDIS_URL}")
    logger.info(f"JWT Secret configured: {'Yes' if JWT_SECRET != 'default-jwt-secret-change-me' else 'No (using default)'}")
    logger.info(f"Payment Provider configured: {'Yes' if PAYMENT_PROVIDER_API_KEY else 'No'}")
    
    port = int(os.environ.get('PORT', 8000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    app.run(host='0.0.0.0', port=port, debug=debug)