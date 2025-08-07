#!/usr/bin/env python3
"""
MevzuatGPT Admin User Creator
Admin kullanıcısı oluşturur
"""

import os
import sys
import random
import string
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

def generate_random_password(length=12):
    """Güvenli rastgele şifre oluştur"""
    characters = string.ascii_letters + string.digits + "!@#$%&"
    return ''.join(random.choice(characters) for _ in range(length))

def generate_random_email():
    """Rastgele admin email oluştur"""
    domains = ['mevzuatgpt.com', 'admin.mevzuat.com', 'hukuk.admin.com']
    names = ['admin', 'yonetici', 'hukuk.admin', 'mevzuat.admin', 'sistem.admin']
    
    name = random.choice(names)
    domain = random.choice(domains)
    random_num = random.randint(100, 999)
    
    return f"{name}{random_num}@{domain}"

def create_admin_user():
    """Admin kullanıcı oluştur"""
    try:
        # Supabase bağlantısı
        SUPABASE_URL = os.getenv('SUPABASE_URL')
        SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            print("❌ HATA: Supabase environment variables bulunamadı!")
            return False
            
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        
        # Rastgele admin bilgileri
        email = generate_random_email()
        password = generate_random_password()
        full_name = f"Admin {random.randint(1, 100)}"
        
        print("🔧 Admin kullanıcı oluşturuluyor...")
        print(f"Email: {email}")
        print(f"Şifre: {password}")
        print(f"İsim: {full_name}")
        print("-" * 50)
        
        # Admin kullanıcı oluştur
        admin_user = supabase.auth.admin.create_user({
            'email': email,
            'password': password,
            'email_confirm': True,
            'user_metadata': {
                'role': 'admin',
                'full_name': full_name,
                'created_by': 'system',
                'creation_date': datetime.now().isoformat()
            }
        })
        
        print("✅ BAŞARILI! Admin kullanıcı oluşturuldu:")
        print(f"📧 Email: {email}")
        print(f"🔒 Şifre: {password}")
        print(f"👤 İsim: {full_name}")
        print(f"🆔 User ID: {admin_user.user.id}")
        print(f"🔑 Role: admin")
        print("-" * 50)
        
        # Login testi
        print("🧪 Login test yapılıyor...")
        login_response = supabase.auth.sign_in_with_password({
            'email': email,
            'password': password
        })
        
        if login_response.user:
            print("✅ Login testi başarılı!")
            print(f"Access token alındı: {login_response.session.access_token[:50]}...")
        else:
            print("❌ Login testi başarısız!")
            
        return True
        
    except Exception as e:
        print(f"❌ HATA: Admin kullanıcı oluşturulamadı: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 MevzuatGPT Admin User Creator")
    print("=" * 60)
    
    success = create_admin_user()
    
    if success:
        print("\n🎉 Admin kullanıcı başarıyla oluşturuldu!")
        print("Bu bilgileri güvenli bir yerde saklayın.")
    else:
        print("\n💥 Kullanıcı oluşturulamadı!")
        sys.exit(1)