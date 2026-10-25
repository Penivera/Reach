import logging
from email.message import EmailMessage

import aiosmtplib
from core import settings
from core.brevo import BrevoClient

logger = logging.getLogger(__name__)

PLAIN_TEXT_BODY = "Please use an HTML email client to view this message."


class EmailService:
    async def send_email(self, to_email: str, subject: str, html: str):
        if settings.BREVO_ENABLED:
            await self._send_via_brevo(to_email, subject, html)
            return

        await self._send_via_smtp(to_email, subject, html)

    async def _send_via_brevo(self, to_email: str, subject: str, html: str):
        client = BrevoClient(
            api_key=settings.BREVO_API_KEY,
            api_url=settings.BREVO_API_URL,
            timeout=settings.BREVO_TIMEOUT_SECONDS,
        )

        await client.send_email(
            to_email=to_email,
            to_name=None,
            subject=subject,
            html=html,
            sender_email=settings.SMTP_FROM_EMAIL,
            sender_name=settings.SMTP_FROM_NAME,
            text=PLAIN_TEXT_BODY,
        )

    async def _send_via_smtp(self, to_email: str, subject: str, html: str):
        message = EmailMessage()

        message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        message["To"] = to_email
        message["Subject"] = subject

        message.set_content(PLAIN_TEXT_BODY)
        message.add_alternative(html, subtype="html")

        send_options = {
            "hostname": settings.SMTP_HOST,
            "port": settings.SMTP_PORT,
            "start_tls": settings.SMTP_START_TLS,
        }

        # Local mail catchers usually have no authentication. Only pass
        # credentials when they are actually configured, otherwise aiosmtplib
        # may try to AUTH against a server that does not support it.
        username = (settings.SMTP_USERNAME or "").strip()
        if username:
            send_options["username"] = username
            send_options["password"] = settings.SMTP_PASSWORD

        await aiosmtplib.send(message, **send_options)


email_service = EmailService()


async def send_verification_email(email: str, token: str) -> None:
    verification_link = f"{settings.BACKEND_URL}/auth/verify-email?token={token}"

    html = f"""
    <h2>Welcome to WorkNear</h2>

    <p>
        Click the link below to verify your email.
    </p>

    <a href="{verification_link}">
        Verify Email
    </a>
    """

    await email_service.send_email(
        to_email=email,
        subject="Verify your WorkNear account",
        html=html,
    )


async def send_reset_password_email(email: str, token: str) -> None:
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"

    html = f"""
    <h2>Password Reset</h2>

    <p>
        Click the link below to reset your password.
    </p>

    <a href="{reset_link}">
        Reset Password
    </a>
    """

    await email_service.send_email(
        to_email=email,
        subject="Reset Your Password",
        html=html,
    )
