"""Webhook receivers.

Two providers deliver money events:

* **FossaPay** — NGN checkouts (`checkout.completed`) and payouts.
* **Obiex** — fiat collections (`COLLECTION`), crypto deposits (`DEPOSIT`) and
  treasury withdrawals (`WITHDRAWAL`).

Both are verified before anything is trusted, both are deduplicated, and both
end in the same place: the task's escrow is locked on Solana.
"""

import hashlib
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core import settings
from core.fossapay import FossaPayError, FossaPayNotConfigured, get_fossapay_client
from core.obiex import verify_webhook_signature
from dependencies import get_db
from models import Job, PaymentIntent, Payout, WebhookEvent
from payment_amounts import AmountError, to_kobo
from payment_signatures import verify_fossapay_event
from schemas import (
    FundingStatus,
    PaymentStatus,
    PayoutStatus,
    TreasuryTransferStatus,
    WebhookStatus,
)
from services import treasury
from services.chain import (
    EscrowError,
    InsufficientEscrowFunds,
    RelayerUnavailable,
    fund_task_escrow,
    retry_pending_fundings,
)
from services.funding import estimate_usdc_units, to_usdc_units


router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class WebhookProcessingError(Exception):
    pass


async def _get_or_create_event(
    db: AsyncSession,
    *,
    event_id: str,
    event_type: str | None,
    reference: str | None,
    provider_object_id: str | None,
) -> WebhookEvent:
    result = await db.execute(
        select(WebhookEvent).where(WebhookEvent.event_id == event_id)
    )
    event = result.scalar_one_or_none()

    if event:
        return event

    event = WebhookEvent(
        event_id=event_id,
        event_type=event_type,
        reference=reference,
        provider_object_id=provider_object_id,
    )
    db.add(event)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        result = await db.execute(
            select(WebhookEvent).where(WebhookEvent.event_id == event_id)
        )
        return result.scalar_one_or_none()

    await db.refresh(event)
    return event


async def _store_rejected_event(
    db: AsyncSession,
    *,
    event_id: str,
    event_type: str | None,
    reference: str | None,
    provider_object_id: str | None,
):
    event = WebhookEvent(
        event_id=event_id,
        event_type=event_type,
        reference=reference,
        provider_object_id=provider_object_id,
        signature_valid=False,
        status=WebhookStatus.REJECTED,
    )
    db.add(event)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()


async def _fund_intent(
    db: AsyncSession,
    intent: PaymentIntent,
    *,
    usdc_units: int,
) -> None:
    """Mark a funding intent paid and lock the task's escrow on-chain."""
    job = await db.get(Job, intent.job_id)

    if job is None:
        raise WebhookProcessingError("The job for this payment no longer exists")

    if intent.status == PaymentStatus.PAID and job.funding_status == FundingStatus.FUNDED:
        return

    intent.status = PaymentStatus.PAID
    intent.paid_at = datetime.now(timezone.utc)
    intent.usdc_amount = usdc_units

    job.funding_status = FundingStatus.PAID

    await db.commit()

    try:
        await fund_task_escrow(
            db,
            job,
            funded_units=usdc_units,
            creation_fee_bps=settings.REACH_CREATION_FEE_BPS,
            tag=(job.title or "")[:30],
            desc=(job.description or "")[:200],
        )
    except InsufficientEscrowFunds as exc:
        # The money is safe with the provider; the escrow waits for the
        # platform's USDC float to be replenished.
        job.funding_status = FundingStatus.PAID
        intent.failure_reason = str(exc)[:1000]
        await db.commit()
    except RelayerUnavailable as exc:
        job.funding_status = FundingStatus.PAID
        intent.failure_reason = str(exc)[:1000]
        await db.commit()
    except EscrowError as exc:
        job.funding_status = FundingStatus.PAID
        intent.failure_reason = str(exc)[:1000]
        await db.commit()
    except Exception as exc:  # pragma: no cover - defensive
        job.funding_status = FundingStatus.PAID
        intent.failure_reason = str(exc)[:1000]
        await db.commit()
        raise


@router.post("/fossapay")
async def fossapay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    raw_body = await request.body()

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

    secret = settings.FOSSAPAY_WEBHOOK_SECRET
    if not secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    data = payload["data"]
    event_type = payload.get("eventType")
    reference = data.get("reference")
    provider_object_id = data.get("checkoutId") or data.get("payoutId")
    event_id = payload.get("eventId") or hashlib.sha256(raw_body).hexdigest()

    signature_valid, _scheme = verify_fossapay_event(
        raw_body, dict(request.headers), secret
    )

    if not signature_valid:
        await _store_rejected_event(
            db,
            event_id=event_id,
            event_type=event_type,
            reference=reference,
            provider_object_id=provider_object_id,
        )
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = await _get_or_create_event(
        db,
        event_id=event_id,
        event_type=event_type,
        reference=reference,
        provider_object_id=provider_object_id,
    )

    if event.status in (
        WebhookStatus.PROCESSED,
        WebhookStatus.IGNORED,
    ):
        return {"received": True}

    event.signature_valid = True
    event.status = WebhookStatus.RECEIVED
    event.last_error = None

    try:
        if data.get("checkoutId"):
            await _sync_checkout(data, db)
        elif data.get("payoutId") or (
            isinstance(reference, str) and reference.startswith("payout-")
        ):
            await _sync_payout(data, payout_reference=reference, db=db)
        else:
            event.status = WebhookStatus.IGNORED

        event.status = WebhookStatus.PROCESSED
        event.processed_at = datetime.now(timezone.utc)
        await db.commit()

    except WebhookProcessingError as exc:
        event.status = WebhookStatus.FAILED
        event.last_error = str(exc)[:1000]
        await db.commit()
        # Tell the provider to retry: the money may still be settling.
        raise HTTPException(status_code=503, detail=str(exc))

    return {"received": True}


