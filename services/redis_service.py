"""
Redis service for caching and rate limiting
Handles search optimization and user experience features
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
    """Redis service for caching, rate limiting and user experience features"""
    
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.redis_client = None
    
    async def get_redis_client(self):
        """Get or create Redis client connection"""
        if self.redis_client is None:
            try:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_keepalive=True,
                    health_check_interval=30
                )
                # Test connection
                await self.redis_client.ping()
                logger.info("Redis connection established")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise AppException(
                    message="Redis connection failed",
                    detail=str(e),
                    error_code="REDIS_CONNECTION_FAILED"
                )
        return self.redis_client
    
    def _generate_query_hash(self, query: str, filters: Dict = None) -> str:
        """Generate consistent hash for query and filters"""
        query_data = {
            "query": query.strip().lower(),
            "filters": filters or {}
        }
        query_json = json.dumps(query_data, sort_keys=True)
        return hashlib.md5(query_json.encode()).hexdigest()
    
    # Embedding Cache
    async def get_cached_embedding(self, query: str) -> Optional[List[float]]:
        """Get cached embedding for query"""
        try:
            client = await self.get_redis_client()
            cache_key = f"embedding:{self._generate_query_hash(query)}"
            
            cached_data = await client.get(cache_key)
            if cached_data:
                embedding = json.loads(cached_data)
                logger.debug(f"Cache hit for embedding: {query[:50]}")
                return embedding
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get cached embedding: {e}")
            return None
    
    async def cache_embedding(self, query: str, embedding: List[float], ttl: int = 3600):
        """Cache embedding with TTL (default 1 hour)"""
        try:
            client = await self.get_redis_client()
            cache_key = f"embedding:{self._generate_query_hash(query)}"
            
            await client.setex(
                cache_key,
                ttl,
                json.dumps(embedding)
            )
            logger.debug(f"Cached embedding for: {query[:50]}")
            
        except Exception as e:
            logger.warning(f"Failed to cache embedding: {e}")
    
    # Search Results Cache
    async def get_cached_search_results(
        self, 
        query: str, 
        filters: Dict = None
    ) -> Optional[List[Dict]]:
        """Get cached search results"""
        try:
            client = await self.get_redis_client()
            cache_key = f"search:{self._generate_query_hash(query, filters)}"
            
            cached_data = await client.get(cache_key)
            if cached_data:
                results = json.loads(cached_data)
                logger.debug(f"Cache hit for search: {query[:50]}")
                return results
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get cached search results: {e}")
            return None
    
    async def cache_search_results(
        self, 
        query: str, 
        results: List[Dict], 
        filters: Dict = None,
        ttl: int = 1800
    ):
        """Cache search results with TTL (default 30 minutes)"""
        try:
            client = await self.get_redis_client()
            cache_key = f"search:{self._generate_query_hash(query, filters)}"
            
            await client.setex(
                cache_key,
                ttl,
                json.dumps(results, default=str)  # Handle datetime serialization
            )
            logger.debug(f"Cached search results for: {query[:50]}")
            
        except Exception as e:
            logger.warning(f"Failed to cache search results: {e}")
    
    # User Search History
    async def add_user_search(self, user_id: str, query: str, institution: str = None):
        """Add search to user history"""
        try:
            client = await self.get_redis_client()
            history_key = f"user_history:{user_id}"
            
            search_entry = {
                "query": query,
                "institution": institution,
                "timestamp": datetime.now().isoformat()
            }
            
            # Add to list (most recent first)
            await client.lpush(history_key, json.dumps(search_entry))
            
            # Keep only last 20 searches
            await client.ltrim(history_key, 0, 19)
            
            # Set expiry (30 days)
            await client.expire(history_key, 30 * 24 * 3600)
            
            logger.debug(f"Added search to user history: {user_id}")
            
        except Exception as e:
            logger.warning(f"Failed to add user search: {e}")
    
    async def get_user_search_history(
        self, 
        user_id: str, 
        limit: int = 10
    ) -> List[Dict]:
        """Get user's recent search history"""
        try:
            client = await self.get_redis_client()
            history_key = f"user_history:{user_id}"
            
            search_entries = await client.lrange(history_key, 0, limit - 1)
            
            history = []
            for entry in search_entries:
                try:
                    history.append(json.loads(entry))
                except json.JSONDecodeError:
                    continue
            
            return history
            
        except Exception as e:
            logger.warning(f"Failed to get user search history: {e}")
            return []
    
    async def get_popular_searches(self, limit: int = 10) -> List[Dict]:
        """Get most popular search queries"""
        try:
            client = await self.get_redis_client()
            popular_key = "popular_searches"
            
            # Get popular searches with scores
            popular = await client.zrevrange(popular_key, 0, limit - 1, withscores=True)
            
            result = []
            for query, score in popular:
                result.append({
                    "query": query,
                    "count": int(score)
                })
            
            return result
            
        except Exception as e:
            logger.warning(f"Failed to get popular searches: {e}")
            return []
    
    async def increment_search_popularity(self, query: str):
        """Increment popularity counter for search query"""
        try:
            client = await self.get_redis_client()
            popular_key = "popular_searches"
            
            # Normalize query
            normalized_query = query.strip().lower()
            
            # Increment counter
            await client.zincrby(popular_key, 1, normalized_query)
            
            # Set expiry if new
            await client.expire(popular_key, 7 * 24 * 3600)  # 7 days
            
        except Exception as e:
            logger.warning(f"Failed to increment search popularity: {e}")
    
    # Rate Limiting
    async def check_rate_limit(
        self, 
        user_id: str, 
        endpoint: str = "ask",
        limit: int = 30, 
        window: int = 60
    ) -> tuple[bool, int]:
        """
        Check if user is within rate limit
        
        Returns:
            (is_allowed: bool, remaining_requests: int)
        """
        try:
            client = await self.get_redis_client()
            current_minute = int(datetime.now().timestamp() // window)
            rate_key = f"rate_limit:{endpoint}:{user_id}:{current_minute}"
            
            # Get current count
            current_count = await client.get(rate_key)
            current_count = int(current_count) if current_count else 0
            
            if current_count >= limit:
                return False, 0
            
            # Increment counter
            await client.incr(rate_key)
            await client.expire(rate_key, window)
            
            remaining = limit - (current_count + 1)
            return True, remaining
            
        except Exception as e:
            logger.warning(f"Rate limit check failed: {e}")
            # On Redis failure, allow request
            return True, limit
    
    async def get_rate_limit_info(
        self, 
        user_id: str, 
        endpoint: str = "ask",
        window: int = 60
    ) -> Dict[str, int]:
        """Get current rate limit status"""
        try:
            client = await self.get_redis_client()
            current_minute = int(datetime.now().timestamp() // window)
            rate_key = f"rate_limit:{endpoint}:{user_id}:{current_minute}"
            
            current_count = await client.get(rate_key)
            current_count = int(current_count) if current_count else 0
            
            return {
                "current_requests": current_count,
                "window_start": current_minute * window,
                "window_end": (current_minute + 1) * window
            }
            
        except Exception as e:
            logger.warning(f"Failed to get rate limit info: {e}")
            return {"current_requests": 0, "window_start": 0, "window_end": 0}
    
    # Institution Filters
    async def get_available_institutions(self) -> List[str]:
        """Get list of available institutions from cache"""
        try:
            client = await self.get_redis_client()
            institutions_key = "available_institutions"
            
            cached_institutions = await client.get(institutions_key)
            if cached_institutions:
                return json.loads(cached_institutions)
            
            return []
            
        except Exception as e:
            logger.warning(f"Failed to get cached institutions: {e}")
            return []
    
    async def cache_institutions(self, institutions: List[str], ttl: int = 86400):
        """Cache available institutions (24 hours TTL)"""
        try:
            client = await self.get_redis_client()
            institutions_key = "available_institutions"
            
            await client.setex(
                institutions_key,
                ttl,
                json.dumps(institutions)
            )
            logger.info(f"Cached {len(institutions)} institutions")
            
        except Exception as e:
            logger.warning(f"Failed to cache institutions: {e}")
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.aclose()
            logger.info("Redis connection closed")

# Global Redis service instance
redis_service = RedisService()