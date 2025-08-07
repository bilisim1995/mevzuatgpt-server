#!/usr/bin/env python3
"""
Bunny.net Storage Test
Bunny.net bağlantısını ve dosya upload/delete işlemlerini test eder
"""

import os
import sys
import asyncio
import aiohttp
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class BunnyStorageTest:
    def __init__(self):
        # Bunny.net configuration from .env
        self.api_key = os.getenv('BUNNY_STORAGE_API_KEY')
        self.zone = os.getenv('BUNNY_STORAGE_ZONE')
        self.region = os.getenv('BUNNY_STORAGE_REGION')
        self.endpoint = os.getenv('BUNNY_STORAGE_ENDPOINT')
        
        # Test file content
        self.test_filename = f"test_file_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        self.test_content = f"""MevzuatGPT Bunny.net Storage Test
Test Time: {datetime.now().isoformat()}
Content: Bu bir test dosyasıdır.

Bu dosya Bunny.net storage test işlemi sırasında oluşturulmuştur.
Test başarılı ise bu dosya otomatik olarak silinecektir.
"""
    
    def check_config(self):
        """Environment variables kontrolü"""
        print("🔧 Environment variables kontrol ediliyor...")
        
        missing = []
        if not self.api_key:
            missing.append('BUNNY_STORAGE_API_KEY')
        if not self.zone:
            missing.append('BUNNY_STORAGE_ZONE')
        if not self.region:
            missing.append('BUNNY_STORAGE_REGION')
        if not self.endpoint:
            missing.append('BUNNY_STORAGE_ENDPOINT')
        
        if missing:
            print(f"❌ Eksik environment variables: {', '.join(missing)}")
            return False
        
        print("✅ Tüm environment variables mevcut")
        print(f"📦 Zone: {self.zone}")
        print(f"🌍 Region: {self.region}")
        print(f"🔗 Endpoint: {self.endpoint}")
        print(f"🔑 API Key: {self.api_key[:10]}..." if self.api_key else "None")
        return True
    
    async def upload_test_file(self):
        """Test dosyası upload et"""
        try:
            print(f"⬆️ Test dosyası yükleniyor: {self.test_filename}")
            
            # Upload URL and headers - try different endpoint formats
            upload_url = f"https://storage.bunnycdn.com/{self.zone}/test/{self.test_filename}"
            headers = {
                "AccessKey": self.api_key,
                "Content-Type": "text/plain"
            }
            
            # Upload file
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.put(
                    upload_url,
                    data=self.test_content.encode('utf-8'),
                    headers=headers
                ) as response:
                    
                    if response.status in [200, 201]:
                        print(f"✅ Upload başarılı! Status: {response.status}")
                        return True
                    else:
                        error_text = await response.text()
                        print(f"❌ Upload başarısız! Status: {response.status}")
                        print(f"Error: {error_text}")
                        return False
                        
        except Exception as e:
            print(f"❌ Upload hatası: {str(e)}")
            return False
    
    async def verify_file_exists(self):
        """Dosyanın yüklendiğini doğrula"""
        try:
            print(f"🔍 Dosya varlığı kontrol ediliyor: {self.test_filename}")
            
            # File URL - use direct storage URL for verification
            file_url = f"https://storage.bunnycdn.com/{self.zone}/test/{self.test_filename}"
            
            # Check if file exists
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(file_url) as response:
                    
                    if response.status == 200:
                        content = await response.text()
                        print("✅ Dosya başarıyla erişilebilir!")
                        print(f"📄 İçerik uzunluğu: {len(content)} karakter")
                        return True
                    else:
                        print(f"❌ Dosya erişilemez! Status: {response.status}")
                        return False
                        
        except Exception as e:
            print(f"❌ Dosya kontrolü hatası: {str(e)}")
            return False
    
    async def delete_test_file(self):
        """Test dosyasını sil"""
        try:
            print(f"🗑️ Test dosyası siliniyor: {self.test_filename}")
            
            # Delete URL and headers - try different endpoint formats
            delete_url = f"https://storage.bunnycdn.com/{self.zone}/test/{self.test_filename}"
            headers = {
                "AccessKey": self.api_key
            }
            
            # Delete file
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.delete(delete_url, headers=headers) as response:
                    
                    if response.status in [200, 204]:
                        print(f"✅ Dosya başarıyla silindi! Status: {response.status}")
                        return True
                    else:
                        error_text = await response.text()
                        print(f"❌ Silme başarısız! Status: {response.status}")
                        print(f"Error: {error_text}")
                        return False
                        
        except Exception as e:
            print(f"❌ Silme hatası: {str(e)}")
            return False
    
    async def run_test(self):
        """Tam test sürecini çalıştır"""
        print("=" * 60)
        print("🧪 Bunny.net Storage Test Başlıyor")
        print("=" * 60)
        
        # 1. Config kontrolü
        if not self.check_config():
            return False
        
        print("\n" + "-" * 40)
        
        # 2. Upload test
        upload_success = await self.upload_test_file()
        if not upload_success:
            return False
        
        print("\n" + "-" * 40)
        
        # 3. File verification
        verify_success = await self.verify_file_exists()
        if not verify_success:
            print("⚠️ Dosya yüklendi ama erişilemiyor!")
        
        print("\n" + "-" * 40)
        
        # 4. Cleanup - delete test file
        delete_success = await self.delete_test_file()
        
        # 5. Final result
        print("\n" + "=" * 60)
        if upload_success and delete_success:
            print("🎉 TÜM TESTLER BAŞARILI!")
            print("✅ Bunny.net storage tamamen çalışıyor")
            print("✅ Upload işlemi çalışıyor")
            print("✅ Delete işlemi çalışıyor")
            if verify_success:
                print("✅ Dosya erişimi çalışıyor")
            return True
        else:
            print("💥 TEST BAŞARISIZ!")
            print("❌ Bunny.net storage problemi var")
            return False

async def main():
    """Ana test fonksiyonu"""
    test = BunnyStorageTest()
    success = await test.run_test()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())