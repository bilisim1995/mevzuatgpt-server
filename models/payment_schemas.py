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
