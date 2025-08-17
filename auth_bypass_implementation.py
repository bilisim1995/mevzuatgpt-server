"""
Auth Bypass Implementation for Self-hosted Supabase
When email logins are disabled, implement direct database authentication
"""

import asyncio
import asyncpg
from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt
import logging

logger = logging.getLogger(__name__)

class DirectAuthService:
    """Direct database authentication when Supabase auth is disabled"""
    
    def __init__(self, database_url: str, jwt_secret: str):
        self.database_url = database_url
        self.jwt_secret = jwt_secret
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    async def authenticate_user_direct(self, email: str, password: str) -> dict:
        """Authenticate user directly against database"""
        try:
            conn = await asyncpg.connect(self.database_url)
            
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
            if not self.pwd_context.verify(password, auth_user['encrypted_password']):
                await conn.close()
                return {"success": False, "error": "Invalid password"}
            
            # Get user profile
            profile = await conn.fetchrow('''
                SELECT * FROM user_profiles 
                WHERE user_id = $1
            ''', auth_user['id'])
            
            await conn.close()
            
            if not profile:
                return {"success": False, "error": "Profile not found"}
            
            # Generate JWT token
            payload = {
                "sub": str(auth_user['id']),
                "email": auth_user['email'],
                "role": profile['role'],
                "exp": datetime.utcnow() + timedelta(hours=1),
                "iat": datetime.utcnow()
            }
            
            token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
            
            return {
                "success": True,
                "user": {
                    "id": str(auth_user['id']),
                    "email": auth_user['email'],
                    "role": profile['role'],
                    "full_name": profile.get('full_name'),
                    "credits": profile.get('credits', 0),
                    "is_active": profile.get('is_active', True)
                },
                "access_token": token,
                "token_type": "bearer"
            }
            
        except Exception as e:
            logger.error(f"Direct auth failed: {e}")
            return {"success": False, "error": str(e)}

async def test_direct_auth():
    """Test direct authentication"""
    auth_service = DirectAuthService(
        database_url='postgresql://postgres.5556795:ObMevzuat2025Pas@supabase.mevzuatgpt.org:5432/postgres',
        jwt_secret='mevzuatgpt-secret-key-2025'
    )
    
    result = await auth_service.authenticate_user_direct(
        email='admin@mevzuatgpt.com',
        password='AdminMevzuat2025!'
    )
    
    print(f"Auth result: {result}")
    return result

if __name__ == "__main__":
    asyncio.run(test_direct_auth())