async def _sync_checkout(data: dict, db: AsyncSession) -> None:
    """A FossaPay checkout reached a terminal state."""
    intent = None

    if data.get("reference"):
        intent = (
            await db.execute(
                select(PaymentIntent).where(
                    PaymentIntent.reference == data["reference"]
                )
            )
        ).scalar_one_or_none()

    if not intent and data.get("checkoutId"):
        intent = (
            await db.execute(
                select(PaymentIntent).where(
                    PaymentIntent.provider_checkout_id == str(data["checkoutId"])
                )
            )
        ).scalar_one_or_none()

    if not intent:
        raise WebhookProcessingError("Unknown checkout")

    if intent.status == PaymentStatus.PAID:
        return

    if not intent.provider_checkout_id:
        raise WebhookProcessingError("Payment intent has no checkout id")

    if data.get("checkoutId") and str(data["checkoutId"]) != intent.provider_checkout_id:
        raise WebhookProcessingError("Checkout id does not match")

    try:
        checkout = await get_fossapay_client().get_checkout(
            intent.provider_checkout_id
        )
    except (FossaPayNotConfigured, FossaPayError) as exc:
        raise WebhookProcessingError(str(exc))

    status = checkout.get("status")

    if checkout.get("reference") and checkout["reference"] != intent.reference:
        raise WebhookProcessingError("Provider reference does not match")

    if status == "completed":
        if checkout.get("amountPayable") is not None:
            try:
                amount_payable = to_kobo(checkout["amountPayable"])
            except AmountError as exc:
                raise WebhookProcessingError(str(exc))

            if amount_payable != intent.amount_payable_kobo:
                intent.status = PaymentStatus.FAILED
                await db.commit()
                return

        # The checkout collected naira. The platform converts it with Obiex
        # and escrows the USDC equivalent from its float.
        naira = intent.amount_kobo // 100
        units = await estimate_usdc_units(naira)
        await _fund_intent(db, intent, usdc_units=units)
        return

    if status in ("failed", "expired", "reversed"):
        intent.status = {
            "failed": PaymentStatus.FAILED,
            "expired": PaymentStatus.EXPIRED,
            "reversed": PaymentStatus.REVERSED,
        }[status]
        await db.commit()
        return

    raise WebhookProcessingError(f"Unexpected checkout status: {status}")


async def _sync_payout(
    data: dict,
    *,
    payout_reference: str | None,
    db: AsyncSession,
) -> None:
    payout = None

    if payout_reference:
        payout = (
            await db.execute(
                select(Payout).where(Payout.reference == payout_reference)
            )
        ).scalar_one_or_none()

    if not payout and data.get("payoutId"):
        payout = (
            await db.execute(
                select(Payout).where(
                    Payout.provider_payout_id == str(data["payoutId"])
                )
            )
        ).scalar_one_or_none()

    if not payout:
        raise WebhookProcessingError("Unknown payout")

    if payout.status == PayoutStatus.COMPLETED:
        return

    payout_id = payout.provider_payout_id or data.get("payoutId")

    try:
        if payout_id:
            provider_payout = await get_fossapay_client().get_payout(str(payout_id))
        else:
            provider_payout = await get_fossapay_client().get_payout_by_reference(
                payout.reference
            )
    except (FossaPayNotConfigured, FossaPayError) as exc:
        raise WebhookProcessingError(str(exc))

    if (
        provider_payout.get("reference")
        and provider_payout["reference"] != payout.reference
    ):
        raise WebhookProcessingError("Provider payout reference does not match")

    if not payout.provider_payout_id and provider_payout.get("id"):
        payout.provider_payout_id = str(provider_payout["id"])

    provider_status = provider_payout.get("status")

    if provider_status == "completed":
        payout.status = PayoutStatus.COMPLETED
        payout.completed_at = datetime.now(timezone.utc)
        await db.commit()
        return

    if provider_status in ("failed", "reversed"):
        payout.status = (
            PayoutStatus.FAILED if provider_status == "failed" else PayoutStatus.REVERSED
        )
        payout.failure_reason = str(provider_payout.get("message") or provider_status)[
            :1000
        ]
        await db.commit()
        return

    raise WebhookProcessingError(f"Unexpected payout status: {provider_status}")


