#!/usr/bin/env python3
"""
Çoklu PDF yükleme testi için script
"""
import asyncio
import httpx
import json
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os
import time

API_BASE = "http://localhost:5000"

def create_test_pdf(filename, title, content):
    """Test PDF oluştur"""
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Başlık
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, title)
    
    # İçerik
    c.setFont("Helvetica", 12)
    y_position = height - 100
    for line in content.split('\n'):
        if line.strip():
            c.drawString(50, y_position, line)
            y_position -= 20
    
    c.save()
    print(f"✅ PDF oluşturuldu: {filename}")

async def get_admin_token():
    """Admin token al"""
    async with httpx.AsyncClient() as client:
        # Önce admin kullanıcısı oluştur/login yap
        try:
            # Login dene
            response = await client.post(
                f"{API_BASE}/api/auth/login",
                json={
                    "email": "testadmin@mevzuatgpt.org",
                    "password": "TestAdmin123!"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                if token:
                    print("✅ Admin token alındı")
                    return token
            
            print(f"❌ Login başarısız: {response.status_code}")
            print(response.text)
            return None
            
        except Exception as e:
            print(f"❌ Token alma hatası: {e}")
            return None

async def bulk_upload_test(token):
    """Bulk upload testi"""
    print("\n📤 Bulk upload başlıyor...")
    
    # Test PDF'leri oluştur
    pdf1_content = """
2024 Yılı Merkezi Yönetim Bütçe Kanunu

Madde 1: Bu kanun, 2024 mali yılı merkezi yönetim bütçesini kapsar.

Madde 2: Genel bütçe kapsamındaki kamu idarelerinin 2024 yılı
gider ve gelir bütçeleri ekteki cetvellerde gösterilmiştir.

Madde 3: Hazine tarafından 2024 yılında yapılacak borçlanmalar
toplamı 850 milyar TL'yi geçemez.

Madde 4: Bu kanun 1 Ocak 2024 tarihinde yürürlüğe girer.
    """
    
    pdf2_content = """
Kamu Personeli Çalışma Yönetmeliği

Madde 1: Bu yönetmelik kamu personelinin çalışma usul ve
esaslarını düzenler.

Madde 2: Mesai saatleri hafta içi 08:30 - 17:30 arasındadır.
Öğle tatili 12:00 - 13:00 saatleri arasındadır.

Madde 3: Yıllık izin hakları:
- 1-5 yıl arası çalışanlar: 20 gün
- 5-10 yıl arası çalışanlar: 25 gün
- 10 yıl üzeri çalışanlar: 30 gün

Madde 4: Bu yönetmelik yayımı tarihinde yürürlüğe girer.
    """
    
    create_test_pdf("test_butce_kanunu.pdf", "2024 Bütçe Kanunu", pdf1_content)
    create_test_pdf("test_calisma_yonetmeligi.pdf", "Çalışma Yönetmeliği", pdf2_content)
    
    # Bulk upload
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # Dosyaları hazırla
            file1 = open("test_butce_kanunu.pdf", "rb")
            file2 = open("test_calisma_yonetmeligi.pdf", "rb")
            
            files = [
                ("files", ("test_butce_kanunu.pdf", file1, "application/pdf")),
                ("files", ("test_calisma_yonetmeligi.pdf", file2, "application/pdf"))
            ]
            
            # Metadata JSON formatı
            metadata = {
                "pdf_sections": [
                    {
                        "output_filename": "test_butce_kanunu.pdf",
                        "title": "2024 Yılı Merkezi Yönetim Bütçe Kanunu",
                        "description": "Türkiye Cumhuriyeti 2024 mali yılı merkezi yönetim bütçe kanunu",
                        "keywords": "bütçe, 2024, kanun, merkezi yönetim"
                    },
                    {
                        "output_filename": "test_calisma_yonetmeligi.pdf",
                        "title": "Kamu Personeli Çalışma Yönetmeliği",
                        "description": "Kamu kurumlarında çalışan personelin çalışma usul ve esaslarını düzenleyen yönetmelik",
                        "keywords": "personel, çalışma, yönetmelik, kamu"
                    }
                ]
            }
            
            # Form data hazırla
            data = {
                "category": "Mevzuat",
                "institution": "Test Kurumu",
                "belge_adi": "Test Belgesi",
                "metadata": json.dumps(metadata)
            }
            
            response = await client.post(
                f"{API_BASE}/api/admin/documents/bulk-upload",
                headers={"Authorization": f"Bearer {token}"},
                files=files,
                data=data
            )
            
            print(f"\n📊 Upload Response Status: {response.status_code}")
            result = response.json()
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            if result.get("success") == True:
                batch_id = result["data"]["batch_id"]
                tasks = result["data"]["tasks"]
                
                print(f"\n✅ Upload başarılı!")
                print(f"Batch ID: {batch_id}")
                print(f"Total files: {result['data']['total_files']}")
                
                # Progress tracking
                await track_batch_progress(client, token, batch_id, tasks)
                
            else:
                print(f"❌ Upload başarısız: {result.get('message')}")
            
            # Cleanup - dosyaları kapat
            file1.close()
            file2.close()
                
        except Exception as e:
            print(f"❌ Upload hatası: {e}")
            import traceback
            traceback.print_exc()

async def track_batch_progress(client, token, batch_id, tasks):
    """Batch progress tracking"""
    print(f"\n📊 Progress tracking başlıyor...")
    print(f"Batch ID: {batch_id}")
    print(f"Task sayısı: {len(tasks)}\n")
    
    headers = {"Authorization": f"Bearer {token}"}
    max_attempts = 60  # 2 dakika (2 saniyede bir)
    attempt = 0
    
    while attempt < max_attempts:
        try:
            # Batch progress
            response = await client.get(
                f"{API_BASE}/api/admin/documents/bulk-upload/batch/{batch_id}/progress",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()["data"]
                
                print(f"⏱️  [{attempt*2}s] Batch Status: {data['batch_status']}")
                print(f"   ✅ Completed: {data['completed_count']}/{data['total_files']}")
                print(f"   ❌ Failed: {data['failed_count']}")
                print(f"   ⏳ Processing: {data['processing_count']}")
                print(f"   📋 Queued: {data['queued_count']}")
                
                # Individual task statuses
                for task in data['tasks']:
                    status_icon = {
                        'completed': '✅',
                        'failed': '❌',
                        'processing': '⏳',
                        'queued': '📋'
                    }.get(task['status'], '❓')
                    
                    print(f"   {status_icon} {task['filename']}: {task['status']}")
                    if task.get('error'):
                        print(f"      Error: {task['error']}")
                
                print()
                
                # Batch tamamlandı mı?
                if data['batch_status'] == 'completed':
                    print("🎉 Batch tamamlandı!")
                    print(f"Toplam süre: {attempt*2} saniye")
                    print(f"Başarılı: {data['completed_count']}, Başarısız: {data['failed_count']}")
                    break
            else:
                print(f"❌ Progress query hatası: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Progress tracking hatası: {e}")
        
        await asyncio.sleep(2)
        attempt += 1
    
    if attempt >= max_attempts:
        print("⚠️  Timeout: Batch tamamlanmadı (2 dakika)")

async def main():
    print("=" * 60)
    print("🧪 MevzuatGPT Bulk Upload Testi")
    print("=" * 60)
    
    # Admin token al
    token = await get_admin_token()
    if not token:
        print("❌ Token alınamadı, test iptal ediliyor")
        return
    
    # Bulk upload test
    await bulk_upload_test(token)
    
    # Cleanup
    print("\n🧹 Test dosyaları temizleniyor...")
    for f in ["test_butce_kanunu.pdf", "test_calisma_yonetmeligi.pdf"]:
        if os.path.exists(f):
            os.remove(f)
            print(f"Silindi: {f}")
    
    print("\n✅ Test tamamlandı!")

if __name__ == "__main__":
    asyncio.run(main())
