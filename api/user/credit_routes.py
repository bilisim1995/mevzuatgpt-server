"""
Kullanıcı Kredi API Endpoints

Kullanıcıların kredi bakiyelerini ve transaction geçmişlerini görüntülemek için API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
import logging

from api.dependencies import get_current_user
from services.credit_service import credit_service
from utils.exceptions import AppException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user/credits", tags=["user-credits"])

@router.get("/balance", response_model=Dict[str, Any])
async def get_credit_balance(current_user: dict = Depends(get_current_user)):
    """
    Kullanıcının mevcut kredi bakiyesini getir
    
    Returns:
        Kredi bakiye bilgileri
    """
    try:
        user_id = current_user["id"]
        balance = await credit_service.get_user_balance(user_id)
        is_admin = await credit_service.is_admin_user(user_id)
        
        return {
            "success": True,
            "data": {
                "current_balance": balance,
                "is_admin": is_admin,
                "unlimited": is_admin  # Admin kullanıcılar için unlimited
            }
        }
        
    except Exception as e:
        logger.error(f"Kredi bakiye getirme hatası: {e}")
        raise HTTPException(
            status_code=500,
            detail="Kredi bakiyesi getirilemedi"
        )

@router.get("/history", response_model=Dict[str, Any])
async def get_credit_history(
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """
    Kullanıcının kredi transaction geçmişini getir
    
    Args:
        limit: Maksimum kayıt sayısı (varsayılan: 20)
    
    Returns:
        Transaction geçmişi
    """
    try:
        user_id = current_user["id"]
        
        if limit > 100:
            limit = 100  # Maksimum limit
        
        history = await credit_service.get_transaction_history(user_id, limit)
        
        # Transaction'ları kullanıcı dostu formata çevir
        formatted_history = []
        for tx in history:
            formatted_tx = {
                "id": tx["id"],
                "type": tx["transaction_type"],
                "amount": tx["amount"],
                "balance_after": tx["balance_after"],
                "description": tx["description"],
                "date": tx["created_at"],
                "query_id": tx.get("query_id")
            }
            formatted_history.append(formatted_tx)
        
        return {
            "success": True,
            "data": {
                "transactions": formatted_history,
                "total_count": len(formatted_history)
            }
        }
        
    except Exception as e:
        logger.error(f"Kredi geçmişi getirme hatası: {e}")
        raise HTTPException(
            status_code=500,
            detail="Kredi geçmişi getirilemedi"
        )

@router.get("/summary", response_model=Dict[str, Any])
async def get_credit_summary(current_user: dict = Depends(get_current_user)):
    """
    Kullanıcının kredi özet bilgilerini getir
    
    Returns:
        Detaylı kredi özeti
    """
    try:
        user_id = current_user["id"]
        summary = await credit_service.get_credit_summary(user_id)
        
        return {
            "success": True,
            "data": summary
        }
        
    except Exception as e:
        logger.error(f"Kredi özet getirme hatası: {e}")
        raise HTTPException(
            status_code=500,
            detail="Kredi özeti getirilemedi"
        )