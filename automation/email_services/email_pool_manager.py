#!/usr/bin/env python3
"""
Email Pool Management System
Production-ready email pool with lifecycle management, rotation, and compliance
"""

import os
import time
import random
import logging
import json
import asyncio
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import redis
from collections import defaultdict, deque
import hashlib

# Import email services
from .temp_email_services import EmailAccount, EmailProviderType, get_email_service_manager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmailPoolStatus(Enum):
    AVAILABLE = "available"
    IN_USE = "in_use"
    EXPIRED = "expired"
    BLACKLISTED = "blacklisted"
    RATE_LIMITED = "rate_limited"

@dataclass
class EmailPoolEntry:
    """Email pool entry with metadata"""
    account: EmailAccount
    status: EmailPoolStatus
    usage_count: int = 0
    last_used: Optional[datetime] = None
    assigned_to: Optional[str] = None  # Service/user using this email
    blacklist_reason: Optional[str] = None
    rate_limit_reset: Optional[datetime] = None
    success_rate: float = 1.0
    total_attempts: int = 0
    successful_attempts: int = 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            'email': self.account.email,
            'provider': self.account.provider.value,
            'status': self.status.value,
            'usage_count': self.usage_count,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'assigned_to': self.assigned_to,
            'blacklist_reason': self.blacklist_reason,
            'rate_limit_reset': self.rate_limit_reset.isoformat() if self.rate_limit_reset else None,
            'success_rate': self.success_rate,
            'total_attempts': self.total_attempts,
            'successful_attempts': self.successful_attempts,
            'created_at': self.account.created_at.isoformat(),
            'expires_at': self.account.expires_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'EmailPoolEntry':
        """Create from dictionary"""
        account = EmailAccount(
            email=data['email'],
            provider=EmailProviderType(data['provider']),
            created_at=datetime.fromisoformat(data['created_at']),
            expires_at=datetime.fromisoformat(data['expires_at'])
        )
        
        entry = cls(
            account=account,
            status=EmailPoolStatus(data['status']),
            usage_count=data['usage_count'],
            assigned_to=data.get('assigned_to'),
            blacklist_reason=data.get('blacklist_reason'),
            success_rate=data['success_rate'],
            total_attempts=data['total_attempts'],
            successful_attempts=data['successful_attempts']
        )
        
        if data.get('last_used'):
            entry.last_used = datetime.fromisoformat(data['last_used'])
        if data.get('rate_limit_reset'):
            entry.rate_limit_reset = datetime.fromisoformat(data['rate_limit_reset'])
            
        return entry

class RateLimitTracker:
    """Track rate limits across domains and services"""
    
    def __init__(self):
        self.domain_limits = defaultdict(deque)  # Domain -> timestamps
        self.service_limits = defaultdict(deque)  # Service -> timestamps
        self.global_limits = deque()  # Global rate limits
        
        # Rate limit configurations
        self.DOMAIN_LIMIT = 40  # 40 emails per day per domain
        self.SERVICE_LIMIT = 120  # 120 emails per day per service
        self.GLOBAL_LIMIT = 1000  # 1000 emails per day globally
        self.WINDOW_HOURS = 24
    
    def can_use_domain(self, domain: str) -> bool:
        """Check if domain is within rate limits"""
        now = time.time()
        domain_times = self.domain_limits[domain]
        
        # Remove old entries
        cutoff = now - (self.WINDOW_HOURS * 3600)
        while domain_times and domain_times[0] < cutoff:
            domain_times.popleft()
        
        return len(domain_times) < self.DOMAIN_LIMIT
    
    def can_use_service(self, service: str) -> bool:
        """Check if service is within rate limits"""
        now = time.time()
        service_times = self.service_limits[service]
        
        # Remove old entries
        cutoff = now - (self.WINDOW_HOURS * 3600)
        while service_times and service_times[0] < cutoff:
            service_times.popleft()
        
        return len(service_times) < self.SERVICE_LIMIT
    
    def can_use_global(self) -> bool:
        """Check global rate limits"""
        now = time.time()
        
        # Remove old entries
        cutoff = now - (self.WINDOW_HOURS * 3600)
        while self.global_limits and self.global_limits[0] < cutoff:
            self.global_limits.popleft()
        
        return len(self.global_limits) < self.GLOBAL_LIMIT
    
    def record_usage(self, email: str, service: str):
        """Record email usage for rate limiting"""
        now = time.time()
        domain = email.split('@')[1] if '@' in email else 'unknown'
        
        self.domain_limits[domain].append(now)
        self.service_limits[service].append(now)
        self.global_limits.append(now)
    
    def get_reset_time(self, email: str, service: str) -> Optional[datetime]:
        """Get when rate limits reset"""
        domain = email.split('@')[1] if '@' in email else 'unknown'
        now = time.time()
        
        # Find earliest reset time
        reset_times = []
        
        if self.domain_limits[domain]:
            oldest_domain = self.domain_limits[domain][0]
            reset_times.append(oldest_domain + (self.WINDOW_HOURS * 3600))
        
        if self.service_limits[service]:
            oldest_service = self.service_limits[service][0]
            reset_times.append(oldest_service + (self.WINDOW_HOURS * 3600))
        
        if self.global_limits:
            oldest_global = self.global_limits[0]
            reset_times.append(oldest_global + (self.WINDOW_HOURS * 3600))
        
        if reset_times:
            return datetime.fromtimestamp(min(reset_times))
        
        return None

