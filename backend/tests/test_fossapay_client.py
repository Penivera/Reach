"""FossaPay client request-shape tests.

The client has to forward query parameters; `list_crypto_wallet_transactions`
and `calculate_crypto_transfer_fee` both pass `params=`, which the transport
used to reject with a TypeError.
"""

import unittest
from unittest import mock

from core.fossapay import FossaPayClient


class FakeResponse:
    is_success = True

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class FakeAsyncClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def request(self, method, url, headers=None, json=None, params=None):
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "json": json,
                "params": params,
            }
        )
        return FakeResponse(self.payload)


class FossaPayRequestTests(unittest.IsolatedAsyncioTestCase):
    async def test_transaction_listing_forwards_pagination(self):
        fake = FakeAsyncClient({"data": []})
        client = FossaPayClient("https://api.example/v1", "key")

        with mock.patch(
            "core.fossapay.httpx.AsyncClient", return_value=fake
        ):
            await client.list_crypto_wallet_transactions("wallet_1", page=2, limit=10)

        self.assertEqual(fake.calls[0]["params"], {"page": 2, "limit": 10})
        self.assertEqual(fake.calls[0]["headers"]["x-api-key"], "key")

    async def test_fee_quote_forwards_its_query(self):
        fake = FakeAsyncClient({"data": {"feeAmount": "0.00"}})
        client = FossaPayClient("https://api.example/v1", "key")

        with mock.patch(
            "core.fossapay.httpx.AsyncClient", return_value=fake
        ):
            await client.calculate_crypto_transfer_fee(
                amount=10, currency="usdc", network="solana"
            )

        self.assertEqual(
            fake.calls[0]["params"],
            {"amount": 10, "currency": "usdc", "network": "solana"},
        )


if __name__ == "__main__":
    unittest.main()
