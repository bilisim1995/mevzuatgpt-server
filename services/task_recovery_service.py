"""
Task Recovery Service
Automatically recovers orphaned Celery tasks after worker restarts
"""

import logging
import json
from typing import List, Dict, Any
from datetime import datetime

from services.redis_service import RedisService
from core.database import AsyncSessionLocal
from sqlalchemy import select
from models.supabase_models import MevzuatDocument

logger = logging.getLogger(__name__)


class TaskRecoveryService:
    """
    Service to recover orphaned bulk upload tasks after worker crashes/restarts
    """
    
    def __init__(self):
        self.redis_service = RedisService()
    
    async def recover_orphaned_tasks(self) -> Dict[str, Any]:
        """
        Scan Redis for orphaned bulk upload tasks and re-queue them
        
        Returns:
            Recovery summary with counts and task IDs
        """
        logger.info("🔄 Starting orphaned task recovery...")
        
        try:
            # Get all bulk_upload keys from Redis
            pattern = "bulk_upload:*"
            keys = await self.redis_service.redis_client.keys(pattern)
            
            if not keys:
                logger.info("✅ No bulk upload tasks found in Redis")
                return {
                    "recovered": 0,
                    "skipped": 0,
                    "failed": 0,
                    "tasks": []
                }
            
            logger.info(f"📊 Found {len(keys)} bulk upload task(s) in Redis")
            
            recovered_count = 0
            skipped_count = 0
            failed_count = 0
            recovered_tasks = []
            
            for key in keys:
                # Extract task_id from key (bulk_upload:TASK_ID)
                task_id = key.decode("utf-8").replace("bulk_upload:", "")
                
                # Get task data
                task_data_raw = await self.redis_service.redis_client.get(key)
                if not task_data_raw:
                    logger.warning(f"⚠️ No data for task {task_id}")
                    continue
                
                task_data = json.loads(task_data_raw)
                status = task_data.get("status")
                total_files = task_data.get("total_files", 0)
                completed_files = len(task_data.get("completed_files", []))
                
                logger.info(f"📋 Task {task_id}: status={status}, progress={completed_files}/{total_files}")
                
                # Only recover tasks that are queued or processing (not completed/failed)
                if status in ["queued", "processing"]:
                    try:
                        # Attempt to recover task
                        success = await self._recover_single_task(task_id, task_data)
                        
                        if success:
                            recovered_count += 1
                            recovered_tasks.append({
                                "task_id": task_id,
                                "total_files": total_files,
                                "completed_files": completed_files,
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
        Recover a single orphaned task by rebuilding document payload and re-queuing
        
        Args:
            task_id: Bulk upload task ID
            task_data: Redis progress data for this task
            
        Returns:
            True if recovery successful, False otherwise
        """
        try:
            filenames = task_data.get("filenames", [])
            completed_files = task_data.get("completed_files", [])
            completed_filenames = [f["filename"] for f in completed_files]
            
            # Get remaining files to process
            remaining_filenames = [f for f in filenames if f not in completed_filenames]
            
            if not remaining_filenames:
                logger.info(f"✅ Task {task_id} already completed (no remaining files)")
                # Update status to completed
                await self.redis_service.update_bulk_upload_progress(task_id, {
                    "status": "completed",
                    "completed_at": datetime.utcnow().isoformat()
                })
                return True
            
            logger.info(f"📝 Task {task_id}: {len(remaining_filenames)} files remaining")
            
            # Fetch document metadata from Supabase for remaining files
            async with AsyncSessionLocal() as session:
                # Query documents by filename
                result = await session.execute(
                    select(MevzuatDocument).where(
                        MevzuatDocument.filename.in_(remaining_filenames)
                    )
                )
                documents_db = result.scalars().all()
            
            if not documents_db:
                logger.error(f"❌ No documents found in database for task {task_id}")
                return False
            
            # Rebuild document payload
            documents = []
            for doc in documents_db:
                documents.append({
                    "filename": doc.filename,
                    "document_id": str(doc.id),
                    "metadata": {
                        "title": doc.title,
                        "description": doc.title,  # Use title as description if no specific description
                        "keywords": doc.category or "legal"
                    }
                })
            
            logger.info(f"📦 Rebuilt payload with {len(documents)} documents")
            
            # Re-queue Celery task
            from tasks.document_processor import bulk_process_documents_task
            
            task_payload = {
                "task_id": task_id,
                "documents": documents,
                "user_id": task_data.get("user_id", "system_recovery")  # Fallback user_id
            }
            
            # Update status to processing
            await self.redis_service.update_bulk_upload_progress(task_id, {
                "status": "processing",
                "recovered_at": datetime.utcnow().isoformat(),
                "recovery_reason": "Worker restart detected"
            })
            
            # Queue task
            celery_task = bulk_process_documents_task.delay(task_payload)
            logger.info(f"✅ Re-queued task {task_id} as Celery task {celery_task.id}")
            
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
            pattern = "bulk_upload:*"
            keys = await self.redis_service.redis_client.keys(pattern)
            
            cleaned_count = 0
            current_time = datetime.utcnow()
            
            for key in keys:
                task_data_raw = await self.redis_service.redis_client.get(key)
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
                        await self.redis_service.redis_client.delete(key)
                        cleaned_count += 1
                        logger.info(f"🗑️ Cleaned up task {key.decode('utf-8')}")
            
            logger.info(f"✅ Cleanup complete: {cleaned_count} tasks removed")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {str(e)}")
            return 0
