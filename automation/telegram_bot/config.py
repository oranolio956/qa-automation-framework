#!/usr/bin/env python3
"""
Telegram Bot Configuration
Central configuration management for the Tinder automation bot
"""

import os
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum
import time

# Secrets/config access with Vault fallback
try:
    from utils.vault_client import get_secret
except Exception:
    def get_secret(name: str, default=None, **kwargs):
        import os as _os
        return _os.getenv(name, default)

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
    BOT_TOKEN = get_secret("TELEGRAM_BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN must be set in the environment or Vault")
    BOT_URL = "t.me/snapchataddfarmer"
    
    # Payment configuration
    PAYMENT_PROVIDER_TOKEN = get_secret("PAYMENT_PROVIDER_TOKEN", "284685063:TEST:ZjE2NzBmN2Y1YTE5")
    STRIPE_SECRET_KEY = get_secret("STRIPE_SECRET_KEY", "")
    WEBHOOK_SECRET = get_secret("WEBHOOK_SECRET", "your-webhook-secret-here")
    WEBHOOK_URL = get_secret("WEBHOOK_URL", "https://your-domain.com/webhook")
    
    # Crypto payment addresses
    CRYPTO_ADDRESSES = {
        "bitcoin": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
        "ethereum": "0x742d35Cc6634C0532925a3b8D238C6f2f8B7a0d7", 
        "usdt_trc20": "TXYZnv3jLGHJ7Km5KpRt8Yq9N3BxCdAeWz",
        "usdt_erc20": "0x742d35Cc6634C0532925a3b8D238C6f2f8B7a0d7",
        "litecoin": "LTC1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
        "monero": "4AdUndXHHZ6cfufTMvppY6JwXNouMBzSkbLYfpAV5Usx3skxNgYeYTRj5UzqtReoS44qo9mtmXCqY45DJ852K5Jv2684Rge"
    }
    
