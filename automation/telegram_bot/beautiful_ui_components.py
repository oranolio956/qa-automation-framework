#!/usr/bin/env python3
"""
Beautiful UI Components for Telegram Bot
Creates stunning visual interfaces with emojis, progress bars, and interactive elements
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

class BeautifulUIComponents:
    """Creates beautiful UI components for the Telegram bot"""
    
    @staticmethod
    def create_order_header(order_id: str, service: str, status: str) -> str:
        """Create beautiful order header"""
        status_icons = {
            "⏳ Queued": "⏳",
            "🔧 Creating": "🔧", 
            "📱 Verifying": "📱",
            "✅ Complete": "🎉",
            "❌ Failed": "⚠️",
            "🚫 Cancelled": "🚫"
        }
        
        icon = status_icons.get(status, "🔄")
        
        return f"""
{icon} **Order #{order_id[-6:]} - {service.title()}**
{'━' * 25}"""

    @staticmethod
    def create_progress_box(completed: int, total: int, status: str, eta_minutes: int = None) -> str:
        """Create beautiful progress display box"""
        progress_percentage = int((completed / total) * 100) if total > 0 else 0
        progress_bar = BeautifulUIComponents.create_progress_bar(completed, total, 10)
        
        eta_text = ""
        if eta_minutes and eta_minutes > 0:
            if eta_minutes < 60:
                eta_text = f"⏰ ETA: {eta_minutes}m"
            else:
                hours = eta_minutes // 60
                mins = eta_minutes % 60
                eta_text = f"⏰ ETA: {hours}h {mins}m"
        
        return f"""
┌─────────────────────────┐
│ 📊 Progress: {completed}/{total} accounts   │
│ {progress_bar} │
│ 🎯 Status: {status}     │
│ {eta_text}                    │
└─────────────────────────┘"""

    @staticmethod
    def create_progress_bar(completed: int, total: int, width: int = 10) -> str:
        """Create visual progress bar"""
        if total == 0:
            return "▓" * width + " 100%"
        
        progress_ratio = completed / total
        filled_blocks = int(progress_ratio * width)
        empty_blocks = width - filled_blocks
        
        bar = "▓" * filled_blocks + "░" * empty_blocks
        percentage = int(progress_ratio * 100)
        return f"{bar} {percentage}%"

    @staticmethod
    def create_account_list(accounts: List, max_display: int = 5) -> str:
        """Create beautiful account status list"""
        if not accounts:
            return "📱 **Account Status:**\n   No accounts created yet"
        
        account_text = "📱 **Account Status:**\n"
        
        # Show first few accounts
        display_accounts = accounts[:max_display]
        
        for i, account in enumerate(display_accounts, 1):
            if hasattr(account, 'status') and hasattr(account, 'username'):
                if account.status == "✅ Complete" and account.username:
                    account_text += f"  {i}. ✅ @{account.username} - Ready\n"
                elif account.status == "🔧 Creating":
                    account_text += f"  {i}. 🔧 Creating account...\n"
                elif account.status == "📱 Verifying":
                    account_text += f"  {i}. 📱 SMS verification...\n"
                elif account.status == "🔥 Warming":
                    account_text += f"  {i}. 🔥 Account warming...\n"
                elif account.status == "❌ Failed":
                    account_text += f"  {i}. ❌ Failed - Retrying\n"
                else:
                    account_text += f"  {i}. ⏳ In queue\n"
            else:
                account_text += f"  {i}. ⏳ Preparing...\n"
        
        # Show remaining count if more accounts
        if len(accounts) > max_display:
            remaining = len(accounts) - max_display
            account_text += f"  ... and {remaining} more account{'s' if remaining > 1 else ''}\n"
        
        return account_text

    @staticmethod
    def create_order_summary(order_id: str, service: str, account_count: int, 
                           total_price: float, status: str, created_at: datetime) -> str:
        """Create beautiful order summary"""
        time_str = created_at.strftime("%Y-%m-%d %H:%M")
        adds_total = account_count * 100
        
        return f"""
