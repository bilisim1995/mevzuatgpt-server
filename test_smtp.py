#!/usr/bin/env python3
"""
SMTP bağlantı testi
Test maili gönderir: bozkurt.bilisim@hotmail.com
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def test_smtp_connection():
    """SMTP bağlantısını test et ve mail gönder"""
    
    # Environment variables'dan SMTP ayarlarını al
    smtp_host = os.getenv('SMTP_HOST', 'smtp.hostinger.com')
    smtp_port = int(os.getenv('SMTP_PORT', '465'))
    smtp_user = os.getenv('SMTP_USER', 'no-reply@mevzuatgpt.org')
    smtp_password = os.getenv('SMTP_PASSWORD')
    
    print("=" * 60)
    print("SMTP Bağlantı Testi")
    print("=" * 60)
    print(f"SMTP Host: {smtp_host}")
    print(f"SMTP Port: {smtp_port}")
    print(f"SMTP User: {smtp_user}")
    print(f"SMTP Password: {'*' * len(smtp_password) if smtp_password else 'NOT SET'}")
    print("=" * 60)
    
    if not smtp_password:
        print("❌ HATA: SMTP_PASSWORD environment variable tanımlanmamış!")
        return False
    
    try:
        # Test maili hazırla
        test_email = "bozkurt.bilisim@hotmail.com"
        
        message = MIMEMultipart("alternative")
        message["Subject"] = "MevzuatGPT - SMTP Test Maili"
        message["From"] = smtp_user
        message["To"] = test_email
        
        # HTML içerik
        html_content = """
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
              <h2 style="color: #2c3e50;">🎉 SMTP Test Başarılı!</h2>
              <p>Merhaba,</p>
              <p>Bu mail, MevzuatGPT sisteminin SMTP bağlantısının başarıyla çalıştığını doğrulamak için gönderilmiştir.</p>
              
              <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #28a745; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #28a745;">✅ Bağlantı Ayarları</h3>
                <ul style="list-style: none; padding-left: 0;">
                  <li>📧 <strong>SMTP Sunucu:</strong> smtp.hostinger.com</li>
                  <li>🔒 <strong>Port:</strong> 465 (SSL)</li>
                  <li>👤 <strong>Gönderen:</strong> no-reply@mevzuatgpt.org</li>
                </ul>
              </div>
              
              <p>Artık kredi yükleme işlemlerinde otomatik mail bildirimleri gönderebiliriz!</p>
              
              <hr style="border: none; border-top: 1px solid #e1e4e8; margin: 30px 0;">
              
              <p style="font-size: 12px; color: #6c757d;">
                Bu bir test mailidir. MevzuatGPT mail sistemi başarıyla yapılandırılmıştır.
              </p>
            </div>
          </body>
        </html>
        """
        
        # Plain text alternatifi
        text_content = """
        SMTP Test Başarılı!
        
        Bu mail, MevzuatGPT sisteminin SMTP bağlantısının başarıyla çalıştığını doğrulamak için gönderilmiştir.
        
        Bağlantı Ayarları:
        - SMTP Sunucu: smtp.hostinger.com
        - Port: 465 (SSL)
        - Gönderen: no-reply@mevzuatgpt.org
        
        Artık kredi yükleme işlemlerinde otomatik mail bildirimleri gönderebiliriz!
        """
        
        part1 = MIMEText(text_content, "plain")
        part2 = MIMEText(html_content, "html")
        
        message.attach(part1)
        message.attach(part2)
        
        # SMTP bağlantısı kur (SSL)
        print("\n📡 SMTP sunucusuna bağlanılıyor...")
        server = smtplib.SMTP_SSL(smtp_host, smtp_port)
        
        print("🔐 Kimlik doğrulaması yapılıyor...")
        server.login(smtp_user, smtp_password)
        
        print(f"📧 Test maili gönderiliyor: {test_email}")
        server.send_message(message)
        
        server.quit()
        
        print("\n" + "=" * 60)
        print("✅ BAŞARILI! Test maili gönderildi.")
        print(f"📬 Alıcı: {test_email}")
        print("=" * 60)
        
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"\n❌ Kimlik doğrulama hatası: {e}")
        print("Kullanıcı adı veya şifre hatalı olabilir.")
        return False
        
    except smtplib.SMTPException as e:
        print(f"\n❌ SMTP Hatası: {e}")
        return False
        
    except Exception as e:
        print(f"\n❌ Beklenmeyen hata: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_smtp_connection()
    exit(0 if success else 1)
