"""
FastAPI dependencies for authentication and authorization
Reusable dependency functions for route protection
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging

from core.database import get_db
from services.supabase_auth_service import auth_service
from models.schemas import UserResponse
from utils.exceptions import AppException

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security_scheme = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
) -> UserResponse:
    """
    Dependency to get current authenticated user from JWT token via Supabase
    
    Args:
        credentials: Bearer token from Authorization header
        
    Returns:
        Current user information
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Verify token with Supabase auth service
        auth_data = await auth_service.verify_token(credentials.credentials)
        
        if not auth_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_data = auth_data["user"]
        # Convert dict to UserResponse model
        return UserResponse(**user_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_admin_user(
    current_user: UserResponse = Depends(get_current_user)
) -> UserResponse:
    """
    Dependency to ensure current user has admin role
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user if they have admin role
        
    Raises:
        HTTPException: If user doesn't have admin role
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
) -> Optional[UserResponse]:
    """
    Dependency to get current user if token is provided (optional authentication)
    
    Args:
        credentials: Bearer token from Authorization header (optional)
        
    Returns:
        Current user information if token is valid, None otherwise
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None

class RoleChecker:
    """Dependency class for checking user roles"""
    
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles
    
    def __call__(self, current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
        """
        Check if current user has one of the allowed roles
        
        Args:
            current_user: Current authenticated user
            
        Returns:
            Current user if they have required role
            
        Raises:
            HTTPException: If user doesn't have required role
        """
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(self.allowed_roles)}"
            )
        
        return current_user

# Pre-defined role checkers
require_admin = RoleChecker(["admin"])
require_user_or_admin = RoleChecker(["user", "admin"])

async def get_current_user_admin(
    current_user: UserResponse = Depends(get_current_user)
) -> dict:
    """
    Dependency to ensure current user has admin privileges
    Returns user data as dict for admin operations
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User data as dict
        
    Raises:
        HTTPException: If user is not admin
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin yetkisi gerekli"
        )
    
    # UserResponse'ı dict'e çevir
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role
    }
