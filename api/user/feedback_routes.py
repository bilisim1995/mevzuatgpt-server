"""
User feedback API routes
Kullanıcı geri bildirim endpoint'leri
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from api.dependencies import get_current_user
from services.feedback_service import feedback_service
from models.feedback_schemas import (
    FeedbackSubmit,
    FeedbackResponse, 
    FeedbackListResponse,
    FeedbackOperationResponse
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feedback", tags=["User Feedback"])

@router.post("/", response_model=FeedbackOperationResponse)
async def submit_feedback(
    feedback_data: FeedbackSubmit,
    current_user = Depends(get_current_user)
):
    """
    Kullanıcı feedback'i gönder veya güncelle
    
    Aynı sorgu için daha önce feedback verilmişse günceller,
    yoksa yeni feedback oluşturur.
    
    Args:
        feedback_data: Feedback bilgileri
        current_user_id: Mevcut kullanıcı ID'si
    
    Returns:
        İşlem sonucu
    """
    try:
        current_user_id = str(current_user.id)
        
        # Önce search_log'dan query ve answer bilgilerini al
        # Bu bilgileri feedback tablosunda tutmak için gerekli
        from models.supabase_client import supabase_client
        
        search_response = supabase_client.supabase.table('search_logs') \
            .select('query') \
            .eq('id', feedback_data.search_log_id) \
            .eq('user_id', current_user_id) \
            .execute()
        
        if not search_response.data or len(search_response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Belirtilen sorgu bulunamadı veya size ait değil"
            )
        
        search_data = search_response.data[0]
        query_text = search_data.get('query', '')
        answer_text = 'AI yanıtı'  # Basitleştirilmiş versiyon
        
        # Feedback'i kaydet/güncelle
        result = await feedback_service.submit_feedback(
            user_id=current_user_id,
            search_log_id=feedback_data.search_log_id,
            query_text=query_text,
            answer_text=answer_text,
            feedback_type=feedback_data.feedback_type,
            feedback_comment=feedback_data.feedback_comment
        )
        
        logger.info(f"Feedback submitted by user {current_user_id}: {feedback_data.feedback_type}")
        return FeedbackOperationResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        current_user_id = str(current_user.id) if hasattr(current_user, 'id') else 'unknown'
        logger.error(f"Feedback submission error for user {current_user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Feedback gönderilirken hata oluştu"
        )

@router.get("/my", response_model=FeedbackListResponse)
async def get_my_feedback(
    page: int = Query(1, ge=1, description="Sayfa numarası"),
    limit: int = Query(20, ge=1, le=100, description="Sayfa başına kayıt sayısı"),
    current_user = Depends(get_current_user)
):
    """
    Kullanıcının kendi feedback geçmişini getir
    
    Args:
        page: Sayfa numarası (1'den başlar)
        limit: Sayfa başına kayıt sayısı
        current_user_id: Mevcut kullanıcı ID'si
    
    Returns:
        Kullanıcının feedback listesi
    """
    try:
        current_user_id = str(current_user.id)
        offset = (page - 1) * limit
        feedback_list = await feedback_service.get_user_feedback(
            user_id=current_user_id,
            limit=limit,
            offset=offset
        )
        
        # Total count için ayrı sorgu (basit implementasyon)
        total_feedback = await feedback_service.get_user_feedback(
            user_id=current_user_id,
            limit=1000000  # Büyük sayı ile tüm kayıtları say
        )
        total_count = len(total_feedback)
        
        return FeedbackListResponse(
            feedback_list=[FeedbackResponse(**fb) for fb in feedback_list],
            total_count=total_count,
            has_more=total_count > (offset + limit),
            page=page,
            limit=limit
        )
        
    except Exception as e:
        current_user_id = str(current_user.id) if hasattr(current_user, 'id') else 'unknown'
        logger.error(f"Get user feedback error for user {current_user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Feedback geçmişi getirilemedi"
        )

@router.get("/search/{search_log_id}", response_model=Optional[FeedbackResponse])
async def get_feedback_by_search(
    search_log_id: str,
    current_user = Depends(get_current_user)
):
    """
    Belirli bir sorgu için feedback'i getir
    
    Args:
        search_log_id: Search log ID'si
        current_user_id: Mevcut kullanıcı ID'si
    
    Returns:
        Feedback bilgisi (varsa)
    """
    try:
        current_user_id = str(current_user.id)
        feedback = await feedback_service.get_feedback_by_search_log(
            user_id=current_user_id,
            search_log_id=search_log_id
        )
        
        if feedback:
            return FeedbackResponse(**feedback)
        return None
        
    except Exception as e:
        logger.error(f"Get feedback by search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Feedback bilgisi getirilemedi"
        )

@router.delete("/{feedback_id}")
async def delete_feedback(
    feedback_id: str,
    current_user = Depends(get_current_user)
):
    """
    Kendi feedback'ini sil
    
    Args:
        feedback_id: Feedback ID'si
        current_user_id: Mevcut kullanıcı ID'si
    
    Returns:
        Silme işlemi sonucu
    """
    try:
        current_user_id = str(current_user.id)
        success = await feedback_service.delete_feedback(
            feedback_id=feedback_id,
            user_id=current_user_id
        )
        
        if success:
            return {"message": "Feedback başarıyla silindi"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Feedback bulunamadı veya silinemedi"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete feedback error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Feedback silinemedi"
        )