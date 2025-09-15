#!/usr/bin/env python3
"""
Redis Session Manager with Fallbacks
Handles session management with Redis or in-memory fallback
"""

import os
import json
import time
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SessionManager:
    """Session manager with Redis and in-memory fallback"""
    
    def __init__(self):
        self.redis_available = False
        self.redis_client = None
        self.memory_store = {}  # Fallback in-memory store
        
        # Try to connect to Redis
        self._init_redis()
    
    def _init_redis(self):
        """Initialize Redis connection with fallback"""
        try:
            import redis
            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            
            # Test connection
            self.redis_client.ping()
            self.redis_available = True
            logger.info("✅ Redis session manager initialized")
            
        except Exception as e:
            logger.warning(f"⚠️ Redis not available, using memory fallback: {e}")
            self.redis_available = False
    
    def set_session(self, session_id: str, data: Dict[str, Any], expire_seconds: int = 3600) -> bool:
        """Set session data with expiration"""
        try:
            serialized_data = json.dumps({
                'data': data,
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(seconds=expire_seconds)).isoformat()
            })
            
            if self.redis_available:
                return self.redis_client.setex(f"session:{session_id}", expire_seconds, serialized_data)
            else:
                # Memory fallback
                self.memory_store[f"session:{session_id}"] = {
                    'data': serialized_data,
                    'expires_at': time.time() + expire_seconds
                }
                return True
                
        except Exception as e:
            logger.error(f"Failed to set session {session_id}: {e}")
            return False
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        try:
            if self.redis_available:
                data = self.redis_client.get(f"session:{session_id}")
                if data:
                    return json.loads(data)
            else:
                # Memory fallback with expiration check
                key = f"session:{session_id}"
                if key in self.memory_store:
                    session = self.memory_store[key]
                    if time.time() < session['expires_at']:
                        return json.loads(session['data'])
                    else:
                        # Expired, remove it
                        del self.memory_store[key]
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session"""
        try:
            if self.redis_available:
                return bool(self.redis_client.delete(f"session:{session_id}"))
            else:
                key = f"session:{session_id}"
                if key in self.memory_store:
                    del self.memory_store[key]
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    def set_user_progress(self, user_id: str, batch_id: str, progress_data: Dict) -> bool:
        """Set user progress for account creation"""
        return self.set_session(f"progress:{user_id}:{batch_id}", progress_data, expire_seconds=7200)
    
    def get_user_progress(self, user_id: str, batch_id: str) -> Optional[Dict]:
        """Get user progress"""
        session_data = self.get_session(f"progress:{user_id}:{batch_id}")
        return session_data['data'] if session_data else None
    
    def set_rate_limit(self, user_id: str, action: str, expire_seconds: int = 3600) -> bool:
        """Set rate limiting for user actions"""
        return self.set_session(f"rate_limit:{user_id}:{action}", {'limited': True}, expire_seconds)
    
    def check_rate_limit(self, user_id: str, action: str) -> bool:
        """Check if user is rate limited for action"""
        return self.get_session(f"rate_limit:{user_id}:{action}") is not None
    
    def cleanup_expired(self):
        """Clean up expired sessions from memory store"""
        if not self.redis_available:
            current_time = time.time()
            expired_keys = [
                key for key, session in self.memory_store.items()
                if current_time >= session['expires_at']
            ]
            for key in expired_keys:
                del self.memory_store[key]
            logger.info(f"Cleaned up {len(expired_keys)} expired sessions")

# Global instance
_session_manager = None

def get_session_manager() -> SessionManager:
    """Get global session manager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager

if __name__ == "__main__":
    # Test the session manager
    sm = get_session_manager()
    
    # Test basic operations
    sm.set_session("test_123", {"user": "test", "status": "active"})
    data = sm.get_session("test_123")
    print(f"Session data: {data}")
    
    # Test progress tracking
    sm.set_user_progress("user_456", "batch_789", {"accounts_created": 5, "total": 10})
    progress = sm.get_user_progress("user_456", "batch_789")
    print(f"Progress data: {progress}")
    
    # Test rate limiting
    sm.set_rate_limit("user_456", "snap_command", 300)  # 5 minute limit
    is_limited = sm.check_rate_limit("user_456", "snap_command")
    print(f"Rate limited: {is_limited}")