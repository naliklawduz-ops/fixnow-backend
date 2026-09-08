import smtplib
import random
import string
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")


def generate_reset_code(length: int = 6) -> str:
    """Generate a random 6-digit code."""
    return ''.join(random.choices(string.digits, k=length))


def send_reset_email(to_email: str, code: str) -> bool:
    """Send password reset code via Gmail SMTP."""
    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_USER
        msg["To"] = to_email
        msg["Subject"] = "FIX.NOW - Password Reset Code"
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #0A0A0A; color: #FFFFFF; padding: 20px;">
            <div style="max-width: 500px; margin: 0 auto; background-color: #1A1A1A; border: 1px solid #C9A84C; border-radius: 15px; padding: 30px;">
                <h1 style="color: #C9A84C; font-size: 28px;">FIX.NOW</h1>
                <p style="font-size: 16px;">Your password reset code is:</p>
                <h2 style="color: #C9A84C; font-size: 36px; letter-spacing: 5px;">{code}</h2>
                <p style="color: #888888;">This code expires in 10 minutes.</p>
                <p style="color: #888888;">If you didn't request this, please ignore this email.</p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, "html"))
        
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False