# Database configuration
    DATABASE_URL = get_secret("DATABASE_URL", "postgresql://user:changeme@localhost/tinder_bot")
    REDIS_URL = get_secret("REDIS_URL", "redis://localhost:6379")
    
    # Service configuration
    MAX_ORDERS_PER_USER_PER_DAY = 10
    DEFAULT_DELIVERY_TIME_HOURS = 2
    ADMIN_USER_IDS = [int(x) for x in str(get_secret("ADMIN_USER_IDS", "5511648343,123456789")).split(",") if x.strip()]
    
    # Batch Processing Configuration (Anti-Detection Optimized)
    DEFAULT_BATCH_SIZE = 3  # Default safe batch size
    MAX_BATCH_SIZE = 5      # Maximum batch size for safety
    OPTIMAL_BATCH_SIZE = 3  # Recommended batch size for best success rate
    BATCH_DELAY_MINUTES = 180  # 3-hour delay between large batches
    DAILY_ACCOUNT_LIMIT = 15   # Maximum accounts per user per day
    MAX_CONCURRENT_EMULATORS = 5  # Maximum parallel emulators
    
    # Batch Size Recommendations for UI
    BATCH_SIZE_RECOMMENDATIONS = {
        "small": {"size": 3, "delay": "2 hours", "success_rate": "80-90%", "recommended": True},
        "medium": {"size": 5, "delay": "3 hours", "success_rate": "70-80%", "recommended": False},
        "large": {"size": 10, "delay": "6 hours", "success_rate": "60-70%", "recommended": False}
    }
    
    # Anti-Detection Rate Limiting
    ACCOUNT_CREATION_DELAYS = {
        "minimum_delay_seconds": 45,    # Minimum delay between account creations
        "maximum_delay_seconds": 180,   # Maximum delay between account creations
        "batch_completion_delay": 7200, # 2-hour delay after batch completion
        "inter_batch_delay": 10800,     # 3-hour delay between batches
        "daily_cooldown": 86400         # 24-hour daily reset
    }
    
    # Referral system
    REFERRAL_BONUS_PERCENTAGE = 10
    MIN_REFERRAL_AMOUNT = 50
    
    # Snapchat Add Farming Packages
    SERVICE_PACKAGES = {
        "snap_single": ServicePackage(
            id="snap_single",
            name="👻 1 Snapchat Account",
            description="1 Snapchat account = 100 adds guaranteed",
            price_usd=25.00,
            delivery_time_hours=1,
            snapchat_accounts=1,
            features=[
                "100 guaranteed adds per account",
                "Fresh account with warming",
                "Phone + email verified", 
                "Anti-ban protection enabled",
                "Live progress tracking",
                "6-minute setup time"
            ]
        ),
        
        "snap_triple": ServicePackage(
            id="snap_triple",
            name="🔥 3 Snapchat Accounts",
            description="3 Snapchat accounts = 300 adds total",
            price_usd=70.00,
            delivery_time_hours=1,
            snapchat_accounts=3,
            features=[
                "300 total guaranteed adds",
                "3 fresh accounts with warming",
                "All verified and protected",
                "Bulk discount applied",
                "Live progress tracking",
                "Parallel processing"
            ]
        ),
        
        "snap_power": ServicePackage(
            id="snap_power",
            name="💥 5 Snapchat Accounts", 
            description="5 Snapchat accounts = 500 adds total",
            price_usd=110.00,
            delivery_time_hours=2,
            snapchat_accounts=5,
            features=[
                "500 total guaranteed adds",
                "5 fresh accounts with warming",
                "Maximum add farming power",
                "Best value package",
                "Live progress tracking",
                "Priority processing"
            ]
        ),
        
        "snap_domination": ServicePackage(
            id="snap_domination",
            name="🚀 10 Snapchat Accounts",
            description="10 Snapchat accounts = 1000 adds total",
            price_usd=200.00,
            delivery_time_hours=3,
            snapchat_accounts=10,
            features=[
                "1000 total guaranteed adds",
                "10 fresh accounts with warming",
                "Complete domination package",
                "Maximum bulk discount",
                "Live progress tracking",
                "VIP processing priority"
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
👻 **SNAPCHAT ADD FARMING MACHINE** 👻

🔥 **WE DOMINATE THE ADD GAME** 🔥

⚡ **LIGHTNING FAST:** 6-minute account creation
💯 **GUARANTEED:** 100 adds per Snapchat account  
🛡️ **UNDETECTABLE:** Military-grade anti-ban tech
📱 **LIVE TRACKING:** Watch your adds grow in real-time

💸 **PRICING THAT DOMINATES:**
👻 1 Account = 100 Adds = $25
🔥 3 Accounts = 300 Adds = $70  
💥 5 Accounts = 500 Adds = $110
🚀 10 Accounts = 1000 Adds = $200

**COMMANDS:**
🆓 `/snap` - FREE account creation (test our power)
💰 Type number of accounts (1-10) to buy adds
📊 `/status` - Check your active farming
🆘 `/support` - Need help dominating?

⚠️ **WARNING:** Our system is TOO powerful for beginners
Ready to DOMINATE? Type a number 1-10 to start! 🔥
    """
    
    HELP_MESSAGE = """
⚡ **SNAPCHAT DOMINATION COMMANDS** ⚡

🔥 **POWER USER COMMANDS:**
🆓 `/snap` - FREE account creation (prove our dominance)
📊 `/status` - Track your add farming empire
🆘 `/support` - Get elite support NOW

💰 **INSTANT ORDER COMMANDS:**
Just type: `1` `2` `3` `4` `5` `6` `7` `8` `9` `10`
(Number = Snapchat accounts = Your add farming power)

🎯 **WHAT HAPPENS WHEN YOU ORDER:**
1️⃣ Type number (1-10 accounts)
2️⃣ Get crypto payment address
3️⃣ Pay instantly, we detect automatically  
4️⃣ Watch LIVE as we create your accounts
5️⃣ Get 100 adds per account GUARANTEED

⚠️ **ELITE FEATURES:**
🛡️ Military-grade anti-detection
📱 Real-time progress updates
⚡ 6-minute account creation
💯 100% add guarantee
🔄 Auto-payment detection

**Ready to DOMINATE? Type a number NOW!** 🚀
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
def validate_batch_size(account_count: int, user_id: int = None) -> Dict:
    """
    Validate batch size and provide recommendations
    
    Args:
        account_count: Number of accounts requested
        user_id: Optional user ID for daily limit checking
        
    Returns:
        Dict with validation results and recommendations
    """
    result = {
        "valid": True,
        "warnings": [],
        "errors": [],
        "recommendation": None,
        "optimal_size": TelegramBotConfig.OPTIMAL_BATCH_SIZE,
        "estimated_time": None,
        "success_rate": None
    }
    
    # Check maximum limits
    if account_count > TelegramBotConfig.DAILY_ACCOUNT_LIMIT:
        result["valid"] = False
        result["errors"].append(f"Daily limit exceeded. Maximum: {TelegramBotConfig.DAILY_ACCOUNT_LIMIT} accounts")
    
    # Determine batch category and provide recommendations
    if account_count <= 3:
        batch_type = "small"
        result["recommendation"] = TelegramBotConfig.BATCH_SIZE_RECOMMENDATIONS["small"]
        result["estimated_time"] = "45-90 minutes"
        result["success_rate"] = "80-90%"
    elif account_count <= 5:
        batch_type = "medium"
        result["recommendation"] = TelegramBotConfig.BATCH_SIZE_RECOMMENDATIONS["medium"]
        result["estimated_time"] = "2-3 hours"
        result["success_rate"] = "70-80%"
        result["warnings"].append("Medium batch size detected. Consider splitting into smaller batches for higher success rate.")
    else:
        batch_type = "large"
        result["recommendation"] = TelegramBotConfig.BATCH_SIZE_RECOMMENDATIONS["large"]
        result["estimated_time"] = "4-6 hours"
        result["success_rate"] = "60-70%"
        result["warnings"].append("Large batch size detected. HIGH RISK: Consider splitting into multiple small batches.")
        result["warnings"].append(f"Recommended: Split into {(account_count + 2) // 3} batches of 3 accounts each")
    
    # Add anti-detection warnings
    if account_count > TelegramBotConfig.MAX_BATCH_SIZE:
        result["warnings"].append(f"Batch size exceeds recommended maximum of {TelegramBotConfig.MAX_BATCH_SIZE}")
        result["warnings"].append("This increases detection risk significantly")
    
    # Add timing recommendations
    if account_count > 3:
        result["warnings"].append(f"Recommended delay between batches: {TelegramBotConfig.BATCH_DELAY_MINUTES // 60} hours")
    
    return result

def get_batch_recommendations_message(account_count: int) -> str:
    """Generate user-friendly batch recommendations message"""
    validation = validate_batch_size(account_count)
    
    message = f"📊 **BATCH ANALYSIS FOR {account_count} ACCOUNTS** 📊\n\n"
    
    # Success rate and timing
    message += f"⏱️ **Estimated Time**: {validation['estimated_time']}\n"
    message += f"📈 **Success Rate**: {validation['success_rate']}\n\n"
    
    # Recommendations
    if validation["recommendation"]["recommended"]:
        message += "✅ **OPTIMAL BATCH SIZE** ✅\n"
        message += "This batch size is recommended for best results.\n\n"
    else:
        message += "⚠️ **SUBOPTIMAL BATCH SIZE** ⚠️\n"
        message += f"Consider using smaller batches of {validation['optimal_size']} accounts.\n\n"
    
    # Warnings
    if validation["warnings"]:
        message += "🚨 **IMPORTANT WARNINGS** 🚨\n"
        for warning in validation["warnings"]:
            message += f"• {warning}\n"
        message += "\n"
    
    # Errors
    if validation["errors"]:
        message += "❌ **ERRORS** ❌\n"
        for error in validation["errors"]:
            message += f"• {error}\n"
        message += "\n"
    
    return message

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