"""
Password Reset Schemas for MevzuatGPT
"""

from pydantic import BaseModel, EmailStr, validator
from typing import Optional

class PasswordResetRequestSchema(BaseModel):
    """Schema for password reset request"""
    email: EmailStr
    
    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com"
            }
        }

class PasswordResetConfirmSchema(BaseModel):
    """Schema for password reset confirmation"""
    token: str
    new_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Şifre en az 8 karakter olmalıdır')
        
        # Check for at least one uppercase letter
        if not any(c.isupper() for c in v):
            raise ValueError('Şifre en az bir büyük harf içermelidir')
        
        # Check for at least one lowercase letter
        if not any(c.islower() for c in v):
            raise ValueError('Şifre en az bir küçük harf içermelidir')
        
        # Check for at least one digit
        if not any(c.isdigit() for c in v):
            raise ValueError('Şifre en az bir rakam içermelidir')
        
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "new_password": "NewPassword123!"
            }
        }

class PasswordResetResponseSchema(BaseModel):
    """Schema for password reset response"""
    success: bool
    message: str
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Şifre sıfırlama bağlantısı e-posta adresinize gönderildi"
            }
        }