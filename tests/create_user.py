#!/usr/bin/env python3
"""
MevzuatGPT User Creator
Normal kullanıcı oluşturur
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

def generate_random_password(length=10):
    """Güvenli rastgele şifre oluştur"""
    characters = string.ascii_letters + string.digits + "!@#"
    return ''.join(random.choice(characters) for _ in range(length))

def generate_random_email():
    """Rastgele kullanıcı email oluştur"""
    domains = ['example.com', 'test.com', 'kullanici.com', 'hukuk.net', 'mevzuat.org']
    first_names = ['ahmet', 'mehmet', 'ayse', 'fatma', 'ali', 'veli', 'zehra', 'osman', 'elif', 'murat']
    last_names = ['yilmaz', 'kaya', 'demir', 'celik', 'aydin', 'ozturk', 'arslan', 'dogan', 'koc', 'sen']
    
    first_name = random.choice(first_names)
    last_name = random.choice(last_names)
    domain = random.choice(domains)
    random_num = random.randint(10, 999)
    
    return f"{first_name}.{last_name}{random_num}@{domain}"

def generate_random_full_name():
    """Rastgele tam isim oluştur"""
    first_names = ['Ahmet', 'Mehmet', 'Ayşe', 'Fatma', 'Ali', 'Veli', 'Zehra', 'Osman', 'Elif', 'Murat', 'Emre', 'Seda']
    last_names = ['Yılmaz', 'Kaya', 'Demir', 'Çelik', 'Aydın', 'Öztürk', 'Arslan', 'Doğan', 'Koç', 'Şen', 'Güzel', 'Akın']
    
    return f"{random.choice(first_names)} {random.choice(last_names)}"

def create_user():
    """Normal kullanıcı oluştur"""
    try:
        # Supabase bağlantısı
        SUPABASE_URL = os.getenv('SUPABASE_URL')
        SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            print("❌ HATA: Supabase environment variables bulunamadı!")
            return False
            
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        
        # Rastgele kullanıcı bilgileri
        email = generate_random_email()
        password = generate_random_password()
        full_name = generate_random_full_name()
        
        print("👤 Normal kullanıcı oluşturuluyor...")
        print(f"Email: {email}")
        print(f"Şifre: {password}")
        print(f"İsim: {full_name}")
        print("-" * 50)
        
        # Normal kullanıcı oluştur
        user = supabase.auth.admin.create_user({
            'email': email,
            'password': password,
            'email_confirm': True,
            'user_metadata': {
                'role': 'user',
                'full_name': full_name,
                'created_by': 'system',
                'creation_date': datetime.now().isoformat(),
                'user_type': 'regular'
            }
        })
        
        print("✅ BAŞARILI! Kullanıcı oluşturuldu:")
        print(f"📧 Email: {email}")
        print(f"🔒 Şifre: {password}")
        print(f"👤 İsim: {full_name}")
        print(f"🆔 User ID: {user.user.id}")
        print(f"🔑 Role: user")
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
        print(f"❌ HATA: Kullanıcı oluşturulamadı: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("👥 MevzuatGPT User Creator")
    print("=" * 60)
    
    success = create_user()
    
    if success:
        print("\n🎉 Kullanıcı başarıyla oluşturuldu!")
        print("Bu bilgileri güvenli bir yerde saklayın.")
    else:
        print("\n💥 Kullanıcı oluşturulamadı!")
        sys.exit(1)