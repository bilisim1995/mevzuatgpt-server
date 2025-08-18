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
from models.schemas import UserResponse, UserCreate, UserLogin, UserProfileUpdate

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
            
            # Register with Supabase Auth (minimal metadata)
            result = await self.supabase.register_user(
                email=user_data.email,
                password=user_data.password,
                user_metadata={}  # Empty metadata, will use user_profiles table
            )
            
            if not result["success"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Kullanıcı kaydı başarısız: {result['error']}"
                )
            
            user_id = str(result["user"].id)
            
            # Create user profile in user_profiles table using correct column name (id, not user_id)
            profile_data = {
                "id": user_id,  # Use id column instead of user_id
                "email": user_data.email,  # Add email field (required)
                "full_name": user_data.full_name,
                "ad": getattr(user_data, 'ad', None),
                "soyad": getattr(user_data, 'soyad', None),
                "meslek": getattr(user_data, 'meslek', None),
                "calistigi_yer": getattr(user_data, 'calistigi_yer', None),
                "role": getattr(user_data, 'role', 'user')
            }
            
            # Insert into user_profiles
            try:
                profile_result = self.supabase.service_client.table("user_profiles").insert(profile_data).execute()
                if profile_result.data:
                    logger.info(f"User profile created successfully for {user_id}")
                else:
                    logger.warning("Profile creation returned no data")
            except Exception as e:
                logger.error(f"Failed to create user profile: {e}")
                # Don't fail registration, just log error
            
            # Create response from user data (just registered)  
            user_response = UserResponse(
                id=user_id,
                email=user_data.email,
                full_name=user_data.full_name,
                ad=getattr(user_data, 'ad', None),
                soyad=getattr(user_data, 'soyad', None), 
                meslek=getattr(user_data, 'meslek', None),
                calistigi_yer=getattr(user_data, 'calistigi_yer', None),
                role=getattr(user_data, 'role', 'user'),
                created_at=datetime.now()
            )
            
            # Generate JWT token
            access_token = self.security.create_access_token(
                data={
                    "sub": user_id,
                    "email": user_data.email,
                    "role": getattr(user_data, 'role', 'user')
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
            
            # Get user profile from user_profiles table
            user = result["user"]
            user_id = str(getattr(user, 'id', ''))
            user_email = getattr(user, 'email', '')
            
            # If direct auth was used, get profile from result
            if result.get("direct_auth") and result.get("profile"):
                profile_data = result["profile"]
                logger.info("Using profile data from direct auth")
            else:
                # Fetch profile data from user_profiles table via Supabase REST (using id column, not user_id)
                try:
                    profile_result = self.supabase.service_client.table("user_profiles").select("*").eq("id", user_id).single().execute()
                    profile_data = profile_result.data if profile_result.data else {}
                    logger.info(f"Profile data retrieved for user {user_id}: {profile_data}")
                except Exception as e:
                    logger.warning(f"Failed to get user profile via REST, using defaults: {e}")
                    profile_data = {}
            
            # Create response from profile data (no preferences field)
            user_response = UserResponse(
                id=user_id,
                email=user_email,
                full_name=profile_data.get("full_name"),
                ad=None,  # These fields not in current schema
                soyad=None,
                meslek=None,
                calistigi_yer=None,
                role=profile_data.get("role", "user"),
                created_at=datetime.now()
            )
            
            # Generate JWT token
            access_token = self.security.create_access_token(
                data={
                    "sub": user_id,
                    "email": user_email,
                    "role": profile_data.get("role", "user")
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
        """Get user by ID from user_profiles table"""
        try:
            # Get profile data from user_profiles table using id column (not user_id)
            profile_result = self.supabase.service_client.table("user_profiles").select("*").eq("id", user_id).single().execute()
            
            if not profile_result.data:
                logger.warning(f"User profile not found for id: {user_id}")
                return None
            
            profile_data = profile_result.data
            
            return UserResponse(
                id=profile_data.get("id", user_id),  # Use id from profile
                email=profile_data.get("email", ""),
                full_name=profile_data.get("full_name"),
                ad=None,  # These fields not in current schema
                soyad=None,
                meslek=None,
                calistigi_yer=None,
                role=profile_data.get("role", "user"),
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

    async def update_user_profile(self, user_id: str, profile_data: UserProfileUpdate) -> bool:
        """
        Kullanıcı profil bilgilerini user_profiles tablosunda güncelle
        
        Args:
            user_id: Kullanıcı ID
            profile_data: Güncellenecek profil bilgileri
            
        Returns:
            Başarılı olursa True
        """
        try:
            # Prepare update data
            update_data = {}
            
            if profile_data.full_name is not None:
                update_data["full_name"] = profile_data.full_name
            if profile_data.ad is not None:
                update_data["ad"] = profile_data.ad
            if profile_data.soyad is not None:
                update_data["soyad"] = profile_data.soyad
            if profile_data.meslek is not None:
                update_data["meslek"] = profile_data.meslek
            if profile_data.calistigi_yer is not None:
                update_data["calistigi_yer"] = profile_data.calistigi_yer
            
            if not update_data:
                logger.warning("No data to update")
                return True
            
            # Add updated_at timestamp
            update_data["updated_at"] = datetime.now().isoformat()
            
            # Update user_profiles table
            result = self.supabase.service_client.table("user_profiles").update(update_data).eq("id", user_id).execute()
            
            if result.data:
                logger.info(f"User profile updated successfully: {user_id}")
                return True
            else:
                logger.error(f"Failed to update user profile: no data returned")
                return False
                
        except Exception as e:
            logger.error(f"Profile update error: {str(e)}")
            return False

# Global auth service instance
auth_service = SupabaseAuthService()