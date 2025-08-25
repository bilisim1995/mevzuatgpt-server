"""
Public routes for MevzuatGPT - No authentication required
Includes announcements for frontend consumption
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, Dict, Any
import logging
from datetime import datetime

from models.supabase_client import supabase_client
from utils.response import success_response, error_response

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/announcements", response_model=Dict[str, Any])
async def get_public_announcements(
    limit: int = Query(10, ge=1, le=50),
    priority: Optional[str] = Query(None),
    include_inactive: bool = Query(False)
):
    """
    Frontend için aktif duyuruları getir (Public endpoint)
    
    Args:
        limit: Maksimum duyuru sayısı
        priority: Öncelik filtresi (low, normal, high, urgent)
        include_inactive: Pasif duyuruları da dahil et
    """
    try:
        logger.info(f"Public announcements requested - limit: {limit}, priority: {priority}")
        
        # Build query
        query = supabase_client.supabase.table('announcements').select(
            'id, title, content, priority, publish_date, created_at'
        )
        
        # Filter active announcements unless specifically requested
        if not include_inactive:
            query = query.eq('is_active', True)
        
        # Apply priority filter
        if priority:
            valid_priorities = ['low', 'normal', 'high', 'urgent']
            if priority not in valid_priorities:
                raise HTTPException(
                    status_code=400,
                    detail=f"Priority must be one of: {', '.join(valid_priorities)}"
                )
            query = query.eq('priority', priority)
        
        # Filter by publish_date (only show published announcements)
        current_time = datetime.utcnow().isoformat()
        query = query.lte('publish_date', current_time)
        
        # Order by priority and date
        announcements_result = query.order('priority', desc=True).order('publish_date', desc=True).limit(limit).execute()
        
        announcements = []
        if announcements_result.data:
            for announcement in announcements_result.data:
                announcements.append({
                    "id": announcement['id'],
                    "title": announcement['title'],
                    "content": announcement['content'],
                    "priority": announcement['priority'],
                    "publish_date": announcement['publish_date'],
                    "created_at": announcement['created_at']
                })
        
        # Sort by priority order for frontend
        priority_order = {'urgent': 4, 'high': 3, 'normal': 2, 'low': 1}
        announcements.sort(key=lambda x: priority_order.get(x['priority'], 0), reverse=True)
        
        return {
            "success": True,
            "data": {
                "announcements": announcements,
                "total": len(announcements),
                "filters": {
                    "limit": limit,
                    "priority": priority,
                    "include_inactive": include_inactive
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get public announcements: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get announcements: {str(e)}")

@router.get("/announcements/{announcement_id}", response_model=Dict[str, Any])
async def get_public_announcement(
    announcement_id: str
):
    """
    Belirli bir duyuru detayını getir (Public endpoint)
    """
    try:
        logger.info(f"Public announcement requested: {announcement_id}")
        
        response = supabase_client.supabase.table('announcements')\
            .select('id, title, content, priority, publish_date, created_at')\
            .eq('id', announcement_id)\
            .eq('is_active', True)\
            .execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Announcement not found or inactive")
        
        announcement = response.data[0]
        
        # Check if announcement is published
        current_time = datetime.utcnow().isoformat()
        if announcement['publish_date'] > current_time:
            raise HTTPException(status_code=404, detail="Announcement not yet published")
        
        return {
            "success": True,
            "data": {
                "id": announcement['id'],
                "title": announcement['title'],
                "content": announcement['content'],
                "priority": announcement['priority'],
                "publish_date": announcement['publish_date'],
                "created_at": announcement['created_at']
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get public announcement: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get announcement: {str(e)}")

@router.get("/announcements/priority/{priority}", response_model=Dict[str, Any])
async def get_announcements_by_priority(
    priority: str,
    limit: int = Query(10, ge=1, le=50)
):
    """
    Öncelik seviyesine göre duyuruları getir (Public endpoint)
    
    Args:
        priority: Öncelik seviyesi (low, normal, high, urgent)
        limit: Maksimum duyuru sayısı
    """
    try:
        logger.info(f"Announcements by priority requested: {priority}")
        
        # Validate priority
        valid_priorities = ['low', 'normal', 'high', 'urgent']
        if priority not in valid_priorities:
            raise HTTPException(
                status_code=400,
                detail=f"Priority must be one of: {', '.join(valid_priorities)}"
            )
        
        current_time = datetime.utcnow().isoformat()
        
        response = supabase_client.supabase.table('announcements')\
            .select('id, title, content, priority, publish_date, created_at')\
            .eq('priority', priority)\
            .eq('is_active', True)\
            .lte('publish_date', current_time)\
            .order('publish_date', desc=True)\
            .limit(limit)\
            .execute()
        
        announcements = []
        if response.data:
            for announcement in response.data:
                announcements.append({
                    "id": announcement['id'],
                    "title": announcement['title'],
                    "content": announcement['content'],
                    "priority": announcement['priority'],
                    "publish_date": announcement['publish_date'],
                    "created_at": announcement['created_at']
                })
        
        return {
            "success": True,
            "data": {
                "announcements": announcements,
                "priority": priority,
                "total": len(announcements),
                "limit": limit,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get announcements by priority: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get announcements: {str(e)}")