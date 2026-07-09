import aiosmtplib
from email.message import EmailMessage
from core import settings

class EmailService:
    
    async def send_email(self, to_email:str, subject:str, html:str):
        
        message = EmailMessage()

        message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"

        message["To"] = to_email

        message["subject"] = subject

        message.set_content("Please use an HTML email client to view this message.")

        message.add_alternative(html, subtype="html")

        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD,
            start_tls=True,
        )
        

email_service = EmailService()

async def send_verification_email(
    email: str,
    token: str,
) -> None:

    verification_link = (
        f"{settings.BACKEND_URL}/auth/verify-email?token={token}"
    )

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



async def send_reset_password_email(
    email: str,
    token: str,
) -> None:

    reset_link = (
        f"{settings.BACKEND_URL}/auth/reset-password?token={token}"
    )

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