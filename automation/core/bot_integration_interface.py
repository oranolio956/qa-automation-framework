#!/usr/bin/env python3
"""
Bot Integration Interface
Provides standardized interfaces for external bot systems to consume account data
"""

import json
import asyncio
import logging
import hashlib
import hmac
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
import aiohttp
import websockets
from pathlib import Path

from .account_export_system import ExportableAccount, AccountExportSystem, SecurityLevel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class BotIntegrationConfig:
    """Configuration for bot integrations"""
    bot_type: str
    webhook_url: Optional[str] = None
    api_key: Optional[str] = None
    secret_key: Optional[str] = None
    delivery_format: str = "json"
    security_level: str = "sanitized"
    retry_attempts: int = 3
    timeout_seconds: int = 30
    batch_size: int = 10
    rate_limit_per_minute: int = 60

class BaseBotIntegration(ABC):
    """Base class for bot integrations"""
    
    def __init__(self, config: BotIntegrationConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.exporter = AccountExportSystem()
        
    @abstractmethod
    async def deliver_account(self, account: ExportableAccount) -> bool:
        """Deliver single account to bot system"""
        pass
    
    @abstractmethod
    async def deliver_accounts_batch(self, accounts: List[ExportableAccount]) -> Dict[str, Any]:
        """Deliver batch of accounts to bot system"""
        pass
    
    def _generate_signature(self, data: str) -> str:
        """Generate HMAC signature for secure delivery"""
        if not self.config.secret_key:
            return ""
        return hmac.new(
            self.config.secret_key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()

class TelegramBotIntegration(BaseBotIntegration):
    """Telegram bot integration for account delivery"""
    
    async def deliver_account(self, account: ExportableAccount) -> bool:
        """Deliver single account via Telegram bot"""
        try:
            # Format for Telegram delivery
            message = self._format_telegram_message(account)
            
            payload = {
                "method": "sendMessage",
                "chat_id": self.config.webhook_url.split("/")[-1],  # Extract chat ID
                "text": message,
                "parse_mode": "Markdown"
            }
            
            success = await self._send_webhook(payload)
            if success:
                self.logger.info(f"Account {account.username} delivered via Telegram")
            return success
            
        except Exception as e:
            self.logger.error(f"Telegram delivery failed for {account.username}: {e}")
            return False
    
    async def deliver_accounts_batch(self, accounts: List[ExportableAccount]) -> Dict[str, Any]:
        """Deliver batch of accounts via Telegram"""
        results = {
            "total": len(accounts),
            "successful": 0,
            "failed": 0,
            "details": []
        }
        
        # Process in batches to avoid rate limits
        for i in range(0, len(accounts), self.config.batch_size):
            batch = accounts[i:i + self.config.batch_size]
            
            for account in batch:
                success = await self.deliver_account(account)
                if success:
                    results["successful"] += 1
                else:
                    results["failed"] += 1
                
                results["details"].append({
                    "username": account.username,
                    "status": "delivered" if success else "failed"
                })
                
                # Rate limiting
                await asyncio.sleep(60 / self.config.rate_limit_per_minute)
        
        return results
    
    def _format_telegram_message(self, account: ExportableAccount) -> str:
        """Format account for Telegram delivery"""
        sanitized = self.exporter.sanitize_account(
            account, 
            SecurityLevel(self.config.security_level)
        )
        
        trust_emoji = "🟢" if sanitized.trust_score >= 80 else "🟡" if sanitized.trust_score >= 60 else "🔴"
        
        message = f"""
🎯 **New Account Ready**

👤 **Username:** `{sanitized.username}`
📧 **Email:** `{sanitized.email}`
🔐 **Password:** `{sanitized.password}`
📱 **Display Name:** {sanitized.display_name}

✅ **Status:** {sanitized.status}
🔐 **Verification:** {sanitized.verification_status}
{trust_emoji} **Trust Score:** {sanitized.trust_score}/100

🆔 **Snapchat ID:** {sanitized.snapchat_user_id or 'Pending'}
📅 **Created:** {sanitized.registration_time[:10]}
🔑 **Export ID:** `{sanitized.export_id}`

*Account ready for use. Handle with care!*
        """
        return message.strip()
    
    async def _send_webhook(self, payload: Dict) -> bool:
        """Send webhook to Telegram API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.webhook_url,
                    json=payload,
                    timeout=self.config.timeout_seconds
                ) as response:
                    return response.status == 200
        except Exception as e:
            self.logger.error(f"Webhook send failed: {e}")
            return False

class DiscordBotIntegration(BaseBotIntegration):
    """Discord bot integration for account delivery"""
    
    async def deliver_account(self, account: ExportableAccount) -> bool:
        """Deliver single account via Discord webhook"""
        try:
            embed = self._create_discord_embed(account)
            
            payload = {
                "embeds": [embed],
                "username": "Account Creator Bot"
            }
            
            success = await self._send_webhook(payload)
            if success:
                self.logger.info(f"Account {account.username} delivered via Discord")
            return success
            
        except Exception as e:
            self.logger.error(f"Discord delivery failed for {account.username}: {e}")
            return False
    
    async def deliver_accounts_batch(self, accounts: List[ExportableAccount]) -> Dict[str, Any]:
        """Deliver batch of accounts via Discord"""
        results = {
            "total": len(accounts),
            "successful": 0,
            "failed": 0,
            "details": []
        }
        
        # Discord allows up to 10 embeds per message
        for i in range(0, len(accounts), 10):
            batch = accounts[i:i + 10]
            embeds = []
            
            for account in batch:
                embed = self._create_discord_embed(account)
                embeds.append(embed)
            
            payload = {
                "embeds": embeds,
                "username": "Account Creator Bot"
            }
            
            success = await self._send_webhook(payload)
            if success:
                results["successful"] += len(batch)
                for account in batch:
                    results["details"].append({
                        "username": account.username,
                        "status": "delivered"
                    })
            else:
                results["failed"] += len(batch)
                for account in batch:
                    results["details"].append({
                        "username": account.username,
                        "status": "failed"
                    })
            
            # Rate limiting for Discord
            await asyncio.sleep(1)
        
        return results
    
    def _create_discord_embed(self, account: ExportableAccount) -> Dict:
        """Create Discord embed for account"""
        sanitized = self.exporter.sanitize_account(
            account, 
            SecurityLevel(self.config.security_level)
        )
        
        trust_color = 0x00ff00 if sanitized.trust_score >= 80 else 0xffff00 if sanitized.trust_score >= 60 else 0xff0000
        
        embed = {
            "title": "🎯 New Account Ready",
            "color": trust_color,
            "timestamp": datetime.now().isoformat(),
            "fields": [
                {"name": "👤 Username", "value": f"`{sanitized.username}`", "inline": True},
                {"name": "📧 Email", "value": f"`{sanitized.email}`", "inline": True},
                {"name": "🔐 Password", "value": f"`{sanitized.password}`", "inline": True},
                {"name": "📱 Display Name", "value": sanitized.display_name, "inline": True},
                {"name": "✅ Status", "value": sanitized.status, "inline": True},
                {"name": "🏆 Trust Score", "value": f"{sanitized.trust_score}/100", "inline": True},
                {"name": "🆔 Snapchat ID", "value": sanitized.snapchat_user_id or "Pending", "inline": True},
                {"name": "📅 Created", "value": sanitized.registration_time[:10], "inline": True},
                {"name": "🔑 Export ID", "value": f"`{sanitized.export_id}`", "inline": True}
            ],
            "footer": {
                "text": "Handle with care • Account Creator System",
                "icon_url": "https://cdn.discordapp.com/attachments/your-icon-url.png"
            }
        }
        
        return embed
    
    async def _send_webhook(self, payload: Dict) -> bool:
        """Send webhook to Discord"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.webhook_url,
                    json=payload,
                    timeout=self.config.timeout_seconds
                ) as response:
                    return response.status in [200, 204]
        except Exception as e:
            self.logger.error(f"Discord webhook send failed: {e}")
            return False

class WebAPIIntegration(BaseBotIntegration):
    """Generic web API integration for account delivery"""
    
    async def deliver_account(self, account: ExportableAccount) -> bool:
        """Deliver single account via web API"""
        try:
            payload = self._create_api_payload(account)
            
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "TinderBot-AccountCreator/1.0"
            }
            
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"
            
            if self.config.secret_key:
                payload_str = json.dumps(payload, sort_keys=True)
                signature = self._generate_signature(payload_str)
                headers["X-Signature"] = signature
            
            success = await self._send_api_request(payload, headers)
            if success:
                self.logger.info(f"Account {account.username} delivered via Web API")
            return success
            
        except Exception as e:
            self.logger.error(f"Web API delivery failed for {account.username}: {e}")
            return False
    
    async def deliver_accounts_batch(self, accounts: List[ExportableAccount]) -> Dict[str, Any]:
        """Deliver batch of accounts via web API"""
        payload = {
            "batch_delivery": True,
            "timestamp": datetime.now().isoformat(),
            "total_accounts": len(accounts),
            "accounts": []
        }
        
        for account in accounts:
            sanitized = self.exporter.sanitize_account(
                account, 
                SecurityLevel(self.config.security_level)
            )
            payload["accounts"].append(self._account_to_dict(sanitized))
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "TinderBot-AccountCreator/1.0"
        }
        
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        
        if self.config.secret_key:
            payload_str = json.dumps(payload, sort_keys=True)
            signature = self._generate_signature(payload_str)
            headers["X-Signature"] = signature
        
        success = await self._send_api_request(payload, headers)
        
        return {
            "total": len(accounts),
            "successful": len(accounts) if success else 0,
            "failed": 0 if success else len(accounts),
            "batch_delivery": True,
            "api_response": success
        }
    
    def _create_api_payload(self, account: ExportableAccount) -> Dict:
        """Create API payload for single account"""
        sanitized = self.exporter.sanitize_account(
            account, 
            SecurityLevel(self.config.security_level)
        )
        
        return {
            "event": "account_created",
            "timestamp": datetime.now().isoformat(),
            "account": self._account_to_dict(sanitized),
            "metadata": {
                "source": "TinderBot Account Creator",
                "version": "1.0",
                "security_level": self.config.security_level
            }
        }
    
    def _account_to_dict(self, account: ExportableAccount) -> Dict:
        """Convert account to dictionary for API delivery"""
        return {
            "username": account.username,
            "display_name": account.display_name,
            "email": account.email,
            "phone_number": account.phone_number,
            "password": account.password,
            "status": account.status,
            "verification_status": account.verification_status,
            "trust_score": account.trust_score,
            "snapchat_user_id": account.snapchat_user_id,
            "export_id": account.export_id,
            "registration_time": account.registration_time,
            "birth_date": account.birth_date,
            "device_fingerprint": account.device_fingerprint
        }
    
    async def _send_api_request(self, payload: Dict, headers: Dict) -> bool:
        """Send API request with retry logic"""
        for attempt in range(self.config.retry_attempts):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.config.webhook_url,
                        json=payload,
                        headers=headers,
                        timeout=self.config.timeout_seconds
                    ) as response:
                        if response.status in [200, 201, 202]:
                            return True
                        else:
                            self.logger.warning(f"API request attempt {attempt + 1} failed with status {response.status}")
                            
            except Exception as e:
                self.logger.error(f"API request attempt {attempt + 1} failed: {e}")
                
            if attempt < self.config.retry_attempts - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        return False

