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
    GENERAL = "general"
    TECHNICAL = "technical"
    BILLING = "billing"
    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"
    ACCOUNT = "account"


class TicketPriority(str, Enum):
    """Ticket öncelik seviyeleri"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketStatus(str, Enum):
    """Ticket durum seviyeleri"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_RESPONSE = "waiting_response"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketCreateRequest(BaseModel):
    """Yeni ticket oluşturma isteği"""
    subject: str = Field(..., min_length=5, max_length=200, description="Ticket konusu")
    category: TicketCategory = Field(..., description="Ticket kategorisi")
    priority: TicketPriority = Field(default=TicketPriority.MEDIUM, description="Ticket önceliği")
    message: str = Field(..., min_length=10, description="İlk mesaj içeriği")
    
    @validator('category', pre=True)
    def validate_category(cls, v):
        # Türkçe -> İngilizce mapping (backward compatibility)
        turkish_to_english = {
            'teknik_sorun': 'technical',
            'hesap_sorunu': 'general',  # account yerine general kullan 
            'ozellik_talebi': 'feature_request',
            'guvenlik': 'bug_report',
            'faturalandirma': 'billing',
            'genel_soru': 'general',
            'diger': 'general'
        }
        return turkish_to_english.get(v, v)
    
    @validator('priority', pre=True)
    def validate_priority(cls, v):
        # Türkçe -> İngilizce mapping (backward compatibility)
        turkish_to_english = {
            'dusuk': 'low',
            'orta': 'medium',
            'yuksek': 'high',
            'acil': 'urgent'
        }
        return turkish_to_english.get(v, v)

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
    TicketCategory.GENERAL: "Genel kullanım soruları, rehberlik",
    TicketCategory.TECHNICAL: "PDF yükleme, sistem hataları, performans sorunları",
    TicketCategory.BILLING: "Ödeme sorunları, fatura soruları",
    TicketCategory.FEATURE_REQUEST: "Yeni özellik istekleri, geliştirme önerileri",
    TicketCategory.BUG_REPORT: "Hata bildirimleri, sistem aksaklıkları",
    TicketCategory.ACCOUNT: "Login sorunları, kredi sorunları, profil ayarları"
}

# Öncelik açıklamaları (UI için)
PRIORITY_DESCRIPTIONS = {
    TicketPriority.LOW: "Genel sorular, özellik talepleri",
    TicketPriority.MEDIUM: "Standart teknik sorunlar", 
    TicketPriority.HIGH: "Kritik işlevsellik sorunları",
    TicketPriority.URGENT: "Güvenlik sorunları, sistem erişim sorunları"
}