import resend

from core import settings

resend.api_key = settings.RESEND_API_KEY

async def send_verification_email(email: str, token: str) -> str:
    verification_link = (f"{settings.BACKEND_URL}/auth/verify-email?token={token}")

    resend.Emails.send(
        {
            "from": "onboarding@resend.dev",
            "to": email,
            "subject": "Verify your WorkNear account",
            "html": f"""
                <h2>Welcome to WorkNear</h2>

                <p>
                    Click the link below to verify your email:
                </p>

                <a href="{verification_link}">
                    Verify Email
                </a>
            """
        }
    )