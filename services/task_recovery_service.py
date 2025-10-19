"""
Task Recovery Service
Automatically recovers orphaned Celery tasks after worker restarts
"""

import logging
import json
from typing import List, Dict, Any
from datetime import datetime

from services.redis_service import RedisService

logger = logging.getLogger(__name__)


class TaskRecoveryService:
    """
    Service to recover orphaned bulk upload tasks after worker crashes/restarts
    """
    
    def __init__(self):
        self.redis_service = RedisService()
    
    async def recover_orphaned_tasks(self) -> Dict[str, Any]:
        """
        Scan Redis for orphaned individual tasks and re-queue them
        
        Returns:
            Recovery summary with counts and task IDs
        """
        logger.info("🔄 Starting orphaned task recovery...")
        
        try:
            async with RedisService() as client:
                # Get all task_progress keys from Redis
                pattern = "task_progress:*"
                keys = await client.keys(pattern)
                
                if not keys:
                    logger.info("✅ No tasks found in Redis")
                    return {
                        "recovered": 0,
                        "skipped": 0,
                        "failed": 0,
                        "tasks": []
                    }
                
                logger.info(f"📊 Found {len(keys)} task(s) in Redis")
                
                recovered_count = 0
                skipped_count = 0
                failed_count = 0
                recovered_tasks = []
                
                for key_raw in keys:
                    # Decode and extract task_id from key (task_progress:TASK_ID)
                    key = key_raw.decode('utf-8') if isinstance(key_raw, bytes) else key_raw
                    task_id = key.replace("task_progress:", "")
                    
                    # Get task data
                    task_data_raw = await client.get(key)
                    if not task_data_raw:
                        logger.warning(f"⚠️ No data for task {task_id}")
                        continue
                    
                    task_data = json.loads(task_data_raw)
                    status = task_data.get("status")
                    document_id = task_data.get("document_id")
                    filename = task_data.get("filename", "unknown")
                    
                    logger.info(f"📋 Task {task_id}: status={status}, document={document_id}, file={filename}")
                    
                    # Only recover tasks that are queued or processing (not completed/failed)
                    if status in ["queued", "pending", "processing"]:
                        try:
                            # Attempt to recover task
                            success = await self._recover_single_task(task_id, task_data)
                            
                            if success:
                                recovered_count += 1
                                recovered_tasks.append({
                                    "task_id": task_id,
                                    "document_id": document_id,
                                    "filename": filename,
                                    "status": status
                                })
                                logger.info(f"✅ Recovered task {task_id}")
                            else:
                                failed_count += 1
                                logger.error(f"❌ Failed to recover task {task_id}")
                                
                        except Exception as e:
                            failed_count += 1
                            logger.error(f"❌ Error recovering task {task_id}: {str(e)}")
                    else:
                        skipped_count += 1
                        logger.info(f"⏭️ Skipping task {task_id} (status: {status})")
                
                summary = {
                    "recovered": recovered_count,
                    "skipped": skipped_count,
                    "failed": failed_count,
                    "tasks": recovered_tasks
                }
                
                logger.info(f"🎯 Recovery complete: {recovered_count} recovered, {skipped_count} skipped, {failed_count} failed")
                return summary
            
        except Exception as e:
            logger.error(f"❌ Task recovery failed: {str(e)}")
            return {
                "recovered": 0,
                "skipped": 0,
                "failed": 0,
                "error": str(e)
            }
    
    async def _recover_single_task(self, task_id: str, task_data: Dict[str, Any]) -> bool:
        """
        Recover a single orphaned task by re-queuing the document processing task
        
        Args:
            task_id: Individual task ID
            task_data: Redis progress data for this task
            
        Returns:
            True if recovery successful, False otherwise
        """
        try:
            document_id = task_data.get("document_id")
            
            if not document_id:
                logger.error(f"❌ No document_id found for task {task_id}")
                return False
            
            logger.info(f"📝 Recovering task {task_id} for document {document_id}")
            
            # Re-queue Celery task with specific task_id to maintain tracking
            from tasks.document_processor import process_document_task
            
            # Reset status to queued
            from services.progress_service import progress_service
            async with RedisService() as client:
                task_key = f"task_progress:{task_id}"
                task_data["status"] = "queued"
                task_data["recovered_at"] = datetime.utcnow().isoformat()
                task_data["recovery_reason"] = "Worker restart detected"
                await client.setex(task_key, 3600, json.dumps(task_data))
            
            # Queue task
            celery_task = process_document_task.apply_async(
                args=[document_id],
                task_id=task_id  # Use same task_id to maintain progress tracking
            )
            logger.info(f"✅ Re-queued task {task_id} for document {document_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to recover task {task_id}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        """
        Clean up old completed/failed tasks from Redis
        
        Args:
            max_age_hours: Maximum age in hours for completed tasks
            
        Returns:
            Number of tasks cleaned up
        """
        logger.info(f"🧹 Cleaning up tasks older than {max_age_hours} hours...")
        
        try:
            async with RedisService() as client:
                pattern = "task_progress:*"
                keys = await client.keys(pattern)
                
                cleaned_count = 0
                current_time = datetime.utcnow()
                
                for key_raw in keys:
                    key = key_raw.decode('utf-8') if isinstance(key_raw, bytes) else key_raw
                    task_data_raw = await client.get(key)
                    if not task_data_raw:
                        continue
                    
                    task_data = json.loads(task_data_raw)
                    status = task_data.get("status")
                    
                    # Only clean up completed/failed tasks
                    if status not in ["completed", "failed"]:
                        continue
                    
                    # Check age
                    completed_at = task_data.get("completed_at")
                    if completed_at:
                        completed_time = datetime.fromisoformat(completed_at)
                        age_hours = (current_time - completed_time).total_seconds() / 3600
                        
                        if age_hours > max_age_hours:
                            await client.delete(key)
                            cleaned_count += 1
                            logger.info(f"🗑️ Cleaned up task {key}")
                
                logger.info(f"✅ Cleanup complete: {cleaned_count} tasks removed")
                return cleaned_count
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {str(e)}")
            return 0
