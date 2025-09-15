#!/usr/bin/env python3
"""
Order Management System for Telegram Bot
Handles order lifecycle, status tracking, and service delivery integration
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .config import TelegramBotConfig, OrderStatus, ServiceType
from .database import get_order_manager, get_user_manager, get_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrderLifecycleManager:
    """Manages complete order lifecycle from creation to delivery"""
    
    def __init__(self):
        self.status_transitions = {
            'pending_payment': ['payment_confirmed', 'cancelled'],
            'payment_confirmed': ['in_progress', 'failed'],
            'in_progress': ['delivery_ready', 'failed'],
            'delivery_ready': ['completed'],
            'completed': [],
            'failed': ['in_progress'],  # Allow retry
            'cancelled': [],
            'refunded': []
        }
    
    async def create_new_order(self, user_id: int, package_id: str, quantity: int = 1) -> Dict[str, any]:
        """Create a new order with full validation"""
        try:
            # Validate package
            package = TelegramBotConfig.get_package(package_id)
            if not package:
                return {
                    'success': False,
                    'error': 'Invalid package selected',
                    'code': 'INVALID_PACKAGE'
                }
            
            # Check user limits
            if not await self._check_user_limits(user_id):
                return {
                    'success': False,
                    'error': f'Daily limit exceeded ({TelegramBotConfig.MAX_ORDERS_PER_USER_PER_DAY} orders/day)',
                    'code': 'RATE_LIMITED'
                }
            
            # Validate quantity
            if quantity < 1 or quantity > 100:
                return {
                    'success': False,
                    'error': 'Invalid quantity (1-100)',
                    'code': 'INVALID_QUANTITY'
                }
            
            # Create order
            order_mgr = await get_order_manager()
            order_id = await order_mgr.create_order(user_id, package_id, quantity)
            
            if not order_id:
                return {
                    'success': False,
                    'error': 'Failed to create order',
                    'code': 'CREATION_FAILED'
                }
            
            # Get pricing details
            total_price, discount = TelegramBotConfig.get_total_price(package_id, quantity)
            
            return {
                'success': True,
                'order_id': order_id,
                'package': package,
                'quantity': quantity,
                'total_price': total_price,
                'discount': discount,
                'estimated_delivery': datetime.now() + timedelta(hours=package.delivery_time_hours)
            }
            
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return {
                'success': False,
                'error': 'Internal error creating order',
                'code': 'INTERNAL_ERROR'
            }
    
    async def update_order_status(self, order_id: str, new_status: str, notes: str = None, user_id: int = None) -> Dict[str, any]:
        """Update order status with validation"""
        try:
            order_mgr = await get_order_manager()
            order = await order_mgr.get_order(order_id)
            
            if not order:
                return {
                    'success': False,
                    'error': 'Order not found',
                    'code': 'ORDER_NOT_FOUND'
                }
            
            # Validate status transition
            current_status = order['status']
            if not self._is_valid_status_transition(current_status, new_status):
                return {
                    'success': False,
                    'error': f'Invalid status transition: {current_status} -> {new_status}',
                    'code': 'INVALID_TRANSITION'
                }
            
            # Update status
            success = await order_mgr.update_order_status(order_id, new_status, notes)
            
            if success:
                # Handle status-specific actions
                await self._handle_status_change(order, new_status)
                
                # Notify user if provided
                if user_id:
                    await self._notify_status_change(user_id, order_id, new_status)
                
                return {
                    'success': True,
                    'order_id': order_id,
                    'old_status': current_status,
                    'new_status': new_status
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to update status',
                    'code': 'UPDATE_FAILED'
                }
                
        except Exception as e:
            logger.error(f"Error updating order status {order_id}: {e}")
            return {
                'success': False,
                'error': 'Internal error updating status',
                'code': 'INTERNAL_ERROR'
            }
    
    async def get_order_details(self, order_id: str, user_id: int = None) -> Dict[str, any]:
        """Get comprehensive order details"""
        try:
            order_mgr = await get_order_manager()
            order = await order_mgr.get_order(order_id)
            
            if not order:
                return {
                    'success': False,
                    'error': 'Order not found',
                    'code': 'ORDER_NOT_FOUND'
                }
            
            # Verify user ownership if user_id provided
            if user_id and order['user_id'] != user_id:
                return {
                    'success': False,
                    'error': 'Unauthorized access',
                    'code': 'UNAUTHORIZED'
                }
            
            # Get package details
            package = TelegramBotConfig.get_package(order['package_id'])
            
            # Get delivery progress
            progress = await self._get_delivery_progress(order_id)
            
            # Calculate status info
            status_info = self._get_status_info(order)
            
            return {
                'success': True,
                'order': {
                    'id': order['order_id'],
                    'status': order['status'],
                    'package': package,
                    'quantity': order['quantity'],
                    'total_amount': float(order['total_amount']),
                    'discount_amount': float(order['discount_amount']),
                    'created_at': order['created_at'],
                    'expected_delivery': order['expected_delivery'],
                    'delivery_started_at': order['delivery_started_at'],
                    'completed_at': order['completed_at'],
                    'notes': order['notes']
                },
                'progress': progress,
                'status_info': status_info
            }
            
        except Exception as e:
            logger.error(f"Error getting order details {order_id}: {e}")
            return {
                'success': False,
                'error': 'Internal error getting order details',
                'code': 'INTERNAL_ERROR'
            }
    
    async def cancel_order(self, order_id: str, user_id: int, reason: str = "User cancellation") -> Dict[str, any]:
        """Cancel an order if possible"""
        try:
            order_mgr = await get_order_manager()
            order = await order_mgr.get_order(order_id)
            
            if not order:
                return {
                    'success': False,
                    'error': 'Order not found',
                    'code': 'ORDER_NOT_FOUND'
                }
            
            if order['user_id'] != user_id:
                return {
                    'success': False,
                    'error': 'Unauthorized',
                    'code': 'UNAUTHORIZED'
                }
            
            # Check if cancellation is allowed
            if order['status'] in ['completed', 'cancelled', 'refunded']:
                return {
                    'success': False,
                    'error': f'Cannot cancel order with status: {order["status"]}',
                    'code': 'CANCELLATION_NOT_ALLOWED'
                }
            
            # Cancel order
            success = await order_mgr.update_order_status(order_id, 'cancelled', f"Cancelled: {reason}")
            
            if success:
                # Stop any automation jobs
                await self._stop_automation_job(order_id)
                
                # Process refund if payment was made
                if order['status'] in ['payment_confirmed', 'in_progress']:
                    await self._process_refund(order_id)
                
                return {
                    'success': True,
                    'order_id': order_id,
                    'message': 'Order cancelled successfully'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to cancel order',
                    'code': 'CANCELLATION_FAILED'
                }
                
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return {
                'success': False,
                'error': 'Internal error cancelling order',
                'code': 'INTERNAL_ERROR'
            }
    
    async def start_delivery_process(self, order_id: str) -> Dict[str, any]:
        """Start the automation/delivery process for an order"""
        try:
            order_mgr = await get_order_manager()
            order = await order_mgr.get_order(order_id)
            
            if not order:
                return {'success': False, 'error': 'Order not found'}
            
            if order['status'] != 'payment_confirmed':
                return {'success': False, 'error': f'Invalid status for delivery: {order["status"]}'}
            
            # Start automation job
            success = await order_mgr.start_automation_job(order_id)
            
            if success:
                await self._track_delivery_start(order_id)
                return {
                    'success': True,
                    'order_id': order_id,
                    'message': 'Delivery process started'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to start delivery process'
                }
                
        except Exception as e:
            logger.error(f"Error starting delivery for order {order_id}: {e}")
            return {'success': False, 'error': 'Internal error starting delivery'}
    
    async def _check_user_limits(self, user_id: int) -> bool:
        """Check if user has exceeded daily order limits"""
        try:
            db = await get_database()
            query = """
            SELECT COUNT(*) as order_count
            FROM orders 
            WHERE user_id = $1 AND created_at >= NOW() - INTERVAL '24 hours'
            """
            
            async with db.postgres_pool.acquire() as connection:
                result = await connection.fetchrow(query, user_id)
                return result['order_count'] < TelegramBotConfig.MAX_ORDERS_PER_USER_PER_DAY
                
        except Exception as e:
            logger.error(f"Error checking user limits: {e}")
            return False
    
    def _is_valid_status_transition(self, current: str, new: str) -> bool:
        """Check if status transition is valid"""
        allowed_transitions = self.status_transitions.get(current, [])
        return new in allowed_transitions
    
    async def _handle_status_change(self, order: dict, new_status: str):
        """Handle status-specific actions"""
        try:
            if new_status == 'payment_confirmed':
                # Start delivery process
                await self.start_delivery_process(order['order_id'])
                
            elif new_status == 'in_progress':
                # Update expected delivery time
                await self._update_delivery_estimate(order['order_id'])
                
            elif new_status == 'completed':
                # Process completion actions
                await self._process_order_completion(order['order_id'])
                
            elif new_status == 'failed':
                # Handle failure
                await self._handle_order_failure(order['order_id'])
                
        except Exception as e:
            logger.error(f"Error handling status change to {new_status}: {e}")
    
    async def _get_delivery_progress(self, order_id: str) -> Dict[str, any]:
        """Get delivery progress for an order"""
        try:
            db = await get_database()
            
            # Get delivered accounts
            query = """
            SELECT 
                account_type,
                COUNT(*) as count,
                AVG(quality_score) as avg_quality
            FROM account_deliveries 
            WHERE order_id = $1 
            GROUP BY account_type
            """
            
            async with db.postgres_pool.acquire() as connection:
                results = await connection.fetch(query, order_id)
                
            progress = {
                'accounts_delivered': sum(row['count'] for row in results),
                'account_breakdown': {
                    row['account_type']: {
                        'count': row['count'],
                        'avg_quality': float(row['avg_quality']) if row['avg_quality'] else 0
                    }
                    for row in results
                },
                'overall_progress': 0
            }
            
            # Calculate overall progress percentage
            order_mgr = await get_order_manager()
            order = await order_mgr.get_order(order_id)
            if order:
                package = TelegramBotConfig.get_package(order['package_id'])
                total_expected = (package.tinder_accounts + package.snapchat_accounts) * order['quantity']
                if total_expected > 0:
                    progress['overall_progress'] = min(100, (progress['accounts_delivered'] / total_expected) * 100)
            
            return progress
            
        except Exception as e:
            logger.error(f"Error getting delivery progress: {e}")
            return {'accounts_delivered': 0, 'overall_progress': 0}
    
    def _get_status_info(self, order: dict) -> Dict[str, any]:
        """Get user-friendly status information"""
        status = order['status']
        
        status_messages = {
            'pending_payment': {
                'message': '💰 Waiting for payment',
                'description': 'Complete your payment to start processing',
                'can_cancel': True,
                'estimated_completion': None
            },
            'payment_confirmed': {
                'message': '✅ Payment confirmed',
                'description': 'Starting account creation process',
                'can_cancel': True,
                'estimated_completion': order['expected_delivery']
            },
            'in_progress': {
                'message': '🔄 Creating accounts',
                'description': 'Your accounts are being created and verified',
                'can_cancel': False,
                'estimated_completion': order['expected_delivery']
            },
            'delivery_ready': {
                'message': '📦 Ready for delivery',
                'description': 'Accounts created successfully, preparing delivery',
                'can_cancel': False,
                'estimated_completion': None
            },
            'completed': {
                'message': '🎉 Order completed',
                'description': 'All accounts delivered successfully',
                'can_cancel': False,
                'estimated_completion': None
            },
            'failed': {
                'message': '❌ Order failed',
                'description': 'There was an issue with your order. Support has been notified.',
                'can_cancel': True,
                'estimated_completion': None
            },
            'cancelled': {
                'message': '🚫 Order cancelled',
                'description': 'Order was cancelled',
                'can_cancel': False,
                'estimated_completion': None
            },
            'refunded': {
                'message': '💸 Refunded',
                'description': 'Payment has been refunded',
                'can_cancel': False,
                'estimated_completion': None
            }
        }
        
        return status_messages.get(status, {
            'message': f'Status: {status}',
            'description': 'Order status',
            'can_cancel': False,
            'estimated_completion': None
        })
    
    async def _notify_status_change(self, user_id: int, order_id: str, new_status: str):
        """Notify user of status change via bot message"""
        # This would integrate with the main bot to send messages
        # Implementation depends on bot architecture
        pass
    
    async def _update_delivery_estimate(self, order_id: str):
        """Update delivery estimate based on current progress"""
        try:
            # Get current progress
            progress = await self._get_delivery_progress(order_id)
            
            if progress['overall_progress'] > 0:
                # Calculate new estimate based on progress
                order_mgr = await get_order_manager()
                order = await order_mgr.get_order(order_id)
                
                if order and order['delivery_started_at']:
                    elapsed = datetime.now() - order['delivery_started_at']
                    if progress['overall_progress'] > 10:  # Avoid division by very small numbers
                        total_estimated = elapsed * (100 / progress['overall_progress'])
                        new_completion = order['delivery_started_at'] + total_estimated
                        
                        # Update expected delivery
                        db = await get_database()
                        query = "UPDATE orders SET expected_delivery = $1 WHERE order_id = $2"
                        async with db.postgres_pool.acquire() as connection:
                            await connection.execute(query, new_completion, order_id)
                            
        except Exception as e:
            logger.error(f"Error updating delivery estimate: {e}")
    
    async def _process_order_completion(self, order_id: str):
        """Process order completion actions"""
        try:
            # Update user statistics
            order_mgr = await get_order_manager()
            order = await order_mgr.get_order(order_id)
            
            if order:
                user_id = order['user_id']
                amount = float(order['total_amount'])
                
                # Update user totals
                db = await get_database()
                query = """
                UPDATE users 
                SET total_orders = total_orders + 1,
                    total_spent = total_spent + $1
                WHERE user_id = $2
                """
                async with db.postgres_pool.acquire() as connection:
                    await connection.execute(query, amount, user_id)
                
                # Track completion analytics
                await self._track_event('order_completed', user_id, order_id, {
                    'package_id': order['package_id'],
                    'quantity': order['quantity'],
                    'total_amount': amount
                })
                
        except Exception as e:
            logger.error(f"Error processing order completion: {e}")
    
    async def _handle_order_failure(self, order_id: str):
        """Handle order failure"""
        try:
            # Stop automation job
            await self._stop_automation_job(order_id)
            
            # Notify admins
            await self._notify_admins_order_failure(order_id)
            
            # Consider automatic retry logic here
            
        except Exception as e:
            logger.error(f"Error handling order failure: {e}")
    
    async def _stop_automation_job(self, order_id: str):
        """Stop automation job for order"""
        try:
            # This would integrate with the automation system to stop jobs
            logger.info(f"Stopping automation job for order {order_id}")
        except Exception as e:
            logger.error(f"Error stopping automation job: {e}")
    
    async def _process_refund(self, order_id: str):
        """Process refund for cancelled order"""
        try:
            # This would integrate with payment processors to issue refunds
            logger.info(f"Processing refund for order {order_id}")
        except Exception as e:
            logger.error(f"Error processing refund: {e}")
    
    async def _track_delivery_start(self, order_id: str):
        """Track delivery start analytics"""
        try:
            await self._track_event('delivery_started', None, order_id)
        except Exception as e:
            logger.error(f"Error tracking delivery start: {e}")
    
    async def _track_event(self, event_type: str, user_id: int = None, order_id: str = None, data: dict = None):
        """Track analytics event"""
        try:
            db = await get_database()
            query = """
            INSERT INTO analytics (event_type, user_id, order_id, event_data)
            VALUES ($1, $2, $3, $4)
            """
            
            async with db.postgres_pool.acquire() as connection:
                await connection.execute(
                    query, event_type, user_id, order_id,
                    json.dumps(data) if data else None
                )
        except Exception as e:
            logger.error(f"Error tracking event: {e}")
    
    async def _notify_admins_order_failure(self, order_id: str):
        """Notify admins of order failure"""
        try:
            # This would send notifications to admin users
            logger.warning(f"Order failure notification needed for {order_id}")
        except Exception as e:
            logger.error(f"Error notifying admins: {e}")

# Keyboard helpers for order management
def create_order_status_keyboard(order_id: str, can_cancel: bool = False) -> InlineKeyboardMarkup:
    """Create order status keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("🔄 Refresh Status", callback_data=f"refresh_order:{order_id}")
        ]
    ]
    
    if can_cancel:
        keyboard.append([
            InlineKeyboardButton("❌ Cancel Order", callback_data=f"cancel_order:{order_id}")
        ])
    
    keyboard.extend([
        [
            InlineKeyboardButton("💬 Support", callback_data="contact_support"),
            InlineKeyboardButton("📋 My Orders", callback_data="my_orders")
        ],
        [
            InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
        ]
    ])
    
    return InlineKeyboardMarkup(keyboard)

