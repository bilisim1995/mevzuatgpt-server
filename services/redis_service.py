"""
SIMPLE Redis service with context manager only
Fixes max connection pool issue
"""

import redis.asyncio as redis
import json
import hashlib
import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from core.config import settings
from utils.exceptions import AppException

logger = logging.getLogger(__name__)

class RedisService:
    """Simple Redis service with context manager pattern"""
    
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.redis_client = None
    
    async def __aenter__(self):
        """Context manager entry"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=False,
                health_check_interval=None
            )
            await self.redis_client.ping()
            logger.debug("Redis connection established")
            return self.redis_client
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise AppException(
                message="Redis connection failed",
                detail=str(e),
                error_code="REDIS_CONNECTION_FAILED"
            )
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.redis_client:
            await self.redis_client.aclose()
            self.redis_client = None
            logger.debug("Redis connection closed")

    # Simple utility method for ping test
    async def ping(self):
        """Ping Redis (for health checks only)"""
        async with RedisService() as client:
            return await client.ping()

    # Cache methods (stub implementations)
    async def get_cached_search_results(self, query, filters=None, limit=None, similarity_threshold=None):
        return None
    
    async def cache_search_results(self, query, results, filters=None, limit=None, similarity_threshold=None, ttl=1800):
        pass
    
    async def get_cached_embedding(self, query):
        return None
    
    async def cache_embedding(self, query, embedding, ttl=3600):
        pass
    
    async def check_rate_limit(self, user_id, endpoint="ask", limit=60, window=60):
        return True, limit
    
    async def add_user_search(self, user_id, query, institution=""):
        pass
    
    async def increment_search_popularity(self, query):
        pass
    
    async def get_user_search_history(self, user_id, limit=5):
        return []
    
    async def get_popular_searches(self, limit=10):
        return []
    
    async def get_available_institutions(self):
        return []
    
    async def cache_institutions(self, institutions_list, ttl=86400):
        pass
    
    # Admin methods for system management
    async def get_info(self):
        """Redis sunucu bilgilerini al"""
        async with RedisService() as client:
            return await client.info()
    
    async def get_db_size(self):
        """Redis database boyutunu al"""
        async with RedisService() as client:
            return await client.dbsize()
    
    async def get_keys_pattern(self, pattern):
        """Pattern'e göre key'leri al"""
        async with RedisService() as client:
            return await client.keys(pattern)
    
    async def delete_keys(self, keys):
        """Birden fazla key'i sil"""
        if not keys:
            return 0
        async with RedisService() as client:
            return await client.delete(*keys)
    
    async def flush_db(self):
        """Database'i tamamen temizle"""
        async with RedisService() as client:
            return await client.flushdb()

# Global instance for backward compatibility
redis_service = RedisService()