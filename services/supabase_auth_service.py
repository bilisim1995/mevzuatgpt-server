"""
Supabase-based authentication service
Handles user registration, login, and role-based access control
"""

import logging
import secrets
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
from fastapi import HTTPException, status
from core.supabase_client import supabase_client
from core.security import SecurityManager
from models.schemas import UserResponse, UserCreate, UserLogin, UserProfileUpdate
from services.email_service import email_service

logger = logging.getLogger(__name__)

class SupabaseAuthService:
    """Authentication service using Supabase Auth"""
    
    def __init__(self):
        self.supabase = supabase_client
        self.security = SecurityManager()
    
    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string safely"""
        if not date_str:
            return None
        try:
            # Handle timezone info if present
            if date_str.endswith('Z'):
                date_str = date_str[:-1] + '+00:00'
            elif '+' not in date_str and 'T' in date_str:
                date_str = date_str + '+00:00'
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except Exception:
            return datetime.now()
    
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
                    
                    # Add initial credits to new user (sync version - direct database insert)
                    try:
                        # Direct credit insertion without async complications
                        initial_credit_amount = 30
                        
                        # Check if user already has credits
                        existing_credits = self.supabase.service_client.table('user_credits') \
                            .select('id') \
                            .eq('user_id', user_id) \
                            .limit(1) \
                            .execute()
                        
                        # Skip complex transaction recording, just set balance directly
                        existing_balance = self.supabase.service_client.table('user_credit_balance') \
                            .select('id') \
                            .eq('user_id', user_id) \
                            .limit(1) \
                            .execute()
                        
                        if not existing_balance.data:
                            # Direct balance insert for initial credits
                            balance_data = {
                                'user_id': user_id,
                                'current_balance': initial_credit_amount
                            }
                            
                            balance_result = self.supabase.service_client.table('user_credit_balance') \
                                .insert(balance_data) \
                                .execute()
                            
                            if balance_result.data:
                                logger.info(f"Initial credits ({initial_credit_amount}) balance set for new user {user_id}")
                            else:
                                logger.warning(f"Failed to set initial credit balance for {user_id}")
                        else:
                            logger.info(f"User {user_id} already has credit balance, skipping initial credit")
                            
                    except Exception as credit_error:
                        logger.error(f"Failed to add initial credits for {user_id}: {credit_error}")
                        # Don't fail registration, just log error
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
            
            # Send welcome email (async, don't block registration)
            try:
                await email_service.send_welcome_email(
                    to_email=user_data.email,
                    user_name=user_data.full_name
                )
                logger.info(f"Welcome email sent to {user_data.email}")
            except Exception as email_error:
                logger.error(f"Failed to send welcome email to {user_data.email}: {email_error}")
                # Don't fail registration if email fails
            
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
                ad=profile_data.get("ad"),  # Get from database
                soyad=profile_data.get("soyad"),
                meslek=profile_data.get("meslek"),
                calistigi_yer=profile_data.get("calistigi_yer"),
                role=profile_data.get("role", "user"),
                created_at=self._parse_datetime(profile_data.get("created_at")) or datetime.now(),
                updated_at=self._parse_datetime(profile_data.get("updated_at"))
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
            # Use service client to query user_profiles table
            response = self.supabase.service_client.table("user_profiles")\
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
                ad=profile_data.get("ad"),  # Get from database
                soyad=profile_data.get("soyad"),
                meslek=profile_data.get("meslek"),
                calistigi_yer=profile_data.get("calistigi_yer"),
                role=profile_data.get("role", "user"),
                created_at=self._parse_datetime(profile_data.get("created_at")) or datetime.now(),
                updated_at=self._parse_datetime(profile_data.get("updated_at"))
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
    
    async def create_password_reset_token(self, email: str) -> Optional[str]:
        """
        Create a password reset token for user
        
        Args:
            email: User's email address
            
        Returns:
            str: Reset token if successful, None otherwise
        """
        try:
            # Check if user exists
            user = await self.get_user_by_email(email)
            if not user:
                logger.warning(f"Password reset requested for non-existent user: {email}")
                # Don't reveal whether user exists or not
                return None
            
            # Generate secure reset token
            reset_token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(hours=24)  # 24 hour expiry
            
            # Store reset token in Redis with TTL (alternative to database)
            try:
                import redis
                import json
                from core.config import settings
                
                # Connect to Redis
                redis_client = redis.from_url(settings.REDIS_URL)
                
                # Store token with email and expiry info
                token_data = {
                    "email": email,
                    "expires_at": expires_at.isoformat()
                }
                
                # Set with 24 hour expiry
                redis_client.setex(
                    f"reset_token:{reset_token}", 
                    24 * 60 * 60,  # 24 hours in seconds
                    json.dumps(token_data)
                )
                
                logger.info(f"Password reset token created for user: {email}")
                return reset_token
                    
            except Exception as e:
                logger.error(f"Database error storing reset token: {str(e)}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating password reset token: {str(e)}")
            return None
    
    async def verify_reset_token(self, token: str) -> Optional[str]:
        """
        Verify password reset token and return user email
        
        Args:
            token: Reset token to verify
            
        Returns:
            str: User email if token is valid, None otherwise
        """
        try:
            import redis
            import json
            from core.config import settings
            
            # Connect to Redis
            redis_client = redis.from_url(settings.REDIS_URL)
            
            # Get token data from Redis
            token_data_str = redis_client.get(f"reset_token:{token}")
            if not token_data_str:
                logger.warning("Invalid or expired reset token provided")
                return None
            
            # Parse token data
            token_data = json.loads(token_data_str)
            email = token_data.get("email")
            expires_str = token_data.get("expires_at")
            
            if not email or not expires_str:
                logger.warning("Invalid token data format")
                return None
            
            # Double-check expiry (Redis TTL should handle this, but extra safety)
            try:
                expires_at = datetime.fromisoformat(expires_str.replace('Z', '+00:00'))
                if datetime.now() > expires_at:
                    logger.warning(f"Reset token expired for user: {email}")
                    redis_client.delete(f"reset_token:{token}")
                    return None
            except Exception:
                logger.warning("Invalid reset token expiry format")
                return None
            
            return email
            
        except Exception as e:
            logger.error(f"Error verifying reset token: {str(e)}")
            return None
    
    async def reset_password(self, token: str, new_password: str) -> bool:
        """
        Reset user password using reset token
        
        Args:
            token: Valid reset token
            new_password: New password
            
        Returns:
            bool: True if password reset successful, False otherwise
        """
        try:
            # Verify token and get user email
            email = await self.verify_reset_token(token)
            if not email:
                return False
            
            # Update password in Supabase Auth
            try:
                # Get user by email first
                auth_result = self.supabase.service_client.auth.admin.list_users()
                user_id = None
                
                for user in auth_result.users:
                    if user.email == email:
                        user_id = user.id
                        break
                
                if not user_id:
                    logger.error(f"User not found in auth for email: {email}")
                    return False
                
                # Update password
                self.supabase.service_client.auth.admin.update_user_by_id(
                    user_id,
                    {"password": new_password}
                )
                
                # Clear reset token after successful password change
                await self._clear_reset_token(token)
                
                logger.info(f"Password successfully reset for user: {email}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to update password in Supabase Auth: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"Error resetting password: {str(e)}")
            return False
    
    async def _clear_reset_token(self, token: str) -> None:
        """Clear reset token from Redis"""
        try:
            import redis
            from core.config import settings
            
            redis_client = redis.from_url(settings.REDIS_URL)
            redis_client.delete(f"reset_token:{token}")
        except Exception as e:
            logger.warning(f"Failed to clear reset token: {str(e)}")
    
    async def send_password_reset_email(self, email: str) -> bool:
        """
        Send password reset email to user
        
        Args:
            email: User's email address
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Create reset token
            reset_token = await self.create_password_reset_token(email)
            if not reset_token:
                # Always return True to prevent email enumeration
                return True
            
            # Get user info for personalization
            user_data = await self.get_user_by_email(email)
            user_name = user_data.get("full_name") if user_data else None
            
            # Send email
            email_sent = await email_service.send_password_reset_email(
                to_email=email,
                reset_token=reset_token,
                user_name=user_name
            )
            
            if email_sent:
                logger.info(f"Password reset email sent to: {email}")
            else:
                logger.error(f"Failed to send password reset email to: {email}")
            
            # Always return True to prevent email enumeration
            return True
            
        except Exception as e:
            logger.error(f"Error sending password reset email: {str(e)}")
            # Always return True to prevent email enumeration
            return True

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