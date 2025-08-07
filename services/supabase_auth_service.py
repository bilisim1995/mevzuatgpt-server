"""
Supabase-based authentication service
Handles user registration, login, and role-based access control
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from core.supabase_client import supabase_client
from core.security import SecurityManager
from models.schemas import UserResponse, UserCreate, UserLogin

logger = logging.getLogger(__name__)

class SupabaseAuthService:
    """Authentication service using Supabase Auth"""
    
    def __init__(self):
        self.supabase = supabase_client
        self.security = SecurityManager()
    
    async def register_user(self, user_data: UserCreate) -> Dict[str, Any]:
        """Register a new user with Supabase Auth"""
        try:
            # Check if user already exists
            existing_user = await self.get_user_by_email(user_data.email)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bu email adresi zaten kayıtlı"
                )
            
            # Create user metadata
            user_metadata = {
                "full_name": user_data.full_name,
                "role": user_data.role if hasattr(user_data, 'role') else "user"
            }
            
            # Register with Supabase
            result = await self.supabase.register_user(
                email=user_data.email,
                password=user_data.password,
                user_metadata=user_metadata
            )
            
            if not result["success"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Kullanıcı kaydı başarısız: {result['error']}"
                )
            
            # Create response
            user_response = UserResponse(
                id=result["user"].id,
                email=result["user"].email,
                full_name=user_metadata.get("full_name"),
                role=user_metadata.get("role", "user"),
                created_at=datetime.now()
            )
            
            # Generate JWT token
            access_token = self.security.create_access_token(
                data={
                    "sub": str(result["user"].id),
                    "email": result["user"].email,
                    "role": user_metadata.get("role", "user")
                }
            )
            
            return {
                "user": user_response,
                "access_token": access_token,
                "token_type": "bearer"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Kullanıcı kaydı sırasında bir hata oluştu"
            )
    
    async def authenticate_user(self, login_data: UserLogin) -> Dict[str, Any]:
        """Authenticate user with Supabase Auth"""
        try:
            # Authenticate with Supabase
            result = await self.supabase.authenticate_user(
                email=login_data.email,
                password=login_data.password
            )
            
            if not result["success"]:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Email veya şifre hatalı"
                )
            
            # Get user metadata
            user = result["user"]
            user_metadata = getattr(user, 'user_metadata', {}) or {}
            
            # Create response
            user_response = UserResponse(
                id=getattr(user, 'id', None),
                email=getattr(user, 'email', None),
                full_name=user_metadata.get("full_name"),
                role=user_metadata.get("role", "user"),
                created_at=datetime.now()
            )
            
            # Generate JWT token
            access_token = self.security.create_access_token(
                data={
                    "sub": str(getattr(user, 'id', '')),
                    "email": getattr(user, 'email', ''),
                    "role": user_metadata.get("role", "user")
                }
            )
            
            return {
                "user": user_response,
                "access_token": access_token,
                "token_type": "bearer"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Giriş işlemi sırasında bir hata oluştu"
            )
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        try:
            # Use service client to query users table
            response = self.supabase.service_client.table("auth.users")\
                .select("*")\
                .eq("email", email)\
                .single()\
                .execute()
            
            return response.data if response.data else None
        except Exception as e:
            logger.debug(f"User not found: {email}")
            return None
    
    async def get_user_by_id(self, user_id: str) -> Optional[UserResponse]:
        """Get user by ID"""
        try:
            user_data = await self.supabase.get_user_by_id(user_id)
            if not user_data:
                return None
            
            user_metadata = user_data.get("user_metadata", {}) or {}
            
            return UserResponse(
                id=user_data.get("id"),
                email=user_data.get("email"),
                full_name=user_metadata.get("full_name"),
                role=user_metadata.get("role", "user"),
                created_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {str(e)}")
            return None
    
    async def update_user_role(self, user_id: str, role: str) -> bool:
        """Update user role"""
        try:
            return await self.supabase.update_user_role(user_id, role)
        except Exception as e:
            logger.error(f"Failed to update user role: {str(e)}")
            return False
    
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return user data"""
        try:
            payload = self.security.verify_token(token)
            if not payload:
                return None
            
            user_id = payload.get("sub")
            if not user_id:
                return None
            
            # Get fresh user data
            user = await self.get_user_by_id(user_id)
            if not user:
                return None
            
            return {
                "user_id": user_id,
                "email": payload.get("email"),
                "role": payload.get("role", "user"),
                "user": user
            }
            
        except Exception as e:
            logger.error(f"Token verification failed: {str(e)}")
            return None

# Global auth service instance
auth_service = SupabaseAuthService()