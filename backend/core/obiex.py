"""Obiex client.

Obiex is the fiat/stablecoin rail behind the custodial flow:

* **Business Collections** collect a customer's NGN on a one-time virtual
  account and settle the money into USDC in the platform's Obiex wallet.
* **Deposit addresses** give every Reach user a Solana address to pay USDC
  from, with a deposit webhook when the funds land.
* **Swaps** convert platform NGN into USDC.
* **Withdrawals** move USDC out to the relayer's Solana address, and turn a
  provider's USDC back into NGN in their bank account.

Obiex has a staging environment, which is the only place this integration can
be exercised end to end before production.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any
from urllib.parse import urlparse

import httpx

PRODUCTION_BASE_URL = "https://api.obiex.finance/v1"
STAGING_BASE_URL = "https://staging.api.obiex.finance/v1"


class ObiexError(Exception):
    pass


class ObiexNotConfigured(ObiexError):
    pass


def sign_request(method: str, path: str, timestamp: int, api_secret: str) -> str:
    """Sign a request the way Obiex expects.

    The signature is an HMAC SHA-256 hex digest of
    `{method}{path}{timestamp}`, where the path includes the `/v1` prefix.
    """
    content = f"{method.upper()}{path}{timestamp}"
    return hmac.new(
        api_secret.encode("utf-8"), content.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def verify_webhook_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    """Verify an Obiex webhook signature (HMAC SHA-512 over the raw body)."""
    if not signature:
        return False

    expected = hmac.new(
        secret.encode("utf-8"), raw_body, hashlib.sha512
    ).hexdigest()

    return hmac.compare_digest(expected, signature.strip())


class ObiexClient:
    """Server-side Obiex client. The API secret must never reach the browser."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        api_secret: str,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.api_secret = api_secret
        self.timeout = timeout
        # Obiex signs the full request path including the `/v1` prefix.
        self.signing_prefix = urlparse(self.base_url).path.rstrip("/")

    async def _request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
        params: dict | None = None,
    ) -> Any:
        if not self.api_key or not self.api_secret:
            raise ObiexNotConfigured("Obiex credentials are not configured")

        url = f"{self.base_url}{path}"
        timestamp = int(time.time() * 1000)
        signature = sign_request(
            method, f"{self.signing_prefix}{path}", timestamp, self.api_secret
        )

        headers = {
            "X-API-KEY": self.api_key,
            "X-API-TIMESTAMP": str(timestamp),
            "X-API-SIGNATURE": signature,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method,
                    url,
                    headers=headers,
                    json=json,
                    params=params,
                )
        except httpx.HTTPError as exc:
            raise ObiexError(f"Obiex request failed: {exc}") from exc

        try:
            payload = response.json()
        except ValueError:
            payload = None

        if not response.is_success:
            message = None
            if isinstance(payload, dict):
                message = payload.get("message")
            raise ObiexError(message or f"Obiex request failed ({response.status_code})")

        if isinstance(payload, dict) and "data" in payload:
            return payload["data"]

        return payload

    # -- collections (fiat in) -------------------------------------------

    async def initiate_collection(
        self,
        *,
        first_name: str,
        last_name: str,
        amount: float,
        target_currency: str = "USDC",
        source_currency: str = "NGNX",
        bvn: str | None = None,
        nin: str | None = None,
    ) -> dict:
        """Create a one-time virtual NGN account for a customer to pay into."""
        customer: dict[str, Any] = {
            "firstName": first_name,
            "lastName": last_name,
        }
        if bvn:
            customer["bvn"] = bvn
        if nin:
            customer["nin"] = nin

        data = await self._request(
            "POST",
            "/collections",
            json={
                "customer": customer,
                "collectionType": "FIAT",
                "sourceCurrency": source_currency,
                "targetCurrency": target_currency,
                "amount": amount,
            },
        )
        return data if isinstance(data, dict) else {}

    async def get_collection_transactions(self) -> list[dict]:
        data = await self._request("GET", "/collections/transactions/me")
        return data if isinstance(data, list) else []

    async def get_collection_customers(self) -> list[dict]:
        data = await self._request("GET", "/collections/customers/me")
        return data if isinstance(data, list) else []

    # -- deposit addresses (crypto in) -----------------------------------

    async def create_deposit_address(
        self,
        *,
        unique_user_identifier: str,
        currency: str = "USDC",
        network: str = "SOL",
    ) -> dict:
        """Create (or fetch) a per-user deposit address for a currency/network."""
        data = await self._request(
            "POST",
            "/addresses/broker",
            json={
                "uniqueUserIdentifier": unique_user_identifier,
                "currency": currency,
                "network": network,
            },
        )
        return data if isinstance(data, dict) else {}

    async def list_deposit_addresses(self) -> list[dict]:
        data = await self._request("GET", "/addresses/me/broker")
        return data if isinstance(data, list) else []

    # -- wallets ----------------------------------------------------------

    async def get_wallet_balance(self, currency: str = "USDC") -> dict:
        data = await self._request("GET", f"/wallets/{currency}")
        return data if isinstance(data, dict) else {}

    async def get_active_networks(self) -> dict:
        data = await self._request("GET", "/currencies/networks/active")
        return data if isinstance(data, dict) else {}

    async def get_fiat_rates(self) -> list[dict]:
        data = await self._request("GET", "/currencies/fiat-rates")
        return data if isinstance(data, list) else []

    # -- trading ----------------------------------------------------------

    async def get_trade_pairs(self) -> list[dict]:
        data = await self._request("GET", "/trades/pairs")
        return data if isinstance(data, list) else []

    async def get_tradable_currencies(self) -> list[dict]:
        data = await self._request("GET", "/currencies/tradeable")
        return data if isinstance(data, list) else []

    async def instant_swap(
        self,
        *,
        source_id: str,
        target_id: str,
        amount: float,
    ) -> dict:
        data = await self._request(
            "POST",
            "/trades/swap",
            json={
                "sourceId": source_id,
                "targetId": target_id,
                "amount": amount,
                "side": "SELL",
            },
        )
        return data if isinstance(data, dict) else {}

    # -- withdrawals (crypto out) ----------------------------------------

    async def request_crypto_withdrawal(
        self,
        *,
        currency: str,
        amount: float,
        address: str,
        network: str = "SOL",
        narration: str | None = None,
    ) -> dict:
        """Withdraw crypto to an external wallet address."""
        payload: dict[str, Any] = {
            "destination": {"address": address, "network": network},
            "amount": amount,
            "currency": currency,
        }
        if narration:
            payload["narration"] = narration

        data = await self._request(
            "POST", "/wallets/ext/debit/crypto", json=payload
        )
        return data if isinstance(data, dict) else {}

    async def request_fiat_withdrawal(
        self,
        *,
        currency: str,
        amount: float,
        account_number: str,
        account_name: str,
        bank_name: str,
        bank_code: str,
        narration: str | None = None,
    ) -> dict:
        """Withdraw a fiat wallet balance to a Nigerian bank account.

        For an off-ramp the wallet is NGNX: swap USDC to NGNX first, then send
        the naira amount (not the USDC amount) here. Obiex returns the exact
        fee and bank payout in `data.payout`.
        """
        payload: dict[str, Any] = {
            "destination": {
                "accountNumber": account_number,
                "accountName": account_name,
                "bankName": bank_name,
                "bankCode": bank_code,
            },
            "amount": amount,
            "currency": currency,
        }
        if narration:
            payload["narration"] = narration

        data = await self._request(
            "POST", "/wallets/ext/debit/fiat", json=payload
        )
        return data if isinstance(data, dict) else {}

    async def get_naira_banks(self) -> list[dict]:
        data = await self._request("GET", "/ngn-payments/banks")
        return data if isinstance(data, list) else []

    async def resolve_naira_account(
        self,
        *,
        account_number: str,
        bank_code: str | None = None,
        bank_id: str | None = None,
    ) -> dict:
        """Resolve the account holder before a payout.

        Obiex's OpenAPI signs this as a GET with `sortCode` and
        `accountNumber`. Its Node SDK still uses `bankId`; support both so an
        account can be resolved whichever identifier the dashboard exposes.
        """
        if not bank_id and not bank_code:
            raise ObiexError("A bank code is required to resolve an account")

        params: dict[str, str] = {"accountNumber": account_number}
        if bank_id:
            params["bankId"] = bank_id
        else:
            params["sortCode"] = bank_code

        try:
            data = await self._request(
                "GET",
                "/ngn-payments/accounts/resolve",
                params=params,
            )
        except ObiexError:
            # Obiex's OpenAPI documents `sortCode`, but its current Node SDK
            # sends `bankId`. The bank list's `uuid` is also a valid bank
            # identifier, so retry with it before failing the payout.
            if not bank_code:
                raise
            fallback = {
                "accountNumber": account_number,
                "bankId": bank_code,
            }
            data = await self._request(
                "GET",
                "/ngn-payments/accounts/resolve",
                params=fallback,
            )

        return data if isinstance(data, dict) else {}

    # -- transactions -----------------------------------------------------

    async def get_transaction(self, transaction_id: str) -> dict:
        data = await self._request("GET", f"/transactions/{transaction_id}")
        return data if isinstance(data, dict) else {}

    async def get_deposit_transactions(self) -> list[dict]:
        data = await self._request("GET", "/transactions/deposits/me")
        return data if isinstance(data, list) else []

    async def get_payout_transactions(self) -> list[dict]:
        data = await self._request("GET", "/transactions/withdrawals/me")
        return data if isinstance(data, list) else []