class WebSocketIntegration(BaseBotIntegration):
    """Real-time WebSocket integration for account delivery"""
    
    def __init__(self, config: BotIntegrationConfig):
        super().__init__(config)
        self.websocket = None
        self.connection_active = False
    
    async def connect(self) -> bool:
        """Establish WebSocket connection"""
        try:
            self.websocket = await websockets.connect(
                self.config.webhook_url,
                timeout=self.config.timeout_seconds
            )
            self.connection_active = True
            self.logger.info("WebSocket connection established")
            return True
        except Exception as e:
            self.logger.error(f"WebSocket connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Close WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            self.connection_active = False
            self.logger.info("WebSocket connection closed")
    
    async def deliver_account(self, account: ExportableAccount) -> bool:
        """Deliver single account via WebSocket"""
        if not self.connection_active:
            if not await self.connect():
                return False
        
        try:
            payload = self._create_websocket_payload(account)
            await self.websocket.send(json.dumps(payload))
            
            # Wait for acknowledgment
            response = await asyncio.wait_for(
                self.websocket.recv(), 
                timeout=5.0
            )
            
            response_data = json.loads(response)
            success = response_data.get("status") == "received"
            
            if success:
                self.logger.info(f"Account {account.username} delivered via WebSocket")
            return success
            
        except Exception as e:
            self.logger.error(f"WebSocket delivery failed for {account.username}: {e}")
            self.connection_active = False
            return False
    
    async def deliver_accounts_batch(self, accounts: List[ExportableAccount]) -> Dict[str, Any]:
        """Deliver batch of accounts via WebSocket"""
        if not self.connection_active:
            if not await self.connect():
                return {"total": len(accounts), "successful": 0, "failed": len(accounts)}
        
        results = {
            "total": len(accounts),
            "successful": 0,
            "failed": 0,
            "details": []
        }
        
        for account in accounts:
            success = await self.deliver_account(account)
            if success:
                results["successful"] += 1
            else:
                results["failed"] += 1
            
            results["details"].append({
                "username": account.username,
                "status": "delivered" if success else "failed"
            })
            
            # Small delay between deliveries
            await asyncio.sleep(0.1)
        
        return results
    
    def _create_websocket_payload(self, account: ExportableAccount) -> Dict:
        """Create WebSocket payload for account"""
        sanitized = self.exporter.sanitize_account(
            account, 
            SecurityLevel(self.config.security_level)
        )
        
        return {
            "type": "account_delivery",
            "timestamp": datetime.now().isoformat(),
            "account": {
                "username": sanitized.username,
                "display_name": sanitized.display_name,
                "email": sanitized.email,
                "password": sanitized.password,
                "status": sanitized.status,
                "trust_score": sanitized.trust_score,
                "snapchat_user_id": sanitized.snapchat_user_id,
                "export_id": sanitized.export_id
            },
            "metadata": {
                "security_level": self.config.security_level,
                "source": "TinderBot Account Creator"
            }
        }

class IntegrationManager:
    """Manager for all bot integrations"""
    
    def __init__(self):
        self.integrations: Dict[str, BaseBotIntegration] = {}
        self.logger = logging.getLogger(__name__)
    
    def add_integration(self, name: str, integration: BaseBotIntegration):
        """Add bot integration"""
        self.integrations[name] = integration
        self.logger.info(f"Integration '{name}' added")
    
    def remove_integration(self, name: str):
        """Remove bot integration"""
        if name in self.integrations:
            del self.integrations[name]
            self.logger.info(f"Integration '{name}' removed")
    
    async def deliver_to_all(self, account: ExportableAccount) -> Dict[str, bool]:
        """Deliver account to all registered integrations"""
        results = {}
        
        tasks = []
        for name, integration in self.integrations.items():
            task = asyncio.create_task(
                integration.deliver_account(account),
                name=name
            )
            tasks.append(task)
        
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, (name, result) in enumerate(zip(self.integrations.keys(), completed_tasks)):
            if isinstance(result, Exception):
                results[name] = False
                self.logger.error(f"Integration '{name}' failed: {result}")
            else:
                results[name] = result
        
        return results
    
    async def deliver_batch_to_all(self, accounts: List[ExportableAccount]) -> Dict[str, Dict]:
        """Deliver account batch to all registered integrations"""
        results = {}
        
        tasks = []
        for name, integration in self.integrations.items():
            task = asyncio.create_task(
                integration.deliver_accounts_batch(accounts),
                name=name
            )
            tasks.append(task)
        
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, (name, result) in enumerate(zip(self.integrations.keys(), completed_tasks)):
            if isinstance(result, Exception):
                results[name] = {
                    "error": str(result),
                    "total": len(accounts),
                    "successful": 0,
                    "failed": len(accounts)
                }
                self.logger.error(f"Batch integration '{name}' failed: {result}")
            else:
                results[name] = result
        
        return results

# Factory functions for quick integration setup
def create_telegram_integration(webhook_url: str, security_level: str = "sanitized") -> TelegramBotIntegration:
    """Create Telegram bot integration"""
    config = BotIntegrationConfig(
        bot_type="telegram",
        webhook_url=webhook_url,
        security_level=security_level,
        rate_limit_per_minute=20  # Telegram rate limit
    )
    return TelegramBotIntegration(config)

def create_discord_integration(webhook_url: str, security_level: str = "sanitized") -> DiscordBotIntegration:
    """Create Discord bot integration"""
    config = BotIntegrationConfig(
        bot_type="discord",
        webhook_url=webhook_url,
        security_level=security_level,
        rate_limit_per_minute=50  # Discord rate limit
    )
    return DiscordBotIntegration(config)

def create_api_integration(api_url: str, api_key: str = None, secret_key: str = None, 
                          security_level: str = "sanitized") -> WebAPIIntegration:
    """Create Web API integration"""
    config = BotIntegrationConfig(
        bot_type="web_api",
        webhook_url=api_url,
        api_key=api_key,
        secret_key=secret_key,
        security_level=security_level
    )
    return WebAPIIntegration(config)

def create_websocket_integration(ws_url: str, security_level: str = "sanitized") -> WebSocketIntegration:
    """Create WebSocket integration"""
    config = BotIntegrationConfig(
        bot_type="websocket",
        webhook_url=ws_url,
        security_level=security_level
    )
    return WebSocketIntegration(config)

# Example usage
if __name__ == "__main__":
    async def test_integrations():
        # Create test account
        test_account = ExportableAccount(
            username="test_user",
            display_name="Test User",
            email="test@example.com",
            phone_number="+1234567890",
            birth_date="1995-01-01",
            password="TestPass123!",
            first_name="Test",
            last_name="User",
            status="ACTIVE",
            verification_status="VERIFIED",
            trust_score=85
        )
        
        # Create integration manager
        manager = IntegrationManager()
        
        # Add integrations (with example URLs - replace with real ones)
        telegram_bot = create_telegram_integration("https://api.telegram.org/bot<token>/sendMessage")
        discord_bot = create_discord_integration("https://discord.com/api/webhooks/your-webhook")
        api_integration = create_api_integration("https://your-api.com/accounts", api_key="your-key")
        
        manager.add_integration("telegram", telegram_bot)
        manager.add_integration("discord", discord_bot)
        manager.add_integration("api", api_integration)
        
        # Test single account delivery
        print("Testing single account delivery...")
        results = await manager.deliver_to_all(test_account)
        print(f"Delivery results: {results}")
        
        # Test batch delivery
        print("Testing batch delivery...")
        batch_results = await manager.deliver_batch_to_all([test_account])
        print(f"Batch delivery results: {batch_results}")
    
    # Run test
    # asyncio.run(test_integrations())
    print("Bot integration interface loaded successfully!")