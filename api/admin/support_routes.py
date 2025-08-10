"""
Admin Support Routes - Admin destek ticket yönetimi endpoint'leri
Admin kullanıcıların tüm ticket'ları yönetebilmesi için API rotaları
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List

from api.dependencies import get_current_user
from services.support_service import SupportService
from models.support_schemas import (
    MessageCreateRequest, TicketStatusUpdate, TicketFilterParams,
    MessageCreateResponse, TicketListResponse, SupportTicketDetail,
    TicketStatsResponse, TicketCategory, TicketPriority, TicketStatus
)

router = APIRouter()
support_service = SupportService()


async def verify_admin(current_user = Depends(get_current_user)):
    """Admin yetkisi kontrolü"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail={
                "success": False,
                "error": "Bu işlem için admin yetkisi gerekli"
            }
        )
    return current_user


@router.get("/tickets", response_model=TicketListResponse, tags=["Admin Support"])
async def get_all_tickets(
    admin_user = Depends(verify_admin),
    page: int = Query(1, ge=1, description="Sayfa numarası"),
    limit: int = Query(20, ge=1, le=100, description="Sayfa başına kayıt sayısı"),
    status: Optional[TicketStatus] = Query(None, description="Durum filtresi"),
    category: Optional[TicketCategory] = Query(None, description="Kategori filtresi"),
    priority: Optional[TicketPriority] = Query(None, description="Öncelik filtresi"),
    user_id: Optional[str] = Query(None, description="Kullanıcı ID filtresi"),
    search: Optional[str] = Query(None, description="Ticket numarası veya konusunda arama")
):
    """
    Tüm kullanıcıların ticket'larını listele (Admin)
    
    Filtreleme seçenekleri:
    - **status**: acik, cevaplandi, kapatildi
    - **category**: teknik_sorun, hesap_sorunu, vb.
    - **priority**: dusuk, orta, yuksek, acil
    - **user_id**: Belirli kullanıcının ticket'ları
    - **search**: Ticket numarası veya konusunda arama
    """
    try:
        filters = TicketFilterParams(
            status=status,
            category=category,
            priority=priority,
            user_id=user_id,
            search=search
        )
        
        result = await support_service.get_admin_tickets(
            admin_user_id=admin_user.id,
            page=page,
            limit=limit,
            filters=filters
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "error": result.get("error", "Ticket'lar yüklenemedi")
                }
            )
        
        return TicketListResponse(
            tickets=result["tickets"],
            total_count=result["total_count"],
            has_more=result["has_more"],
            page=page,
            limit=limit
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "Ticket'lar yüklenirken hata oluştu"
            }
        )


@router.get("/tickets/{ticket_id}", response_model=SupportTicketDetail, tags=["Admin Support"])
async def get_ticket_detail_admin(
    ticket_id: str,
    admin_user = Depends(verify_admin)
):
    """
    Herhangi bir ticket'ın detaylarını ve tüm mesajlarını getir (Admin)
    """
    try:
        result = await support_service.get_ticket_detail(
            ticket_id=ticket_id,
            user_id=admin_user.id,
            is_admin=True
        )
        
        if not result["success"]:
            if "bulunamadı" in result.get("error", ""):
                raise HTTPException(
                    status_code=404,
                    detail={
                        "success": False,
                        "error": result["error"]
                    }
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "success": False,
                        "error": result.get("error", "Ticket detayları yüklenemedi")
                    }
                )
        
        return SupportTicketDetail(**result["ticket"])
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "Ticket detayları yüklenirken hata oluştu"
            }
        )


@router.post("/tickets/{ticket_id}/reply", response_model=MessageCreateResponse, tags=["Admin Support"])
async def admin_reply_to_ticket(
    ticket_id: str,
    message_request: MessageCreateRequest,
    admin_user = Depends(verify_admin)
):
    """
    Ticket'a admin yanıtı ekle
    
    Admin yanıtı ticket durumunu otomatik olarak 'cevaplandi' yapar.
    """
    try:
        result = await support_service.add_message(
            ticket_id=ticket_id,
            sender_id=admin_user.id,
            message=message_request.message,
            is_admin=True
        )
        
        if not result["success"]:
            error_msg = result.get("error", "")
            if "bulunamadı" in error_msg:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "success": False,
                        "error": result["error"]
                    }
                )
            elif "kapalı" in error_msg.lower():
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "error": result["error"]
                    }
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "success": False,
                        "error": result["error"]
                    }
                )
        
        return MessageCreateResponse(
            success=True,
            message=result["message"],
            support_message=result["support_message"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "Admin yanıtı gönderilirken hata oluştu"
            }
        )


