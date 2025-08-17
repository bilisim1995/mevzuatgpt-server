"""
Supabase client configuration and utilities
Handles database connections, auth, and vector operations
"""

import logging
from typing import Optional, Dict, Any, List
from supabase import create_client, Client
from core.config import settings

logger = logging.getLogger(__name__)

class SupabaseClient:
    """Centralized Supabase client for database and auth operations"""
    
    def __init__(self):
        self.supabase: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY
        )
        self.service_client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )
    
    def get_client(self, use_service_key: bool = False) -> Client:
        """Get Supabase client (service key for admin operations)"""
        return self.service_client if use_service_key else self.supabase
    
    async def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user with Supabase Auth or direct database fallback"""
        try:
            # Try Supabase Auth first
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            return {
                "success": True,
                "user": response.user,
                "session": response.session
            }
        except Exception as e:
            logger.warning(f"Supabase Auth failed, trying direct database auth: {str(e)}")
            
            # Fallback to direct database authentication
            if "Email logins are disabled" in str(e) or "422" in str(e):
                return await self._authenticate_direct(email, password)
            
            logger.error(f"Authentication failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _authenticate_direct(self, email: str, password: str) -> Dict[str, Any]:
        """Direct database authentication when Supabase auth is disabled"""
        try:
            from passlib.context import CryptContext
            import asyncpg
            from core.config import settings
            
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            
            # Connect to database
            conn = await asyncpg.connect(settings.DATABASE_URL)
            
            # Get user from auth.users
            auth_user = await conn.fetchrow('''
                SELECT id, email, encrypted_password 
                FROM auth.users 
                WHERE email = $1
            ''', email)
            
            if not auth_user:
                await conn.close()
                return {"success": False, "error": "User not found"}
            
            # Verify password
            if not pwd_context.verify(password, auth_user['encrypted_password']):
                await conn.close()
                return {"success": False, "error": "Invalid credentials"}
            
            # Get user profile
            profile = await conn.fetchrow('''
                SELECT * FROM user_profiles 
                WHERE user_id = $1
            ''', auth_user['id'])
            
            await conn.close()
            
            if not profile:
                return {"success": False, "error": "Profile not found"}
            
            # Create mock user object
            class MockUser:
                def __init__(self, user_id, email):
                    self.id = str(user_id)
                    self.email = email
            
            return {
                "success": True,
                "user": MockUser(auth_user['id'], auth_user['email']),
                "session": None,
                "profile": dict(profile) if profile else {},  # Add profile data as dict
                "direct_auth": True  # Flag for direct auth
            }
            
        except Exception as e:
            logger.error(f"Direct auth failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def register_user(self, email: str, password: str, user_metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Register new user with Supabase Auth"""
        try:
            response = self.supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": user_metadata or {}
                }
            })
            return {
                "success": True,
                "user": response.user,
                "session": response.session
            }
        except Exception as e:
            logger.error(f"Registration failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user details by ID"""
        try:
            response = self.service_client.auth.admin.get_user_by_id(user_id)
            return response.user
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {str(e)}")
            return None
    
    async def update_user_role(self, user_id: str, role: str) -> bool:
        """Update user role in Supabase"""
        try:
            response = self.service_client.auth.admin.update_user_by_id(
                user_id,
                {"user_metadata": {"role": role}}
            )
            return response.user is not None
        except Exception as e:
            logger.error(f"Failed to update user role: {str(e)}")
            return False
    
    async def store_embedding(self, document_id: str, content: str, embedding: List[float], metadata: Optional[Dict] = None) -> bool:
        """Store document embedding in Supabase with vector support"""
        try:
            data = {
                "document_id": document_id,
                "content": content,
                "embedding": embedding,
                "metadata": metadata or {}
            }
            
            response = self.service_client.table("mevzuat_embeddings").insert(data).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Failed to store embedding: {str(e)}")
            return False
    
    async def search_similar_embeddings(self, query_embedding: List[float], limit: int = 10, similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search for similar embeddings using vector similarity"""
        try:
            # Supabase vector similarity search using RPC
            response = self.service_client.rpc(
                "search_embeddings",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": similarity_threshold,
                    "match_count": limit
                }
            ).execute()
            
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Failed to search embeddings: {str(e)}")
            return []
    
    async def get_document_metadata(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document metadata from Supabase"""
        try:
            response = self.service_client.table("mevzuat_documents")\
                .select("*")\
                .eq("id", document_id)\
                .single()\
                .execute()
            
            return response.data if response.data else None
        except Exception as e:
            logger.error(f"Failed to get document metadata: {str(e)}")
            return None
    
    async def store_document_metadata(self, document_data: Dict[str, Any]) -> Optional[str]:
        """Store document metadata in Supabase"""
        try:
            response = self.service_client.table("mevzuat_documents")\
                .insert(document_data)\
                .execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]["id"]
            return None
        except Exception as e:
            logger.error(f"Failed to store document metadata: {str(e)}")
            return None
    
    async def log_search_activity(self, user_id: Optional[str], query: str, results_count: int, execution_time: float, ip_address: Optional[str] = None) -> bool:
        """Log search activity for analytics"""
        try:
            data = {
                "user_id": user_id,
                "query": query,
                "results_count": results_count,
                "execution_time": execution_time,
                "ip_address": ip_address
            }
            
            response = self.service_client.table("search_logs").insert(data).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Failed to log search activity: {str(e)}")
            return False

# Global Supabase client instance
supabase_client = SupabaseClient()