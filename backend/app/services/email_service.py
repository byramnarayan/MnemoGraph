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


async def send_onboarding_welcome_email(
    to_email: str,
    full_name: str,
    temp_password: str,
    role: str = "Member",
    clearance_level: str = "Internal",
) -> None:
    """
    Dispatches institutional onboarding email with login credentials and clearance level
    to newly provisioned discovered personnel.
    """
    login_url = f"{settings.frontend_url}/login"

    message = MIMEMultipart("alternative")
    message["Subject"] = f"Welcome to MnemoGraph - Your Account Credentials ({role})"
    message["From"] = settings.mail_from
    message["To"] = to_email

    text_content = f"""
Hello {full_name},

Your institutional account on MnemoGraph has been provisioned and synchronized with the knowledge graph.

Here are your account access credentials:
- Platform URL: {login_url}
- Login Email: {to_email}
- Temporary Password: {temp_password}
- Assigned Role: {role}
- Security Clearance: {clearance_level}

Please log in at your earliest convenience and update your password under your Profile settings.

Welcome aboard,
The Institutional Intelligence Administration
"""

    html_content = f"""
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 28px; background-color: #0f172a; color: #f8fafc; border: 1px solid #334155; border-radius: 12px;">
    <div style="border-bottom: 1px solid #334155; padding-bottom: 16px; margin-bottom: 24px;">
        <h2 style="margin: 0; color: #38bdf8; font-size: 20px; font-weight: 700; letter-spacing: -0.5px;">MnemoGraph Platform</h2>
        <p style="margin: 4px 0 0; color: #94a3b8; font-size: 13px;">Enterprise Knowledge Graph & Operational Memory</p>
    </div>
    
    <h3 style="color: #f1f5f9; font-size: 16px; margin-top: 0;">Welcome, {full_name}</h3>
    <p style="color: #cbd5e1; font-size: 14px; line-height: 1.5;">
        Your identity has been authenticated from ingested institutional records, and your platform account has been successfully provisioned.
    </p>

    <div style="background-color: #1e293b; border: 1px solid #475569; border-radius: 8px; padding: 18px; margin: 20px 0;">
        <h4 style="margin: 0 0 12px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; color: #38bdf8;">Your Login Credentials</h4>
        <table style="width: 100%; font-size: 13px; color: #e2e8f0; border-collapse: collapse;">
            <tr>
                <td style="padding: 6px 0; color: #94a3b8; width: 140px;">Login Email:</td>
                <td style="padding: 6px 0; font-family: monospace; font-weight: 600; color: #f8fafc;">{to_email}</td>
            </tr>
            <tr>
                <td style="padding: 6px 0; color: #94a3b8;">Temporary Password:</td>
                <td style="padding: 6px 0; font-family: monospace; font-weight: 600; color: #38bdf8;">{temp_password}</td>
            </tr>
            <tr>
                <td style="padding: 6px 0; color: #94a3b8;">Assigned Role:</td>
                <td style="padding: 6px 0; font-weight: 500;">{role}</td>
            </tr>
            <tr>
                <td style="padding: 6px 0; color: #94a3b8;">Clearance Level:</td>
                <td style="padding: 6px 0; font-weight: 500; color: #a78bfa;">{clearance_level}</td>
            </tr>
        </table>
    </div>

    <div style="margin: 28px 0; text-align: center;">
        <a href="{login_url}" style="background-color: #0284c7; color: #ffffff; padding: 12px 28px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 14px; display: inline-block;">Log In to MnemoGraph</a>
    </div>

    <p style="color: #64748b; font-size: 12px; line-height: 1.5; margin-top: 24px; border-top: 1px solid #334155; padding-top: 16px;">
        For security compliance, please change your temporary password immediately upon your first sign in. If you did not expect this invitation, please notify your system administrator.
    </p>
</div>
"""
    message.attach(MIMEText(text_content, "plain"))
    message.attach(MIMEText(html_content, "html"))

    print(f"[Email Notification] Dispatching onboarding welcome email to {to_email} with role={role}, clearance={clearance_level}")

    try:
        pw = settings.mail_password.get_secret_value() if hasattr(settings.mail_password, "get_secret_value") else str(settings.mail_password)
        if settings.mail_username and pw:
            await aiosmtplib.send(
                message,
                hostname=settings.mail_server,
                port=settings.mail_port,
                username=settings.mail_username,
                password=pw,
                start_tls=settings.mail_use_tls,
            )
            print(f"[Email Notification] Successfully sent onboarding email to {to_email} via SMTP {settings.mail_server}")
        else:
            print(f"[Email Notification] SMTP credentials not configured. Email logged to console: to={to_email}, temp_pw={temp_password}")
    except Exception as e:
        print(f"[Email Error] Could not send onboarding email to {to_email}: {e}")


