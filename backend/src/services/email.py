import resend
from src.config import settings
from src.utils.logger import logger


def _client():
    resend.api_key = settings.resend_api_key


def send_verification_email(to_email: str, name: str, token: str) -> bool:
    """Send an email verification link. Returns True on success."""
    _client()
    base = settings.frontend_url.rstrip("/")
    verify_url = f"{base}/verify-email?token={token}"

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": to_email,
            "subject": "Verify your Turboman account",
            "html": f"""
            <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px 24px">
              <h2 style="margin:0 0 8px;font-size:22px;color:#0f172a">Welcome to Turboman, {name}!</h2>
              <p style="margin:0 0 24px;color:#475569;font-size:15px;line-height:1.6">
                Click the button below to verify your email and activate your account.
                This link expires in 24 hours.
              </p>
              <a href="{verify_url}"
                 style="display:inline-block;background:#2563eb;color:#fff;font-weight:600;
                        font-size:14px;padding:12px 24px;border-radius:8px;text-decoration:none">
                Verify my email
              </a>
              <p style="margin:24px 0 0;color:#94a3b8;font-size:12px">
                If you didn't create a Turboman account, you can ignore this email.
              </p>
            </div>
            """,
        })
        logger.info("Verification email sent", to=to_email)
        return True
    except Exception as e:
        logger.error("Failed to send verification email", to=to_email, error=str(e))
        return False
