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
        self._shared_client = None
    
    async def __aenter__(self):
        """Context manager entry"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,  # Daha kısa timeout
                socket_timeout=2,          # Socket operations timeout
                socket_keepalive=False,
                health_check_interval=None,
                retry_on_timeout=True,     # Timeout'ta retry
                retry_on_error=[ConnectionError, TimeoutError]  # Hata durumlarında retry
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

    async def _get_client(self):
        """Get shared Redis client"""
        if not self._shared_client:
            try:
                self._shared_client = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                    socket_keepalive=False,
                    health_check_interval=None,
                    retry_on_timeout=True,
                    retry_on_error=[ConnectionError, TimeoutError]
                )
                await self._shared_client.ping()
                logger.debug("Shared Redis client established")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self._shared_client = None
                raise
        return self._shared_client
    
    async def _close_client(self):
        """Close shared client"""
        if self._shared_client:
            await self._shared_client.aclose()
            self._shared_client = None
            logger.debug("Shared Redis client closed")

    # Simple utility method for ping test
    async def ping(self):
        """Ping Redis (for health checks only)"""
        try:
            client = await self._get_client()
            return await client.ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            # Try to reconnect
            await self._close_client()
            raise

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
        try:
            client = await self._get_client()
            return await client.info()
        except Exception as e:
            logger.error(f"Redis get_info failed: {e}")
            await self._close_client()
            raise
    
    async def get_db_size(self):
        """Redis database boyutunu al"""
        try:
            client = await self._get_client()
            return await client.dbsize()
        except Exception as e:
            logger.error(f"Redis get_db_size failed: {e}")
            await self._close_client()
            raise
    
    async def get_keys_pattern(self, pattern):
        """Pattern'e göre key'leri al"""
        try:
            client = await self._get_client()
            return await client.keys(pattern)
        except Exception as e:
            logger.error(f"Redis get_keys_pattern failed: {e}")
            await self._close_client()
            raise
    
    async def delete_keys(self, keys):
        """Birden fazla key'i sil"""
        if not keys:
            return 0
        try:
            client = await self._get_client()
            return await client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis delete_keys failed: {e}")
            await self._close_client()
            raise
    
    async def flush_db(self):
        """Database'i tamamen temizle"""
        try:
            client = await self._get_client()
            return await client.flushdb()
        except Exception as e:
            logger.error(f"Redis flush_db failed: {e}")
            await self._close_client()
            raise

# Global instance for backward compatibility
redis_service = RedisService()