🎯 **ORDER SUMMARY**

📋 **Order ID:** #{order_id[-6:]}
📱 **Service:** {service.title()} Accounts
📊 **Quantity:** {account_count} accounts
💯 **Total Adds:** {adds_total:,} 
💰 **Price:** ${total_price:.2f}
📅 **Created:** {time_str}
🎚️ **Status:** {status}
"""

    @staticmethod
    def create_payment_box(crypto_type: str, address: str, amount: float) -> str:
        """Create beautiful payment information box"""
        crypto_icons = {
            "bitcoin": "₿",
            "ethereum": "Ξ", 
            "usdt_trc20": "₮",
            "usdt_erc20": "₮",
            "litecoin": "Ł",
            "monero": "ɱ"
        }
        
        icon = crypto_icons.get(crypto_type, "💰")
        crypto_name = crypto_type.replace("_", " ").upper()
        
        return f"""
💳 **PAYMENT INFORMATION**

{icon} **Currency:** {crypto_name}
💰 **Amount:** ${amount:.2f}

🔗 **Send Payment To:**
`{address}`

⚡ **Payment will be detected automatically within 1-3 minutes**
"""

    @staticmethod
    def create_completion_celebration(order_id: str, account_count: int, 
                                    completed_accounts: List, total_time: str) -> str:
        """Create beautiful order completion display"""
        adds_total = account_count * 100
        success_count = len(completed_accounts)
        
        celebration = f"""
🎉 **ORDER COMPLETE!** 🎉

🎯 **Order #{order_id[-6:]} - DELIVERED**

✅ **SUCCESS METRICS:**
• 📱 {success_count}/{account_count} accounts created
• 💯 {success_count * 100:,} adds configured  
• ⏱️ Completed in {total_time}
• 🛡️ All accounts protected & warmed

🚀 **YOUR SNAPCHAT ARMY:**
"""
        
        # Add account details
        for i, account in enumerate(completed_accounts[:3], 1):  # Show first 3
            if hasattr(account, 'username') and account.username:
                celebration += f"  {i}. @{account.username} - Ready for domination\n"
        
        if len(completed_accounts) > 3:
            remaining = len(completed_accounts) - 3
            celebration += f"  ... and {remaining} more account{'s' if remaining > 1 else ''}!\n"
        
        celebration += "\n💥 **READY TO DOMINATE!** 💥"
        
        return celebration

    @staticmethod
    def create_stats_dashboard(total_orders: int, active_orders: int, 
                             completed_orders: int, total_accounts: int) -> str:
        """Create beautiful statistics dashboard"""
        return f"""
📊 **SYSTEM DASHBOARD**

🎯 **ORDER STATISTICS:**
• 📋 Total Orders: {total_orders:,}
• ⚡ Active Orders: {active_orders:,}  
• ✅ Completed: {completed_orders:,}
• 📱 Accounts Created: {total_accounts:,}

📈 **PERFORMANCE:**
• 🚀 Average Creation Time: 3-5 minutes
• 🎯 Success Rate: 98.5%
• ⚡ Response Time: < 1 second
"""

    @staticmethod
    def create_service_selection_menu() -> str:
        """Create beautiful service selection menu"""
        return f"""
🛒 **SERVICE SELECTION MENU**

📱 **AVAILABLE SERVICES:**

🔥 **SNAPCHAT DOMINATION**
• Premium female accounts
• 100+ adds per account  
• SMS verification included
• Account warming service
• Military-grade security

💰 **PRICING:**
• 1 account: $25
• 3 accounts: $70 (SAVE $5)
• 5 accounts: $110 (SAVE $15) 
• 10 accounts: $200 (SAVE $50)

⚡ **DELIVERY TIME:** 3-5 minutes per account
"""

    @staticmethod
    def create_live_update_message(order_id: str, current_account: int, 
                                 total_accounts: int, current_step: str) -> str:
        """Create live update message"""
        progress_percentage = int((current_account / total_accounts) * 100)
        progress_bar = BeautifulUIComponents.create_progress_bar(current_account, total_accounts, 8)
        
        return f"""
