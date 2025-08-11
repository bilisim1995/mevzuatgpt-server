"""
Admin maintenance mode routes - maintenance management endpoints
"""

import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from utils.response import success_response
from api.dependencies import get_current_user, require_admin
from utils.exceptions import AppException
from services.maintenance_service import MaintenanceService
from models.maintenance_schemas import (
    MaintenanceDetailResponse, 
    MaintenanceUpdateRequest
)
from models.schemas import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/maintenance", response_model=MaintenanceDetailResponse)
async def get_maintenance_details(
    current_user: UserResponse = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed maintenance mode information
    
    Admin only endpoint - returns complete maintenance configuration
    including admin metadata and timestamps.
    
    Args:
        current_user: Current authenticated admin user
        db: Database session
    
    Returns:
        Detailed maintenance mode configuration
    """
    try:
        maintenance_service = MaintenanceService(db)
        
        details = await maintenance_service.get_maintenance_details()
        
        logger.info(f"Maintenance details requested by admin {current_user.id}")
        
        return success_response(data=details.model_dump(mode='json'))
        
    except Exception as e:
        logger.error(f"Error getting maintenance details for admin {current_user.id}: {str(e)}")
        raise AppException(
            message="Maintenance details retrieval failed",
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.put("/maintenance", response_model=MaintenanceDetailResponse)
async def update_maintenance_mode(
    request: MaintenanceUpdateRequest,
    current_user: UserResponse = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update system maintenance mode
    
    Admin only endpoint - enables/disables maintenance mode
    and updates maintenance message and timing.
    
    Args:
        request: Maintenance update parameters
        current_user: Current authenticated admin user
        db: Database session
    
    Returns:
        Updated maintenance mode configuration
    """
    try:
        maintenance_service = MaintenanceService(db)
        
        # Update maintenance mode
        updated_details = await maintenance_service.update_maintenance_mode(
            request=request,
            admin_user_id=str(current_user.id)
        )
        
        action = "enabled" if request.is_enabled else "disabled"
        logger.info(f"Maintenance mode {action} by admin {current_user.id}")
        
        return success_response(data=updated_details.model_dump(mode='json'))
        
    except Exception as e:
        logger.error(f"Error updating maintenance mode by admin {current_user.id}: {str(e)}")
        raise AppException(
            message="Maintenance mode update failed",
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )