import hashlib
import re

import httpx

from core import settings


class FossaPayError(Exception):
    pass


class FossaPayNotConfigured(FossaPayError):
    pass


class FossaPayClient:
    """Server-side FossaPay client. The API key must never reach the browser."""

    def __init__(self, api_url: str, api_key: str, timeout: float = 30.0):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    async def _request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
        params: dict | None = None,
        idempotency_key: str | None = None,
    ):
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method,
                    f"{self.api_url}/{path.lstrip('/')}",
                    headers=headers,
                    json=json,
                    params=params,
                )
        except httpx.HTTPError as exc:
            raise FossaPayError(f"FossaPay request failed: {exc}") from exc

        try:
            payload = response.json()
        except ValueError:
            payload = None

        if not response.is_success:
            message = payload.get("message") if isinstance(payload, dict) else None
            raise FossaPayError(message or "FossaPay request failed")

        if isinstance(payload, dict) and payload.get("status") == "error":
            raise FossaPayError(payload.get("message") or "FossaPay returned an error")

        if isinstance(payload, dict) and "data" in payload:
            return payload["data"]

        return payload

    async def create_customer(self, payload: dict) -> dict:
        data = await self._request("POST", "/customers", json=payload)
        if not isinstance(data, dict) or not data.get("id"):
            raise FossaPayError("FossaPay did not return a customer id")
        return data

    async def create_fiat_wallet(
        self,
        customer_id: str,
        wallet_name: str,
        wallet_reference: str,
    ) -> dict:
        data = await self._request(
            "POST",
            "/wallets/fiat/create",
            json={
                "customerId": customer_id,
                "walletName": wallet_name,
                "walletReference": wallet_reference,
            },
        )
        if not isinstance(data, dict) or not data.get("walletId"):
            raise FossaPayError("FossaPay did not return a wallet id")
        return data

    async def create_checkout(
        self,
        amount_ngn: int,
        reference: str,
        customer: dict,
    ) -> dict:
        data = await self._request(
            "POST",
            "/checkouts",
            json={
                "amount": amount_ngn,
                "currency": "NGN",
                "reference": reference,
                "feeBearer": "customer",
                "customer": customer,
                "metadata": {"reach_reference": reference},
            },
            idempotency_key=reference,
        )
        if not isinstance(data, dict) or not data.get("id") or not data.get("account"):
            raise FossaPayError("FossaPay did not return a checkout account")
        return data

    async def get_checkout(self, checkout_id: str) -> dict:
        data = await self._request("GET", f"/checkouts/{checkout_id}")
        if not isinstance(data, dict):
            raise FossaPayError("FossaPay returned an invalid checkout")
        return data

    async def get_payout(self, payout_id: str) -> dict:
        data = await self._request("GET", f"/payouts/{payout_id}")
        if not isinstance(data, dict):
            raise FossaPayError("FossaPay returned an invalid payout")
        return data

    async def get_payout_by_reference(self, reference: str) -> dict:
        data = await self._request("GET", f"/payouts/reference/{reference}")
        if not isinstance(data, dict):
            raise FossaPayError("FossaPay returned an invalid payout")
        return data

    async def expire_checkout(self, checkout_id: str) -> dict:
        data = await self._request("POST", f"/checkouts/{checkout_id}/expire")
        if not isinstance(data, dict):
            raise FossaPayError("FossaPay returned an invalid checkout")
        return data

    async def get_customer(self, customer_id: str) -> dict:
        data = await self._request("GET", f"/customers/{customer_id}")
        if not isinstance(data, dict):
            raise FossaPayError("FossaPay returned an invalid customer")
        return data

    async def list_customers(self) -> list[dict]:
        data = await self._request("GET", "/customers")
        if isinstance(data, dict):
            data = data.get("result", [])
        return data if isinstance(data, list) else []

    # -- crypto wallets ----------------------------------------------------

    async def create_crypto_wallet(
        self,
        customer_id: str,
        network: str = "solana",
    ) -> dict:
        """Provision a Solana (or Stellar) wallet for a customer."""
        data = await self._request(
            "POST",
            "/wallets/crypto/create",
            json={"network": network, "customerId": customer_id},
        )
        if not isinstance(data, dict) or not data.get("address"):
            raise FossaPayError("FossaPay did not return a crypto wallet address")
        return data

    async def create_master_crypto_wallet(self, network: str = "solana") -> list[dict]:
        data = await self._request(
            "POST", "/wallets/crypto/master/create", json={"network": network}
        )
        return data if isinstance(data, list) else []

    async def get_master_crypto_wallet(self) -> list[dict]:
        data = await self._request("GET", "/wallets/crypto/master")
        return data if isinstance(data, list) else []

    async def get_customer_crypto_balance(
        self,
        customer_id: str,
        network: str | None = None,
    ) -> dict:
        path = f"/wallets/crypto/customer/{customer_id}/balance"
        if network:
            path = f"{path}?network={network}"
        data = await self._request("GET", path)
        return data if isinstance(data, dict) else {}

    async def get_crypto_wallet(self, wallet_id: str) -> dict:
        data = await self._request("GET", f"/wallets/crypto/{wallet_id}")
        if not isinstance(data, dict):
            raise FossaPayError("FossaPay returned an invalid crypto wallet")
        return data

    async def get_crypto_wallet_by_address(self, address: str) -> dict:
        data = await self._request("GET", f"/wallets/crypto/address/{address}")
        if not isinstance(data, dict):
            raise FossaPayError("FossaPay returned an invalid crypto wallet")
        return data

    async def list_crypto_wallet_transactions(
        self,
        wallet_id: str,
        page: int = 1,
        limit: int = 50,
    ) -> list[dict]:
        data = await self._request(
            "GET",
            f"/wallets/crypto/{wallet_id}/transactions",
            params={"page": page, "limit": limit},
        )
        return data if isinstance(data, list) else []

    async def get_crypto_transaction(self, transaction_id: str) -> dict:
        data = await self._request("GET", f"/wallets/crypto/transactions/{transaction_id}")
        if not isinstance(data, dict):
            raise FossaPayError("FossaPay returned an invalid crypto transaction")
        return data

    async def create_crypto_transfer(
        self,
        *,
        customer_id: str,
        recipient: str,
        amount: float,
        currency: str = "usdc",
        network: str = "solana",
        memo: str | None = None,
    ) -> dict:
        """Send crypto from a customer's wallet to any address on the network."""
        payload: dict = {
            "customerId": customer_id,
            "recipient": recipient,
            "network": network,
            "currency": currency,
            "amount": amount,
        }
        if memo:
            payload["memo"] = memo

        data = await self._request("POST", "/transfers/crypto", json=payload)
        if not isinstance(data, dict):
            raise FossaPayError("FossaPay returned an invalid crypto transfer")
        return data

    async def calculate_crypto_transfer_fee(
        self,
        *,
        amount: float,
        currency: str = "usdc",
        network: str | None = None,
    ) -> dict:
        params = {"amount": amount, "currency": currency}
        if network:
            params["network"] = network

        data = await self._request(
            "GET", "/transfers/crypto/calculate-fee", params=params
        )
        return data if isinstance(data, dict) else {}

    # -- identity ----------------------------------------------------------

    async def verify_identity(
        self,
        *,
        method: str,
        identity_number: str,
    ) -> dict:
        """Look up a Nigerian NIN or BVN. `method` is `nin` or `bvn`."""
        data = await self._request(
            "POST",
            "/kyc/verifications",
            json={"method": method, "identityNumber": identity_number},
        )
        return data if isinstance(data, dict) else {}

    # -- webhook administration -------------------------------------------

    async def update_webhook_settings(
        self,
        *,
        url: str,
        events: list[str],
        secret: str,
    ) -> dict:
        data = await self._request(
            "PUT",
            "/settings/webhooks",
            json={"url": url, "events": events, "secret": secret},
        )
        return data if isinstance(data, dict) else {}

    async def simulate_webhook(
        self,
        *,
        event: str,
        customer_id: str,
        amount: float,
        currency: str = "NGN",
    ) -> dict:
        data = await self._request(
            "POST",
            "/webhooks/simulate",
            json={
                "event": event,
                "customer_id": customer_id,
                "amount": amount,
                "currency": currency,
            },
        )
        return data if isinstance(data, dict) else {}

    async def create_payout(
        self,
        amount_ngn: int,
        reference: str,
        destination: dict,
    ) -> dict:
        data = await self._request(
            "POST",
            "/payouts",
            json={
                "amount": amount_ngn,
                "currency": "NGN",
                "reference": reference,
                "destinationBankCode": destination["bank_code"],
                "destinationBankName": destination["bank_name"],
                "destinationAccountName": destination["account_name"],
                "destinationAccountNumber": destination["account_number"],
                "remarks": "Reach job payout",
                "metadata": {"reach_reference": reference},
            },
            idempotency_key=reference,
        )
        if not isinstance(data, dict) or not data.get("id"):
            raise FossaPayError("FossaPay did not return a payout id")
        return data


