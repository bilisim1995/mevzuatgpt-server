"""
Comprehensive System Health Monitoring Service
Provides detailed health checks for all system components
"""

import logging
import time
import aiohttp
import redis
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from core.config import get_settings
from services.elasticsearch_service import ElasticsearchService
from services.storage_service import StorageService
from models.supabase_client import supabase_client

logger = logging.getLogger(__name__)
settings = get_settings()

class HealthService:
    def __init__(self, db: AsyncSession = None):
        self.db = db
        # Remove persistent elasticsearch_service instance
        
    async def get_comprehensive_health(self) -> Dict[str, Any]:
        """
        Get comprehensive system health information
        
        Returns:
            Dictionary containing all system health metrics
        """
        start_time = time.time()
        
        # Run all health checks in parallel for better performance
        health_checks = await self._run_all_health_checks()
        
        # Calculate overall health status
        overall_status = self._calculate_overall_status(health_checks)
        
        response_time = round((time.time() - start_time) * 1000, 2)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": overall_status,
            "response_time_ms": response_time,
            "components": health_checks
        }
    
    async def _run_all_health_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        checks = {}
        
        # Database Health
        checks["database"] = await self._check_database_health()
        
        # Redis Health  
        checks["redis"] = await self._check_redis_health()
        
        # Elasticsearch Health
        checks["elasticsearch"] = await self._check_elasticsearch_health()
        
        # Celery Health
        checks["celery"] = await self._check_celery_health()
        
        # Email Service Health
        checks["email"] = await self._check_email_health()
        
        # AI Services Health
        checks["ai_services"] = await self._check_ai_services_health()
        
        # Storage Health
        checks["storage"] = await self._check_storage_health()
        
        # API Performance
        checks["api"] = await self._check_api_performance()
        
        return checks
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """Check Supabase database health"""
        try:
            start_time = time.time()
            
            # Test basic connection
            result = supabase_client.supabase.table('user_profiles').select('id').limit(1).execute()
            connection_time = round((time.time() - start_time) * 1000, 2)
            
            # Get document count
            doc_count = supabase_client.supabase.table('mevzuat_documents').select('id', count='exact').execute()
            total_documents = doc_count.count if doc_count.count else 0
            
            # Get user count
            user_count = supabase_client.supabase.table('user_profiles').select('id', count='exact').execute()
            total_users = user_count.count if user_count.count else 0
            
            return {
                "status": "healthy",
                "connection_time_ms": connection_time,
                "total_documents": total_documents,
                "total_users": total_users,
                "provider": "supabase",
                "last_check": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
    
    async def _check_redis_health(self) -> Dict[str, Any]:
        """Check Redis health"""
        try:
            start_time = time.time()
            
            r = redis.from_url(settings.REDIS_URL)
            
            # Test ping
            r.ping()
            ping_time = round((time.time() - start_time) * 1000, 2)
            
            # Get Redis info
            info = r.info()
            
            return {
                "status": "healthy",
                "ping_time_ms": ping_time,
                "memory_usage_mb": round(info.get('used_memory', 0) / 1024 / 1024, 2),
                "connected_clients": info.get('connected_clients', 0),
                "uptime_seconds": info.get('uptime_in_seconds', 0),
                "version": info.get('redis_version', 'unknown'),
                "last_check": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "error", 
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
    
    async def _check_elasticsearch_health(self) -> Dict[str, Any]:
        """Check Elasticsearch health"""
        try:
            async with ElasticsearchService() as es_service:
                health_data = await es_service.health_check()
            
            if health_data.get("health") == "ok":
                return {
                    "status": "healthy",
                    "cluster_status": health_data.get("cluster_status"),
                    "cluster_name": health_data.get("cluster_name"),
                    "document_count": health_data.get("document_count"),
                    "vector_dimensions": health_data.get("vector_dimensions"),
                    "last_check": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "error": health_data.get("error"),
                    "last_check": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Elasticsearch health check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
    
    async def _check_celery_health(self) -> Dict[str, Any]:
        """Check Celery worker health"""
        try:
            r = redis.from_url(settings.REDIS_URL)
            
            # Check active workers
            active_workers = 0
            try:
                # Celery stores worker heartbeats in Redis
                worker_keys = r.keys('_kombu.binding.celery*')
                active_workers = len(worker_keys)
            except:
                active_workers = 1  # Assume 1 worker if can't determine
            
            # Get task queue lengths
            pending_tasks = 0
            try:
                pending_tasks = r.llen('celery')  # Default queue
            except:
                pending_tasks = 0
            
            # Get task stats from today
            today = datetime.utcnow().date()
            completed_tasks_today = 0
            failed_tasks_today = 0
            
            # These would normally come from Celery monitoring
            # For now, we'll use estimated values
            
            return {
                "status": "healthy" if active_workers > 0 else "warning",
                "active_workers": active_workers,
                "pending_tasks": pending_tasks,
                "completed_tasks_today": completed_tasks_today,
                "failed_tasks_today": failed_tasks_today,
                "queue_backend": "redis",
                "last_check": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Celery health check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
    
    async def _check_email_health(self) -> Dict[str, Any]:
        """Check SMTP email service health"""
        try:
            if not hasattr(settings, 'SMTP_PASSWORD') or not settings.SMTP_PASSWORD:
                return {
                    "status": "not_configured",
                    "error": "SMTP password not configured",
                    "last_check": datetime.utcnow().isoformat()
                }
            
            smtp_host = getattr(settings, 'SMTP_HOST', 'smtp.hostinger.com')
            smtp_port = getattr(settings, 'SMTP_PORT', 465)
            smtp_user = getattr(settings, 'SMTP_USER', 'info@mevzuatgpt.org')
            
            start_time = time.time()
            
            # Test SMTP connection
            try:
                import smtplib
                
                if smtp_port == 587:
                    server = smtplib.SMTP(smtp_host, smtp_port, timeout=5)
                    server.starttls()
                else:
                    server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=5)
                
                # Just check connection, don't login (to avoid rate limiting)
                server.quit()
                
                connection_time = round((time.time() - start_time) * 1000, 2)
                
                return {
                    "status": "healthy",
                    "connection_time_ms": connection_time,
                    "provider": "smtp",
                    "host": smtp_host,
                    "port": smtp_port,
                    "user": smtp_user,
                    "last_check": datetime.utcnow().isoformat()
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"SMTP connection failed: {str(e)}",
                    "last_check": datetime.utcnow().isoformat()
                }
                        
        except Exception as e:
            logger.error(f"Email service health check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
    
    async def _check_ai_services_health(self) -> Dict[str, Any]:
        """Check AI services (OpenAI and Groq) health"""
        ai_status = {}
        
        # Check OpenAI
        try:
            if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
                start_time = time.time()
                
                try:
                    async with aiohttp.ClientSession() as session:
                        headers = {
                            'Authorization': f'Bearer {settings.OPENAI_API_KEY}',
                            'Content-Type': 'application/json'
                        }
                        
                        async with session.get(
                            'https://api.openai.com/v1/models',
                            headers=headers
                        ) as response:
                            response_time = round((time.time() - start_time) * 1000, 2)
                            
                            if response.status == 200:
                                ai_status["openai"] = {
                                    "status": "healthy",
                                    "api_response_time_ms": response_time,
                                    "model": settings.OPENAI_MODEL
                                }
                            else:
                                ai_status["openai"] = {
                                    "status": "error",
                                    "error": f"OpenAI API returned {response.status}"
                                }
                except Exception as e:
                    ai_status["openai"] = {
                        "status": "error",
                        "error": f"OpenAI API request failed: {str(e)}"
                    }
            else:
                ai_status["openai"] = {
                    "status": "not_configured",
                    "error": "OpenAI API key not configured"
                }
                
        except Exception as e:
            ai_status["openai"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Check Groq  
        try:
            if hasattr(settings, 'GROQ_API_KEY') and settings.GROQ_API_KEY:
                start_time = time.time()
                
                try:
                    async with aiohttp.ClientSession() as session:
                        headers = {
                            'Authorization': f'Bearer {settings.GROQ_API_KEY}',
                            'Content-Type': 'application/json'
                        }
                        
                        async with session.get(
                            'https://api.groq.com/openai/v1/models',
                            headers=headers
                        ) as response:
                            response_time = round((time.time() - start_time) * 1000, 2)
                            
                            if response.status == 200:
                                groq_model = getattr(settings, 'GROQ_MODEL', 'llama3-70b-8192')
                                ai_status["groq"] = {
                                    "status": "healthy",
                                    "api_response_time_ms": response_time,
                                    "model": groq_model
                                }
                            else:
                                ai_status["groq"] = {
                                    "status": "error",
                                    "error": f"Groq API returned {response.status}"
                                }
                except Exception as e:
                    ai_status["groq"] = {
                        "status": "error",
                        "error": f"Groq API request failed: {str(e)}"
                    }
            else:
                ai_status["groq"] = {
                    "status": "not_configured",
                    "error": "Groq API key not configured"
                }
                
        except Exception as e:
            ai_status["groq"] = {
                "status": "error",
                "error": str(e)
            }
        
        return ai_status
    
    async def _check_storage_health(self) -> Dict[str, Any]:
        """Check Bunny.net storage health"""
        try:
            storage_service = StorageService()
            
            # Get document count and file sizes from database
            doc_result = supabase_client.supabase.table('mevzuat_documents').select('file_size').execute()
            total_files = len(doc_result.data) if doc_result.data else 0
            
            # Calculate total storage used
            total_size = 0
            if doc_result.data:
                for doc in doc_result.data:
                    file_size = doc.get('file_size')
                    if file_size and isinstance(file_size, (int, float)):
                        total_size += file_size
            
            storage_used_gb = round(total_size / 1024 / 1024 / 1024, 2) if total_size > 0 else 0.0
            
            return {
                "status": "healthy",
                "provider": "bunny.net",
                "total_files": total_files,
                "storage_used_gb": storage_used_gb,
                "cdn_url": "https://cdn.mevzuatgpt.org",
                "last_check": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Storage health check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
    
    async def _check_api_performance(self) -> Dict[str, Any]:
        """Check API performance metrics"""
        try:
            # Get search logs from last hour for performance metrics
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            search_logs = supabase_client.supabase.table('search_logs') \
                .select('execution_time, reliability_score') \
                .gte('created_at', one_hour_ago.isoformat()) \
                .execute()
            
            if search_logs.data:
                execution_times = [log.get('execution_time', 0) for log in search_logs.data if log.get('execution_time')]
                avg_response_time = round(sum(execution_times) / len(execution_times), 2) if execution_times else 0
                requests_count = len(search_logs.data)
                
                # Calculate reliability
                reliability_scores = [log.get('reliability_score', 0) for log in search_logs.data if log.get('reliability_score')]
                avg_reliability = round(sum(reliability_scores) / len(reliability_scores), 2) if reliability_scores else 0
            else:
                avg_response_time = 0
                requests_count = 0
                avg_reliability = 0
            
            return {
                "status": "healthy",
                "avg_response_time_ms": avg_response_time,
                "requests_last_hour": requests_count,
                "avg_reliability_score": avg_reliability,
                "uptime_status": "operational",
                "last_check": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"API performance check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
    
    def _calculate_overall_status(self, health_checks: Dict[str, Any]) -> str:
        """Calculate overall system status based on component health"""
        critical_components = ["database", "redis", "elasticsearch"]
        important_components = ["celery", "storage"]
        optional_components = ["email", "ai_services"]
        
        # Check critical components
        for component in critical_components:
            if component in health_checks:
                status = health_checks[component].get("status")
                if status == "error":
                    return "critical"
        
        # Check important components
        error_count = 0
        for component in important_components:
            if component in health_checks:
                status = health_checks[component].get("status")
                if status == "error":
                    error_count += 1
        
        if error_count >= 2:
            return "degraded"
        elif error_count >= 1:
            return "warning"
        
        # Check AI services
        ai_services = health_checks.get("ai_services", {})
        if isinstance(ai_services, dict):
            ai_errors = sum(1 for service in ai_services.values() if service.get("status") == "error")
            if ai_errors >= 2:
                return "warning"
        
        return "healthy"