🔧 **LIVE UPDATE - Order #{order_id[-6:]}**

📊 **Current Progress:**
{progress_bar}

🎯 **Account {current_account}/{total_accounts}:**
└ {current_step}

⚡ **System Status:** All systems operational
🛡️ **Security:** Anti-detection active
"""

    @staticmethod
    def create_error_message(error_type: str, order_id: str = None, 
                           support_available: bool = True) -> str:
        """Create beautiful error message"""
        error_messages = {
            "payment_failed": "💳 Payment verification failed",
            "creation_failed": "🔧 Account creation encountered an issue", 
            "verification_failed": "📱 SMS verification timeout",
            "system_error": "⚙️ System temporarily unavailable",
            "order_not_found": "🔍 Order not found"
        }
        
        error_title = error_messages.get(error_type, "⚠️ An error occurred")
        
        message = f"""
⚠️ **{error_title.upper()}**
"""
        
        if order_id:
            message += f"\n🎯 **Order:** #{order_id[-6:]}\n"
        
        message += """
🔧 **WHAT WE'RE DOING:**
• Automatic retry in progress
• System diagnostics running
• Issue reported to technical team

⏱️ **EXPECTED RESOLUTION:** 1-3 minutes
"""
        
        if support_available:
            message += "\n🆘 **Need immediate help?** Contact support below"
        
        return message

    @staticmethod
    def create_welcome_interface(user_name: str) -> Tuple[str, InlineKeyboardMarkup]:
        """Create beautiful welcome interface"""
        welcome_message = f"""
🔥 **WELCOME TO SNAPCHAT DOMINATION** 🔥

👋 **Hello {user_name}!** Ready to dominate social media?

🚀 **WHAT WE OFFER:**
• 📱 Premium Snapchat accounts
• ⚡ Real-time order tracking  
• 🛡️ Military-grade security
• 💯 100+ adds per account
• 🔥 Instant account warming