class FakeObiexClient:
    """Deterministic local/test provider."""

    async def initiate_collection(
        self,
        *,
        first_name: str,
        last_name: str,
        amount: float,
        target_currency: str = "USDC",
        source_currency: str = "NGNX",
        bvn: str | None = None,
        nin: str | None = None,
    ) -> dict:
        suffix = hashlib.sha256(
            f"{first_name}{last_name}{amount}".encode()
        ).hexdigest()[:16]
        return {
            "customerId": f"fake_obiex_customer_{suffix}",
            "transactionReference": f"col_{suffix}",
            "collectionType": "FIAT",
            "sourceCurrency": source_currency,
            "targetCurrency": target_currency,
            "expiresAt": "2099-01-01T00:00:00.000Z",
            "account": {
                "bankName": "Fake Bank",
                "accountName": f"Obiex-{first_name} {last_name}",
                "accountNumber": f"90{suffix[:8]}",
            },
        }

    async def create_deposit_address(
        self,
        *,
        unique_user_identifier: str,
        currency: str = "USDC",
        network: str = "SOL",
    ) -> dict:
        suffix = hashlib.sha256(
            f"{unique_user_identifier}{currency}{network}".encode()
        ).hexdigest()[:32]
        return {
            "id": f"fake_obiex_address_{suffix[:12]}",
            "value": _fake_solana_address(suffix),
            "network": network,
            "currency": currency,
        }

    async def get_wallet_balance(self, currency: str = "USDC") -> dict:
        return {
            "currency": currency,
            "availableBalance": 100000000,
            "balance": 100000000,
        }

    async def get_fiat_rates(self) -> list[dict]:
        return [{"currency": "NGNX", "base": "USDT", "buyRate": 1600, "sellRate": 1580}]

    async def get_active_networks(self) -> dict:
        return {
            "USDC": {
                "currencyName": "USD Coin",
                "networks": [
                    {
                        "networkName": "Solana",
                        "networkCode": "SOL",
                        "isReceivable": True,
                        "isWithdrawable": True,
                    }
                ],
            },
            "NGNX": {
                "currencyName": "Naira",
                "networks": [
                    {
                        "networkName": "Naira",
                        "networkCode": "NGN",
                        "isReceivable": True,
                        "isWithdrawable": True,
                    }
                ],
            },
        }

    async def get_trade_pairs(self) -> list[dict]:
        return [
            {
                "id": "fake-usdc-ngnx",
                "source": {"id": "USDC", "code": "USDC"},
                "target": {"id": "NGNX", "code": "NGNX"},
                "isSellable": True,
                "isBuyable": True,
            },
            {
                "id": "fake-usdc-usdt",
                "source": {"id": "USDC", "code": "USDC"},
                "target": {"id": "USDT", "code": "USDT"},
                "isSellable": True,
                "isBuyable": True,
            },
            {
                "id": "fake-usdt-ngnx",
                "source": {"id": "USDT", "code": "USDT"},
                "target": {"id": "NGNX", "code": "NGNX"},
                "isSellable": True,
                "isBuyable": True,
            },
        ]

    async def get_tradable_currencies(self) -> list[dict]:
        return [
            {
                "id": "NGNX",
                "active": True,
                "name": "Naira",
                "code": "NGNX",
                "receivable": True,
                "withdrawable": True,
                "minimumWithdrawal": 5000,
                "maximumWithdrawal": 10000000,
                "withdrawalFee": 50,
                "withdrawalFeeType": "FLAT",
            },
            {
                "id": "USDC",
                "active": True,
                "name": "USD Coin",
                "code": "USDC",
                "receivable": True,
                "withdrawable": True,
                "minimumWithdrawal": 5,
                "maximumWithdrawal": 5000000,
                "withdrawalFee": 0,
                "withdrawalFeeType": "FLAT",
            },
        ]

    async def instant_swap(
        self,
        *,
        source_id: str,
        target_id: str,
        amount: float,
    ) -> dict:
        if target_id == "NGNX":
            rate = 1580
            received = round(float(amount) * rate, 2)
            return {
                "id": "fake_swap_ngnx",
                "reference": "fake_swap_ngnx",
                "status": "SUCCESSFUL",
                "rate": rate,
                "amount": amount,
                "amountReceived": received,
            }
        return {
            "id": "fake_swap_usdt",
            "reference": "fake_swap_usdt",
            "status": "SUCCESSFUL",
            "rate": 1,
            "amount": amount,
            "amountReceived": amount,
        }

    async def request_crypto_withdrawal(
        self,
        *,
        currency: str,
        amount: float,
        address: str,
        network: str = "SOL",
        narration: str | None = None,
    ) -> dict:
        return {
            "id": "fake_withdrawal",
            "reference": "fake_withdrawal_reference",
            "status": "APPROVED",
            "amount": amount,
            "payout": {"status": "APPROVED", "wallet": {"address": address}},
        }

    async def request_fiat_withdrawal(
        self,
        *,
        currency: str,
        amount: float,
        account_number: str,
        account_name: str,
        bank_name: str,
        bank_code: str,
        narration: str | None = None,
    ) -> dict:
        fee = 50
        return {
            "id": "fake_fiat_withdrawal",
            "reference": "fake_fiat_withdrawal_reference",
            "status": "APPROVED",
            "amount": amount,
            "payout": {
                "id": "fake_fiat_payout",
                "status": "APPROVED",
                "fee": fee,
                "payoutAmount": max(float(amount) - fee, 0),
                "payoutCurrency": "NGNX",
                "bankAccount": {
                    "accountNumber": account_number,
                    "accountName": account_name,
                    "bankName": bank_name,
                    "bankCode": bank_code,
                },
            },
        }

    async def get_naira_banks(self) -> list[dict]:
        return [
            {"name": "Fake Bank", "uuid": "fake-bank", "sortCode": "058"},
            {"name": "Fake Microfinance Bank", "uuid": "fake-mfb", "sortCode": "090133"},
        ]

    async def resolve_naira_account(
        self,
        *,
        account_number: str,
        bank_code: str | None = None,
        bank_id: str | None = None,
    ) -> dict:
        return {
            "bankId": bank_id or bank_code,
            "accountNumber": account_number,
            "accountName": "Ada Okafor",
        }

    async def get_collection_transactions(self) -> list[dict]:
        return []

    async def get_payout_transactions(self) -> list[dict]:
        return []

    async def get_transaction(self, transaction_id: str) -> dict:
        return {"id": transaction_id, "status": "SUCCESSFUL"}


def _fake_solana_address(seed: str) -> str:
    digest = hashlib.sha256(seed.encode()).digest()
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    number = int.from_bytes(digest, "big")
    encoded = ""
    while number > 0:
        number, remainder = divmod(number, 58)
        encoded = alphabet[remainder] + encoded
    return encoded[:44].ljust(44, "1")


def get_obiex_client() -> ObiexClient | FakeObiexClient:
    """Build the Obiex client from the settings."""
    from core import settings

    if settings.PAYMENT_PROVIDER == "fake":
        return FakeObiexClient()

    if not settings.OBiex_ENABLED:
        raise ObiexNotConfigured("Obiex is not enabled")

    if not settings.OBiex_API_KEY or not settings.OBiex_API_SECRET:
        raise ObiexNotConfigured("Obiex credentials are not configured")

    return ObiexClient(
        base_url=settings.OBiex_API_URL,
        api_key=settings.OBiex_API_KEY,
        api_secret=settings.OBiex_API_SECRET,
        timeout=settings.OBiex_TIMEOUT_SECONDS,
    )
