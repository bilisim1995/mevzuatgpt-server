"""
Email Service for MevzuatGPT
Handles password reset and other email notifications using SendGrid
"""

import os
import logging
from typing import Optional
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.api_key = os.getenv('SENDGRID_API_KEY')
        if not self.api_key:
            logger.error("SENDGRID_API_KEY environment variable not set")
            raise ValueError("SendGrid API key is required")
        
        self.sg = SendGridAPIClient(self.api_key)
        self.from_email = "noreply@mevzuatgpt.org"
        self.from_name = "MevzuatGPT"
    
    async def send_password_reset_email(
        self, 
        to_email: str, 
        reset_token: str, 
        user_name: str = None
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
        user_name: str = None
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

# Global email service instance
email_service = EmailService()