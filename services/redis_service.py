"""
Redis service with global connection pool
Fixes max connection leak issue
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

# Global connection pool (singleton)
_redis_pool = None

async def get_redis_pool():
    """Get or create global Redis connection pool"""
    global _redis_pool
    if _redis_pool is None:
        try:
            _redis_pool = redis.ConnectionPool.from_url(
                url=settings.REDIS_URL,
                max_connections=12,  # Optimized for Redis Cloud Free Plan (30 max total)
                decode_responses=True,
                encoding="utf-8",
                socket_connect_timeout=5,
                socket_timeout=5,
                socket_keepalive=True,
                health_check_interval=30
            )
            logger.info("✅ Redis connection pool created (max 12 connections)")
        except Exception as e:
            logger.error(f"Failed to create Redis pool: {e}")
            _redis_pool = None
            raise
    return _redis_pool

async def close_redis_pool():
    """Close global Redis connection pool"""
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.disconnect()
        _redis_pool = None
        logger.info("Redis connection pool closed")

class RedisService:
    """Redis service using global connection pool with context manager support"""
    
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.redis_client = None
    
    async def __aenter__(self):
        """Context manager entry - get client from pool"""
        try:
            pool = await get_redis_pool()
            self.redis_client = redis.Redis(connection_pool=pool)
            return self.redis_client
        except Exception as e:
            logger.error(f"Failed to get Redis client from pool: {e}")
            raise AppException(
                message="Redis connection failed",
                detail=str(e),
                error_code="REDIS_CONNECTION_FAILED"
            )
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - return client to pool"""
        if self.redis_client:
            await self.redis_client.close(close_connection_pool=False)
            self.redis_client = None
    
    async def ping(self):
        """Ping Redis (for health checks only)"""
        try:
            async with self as client:
                return await client.ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            raise
    
    async def get_info(self):
        """Redis sunucu bilgilerini al"""
        try:
            async with self as client:
                return await client.info()
        except Exception as e:
            logger.error(f"Redis get_info failed: {e}")
            raise
    
    async def get_db_size(self):
        """Redis database boyutunu al"""
        try:
            async with self as client:
                return await client.dbsize()
        except Exception as e:
            logger.error(f"Redis get_db_size failed: {e}")
            raise
    
    async def get_keys_pattern(self, pattern):
        """Pattern'e göre key'leri al"""
        try:
            async with self as client:
                return await client.keys(pattern)
        except Exception as e:
            logger.error(f"Redis get_keys_pattern failed: {e}")
            raise
    
    async def delete_keys(self, keys):
        """Birden fazla key'i sil"""
        if not keys:
            return 0
        try:
            async with self as client:
                return await client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis delete_keys failed: {e}")
            raise
    
    async def flush_db(self):
        """Database'i tamamen temizle"""
        try:
            async with self as client:
                return await client.flushdb()
        except Exception as e:
            logger.error(f"Redis flush_db failed: {e}")
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
    
    async def init_bulk_upload_progress(self, task_id: str, total_files: int, filenames: List[str]):
        """Initialize bulk upload progress tracking"""
        try:
            async with self as client:
                progress_data = {
                    "status": "queued",
                    "total_files": total_files,
                    "current_index": 0,
                    "current_filename": None,
                    "completed_files": [],
                    "filenames": filenames,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                key = f"bulk_upload:{task_id}"
                await client.setex(key, 86400, json.dumps(progress_data))
                logger.info(f"Initialized bulk upload progress for task {task_id} with {total_files} files")
                return progress_data
        except Exception as e:
            logger.error(f"Failed to initialize bulk upload progress: {e}")
            raise
    
    async def update_bulk_upload_progress(self, task_id: str, updates: Dict[str, Any]):
        """Update bulk upload progress"""
        try:
            async with self as client:
                key = f"bulk_upload:{task_id}"
                
                existing_data = await client.get(key)
                if not existing_data:
                    logger.warning(f"Bulk upload progress not found for task {task_id}")
                    return None
                
                progress_data = json.loads(existing_data)
                progress_data.update(updates)
                progress_data["updated_at"] = datetime.utcnow().isoformat()
                
                await client.setex(key, 86400, json.dumps(progress_data))
                logger.debug(f"Updated bulk upload progress for task {task_id}")
                return progress_data
        except Exception as e:
            logger.error(f"Failed to update bulk upload progress: {e}")
            raise
    
    async def get_bulk_upload_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get bulk upload progress"""
        try:
            async with self as client:
                key = f"bulk_upload:{task_id}"
                data = await client.get(key)
                
                if not data:
                    return None
                
                progress_data = json.loads(data)
                
                if progress_data["total_files"] > 0:
                    progress_data["progress_percent"] = int((len(progress_data.get("completed_files", [])) / progress_data["total_files"]) * 100)
                else:
                    progress_data["progress_percent"] = 0
                
                return progress_data
        except Exception as e:
            logger.error(f"Failed to get bulk upload progress: {e}")
            raise
    
    async def complete_bulk_upload_file(self, task_id: str, filename: str, document_id: str):
        """Mark a file as completed in bulk upload"""
        try:
            async with self as client:
                key = f"bulk_upload:{task_id}"
                
                existing_data = await client.get(key)
                if not existing_data:
                    return None
                
                progress_data = json.loads(existing_data)
                progress_data["completed_files"].append({
                    "filename": filename,
                    "document_id": document_id,
                    "status": "completed",
                    "error": None,
                    "completed_at": datetime.utcnow().isoformat()
                })
                progress_data["updated_at"] = datetime.utcnow().isoformat()
                
                await client.setex(key, 86400, json.dumps(progress_data))
                logger.info(f"Marked file {filename} as completed for task {task_id}")
                return progress_data
        except Exception as e:
            logger.error(f"Failed to complete bulk upload file: {e}")
            raise
    
    async def fail_bulk_upload_file(self, task_id: str, filename: str, error: str):
        """Mark a file as failed in bulk upload"""
        try:
            async with self as client:
                key = f"bulk_upload:{task_id}"
                
                existing_data = await client.get(key)
                if not existing_data:
                    return None
                
                progress_data = json.loads(existing_data)
                progress_data["completed_files"].append({
                    "filename": filename,
                    "document_id": None,
                    "status": "failed",
                    "error": error,
                    "failed_at": datetime.utcnow().isoformat()
                })
                progress_data["updated_at"] = datetime.utcnow().isoformat()
                
                await client.setex(key, 86400, json.dumps(progress_data))
                logger.warning(f"Marked file {filename} as failed for task {task_id}: {error}")
                return progress_data
        except Exception as e:
            logger.error(f"Failed to mark bulk upload file as failed: {e}")
            raise

# Global instance for backward compatibility
redis_service = RedisService()
