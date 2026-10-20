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
