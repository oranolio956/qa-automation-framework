#!/usr/bin/env python3
"""
Payment Processing System for Telegram Bot
Handles Stripe payments, webhooks, and retry mechanisms
"""

import os
import json
import hmac
import hashlib
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal

import stripe
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import ContextTypes

from .config import TelegramBotConfig, OrderStatus
from .database import get_payment_manager, get_order_manager, get_user_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = TelegramBotConfig.STRIPE_SECRET_KEY

class PaymentProcessor:
    """Main payment processing class"""
    
    def __init__(self):
        self.webhook_secret = TelegramBotConfig.WEBHOOK_SECRET
        self.max_retries = 3
        self.retry_delays = [30, 300, 1800]  # 30s, 5min, 30min
    
    async def create_telegram_payment_invoice(self, 
                                            user_id: int, 
                                            order_id: str, 
                                            package_id: str, 
                                            quantity: int = 1) -> Dict[str, any]:
        """Create Telegram payment invoice"""
        try:
            package = TelegramBotConfig.get_package(package_id)
            if not package:
                return {'success': False, 'error': 'Package not found'}
            
            # Calculate pricing
            total_price, discount = TelegramBotConfig.get_total_price(package_id, quantity)
            
            # Create payment record
            payment_mgr = await get_payment_manager()
            payment_id = await payment_mgr.create_payment(
                order_id, user_id, total_price, 'telegram'
            )
            
            # Create invoice payload
            title = f"{package.name} (x{quantity})"
            description = package.description
            
            if discount > 0:
                description += f"\n\n💰 Bulk discount: ${discount:.2f} saved!"
            
            # Telegram expects prices in smallest currency unit (cents)
            prices = [LabeledPrice(title, int(total_price * 100))]
            
            payload = {
                'payment_id': payment_id,
                'order_id': order_id,
                'user_id': user_id,
                'package_id': package_id,
                'quantity': quantity,
                'amount': total_price
            }
            
            return {
                'success': True,
                'payment_id': payment_id,
                'title': title,
                'description': description,
                'payload': json.dumps(payload),
                'prices': prices,
                'currency': 'USD'
            }
            
        except Exception as e:
            logger.error(f"Error creating Telegram invoice: {e}")
            return {'success': False, 'error': str(e)}
    
    async def create_stripe_payment_intent(self, 
                                         user_id: int,
                                         order_id: str,
                                         package_id: str,
                                         quantity: int = 1) -> Dict[str, any]:
        """Create Stripe payment intent for web payments"""
        try:
            package = TelegramBotConfig.get_package(package_id)
            if not package:
                return {'success': False, 'error': 'Package not found'}
            
            total_price, discount = TelegramBotConfig.get_total_price(package_id, quantity)
            
            # Create payment record
            payment_mgr = await get_payment_manager()
            payment_id = await payment_mgr.create_payment(
                order_id, user_id, total_price, 'stripe'
            )
            
            # Create Stripe payment intent
            intent = stripe.PaymentIntent.create(
                amount=int(total_price * 100),  # Convert to cents
                currency='usd',
                metadata={
                    'payment_id': payment_id,
                    'order_id': order_id,
                    'user_id': str(user_id),
                    'package_id': package_id,
                    'quantity': str(quantity)
                },
                description=f"Tinder Accounts - {package.name} (x{quantity})"
            )
            
            return {
                'success': True,
                'payment_id': payment_id,
                'client_secret': intent.client_secret,
                'amount': total_price,
                'currency': 'USD'
            }
            
        except Exception as e:
            logger.error(f"Error creating Stripe payment intent: {e}")
            return {'success': False, 'error': str(e)}
    
    async def process_telegram_pre_checkout(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process Telegram pre-checkout query"""
        try:
            query = update.pre_checkout_query
            payload_data = json.loads(query.invoice_payload)
            
            # Verify order exists and is valid
            order_mgr = await get_order_manager()
            order = await order_mgr.get_order(payload_data['order_id'])
            
            if not order:
                await query.answer(ok=False, error_message="Order not found")
                return
            
            if order['status'] != 'pending_payment':
                await query.answer(ok=False, error_message="Order already processed")
                return
            
            if order['user_id'] != query.from_user.id:
                await query.answer(ok=False, error_message="Unauthorized")
                return
            
            # Verify amount
            expected_amount = int(float(payload_data['amount']) * 100)
            if query.total_amount != expected_amount:
                await query.answer(ok=False, error_message="Amount mismatch")
                return
            
            # Pre-checkout OK
            await query.answer(ok=True)
            
        except Exception as e:
            logger.error(f"Error in pre-checkout: {e}")
            await query.answer(ok=False, error_message="Payment processing error")
    
    async def process_telegram_successful_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process successful Telegram payment"""
        try:
            payment = update.message.successful_payment
            payload_data = json.loads(payment.invoice_payload)
            
            # Update payment status
            payment_mgr = await get_payment_manager()
            await payment_mgr.update_payment_status(
                payload_data['payment_id'], 
                'completed',
                payment.telegram_payment_charge_id
            )
            
            # Send confirmation message
            order_id = payload_data['order_id']
            package_id = payload_data['package_id']
            package = TelegramBotConfig.get_package(package_id)
            
            message = f"""
🎉 **Payment Successful!**

✅ Order ID: `{order_id}`
📦 Package: {package.name}
💰 Amount: ${payload_data['amount']:.2f}
🚀 Delivery: {package.delivery_time_hours} hours

Your accounts are now being created! 
You'll receive updates as they're ready.

Use /status to check progress anytime.
            """
            
            await update.message.reply_text(
                message,
                parse_mode='Markdown'
            )
            
            # Track successful payment
            await self._track_payment_event('telegram_payment_success', update.effective_user.id, order_id)
            
        except Exception as e:
            logger.error(f"Error processing successful payment: {e}")
    
    async def handle_stripe_webhook(self, request_body: bytes, signature: str) -> Dict[str, any]:
        """Handle Stripe webhook events"""
        try:
            # Verify webhook signature
            if not self._verify_stripe_signature(request_body, signature):
                return {'success': False, 'error': 'Invalid signature'}
            
            event = json.loads(request_body.decode('utf-8'))
            
            if event['type'] == 'payment_intent.succeeded':
                await self._handle_stripe_payment_success(event['data']['object'])
            elif event['type'] == 'payment_intent.payment_failed':
                await self._handle_stripe_payment_failed(event['data']['object'])
            
            return {'success': True, 'processed': event['type']}
            
        except Exception as e:
            logger.error(f"Error handling Stripe webhook: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_stripe_payment_success(self, payment_intent: dict):
        """Handle successful Stripe payment"""
        try:
            metadata = payment_intent['metadata']
            payment_id = metadata['payment_id']
            order_id = metadata['order_id']
            user_id = int(metadata['user_id'])
            
            # Update payment status
            payment_mgr = await get_payment_manager()
            await payment_mgr.update_payment_status(
                payment_id, 'completed', payment_intent['id']
            )
            
            # Send notification to user (if possible)
            await self._notify_user_payment_success(user_id, order_id)
            
            logger.info(f"Stripe payment success processed: {payment_id}")
            
        except Exception as e:
            logger.error(f"Error handling Stripe payment success: {e}")
    
    async def _handle_stripe_payment_failed(self, payment_intent: dict):
        """Handle failed Stripe payment"""
        try:
            metadata = payment_intent['metadata']
            payment_id = metadata['payment_id']
            
            # Update payment status
            payment_mgr = await get_payment_manager()
            await payment_mgr.update_payment_status(payment_id, 'failed')
            
            # Implement retry logic here if needed
            
            logger.info(f"Stripe payment failed: {payment_id}")
            
        except Exception as e:
            logger.error(f"Error handling Stripe payment failure: {e}")
    
    def _verify_stripe_signature(self, payload: bytes, signature: str) -> bool:
        """Verify Stripe webhook signature"""
        try:
            stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            return True
        except (ValueError, stripe.error.SignatureVerificationError):
            return False
    
    async def _notify_user_payment_success(self, user_id: int, order_id: str):
        """Notify user of successful payment via bot"""
        # This would need the bot instance to send messages
        # Implementation depends on how the bot is structured
        pass
    
    async def _track_payment_event(self, event_type: str, user_id: int, order_id: str, data: dict = None):
        """Track payment-related analytics events"""
        try:
            # Use database analytics tracking
            from .database import get_database
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
            logger.error(f"Error tracking payment event: {e}")

class PaymentRetryManager:
    """Manages payment retry logic and failed payment recovery"""
    
    def __init__(self):
        self.max_retries = 3
        self.base_delay = 60  # Base delay in seconds
    
    async def schedule_payment_retry(self, payment_id: str, retry_count: int = 0):
        """Schedule a payment retry"""
        if retry_count >= self.max_retries:
            logger.warning(f"Payment {payment_id} exceeded max retries")
            return
        
        delay = self.base_delay * (2 ** retry_count)  # Exponential backoff
        
        # Schedule retry (this would use a task queue in production)
        await asyncio.sleep(delay)
        await self._retry_payment(payment_id, retry_count)
    
    async def _retry_payment(self, payment_id: str, retry_count: int):
        """Attempt to retry a failed payment"""
        try:
            payment_mgr = await get_payment_manager()
            
            # Update retry count
            query = """
            UPDATE payments 
            SET retry_count = $1, last_retry_at = NOW()
            WHERE payment_id = $2
            """
            
            db = await get_payment_manager()
            async with db.db.postgres_pool.acquire() as connection:
                await connection.execute(query, retry_count + 1, payment_id)
            
            # Implement specific retry logic based on payment provider
            logger.info(f"Retried payment {payment_id}, attempt {retry_count + 1}")
            
        except Exception as e:
            logger.error(f"Error retrying payment {payment_id}: {e}")

# Payment keyboard helpers
def create_payment_keyboard(order_id: str, total_amount: float) -> InlineKeyboardMarkup:
    """Create payment method selection keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(
                f"💳 Pay ${total_amount:.2f} (Telegram)", 
                callback_data=f"pay_telegram:{order_id}"
            )
        ],
        [
            InlineKeyboardButton(
                f"🌐 Pay ${total_amount:.2f} (Web)", 
                callback_data=f"pay_web:{order_id}"
            )
        ],
        [
            InlineKeyboardButton("❌ Cancel Order", callback_data=f"cancel_order:{order_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_order_summary_keyboard(order_id: str) -> InlineKeyboardMarkup:
    """Create order summary and action keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("📊 Order Status", callback_data=f"order_status:{order_id}"),
            InlineKeyboardButton("💬 Support", callback_data="contact_support")
        ],
        [
            InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# Global payment processor instance
_payment_processor = None

def get_payment_processor() -> PaymentProcessor:
    """Get global payment processor instance"""
    global _payment_processor
    if _payment_processor is None:
        _payment_processor = PaymentProcessor()
    return _payment_processor

if __name__ == "__main__":
    # Test payment processing
    async def test_payments():
        processor = PaymentProcessor()
        
        # Test Telegram invoice creation
        telegram_invoice = await processor.create_telegram_payment_invoice(
            user_id=123456,
            order_id="ORD123456",
            package_id="starter_pack",
            quantity=1
        )
        print(f"Telegram invoice: {telegram_invoice}")
        
        # Test Stripe payment intent
        stripe_intent = await processor.create_stripe_payment_intent(
            user_id=123456,
            order_id="ORD123456",
            package_id="growth_pack",
            quantity=2
        )
        print(f"Stripe intent: {stripe_intent}")
        
        print("✅ Payment processor tests completed")
    
    asyncio.run(test_payments())