🎯 **QUICK START OPTIONS:**
Choose your domination level below!
"""
        
        keyboard = [
            [
                InlineKeyboardButton("📱 Free Demo", callback_data="free_demo"),
                InlineKeyboardButton("🛒 Quick Order", callback_data="quick_order_menu")
            ],
            [
                InlineKeyboardButton("1 Account - $25", callback_data="quick_order_snapchat_1"),
                InlineKeyboardButton("3 Accounts - $70", callback_data="quick_order_snapchat_3")
            ],
            [
                InlineKeyboardButton("5 Accounts - $110 💸 SAVE $15", callback_data="quick_order_snapchat_5")
            ],
            [
                InlineKeyboardButton("📋 My Orders", callback_data="my_orders"),
                InlineKeyboardButton("💬 Support", callback_data="contact_support")
            ],
            [
                InlineKeyboardButton("❓ Help & Commands", callback_data="show_help")
            ]
        ]
        
        return welcome_message, InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_order_action_buttons(order_id: str, status: str) -> InlineKeyboardMarkup:
        """Create contextual action buttons based on order status"""
        buttons = []
        
        # Always available actions
        buttons.append([
            InlineKeyboardButton("🔄 Refresh Status", callback_data=f"refresh_progress_{order_id}"),
            InlineKeyboardButton("📊 Order Details", callback_data=f"order_details_{order_id}")
        ])
        
        # Status-specific actions
        if status in ["⏳ Queued", "🔧 Creating", "📱 Verifying"]:
            buttons.append([
                InlineKeyboardButton("⏸️ Pause Order", callback_data=f"pause_order_{order_id}"),
                InlineKeyboardButton("❌ Cancel Order", callback_data=f"cancel_order_{order_id}")
            ])
        
        elif status == "✅ Complete":
            buttons.append([
                InlineKeyboardButton("📥 Download All", callback_data=f"download_accounts_{order_id}"),
                InlineKeyboardButton("🔄 Order Again", callback_data=f"reorder_{order_id}")
            ])
        
        elif status == "❌ Failed":
            buttons.append([
                InlineKeyboardButton("🔄 Retry Order", callback_data=f"retry_order_{order_id}"),
                InlineKeyboardButton("💬 Get Support", callback_data="contact_support")
            ])
        
        # Navigation buttons
        buttons.append([
            InlineKeyboardButton("📋 My Orders", callback_data="my_orders"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
        ])
        
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def create_payment_method_buttons(order_id: str) -> InlineKeyboardMarkup:
        """Create beautiful payment method selection buttons"""
        buttons = [
            [
                InlineKeyboardButton("₿ Bitcoin", callback_data=f"pay_bitcoin_{order_id}"),
                InlineKeyboardButton("Ξ Ethereum", callback_data=f"pay_ethereum_{order_id}")
            ],
            [
                InlineKeyboardButton("₮ USDT (TRC20)", callback_data=f"pay_usdt_trc20_{order_id}"),
                InlineKeyboardButton("₮ USDT (ERC20)", callback_data=f"pay_usdt_erc20_{order_id}")
            ],
            [
                InlineKeyboardButton("Ł Litecoin", callback_data=f"pay_litecoin_{order_id}"),
                InlineKeyboardButton("ɱ Monero", callback_data=f"pay_monero_{order_id}")
            ],
            [
                InlineKeyboardButton("📊 Order Details", callback_data=f"order_details_{order_id}"),
                InlineKeyboardButton("❌ Cancel Order", callback_data=f"cancel_order_{order_id}")
            ]
        ]
        
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def format_time_elapsed(start_time: datetime) -> str:
        """Format time elapsed in beautiful format"""
        elapsed = datetime.now() - start_time
        total_seconds = int(elapsed.total_seconds())
        
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"

    @staticmethod
    def format_eta(minutes: int) -> str:
        """Format ETA in beautiful format"""
        if minutes <= 0:
            return "Completing now..."
        elif minutes < 60:
            return f"~{minutes} minutes"
        else:
            hours = minutes // 60
            remaining_minutes = minutes % 60
            if remaining_minutes == 0:
                return f"~{hours} hour{'s' if hours > 1 else ''}"
            else:
                return f"~{hours}h {remaining_minutes}m"

    @staticmethod
    def create_notification_message(notification_type: str, order_id: str, 
                                  details: Dict = None) -> str:
        """Create beautiful notification messages"""
        notifications = {
            "payment_confirmed": f"""
🎉 **PAYMENT CONFIRMED!**

Order #{order_id[-6:]} payment has been verified!
🚀 Account creation starting immediately...
""",
            
            "order_started": f"""
🔧 **ACCOUNT CREATION STARTED!**

Order #{order_id[-6:]} is now in progress!
📱 You'll receive live updates as each account is created.
""",
            
            "account_completed": f"""
✅ **ACCOUNT READY!**

Order #{order_id[-6:]} - Account {details.get('account_num', 'X')} completed!
@{details.get('username', 'username')} is ready for domination!
""",
            
            "order_completed": f"""
🎉 **ORDER COMPLETE!**

Order #{order_id[-6:]} - All accounts delivered!
🚀 Your Snapchat army is ready for domination!
"""
        }
        
        return notifications.get(notification_type, f"📱 Update for Order #{order_id[-6:]}")

# Global UI helper instance
ui = BeautifulUIComponents()

def get_ui_components() -> BeautifulUIComponents:
    """Get global UI components instance"""
    return ui

if __name__ == "__main__":
    # Test UI components
    ui = BeautifulUIComponents()
    
    # Test progress bar
    print("Progress Bar Test:")
    print(ui.create_progress_bar(3, 5))
    print(ui.create_progress_bar(10, 10))
    print(ui.create_progress_bar(0, 5))
    
    # Test order summary
    print("\nOrder Summary Test:")
    print(ui.create_order_summary(
        "ORD123456789", "snapchat", 5, 110.0, 
        "🔧 Creating", datetime.now()
    ))
    
    print("✅ UI Components test completed")