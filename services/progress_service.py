"""
Progress tracking service for long-running tasks
Provides real-time progress updates via Redis
"""
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from core.config import settings
from services.redis_service import redis_service
import logging

logger = logging.getLogger(__name__)

class ProgressService:
    """Service for tracking task progress"""
    
    def __init__(self):
        self.redis_service = redis_service
        self.progress_key_prefix = "task_progress:"
        self.progress_ttl = 3600  # 1 hour TTL for progress data
    
    async def initialize_task_progress(
        self, 
        task_id: str, 
        document_id: str, 
        document_title: str,
        total_steps: int = 5
    ) -> None:
        """Initialize progress tracking for a new task"""
        try:
            progress_data = {
                "task_id": task_id,
                "document_id": document_id,
                "document_title": document_title,
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
            async with self.redis_service as client:
                await client.setex(key, self.progress_ttl, json.dumps(progress_data))
            logger.info(f"Initialized progress tracking for task {task_id}")
            
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
            async with self.redis_service as client:
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
            async with self.redis_service as client:
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
            async with self.redis_service as client:
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

# Global instance
progress_service = ProgressService()