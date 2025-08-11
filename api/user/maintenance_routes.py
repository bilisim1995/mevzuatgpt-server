"""
User maintenance mode routes - public maintenance status endpoint
"""

import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from utils.response import success_response
from services.maintenance_service import MaintenanceService
from models.maintenance_schemas import MaintenanceStatusResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/status", response_model=MaintenanceStatusResponse)
async def get_maintenance_status(
    db: AsyncSession = Depends(get_db)
):
    """
    Get current system maintenance status
    
    Public endpoint - no authentication required.
    Returns maintenance mode status and message for user display.
    
    Args:
        db: Database session
    
    Returns:
        Current maintenance mode status with user-friendly message
    """
    try:
        maintenance_service = MaintenanceService(db)
        
        status = await maintenance_service.get_maintenance_status()
        
        logger.info(f"Maintenance status requested: enabled={status.is_enabled}")
        
        return success_response(data=status.model_dump(mode='json'))
        
    except Exception as e:
        logger.error(f"Error getting maintenance status: {str(e)}")
        # Return safe default on error
        return success_response(data={
            "is_enabled": False,
            "title": "Sistem Durumu Bilinmiyor",
            "message": "Sistem durumu kontrol edilemiyor, lütfen daha sonra tekrar deneyin.",
            "start_time": None,
            "end_time": None
        })