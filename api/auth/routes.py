"""
Authentication routes using Supabase Auth
Handles user registration, login, logout, and token management
"""

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer
import logging

from api.dependencies import get_current_user
from models.schemas import (
    UserCreate, UserLogin, UserResponse, TokenResponse
)
from services.supabase_auth_service import auth_service

logger = logging.getLogger(__name__)
router = APIRouter()
security_scheme = HTTPBearer()

@router.post("/register", response_model=TokenResponse)
async def register_user(user_data: UserCreate):
    """
    Register a new user with Supabase Auth
    
    Creates a new user account with email and password.
    Returns JWT token for immediate authentication.
    
    Args:
        user_data: User registration data (email, password, full_name)
    
    Returns:
        JWT token and user information
    """
    try:
        result = await auth_service.register_user(user_data)
        
        return TokenResponse(
            access_token=result["access_token"],
            refresh_token="",  # Supabase handles refresh tokens internally
            token_type=result["token_type"],
            expires_in=3600,
            user=result["user"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Kullanıcı kaydı başarısız"
        )

@router.post("/login", response_model=TokenResponse)
async def login_user(login_data: UserLogin):
    """
    Authenticate user with Supabase Auth
    
    Validates user credentials and returns JWT token.
    
    Args:
        login_data: User login credentials (email, password)
    
    Returns:
        JWT token and user information
    """
    try:
        result = await auth_service.authenticate_user(login_data)
        
        return TokenResponse(
            access_token=result["access_token"],
            refresh_token="",  # Supabase handles refresh tokens internally
            token_type=result["token_type"],
            expires_in=3600,
            user=result["user"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Giriş işlemi başarısız"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserResponse = Depends(get_current_user)):
    """
    Get current user information
    
    Returns the authenticated user's profile information.
    Requires valid JWT token in Authorization header.
    
    Returns:
        Current user information
    """
    return current_user

@router.post("/logout")
async def logout_user():
    """
    Logout user (client-side token removal)
    
    Note: With Supabase Auth, logout is typically handled client-side
    by removing the JWT token from storage.
    
    Returns:
        Success message
    """
    return {
        "message": "Başarıyla çıkış yapıldı",
        "detail": "Token'ı client tarafında kaldırın"
    }

@router.get("/verify-token")
async def verify_token(current_user: UserResponse = Depends(get_current_user)):
    """
    Verify if current token is valid
    
    Returns user information if token is valid, otherwise returns 401.
    
    Returns:
        Token validation status and user info
    """
    return {
        "valid": True,
        "user": current_user,
        "message": "Token geçerli"
    }