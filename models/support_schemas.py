"""
Support Ticket System - Pydantic Schemas
Destek ticket sistemi için veri modelleri ve validasyonlar
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum


class TicketCategory(str, Enum):
    """Ticket kategorileri"""
    TEKNIK_SORUN = "teknik_sorun"
    HESAP_SORUNU = "hesap_sorunu"
    OZELLIK_TALEBI = "ozellik_talebi"
    GUVENLIK = "guvenlik"
    FATURALANDIRMA = "faturalandirma"
    GENEL_SORU = "genel_soru"
    DIGER = "diger"


class TicketPriority(str, Enum):
    """Ticket öncelik seviyeleri"""
    DUSUK = "dusuk"
    ORTA = "orta"
    YUKSEK = "yuksek"
    ACIL = "acil"


class TicketStatus(str, Enum):
    """Ticket durum seviyeleri"""
    ACIK = "acik"
    CEVAPLANDI = "cevaplandi"
    KAPATILDI = "kapatildi"


class TicketCreateRequest(BaseModel):
    """Yeni ticket oluşturma isteği"""
    subject: str = Field(..., min_length=5, max_length=200, description="Ticket konusu")
    category: TicketCategory = Field(..., description="Ticket kategorisi")
    priority: TicketPriority = Field(default=TicketPriority.ORTA, description="Ticket önceliği")
    message: str = Field(..., min_length=10, description="İlk mesaj içeriği")
    
    @validator('subject')
    def validate_subject(cls, v):
        if not v or v.strip() == '':
            raise ValueError('Konu boş olamaz')
        return v.strip()
    
    @validator('message')
    def validate_message(cls, v):
        if not v or v.strip() == '':
            raise ValueError('Mesaj boş olamaz')
        if len(v.strip()) < 10:
            raise ValueError('Mesaj en az 10 karakter olmalıdır')
        return v.strip()

    class Config:
        use_enum_values = True


class MessageCreateRequest(BaseModel):
    """Ticket'a yeni mesaj ekleme isteği"""
    message: str = Field(..., min_length=1, description="Mesaj içeriği")
    
    @validator('message')
    def validate_message(cls, v):
        if not v or v.strip() == '':
            raise ValueError('Mesaj boş olamaz')
        return v.strip()


class TicketStatusUpdate(BaseModel):
    """Ticket durum güncelleme (Admin için)"""
    status: TicketStatus = Field(..., description="Yeni ticket durumu")

    class Config:
        use_enum_values = True


class SupportMessage(BaseModel):
    """Destek mesajı response modeli"""
    id: str
    ticket_id: str
    sender_id: str
    message: str
    created_at: datetime
    
    # Sender bilgileri (join'den gelecek)
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None
    is_admin: Optional[bool] = False

    class Config:
        from_attributes = True


class SupportTicket(BaseModel):
    """Destek ticket'ı response modeli"""
    id: str
    ticket_number: str
    user_id: str
    subject: str
    category: TicketCategory
    priority: TicketPriority
    status: TicketStatus
    created_at: datetime
    updated_at: datetime
    
    # Kullanıcı bilgileri (join'den gelecek)
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    
    # İstatistikler
    message_count: Optional[int] = 0
    last_reply_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        use_enum_values = True


class SupportTicketDetail(SupportTicket):
    """Detaylı ticket bilgisi (mesajlar dahil)"""
    messages: List[SupportMessage] = []


class TicketListResponse(BaseModel):
    """Ticket listesi response"""
    tickets: List[SupportTicket]
    total_count: int
    has_more: bool
    page: int
    limit: int


class TicketCreateResponse(BaseModel):
    """Ticket oluşturma response"""
    success: bool
    message: str
    ticket: SupportTicket


class MessageCreateResponse(BaseModel):
    """Mesaj oluşturma response"""
    success: bool
    message: str
    support_message: SupportMessage


class TicketStatsResponse(BaseModel):
    """Ticket istatistikleri (Admin için)"""
    total_tickets: int
    open_tickets: int
    answered_tickets: int
    closed_tickets: int
    by_category: dict
    by_priority: dict
    avg_response_time: Optional[float] = None  # Saat cinsinden


# Filtreleme parametreleri
class TicketFilterParams(BaseModel):
    """Ticket filtreleme parametreleri"""
    status: Optional[TicketStatus] = None
    category: Optional[TicketCategory] = None
    priority: Optional[TicketPriority] = None
    user_id: Optional[str] = None
    search: Optional[str] = None  # Konu veya mesajlarda arama
    
    class Config:
        use_enum_values = True


# Error responses
class TicketErrorResponse(BaseModel):
    """Hata response modeli"""
    success: bool = False
    error: str
    details: Optional[dict] = None


class TicketNotFoundResponse(BaseModel):
    """Ticket bulunamadı response"""
    success: bool = False
    error: str = "Ticket bulunamadı"
    ticket_id: Optional[str] = None


class UnauthorizedResponse(BaseModel):
    """Yetkisiz erişim response"""
    success: bool = False
    error: str = "Bu işlem için yetkiniz yok"


# Kategori açıklamaları (UI için)
CATEGORY_DESCRIPTIONS = {
    TicketCategory.TEKNIK_SORUN: "PDF yükleme, sistem hataları, performans sorunları",
    TicketCategory.HESAP_SORUNU: "Login sorunları, kredi sorunları, profil ayarları", 
    TicketCategory.OZELLIK_TALEBI: "Yeni özellik istekleri, geliştirme önerileri",
    TicketCategory.GUVENLIK: "Güvenlik endişeleri, şüpheli aktiviteler",
    TicketCategory.FATURALANDIRMA: "Ödeme sorunları, fatura soruları",
    TicketCategory.GENEL_SORU: "Genel kullanım soruları, rehberlik",
    TicketCategory.DIGER: "Diğer konular"
}

# Öncelik açıklamaları (UI için)
PRIORITY_DESCRIPTIONS = {
    TicketPriority.DUSUK: "Genel sorular, özellik talepleri",
    TicketPriority.ORTA: "Standart teknik sorunlar", 
    TicketPriority.YUKSEK: "Kritik işlevsellik sorunları",
    TicketPriority.ACIL: "Güvenlik sorunları, sistem erişim sorunları"
}