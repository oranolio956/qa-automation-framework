#!/usr/bin/env python3
"""
Pydantic Schemas for Order and Billing Pipeline
Defines data validation models for the order management system
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class JobType(str, Enum):
    """Available job types for testing"""
    TOUCH_TEST = "touch_test"
    NETWORK_TEST = "network_test"
    IMAGE_TEST = "image_test"
    FULL_SUITE = "full_suite"
    LOAD_TEST = "load_test"
    CUSTOM = "custom"

class OrderStatus(str, Enum):
    """Order status states"""
    PENDING = "pending"
    PAID = "paid"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class PaymentStatus(str, Enum):
    """Payment status states"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

class Priority(str, Enum):
    """Job priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class OrderRequest(BaseModel):
    """Schema for creating a new order"""
    job_type: JobType = Field(..., description="Type of testing job to perform")
    quantity: int = Field(..., gt=0, le=1000, description="Number of test iterations")
    priority: Priority = Field(default=Priority.NORMAL, description="Job priority level")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional job parameters")
    notification_webhook: Optional[str] = Field(None, description="Webhook URL for completion notifications")
    customer_id: Optional[str] = Field(None, description="Customer identifier")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom metadata")

    @validator('parameters')
    def validate_parameters(cls, v):
        """Validate job parameters based on job type"""
        if v is None:
            return {}
        
        # Ensure parameters don't contain sensitive data
        forbidden_keys = ['password', 'secret', 'token', 'key']
        for key in v.keys():
            if any(forbidden in key.lower() for forbidden in forbidden_keys):
                raise ValueError(f"Parameter key '{key}' contains forbidden terms")
        
        return v

    @validator('notification_webhook')
    def validate_webhook_url(cls, v):
        """Validate webhook URL format"""
        if v is not None:
            if not v.startswith(('http://', 'https://')):
                raise ValueError("Webhook URL must start with http:// or https://")
            if len(v) > 2048:
                raise ValueError("Webhook URL too long")
        return v

class OrderResponse(BaseModel):
    """Schema for order response"""
    order_id: str
    status: OrderStatus
    job_type: JobType
    quantity: int
    priority: Priority
    total_amount: float
    currency: str = "USD"
    invoice_url: Optional[str] = None
    estimated_completion_time: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None

class PaymentWebhook(BaseModel):
    """Schema for payment webhook payload"""
    order_id: str
    payment_id: str
    status: PaymentStatus
    amount: float
    currency: str = "USD"
    provider: str
    transaction_id: Optional[str] = None
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @validator('amount')
    def validate_amount(cls, v):
        """Validate payment amount"""
        if v <= 0:
            raise ValueError("Payment amount must be positive")
        if v > 100000:  # $100k limit
            raise ValueError("Payment amount exceeds maximum limit")
        return round(v, 2)

class OrderUpdate(BaseModel):
    """Schema for updating order status"""
    status: Optional[OrderStatus] = None
    progress_percentage: Optional[int] = Field(None, ge=0, le=100)
    results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    worker_id: Optional[str] = None
    estimated_completion: Optional[datetime] = None

class OrderQuery(BaseModel):
    """Schema for querying orders"""
    customer_id: Optional[str] = None
    status: Optional[OrderStatus] = None
    job_type: Optional[JobType] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)

class BillingInfo(BaseModel):
    """Schema for billing information"""
    customer_id: str
    email: str
    company_name: Optional[str] = None
    billing_address: Optional[Dict[str, str]] = None
    tax_id: Optional[str] = None
    payment_method: Optional[str] = None

class PricingTier(BaseModel):
    """Schema for pricing tier definition"""
    name: str
    job_type: JobType
    base_price: float
    price_per_unit: float
    bulk_discounts: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    max_quantity: Optional[int] = None

class InvoiceLineItem(BaseModel):
    """Schema for invoice line items"""
    description: str
    quantity: int
    unit_price: float
    total_price: float
    job_type: Optional[JobType] = None

class Invoice(BaseModel):
    """Schema for invoice generation"""
    invoice_id: str
    order_id: str
    customer_id: str
    line_items: List[InvoiceLineItem]
    subtotal: float
    tax_amount: float = 0.0
    total_amount: float
    currency: str = "USD"
    issued_at: datetime
    due_at: datetime
    status: str = "pending"
    payment_url: Optional[str] = None

    @validator('total_amount')
    def validate_total_matches(cls, v, values):
        """Ensure total amount matches subtotal + tax"""
        subtotal = values.get('subtotal', 0)
        tax_amount = values.get('tax_amount', 0)
        expected_total = subtotal + tax_amount
        
        if abs(v - expected_total) > 0.01:  # Allow for rounding differences
            raise ValueError(f"Total amount {v} doesn't match subtotal + tax {expected_total}")
        
        return v

class RefundRequest(BaseModel):
    """Schema for refund requests"""
    order_id: str
    amount: Optional[float] = None  # None means full refund
    reason: str
    initiated_by: str

class RefundResponse(BaseModel):
    """Schema for refund response"""
    refund_id: str
    order_id: str
    amount: float
    status: str
    reason: str
    processed_at: Optional[datetime] = None

# Pricing configuration
PRICING_CONFIG = {
    JobType.TOUCH_TEST: {
        "base_price": 2.00,
        "price_per_unit": 0.50,
        "bulk_discounts": [
            {"min_quantity": 50, "discount_percent": 10},
            {"min_quantity": 100, "discount_percent": 20},
            {"min_quantity": 500, "discount_percent": 30}
        ]
    },
    JobType.NETWORK_TEST: {
        "base_price": 3.00,
        "price_per_unit": 0.75,
        "bulk_discounts": [
            {"min_quantity": 25, "discount_percent": 15},
            {"min_quantity": 100, "discount_percent": 25}
        ]
    },
    JobType.IMAGE_TEST: {
        "base_price": 1.50,
        "price_per_unit": 0.30,
        "bulk_discounts": [
            {"min_quantity": 100, "discount_percent": 10},
            {"min_quantity": 500, "discount_percent": 20}
        ]
    },
    JobType.FULL_SUITE: {
        "base_price": 10.00,
        "price_per_unit": 2.50,
        "bulk_discounts": [
            {"min_quantity": 10, "discount_percent": 15},
            {"min_quantity": 50, "discount_percent": 25}
        ]
    },
    JobType.LOAD_TEST: {
        "base_price": 15.00,
        "price_per_unit": 5.00,
        "bulk_discounts": [
            {"min_quantity": 5, "discount_percent": 10},
            {"min_quantity": 20, "discount_percent": 20}
        ]
    }
}

def calculate_order_total(job_type: JobType, quantity: int) -> float:
    """Calculate total price for an order"""
    config = PRICING_CONFIG.get(job_type)
    if not config:
        raise ValueError(f"Pricing not configured for job type: {job_type}")
    
    base_price = config["base_price"]
    price_per_unit = config["price_per_unit"]
    
    # Calculate base total
    total = base_price + (price_per_unit * quantity)
    
    # Apply bulk discounts
    for discount in config.get("bulk_discounts", []):
        if quantity >= discount["min_quantity"]:
            discount_amount = total * (discount["discount_percent"] / 100)
            total -= discount_amount
            break  # Apply only the highest applicable discount
    
    return round(total, 2)