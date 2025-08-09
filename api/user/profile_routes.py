"""
User profile management routes
Handles user profile updates with extended personal information
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from services.supabase_auth_service import auth_service
from models.schemas import UserResponse, UserProfileUpdate
from api.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/profile", response_model=UserResponse)
async def get_user_profile(current_user: UserResponse = Depends(get_current_user)):
    """
    Kullanıcının profil bilgilerini getir
    
    Returns:
        Tam kullanıcı profil bilgileri (ad, soyad, meslek, çalıştığı yer dahil)
    """
    return current_user

@router.put("/profile", response_model=UserResponse)
async def update_user_profile(
    profile_data: UserProfileUpdate,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Kullanıcı profil bilgilerini güncelle
    
    Args:
        profile_data: Güncellenecek profil bilgileri (ad, soyad, meslek, çalıştığı yer)
        current_user: Mevcut kullanıcı
        
    Returns:
        Güncellenmiş kullanıcı bilgileri
    """
    try:
        # Profil güncellemesi için Supabase çağrısı
        success = await auth_service.update_user_profile(str(current_user.id), profile_data)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Profil güncelleme başarısız"
            )
        
        # Güncellenmiş kullanıcı bilgilerini getir
        updated_user = await auth_service.get_user_by_id(str(current_user.id))
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Kullanıcı bulunamadı"
            )
        
        logger.info(f"User profile updated: {current_user.email}")
        return updated_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile update error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profil güncelleme sırasında hata oluştu"
        )