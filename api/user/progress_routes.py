"""
Progress tracking routes for document processing
Allows users to track real-time progress of their document uploads
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Optional
import logging
from models.schemas import TaskProgressResponse, TaskProgress
from services.progress_service import progress_service
from api.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/progress/{task_id}", response_model=TaskProgressResponse)
async def get_task_progress(
    task_id: str,
    current_user=Depends(get_current_user)
):
    """
    Get real-time progress for a document processing task
    
    Args:
        task_id: Celery task ID
        current_user: Authenticated user
        
    Returns:
        Task progress information with percentage and current step
    """
    try:
        logger.info(f"Getting progress for task {task_id} for user {current_user.get('id')}")
        
        # Get progress data from Redis
        progress_data = await progress_service.get_task_progress(task_id)
        
        if not progress_data:
            raise HTTPException(
                status_code=404,
                detail="Task progress not found. Task may have completed or expired."
            )
        
        # Create progress object
        progress = TaskProgress(**progress_data)
        
        logger.info(f"Progress retrieved for task {task_id}: {progress.progress_percent}%")
        
        return TaskProgressResponse(
            task_id=task_id,
            progress=progress,
            success=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get progress for task {task_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve task progress"
        )

@router.delete("/progress/{task_id}")
async def clear_task_progress(
    task_id: str,
    current_user=Depends(get_current_user)
):
    """
    Clear progress data for a completed/failed task
    
    Args:
        task_id: Celery task ID to clear
        current_user: Authenticated user
        
    Returns:
        Success confirmation
    """
    try:
        logger.info(f"Clearing progress for task {task_id} for user {current_user.get('id')}")
        
        # Delete progress data from Redis
        client = await progress_service.redis_service.get_redis_client()
        await client.delete(f"{progress_service.progress_key_prefix}{task_id}")
        
        logger.info(f"Progress cleared for task {task_id}")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Task progress cleared successfully"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to clear progress for task {task_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to clear task progress"
        )

@router.get("/progress")
async def get_user_active_tasks(
    current_user=Depends(get_current_user)
):
    """
    Get all active tasks for the current user
    
    Args:
        current_user: Authenticated user
        
    Returns:
        List of active task progress data
    """
    try:
        user_id = current_user.get('id')
        logger.info(f"Getting active tasks for user {user_id}")
        
        # Get all progress keys from Redis
        client = await progress_service.redis_service.get_redis_client()
        keys = await client.keys(f"{progress_service.progress_key_prefix}*")
        
        active_tasks = []
        
        for key in keys:
            try:
                data = await client.get(key)
                if data:
                    import json
                    progress_data = json.loads(data)
                    
                    # Only include processing/pending tasks
                    if progress_data.get('status') in ['pending', 'processing']:
                        active_tasks.append({
                            "task_id": progress_data.get('task_id'),
                            "document_title": progress_data.get('document_title'),
                            "status": progress_data.get('status'),
                            "progress_percent": progress_data.get('progress_percent', 0),
                            "current_step": progress_data.get('current_step'),
                            "stage": progress_data.get('stage')
                        })
            except Exception as e:
                logger.error(f"Error parsing progress data for key {key}: {e}")
                continue
        
        logger.info(f"Found {len(active_tasks)} active tasks for user {user_id}")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "active_tasks": active_tasks,
                    "count": len(active_tasks)
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get active tasks: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve active tasks"
        )