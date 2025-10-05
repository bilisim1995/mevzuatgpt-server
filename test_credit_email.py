import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class EmailService:

    def __init__(self):
        """
        Email servisi için gerekli SMTP ayarlarını doğrudan tanımlar.

        !!! UYARI: Bu yöntem GÜVENLİ DEĞİLDİR. Sadece geçici testler için kullanın.
        Hassas bilgileri kod içinde saklamak büyük bir güvenlik riskidir.
        """
        self.smtp_host = "smtp.hostinger.com"
        self.smtp_port = 465  # SSL için port 465 kullanılır
        self.smtp_user = "info@mevzuatgpt.org"
        self.smtp_password = "Ob115733+++"
        self.sender_email = "no-reply@mevzuatgpt.org"  # Gönderen adres

    def _create_credit_purchase_html(self, credit_amount, price, payment_id):
        """Kredi satın alma için HTML mail içeriği oluşturur."""
        # (Bu fonksiyonun içeriği değişmedi)
        return f"""
        <!DOCTYPE html>
        <html lang="tr">
        <head>
            <meta charset="UTF-8">
            <title>Kredi Yükleme Başarılı</title>
        </head>
        <body style="font-family: Arial, sans-serif; margin: 20px; color: #333;">
            <h2>Merhaba,</h2>
            <p><b>MevzuatGPT</b> hesabınıza başarıyla kredi yüklenmiştir.</p>
            <hr>
            <h3>İşlem Detayları:</h3>
            <ul>
                <li><b>Yüklenen Kredi:</b> {credit_amount} Kredi</li>
                <li><b>Ödenen Tutar:</b> {price} TL</li>
                <li><b>Ödeme Referans No:</b> {payment_id}</li>
            </ul>
            <hr>
            <p>MevzuatGPT'yi tercih ettiğiniz için teşekkür ederiz.</p>
            <p>Saygılarımızla,<br>MevzuatGPT Ekibi</p>
            <p><small>Bu otomatik bir bildirimdir, lütfen bu e-postayı yanıtlamayınız.</small></p>
        </body>
        </html>
        """

    def send_credit_purchase_notification_smtp(self, to_email, credit_amount,
                                               price, payment_id):
        """
        SMTP kullanarak kredi satın alma bildirim maili gönderir.
        Başarılı ve başarısız durumları konsola yazdırır.
        """
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = "✅ Kredi Yükleme İşleminiz Tamamlandı"
            msg['From'] = f"MevzuatGPT <{self.sender_email}>"
            msg['To'] = to_email

            html_body = self._create_credit_purchase_html(
                credit_amount, price, payment_id)
            msg.attach(MIMEText(html_body, 'html'))

            # --- YENİ EKLENEN KONSOL MESAJLARI ---
            print(
                f"SMTP sunucusuna bağlanılıyor: {self.smtp_host}:{self.smtp_port}"
            )

            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                print("Giriş yapılıyor...")
                server.login(self.smtp_user, self.smtp_password)

                print(f"Mail gönderiliyor -> {to_email}")
                server.sendmail(self.sender_email, to_email, msg.as_string())

                # Başarı mesajı eklendi
                print("✓ Mail başarıyla gönderildi.")

            return True

        except smtplib.SMTPAuthenticationError as e:
            # Hata durumunda konsola detaylı bilgi yazdır
            print(
                f"❌ HATA: SMTP kimlik doğrulaması başarısız! Kullanıcı adı veya şifre yanlış."
            )
            print(f"   Detay: {e}")
            return False
        except Exception as e:
            # Diğer hatalar için konsola detaylı bilgi yazdır
            print(f"❌ HATA: Mail gönderilirken beklenmedik bir sorun oluştu.")
            print(f"   Detay: {e}")
            return False


# Servisin bir örneğini oluşturup dışa aktarıyoruz
email_service = EmailService()
