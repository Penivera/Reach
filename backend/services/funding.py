"""Funding rails: how a customer's money reaches a task's escrow.

Model 1 locks the escrow when the task is created, so a task is created
waiting for funding and opens once the escrow is on-chain. Three rails are
supported:

* ``obiex_fiat`` — the customer pays NGN into a one-time virtual account and
  Obiex settles it into USDC. The settled USDC amount is what gets escrowed.
* ``fossapay_checkout`` — the customer pays NGN into a FossaPay checkout. The
  platform converts the NGN with Obiex and escrows from its USDC float.
* ``crypto`` — the customer sends USDC to a per-user Solana deposit address.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import settings
from core.fossapay import get_fossapay_client
from core.obiex import get_obiex_client
from models import FossaPayCustomer, Job, PaymentIntent, PaymentProfile, User
from schemas.enums import FundingRail, PaymentStatus

USDC_UNIT = 10**6


class FundingError(RuntimeError):
    pass


class ProfileIncomplete(FundingError):
    """The customer is missing information the rail needs."""


def to_usdc_units(amount) -> int:
    """Convert a decimal amount of USDC into base units."""
    try:
        value = Decimal(str(amount))
    except Exception as exc:  # pragma: no cover - defensive
        raise FundingError("Invalid USDC amount") from exc

    units = (value * USDC_UNIT).to_integral_value(rounding=ROUND_DOWN)
    return int(units)


def to_kobo(amount) -> int:
    """Convert a naira amount into kobo."""
    try:
        value = Decimal(str(amount)) * 100
    except Exception as exc:  # pragma: no cover - defensive
        raise FundingError("Invalid naira amount") from exc

    if value != value.to_integral_value():
        raise FundingError("Amount cannot have sub-kobo precision")

    return int(value)


def job_budget_naira(job: Job) -> int:
    """The job's budget in whole naira."""
    budget = int(round(float(job.budget)))
    if budget <= 0:
        raise FundingError("The job has no budget to fund")
    return budget


def _reference(prefix: str, job_id: int) -> str:
    return f"{prefix}-job-{job_id}-{uuid4().hex[:10]}"


async def _existing_intent(
    db: AsyncSession, job_id: int, rail: FundingRail
) -> PaymentIntent | None:
    """Reuse a pending intent for the same job and rail."""
    result = await db.execute(
        select(PaymentIntent)
        .where(
            PaymentIntent.job_id == job_id,
            PaymentIntent.rail == rail,
            PaymentIntent.status == PaymentStatus.PENDING,
        )
        .order_by(PaymentIntent.id.desc())
    )
    return result.scalars().first()


async def create_obiex_collection(
    db: AsyncSession,
    *,
    job: Job,
    user: User,
    profile: PaymentProfile,
) -> PaymentIntent:
    """Open a one-time NGN virtual account for the customer to pay into."""
    if not (profile.bvn or profile.nin):
        raise ProfileIncomplete(
            "A BVN or NIN is required before we can collect your payment"
        )

    existing = await _existing_intent(db, job.id, FundingRail.OBIEX_FIAT)
    if existing:
        return existing

    client = get_obiex_client()
    amount_naira = job_budget_naira(job)

    collection = await client.initiate_collection(
        first_name=(user.first_name or "").strip(),
        last_name=(user.last_name or "").strip(),
        amount=amount_naira,
        target_currency=settings.OBiex_COLLECTION_CURRENCY,
        bvn=profile.bvn,
        nin=profile.nin,
    )

    account = collection.get("account") or {}
    expires_at = collection.get("expiresAt")

    intent = PaymentIntent(
        job_id=job.id,
        reference=_reference("fund", job.id),
        rail=FundingRail.OBIEX_FIAT,
        amount_kobo=to_kobo(amount_naira),
        amount_payable_kobo=to_kobo(amount_naira),
        status=PaymentStatus.PENDING,
        provider_reference=collection.get("transactionReference"),
        provider_customer_id=collection.get("customerId"),
        bank_name=account.get("bankName"),
        account_name=account.get("accountName"),
        account_number=account.get("accountNumber"),
        expires_at=datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if expires_at
        else None,
    )

    db.add(intent)
    await db.commit()
    await db.refresh(intent)
    return intent


async def create_crypto_deposit_address(
    db: AsyncSession,
    *,
    job: Job,
    user: User,
) -> PaymentIntent:
    """Give the customer a Solana address to send USDC to."""
    existing = await _existing_intent(db, job.id, FundingRail.CRYPTO)
    if existing:
        return existing

    client = get_obiex_client()

    address = await client.create_deposit_address(
        unique_user_identifier=f"reach-user-{user.id}",
        currency=settings.OBiex_COLLECTION_CURRENCY,
        network="SOL",
    )

    intent = PaymentIntent(
        job_id=job.id,
        reference=_reference("fund", job.id),
        rail=FundingRail.CRYPTO,
        amount_kobo=to_kobo(job_budget_naira(job)),
        amount_payable_kobo=to_kobo(job_budget_naira(job)),
        status=PaymentStatus.PENDING,
        provider_reference=address.get("id"),
        deposit_address=address.get("value"),
        network=address.get("network"),
    )

    db.add(intent)
    await db.commit()
    await db.refresh(intent)
    return intent


async def create_fossapay_checkout(
    db: AsyncSession,
    *,
    job: Job,
    customer: FossaPayCustomer,
) -> PaymentIntent:
    """Open a FossaPay NGN checkout for the job."""
    existing = await _existing_intent(db, job.id, FundingRail.FOSSAPAY_CHECKOUT)
    if existing:
        return existing

    client = get_fossapay_client()
    amount_naira = job_budget_naira(job)
    reference = _reference("checkout", job.id)

    checkout = await client.create_checkout(
        amount_ngn=amount_naira,
        reference=reference,
        customer={},
    )

    account = checkout.get("account") or {}
    expires_at = checkout.get("expiresAt")

    intent = PaymentIntent(
        job_id=job.id,
        reference=reference,
        rail=FundingRail.FOSSAPAY_CHECKOUT,
        amount_kobo=to_kobo(amount_naira),
        amount_payable_kobo=to_kobo(
            Decimal(str(checkout.get("amountPayable", amount_naira)))
        ),
        status=PaymentStatus.PENDING,
        provider_checkout_id=checkout.get("id"),
        provider_customer_id=customer.provider_customer_id,
        bank_name=account.get("bankName"),
        account_name=account.get("accountName"),
        account_number=account.get("accountNumber"),
        expires_at=datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if expires_at
        else None,
    )

    db.add(intent)
    await db.commit()
    await db.refresh(intent)
    return intent


async def estimate_usdc_units(naira: int) -> int:
    """Convert naira into USDC base units using the live Obiex rate."""
    client = get_obiex_client()
    rates = await client.get_fiat_rates()

    rate = None
    for entry in rates:
        if str(entry.get("currency", "")).upper() in ("NGNX", "NGN"):
            rate = entry.get("buyRate")
            break

    if not rate:
        raise FundingError("No naira rate is available right now")

    return to_usdc_units(Decimal(naira) / Decimal(str(rate)))
