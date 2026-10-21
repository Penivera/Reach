"""Test helpers: deterministic env, a fake async session, and a fake provider.

These let us exercise the real webhook and payout code paths without a
PostgreSQL instance.
"""

import os

# Deterministic settings for tests. Env vars win over the .env file.
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
os.environ.setdefault("BACKEND_URL", "http://localhost:8000")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/test"
)
os.environ.setdefault("SMTP_HOST", "localhost")
os.environ.setdefault("SMTP_PORT", "1025")
os.environ.setdefault("SMTP_USERNAME", "")
os.environ.setdefault("SMTP_PASSWORD", "")
os.environ.setdefault("SMTP_FROM_EMAIL", "no-reply@localhost")
os.environ.setdefault("SMTP_FROM_NAME", "Reach Test")
os.environ.setdefault("CLOUDINARY_CLOUD_NAME", "test")
os.environ.setdefault("CLOUDINARY_API_KEY", "test")
os.environ.setdefault("CLOUDINARY_API_SECRET", "test")
os.environ.setdefault("FOSSAPAY_ENABLED", "false")
os.environ.setdefault("PAYMENT_PROVIDER", "fake")
os.environ.setdefault("FOSSAPAY_WEBHOOK_SECRET", "test-webhook-secret")
os.environ.setdefault("PLATFORM_FEE_BPS", "500")
os.environ.setdefault("MIN_ESCROW_KOBO", "100000")
os.environ.setdefault("OBiex_ENABLED", "false")
os.environ.setdefault("OBiex_WEBHOOK_SECRET", "test-obiex-secret")
os.environ.setdefault("REACH_CREATION_FEE_BPS", "250")
os.environ.setdefault("REACH_SOLANA_RPC_URL", "http://localhost:8899")
os.environ.setdefault("REACH_PROGRAM_ID", "5iCtrxFDsPQf6qyR2nfjkDgUJyuH7oxoA5Lf1qQiDfwY")
os.environ.setdefault(
    "REACH_STABLE_MINT", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
)

# Imported after the environment is set: the settings object reads it at
# import time.
from core.fossapay import FossaPayError  # noqa: E402
from core import settings as _settings  # noqa: E402

# Another module may have imported the settings before this file ran, so the
# test values are applied to the object as well.
_settings.PAYMENT_PROVIDER = "fake"
_settings.FOSSAPAY_WEBHOOK_SECRET = "test-webhook-secret"
_settings.OBiex_WEBHOOK_SECRET = "test-obiex-secret"
_settings.REACH_CREATION_FEE_BPS = 250


class FakeResult:
    def __init__(self, value=None):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        return self

    def first(self):
        return self._value


class FakeSession:
    """Minimal async session stub.

    `execute()` returns queued results in order, which keeps the tests explicit
    about how many queries a code path performs.
    """

    def __init__(self, results=None, get_results=None):
        self.results = list(results or [])
        self.get_results = dict(get_results or {})
        self.added = []
        self.commits = 0
        self.rollbacks = 0
        self.refreshed = []

    async def execute(self, statement):
        if not self.results:
            raise AssertionError("FakeSession ran out of queued results")
        return FakeResult(self.results.pop(0))

    async def get(self, model, ident):
        if (model, ident) in self.get_results:
            return self.get_results[(model, ident)]
        return self.get_results.get(ident)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        return None

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1

    async def refresh(self, obj):
        self.refreshed.append(obj)


class FakeRequest:
    def __init__(self, body: bytes, headers: dict | None = None):
        self._body = body
        self.headers = headers or {}

    async def body(self) -> bytes:
        return self._body


class FakeProvider:
    """Stands in for the FossaPay client."""

    def __init__(self, checkout=None, payout=None, error=None):
        self.checkout = checkout
        self.payout = payout
        self.error = error
        self.checkout_calls = []
        self.payout_calls = []

    async def get_checkout(self, checkout_id):
        self.checkout_calls.append(checkout_id)
        if self.error:
            raise FossaPayError(str(self.error))
        if self.checkout is None:
            raise AssertionError("unexpected get_checkout call")
        return self.checkout

    async def get_payout(self, payout_id):
        self.payout_calls.append(payout_id)
        if self.error:
            raise FossaPayError(str(self.error))
        if self.payout is None:
            raise AssertionError("unexpected get_payout call")
        return self.payout

    async def get_payout_by_reference(self, reference):
        self.payout_calls.append(reference)
        if self.error:
            raise FossaPayError(str(self.error))
        if self.payout is None:
            raise AssertionError("unexpected get_payout_by_reference call")
        return self.payout

    async def create_payout(self, amount_ngn, reference, destination):
        self.payout_calls.append(reference)
        return {
            "id": "po_test_1",
            "reference": reference,
            "status": "completed",
            "amount": f"{amount_ngn}.00",
        }


class FakeObiex:
    """Stands in for the Obiex client."""

    def __init__(self, rates=None):
        self.rates = rates or [
            {"currency": "NGNX", "base": "USDT", "buyRate": 1600, "sellRate": 1580}
        ]
        self.calls = []

    async def get_fiat_rates(self):
        self.calls.append("get_fiat_rates")
        return self.rates

    async def initiate_collection(self, **kwargs):
        self.calls.append("initiate_collection")
        return {
            "customerId": "cus_1",
            "transactionReference": "col_1",
            "targetCurrency": kwargs.get("target_currency", "USDC"),
            "expiresAt": "2099-01-01T00:00:00.000Z",
            "account": {
                "bankName": "Fake Bank",
                "accountName": "Obiex-Ada Okoro",
                "accountNumber": "9012345678",
            },
        }

    async def create_deposit_address(self, **kwargs):
        self.calls.append("create_deposit_address")
        return {
            "id": "addr_1",
            "value": "7EcJ1eB6J3ggRrGkQWsT4ZP8dkqPZ4JmW4YRwR7Qp5cY",
            "network": kwargs.get("network", "SOL"),
            "currency": kwargs.get("currency", "USDC"),
        }
