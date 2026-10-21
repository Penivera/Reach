import hashlib
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core import settings
from core.fossapay import FossaPayError, FossaPayNotConfigured, get_fossapay_client
from dependencies import get_db
from models import Job, PaymentIntent, Payout, WebhookEvent
from payment_amounts import AmountError, to_kobo
from payment_signatures import extract_raw_data, verify_signature
from schemas import (
    JobStatus,
    PaymentStatus,
    PayoutStatus,
    WebhookStatus,
)


router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class WebhookProcessingError(Exception):
    pass


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

    raw_data = extract_raw_data(raw_body)
    signature = request.headers.get("x-fossapay-signature", "")
    signature_valid = bool(raw_data) and verify_signature(
        raw_data, signature, secret
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

    # A rejected row may exist from an earlier invalid signature. A valid
    # signature is allowed to reprocess it.

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

        if event.status != WebhookStatus.IGNORED:
            event.status = WebhookStatus.PROCESSED
            event.processed_at = datetime.now(timezone.utc)

        await db.commit()

    except WebhookProcessingError as exc:
        event.status = WebhookStatus.FAILED
        event.last_error = str(exc)[:1000]
        await db.commit()
        raise HTTPException(status_code=503, detail=str(exc))

    return {"received": True}


async def _get_or_create_event(
    db: AsyncSession,
    *,
    event_id: str,
    event_type: str | None,
    reference: str | None,
    provider_object_id: str | None,
) -> WebhookEvent:
    event = (
        await db.execute(
            select(WebhookEvent).where(WebhookEvent.event_id == event_id)
        )
    ).scalar_one_or_none()

    if event:
        return event

    # A replay can change eventId. The provider object plus event type is the
    # business-level dedupe key; the eventType is still checked by the provider
    # lookup before any state changes.
    if provider_object_id and event_type:
        event = (
            await db.execute(
                select(WebhookEvent).where(
                    WebhookEvent.provider_object_id == provider_object_id,
                    WebhookEvent.event_type == event_type,
                )
            )
        ).scalar_one_or_none()
        if event:
            return event

    event = WebhookEvent(
        event_id=event_id,
        event_type=event_type,
        reference=reference,
        provider_object_id=provider_object_id,
        signature_valid=True,
        status=WebhookStatus.RECEIVED,
    )
    db.add(event)

    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        event = (
            await db.execute(
                select(WebhookEvent).where(WebhookEvent.event_id == event_id)
            )
        ).scalar_one_or_none()
        if not event:
            raise

    return event


async def _store_rejected_event(
    db: AsyncSession,
    *,
    event_id: str,
    event_type: str | None,
    reference: str | None,
    provider_object_id: str | None,
) -> None:
    event = WebhookEvent(
        event_id=event_id,
        event_type=event_type,
        reference=reference,
        provider_object_id=provider_object_id,
        signature_valid=False,
        status=WebhookStatus.REJECTED,
        last_error="Invalid signature",
    )
    db.add(event)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()


async def _sync_checkout(data: dict, db: AsyncSession) -> None:
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

        intent.status = PaymentStatus.PAID
        intent.paid_at = datetime.now(timezone.utc)

        job = (
            await db.execute(select(Job).where(Job.id == intent.job_id))
        ).scalar_one_or_none()

        if job and job.status == JobStatus.AWAITING_PAYMENT:
            job.status = JobStatus.IN_PROGRESS

        await db.commit()
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
            provider_payout = await get_fossapay_client().get_payout(
                str(payout_id)
            )
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

    status = provider_payout.get("status")

    if status == "completed":
        payout.status = PayoutStatus.COMPLETED
        payout.completed_at = datetime.now(timezone.utc)
        payout.failure_reason = None
    elif status == "failed":
        payout.status = PayoutStatus.FAILED
    elif status == "reversed":
        payout.status = PayoutStatus.REVERSED
    elif status in ("processing", "pending"):
        await db.commit()
        return
    else:
        raise WebhookProcessingError(f"Unexpected payout status: {status}")

    await db.commit()
