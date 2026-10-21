from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import settings
from core.fossapay import FossaPayError, FossaPayNotConfigured, get_fossapay_client
from dependencies import get_current_user, get_db
from models import (
    FossaPayCustomer,
    Job,
    JobApplication,
    PaymentIntent,
    PaymentProfile,
    Payout,
    User,
)
from payment_amounts import AmountError, commission_kobo, to_kobo, to_ngn
from payment_validation import (
    PaymentProfileValidationError,
    normalize_phone_number,
    validate_single_name,
)
from schemas import (
    ApplicationStatus,
    FossaPayAccountResponse,
    JobStatus,
    PaymentIntentResponse,
    PaymentProfileResponse,
    PaymentProfileStateResponse,
    PaymentProfileUpsert,
    PaymentStatus,
    PayoutResponse,
    PayoutStatus,
    ProvisioningStatus,
)
from services import (
    ensure_customer_record,
    provision_user,
    provision_user_by_id,
)


router = APIRouter(prefix="/payments", tags=["payments"])


async def _get_profile(user_id: int, db: AsyncSession) -> PaymentProfile | None:
    result = await db.execute(
        select(PaymentProfile).where(PaymentProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def _get_customer(user_id: int, db: AsyncSession) -> FossaPayCustomer | None:
    result = await db.execute(
        select(FossaPayCustomer).where(FossaPayCustomer.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def _get_job_for_participant(
    job_id: int,
    user_id: int,
    db: AsyncSession,
) -> Job:
    job = (
        await db.execute(select(Job).where(Job.id == job_id))
    ).scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.owner_id != user_id:
        application = (
            await db.execute(
                select(JobApplication).where(
                    JobApplication.job_id == job.id,
                    JobApplication.applicant_id == user_id,
                    JobApplication.status == ApplicationStatus.ACCEPTED,
                )
            )
        ).scalar_one_or_none()

        if not application:
            raise HTTPException(status_code=403, detail="Not allowed")

    return job


def _state(profile, customer, user) -> PaymentProfileStateResponse:
    missing_fields: list[str] = []

    if not profile:
        missing_fields = ["date_of_birth", "address", "city", "country"]

    try:
        validate_single_name(user.first_name, "first_name")
    except PaymentProfileValidationError:
        missing_fields.append("first_name")

    try:
        validate_single_name(user.last_name, "last_name")
    except PaymentProfileValidationError:
        missing_fields.append("last_name")

    try:
        normalize_phone_number(user.phone_number)
    except PaymentProfileValidationError:
        missing_fields.append("phone_number")

    return PaymentProfileStateResponse(
        profile_completed=profile is not None,
        can_pay=bool(
            profile
            and customer
            and customer.status == ProvisioningStatus.PROVISIONED
        ),
        missing_fields=missing_fields,
        profile=(
            PaymentProfileResponse.model_validate(profile)
            if profile
            else None
        ),
        provisioning=(
            FossaPayAccountResponse.model_validate(customer)
            if customer
            else None
        ),
    )


@router.get("/profile", response_model=PaymentProfileStateResponse)
async def get_payment_profile(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    profile = await _get_profile(current_user.id, db)
    customer = await _get_customer(current_user.id, db)
    return _state(profile, customer, current_user)


@router.put("/profile", response_model=PaymentProfileStateResponse)
async def upsert_payment_profile(
    data: PaymentProfileUpsert,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    first_name = data.first_name if data.first_name is not None else current_user.first_name
    last_name = data.last_name if data.last_name is not None else current_user.last_name
    phone_number = (
        data.phone_number if data.phone_number is not None else current_user.phone_number
    )

    try:
        first_name = validate_single_name(first_name, "first_name")
        last_name = validate_single_name(last_name, "last_name")
        phone_number = normalize_phone_number(phone_number)
    except PaymentProfileValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    customer = await _get_customer(current_user.id, db)

    if customer and customer.status == ProvisioningStatus.PROVISIONED:
        if (
            first_name != current_user.first_name
            or last_name != current_user.last_name
            or phone_number != normalize_phone_number(current_user.phone_number)
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your FossaPay account is already provisioned. Contact support to change your identity details.",
            )

    current_user.first_name = first_name
    current_user.last_name = last_name
    current_user.phone_number = phone_number

    profile = await _get_profile(current_user.id, db)

    if (
        customer
        and customer.status == ProvisioningStatus.PROVISIONED
        and profile
        and data.date_of_birth != profile.date_of_birth
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your FossaPay account is already provisioned. Contact support to change your date of birth.",
        )

    if profile:
        profile.middle_name = data.middle_name
        profile.date_of_birth = data.date_of_birth
        profile.address = data.address
        profile.city = data.city
        profile.country = data.country
    else:
        profile = PaymentProfile(
            user_id=current_user.id,
            middle_name=data.middle_name,
            date_of_birth=data.date_of_birth,
            address=data.address,
            city=data.city,
            country=data.country,
        )
        db.add(profile)

    try:
        await db.commit()
        await db.refresh(profile)
    except Exception:
        await db.rollback()
        raise

    customer = await ensure_customer_record(current_user.id, db)
    background_tasks.add_task(provision_user_by_id, current_user.id)

    return _state(profile, customer, current_user)


@router.post("/profile/provision", response_model=PaymentProfileStateResponse)
async def retry_payment_profile_provisioning(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    profile = await _get_profile(current_user.id, db)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complete your payment profile first",
        )

    customer = await provision_user(current_user, db)
    return _state(profile, customer, current_user)


def _parse_expiry(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


@router.post("/jobs/{job_id}/checkout", response_model=PaymentIntentResponse)
async def create_job_checkout(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    job = (
        await db.execute(select(Job).where(Job.id == job_id))
    ).scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the job owner can pay")

    if job.status != JobStatus.AWAITING_PAYMENT:
        raise HTTPException(
            status_code=400,
            detail="Accept an applicant before creating a payment",
        )

    profile = await _get_profile(current_user.id, db)
    customer = await _get_customer(current_user.id, db)

    if (
        not profile
        or not customer
        or customer.status != ProvisioningStatus.PROVISIONED
    ):
        raise HTTPException(
            status_code=400,
            detail="Complete your payment profile first",
        )

    application = (
        await db.execute(
            select(JobApplication).where(
                JobApplication.job_id == job.id,
                JobApplication.status == ApplicationStatus.ACCEPTED,
            )
        )
    ).scalar_one_or_none()

    if not application:
        raise HTTPException(status_code=400, detail="No accepted applicant")

    now = datetime.now(timezone.utc)
    existing = (
        await db.execute(
            select(PaymentIntent)
            .where(
                PaymentIntent.job_id == job.id,
                PaymentIntent.status == PaymentStatus.PENDING,
            )
            .order_by(PaymentIntent.id.desc())
        )
    ).scalars().first()

    if existing:
        if existing.expires_at is None or existing.expires_at > now:
            return existing
        existing.status = PaymentStatus.EXPIRED
        await db.commit()

    try:
        amount_kobo = to_kobo(application.proposed_price)
        amount_ngn = to_ngn(amount_kobo)
    except AmountError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if amount_kobo < settings.MIN_ESCROW_KOBO:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum job payment is ₦{settings.MIN_ESCROW_KOBO // 100:,}",
        )

    reference = f"job-{job.id}-{uuid4().hex[:12]}"

    try:
        checkout = await get_fossapay_client().create_checkout(
            amount_ngn=amount_ngn,
            reference=reference,
            customer={
                "name": f"{current_user.first_name} {current_user.last_name}".strip(),
                "email": current_user.email,
                "phoneNumber": current_user.phone_number,
            },
        )
    except FossaPayNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except FossaPayError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    account = checkout.get("account") or {}

    try:
        amount_payable_kobo = to_kobo(
            checkout.get("amountPayable") or amount_ngn
        )
    except AmountError:
        amount_payable_kobo = amount_kobo

    intent = PaymentIntent(
        job_id=job.id,
        reference=reference,
        amount_kobo=amount_kobo,
        amount_payable_kobo=amount_payable_kobo,
        status=PaymentStatus.PENDING,
        provider_checkout_id=str(checkout["id"]),
        bank_name=account.get("bankName"),
        account_name=account.get("accountName"),
        account_number=account.get("accountNumber"),
        expires_at=_parse_expiry(checkout.get("expiresAt")),
    )

    db.add(intent)

    try:
        await db.commit()
        await db.refresh(intent)
    except Exception:
        await db.rollback()
        raise

    return intent


@router.get("/jobs/{job_id}", response_model=PaymentIntentResponse)
async def get_job_payment(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    job = await _get_job_for_participant(job_id, current_user.id, db)

    intent = (
        await db.execute(
            select(PaymentIntent)
            .where(PaymentIntent.job_id == job.id)
            .order_by(PaymentIntent.id.desc())
        )
    ).scalars().first()

    if not intent:
        raise HTTPException(status_code=404, detail="No payment found")

    return intent


@router.post("/jobs/{job_id}/release", response_model=PayoutResponse)
async def release_job_payment(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    job = (
        await db.execute(select(Job).where(Job.id == job_id))
    ).scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the job owner can release funds")

    if not (job.client_completed and job.worker_completed):
        raise HTTPException(
            status_code=400,
            detail="Both parties must confirm completion before release",
        )

    intent = (
        await db.execute(
            select(PaymentIntent)
            .where(
                PaymentIntent.job_id == job.id,
                PaymentIntent.status == PaymentStatus.PAID,
            )
            .order_by(PaymentIntent.id.desc())
        )
    ).scalars().first()

    if not intent:
        raise HTTPException(status_code=400, detail="Job has not been funded")

    existing = (
        await db.execute(
            select(Payout).where(Payout.payment_intent_id == intent.id)
        )
    ).scalar_one_or_none()

    if existing:
        return existing

    application = (
        await db.execute(
            select(JobApplication).where(
                JobApplication.job_id == job.id,
                JobApplication.status == ApplicationStatus.ACCEPTED,
            )
        )
    ).scalar_one_or_none()

    if not application:
        raise HTTPException(status_code=400, detail="No accepted applicant")

    provider = await db.get(User, application.applicant_id)
    provider_account = (
        await _get_customer(provider.id, db) if provider else None
    )

    if (
        not provider_account
        or provider_account.status != ProvisioningStatus.PROVISIONED
        or not provider_account.account_number
        or not provider_account.account_name
        or not provider_account.bank_name
        or not provider_account.bank_code
    ):
        raise HTTPException(
            status_code=400,
            detail="Provider's FossaPay wallet is not ready",
        )

    fee_kobo = commission_kobo(intent.amount_kobo, settings.PLATFORM_FEE_BPS)
    provider_payout_kobo = intent.amount_kobo - fee_kobo

    if provider_payout_kobo <= 0:
        raise HTTPException(status_code=400, detail="Payout amount is too small")

    reference = f"payout-job-{job.id}-{intent.id}"

    payout = Payout(
        payment_intent_id=intent.id,
        payee_id=provider.id,
        reference=reference,
        amount_kobo=intent.amount_kobo,
        commission_kobo=fee_kobo,
        provider_payout_kobo=provider_payout_kobo,
        status=PayoutStatus.PROCESSING,
    )
    db.add(payout)

    try:
        await db.commit()
        await db.refresh(payout)
    except Exception:
        await db.rollback()
        raise

    try:
        result = await get_fossapay_client().create_payout(
            amount_ngn=to_ngn(provider_payout_kobo),
            reference=reference,
            destination={
                "bank_code": provider_account.bank_code,
                "bank_name": provider_account.bank_name,
                "account_name": provider_account.account_name,
                "account_number": provider_account.account_number,
            },
        )
    except FossaPayNotConfigured as exc:
        payout.status = PayoutStatus.FAILED
        payout.failure_reason = str(exc)
        await db.commit()
        raise HTTPException(status_code=503, detail=str(exc))
    except FossaPayError as exc:
        payout.status = PayoutStatus.FAILED
        payout.failure_reason = str(exc)
        await db.commit()
        raise HTTPException(status_code=502, detail=str(exc))

    payout.provider_payout_id = str(result["id"])
    provider_status = result.get("status")

    if provider_status == "completed":
        payout.status = PayoutStatus.COMPLETED
        payout.completed_at = datetime.now(timezone.utc)
    elif provider_status == "failed":
        payout.status = PayoutStatus.FAILED
    elif provider_status == "reversed":
        payout.status = PayoutStatus.REVERSED

    await db.commit()
    await db.refresh(payout)
    return payout


@router.get("/jobs/{job_id}/payout", response_model=PayoutResponse)
async def get_job_payout(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    job = await _get_job_for_participant(job_id, current_user.id, db)

    payout = (
        await db.execute(
            select(Payout)
            .join(PaymentIntent, PaymentIntent.id == Payout.payment_intent_id)
            .where(PaymentIntent.job_id == job.id)
            .order_by(Payout.id.desc())
        )
    ).scalars().first()

    if not payout:
        raise HTTPException(status_code=404, detail="No payout found")

    return payout
