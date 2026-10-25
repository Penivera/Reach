"""Brevo transactional email tests.

The HTTP payload matters: Brevo rejects mail whose sender is not verified, so
the request has to carry the configured From address and the HTML body without
wrapping it in SMTP concepts.
"""

import unittest
from unittest import mock

import support  # noqa: F401  (sets deterministic settings before imports)

import utils.email_service as mail
from core.brevo import BrevoClient, BrevoError, BrevoNotConfigured
from utils.email_service import EmailService


class FakeResponse:
    def __init__(self, payload, is_success=True):
        self.payload = payload
        self.is_success = is_success

    def json(self):
        return self.payload


class FakeAsyncClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, headers=None, json=None):
        self.calls.append({"url": url, "headers": headers, "json": json})
        return self.response


def send(client, **overrides):
    payload = {
        "to_email": "ada@example.com",
        "to_name": "Ada",
        "subject": "Verify your account",
        "html": "<p>Click to verify</p>",
        "sender_email": "no-reply@reach.example",
        "sender_name": "Reach",
        "text": "Use an HTML client",
    }
    payload.update(overrides)
    return client.send_email(**payload)


class BrevoClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_send_email_posts_the_transactional_payload(self):
        fake = FakeAsyncClient(FakeResponse({"messageId": "<abc@brevo>"}))
        client = BrevoClient("key-1")

        with mock.patch("core.brevo.httpx.AsyncClient", return_value=fake):
            message_id = await send(client)

        self.assertEqual(message_id, "<abc@brevo>")
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(
            fake.calls[0]["url"], "https://api.brevo.com/v3/smtp/email"
        )
        self.assertEqual(fake.calls[0]["headers"]["api-key"], "key-1")
        self.assertEqual(
            fake.calls[0]["json"],
            {
                "sender": {"email": "no-reply@reach.example", "name": "Reach"},
                "to": [{"email": "ada@example.com", "name": "Ada"}],
                "subject": "Verify your account",
                "htmlContent": "<p>Click to verify</p>",
                "textContent": "Use an HTML client",
            },
        )

    async def test_recipient_name_is_omitted_when_unknown(self):
        fake = FakeAsyncClient(FakeResponse({"messageId": "1"}))
        client = BrevoClient("key-1")

        with mock.patch("core.brevo.httpx.AsyncClient", return_value=fake):
            await send(client, to_name=None)

        self.assertEqual(
            fake.calls[0]["json"]["to"], [{"email": "ada@example.com"}]
        )

    async def test_missing_api_key_is_a_configuration_error(self):
        with self.assertRaises(BrevoNotConfigured):
            await send(BrevoClient(None))

    async def test_provider_error_message_is_surfaced(self):
        fake = FakeAsyncClient(
            FakeResponse({"message": "Sender not verified"}, is_success=False)
        )

        with mock.patch("core.brevo.httpx.AsyncClient", return_value=fake):
            with self.assertRaises(BrevoError) as raised:
                await send(BrevoClient("key-1"))

        self.assertIn("Sender not verified", str(raised.exception))


class EmailServiceProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_brevo_is_used_when_enabled(self):
        service = EmailService()
        fake = FakeAsyncClient(FakeResponse({"messageId": "1"}))

        with mock.patch.object(mail.settings, "BREVO_ENABLED", True), \
                mock.patch.object(mail.settings, "BREVO_API_KEY", "key-1"), \
                mock.patch("core.brevo.httpx.AsyncClient", return_value=fake):
            await service.send_email(
                "ada@example.com", "Verify your account", "<p>Hi</p>"
            )

        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(fake.calls[0]["url"], "https://api.brevo.com/v3/smtp/email")
        self.assertEqual(fake.calls[0]["json"]["htmlContent"], "<p>Hi</p>")
        self.assertEqual(
            fake.calls[0]["json"]["sender"]["email"], mail.settings.SMTP_FROM_EMAIL
        )

    async def test_smtp_is_used_when_brevo_is_disabled(self):
        service = EmailService()

        with mock.patch.object(mail.settings, "BREVO_ENABLED", False), \
                mock.patch(
                    "utils.email_service.aiosmtplib.send", new=mock.AsyncMock()
                ) as smtp:
            await service.send_email(
                "ada@example.com", "Verify your account", "<p>Hi</p>"
            )

        smtp.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
