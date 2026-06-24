import resend
from src.config import settings
from src.utils.logger import logger


def _client():
    resend.api_key = settings.resend_api_key


def send_password_reset_email(to_email: str, name: str, token: str) -> bool:
    """Send a password reset link. Returns True on success."""
    _client()
    base = settings.frontend_url.rstrip("/")
    reset_url = f"{base}/reset-password?token={token}"

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": to_email,
            "subject": "Reset your Turboman password",
            "html": f"""
            <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px 24px">
              <h2 style="margin:0 0 8px;font-size:22px;color:#0f172a">Reset your password</h2>
              <p style="margin:0 0 24px;color:#475569;font-size:15px;line-height:1.6">
                Hi {name}, click the button below to set a new password.
                This link expires in 1 hour.
              </p>
              <a href="{reset_url}"
                 style="display:inline-block;background:#1e293b;color:#fff;font-weight:600;
                        font-size:14px;padding:12px 24px;border-radius:8px;text-decoration:none">
                Reset password
              </a>
              <p style="margin:24px 0 0;color:#94a3b8;font-size:12px">
                If you didn't request a password reset, you can ignore this email.
              </p>
            </div>
            """,
        })
        logger.info("Password reset email sent", to=to_email)
        return True
    except Exception as e:
        logger.error("Failed to send password reset email", to=to_email, error=str(e))
        return False


def send_invite_email(to_email: str, name: str, temp_password: str) -> bool:
    """Send a team invite with a temporary password. Returns True on success."""
    _client()
    login_url = settings.frontend_url.rstrip("/") + "/login"

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": to_email,
            "subject": "You've been invited to Turboman",
            "html": f"""
            <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px 24px">
              <h2 style="margin:0 0 8px;font-size:22px;color:#0f172a">Welcome to Turboman, {name}!</h2>
              <p style="margin:0 0 16px;color:#475569;font-size:15px;line-height:1.6">
                You've been added to your team's Turboman account. Use the credentials below to log in.
              </p>
              <p style="margin:0 0 8px;color:#475569;font-size:15px"><strong>Email:</strong> {to_email}</p>
              <p style="margin:0 0 24px;color:#475569;font-size:15px"><strong>Temporary password:</strong> {temp_password}</p>
              <a href="{login_url}"
                 style="display:inline-block;background:#1e293b;color:#fff;font-weight:600;
                        font-size:14px;padding:12px 24px;border-radius:8px;text-decoration:none">
                Log in to Turboman
              </a>
              <p style="margin:24px 0 0;color:#94a3b8;font-size:12px">
                Please change your password after your first login.
              </p>
            </div>
            """,
        })
        logger.info("Invite email sent", to=to_email)
        return True
    except Exception as e:
        logger.error("Failed to send invite email", to=to_email, error=str(e))
        return False


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
                 style="display:inline-block;background:#1e293b;color:#fff;font-weight:600;
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
