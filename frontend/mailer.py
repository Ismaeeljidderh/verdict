"""
mailer.py
Sends transactional emails via SMTP (no extra dependency — uses
Python's stdlib smtplib). Works with Gmail App Passwords, Outlook,
Zoho, or any other SMTP provider.

Configure in .env:
  MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM

Password reset links are signed with itsdangerous so they can't
be forged, and they expire after 1 hour.
"""

import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask import current_app


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def generate_reset_token(email: str) -> str:
    return _serializer().dumps(email, salt="password-reset")


def verify_reset_token(token: str, max_age_seconds: int = 3600):
    """Returns the email if the token is valid, None otherwise."""
    try:
        email = _serializer().loads(token, salt="password-reset", max_age=max_age_seconds)
        return email
    except (SignatureExpired, BadSignature):
        return None


def send_reset_email(to_email: str, reset_url: str) -> bool:
    """
    Sends a password reset email. Returns True on success, False on failure.
    In dev mode (MAIL_SERVER not set), prints the link to the console instead.
    """
    mail_server = os.environ.get("MAIL_SERVER", "")
    mail_username = os.environ.get("MAIL_USERNAME", "")
    mail_password = os.environ.get("MAIL_PASSWORD", "")
    mail_from = os.environ.get("MAIL_FROM", mail_username or "noreply@veridict.com")
    mail_port = int(os.environ.get("MAIL_PORT", 587))

    subject = "Reset your Veridict password"

    html_body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#05060a;font-family:'Inter',sans-serif;color:#e8e9f0;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 20px;">
      <table width="520" cellpadding="0" cellspacing="0"
             style="background:#0d0f1a;border:1px solid rgba(255,255,255,0.1);border-radius:16px;overflow:hidden;">
        <tr>
          <td style="padding:36px 36px 28px;border-bottom:1px solid rgba(255,255,255,0.08);">
            <span style="font-size:1.2rem;font-weight:700;color:#e8e9f0;letter-spacing:-0.01em;">Veridict</span>
          </td>
        </tr>
        <tr>
          <td style="padding:36px;">
            <h1 style="font-size:1.4rem;font-weight:600;margin:0 0 14px;letter-spacing:-0.01em;">Reset your password</h1>
            <p style="color:#8a8fa3;font-size:0.92rem;line-height:1.6;margin:0 0 28px;">
              Someone requested a password reset for this Veridict account.
              If that was you, click the button below. This link expires in 1 hour.
            </p>
            <a href="{reset_url}"
               style="display:inline-block;padding:13px 26px;background:linear-gradient(135deg,#7c5cfc,#4f8fff);
                      color:#fff;text-decoration:none;border-radius:8px;font-weight:600;font-size:0.92rem;">
              Reset password
            </a>
            <p style="color:#565b6e;font-size:0.76rem;margin:28px 0 0;line-height:1.6;">
              If you didn't request this, you can ignore this email — your password won't change.
              <br/>This link will expire in 1 hour.
            </p>
          </td>
        </tr>
        <tr>
          <td style="padding:20px 36px;border-top:1px solid rgba(255,255,255,0.06);
                     color:#565b6e;font-size:0.72rem;">
            Jyram Labs — Decode. Defend. Discover.
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""

    text_body = f"Reset your Veridict password by visiting this link (expires in 1 hour):\n\n{reset_url}\n\nIf you didn't request this, ignore this email."

    if not mail_server:
        # Dev fallback — print to console
        current_app.logger.warning(
            "MAIL_SERVER not configured. Password reset link for %s:\n%s",
            to_email,
            reset_url,
        )
        return True

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(mail_server, mail_port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(mail_username, mail_password)
            server.sendmail(mail_from, to_email, msg.as_string())
        return True
    except Exception as exc:
        current_app.logger.error("Failed to send reset email to %s: %s", to_email, exc)
        return False


def send_verification_email(to_email: str, verify_url: str) -> bool:
    """Sends an email verification link."""
    mail_server   = os.environ.get("MAIL_SERVER", "")
    mail_username = os.environ.get("MAIL_USERNAME", "")
    mail_password = os.environ.get("MAIL_PASSWORD", "")
    mail_from     = os.environ.get("MAIL_FROM", mail_username or "noreply@veridict.com")
    mail_port     = int(os.environ.get("MAIL_PORT", 587))

    subject = "Verify your Veridict email address"

    html_body = f"""
<!DOCTYPE html><html><head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#05060a;font-family:'Inter',sans-serif;color:#e8e9f0;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td align="center" style="padding:40px 20px;">
<table width="520" cellpadding="0" cellspacing="0"
       style="background:#0d0f1a;border:1px solid rgba(255,255,255,0.1);border-radius:16px;overflow:hidden;">
  <tr><td style="padding:36px 36px 28px;border-bottom:1px solid rgba(255,255,255,0.08);">
    <span style="font-size:1.2rem;font-weight:700;color:#e8e9f0">Veridict</span>
  </td></tr>
  <tr><td style="padding:36px;">
    <h1 style="font-size:1.4rem;font-weight:600;margin:0 0 14px">Verify your email address</h1>
    <p style="color:#8a8fa3;font-size:0.92rem;line-height:1.6;margin:0 0 28px">
      Click the button below to verify your email. This link expires in 24 hours.
    </p>
    <a href="{verify_url}" style="display:inline-block;padding:13px 26px;
       background:linear-gradient(135deg,#7c5cfc,#4f8fff);color:#fff;
       text-decoration:none;border-radius:8px;font-weight:600;font-size:0.92rem">
      Verify email address
    </a>
    <p style="color:#565b6e;font-size:0.76rem;margin:28px 0 0;line-height:1.6">
      If you didn't create a Veridict account, ignore this email.
    </p>
  </td></tr>
  <tr><td style="padding:20px 36px;border-top:1px solid rgba(255,255,255,0.06);color:#565b6e;font-size:0.72rem">
    Jyram Labs — Decode. Defend. Discover.
  </td></tr>
</table></td></tr></table>
</body></html>"""

    text_body = f"Verify your Veridict email:\n\n{verify_url}\n\nLink expires in 24 hours."

    if not mail_server:
        current_app.logger.warning("MAIL_SERVER not set. Email verify link for %s:\n%s", to_email, verify_url)
        return True

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = mail_from
    msg["To"]      = to_email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(mail_server, mail_port) as server:
            server.ehlo(); server.starttls(context=context)
            server.login(mail_username, mail_password)
            server.sendmail(mail_from, to_email, msg.as_string())
        return True
    except Exception as exc:
        current_app.logger.error("Failed to send verify email to %s: %s", to_email, exc)
        return False

def send_verification_email(to_email: str, verify_url: str, full_name: str = "") -> bool:
    """Sends an email verification link after registration."""
    mail_server   = os.environ.get("MAIL_SERVER", "")
    mail_username = os.environ.get("MAIL_USERNAME", "")
    mail_password = os.environ.get("MAIL_PASSWORD", "")
    mail_from     = os.environ.get("MAIL_FROM", mail_username or "noreply@veridict.com")
    mail_port     = int(os.environ.get("MAIL_PORT", 587))

    name    = full_name or to_email.split("@")[0]
    subject = "Verify your Veridict email"

    html_body = f"""
<html><body style="margin:0;padding:0;background:#05060a;font-family:Inter,sans-serif;color:#e8e9f0">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 20px">
      <table width="520" cellpadding="0" cellspacing="0"
             style="background:#0d0f1a;border:1px solid rgba(255,255,255,0.1);border-radius:16px;overflow:hidden">
        <tr><td style="padding:32px 36px 24px;border-bottom:1px solid rgba(255,255,255,0.08)">
          <span style="font-size:1.2rem;font-weight:700;color:#e8e9f0">Veridict</span>
        </td></tr>
        <tr><td style="padding:36px">
          <h1 style="font-size:1.3rem;font-weight:600;margin:0 0 14px">Hey {name}, verify your email</h1>
          <p style="color:#8a8fa3;font-size:0.9rem;line-height:1.6;margin:0 0 28px">
            Click the button below to verify your email address and complete your Veridict registration.
            This link expires in 24 hours.
          </p>
          <a href="{verify_url}"
             style="display:inline-block;padding:13px 26px;background:linear-gradient(135deg,#7c5cfc,#4f8fff);
                    color:#fff;text-decoration:none;border-radius:8px;font-weight:600;font-size:0.92rem">
            Verify email address
          </a>
          <p style="color:#565b6e;font-size:0.76rem;margin:28px 0 0;line-height:1.6">
            If you didn't create a Veridict account, you can safely ignore this email.
          </p>
        </td></tr>
        <tr><td style="padding:20px 36px;border-top:1px solid rgba(255,255,255,0.06);color:#565b6e;font-size:0.72rem">
          Jyram Labs — Decode. Defend. Discover.
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""

    text_body = f"Hi {name},\n\nVerify your Veridict email by visiting:\n{verify_url}\n\nLink expires in 24 hours."

    if not mail_server:
        current_app.logger.warning("MAIL_SERVER not set. Verification link for %s:\n%s", to_email, verify_url)
        return True

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = mail_from
    msg["To"]      = to_email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(mail_server, mail_port) as server:
            server.ehlo(); server.starttls(context=context)
            server.login(mail_username, mail_password)
            server.sendmail(mail_from, to_email, msg.as_string())
        return True
    except Exception as exc:
        current_app.logger.error("Verification email failed for %s: %s", to_email, exc)
        return False
