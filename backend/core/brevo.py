"""Brevo transactional email client.

Brevo (formerly Sendinblue) sends mail over HTTPS instead of SMTP. The API key
is a server-side secret and must never reach the browser.
"""

from __future__ import annotations

import httpx

BREVO_API_URL = "https://api.brevo.com/v3"


class BrevoError(Exception):
    pass


class BrevoNotConfigured(BrevoError):
    pass


class BrevoClient:
    """Server-side Brevo client for the transactional email endpoint."""

    def __init__(
        self,
        api_key: str | None,
        api_url: str = BREVO_API_URL,
        timeout: float = 30.0,
    ):
        self.api_key = api_key
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout

    async def send_email(
        self,
        to_email: str,
        to_name: str | None,
        subject: str,
        html: str,
        sender_email: str,
        sender_name: str,
        text: str | None = None,
    ) -> str | None:
        """Send one transactional email and return Brevo's message id."""
        if not self.api_key:
            raise BrevoNotConfigured("Brevo API key is not configured")

        recipient: dict[str, str] = {"email": to_email}
        if to_name:
            recipient["name"] = to_name

        payload = {
            "sender": {"email": sender_email, "name": sender_name},
            "to": [recipient],
            "subject": subject,
            "htmlContent": html,
        }
        if text:
            payload["textContent"] = text

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.api_url}/smtp/email",
                    headers={
                        "api-key": self.api_key,
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise BrevoError(f"Brevo request failed: {exc}") from exc

        try:
            data = response.json()
        except ValueError:
            data = None

        if not response.is_success:
            message = data.get("message") if isinstance(data, dict) else None
            raise BrevoError(message or "Brevo request failed")

        if isinstance(data, dict):
            return data.get("messageId")

        return None
