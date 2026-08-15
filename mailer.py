import os, ssl, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from itsdangerous import URLSafeTimedSerializer
from flask import current_app


def _secret():
    return os.environ.get("SECRET_KEY", "dev-secret")


def generate_reset_token(value: str) -> str:
    s = URLSafeTimedSerializer(_secret())
    return s.dumps(value, salt="veridict-token")


def verify_reset_token(token: str, max_age_seconds: int = 3600) -> str | None:
    s = URLSafeTimedSerializer(_secret())
    try:
        return s.loads(token, salt="veridict-token", max_age=max_age_seconds)
    except Exception:
        return None


def _send(to_email: str, subject: str, html: str, text: str) -> bool:
    server   = os.environ.get("MAIL_SERVER", "")
    username = os.environ.get("MAIL_USERNAME", "")
    password = os.environ.get("MAIL_PASSWORD", "")
    from_    = os.environ.get("MAIL_FROM", username or "noreply@veridict.com")
    port     = int(os.environ.get("MAIL_PORT", 587))

    if not server:
        current_app.logger.warning("MAIL_SERVER not set. Email to %s:\n%s", to_email, text)
        return True

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = from_
    msg["To"]      = to_email
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(server, port) as s:
            s.ehlo(); s.starttls(context=ctx); s.login(username, password)
            s.sendmail(from_, to_email, msg.as_string())
        return True
    except Exception as e:
        current_app.logger.error("Email failed for %s: %s", to_email, e)
        return False


def _html_wrapper(name: str, heading: str, body_html: str) -> str:
    return f"""<html><body style="margin:0;padding:0;background:#08080f;font-family:Inter,sans-serif;color:#eeeef4">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:40px 20px">
<table width="520" cellpadding="0" cellspacing="0" style="background:#0d0d18;border:1px solid rgba(255,255,255,0.1);border-radius:16px;overflow:hidden">
  <tr><td style="padding:28px 36px 22px;border-bottom:1px solid rgba(255,255,255,0.07)">
    <span style="font-family:Space Grotesk,sans-serif;font-size:1.1rem;font-weight:700;color:#eeeef4">VERIDICT</span>
    <span style="color:#e0ac4a;margin-left:2px">·</span>
    <span style="font-size:0.72rem;color:#8a8faa;margin-left:4px">Know before you click.</span>
  </td></tr>
  <tr><td style="padding:32px 36px">
    <h1 style="font-family:Space Grotesk,sans-serif;font-size:1.25rem;font-weight:600;margin:0 0 12px;color:#eeeef4">{heading}</h1>
    {body_html}
    <p style="color:#44485e;font-size:0.72rem;margin:28px 0 0;line-height:1.6">
      If you didn't request this, you can safely ignore this email.<br/>
      Jyram Labs · Jay'stech · Nigeria
    </p>
  </td></tr>
</table></td></tr></table></body></html>"""


def send_password_reset_email(to_email: str, reset_url: str, name: str = "") -> bool:
    n = name or to_email.split("@")[0]
    body = f"""<p style="color:#8a8faa;font-size:0.9rem;line-height:1.6;margin:0 0 24px">
Hi {n}, click the button below to reset your Veridict password. This link expires in 1 hour.
</p>
<a href="{reset_url}" style="display:inline-block;padding:12px 24px;background:linear-gradient(135deg,#a97821,#c9932e);color:#fff;text-decoration:none;border-radius:8px;font-weight:600;font-size:0.9rem">Reset my password</a>"""
    html = _html_wrapper(n, "Reset your password", body)
    text = f"Hi {n},\n\nReset your Veridict password:\n{reset_url}\n\nExpires in 1 hour."
    return _send(to_email, "Reset your Veridict password", html, text)


def send_verification_email(to_email: str, verify_url: str, name: str = "") -> bool:
    n = name or to_email.split("@")[0]
    body = f"""<p style="color:#8a8faa;font-size:0.9rem;line-height:1.6;margin:0 0 24px">
Hi {n}, verify your Veridict email address to complete registration. This link expires in 24 hours.
</p>
<a href="{verify_url}" style="display:inline-block;padding:12px 24px;background:linear-gradient(135deg,#a97821,#c9932e);color:#fff;text-decoration:none;border-radius:8px;font-weight:600;font-size:0.9rem">Verify email address</a>"""
    html = _html_wrapper(n, "Verify your email", body)
    text = f"Hi {n},\n\nVerify your Veridict email:\n{verify_url}\n\nExpires in 24 hours."
    return _send(to_email, "Verify your Veridict email", html, text)