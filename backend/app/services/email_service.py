from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.core.config import settings


async def send_password_reset_email(to_email: str, reset_token: str) -> None:
    reset_url = f"{settings.frontend_url}/reset-password?token={reset_token}"

    message = MIMEMultipart("alternative")
    message["Subject"] = "Password Reset Request"
    message["From"] = settings.mail_from
    message["To"] = to_email

    text_content = f"""
Hello,

You requested a password reset. Please click the link below to set a new password:
{reset_url}

If you did not make this request, you can safely ignore this email.
"""
    html_content = f"""
<div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 4px;">
    <h2 style="color: #111;">Password Reset Request</h2>
    <p>You recently requested to reset your password. Click the button below to proceed:</p>
    <div style="margin: 24px 0;">
        <a href="{reset_url}" style="background-color: #0ea5e9; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; font-weight: 500; display: inline-block;">Reset Password</a>
    </div>
    <p style="color: #666; font-size: 13px;">Or copy and paste this link in your browser:<br/><a href="{reset_url}">{reset_url}</a></p>
    <p style="color: #999; font-size: 12px; margin-top: 30px;">If you didn't request this, you can safely ignore this message.</p>
</div>
"""
    message.attach(MIMEText(text_content, "plain"))
    message.attach(MIMEText(html_content, "html"))

    try:
        if settings.mail_username and settings.mail_password.get_secret_value():
            await aiosmtplib.send(
                message,
                hostname=settings.mail_server,
                port=settings.mail_port,
                username=settings.mail_username,
                password=settings.mail_password.get_secret_value(),
                start_tls=settings.mail_use_tls,
            )
    except Exception as e:
        # In development or if SMTP is unconfigured, log and continue gracefully
        print(f"[Email Error] Could not send password reset email: {e}")

