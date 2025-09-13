#!/usr/bin/env python3
"""
Telegram Bot Configuration
Central configuration management for the Tinder automation bot
"""

import os
from typing import Dict, List
from dataclasses import dataclass
from enum import Enum

class ServiceType(Enum):
    """Available service types"""
    TINDER_ACCOUNTS = "tinder_accounts"
    SNAPCHAT_ACCOUNTS = "snapchat_accounts" 
    COMBO_PACKAGES = "combo_packages"
    CUSTOM_ORDERS = "custom_orders"

class OrderStatus(Enum):
    """Order status tracking"""
    PENDING_PAYMENT = "pending_payment"
    PAYMENT_CONFIRMED = "payment_confirmed"
    IN_PROGRESS = "in_progress"
    DELIVERY_READY = "delivery_ready"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"

@dataclass
class ServicePackage:
    """Service package configuration"""
    id: str
    name: str
    description: str
    price_usd: float
    delivery_time_hours: int
    features: List[str]
    tinder_accounts: int = 0
    snapchat_accounts: int = 0
    includes_warming: bool = True
    includes_verification: bool = True

class TelegramBotConfig:
    """Main bot configuration"""
    
    # Bot credentials
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8163343176:AAGnfDmoyeL7NSU0nLfLMqEohWxL5hZA6_0")
    BOT_URL = "t.me/buytinderadds"
    
    # Payment configuration
    PAYMENT_PROVIDER_TOKEN = os.getenv("PAYMENT_PROVIDER_TOKEN", "")
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
    WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "your-webhook-secret-here")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://your-domain.com/webhook")
    
    # Database configuration
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/tinder_bot")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Service configuration
    MAX_ORDERS_PER_USER_PER_DAY = 10
    DEFAULT_DELIVERY_TIME_HOURS = 2
    ADMIN_USER_IDS = [int(x) for x in os.getenv("ADMIN_USER_IDS", "").split(",") if x.strip()]
    
    # Referral system
    REFERRAL_BONUS_PERCENTAGE = 10
    MIN_REFERRAL_AMOUNT = 50
    
    # Service packages
    SERVICE_PACKAGES = {
        "starter_pack": ServicePackage(
            id="starter_pack",
            name="🚀 Starter Pack",
            description="Perfect for beginners - 3 premium Tinder accounts with warming",
            price_usd=29.99,
            delivery_time_hours=1,
            tinder_accounts=3,
            features=[
                "3 High-quality Tinder accounts",
                "Email + phone verified",
                "7-day warming included",
                "Anti-ban protection",
                "24/7 support"
            ]
        ),
        
        "growth_pack": ServicePackage(
            id="growth_pack", 
            name="📈 Growth Pack",
            description="Best value - 10 Tinder accounts + 5 Snapchat for social proof",
            price_usd=79.99,
            delivery_time_hours=2,
            tinder_accounts=10,
            snapchat_accounts=5,
            features=[
                "10 Premium Tinder accounts",
                "5 Snapchat accounts for social proof",
                "Full verification (email + phone)",
                "14-day warming included",
                "Custom profile optimization",
                "Anti-ban protection",
                "Priority support"
            ]
        ),
        
        "business_pack": ServicePackage(
            id="business_pack",
            name="💼 Business Pack", 
            description="For serious marketers - 25 accounts with advanced features",
            price_usd=199.99,
            delivery_time_hours=4,
            tinder_accounts=25,
            snapchat_accounts=10,
            features=[
                "25 Premium Tinder accounts",
                "10 Snapchat accounts",
                "Full verification + warming",
                "Custom profile creation",
                "Advanced anti-detection",
                "30-day replacement guarantee",
                "Dedicated account manager",
                "API access for automation"
            ]
        ),
        
        "enterprise_pack": ServicePackage(
            id="enterprise_pack",
            name="🏢 Enterprise Pack",
            description="Maximum scale - 100+ accounts with full management",
            price_usd=499.99,
            delivery_time_hours=6,
            tinder_accounts=100,
            snapchat_accounts=25,
            features=[
                "100+ Premium Tinder accounts",
                "25+ Snapchat accounts", 
                "Custom quantity options",
                "Full verification + warming",
                "Advanced anti-detection",
                "Custom profile creation",
                "60-day replacement guarantee",
                "Dedicated account manager",
                "API access + webhooks",
                "White-label options",
                "Custom integrations"
            ]
        )
    }
    
    # Bulk discount tiers
    BULK_DISCOUNTS = {
        3: 0.05,    # 5% off for 3+ packages
        5: 0.10,    # 10% off for 5+ packages  
        10: 0.15,   # 15% off for 10+ packages
        25: 0.20    # 20% off for 25+ packages
    }
    
    # Automated responses
    WELCOME_MESSAGE = """
🎉 Welcome to **Tinder Account Services**!

We provide high-quality, verified Tinder accounts with:
✅ Phone + Email Verification
✅ Anti-Ban Protection  
✅ Account Warming Service
✅ 24/7 Support
✅ Fast Delivery (1-6 hours)

💰 **Current Packages:**
🚀 Starter Pack - $29.99 (3 accounts)
📈 Growth Pack - $79.99 (10 accounts + 5 Snapchat)  
💼 Business Pack - $199.99 (25 accounts + 10 Snapchat)
🏢 Enterprise Pack - $499.99 (100+ accounts custom)

Use /packages to see all options
Use /order to start your order
Use /status to check existing orders
Use /support for help

Ready to boost your dating game? 🔥
    """
    
    HELP_MESSAGE = """
🤖 **Bot Commands:**

**Main Commands:**
/start - Welcome message & overview
/packages - View all service packages  
/order - Start a new order
/status - Check your order status
/support - Contact support
/referral - Get your referral link

**Account Commands:**
/balance - Check account balance
/history - View order history
/profile - Manage your profile

**Admin Commands** (Admin only):
/admin - Admin panel
/stats - Bot statistics
/users - User management
/orders - Order management

**Need Help?**
For technical support: @your_support_username
For urgent issues: Use /support command

Business hours: 24/7 automated + human support 9AM-11PM EST
    """
    
    # Rate limiting
    RATE_LIMITS = {
        "messages_per_minute": 20,
        "orders_per_hour": 5,
        "payment_attempts_per_hour": 3
    }
    
    # Quality assurance
    MIN_ACCOUNT_QUALITY_SCORE = 85
    MAX_DELIVERY_TIME_HOURS = 24
    SUCCESS_RATE_THRESHOLD = 95
    
    @classmethod
    def get_package(cls, package_id: str) -> ServicePackage:
        """Get service package by ID"""
        return cls.SERVICE_PACKAGES.get(package_id)
    
    @classmethod
    def get_all_packages(cls) -> Dict[str, ServicePackage]:
        """Get all available packages"""
        return cls.SERVICE_PACKAGES
    
    @classmethod
    def calculate_bulk_discount(cls, quantity: int) -> float:
        """Calculate bulk discount percentage"""
        discount = 0.0
        for min_qty, discount_pct in sorted(cls.BULK_DISCOUNTS.items(), reverse=True):
            if quantity >= min_qty:
                discount = discount_pct
                break
        return discount
    
    @classmethod
    def get_total_price(cls, package_id: str, quantity: int = 1) -> tuple[float, float]:
        """Calculate total price with discounts"""
        package = cls.get_package(package_id)
        if not package:
            return 0.0, 0.0
        
        base_price = package.price_usd * quantity
        discount_pct = cls.calculate_bulk_discount(quantity)
        discount_amount = base_price * discount_pct
        final_price = base_price - discount_amount
        
        return final_price, discount_amount

