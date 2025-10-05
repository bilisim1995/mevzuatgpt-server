"""
Email Service for MevzuatGPT
Handles password reset and other email notifications using SendGrid and SMTP
"""

import os
import logging
import smtplib
from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        # SendGrid config (for password reset)
        self.api_key = os.getenv('SENDGRID_API_KEY')
        if self.api_key:
            self.sg = SendGridAPIClient(self.api_key)
        else:
            logger.warning("SENDGRID_API_KEY not set, SendGrid features disabled")
            self.sg = None
        
        # SMTP config (for credit notifications) - .env'den okunur
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.hostinger.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '465'))
        self.smtp_user = os.getenv('SMTP_USER', 'info@mevzuatgpt.org')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.smtp_sender = os.getenv('SMTP_SENDER', 'no-reply@mevzuatgpt.org')
        
        # SendGrid gönderici adresi
        self.from_email = "noreply@mevzuatgpt.org"
        self.from_name = "MevzuatGPT"
    
    async def send_password_reset_email(
        self, 
        to_email: str, 
        reset_token: str, 
        user_name: Optional[str] = None
    ) -> bool:
        """
        Send password reset email with reset link
        
        Args:
            to_email: Recipient email address
            reset_token: Password reset token
            user_name: User's name for personalization
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Create reset URL - in production this would be your frontend URL
            reset_url = f"https://mevzuatgpt.com/reset-password?token={reset_token}"
            
            # Email subject
            subject = "MevzuatGPT - Şifre Sıfırlama"
            
            # HTML content
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Şifre Sıfırlama</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #2563eb; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; background-color: #f9f9f9; }}
                    .button {{ 
                        display: inline-block; 
                        background-color: #2563eb; 
                        color: white; 
                        padding: 12px 24px; 
                        text-decoration: none; 
                        border-radius: 4px; 
                        margin: 20px 0;
                    }}
                    .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>MevzuatGPT</h1>
                    </div>
                    <div class="content">
                        <h2>Şifre Sıfırlama Talebi</h2>
                        <p>Merhaba{f" {user_name}" if user_name else ""},</p>
                        <p>MevzuatGPT hesabınız için şifre sıfırlama talebinde bulundunuz.</p>
                        <p>Şifrenizi sıfırlamak için aşağıdaki butona tıklayın:</p>
                        <p style="text-align: center;">
                            <a href="{reset_url}" class="button">Şifremi Sıfırla</a>
                        </p>
                        <p><strong>Önemli:</strong> Bu link 24 saat geçerlidir. Eğer şifre sıfırlama talebinde bulunmadıysanız, bu e-postayı dikkate almayın.</p>
                        <p>Link çalışmıyorsa, aşağıdaki URL'yi tarayıcınıza kopyalayın:</p>
                        <p style="word-break: break-all; font-size: 12px; color: #666;">{reset_url}</p>
                    </div>
                    <div class="footer">
                        <p>Bu e-posta MevzuatGPT tarafından otomatik olarak gönderilmiştir.</p>
                        <p>Sorularınız için: destek@mevzuatgpt.com</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Plain text fallback
            text_content = f"""
            MevzuatGPT - Şifre Sıfırlama
            
            Merhaba{f" {user_name}" if user_name else ""},
            
            MevzuatGPT hesabınız için şifre sıfırlama talebinde bulundunuz.
            
            Şifrenizi sıfırlamak için aşağıdaki linke tıklayın:
            {reset_url}
            
            Bu link 24 saat geçerlidir. Eğer şifre sıfırlama talebinde bulunmadıysanız, bu e-postayı dikkate almayın.
            
            MevzuatGPT Destek Ekibi
            """
            
            # Create email message
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email),
                subject=subject
            )
            message.content = [
                Content("text/plain", text_content),
                Content("text/html", html_content)
            ]
            
            # Send email
            if not self.sg:
                logger.error("SendGrid client not initialized")
                return False
            
            response = self.sg.send(message)
            
            if response.status_code in [200, 202]:
                logger.info(f"Password reset email sent successfully to {to_email}")
                return True
            else:
                logger.error(f"Failed to send password reset email. Status: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending password reset email to {to_email}: {str(e)}")
            return False
    
    async def send_password_changed_notification(
        self, 
        to_email: str, 
        user_name: Optional[str] = None
    ) -> bool:
        """
        Send notification when password is successfully changed
        
        Args:
            to_email: Recipient email address
            user_name: User's name for personalization
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            subject = "MevzuatGPT - Şifreniz Değiştirildi"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Şifre Değiştirildi</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #16a34a; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; background-color: #f9f9f9; }}
                    .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>MevzuatGPT</h1>
                    </div>
                    <div class="content">
                        <h2>Şifreniz Başarıyla Değiştirildi</h2>
                        <p>Merhaba{f" {user_name}" if user_name else ""},</p>
                        <p>MevzuatGPT hesabınızın şifresi başarıyla değiştirildi.</p>
                        <p>Eğer bu değişikliği siz yapmadıysanız, lütfen derhal bizimle iletişime geçin.</p>
                        <p>Güvenliğiniz için:</p>
                        <ul>
                            <li>Güçlü ve benzersiz şifreler kullanın</li>
                            <li>Şifrenizi kimseyle paylaşmayın</li>
                            <li>Düzenli olarak şifrenizi değiştirin</li>
                        </ul>
                    </div>
                    <div class="footer">
                        <p>Bu e-posta MevzuatGPT tarafından otomatik olarak gönderilmiştir.</p>
                        <p>Sorularınız için: destek@mevzuatgpt.com</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
            MevzuatGPT - Şifreniz Değiştirildi
            
            Merhaba{f" {user_name}" if user_name else ""},
            
            MevzuatGPT hesabınızın şifresi başarıyla değiştirildi.
            
            Eğer bu değişikliği siz yapmadıysanız, lütfen derhal bizimle iletişime geçin.
            
            MevzuatGPT Destek Ekibi
            """
            
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email),
                subject=subject
            )
            message.content = [
                Content("text/plain", text_content),
                Content("text/html", html_content)
            ]
            
            if not self.sg:
                logger.error("SendGrid client not initialized")
                return False
            
            response = self.sg.send(message)
            
            if response.status_code in [200, 202]:
                logger.info(f"Password changed notification sent successfully to {to_email}")
                return True
            else:
                logger.error(f"Failed to send password changed notification. Status: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending password changed notification to {to_email}: {str(e)}")
            return False
    
    def send_credit_purchase_notification_smtp(
        self,
        to_email: str,
        credit_amount: int,
        price: str,
        payment_id: str
    ) -> bool:
        """
        Kredi satın alma bildirimi gönder (SMTP)
        Port 587 (TLS) ve 465 (SSL) destekli
        
        Args:
            to_email: Kullanıcı email adresi
            credit_amount: Satın alınan kredi miktarı
            price: Ödenen tutar
            payment_id: Ödeme ID
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.smtp_password:
                logger.error("SMTP password not configured")
                return False
            
            subject = "🎉 Ödemeniz Başarıyla Alındı!"
            
            html_content = f"""
            <!DOCTYPE html>
            <html lang="tr">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background-color: #f4f4f4;
                        margin: 0;
                        padding: 0;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 30px auto;
                        background: white;
                        border-radius: 10px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                        overflow: hidden;
                    }}
                    h1 {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        text-align: center;
                        padding: 30px 20px;
                        margin: 0;
                        font-size: 28px;
                    }}
                    .slogan {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: #f0f0f0;
                        text-align: center;
                        padding: 0 20px 20px 20px;
                        margin: 0;
                        font-size: 14px;
                        font-style: italic;
                    }}
                    .container p {{
                        color: #333;
                        line-height: 1.6;
                        padding: 0 30px;
                    }}
                    .details-box {{
                        background-color: #f8f9fa;
                        margin: 25px 30px;
                        padding: 20px;
                        border-left: 4px solid #28a745;
                        border-radius: 5px;
                    }}
                    .details-box h3 {{
                        margin-top: 0;
                        color: #28a745;
                        font-size: 18px;
                    }}
                    .details-box ul {{
                        list-style: none;
                        padding: 0;
                        margin: 10px 0 0 0;
                    }}
                    .details-box li {{
                        padding: 8px 0;
                        border-bottom: 1px solid #e1e4e8;
                    }}
                    .details-box li:last-child {{
                        border-bottom: none;
                    }}
                    .button {{
                        display: inline-block;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: 15px 40px;
                        text-decoration: none;
                        border-radius: 5px;
                        font-weight: bold;
                        margin: 20px 0;
                    }}
                    .footer {{
                        background-color: #f8f9fa;
                        text-align: center;
                        padding: 20px;
                        margin-top: 30px;
                        border-top: 1px solid #e1e4e8;
                    }}
                    .footer p {{
                        margin: 5px 0;
                        padding: 0;
                        font-size: 13px;
                        color: #6c757d;
                    }}
                    .footer a {{
                        color: #667eea;
                        text-decoration: none;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🎉 Ödemeniz Başarıyla Alındı!</h1>
                    <p class="slogan">Türkiye'nin en büyük yapay zeka destekli mevzuat asistanı.</p>
                    <p>Merhaba,</p>
                    <p><b>MevzuatGPT</b> hesabınıza yeni kredileriniz başarıyla eklendi. Artık mevzuatın karmaşık dünyasında yapay zeka desteğiyle daha hızlı ve verimli çalışmaya devam edebilirsiniz.</p>
                    
                    <div class="details-box">
                        <h3>İşlem Detayları:</h3>
                        <ul>
                            <li><b>Yüklenen Kredi:</b> {credit_amount} Kredi</li>
                            <li><b>Ödenen Tutar:</b> {price} TL</li>
                            <li><b>Ödeme Referans No:</b> {payment_id}</li>
                        </ul>
                    </div>

                    <p>Hemen şimdi yeni kredilerinizle mevzuatın derinliklerine dalmaya başlamak için:</p>
                    <p style="text-align: center;">
                        <a href="https://mevzuatgpt.org" class="button" style="color: #ffffff;">MevzuatGPT'ye Git</a>
                    </p>
                    
                    <div class="footer">
                        <p>MevzuatGPT'yi tercih ettiğiniz için teşekkür ederiz.</p>
                        <p><strong>MevzuatGPT Ekibi</strong></p>
                        <p><a href="https://mevzuatgpt.org">mevzuatgpt.org</a></p>
                        <p><small>Bu otomatik bir bildirimdir, lütfen bu e-postayı yanıtlamayınız.</small></p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
🎉 Ödemeniz Başarıyla Alındı!

Türkiye'nin en büyük yapay zeka destekli mevzuat asistanı.

Merhaba,

MevzuatGPT hesabınıza yeni kredileriniz başarıyla eklendi. Artık mevzuatın karmaşık dünyasında yapay zeka desteğiyle daha hızlı ve verimli çalışmaya devam edebilirsiniz.

İşlem Detayları:
- Yüklenen Kredi: {credit_amount} Kredi
- Ödenen Tutar: {price} TL
- Ödeme Referans No: {payment_id}

Hemen şimdi yeni kredilerinizle mevzuatın derinliklerine dalmaya başlamak için:
https://mevzuatgpt.org

MevzuatGPT'yi tercih ettiğiniz için teşekkür ederiz.

MevzuatGPT Ekibi
mevzuatgpt.org

Bu otomatik bir bildirimdir, lütfen bu e-postayı yanıtlamayınız.
            """
            
            # Email mesajı oluştur
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"MevzuatGPT <{self.smtp_sender}>"
            message["To"] = to_email
            
            # Plain text ve HTML ekle
            part1 = MIMEText(text_content, "plain")
            part2 = MIMEText(html_content, "html")
            message.attach(part1)
            message.attach(part2)
            
            # SMTP bağlantısı kur - Port 587 (TLS) veya 465 (SSL)
            logger.info(f"Sending credit notification email to {to_email}")
            
            if self.smtp_port == 587:
                # Port 587 - TLS/STARTTLS (Hostinger önerisi)
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
            else:
                # Port 465 - SSL (varsayılan)
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
            
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(message)
            server.quit()
            
            logger.info(f"Credit notification email sent successfully to {to_email} (Port: {self.smtp_port})")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return False
            
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to send credit notification email: {e}")
            return False

# Global email service instance
email_service = EmailService()