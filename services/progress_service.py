"""
Progress tracking service for long-running tasks
Provides real-time progress updates via Redis
"""
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from core.config import settings
from services.redis_service import RedisService
import logging

logger = logging.getLogger(__name__)

class ProgressService:
    """Service for tracking task progress"""
    
    def __init__(self):
        self.redis_service = RedisService()
        self.progress_key_prefix = "task_progress:"
        self.batch_key_prefix = "batch_progress:"
        self.batch_tasks_prefix = "batch_tasks:"
        self.progress_ttl = 3600  # 1 hour TTL for progress data
    
    async def initialize_task_progress(
        self, 
        task_id: str, 
        document_id: str, 
        document_title: str,
        total_steps: int = 5,
        batch_id: Optional[str] = None,
        filename: Optional[str] = None
    ) -> None:
        """Initialize progress tracking for a new task"""
        try:
            progress_data = {
                "task_id": task_id,
                "document_id": document_id,
                "document_title": document_title,
                "filename": filename or document_title,
                "batch_id": batch_id,
                "status": "pending",
                "stage": "upload",
                "progress_percent": 0,
                "current_step": "Task başlatılıyor...",
                "total_steps": total_steps,
                "completed_steps": 0,
                "error_message": None,
                "started_at": datetime.utcnow().isoformat(),
                "completed_at": None,
                "estimated_remaining_seconds": None
            }
            
            key = f"{self.progress_key_prefix}{task_id}"
            async with RedisService() as client:
                await client.setex(key, self.progress_ttl, json.dumps(progress_data))
                
                if batch_id:
                    await client.sadd(f"{self.batch_tasks_prefix}{batch_id}", task_id)
                    await client.expire(f"{self.batch_tasks_prefix}{batch_id}", self.progress_ttl)
                    
            logger.info(f"Initialized progress tracking for task {task_id}" + (f" in batch {batch_id}" if batch_id else ""))
            
        except Exception as e:
            logger.error(f"Failed to initialize progress for task {task_id}: {e}")
    
    async def update_progress(
        self,
        task_id: str,
        stage: str,
        current_step: str,
        completed_steps: int,
        total_steps: Optional[int] = None,
        status: str = "processing",
        error_message: Optional[str] = None
    ) -> None:
        """Update task progress"""
        try:
            key = f"{self.progress_key_prefix}{task_id}"
            async with RedisService() as client:
                existing_data = await client.get(key)
                
                if not existing_data:
                    logger.warning(f"No existing progress data found for task {task_id}")
                    return
                
                progress_data = json.loads(existing_data)
                
                # Update fields
                progress_data["stage"] = stage
                progress_data["current_step"] = current_step
                progress_data["completed_steps"] = completed_steps
                progress_data["status"] = status
                
                if total_steps:
                    progress_data["total_steps"] = total_steps
                
                if error_message:
                    progress_data["error_message"] = error_message
                    progress_data["status"] = "failed"
                
                # Calculate progress percentage
                if progress_data["total_steps"] > 0:
                    progress_data["progress_percent"] = min(
                        100, 
                        int((completed_steps / progress_data["total_steps"]) * 100)
                    )
                
                # Estimate remaining time (simple calculation)
                if progress_data["started_at"] and progress_data["progress_percent"] > 0:
                    start_time = datetime.fromisoformat(progress_data["started_at"])
                    elapsed_seconds = (datetime.utcnow() - start_time).total_seconds()
                    if progress_data["progress_percent"] < 100:
                        estimated_total = (elapsed_seconds * 100) / progress_data["progress_percent"]
                        remaining = max(0, estimated_total - elapsed_seconds)
                        progress_data["estimated_remaining_seconds"] = int(remaining)
                
                # Mark as completed if all steps done
                if completed_steps >= progress_data["total_steps"]:
                    progress_data["status"] = "completed"
                    progress_data["progress_percent"] = 100
                    progress_data["completed_at"] = datetime.utcnow().isoformat()
                    progress_data["estimated_remaining_seconds"] = 0
                
                await client.setex(key, self.progress_ttl, json.dumps(progress_data))
            logger.info(f"Updated progress for task {task_id}: {progress_data['progress_percent']}% - {current_step}")
            
        except Exception as e:
            logger.error(f"Failed to update progress for task {task_id}: {e}")
    
    async def get_task_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current progress for a task"""
        try:
            key = f"{self.progress_key_prefix}{task_id}"
            async with RedisService() as client:
                data = await client.get(key)
                
                if not data:
                    return None
                
                return json.loads(data)
                
        except Exception as e:
            logger.error(f"Failed to get progress for task {task_id}: {e}")
            return None
    
    async def mark_task_failed(self, task_id: str, error_message: str) -> None:
        """Mark a task as failed with error message"""
        try:
            key = f"{self.progress_key_prefix}{task_id}"
            async with RedisService() as client:
                existing_data = await client.get(key)
                
                if existing_data:
                    progress_data = json.loads(existing_data)
                    progress_data["status"] = "failed"
                    progress_data["error_message"] = error_message
                    progress_data["completed_at"] = datetime.utcnow().isoformat()
                    
                    await client.setex(key, self.progress_ttl, json.dumps(progress_data))
                logger.info(f"Marked task {task_id} as failed: {error_message}")
            
        except Exception as e:
            logger.error(f"Failed to mark task {task_id} as failed: {e}")
    
    async def cleanup_old_progress(self, older_than_hours: int = 24) -> None:
        """Clean up old progress entries"""
        try:
            # This is a simple implementation - Redis TTL handles most cleanup
            # Could be enhanced to scan and remove based on timestamp
            logger.info("Progress cleanup relies on Redis TTL")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old progress entries: {e}")
    
    async def clear_all_active_tasks(self) -> int:
        """Clear all active task progress data"""
        try:
            async with RedisService() as client:
                keys = await client.keys(f"{self.progress_key_prefix}*")
                
                if not keys:
                    logger.info("No active tasks found to clear")
                    return 0
                
                # Delete all task progress keys
                for key in keys:
                    await client.delete(key)
                
                logger.info(f"Cleared {len(keys)} active tasks")
                return len(keys)
                
        except Exception as e:
            logger.error(f"Failed to clear all active tasks: {e}")
            return 0

    async def complete_task_progress(self, task_id: str) -> bool:
        """
        Complete and clean up task progress when processing finishes successfully
        
        Args:
            task_id: Celery task ID
            
        Returns:
            True if progress was cleaned up successfully
        """
        try:
            progress_key = f"{self.progress_key_prefix}{task_id}"
            
            # Task'ı tamamlandı olarak işaretle ve kısa süre sonra silinmesini sağla
            async with RedisService() as client:
                await client.setex(
                    progress_key,
                    60,  # 1 dakika sonra otomatik silinecek
                    json.dumps({
                        "status": "completed",
                        "completed_at": datetime.utcnow().isoformat(),
                        "percentage": 100
                    })
                )
            
            logger.info(f"Task progress marked as completed and will auto-expire: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to complete task progress {task_id}: {e}")
            return False

    async def initialize_batch_progress(
        self, 
        batch_id: str, 
        total_files: int,
        admin_id: str
    ) -> None:
        """Initialize progress tracking for a batch upload"""
        try:
            batch_data = {
                "batch_id": batch_id,
                "admin_id": admin_id,
                "total_files": total_files,
                "status": "processing",
                "queued_count": total_files,
                "processing_count": 0,
                "completed_count": 0,
                "failed_count": 0,
                "created_at": datetime.utcnow().isoformat(),
                "completed_at": None
            }
            
            key = f"{self.batch_key_prefix}{batch_id}"
            async with RedisService() as client:
                await client.setex(key, self.progress_ttl, json.dumps(batch_data))
            logger.info(f"Initialized batch progress for {batch_id} with {total_files} files")
            
        except Exception as e:
            logger.error(f"Failed to initialize batch progress for {batch_id}: {e}")

    async def get_batch_progress(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get progress for all tasks in a batch"""
        try:
            async with RedisService() as client:
                batch_key = f"{self.batch_key_prefix}{batch_id}"
                tasks_key = f"{self.batch_tasks_prefix}{batch_id}"
                
                batch_data_raw = await client.get(batch_key)
                task_ids = await client.smembers(tasks_key)
                
                if not batch_data_raw:
                    return None
                
                batch_data = json.loads(batch_data_raw)
                
                tasks = []
                status_counts = {"queued": 0, "pending": 0, "processing": 0, "completed": 0, "failed": 0}
                
                for task_id_raw in task_ids:
                    task_id = task_id_raw.decode('utf-8') if isinstance(task_id_raw, bytes) else task_id_raw
                    task_data = await self.get_task_progress(task_id)
                    if task_data:
                        tasks.append(task_data)
                        status = task_data.get("status", "pending")
                        status_counts[status] = status_counts.get(status, 0) + 1
                
                batch_data["tasks"] = tasks
                batch_data["queued_count"] = status_counts.get("queued", 0) + status_counts.get("pending", 0)
                batch_data["processing_count"] = status_counts["processing"]
                batch_data["completed_count"] = status_counts["completed"]
                batch_data["failed_count"] = status_counts["failed"]
                
                if batch_data["completed_count"] + batch_data["failed_count"] >= batch_data["total_files"]:
                    batch_data["status"] = "completed"
                    batch_data["completed_at"] = datetime.utcnow().isoformat()
                
                await client.setex(batch_key, self.progress_ttl, json.dumps(batch_data))
                
                return batch_data
                
        except Exception as e:
            logger.error(f"Failed to get batch progress for {batch_id}: {e}")
            return None

    async def get_tasks_by_ids(self, task_ids: List[str]) -> List[Dict[str, Any]]:
        """Get progress for multiple tasks by their IDs"""
        try:
            tasks = []
            for task_id in task_ids:
                task_data = await self.get_task_progress(task_id)
                if task_data:
                    tasks.append(task_data)
            return tasks
        except Exception as e:
            logger.error(f"Failed to get tasks by IDs: {e}")
            return []

# Global instance
progress_service = ProgressService()