"""Tests for the Obiex client: request signing and webhook verification."""

import hashlib
import hmac
import unittest
from unittest import mock

from core.obiex import (
    STAGING_BASE_URL,
    ObiexError,
    ObiexNotConfigured,
    sign_request,
    verify_webhook_signature,
)


class ObiexSigningTests(unittest.TestCase):
    def test_signature_covers_method_path_and_timestamp(self):
        secret = "api-secret"
        timestamp = 1_700_000_000_000

        expected = hmac.new(
            secret.encode(),
            b"POST/v1/collections1700000000000",
            hashlib.sha256,
        ).hexdigest()

        self.assertEqual(
            sign_request("post", "/v1/collections", timestamp, secret), expected
        )

    def test_signature_uses_the_full_path_including_the_version(self):
        secret = "api-secret"
        timestamp = 1_700_000_000_000

        with_version = sign_request("GET", "/v1/wallets/USDC", timestamp, secret)
        without_version = sign_request("GET", "/wallets/USDC", timestamp, secret)

        self.assertNotEqual(with_version, without_version)

    def test_staging_base_url(self):
        self.assertEqual(
            STAGING_BASE_URL, "https://staging.api.obiex.finance/v1"
        )


class ObiexWebhookVerificationTests(unittest.TestCase):
    SECRET = "signature-secret"

    def _sign(self, body: bytes) -> str:
        return hmac.new(self.SECRET.encode(), body, hashlib.sha512).hexdigest()

    def test_a_valid_signature_is_accepted(self):
        body = b'{"type":"COLLECTION","status":"COMPLETED"}'

        self.assertTrue(verify_webhook_signature(body, self._sign(body), self.SECRET))

    def test_a_tampered_body_is_rejected(self):
        body = b'{"type":"COLLECTION","status":"COMPLETED"}'
        signature = self._sign(body)

        self.assertFalse(
            verify_webhook_signature(
                b'{"type":"COLLECTION","status":"HELD"}', signature, self.SECRET
            )
        )

    def test_a_missing_signature_is_rejected(self):
        self.assertFalse(
            verify_webhook_signature(b"{}", "", self.SECRET)
        )

    def test_the_wrong_secret_is_rejected(self):
        body = b"{}"

        self.assertFalse(
            verify_webhook_signature(body, self._sign(body), "other-secret")
        )


class ObiexClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_credentials_are_reported(self):
        from core.obiex import ObiexClient

        client = ObiexClient(base_url="https://api.obiex.finance/v1", api_key="", api_secret="")

        with self.assertRaises(ObiexNotConfigured):
            await client.get_fiat_rates()

    async def test_account_resolve_is_a_get_with_a_sort_code(self):
        from core.obiex import ObiexClient

        client = ObiexClient(
            base_url="https://api.obiex.finance/v1",
            api_key="key",
            api_secret="secret",
        )
        client._request = mock.AsyncMock(return_value={})

        await client.resolve_naira_account(
            account_number="9012345678", bank_code="058"
        )

        client._request.assert_awaited_once_with(
            "GET",
            "/ngn-payments/accounts/resolve",
            params={"accountNumber": "9012345678", "sortCode": "058"},
        )

    async def test_account_resolve_falls_back_to_bank_id(self):
        from core.obiex import ObiexClient

        client = ObiexClient(
            base_url="https://api.obiex.finance/v1",
            api_key="key",
            api_secret="secret",
        )
        client._request = mock.AsyncMock(
            side_effect=[ObiexError("sortCode rejected"), {"accountName": "Ada Okafor"}]
        )

        await client.resolve_naira_account(
            account_number="9012345678", bank_code="058"
        )

        self.assertEqual(client._request.await_count, 2)
        self.assertEqual(
            client._request.await_args_list[1].kwargs["params"],
            {"accountNumber": "9012345678", "bankId": "058"},
        )

    async def test_fiat_withdrawal_debits_the_currency_code(self):
        from core.obiex import ObiexClient

        client = ObiexClient(
            base_url="https://api.obiex.finance/v1",
            api_key="key",
            api_secret="secret",
        )
        client._request = mock.AsyncMock(return_value={})

        await client.request_fiat_withdrawal(
            currency="NGNX",
            amount=15_000,
            account_number="9012345678",
            account_name="Ada Okafor",
            bank_name="Fake Bank",
            bank_code="058",
        )

        method, path = client._request.await_args.args
        payload = client._request.await_args.kwargs["json"]

        self.assertEqual(method, "POST")
        self.assertEqual(path, "/wallets/ext/debit/fiat")
        self.assertEqual(payload["currency"], "NGNX")
        self.assertEqual(payload["amount"], 15_000)
        self.assertEqual(payload["destination"]["bankCode"], "058")


if __name__ == "__main__":
    unittest.main()
