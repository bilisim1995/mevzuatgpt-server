"""
Payment order schemas
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal


class OnSiparisCreate(BaseModel):
    """Sipariş kaydı için schema"""
    email: str
    tarih: Optional[datetime] = None
    user_agent: Optional[str] = None
    referrer: Optional[str] = None
    user_ip: Optional[str] = None
    status: str
    conversation_id: str
    price: Decimal
    payment_id: Optional[str] = None
    fraud_status: Optional[str] = None
    commission_rate: Optional[Decimal] = None
    commission_fee: Optional[Decimal] = None
    host_reference: Optional[str] = None
    credit_amount: int
    system_time: Optional[datetime] = None
    request_url: Optional[str] = None


class OnSiparisResponse(BaseModel):
    """Sipariş response"""
    success: bool
    message: str
    order_id: Optional[str] = None
    payment_id: Optional[str] = None
    conversation_id: Optional[str] = None


class PurchaseHistoryItem(BaseModel):
    """Kullanıcı satın alım geçmişi item"""
    created_at: datetime
    status: str
    price: Decimal
    payment_id: Optional[str] = None
    credit_amount: int


class PurchaseHistoryResponse(BaseModel):
    """Kullanıcı satın alım geçmişi response"""
    success: bool
    data: list[PurchaseHistoryItem]
    total: int


class PaymentSettingsResponse(BaseModel):
    """Ödeme ayarları response"""
    success: bool
    payment_mode: str  # "sandbox" veya "production"
    is_active: bool  # Ödeme sisteminin aktif/pasif durumu
    description: Optional[str] = None


class PaymentSettingsUpdate(BaseModel):
    """Ödeme ayarları güncelleme (Admin)"""
    payment_mode: Optional[str] = Field(None, pattern="^(sandbox|production)$")
    is_active: Optional[bool] = None
    description: Optional[str] = None