# Environment validation
def validate_config():
    """Validate critical configuration"""
    errors = []
    
    if not TelegramBotConfig.BOT_TOKEN or TelegramBotConfig.BOT_TOKEN.startswith("your-token"):
        errors.append("Missing or invalid BOT_TOKEN")
    
    if not TelegramBotConfig.PAYMENT_PROVIDER_TOKEN:
        errors.append("Missing PAYMENT_PROVIDER_TOKEN for Telegram payments")
    
    if not TelegramBotConfig.STRIPE_SECRET_KEY:
        errors.append("Missing STRIPE_SECRET_KEY for payment processing")
    
    if not TelegramBotConfig.ADMIN_USER_IDS:
        errors.append("No admin users configured")
    
    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")
    
    return True

if __name__ == "__main__":
    # Test configuration
    try:
        validate_config()
        print("✅ Configuration validated successfully")
        
        # Show package details
        print("\n📦 Available Packages:")
        for pkg_id, pkg in TelegramBotConfig.get_all_packages().items():
            print(f"  {pkg.name}: ${pkg.price_usd} ({pkg.tinder_accounts} accounts)")
        
        # Test bulk pricing
        print("\n💰 Bulk Pricing Examples:")
        for qty in [1, 3, 5, 10, 25]:
            price, discount = TelegramBotConfig.get_total_price("growth_pack", qty)
            print(f"  {qty}x Growth Pack: ${price:.2f} (${discount:.2f} discount)")
    
    except ValueError as e:
        print(f"❌ Configuration error: {e}")