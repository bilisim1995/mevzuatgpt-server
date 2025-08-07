"""
Authentication routes for user management
Handles registration, login, token refresh, and user profile operations
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from core.database import get_db
from core.security import security
from api.dependencies import get_current_user
from models.schemas import (
    UserCreate, UserLogin, UserResponse, TokenResponse,
    PasswordReset, PasswordChange, UserProfileUpdate
)
from services.auth_service import AuthService
from utils.response import success_response
from utils.exceptions import AppException

logger = logging.getLogger(__name__)
router = APIRouter()
security_scheme = HTTPBearer()

@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user
    
    Creates a new user account with email verification.
    Default role is 'user' unless explicitly set to 'admin'.
    
    Args:
        user_data: User registration data
        db: Database session
    
    Returns:
        Created user information (without password)
    """
    try:
        auth_service = AuthService(db)
        
        # Check if user already exists
        existing_user = await auth_service.get_user_by_email(user_data.email)
        if existing_user:
            raise AppException(
                message="Email already registered",
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="EMAIL_EXISTS"
            )
        
        # Create new user
        user = await auth_service.create_user(user_data)
        
        logger.info(f"New user registered: {user.email}")
        
        return success_response(data=user)
        
    except AppException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise AppException(
            message="Failed to register user",
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="REGISTRATION_FAILED"
        )

@router.post("/login", response_model=TokenResponse)
async def login_user(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens
    
    Validates user credentials and returns access and refresh tokens.
    
    Args:
        login_data: User login credentials
        db: Database session
    
    Returns:
        JWT tokens and user information
    """
    try:
        auth_service = AuthService(db)
        
        # Authenticate user
        user = await auth_service.authenticate_user(login_data.email, login_data.password)
        
        if not user:
            raise AppException(
                message="Invalid email or password",
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_code="INVALID_CREDENTIALS"
            )
        
        # Generate tokens
        access_token = security.create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role}
        )
        refresh_token = security.create_refresh_token(
            data={"sub": str(user.id)}
        )
        
        logger.info(f"User logged in: {user.email}")
        
        return success_response(
            data={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": 30 * 60,  # 30 minutes in seconds
                "user": user
            }
        )
        
    except AppException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise AppException(
            message="Login failed",
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="LOGIN_FAILED"
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token
    
    Args:
        credentials: Refresh token from Authorization header
        db: Database session
    
    Returns:
        New access token and user information
    """
    try:
        # Verify refresh token
        payload = security.verify_token(credentials.credentials, "refresh")
        user_id = payload.get("sub")
        
        if not user_id:
            raise AppException(
                message="Invalid refresh token",
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_code="INVALID_TOKEN"
            )
        
        # Get user information
        auth_service = AuthService(db)
        user = await auth_service.get_user_by_id(user_id)
        
        if not user:
            raise AppException(
                message="User not found",
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_code="USER_NOT_FOUND"
            )
        
        # Generate new access token
        access_token = security.create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role}
        )
        
        return success_response(
            data={
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": 30 * 60,  # 30 minutes in seconds
                "user": user
            }
        )
        
    except AppException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise AppException(
            message="Token refresh failed",
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="REFRESH_FAILED"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get current user profile information
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        Current user profile
    """
    return success_response(data=current_user)

@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    profile_data: UserProfileUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user profile
    
    Args:
        profile_data: Updated profile data
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Updated user profile
    """
    try:
        auth_service = AuthService(db)
        
        updated_user = await auth_service.update_user_profile(
            user_id=current_user.id,
            profile_data=profile_data
        )
        
        logger.info(f"User profile updated: {current_user.email}")
        
        return success_response(data=updated_user)
        
    except Exception as e:
        logger.error(f"Profile update error for user {current_user.id}: {str(e)}")
        raise AppException(
            message="Failed to update profile",
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="UPDATE_FAILED"
        )

@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change user password
    
    Args:
        password_data: Current and new password
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Success message
    """
    try:
        auth_service = AuthService(db)
        
        # Verify current password
        user = await auth_service.authenticate_user(
            current_user.email, 
            password_data.current_password
        )
        
        if not user:
            raise AppException(
                message="Current password is incorrect",
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="INVALID_PASSWORD"
            )
        
        # Update password
        await auth_service.change_password(
            user_id=current_user.id,
            new_password=password_data.new_password
        )
        
        logger.info(f"Password changed for user: {current_user.email}")
        
        return success_response(
            data={"message": "Password changed successfully"}
        )
        
    except AppException:
        raise
    except Exception as e:
        logger.error(f"Password change error for user {current_user.id}: {str(e)}")
        raise AppException(
            message="Failed to change password",
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="PASSWORD_CHANGE_FAILED"
        )

@router.post("/logout")
async def logout_user(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Logout user (token invalidation would be handled by client)
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        Success message
    """
    logger.info(f"User logged out: {current_user.email}")
    
    return success_response(
        data={"message": "Logged out successfully"}
    )

@router.post("/forgot-password")
async def forgot_password(
    email: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Initiate password reset process
    
    Args:
        email: User email address
        db: Database session
    
    Returns:
        Success message (always returns success for security)
    """
    try:
        auth_service = AuthService(db)
        
        # Check if user exists (but don't reveal this information)
        user = await auth_service.get_user_by_email(email)
        
        if user:
            # In a real implementation, you would:
            # 1. Generate a secure reset token
            # 2. Store it in database with expiration
            # 3. Send email with reset link
            logger.info(f"Password reset requested for: {email}")
        
        # Always return success for security reasons
        return success_response(
            data={"message": "If the email exists, a password reset link has been sent"}
        )
        
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        # Still return success for security
        return success_response(
            data={"message": "If the email exists, a password reset link has been sent"}
        )