def create_order_confirmation_keyboard(order_id: str) -> InlineKeyboardMarkup:
    """Create order confirmation keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("💳 Pay Now", callback_data=f"pay_order:{order_id}")
        ],
        [
            InlineKeyboardButton("📋 Order Details", callback_data=f"order_details:{order_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_order:{order_id}")
        ],
        [
            InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# Global order lifecycle manager
_order_lifecycle_manager = None

def get_order_lifecycle_manager() -> OrderLifecycleManager:
    """Get global order lifecycle manager"""
    global _order_lifecycle_manager
    if _order_lifecycle_manager is None:
        _order_lifecycle_manager = OrderLifecycleManager()
    return _order_lifecycle_manager

if __name__ == "__main__":
    # Test order management
    async def test_order_management():
        manager = OrderLifecycleManager()
        
        # Test order creation
        result = await manager.create_new_order(
            user_id=123456,
            package_id='starter_pack',
            quantity=1
        )
        print(f"Order creation: {result}")
        
        if result['success']:
            order_id = result['order_id']
            
            # Test order details
            details = await manager.get_order_details(order_id)
            print(f"Order details: {details}")
            
            # Test status update
            status_update = await manager.update_order_status(
                order_id, 'payment_confirmed', 'Test payment confirmation'
            )
            print(f"Status update: {status_update}")
        
        print("✅ Order management tests completed")
    
    asyncio.run(test_order_management())