class DeliverabilityTracker:
    """Track email deliverability and spam rates"""
    
    def __init__(self):
        self.provider_stats = defaultdict(lambda: {
            'sent': 0,
            'delivered': 0,
            'bounced': 0,
            'spam': 0,
            'success_rate': 1.0,
            'last_updated': datetime.now()
        })
        
        self.domain_reputation = defaultdict(lambda: {
            'score': 100,  # Start with perfect score
            'messages_sent': 0,
            'spam_reports': 0,
            'bounce_rate': 0.0
        })
    
    def record_delivery(self, email: str, provider: EmailProviderType, success: bool, 
                       is_spam: bool = False, bounced: bool = False):
        """Record email delivery result"""
        provider_key = provider.value
        domain = email.split('@')[1] if '@' in email else 'unknown'
        
        # Update provider stats
        stats = self.provider_stats[provider_key]
        stats['sent'] += 1
        
        if success:
            stats['delivered'] += 1
        if bounced:
            stats['bounced'] += 1
        if is_spam:
            stats['spam'] += 1
            
        # Calculate success rate
        if stats['sent'] > 0:
            stats['success_rate'] = stats['delivered'] / stats['sent']
        
        stats['last_updated'] = datetime.now()
        
        # Update domain reputation
        domain_rep = self.domain_reputation[domain]
        domain_rep['messages_sent'] += 1
        
        if is_spam:
            domain_rep['spam_reports'] += 1
        if bounced:
            domain_rep['bounce_rate'] = (domain_rep.get('bounces', 0) + 1) / domain_rep['messages_sent']
            domain_rep['bounces'] = domain_rep.get('bounces', 0) + 1
        
        # Calculate reputation score (0-100)
        spam_rate = domain_rep['spam_reports'] / domain_rep['messages_sent']
        bounce_rate = domain_rep['bounce_rate']
        
        # Score formula: penalize spam and bounces heavily
        domain_rep['score'] = max(0, 100 - (spam_rate * 50) - (bounce_rate * 30))
    
    def get_provider_reputation(self, provider: EmailProviderType) -> Dict:
        """Get provider reputation metrics"""
        return dict(self.provider_stats[provider.value])
    
    def get_domain_reputation(self, domain: str) -> Dict:
        """Get domain reputation metrics"""
        return dict(self.domain_reputation[domain])
    
    def is_provider_healthy(self, provider: EmailProviderType, min_success_rate: float = 0.7) -> bool:
        """Check if provider is healthy for use"""
        stats = self.provider_stats[provider.value]
        return stats['success_rate'] >= min_success_rate and stats['sent'] > 0