class FakeFossaPayClient:
    """Deterministic local/test provider. Never used when PAYMENT_PROVIDER=fossapay."""

    async def create_customer(self, payload: dict) -> dict:
        email = str(payload.get("emailAddress", "")).strip().lower()
        suffix = hashlib.sha256(email.encode()).hexdigest()[:12]
        return {"id": f"fake_cust_{suffix}"}

    async def create_fiat_wallet(
        self,
        customer_id: str,
        wallet_name: str,
        wallet_reference: str,
    ) -> dict:
        suffix = hashlib.sha256(customer_id.encode()).hexdigest()[:8]
        number = re.sub(r"\D", "", suffix)[:8].ljust(8, "0")
        return {
            "walletId": f"fake_wallet_{suffix}",
            "bankName": "Fake Bank",
            "accountName": wallet_name.upper(),
            "accountNumber": f"99{number}",
        }

    async def create_checkout(
        self,
        amount_ngn: int,
        reference: str,
        customer: dict,
    ) -> dict:
        return {
            "id": f"fake_checkout_{reference}",
            "reference": reference,
            "status": "pending",
            "amount": f"{amount_ngn:.2f}",
            "amountPayable": f"{amount_ngn:.2f}",
            "expiresAt": "2099-01-01T00:00:00.000Z",
            "account": {
                "bankName": "Fake Bank",
                "accountName": "FOSSAPAY CHECKOUT",
                "accountNumber": "9541382701",
            },
        }

    async def create_payout(
        self,
        amount_ngn: int,
        reference: str,
        destination: dict,
    ) -> dict:
        return {
            "id": f"fake_payout_{reference}",
            "reference": reference,
            "status": "completed",
            "amount": f"{amount_ngn:.2f}",
            "fee": "0.00",
        }

    async def get_checkout(self, checkout_id: str) -> dict:
        return {"id": checkout_id, "status": "completed"}

    async def get_payout(self, payout_id: str) -> dict:
        return {"id": payout_id, "status": "completed"}

    async def get_payout_by_reference(self, reference: str) -> dict:
        return {
            "id": f"fake_payout_{reference}",
            "reference": reference,
            "status": "completed",
        }

    async def create_crypto_wallet(
        self,
        customer_id: str,
        network: str = "solana",
    ) -> dict:
        suffix = hashlib.sha256(customer_id.encode()).hexdigest()[:32]
        return {
            "id": f"fake_crypto_wallet_{suffix}",
            "walletId": f"fake_crypto_wallet_{suffix}",
            "address": _fake_solana_address(suffix),
            "network": network,
        }

    async def get_master_crypto_wallet(self) -> list[dict]:
        return [
            {
                "id": "fake_master_wallet",
                "address": _fake_solana_address("master"),
                "network": "solana",
                "tokens": {},
            }
        ]

    async def get_customer_crypto_balance(
        self,
        customer_id: str,
        network: str | None = None,
    ) -> dict:
        return {"customerId": customer_id, "tokens": {}}

    async def get_crypto_wallet(self, wallet_id: str) -> dict:
        return {"id": wallet_id, "address": _fake_solana_address(wallet_id)}

    async def get_crypto_wallet_by_address(self, address: str) -> dict:
        return {"id": "fake_crypto_wallet", "address": address}

    async def list_crypto_wallet_transactions(
        self,
        wallet_id: str,
        page: int = 1,
        limit: int = 50,
    ) -> list[dict]:
        return []

    async def get_crypto_transaction(self, transaction_id: str) -> dict:
        return {"id": transaction_id, "status": "success"}

    async def create_crypto_transfer(
        self,
        *,
        customer_id: str,
        recipient: str,
        amount: float,
        currency: str = "usdc",
        network: str = "solana",
        memo: str | None = None,
    ) -> dict:
        return {
            "token": {"symbol": currency, "amount": amount},
            "network": network.upper(),
            "recipientAddress": recipient,
            "status": "processing",
        }

    async def calculate_crypto_transfer_fee(
        self,
        *,
        amount: float,
        currency: str = "usdc",
        network: str | None = None,
    ) -> dict:
        return {"amount": amount, "currency": currency, "feeAmount": 0, "total": amount}

    async def verify_identity(
        self,
        *,
        method: str,
        identity_number: str,
    ) -> dict:
        return {
            "reference": f"fake_kyc_{method}",
            "method": method,
            "charged": False,
            "feeAmount": "0.00",
            "currency": "NGN",
            "person": {"firstName": "Fake", "lastName": "Customer"},
        }

    async def update_webhook_settings(
        self,
        *,
        url: str,
        events: list[str],
        secret: str,
    ) -> dict:
        return {"url": url, "events": events, "active": True}

    async def simulate_webhook(
        self,
        *,
        event: str,
        customer_id: str,
        amount: float,
        currency: str = "NGN",
    ) -> dict:
        return {"event": event, "customerId": customer_id, "status": "simulated"}


def _fake_solana_address(seed: str) -> str:
    """A deterministic, syntactically valid base58 Solana address."""
    digest = hashlib.sha256(seed.encode()).digest()
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    number = int.from_bytes(digest, "big")
    encoded = ""
    while number > 0:
        number, remainder = divmod(number, 58)
        encoded = alphabet[remainder] + encoded
    return encoded[:44].ljust(44, "1")


def get_fossapay_client() -> FossaPayClient | FakeFossaPayClient:
    if settings.PAYMENT_PROVIDER == "fake":
        return FakeFossaPayClient()

    if not settings.FOSSAPAY_ENABLED:
        raise FossaPayNotConfigured("FossaPay is not enabled")

    if not settings.FOSSAPAY_API_KEY:
        raise FossaPayNotConfigured("FOSSAPAY_API_KEY is not configured")

    return FossaPayClient(
        api_url=settings.FOSSAPAY_API_URL,
        api_key=settings.FOSSAPAY_API_KEY,
        timeout=settings.FOSSAPAY_TIMEOUT_SECONDS,
    )
