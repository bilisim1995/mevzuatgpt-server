#!/usr/bin/env python3
"""
Kredi yükleme mail bildirimi test scripti
Email service'in SMTP ile mail gönderme fonksiyonunu test eder
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.email_service import email_service


def test_credit_purchase_email():
    """Kredi satın alma mail bildirimi testi"""
    
    print("\n" + "=" * 70)
    print("SMTP KREDİ YÜKLEME MAİL TESTİ")
    print("=" * 70)
    
    # Test verileri
    test_data = {
        "to_email": "bozkurt.bilisim@hotmail.com",
        "credit_amount": 100,
        "price": "49.90",
        "payment_id": "TEST-1234567890"
    }
    
    print("\n📧 Test Mail Detayları:")
    print(f"   Alıcı: {test_data['to_email']}")
    print(f"   Kredi Miktarı: {test_data['credit_amount']} kredi")
    print(f"   Ödenen Tutar: {test_data['price']} TL")
    print(f"   Ödeme ID: {test_data['payment_id']}")
    
    print("\n" + "-" * 70)
    print("📡 Mail gönderiliyor...\n")
    
    try:
        # Email service'i kullanarak mail gönder
        result = email_service.send_credit_purchase_notification_smtp(
            to_email=test_data['to_email'],
            credit_amount=test_data['credit_amount'],
            price=test_data['price'],
            payment_id=test_data['payment_id']
        )
        
        print("\n" + "=" * 70)
        
        if result:
            print("✅ BAŞARILI! MAİL GÖNDERİLDİ")
            print("=" * 70)
            print("\n✉️  İşlem Sonucu: BAŞARILI")
            print(f"📬 Alıcı: {test_data['to_email']}")
            print(f"📧 Gönderen: no-reply@mevzuatgpt.org")
            print(f"📝 Konu: ✅ Kredi Yükleme İşleminiz Tamamlandı")
            print("\n💡 Lütfen email hesabınızı kontrol edin!")
            print("   (Spam klasörünü de kontrol etmeyi unutmayın)\n")
            return True
            
        else:
            print("❌ BAŞARISIZ! MAİL GÖNDERİLEMEDİ")
            print("=" * 70)
            print("\n⚠️  İşlem Sonucu: BAŞARISIZ")
            print("\n🔍 Olası Sorunlar:")
            print("   1. SMTP_PASSWORD hatalı olabilir")
            print("   2. Hostinger'da SMTP authentication kapalı olabilir")
            print("   3. Port ayarı yanlış olabilir (587 veya 465)")
            print("   4. Internet bağlantısı sorunlu olabilir")
            print("   5. Email hesabı kilitli olabilir\n")
            return False
            
    except Exception as e:
        print("❌ HATA! BEKLENMEDİK BİR SORUN OLUŞTU")
        print("=" * 70)
        print(f"\n⚠️  İşlem Sonucu: HATA")
        print(f"\n🔴 Hata Mesajı: {str(e)}")
        print("\n📋 Detaylı Hata:")
        import traceback
        traceback.print_exc()
        print()
        return False


if __name__ == "__main__":
    success = test_credit_purchase_email()
    
    print("=" * 70)
    if success:
        print("🎉 TEST SONUCU: BAŞARILI")
        print("=" * 70)
        print("\nMail sistemi düzgün çalışıyor! ✅\n")
        exit(0)
    else:
        print("⛔ TEST SONUCU: BAŞARISIZ")
        print("=" * 70)
        print("\nMail sistemi çalışmıyor. Lütfen ayarları kontrol edin. ❌\n")
        exit(1)
