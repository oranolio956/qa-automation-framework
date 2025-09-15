"""
Telegram Bot Package for Tinder Account Services
Production-ready bot with payment processing, order management, and admin panel
"""

__version__ = "1.0.0"
__author__ = "Tinder Automation Team"

from .main_bot import TinderBotApplication
from .config import TelegramBotConfig
from .database import get_database, get_user_manager, get_order_manager, get_payment_manager
from .customer_service import get_customer_service_manager
from .order_manager import get_order_lifecycle_manager
from .payment_handler import get_payment_processor
from .admin_panel import get_admin_panel_manager

__all__ = [
    'TinderBotApplication',
    'TelegramBotConfig',
    'get_database',
    'get_user_manager',
    'get_order_manager',
    'get_payment_manager',
    'get_customer_service_manager',
    'get_order_lifecycle_manager',
    'get_payment_processor',
    'get_admin_panel_manager'
]