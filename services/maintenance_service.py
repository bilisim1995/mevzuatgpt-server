"""
Maintenance mode service for system maintenance management
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from models.maintenance_schemas import (
    MaintenanceStatusResponse, 
    MaintenanceUpdateRequest, 
    MaintenanceDetailResponse
)
from core.supabase_client import supabase_client

logger = logging.getLogger(__name__)


class MaintenanceService:
    """Service for managing system maintenance mode"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.supabase = supabase_client.service_client  # Use service client for admin operations
    
    async def get_maintenance_status(self) -> MaintenanceStatusResponse:
        """
        Get current maintenance mode status (public endpoint)
        
        Returns:
            Maintenance status for user consumption
        """
        try:
            # Get maintenance status from database
            result = self.supabase.table('maintenance_mode') \
                .select('is_enabled, title, message, start_time, end_time') \
                .limit(1) \
                .execute()
            
            if result.data and len(result.data) > 0:
                data = result.data[0]
                return MaintenanceStatusResponse(
                    is_enabled=data.get('is_enabled', False),
                    title=data.get('title', 'Sistem Bakımda'),
                    message=data.get('message', 'Sistem geçici olarak bakım modunda.'),
                    start_time=data.get('start_time'),
                    end_time=data.get('end_time')
                )
            else:
                # Default response if no maintenance record found
                return MaintenanceStatusResponse(
                    is_enabled=False,
                    title='Sistem Aktif',
                    message='Sistem normal çalışıyor.'
                )
                
        except Exception as e:
            logger.error(f"Error getting maintenance status: {e}")
            # Return safe default on error
            return MaintenanceStatusResponse(
                is_enabled=False,
                title='Sistem Durumu Bilinmiyor',
                message='Sistem durumu kontrol edilemiyor.'
            )
    
    async def get_maintenance_details(self) -> MaintenanceDetailResponse:
        """
        Get detailed maintenance mode information (admin endpoint)
        
        Returns:
            Detailed maintenance information for admin consumption
        """
        try:
            # Get full maintenance details
            result = self.supabase.table('maintenance_mode') \
                .select('*') \
                .limit(1) \
                .execute()
            
            if result.data and len(result.data) > 0:
                data = result.data[0]
                return MaintenanceDetailResponse(
                    id=data['id'],
                    is_enabled=data.get('is_enabled', False),
                    title=data.get('title', 'Sistem Bakımda'),
                    message=data.get('message', 'Sistem geçici olarak bakım modunda.'),
                    start_time=data.get('start_time'),
                    end_time=data.get('end_time'),
                    updated_by=None,  # Bu alan artık kullanılmıyor
                    created_at=data['created_at'],
                    updated_at=data['updated_at']
                )
            else:
                raise Exception("No maintenance record found")
                
        except Exception as e:
            logger.error(f"Error getting maintenance details: {e}")
            raise e
    
    async def update_maintenance_mode(
        self, 
        request: MaintenanceUpdateRequest, 
        admin_user_id: str
    ) -> MaintenanceDetailResponse:
        """
        Update maintenance mode settings (admin only)
        
        Args:
            request: Maintenance update request
            admin_user_id: ID of admin user making the update
            
        Returns:
            Updated maintenance details
        """
        try:
            # Prepare update data
            update_data = {
                'is_enabled': request.is_enabled,
                'updated_at': datetime.utcnow().isoformat()
            }
            # Note: updated_by kolonu tablodan kaldırıldı
            
            # Add optional fields if provided
            if request.title is not None:
                update_data['title'] = request.title
            if request.message is not None:
                update_data['message'] = request.message
            if request.start_time is not None:
                update_data['start_time'] = request.start_time.isoformat()
            if request.end_time is not None:
                update_data['end_time'] = request.end_time.isoformat()
            
            # Önce mevcut maintenance kaydını al (genelde tek kayıt vardır)
            existing_result = self.supabase.table('maintenance_mode') \
                .select('id') \
                .limit(1) \
                .execute()
                
            if existing_result.data and len(existing_result.data) > 0:
                # Mevcut kayıt var - güncelle
                existing_id = existing_result.data[0]['id']
                result = self.supabase.table('maintenance_mode') \
                    .update(update_data) \
                    .eq('id', existing_id) \
                    .execute()
            else:
                # Hiç kayıt yok - yeni oluştur (UUID otomatik oluşturulacak)
                insert_data = update_data.copy()
                insert_data['created_at'] = datetime.utcnow().isoformat()
                
                result = self.supabase.table('maintenance_mode') \
                    .insert(insert_data) \
                    .execute()
            
            if result.data and len(result.data) > 0:
                data = result.data[0]
                
                logger.info(f"Maintenance mode updated by admin {admin_user_id}: enabled={request.is_enabled}")
                
                return MaintenanceDetailResponse(
                    id=data['id'],
                    is_enabled=data.get('is_enabled', False),
                    title=data.get('title', 'Sistem Bakımda'),
                    message=data.get('message', 'Sistem geçici olarak bakım modunda.'),
                    start_time=data.get('start_time'),
                    end_time=data.get('end_time'),
                    updated_by=None,  # Bu alan artık kullanılmıyor
                    created_at=data['created_at'],
                    updated_at=data['updated_at']
                )
            else:
                raise Exception("Failed to update maintenance mode")
                
        except Exception as e:
            logger.error(f"Error updating maintenance mode: {e}")
            raise e
    
    async def is_maintenance_active(self) -> bool:
        """
        Quick check if maintenance mode is currently active
        
        Returns:
            True if maintenance mode is enabled
        """
        try:
            status = await self.get_maintenance_status()
            return status.is_enabled
        except Exception as e:
            logger.error(f"Error checking maintenance status: {e}")
            # Return False on error to allow system operation
            return False