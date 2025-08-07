"""
Authentication service
Handles user management, authentication, and authorization operations
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Optional
import logging
from uuid import UUID

from core.security import security
from models.database import User
from models.schemas import UserCreate, UserProfileUpdate, UserResponse
from utils.exceptions import AppException

logger = logging.getLogger(__name__)

class AuthService:
    """Service class for authentication and user management operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """
        Create a new user account
        
        Args:
            user_data: User creation data
            
        Returns:
            Created user information
            
        Raises:
            AppException: If user creation fails
        """
        try:
            # Hash password
            hashed_password = security.hash_password(user_data.password)
            
            # Create user instance
            db_user = User(
                email=user_data.email,
                password_hash=hashed_password,
                full_name=user_data.full_name,
                role=user_data.role
            )
            
            # Add to database
            self.db.add(db_user)
            await self.db.flush()  # Flush to get the ID
            await self.db.refresh(db_user)
            
            logger.info(f"User created successfully: {user_data.email}")
            
            return UserResponse(
                id=db_user.id,
                email=db_user.email,
                full_name=db_user.full_name,
                role=db_user.role,
                created_at=db_user.created_at,
                updated_at=db_user.updated_at
            )
            
        except Exception as e:
            logger.error(f"Failed to create user {user_data.email}: {str(e)}")
            await self.db.rollback()
            raise AppException(
                message="Failed to create user account",
                detail=str(e),
                error_code="USER_CREATION_FAILED"
            )
    
    async def get_user_by_email(self, email: str) -> Optional[UserResponse]:
        """
        Get user by email address
        
        Args:
            email: User email address
            
        Returns:
            User information if found, None otherwise
        """
        try:
            stmt = select(User).where(User.email == email, User.is_active == True)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                return UserResponse(
                    id=user.id,
                    email=user.email,
                    full_name=user.full_name,
                    role=user.role,
                    created_at=user.created_at,
                    updated_at=user.updated_at
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get user by email {email}: {str(e)}")
            return None
    
    async def get_user_by_id(self, user_id: str) -> Optional[UserResponse]:
        """
        Get user by ID
        
        Args:
            user_id: User UUID
            
        Returns:
            User information if found, None otherwise
        """
        try:
            stmt = select(User).where(User.id == UUID(user_id), User.is_active == True)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                return UserResponse(
                    id=user.id,
                    email=user.email,
                    full_name=user.full_name,
                    role=user.role,
                    created_at=user.created_at,
                    updated_at=user.updated_at
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get user by ID {user_id}: {str(e)}")
            return None
    
    async def authenticate_user(self, email: str, password: str) -> Optional[UserResponse]:
        """
        Authenticate user with email and password
        
        Args:
            email: User email address
            password: Plain text password
            
        Returns:
            User information if authentication successful, None otherwise
        """
        try:
            stmt = select(User).where(User.email == email, User.is_active == True)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user and security.verify_password(password, user.password_hash):
                return UserResponse(
                    id=user.id,
                    email=user.email,
                    full_name=user.full_name,
                    role=user.role,
                    created_at=user.created_at,
                    updated_at=user.updated_at
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Authentication failed for {email}: {str(e)}")
            return None
    
    async def update_user_profile(
        self, 
        user_id: UUID, 
        profile_data: UserProfileUpdate
    ) -> UserResponse:
        """
        Update user profile information
        
        Args:
            user_id: User UUID
            profile_data: Updated profile data
            
        Returns:
            Updated user information
            
        Raises:
            AppException: If update fails
        """
        try:
            # Prepare update data
            update_data = {}
            if profile_data.full_name is not None:
                update_data["full_name"] = profile_data.full_name
            
            if not update_data:
                # No changes to make
                return await self.get_user_by_id(str(user_id))
            
            # Update user
            stmt = (
                update(User)
                .where(User.id == user_id, User.is_active == True)
                .values(**update_data)
                .returning(User)
            )
            
            result = await self.db.execute(stmt)
            updated_user = result.scalar_one_or_none()
            
            if not updated_user:
                raise AppException(
                    message="User not found",
                    error_code="USER_NOT_FOUND"
                )
            
            await self.db.flush()
            
            logger.info(f"User profile updated: {updated_user.email}")
            
            return UserResponse(
                id=updated_user.id,
                email=updated_user.email,
                full_name=updated_user.full_name,
                role=updated_user.role,
                created_at=updated_user.created_at,
                updated_at=updated_user.updated_at
            )
            
        except AppException:
            raise
        except Exception as e:
            logger.error(f"Failed to update user profile {user_id}: {str(e)}")
            await self.db.rollback()
            raise AppException(
                message="Failed to update user profile",
                detail=str(e),
                error_code="PROFILE_UPDATE_FAILED"
            )
    
    async def change_password(self, user_id: UUID, new_password: str) -> bool:
        """
        Change user password
        
        Args:
            user_id: User UUID
            new_password: New plain text password
            
        Returns:
            True if password changed successfully
            
        Raises:
            AppException: If password change fails
        """
        try:
            # Hash new password
            hashed_password = security.hash_password(new_password)
            
            # Update password
            stmt = (
                update(User)
                .where(User.id == user_id, User.is_active == True)
                .values(password_hash=hashed_password)
            )
            
            result = await self.db.execute(stmt)
            
            if result.rowcount == 0:
                raise AppException(
                    message="User not found",
                    error_code="USER_NOT_FOUND"
                )
            
            await self.db.flush()
            
            logger.info(f"Password changed for user: {user_id}")
            return True
            
        except AppException:
            raise
        except Exception as e:
            logger.error(f"Failed to change password for user {user_id}: {str(e)}")
            await self.db.rollback()
            raise AppException(
                message="Failed to change password",
                detail=str(e),
                error_code="PASSWORD_CHANGE_FAILED"
            )
    
    async def deactivate_user(self, user_id: UUID) -> bool:
        """
        Deactivate user account
        
        Args:
            user_id: User UUID
            
        Returns:
            True if user deactivated successfully
            
        Raises:
            AppException: If deactivation fails
        """
        try:
            stmt = (
                update(User)
                .where(User.id == user_id)
                .values(is_active=False)
            )
            
            result = await self.db.execute(stmt)
            
            if result.rowcount == 0:
                raise AppException(
                    message="User not found",
                    error_code="USER_NOT_FOUND"
                )
            
            await self.db.flush()
            
            logger.info(f"User deactivated: {user_id}")
            return True
            
        except AppException:
            raise
        except Exception as e:
            logger.error(f"Failed to deactivate user {user_id}: {str(e)}")
            await self.db.rollback()
            raise AppException(
                message="Failed to deactivate user",
                detail=str(e),
                error_code="USER_DEACTIVATION_FAILED"
            )
