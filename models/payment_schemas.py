"""
Payment and iyzico webhook schemas
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal


class OnSiparisCreate(BaseModel):
    """İlk sipariş kaydı için schema"""
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
    """İlk sipariş response"""
    success: bool
    message: str
    order_id: Optional[str] = None
    payment_id: Optional[str] = None
    conversation_id: Optional[str] = None


class IyzicoWebhook(BaseModel):
    """İyzico webhook request schema - Tüm fieldlar optional (esnek validation)"""
    paymentConversationId: Optional[str] = None
    merchantId: Optional[str] = None
    paymentId: Optional[str] = None
    status: Optional[str] = None
    iyziReferenceCode: Optional[str] = None
    iyziEventType: Optional[str] = None
    iyziEventTime: Optional[int] = None  # unix timestamp
    iyziPaymentId: Optional[int] = None
    
    class Config:
        extra = "allow"  # İyzico'dan gelen extra fieldları kabul et


class IyzicoWebhookResponse(BaseModel):
    """İyzico webhook response"""
    success: bool
    message: str
    webhook_id: Optional[str] = None
    matched_order: Optional[bool] = None
    credit_added: Optional[bool] = None
    credit_amount: Optional[int] = None