@router.put("/tickets/{ticket_id}/status", tags=["Admin Support"])
async def update_ticket_status(
    ticket_id: str,
    status_update: TicketStatusUpdate,
    admin_user = Depends(verify_admin)
):
    """
    Ticket durumunu güncelle (Admin)
    
    Mümkün durumlar:
    - **acik**: Kullanıcı yanıtı bekleniyor
    - **cevaplandi**: Admin yanıtı verildi
    - **kapatildi**: Ticket kapatıldı
    """
    try:
        result = await support_service.update_ticket_status(
            ticket_id=ticket_id,
            new_status=status_update.status,
            admin_user_id=admin_user.id
        )
        
        if not result["success"]:
            error_msg = result.get("error", "")
            if "bulunamadı" in error_msg:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "success": False,
                        "error": result["error"]
                    }
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "success": False,
                        "error": result["error"]
                    }
                )
        
        return {
            "success": True,
            "message": result["message"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "Durum güncellenirken hata oluştu"
            }
        )


@router.get("/tickets/stats", response_model=TicketStatsResponse, tags=["Admin Support"])
async def get_ticket_statistics(
    admin_user = Depends(verify_admin)
):
    """
    Ticket istatistiklerini getir (Admin)
    
    Genel istatistikler ve kategori/öncelik bazlı dağılım.
    """
    try:
        result = await support_service.get_ticket_stats(
            admin_user_id=admin_user.id
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "error": result.get("error", "İstatistikler yüklenemedi")
                }
            )
        
        return TicketStatsResponse(**result["stats"])
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "İstatistikler yüklenirken hata oluştu"
            }
        )


@router.get("/tickets/user/{user_id}", response_model=TicketListResponse, tags=["Admin Support"])
async def get_user_tickets_admin(
    user_id: str,
    admin_user = Depends(verify_admin),
    page: int = Query(1, ge=1, description="Sayfa numarası"),
    limit: int = Query(20, ge=1, le=100, description="Sayfa başına kayıt sayısı"),
    status: Optional[TicketStatus] = Query(None, description="Durum filtresi")
):
    """
    Belirli bir kullanıcının tüm ticket'larını getir (Admin)
    """
    try:
        filters = TicketFilterParams(
            status=status,
            user_id=user_id
        )
        
        result = await support_service.get_admin_tickets(
            admin_user_id=admin_user.id,
            page=page,
            limit=limit,
            filters=filters
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "error": result.get("error", "Kullanıcı ticket'ları yüklenemedi")
                }
            )
        
        return TicketListResponse(
            tickets=result["tickets"],
            total_count=result["total_count"],
            has_more=result["has_more"],
            page=page,
            limit=limit
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "Kullanıcı ticket'ları yüklenirken hata oluştu"
            }
        )


@router.delete("/tickets/{ticket_id}", tags=["Admin Support"])
async def delete_ticket(
    ticket_id: str,
    admin_user = Depends(verify_admin)
):
    """
    Ticket'ı tamamen sil (Admin - Dikkatli kullanın!)
    
    Bu işlem geri alınamaz. Ticket ve tüm mesajları silinir.
    """
    try:
        # Önce ticket'ın varlığını kontrol et
        result = await support_service.get_ticket_detail(
            ticket_id=ticket_id,
            user_id=admin_user.id,
            is_admin=True
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error": "Ticket bulunamadı"
                }
            )
        
        # Ticket'ı sil (CASCADE ile mesajlar da silinir)
        delete_response = support_service.supabase.table('support_tickets') \
            .delete().eq('id', ticket_id).execute()
        
        if delete_response.data:
            return {
                "success": True,
                "message": f"Ticket {result['ticket']['ticket_number']} başarıyla silindi"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "error": "Ticket silinemedi"
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "Ticket silinirken hata oluştu"
            }
        )