class EmailPoolManager:
    """Main email pool management system"""
    
    def __init__(self, redis_config: Dict = None, pool_config: Dict = None):
        self.redis_config = redis_config or {'host': 'localhost', 'port': 6379, 'db': 2}
        self.pool_config = pool_config or {}
        
        # Initialize Redis connection
        self.redis_client = redis.Redis(**self.redis_config)
        
        # Initialize components
        self.email_service = get_email_service_manager()
        self.rate_limiter = RateLimitTracker()
        self.deliverability = DeliverabilityTracker()
        
        # Pool configuration
        self.MIN_POOL_SIZE = self.pool_config.get('min_pool_size', 20)
        self.MAX_POOL_SIZE = self.pool_config.get('max_pool_size', 100)
        self.REFILL_THRESHOLD = self.pool_config.get('refill_threshold', 5)
        self.MAX_USAGE_PER_EMAIL = self.pool_config.get('max_usage_per_email', 3)
        
        # Redis keys
        self.POOL_KEY = "email_pool"
        self.STATS_KEY = "email_pool_stats"
        self.RATE_LIMIT_KEY = "email_rate_limits"
        
        logger.info(f"Email Pool Manager initialized (min: {self.MIN_POOL_SIZE}, max: {self.MAX_POOL_SIZE})")
    
    async def initialize_pool(self, initial_size: int = None) -> bool:
        """Initialize email pool with accounts"""
        try:
            target_size = initial_size or self.MIN_POOL_SIZE
            current_size = await self.get_pool_size()
            
            if current_size >= target_size:
                logger.info(f"Pool already has {current_size} accounts")
                return True
            
            accounts_to_create = target_size - current_size
            logger.info(f"Creating {accounts_to_create} email accounts for pool...")
            
            created = 0
            failed = 0
            
            # Create accounts across different providers for diversity
            providers = list(EmailProviderType)
            
            for i in range(accounts_to_create):
                try:
                    # Rotate providers for diversity
                    provider = providers[i % len(providers)]
                    account = await self.email_service.create_email_account(provider)
                    
                    # Add to pool
                    pool_entry = EmailPoolEntry(
                        account=account,
                        status=EmailPoolStatus.AVAILABLE
                    )
                    
                    await self._add_to_pool(pool_entry)
                    created += 1
                    
                    # Small delay between creations to avoid rate limits
                    await asyncio.sleep(random.uniform(1, 3))
                    
                except Exception as e:
                    logger.error(f"Failed to create email account {i+1}: {e}")
                    failed += 1
                    
                    if failed > accounts_to_create * 0.5:  # Stop if >50% failures
                        logger.error("Too many failures, stopping pool initialization")
                        break
            
            logger.info(f"Pool initialization complete: {created} created, {failed} failed")
            return created > 0
            
        except Exception as e:
            logger.error(f"Pool initialization failed: {e}")
            return False
    
    async def get_email_account(self, service: str, purpose: str = None) -> Optional[EmailAccount]:
        """Get available email account from pool"""
        try:
            # Check global rate limits
            if not self.rate_limiter.can_use_global():
                logger.warning("Global rate limit reached")
                return None
            
            if not self.rate_limiter.can_use_service(service):
                logger.warning(f"Service {service} rate limit reached")
                return None
            
            # Get available accounts
            available_accounts = await self._get_available_accounts()
            
            if not available_accounts:
                logger.warning("No available accounts in pool")
                # Try to refill pool
                await self._refill_pool()
                available_accounts = await self._get_available_accounts()
                
                if not available_accounts:
                    return None
            
            # Select best account based on criteria
            best_account = self._select_best_account(available_accounts, service)
            
            if best_account:
                # Mark as in use
                best_account.status = EmailPoolStatus.IN_USE
                best_account.assigned_to = service
                best_account.last_used = datetime.now()
                best_account.usage_count += 1
                
                await self._update_pool_entry(best_account)
                
                # Record rate limit usage
                self.rate_limiter.record_usage(best_account.account.email, service)
                
                logger.info(f"Assigned email {best_account.account.email} to {service}")
                return best_account.account
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get email account: {e}")
            return None
    
    async def return_email_account(self, email: str, success: bool = True, 
                                 spam_reported: bool = False, bounced: bool = False) -> bool:
        """Return email account to pool"""
        try:
            pool_entry = await self._get_pool_entry(email)
            
            if not pool_entry:
                logger.warning(f"Email {email} not found in pool")
                return False
            
            # Update success metrics
            pool_entry.total_attempts += 1
            if success:
                pool_entry.successful_attempts += 1
            
            # Calculate success rate
            pool_entry.success_rate = pool_entry.successful_attempts / pool_entry.total_attempts
            
            # Record deliverability
            self.deliverability.record_delivery(
                email, 
                pool_entry.account.provider, 
                success, 
                spam_reported, 
                bounced
            )
            
            # Determine new status
            if spam_reported or bounced:
                pool_entry.status = EmailPoolStatus.BLACKLISTED
                pool_entry.blacklist_reason = "spam_reported" if spam_reported else "bounced"
                logger.warning(f"Blacklisted email {email}: {pool_entry.blacklist_reason}")
            elif pool_entry.usage_count >= self.MAX_USAGE_PER_EMAIL:
                pool_entry.status = EmailPoolStatus.EXPIRED
                logger.info(f"Email {email} expired after {pool_entry.usage_count} uses")
            elif pool_entry.success_rate < 0.5:  # Low success rate
                pool_entry.status = EmailPoolStatus.BLACKLISTED
                pool_entry.blacklist_reason = "low_success_rate"
                logger.warning(f"Blacklisted email {email} due to low success rate: {pool_entry.success_rate}")
            else:
                pool_entry.status = EmailPoolStatus.AVAILABLE
                pool_entry.assigned_to = None
            
            await self._update_pool_entry(pool_entry)
            
            # Trigger refill if needed
            if await self.get_available_count() < self.REFILL_THRESHOLD:
                asyncio.create_task(self._refill_pool())
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to return email account {email}: {e}")
            return False
    
    def _select_best_account(self, accounts: List[EmailPoolEntry], service: str) -> Optional[EmailPoolEntry]:
        """Select best email account based on criteria"""
        if not accounts:
            return None
        
        # Score accounts based on multiple criteria
        scored_accounts = []
        
        for entry in accounts:
            score = 0
            
            # Prefer accounts with fewer uses
            usage_score = max(0, 10 - entry.usage_count)
            score += usage_score * 3
            
            # Prefer accounts with higher success rates
            score += entry.success_rate * 5
            
            # Prefer accounts from providers with good reputation
            provider_rep = self.deliverability.get_provider_reputation(entry.account.provider)
            score += provider_rep.get('success_rate', 1.0) * 2
            
            # Check domain rate limits
            domain = entry.account.email.split('@')[1]
            if self.rate_limiter.can_use_domain(domain):
                score += 5
            else:
                score -= 10  # Heavy penalty for rate-limited domains
            
            # Prefer newer accounts (less likely to be flagged)
            account_age_hours = (datetime.now() - entry.account.created_at).total_seconds() / 3600
            if account_age_hours < 1:  # Very fresh
                score += 3
            elif account_age_hours < 6:  # Fresh
                score += 1
            elif account_age_hours > 24:  # Old
                score -= 2
            
            scored_accounts.append((score, entry))
        
        # Sort by score (highest first) and return best
        scored_accounts.sort(key=lambda x: x[0], reverse=True)
        return scored_accounts[0][1] if scored_accounts[0][0] > 0 else None
    
    async def _get_available_accounts(self) -> List[EmailPoolEntry]:
        """Get all available accounts from pool"""
        try:
            pool_data = self.redis_client.hgetall(self.POOL_KEY)
            available_accounts = []
            
            for email_bytes, data_bytes in pool_data.items():
                try:
                    email = email_bytes.decode()
                    data = json.loads(data_bytes.decode())
                    entry = EmailPoolEntry.from_dict(data)
                    
                    # Check if account is truly available
                    if (entry.status == EmailPoolStatus.AVAILABLE and
                        datetime.now() < entry.account.expires_at and
                        (not entry.rate_limit_reset or datetime.now() > entry.rate_limit_reset)):
                        available_accounts.append(entry)
                        
                except Exception as e:
                    logger.warning(f"Failed to parse pool entry: {e}")
                    continue
            
            return available_accounts
            
        except Exception as e:
            logger.error(f"Failed to get available accounts: {e}")
            return []
    
    async def _add_to_pool(self, pool_entry: EmailPoolEntry):
        """Add email account to pool"""
        try:
            email = pool_entry.account.email
            data = json.dumps(pool_entry.to_dict())
            
            self.redis_client.hset(self.POOL_KEY, email, data)
            logger.debug(f"Added {email} to pool")
            
        except Exception as e:
            logger.error(f"Failed to add account to pool: {e}")
    
    async def _update_pool_entry(self, pool_entry: EmailPoolEntry):
        """Update existing pool entry"""
        try:
            email = pool_entry.account.email
            data = json.dumps(pool_entry.to_dict())
            
            self.redis_client.hset(self.POOL_KEY, email, data)
            logger.debug(f"Updated pool entry for {email}")
            
        except Exception as e:
            logger.error(f"Failed to update pool entry: {e}")
    
    async def _get_pool_entry(self, email: str) -> Optional[EmailPoolEntry]:
        """Get pool entry by email"""
        try:
            data_bytes = self.redis_client.hget(self.POOL_KEY, email)
            
            if data_bytes:
                data = json.loads(data_bytes.decode())
                return EmailPoolEntry.from_dict(data)
                
            return None
            
        except Exception as e:
            logger.error(f"Failed to get pool entry for {email}: {e}")
            return None
    
    async def _refill_pool(self):
        """Refill pool with new accounts if needed"""
        try:
            current_size = await self.get_pool_size()
            available_count = await self.get_available_count()
            
            if available_count >= self.REFILL_THRESHOLD:
                return  # No refill needed
            
            accounts_needed = min(
                self.MAX_POOL_SIZE - current_size,
                self.MIN_POOL_SIZE - available_count
            )
            
            if accounts_needed <= 0:
                return
            
            logger.info(f"Refilling pool with {accounts_needed} accounts...")
            
            # Create new accounts
            created = 0
            providers = list(EmailProviderType)
            
            for i in range(accounts_needed):
                try:
                    provider = providers[i % len(providers)]
                    account = await self.email_service.create_email_account(provider)
                    
                    pool_entry = EmailPoolEntry(
                        account=account,
                        status=EmailPoolStatus.AVAILABLE
                    )
                    
                    await self._add_to_pool(pool_entry)
                    created += 1
                    
                    await asyncio.sleep(random.uniform(0.5, 2))
                    
                except Exception as e:
                    logger.error(f"Failed to create account during refill: {e}")
                    continue
            
            logger.info(f"Pool refill complete: {created} accounts added")
            
        except Exception as e:
            logger.error(f"Pool refill failed: {e}")
    
    async def cleanup_expired_accounts(self) -> int:
        """Remove expired and blacklisted accounts from pool"""
        try:
            pool_data = self.redis_client.hgetall(self.POOL_KEY)
            current_time = datetime.now()
            removed = 0
            
            for email_bytes, data_bytes in pool_data.items():
                try:
                    email = email_bytes.decode()
                    data = json.loads(data_bytes.decode())
                    entry = EmailPoolEntry.from_dict(data)
                    
                    # Remove if expired or blacklisted for too long
                    should_remove = (
                        current_time > entry.account.expires_at or
                        entry.status == EmailPoolStatus.BLACKLISTED or
                        (entry.status == EmailPoolStatus.EXPIRED and 
                         entry.last_used and 
                         current_time > entry.last_used + timedelta(hours=6))
                    )
                    
                    if should_remove:
                        self.redis_client.hdel(self.POOL_KEY, email)
                        removed += 1
                        logger.debug(f"Removed expired/blacklisted account: {email}")
                        
                except Exception as e:
                    logger.warning(f"Error processing account during cleanup: {e}")
                    continue
            
            if removed > 0:
                logger.info(f"Cleanup complete: removed {removed} accounts")
                
                # Trigger refill if needed
                if await self.get_available_count() < self.REFILL_THRESHOLD:
                    asyncio.create_task(self._refill_pool())
            
            return removed
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return 0
    
    async def get_pool_size(self) -> int:
        """Get total pool size"""
        try:
            return self.redis_client.hlen(self.POOL_KEY)
        except Exception:
            return 0
    
    async def get_available_count(self) -> int:
        """Get count of available accounts"""
        available_accounts = await self._get_available_accounts()
        return len(available_accounts)
    
    async def get_pool_statistics(self) -> Dict:
        """Get comprehensive pool statistics"""
        try:
            pool_data = self.redis_client.hgetall(self.POOL_KEY)
            
            stats = {
                'total_accounts': len(pool_data),
                'available': 0,
                'in_use': 0,
                'expired': 0,
                'blacklisted': 0,
                'rate_limited': 0,
                'by_provider': defaultdict(int),
                'by_status': defaultdict(int),
                'average_usage': 0,
                'average_success_rate': 0,
                'provider_health': {},
                'domain_distribution': defaultdict(int)
            }
            
            total_usage = 0
            total_success_rate = 0
            valid_entries = 0
            
            for email_bytes, data_bytes in pool_data.items():
                try:
                    data = json.loads(data_bytes.decode())
                    entry = EmailPoolEntry.from_dict(data)
                    
                    # Count by status
                    stats['by_status'][entry.status.value] += 1
                    
                    if entry.status == EmailPoolStatus.AVAILABLE:
                        stats['available'] += 1
                    elif entry.status == EmailPoolStatus.IN_USE:
                        stats['in_use'] += 1
                    elif entry.status == EmailPoolStatus.EXPIRED:
                        stats['expired'] += 1
                    elif entry.status == EmailPoolStatus.BLACKLISTED:
                        stats['blacklisted'] += 1
                    elif entry.status == EmailPoolStatus.RATE_LIMITED:
                        stats['rate_limited'] += 1
                    
                    # Count by provider
                    stats['by_provider'][entry.account.provider.value] += 1
                    
                    # Domain distribution
                    domain = entry.account.email.split('@')[1]
                    stats['domain_distribution'][domain] += 1
                    
                    # Calculate averages
                    total_usage += entry.usage_count
                    total_success_rate += entry.success_rate
                    valid_entries += 1
                    
                except Exception as e:
                    logger.warning(f"Error processing entry for stats: {e}")
                    continue
            
            if valid_entries > 0:
                stats['average_usage'] = total_usage / valid_entries
                stats['average_success_rate'] = total_success_rate / valid_entries
            
            # Get provider health
            for provider in EmailProviderType:
                stats['provider_health'][provider.value] = self.deliverability.is_provider_healthy(provider)
            
            # Convert defaultdicts to regular dicts for JSON serialization
            stats['by_provider'] = dict(stats['by_provider'])
            stats['by_status'] = dict(stats['by_status'])
            stats['domain_distribution'] = dict(stats['domain_distribution'])
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get pool statistics: {e}")
            return {}

