"""
Credit package models for MevzuatGPT
Handles credit packages, purchases, and pricing
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from core.database import Base


class CreditPackage(Base):
    """Credit package definitions"""
    __tablename__ = "credit_packages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    credits = Column(Integer, nullable=False)
    price_without_tax = Column(Float, nullable=False)  # Price in TL without VAT
    tax_rate = Column(Float, default=0.20)  # 20% VAT
    validity_days = Column(Integer, nullable=False)  # Package validity in days
    description = Column(Text)
    target_audience = Column(String(200))  # "Yeni kullanıcılar, test kullanımı"
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    purchases = relationship("CreditPurchase", back_populates="package")
    
    @property
    def price_with_tax(self) -> float:
        """Calculate price including VAT"""
        return round(self.price_without_tax * (1 + self.tax_rate), 2)
    
    @property
    def cost_per_credit(self) -> float:
        """Calculate cost per credit"""
        return round(self.price_without_tax / self.credits, 4)
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "credits": self.credits,
            "price_without_tax": self.price_without_tax,
            "price_with_tax": self.price_with_tax,
            "tax_rate": self.tax_rate,
            "validity_days": self.validity_days,
            "description": self.description,
            "target_audience": self.target_audience,
            "cost_per_credit": self.cost_per_credit,
            "is_active": self.is_active,
            "sort_order": self.sort_order
        }


class CreditPurchase(Base):
    """Credit package purchases"""
    __tablename__ = "credit_purchases"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    package_id = Column(UUID(as_uuid=True), ForeignKey("credit_packages.id"), nullable=False)
    
    credits_purchased = Column(Integer, nullable=False)
    price_paid = Column(Float, nullable=False)  # Amount paid including tax
    tax_amount = Column(Float, nullable=False)  # VAT amount
    
    # Payment info
    payment_status = Column(String(50), default="pending")  # pending, completed, failed, refunded
    payment_method = Column(String(50))  # credit_card, bank_transfer, etc.
    payment_reference = Column(String(200))  # External payment system reference
    
    # Validity
    valid_until = Column(DateTime, nullable=False)
    credits_remaining = Column(Integer, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    package = relationship("CreditPackage", back_populates="purchases")
    
    @property
    def is_expired(self) -> bool:
        """Check if purchase is expired"""
        return datetime.utcnow() > self.valid_until
    
    @property
    def credits_used(self) -> int:
        """Calculate credits used"""
        return self.credits_purchased - self.credits_remaining
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "package_id": str(self.package_id),
            "package_name": self.package.name if self.package else None,
            "credits_purchased": self.credits_purchased,
            "credits_remaining": self.credits_remaining,
            "credits_used": self.credits_used,
            "price_paid": self.price_paid,
            "tax_amount": self.tax_amount,
            "payment_status": self.payment_status,
            "valid_until": self.valid_until.isoformat(),
            "is_expired": self.is_expired,
            "created_at": self.created_at.isoformat(),
        }