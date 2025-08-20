import asyncio
import sys
import os
sys.path.append('.')
from models.supabase_client import get_supabase_client

async def create_test_admin():
    """Create test admin user for document upload testing"""
    try:
        supabase = get_supabase_client()
        
        # Test admin credentials
        test_email = "admin@test.com"
        test_password = "TestAdmin123!"
        
        print(f"🔑 Creating test admin: {test_email}")
        
        # Sign up user
        auth_response = supabase.auth.sign_up({
            "email": test_email,
            "password": test_password
        })
        
        if auth_response.user:
            user_id = auth_response.user.id
            print(f"✅ User created with ID: {user_id}")
            
            # Insert into user_profiles as admin
            profile_response = supabase.table("user_profiles").insert({
                "id": user_id,
                "email": test_email,
                "role": "admin",
                "is_active": True,
                "display_name": "Test Admin"
            }).execute()
            
            print("✅ Admin profile created")
            print(f"📧 Email: {test_email}")
            print(f"🔒 Password: {test_password}")
            
            return test_email, test_password
        else:
            print("❌ User creation failed")
            return None, None
            
    except Exception as e:
        print(f"Error: {e}")
        return None, None

if __name__ == "__main__":
    email, password = asyncio.run(create_test_admin())