# Global pool manager instance
_email_pool_manager = None

def get_email_pool_manager(redis_config: Dict = None, pool_config: Dict = None) -> EmailPoolManager:
    """Get global email pool manager instance"""
    global _email_pool_manager
    if _email_pool_manager is None:
        _email_pool_manager = EmailPoolManager(redis_config, pool_config)
    return _email_pool_manager

# Convenience functions
async def get_email_for_service(service: str, purpose: str = None) -> Optional[EmailAccount]:
    """Get email account for service use"""
    manager = get_email_pool_manager()
    return await manager.get_email_account(service, purpose)

async def return_email_to_pool(email: str, success: bool = True, spam_reported: bool = False, 
                             bounced: bool = False) -> bool:
    """Return email account to pool"""
    manager = get_email_pool_manager()
    return await manager.return_email_account(email, success, spam_reported, bounced)

if __name__ == "__main__":
    async def test_pool_manager():
        """Test pool manager functionality"""
        print("Testing Email Pool Manager...")
        
        # Initialize pool
        manager = get_email_pool_manager()
        success = await manager.initialize_pool(5)
        print(f"Pool initialization: {'Success' if success else 'Failed'}")
        
        # Get statistics
        stats = await manager.get_pool_statistics()
        print(f"Pool statistics: {json.dumps(stats, indent=2)}")
        
        # Get email account
        account = await manager.get_email_account("test_service", "verification")
        if account:
            print(f"Got email account: {account.email}")
            
            # Return account
            await asyncio.sleep(5)
            returned = await manager.return_email_account(account.email, success=True)
            print(f"Returned account: {'Success' if returned else 'Failed'}")
        
        # Cleanup test
        cleaned = await manager.cleanup_expired_accounts()
        print(f"Cleaned up {cleaned} expired accounts")
        
        # Final statistics
        final_stats = await manager.get_pool_statistics()
        print(f"Final statistics: {json.dumps(final_stats, indent=2)}")
    
    # Run test
    asyncio.run(test_pool_manager())