@router.post("/obiex")
async def obiex_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Receive Obiex collection, deposit and withdrawal events."""
    raw_body = await request.body()

    secret = settings.OBiex_WEBHOOK_SECRET
    if not secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    signature = request.headers.get("x-obiex-signature", "")

    if not verify_webhook_signature(raw_body, signature, secret):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

    event_type = payload.get("type")
    reference = payload.get("reference")
    status = payload.get("status")

    event_id = (
        f"obiex:{reference}:{event_type}:{status}"
        if reference
        else hashlib.sha256(raw_body).hexdigest()
    )

    event = await _get_or_create_event(
        db,
        event_id=event_id,
        event_type=event_type,
        reference=reference,
        provider_object_id=reference,
    )

    if event.status in (WebhookStatus.PROCESSED, WebhookStatus.IGNORED):
        return {"received": True}

    event.signature_valid = True
    event.status = WebhookStatus.RECEIVED
    event.last_error = None

    try:
        if event_type == "COLLECTION":
            await _sync_collection(payload, db)
        elif event_type == "DEPOSIT":
            await _sync_deposit(payload, db)
        elif event_type == "WITHDRAWAL":
            await _sync_withdrawal(payload, db)
        else:
            event.status = WebhookStatus.IGNORED

        event.status = WebhookStatus.PROCESSED
        event.processed_at = datetime.now(timezone.utc)
        await db.commit()

    except WebhookProcessingError as exc:
        event.status = WebhookStatus.FAILED
        event.last_error = str(exc)[:1000]
        await db.commit()
        raise HTTPException(status_code=503, detail=str(exc))

    return {"received": True}


async def _sync_collection(payload: dict, db: AsyncSession) -> None:
    """A fiat collection settled, or was held for review."""
    reference = payload.get("reference")
    status = payload.get("status")

    if not reference:
        raise WebhookProcessingError("The collection has no reference")

    intent = (
        await db.execute(
            select(PaymentIntent).where(PaymentIntent.provider_reference == reference)
        )
    ).scalar_one_or_none()

    if not intent:
        raise WebhookProcessingError("Unknown collection")

    if status == "HELD":
        intent.status = PaymentStatus.HELD
        intent.failure_reason = (
            "The payer's name does not match the account holder. "
            "Support is reviewing this payment."
        )
        job = await db.get(Job, intent.job_id)
        if job:
            job.funding_status = FundingStatus.HELD
        await db.commit()
        return

    if status != "COMPLETED":
        return

    target_amount = payload.get("targetAmount")
    if target_amount is None:
        raise WebhookProcessingError("The collection has no settled amount")

    units = to_usdc_units(target_amount)
    await _fund_intent(db, intent, usdc_units=units)


async def _sync_deposit(payload: dict, db: AsyncSession) -> None:
    """A customer deposited USDC into their Solana deposit address."""
    address = payload.get("address")
    status = payload.get("status")

    if not address:
        raise WebhookProcessingError("The deposit has no address")

    if status != "CONFIRMED":
        return

    intent = (
        await db.execute(
            select(PaymentIntent).where(PaymentIntent.deposit_address == address)
        )
    ).scalar_one_or_none()

    if not intent:
        # Not every deposit belongs to a task; the treasury deposits land
        # on the same rail.
        return

    amount = payload.get("amount")
    if amount is None:
        raise WebhookProcessingError("The deposit has no amount")

    units = to_usdc_units(amount)
    await _fund_intent(db, intent, usdc_units=units)


async def _sync_withdrawal(payload: dict, db: AsyncSession) -> None:
    """A treasury withdrawal from the provider landed (or failed).

    The escrow float is topped up from the provider's balance, so a completed
    withdrawal is what lets the waiting escrows be locked.
    """
    reference = payload.get("reference")
    status = payload.get("status")

    if not reference:
        raise WebhookProcessingError("The withdrawal has no reference")

    transfer = await treasury.get_transfer(db, reference)

    if transfer is None:
        # Not one of ours (a treasury sweep we did not record, say).
        return

    if transfer.status == TreasuryTransferStatus.CONFIRMED:
        return

    if status == "SUCCESSFUL":
        await treasury.mark_transfer(
            db,
            transfer,
            status=TreasuryTransferStatus.CONFIRMED,
            tx_hash=payload.get("hash"),
        )
    elif status == "FAILED":
        await treasury.mark_transfer(
            db,
            transfer,
            status=TreasuryTransferStatus.FAILED,
            tx_hash=payload.get("hash"),
        )
    else:
        # Still in flight.
        await treasury.mark_transfer(
            db,
            transfer,
            status=TreasuryTransferStatus.SUBMITTED,
            tx_hash=payload.get("hash"),
        )
        return

    # The float should cover the escrows that were waiting for it.
    await retry_pending_fundings(db)
