"""
Admin Kredi Yönetim API Endpoints

Admin kullanıcıların diğer kullanıcıların kredi bakiyelerini yönetmesi için API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, List, Optional
import logging

from api.dependencies import get_current_user_admin
from services.credit_service import credit_service
from utils.exceptions import AppException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/credits", tags=["admin-credits"])

class AddCreditsRequest(BaseModel):
    user_id: str
    amount: int
    description: str = "Admin tarafından eklenen kredi"

class SetCreditsRequest(BaseModel):
    user_id: str
    amount: int
    description: str = "Admin tarafından belirlenen kredi"

@router.post("/add", response_model=Dict[str, Any])
async def add_user_credits(
    request: AddCreditsRequest,
    current_user: dict = Depends(get_current_user_admin)
):
    """
    Kullanıcıya kredi ekle (sadece admin)
    
    Args:
        request: Kredi ekleme isteği
        current_user: Mevcut admin kullanıcı
        
    Returns:
        İşlem sonucu ve güncel bakiye
    """
    try:
        # Mevcut bakiyeyi al
        current_balance = await credit_service.get_user_balance(request.user_id)
        new_balance = current_balance + request.amount
        
        # Credit transaction kaydet
        from models.supabase_client import supabase_client
        transaction_data = {
            'user_id': request.user_id,
            'transaction_type': 'admin_add',
            'amount': request.amount,
            'balance_after': new_balance,
            'description': f"{request.description} (Admin: {current_user['email']})"
        }
        
        response = supabase_client.supabase.table('user_credits') \
            .insert(transaction_data) \
            .execute()
        
        if response.data:
            logger.info(f"Admin {current_user['email']} added {request.amount} credits to user {request.user_id}")
            return {
                "success": True,
                "data": {
                    "user_id": request.user_id,
                    "credits_added": request.amount,
                    "previous_balance": current_balance,
                    "new_balance": new_balance,
                    "transaction_id": response.data[0]['id']
                }
            }
        else:
            raise AppException(message="Kredi ekleme işlemi başarısız")
            
    except Exception as e:
        logger.error(f"Admin credit addition error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Kredi ekleme işlemi başarısız oldu"
        )

@router.post("/set", response_model=Dict[str, Any])
async def set_user_credits(
    request: SetCreditsRequest,
    current_user: dict = Depends(get_current_user_admin)
):
    """
    Kullanıcının kredi bakiyesini belirli bir değere ayarla (sadece admin)
    
    Args:
        request: Kredi ayarlama isteği
        current_user: Mevcut admin kullanıcı
        
    Returns:
        İşlem sonucu ve güncel bakiye
    """
    try:
        # Mevcut bakiyeyi al
        current_balance = await credit_service.get_user_balance(request.user_id)
        difference = request.amount - current_balance
        
        # Credit transaction kaydet
        from models.supabase_client import supabase_client
        transaction_data = {
            'user_id': request.user_id,
            'transaction_type': 'admin_set',
            'amount': difference,
            'balance_after': request.amount,
            'description': f"{request.description} (Admin: {current_user['email']})"
        }
        
        response = supabase_client.supabase.table('user_credits') \
            .insert(transaction_data) \
            .execute()
        
        if response.data:
            logger.info(f"Admin {current_user['email']} set user {request.user_id} credits to {request.amount}")
            return {
                "success": True,
                "data": {
                    "user_id": request.user_id,
                    "previous_balance": current_balance,
                    "new_balance": request.amount,
                    "difference": difference,
                    "transaction_id": response.data[0]['id']
                }
            }
        else:
            raise AppException(message="Kredi ayarlama işlemi başarısız")
            
    except Exception as e:
        logger.error(f"Admin credit setting error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Kredi ayarlama işlemi başarısız oldu"
        )

@router.get("/users", response_model=Dict[str, Any])
async def get_users_credit_status(
    page: int = Query(1, ge=1, description="Sayfa numarası"),
    limit: int = Query(20, ge=1, le=100, description="Sayfa başına kayıt"),
    current_user: dict = Depends(get_current_user_admin)
):
    """
    Tüm kullanıcıların kredi durumunu listele (sadece admin)
    
    Args:
        page: Sayfa numarası
        limit: Sayfa başına kayıt sayısı
        current_user: Mevcut admin kullanıcı
        
    Returns:
        Kullanıcı kredi listesi
    """
    try:
        from models.supabase_client import supabase_client
        
        # Kullanıcı profilleri ile kredi bakiyelerini birleştir
        offset = (page - 1) * limit
        
        # Önce toplam sayıyı al
        count_response = supabase_client.supabase.table('user_profiles') \
            .select('*', count='exact') \
            .execute()
        
        total_count = count_response.count or 0
        
        # Kullanıcı profillerini al
        profiles_response = supabase_client.supabase.table('user_profiles') \
            .select('user_id, email, full_name, role') \
            .range(offset, offset + limit - 1) \
            .execute()
        
        users_with_credits = []
        
        for profile in profiles_response.data or []:
            user_id = profile['user_id']
            balance = await credit_service.get_user_balance(user_id)
            
            users_with_credits.append({
                "user_id": user_id,
                "email": profile['email'],
                "full_name": profile.get('full_name'),
                "role": profile.get('role'),
                "credit_balance": balance
            })
        
        return {
            "success": True,
            "data": {
                "users": users_with_credits,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total_count,
                    "pages": (total_count + limit - 1) // limit
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Admin users credit listing error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Kullanıcı kredi listesi getirilemedi"
        )

@router.get("/user/{user_id}/history", response_model=Dict[str, Any])
async def get_user_credit_history(
    user_id: str,
    limit: int = Query(50, ge=1, le=200, description="Maksimum kayıt sayısı"),
    current_user: dict = Depends(get_current_user_admin)
):
    """
    Belirli bir kullanıcının kredi geçmişini getir (sadece admin)
    
    Args:
        user_id: Kullanıcı UUID'si
        limit: Maksimum kayıt sayısı
        current_user: Mevcut admin kullanıcı
        
    Returns:
        Kullanıcının kredi transaction geçmişi
    """
    try:
        history = await credit_service.get_transaction_history(user_id, limit)
        summary = await credit_service.get_credit_summary(user_id)
        
        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "current_balance": summary["current_balance"],
                "total_earned": summary["total_earned"],
                "total_spent": summary["total_spent"],
                "transactions": history
            }
        }
        
    except Exception as e:
        logger.error(f"Admin user credit history error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Kullanıcı kredi geçmişi getirilemedi"
        )


# ============ CREDIT TRANSACTIONS ADMIN ENDPOINTS ============

@router.get("/transactions", response_model=Dict[str, Any])
async def get_all_transactions(
    page: int = Query(1, ge=1, description="Sayfa numarası"),
    limit: int = Query(50, ge=1, le=200, description="Sayfa başına kayıt"),
    transaction_type: Optional[str] = Query(None, description="İşlem tipi: purchase, usage, refund, bonus"),
    user_id: Optional[str] = Query(None, description="Kullanıcı ID filtresi"),
    current_user: dict = Depends(get_current_user_admin)
):
    """
    Tüm kredi işlemlerini listele (Admin)
    
    Args:
        page: Sayfa numarası
        limit: Sayfa başına kayıt sayısı
        transaction_type: İşlem tipi filtresi
        user_id: Kullanıcı filtresi
        current_user: Admin kullanıcı
        
    Returns:
        Kredi işlemleri listesi
    """
    try:
        from models.supabase_client import supabase_client
        
        # Base query
        query = supabase_client.supabase.table('credit_transactions').select('*')
        
        # Filtreleme
        if transaction_type:
            if transaction_type not in ['purchase', 'usage', 'refund', 'bonus']:
                raise HTTPException(status_code=400, detail="Geçersiz işlem tipi")
            query = query.eq('transaction_type', transaction_type)
        
        if user_id:
            query = query.eq('user_id', user_id)
        
        # Toplam sayı için count
        count_response = query.execute()
        total_count = len(count_response.data) if count_response.data else 0
        
        # Sayfalama
        offset = (page - 1) * limit
        response = query.order('created_at', desc=True).range(offset, offset + limit - 1).execute()
        
        # Kullanıcı bilgilerini ekle
        transactions_with_user = []
        if response.data:
            for transaction in response.data:
                # Kullanıcı bilgilerini al
                user_response = supabase_client.supabase.table('user_profiles') \
                    .select('full_name, email') \
                    .eq('id', transaction['user_id']) \
                    .single() \
                    .execute()
                
                transaction_with_user = transaction.copy()
                if user_response.data:
                    transaction_with_user['user_name'] = user_response.data.get('full_name', 'Bilinmiyor')
                    transaction_with_user['user_email'] = user_response.data.get('email', 'Bilinmiyor')
                else:
                    transaction_with_user['user_name'] = 'Silinmiş Kullanıcı'
                    transaction_with_user['user_email'] = 'Silinmiş'
                
                transactions_with_user.append(transaction_with_user)
        
        return {
            "success": True,
            "data": {
                "transactions": transactions_with_user,
                "total_count": total_count,
                "has_more": total_count > offset + limit,
                "page": page,
                "limit": limit,
                "filters": {
                    "transaction_type": transaction_type,
                    "user_id": user_id
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tüm işlemler alınırken hata: {e}")
        raise HTTPException(
            status_code=500,
            detail="Kredi işlemleri alınamadı"
        )

@router.get("/transactions/stats", response_model=Dict[str, Any])
async def get_transaction_stats(
    current_user: dict = Depends(get_current_user_admin)
):
    """
    Kredi işlemleri istatistikleri (Admin)
    
    Returns:
        Kredi işlem istatistikleri
    """
    try:
        from models.supabase_client import supabase_client
        
        # Tüm işlemler
        all_transactions = supabase_client.supabase.table('credit_transactions') \
            .select('transaction_type, amount') \
            .execute()
        
        stats = {
            "total_transactions": 0,
            "by_type": {
                "purchase": {"count": 0, "total_amount": 0},
                "usage": {"count": 0, "total_amount": 0},
                "refund": {"count": 0, "total_amount": 0},
                "bonus": {"count": 0, "total_amount": 0}
            },
            "total_credits_purchased": 0,
            "total_credits_used": 0,
            "total_credits_refunded": 0,
            "total_credits_bonus": 0
        }
        
        if all_transactions.data:
            stats["total_transactions"] = len(all_transactions.data)
            
            for transaction in all_transactions.data:
                t_type = transaction['transaction_type']
                amount = transaction['amount']
                
                if t_type in stats["by_type"]:
                    stats["by_type"][t_type]["count"] += 1
                    stats["by_type"][t_type]["total_amount"] += amount
                    
                    # Toplam rakamlar
                    if t_type == "purchase":
                        stats["total_credits_purchased"] += amount
                    elif t_type == "usage":
                        stats["total_credits_used"] += abs(amount)  # Usage negatif olabilir
                    elif t_type == "refund":
                        stats["total_credits_refunded"] += amount
                    elif t_type == "bonus":
                        stats["total_credits_bonus"] += amount
        
        return {
            "success": True,
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"İşlem istatistikleri alınırken hata: {e}")
        raise HTTPException(
            status_code=500,
            detail="İstatistikler alınamadı"
        )

@router.get("/transactions/user/{user_id}", response_model=Dict[str, Any])
async def get_user_transactions(
    user_id: str,
    page: int = Query(1, ge=1, description="Sayfa numarası"),
    limit: int = Query(50, ge=1, le=200, description="Sayfa başına kayıt"),
    transaction_type: Optional[str] = Query(None, description="İşlem tipi filtresi"),
    current_user: dict = Depends(get_current_user_admin)
):
    """
    Belirli kullanıcının kredi işlemlerini getir (Admin)
    
    Args:
        user_id: Kullanıcı ID'si
        page: Sayfa numarası
        limit: Sayfa başına kayıt
        transaction_type: İşlem tipi filtresi
        current_user: Admin kullanıcı
        
    Returns:
        Kullanıcının kredi işlemleri
    """
    try:
        from models.supabase_client import supabase_client
        
        # Kullanıcı varlığını kontrol et
        user_check = supabase_client.supabase.table('user_profiles') \
            .select('full_name, email') \
            .eq('id', user_id) \
            .single() \
            .execute()
        
        if not user_check.data:
            raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
        
        # Base query
        query = supabase_client.supabase.table('credit_transactions') \
            .select('*') \
            .eq('user_id', user_id)
        
        # Filtreleme
        if transaction_type:
            if transaction_type not in ['purchase', 'usage', 'refund', 'bonus']:
                raise HTTPException(status_code=400, detail="Geçersiz işlem tipi")
            query = query.eq('transaction_type', transaction_type)
        
        # Toplam sayı
        count_response = query.execute()
        total_count = len(count_response.data) if count_response.data else 0
        
        # Sayfalama ile sonuçlar
        offset = (page - 1) * limit
        response = query.order('created_at', desc=True).range(offset, offset + limit - 1).execute()
        
        return {
            "success": True,
            "data": {
                "user_info": {
                    "user_id": user_id,
                    "user_name": user_check.data.get('full_name', 'Bilinmiyor'),
                    "user_email": user_check.data.get('email', 'Bilinmiyor')
                },
                "transactions": response.data or [],
                "total_count": total_count,
                "has_more": total_count > offset + limit,
                "page": page,
                "limit": limit,
                "filters": {
                    "transaction_type": transaction_type
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Kullanıcı işlemleri alınırken hata {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Kullanıcı işlemleri alınamadı"
        )