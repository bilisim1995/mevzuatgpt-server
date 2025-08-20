"""
Password Reset Routes for MevzuatGPT
Handles password reset functionality
"""

import logging
from fastapi import APIRouter, HTTPException, status
from models.password_reset_schemas import (
    PasswordResetRequestSchema,
    PasswordResetConfirmSchema, 
    PasswordResetResponseSchema
)
from services.supabase_auth_service import auth_service
from services.email_service import email_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Password Reset"])

@router.post(
    "/forgot-password",
    response_model=PasswordResetResponseSchema,
    summary="Şifre Sıfırlama Talebi",
    description="Kullanıcının email adresine şifre sıfırlama bağlantısı gönderir"
)
async def forgot_password(request: PasswordResetRequestSchema):
    """
    Send password reset email to user
    
    Args:
        request: Email address for password reset
        
    Returns:
        Success message (always returns success to prevent email enumeration)
    """
    try:
        # Send password reset email
        await auth_service.send_password_reset_email(request.email)
        
        # Always return success to prevent email enumeration
        return PasswordResetResponseSchema(
            success=True,
            message="Eğer bu email adresi sistemde kayıtlıysa, şifre sıfırlama bağlantısı gönderilmiştir"
        )
        
    except Exception as e:
        logger.error(f"Error in forgot password endpoint: {str(e)}")
        # Always return success to prevent email enumeration
        return PasswordResetResponseSchema(
            success=True,
            message="Eğer bu email adresi sistemde kayıtlıysa, şifre sıfırlama bağlantısı gönderilmiştir"
        )

@router.post(
    "/reset-password",
    response_model=PasswordResetResponseSchema,
    summary="Şifre Sıfırlama",
    description="Reset token ile yeni şifre belirleme"
)
async def reset_password(request: PasswordResetConfirmSchema):
    """
    Reset password using reset token
    
    Args:
        request: Reset token and new password
        
    Returns:
        Success or error message
    """
    try:
        # Verify token and reset password
        success = await auth_service.reset_password(
            token=request.token,
            new_password=request.new_password
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Geçersiz veya süresi dolmuş şifre sıfırlama kodu"
            )
        
        # Get user email for notification
        email = await auth_service.verify_reset_token(request.token)
        if email:
            # Send password changed notification
            user_data = await auth_service.get_user_by_email(email)
            user_name = user_data.get("full_name") if user_data else None
            
            await email_service.send_password_changed_notification(
                to_email=email,
                user_name=user_name
            )
        
        return PasswordResetResponseSchema(
            success=True,
            message="Şifreniz başarıyla değiştirildi"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in reset password endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Şifre sıfırlama işlemi sırasında bir hata oluştu"
        )

@router.post(
    "/verify-reset-token",
    response_model=PasswordResetResponseSchema,
    summary="Reset Token Doğrulama",
    description="Reset token'ın geçerliliğini kontrol eder"
)
async def verify_reset_token(token: str):
    """
    Verify if reset token is valid
    
    Args:
        token: Reset token to verify
        
    Returns:
        Token validity status
    """
    try:
        email = await auth_service.verify_reset_token(token)
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Geçersiz veya süresi dolmuş şifre sıfırlama kodu"
            )
        
        return PasswordResetResponseSchema(
            success=True,
            message="Token geçerli"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying reset token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token doğrulama sırasında bir hata oluştu"
        )