"""
Admin feedback API routes
Admin geri bildirim endpoint'leri
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from api.dependencies import get_admin_user
from services.feedback_service import feedback_service
from models.feedback_schemas import FeedbackListResponse, FeedbackResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feedback", tags=["Admin Feedback"])

@router.get("/", response_model=FeedbackListResponse)
async def get_all_feedback(
    feedback_type: Optional[str] = Query(None, description="Feedback tipi: positive veya negative"),
    page: int = Query(1, ge=1, description="Sayfa numarası"),
    limit: int = Query(50, ge=1, le=200, description="Sayfa başına kayıt sayısı"),
    current_user = Depends(get_admin_user)
):
    """
    Tüm kullanıcı feedback'lerini getir (admin için)
    
    Args:
        feedback_type: Feedback tipi filtresi
        page: Sayfa numarası (1'den başlar)
        limit: Sayfa başına kayıt sayısı
        current_user_id: Mevcut admin kullanıcı ID'si
    
    Returns:
        Tüm feedback'lerin listesi
    """
    try:
        # Feedback type validation
        if feedback_type and feedback_type not in ['positive', 'negative']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="feedback_type 'positive' veya 'negative' olmalı"
            )
        
        offset = (page - 1) * limit
        result = await feedback_service.get_all_feedback_admin(
            feedback_type=feedback_type,
            limit=limit,
            offset=offset
        )
        
        return FeedbackListResponse(
            feedback_list=[FeedbackResponse(**fb) for fb in result['feedback_list']],
            total_count=result['total_count'],
            has_more=result['has_more'],
            page=page,
            limit=limit
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get all feedback error for admin {current_user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Feedback listesi getirilemedi"
        )

@router.get("/user/{user_id}", response_model=FeedbackListResponse)
async def get_user_feedback_admin(
    user_id: str,
    page: int = Query(1, ge=1, description="Sayfa numarası"),
    limit: int = Query(50, ge=1, le=200, description="Sayfa başına kayıt sayısı"),
    current_user = Depends(get_admin_user)
):
    """
    Belirli bir kullanıcının feedback'lerini getir (admin için)
    
    Args:
        user_id: Hedef kullanıcı ID'si
        page: Sayfa numarası (1'den başlar)
        limit: Sayfa başına kayıt sayısı
        current_user_id: Mevcut admin kullanıcı ID'si
    
    Returns:
        Kullanıcının feedback listesi
    """
    try:
        offset = (page - 1) * limit
        feedback_list = await feedback_service.get_user_feedback(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        # Total count için basit hesaplama
        all_feedback = await feedback_service.get_user_feedback(
            user_id=user_id,
            limit=1000000
        )
        total_count = len(all_feedback)
        
        return FeedbackListResponse(
            feedback_list=[FeedbackResponse(**fb) for fb in feedback_list],
            total_count=total_count,
            has_more=total_count > (offset + limit),
            page=page,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"Get user feedback admin error for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Kullanıcı feedback listesi getirilemedi"
        )

@router.delete("/{feedback_id}")
async def delete_feedback_admin(
    feedback_id: str,
    current_user = Depends(get_admin_user)
):
    """
    Herhangi bir feedback'i sil (admin için)
    
    Args:
        feedback_id: Feedback ID'si
        current_user_id: Mevcut admin kullanıcı ID'si
    
    Returns:
        Silme işlemi sonucu
    """
    try:
        # Admin için özel silme işlemi
        from models.supabase_client import supabase_client
        
        response = supabase_client.supabase.table('user_feedback') \
            .delete() \
            .eq('id', feedback_id) \
            .execute()
        
        if response.data:
            logger.info(f"Feedback deleted by admin {current_user.id}: {feedback_id}")
            return {"message": "Feedback başarıyla silindi"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Feedback bulunamadı"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete feedback admin error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Feedback silinemedi"
        )