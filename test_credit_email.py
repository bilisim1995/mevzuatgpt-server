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
    
    print("=" * 70)
    print("SMTP Kredi Yükleme Mail Testi")
    print("=" * 70)
    print()
    
    # Test verileri
    test_data = {
        "to_email": "bozkurt.bilisim@hotmail.com",
        "credit_amount": 100,
        "price": "49.90",
        "payment_id": "TEST-" + "1234567890"
    }
    
    print("📧 Test Mail Detayları:")
    print(f"   Alıcı: {test_data['to_email']}")
    print(f"   Kredi Miktarı: {test_data['credit_amount']} kredi")
    print(f"   Ödenen Tutar: {test_data['price']} TL")
    print(f"   Ödeme ID: {test_data['payment_id']}")
    print()
    
    print("📡 Mail gönderiliyor...")
    print("-" * 70)
    
    try:
        # Email service'i kullanarak mail gönder
        result = email_service.send_credit_purchase_notification_smtp(
            to_email=test_data['to_email'],
            credit_amount=test_data['credit_amount'],
            price=test_data['price'],
            payment_id=test_data['payment_id']
        )
        
        print()
        if result:
            print("=" * 70)
            print("✅ BAŞARILI! Mail gönderildi.")
            print("=" * 70)
            print()
            print("📬 Kontrol Listesi:")
            print(f"   1. {test_data['to_email']} adresine mail geldi mi?")
            print("   2. Mail içeriği düzgün görünüyor mu?")
            print("   3. Gönderen adresi: no-reply@mevzuatgpt.org")
            print("   4. Konu: ✅ Kredi Yükleme İşleminiz Tamamlandı")
            print()
            print("💡 Email klasörünüzü ve spam kutunuzu kontrol edin!")
            print()
            return True
        else:
            print("=" * 70)
            print("❌ BAŞARISIZ! Mail gönderilemedi.")
            print("=" * 70)
            print()
            print("🔍 Olası Sorunlar:")
            print("   1. SMTP_PASSWORD secret doğru mu?")
            print("   2. Hostinger hesabında SMTP authentication açık mı?")
            print("   3. Port ayarı doğru mu? (587 veya 465)")
            print("   4. Internet bağlantısı var mı?")
            print()
            return False
            
    except Exception as e:
        print("=" * 70)
        print("❌ HATA! Beklenmeyen bir sorun oluştu.")
        print("=" * 70)
        print(f"Hata: {str(e)}")
        print()
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print()
    success = test_credit_purchase_email()
    print()
    
    if success:
        print("🎉 Test tamamlandı! Mail sistemi çalışıyor.")
        exit(0)
    else:
        print("⚠️  Test başarısız oldu. Lütfen ayarları kontrol edin.")
        exit(1)
