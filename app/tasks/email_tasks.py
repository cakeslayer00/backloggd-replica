import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import hashlib
import time
from app.core.celery_app import celery_app
from app.core.config import settings


def send_email(to_email: str, subject: str, body: str, html_body: str | None = None):
    if not settings.SMTP_ENABLED:
        print(f"[EMAIL] SMTP disabled - would have sent to {to_email}: {subject}")
        print(f"[EMAIL] Body preview: {body[:100]}...")
        return True

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM_EMAIL
    msg["To"] = to_email

    text_part = MIMEText(body, "plain")
    msg.attach(text_part)

    if html_body:
        html_part = MIMEText(html_body, "html")
        msg.attach(html_part)

    print(f"[EMAIL] Sending to {to_email}: {subject}")

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, [to_email], msg.as_string())
        print(f"[EMAIL] Successfully sent to {to_email}")
        return True
    except Exception as e:
        print(f"[EMAIL] Failed to send to {to_email}: {e}")
        return False


def send_email_with_attachment(
    to_email: str, subject: str, body: str, filename: str, content: str
):
    if not settings.SMTP_ENABLED:
        print(f"[EMAIL] SMTP disabled - would have sent to {to_email}: {subject}")
        print(f"[EMAIL] Attachment: {filename} ({len(content)} bytes)")
        return True

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM_EMAIL
    msg["To"] = to_email

    body_part = MIMEText(body, "plain")
    msg.attach(body_part)

    part = MIMEBase("application", "octet-stream")
    part.set_payload(content.encode("utf-8"))
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
    msg.attach(part)

    print(f"[EMAIL] Sending with attachment to {to_email}: {subject}")

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, [to_email], msg.as_string())
        print(f"[EMAIL] Successfully sent with attachment to {to_email}")
        return True
    except Exception as e:
        print(f"[EMAIL] Failed to send to {to_email}: {e}")
        return False


@celery_app.task(bind=True, max_retries=3)
def send_confirmation_email(self, user_id: int, email: str, username: str):
    import asyncio
    from app.core.redis import store_confirmation_token

    token = hashlib.sha256(f"{email}{time.time()}".encode()).hexdigest()[:32]

    asyncio.run(store_confirmation_token(token, user_id, email))

    confirmation_link = f"http://localhost:3000/confirm/{token}"

    subject = "Confirm your BacklogGD account"
    body = f"""Hi {username},

Please confirm your email address.

TO CONFIRM YOUR EMAIL, RUN THIS COMMAND:
curl -X POST "http://localhost:8000/api/auth/confirm-email?token={token}"

"""
    html_body = f"""
<html>
<body>
<h2>Hi {username},</h2>
<p>Please confirm your email address:)</p>

<h3>To confirm your email, run this command:</h3>
<pre style="background:#f4f4f4;padding:15px;border-radius:5px;">
curl -X POST "http://localhost:8000/api/auth/confirm-email?token={token}"
</pre>

</body>
</html>
"""
    success = send_email(email, subject, body, html_body)
    if not success:
        raise self.retry(exc=Exception("Email send failed"))
    return {"user_id": user_id, "email": email, "token": token}


@celery_app.task(bind=True, max_retries=3)
def send_password_reset_email(self, user_id: int, email: str, username: str):
    import asyncio
    from app.core.redis import store_reset_token

    token = hashlib.sha256(f"reset{email}{time.time()}".encode()).hexdigest()[:32]

    asyncio.run(store_reset_token(token, user_id))

    reset_link = f"http://localhost:3000/reset-password/{token}"

    subject = "Reset your BacklogGD password"
    body = f"""Hi {username},

We received a request to reset your password.

TO RESET YOUR PASSWORD, RUN THIS COMMAND:
curl -X POST "http://localhost:8000/api/auth/reset-password" \\
  -H "Content-Type: application/json" \\
  -d '{{"token":"{token}","new_password":"your_new_password"}}'

"""
    html_body = f"""
<html>
<body>
<h2>Hi {username},</h2>
<p>We received a request to reset your password.</p>

<h3>To reset your password, run this command:</h3>
<pre style="background:#f4f4f4;padding:15px;border-radius:5px;">
curl -X POST "http://localhost:8000/api/auth/reset-password" \\
  -H "Content-Type: application/json" \\
  -d '{{"token":"{token}","new_password":"your_new_password"}}'
</pre>

</body>
</html>
"""
    success = send_email(email, subject, body, html_body)
    if not success:
        raise self.retry(exc=Exception("Email send failed"))
    return {"user_id": user_id, "email": email, "token": token}
