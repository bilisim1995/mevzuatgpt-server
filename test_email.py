import asyncio
import sys
sys.path.append('.')

from services.email_service import EmailService

async def test_email():
    try:
        email_service = EmailService()
        result = await email_service.send_password_reset_email(
            to_email="bozkurt.bilisim@hotmail.com",
            reset_token="TEST_TOKEN_123456",
            user_name="Test User"
        )
        print(f"Email gönderim sonucu: {result}")
        return result
    except Exception as e:
        print(f"Email gönderim hatası: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_email())
    print(f"Final result: {result}")
