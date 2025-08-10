"""
User Support Routes - Kullanıcı destek ticket endpoint'leri
Kullanıcıların kendi ticket'larını yönetebilmesi için API rotaları
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List

from api.dependencies import get_current_user
from services.support_service import SupportService
from models.support_schemas import (
    TicketCreateRequest, MessageCreateRequest, TicketFilterParams,
    TicketCreateResponse, MessageCreateResponse, TicketListResponse,
    SupportTicketDetail, TicketErrorResponse, TicketNotFoundResponse,
    TicketCategory, TicketPriority, TicketStatus
)

router = APIRouter()
support_service = SupportService()


@router.post("/tickets", response_model=TicketCreateResponse, tags=["User Support"])
async def create_ticket(
    ticket_request: TicketCreateRequest,
    current_user = Depends(get_current_user)
):
    """
    Yeni destek ticket'ı oluştur
    
    - **subject**: Ticket konusu (5-200 karakter)
    - **category**: Ticket kategorisi 
    - **priority**: Ticket önceliği (varsayılan: orta)
    - **message**: İlk mesaj içeriği (min 10 karakter)
    """
    try:
        result = await support_service.create_ticket(
            user_id=current_user.id,
            subject=ticket_request.subject,
            category=ticket_request.category,
            priority=ticket_request.priority,
            initial_message=ticket_request.message
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": result.get("error", "Ticket oluşturulamadı")
                }
            )
        
        return TicketCreateResponse(
            success=True,
            message=result["message"],
            ticket=result["ticket"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "Sistem hatası oluştu"
            }
        )


@router.get("/tickets", response_model=TicketListResponse, tags=["User Support"])
async def get_my_tickets(
    current_user = Depends(get_current_user),
    page: int = Query(1, ge=1, description="Sayfa numarası"),
    limit: int = Query(10, ge=1, le=50, description="Sayfa başına kayıt sayısı"),
    status: Optional[TicketStatus] = Query(None, description="Durum filtresi"),
    category: Optional[TicketCategory] = Query(None, description="Kategori filtresi"),
    priority: Optional[TicketPriority] = Query(None, description="Öncelik filtresi"),
    search: Optional[str] = Query(None, description="Konu içinde arama")
):
    """
    Kullanıcının kendi ticket'larını listele
    
    Filtreleme seçenekleri:
    - **status**: acik, cevaplandi, kapatildi
    - **category**: teknik_sorun, hesap_sorunu, vb.
    - **priority**: dusuk, orta, yuksek, acil
    - **search**: Ticket konusunda arama
    """
    try:
        filters = TicketFilterParams(
            status=status,
            category=category,
            priority=priority,
            search=search
        )
        
        result = await support_service.get_user_tickets(
            user_id=current_user.id,
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


@router.get("/tickets/{ticket_id}", response_model=SupportTicketDetail, tags=["User Support"])
async def get_ticket_detail(
    ticket_id: str,
    current_user = Depends(get_current_user)
):
    """
    Belirli bir ticket'ın detaylarını ve tüm mesajlarını getir
    
    Sadece kendi ticket'larınızın detaylarını görebilirsiniz.
    """
    try:
        result = await support_service.get_ticket_detail(
            ticket_id=ticket_id,
            user_id=current_user.id,
            is_admin=False
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


@router.post("/tickets/{ticket_id}/reply", response_model=MessageCreateResponse, tags=["User Support"])
async def reply_to_ticket(
    ticket_id: str,
    message_request: MessageCreateRequest,
    current_user = Depends(get_current_user)
):
    """
    Ticket'a yeni mesaj ekle
    
    Sadece kendi ticket'larınıza mesaj ekleyebilirsiniz.
    Kapalı ticket'lara mesaj eklenemez.
    """
    try:
        result = await support_service.add_message(
            ticket_id=ticket_id,
            sender_id=current_user.id,
            message=message_request.message,
            is_admin=False
        )
        
        if not result["success"]:
            error_msg = result.get("error", "")
            if "bulunamadı" in error_msg or "yetkiniz yok" in error_msg:
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
                "error": "Mesaj gönderilirken hata oluştu"
            }
        )


@router.get("/tickets/{ticket_id}/messages", tags=["User Support"])
async def get_ticket_messages(
    ticket_id: str,
    current_user = Depends(get_current_user)
):
    """
    Ticket'ın sadece mesajlarını getir (detay endpoint'inin alternatifi)
    """
    try:
        result = await support_service.get_ticket_detail(
            ticket_id=ticket_id,
            user_id=current_user.id,
            is_admin=False
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
                        "error": result.get("error", "Mesajlar yüklenemedi")
                    }
                )
        
        return {
            "success": True,
            "messages": result["ticket"]["messages"],
            "message_count": result["ticket"]["message_count"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "Mesajlar yüklenirken hata oluştu"
            }
        )