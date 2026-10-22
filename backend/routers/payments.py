"""Payment and funding endpoints.

Model 1 funds a task when it is created, and settles it on-chain. The
endpoints here cover the two halves of that:

* **funding** — the customer opens a collection (naira), a deposit address
  (USDC) or a checkout, and the money arrives;
* **release** — the creator approves the work and the relayer signs
  `approve_work`, which pays the provider on-chain.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.fossapay import FossaPayError, FossaPayNotConfigured
from core.obiex import ObiexError, ObiexNotConfigured
from core.relayer import RelayerError
from dependencies import get_current_user, get_db
from models import (
    FossaPayCustomer,
    Job,
    JobApplication,
    PaymentIntent,
    PaymentProfile,
    User,
)
from payment_validation import (
    PaymentProfileValidationError,
    normalize_phone_number,
    validate_single_name,
)
from schemas import (
    ApplicationStatus,
    ChainTransactionResponse,
    FossaPayAccountResponse,
    FundingIntentResponse,
    FundingRail,
    FundingStateResponse,
    FundingStatus,
    PaymentProfileResponse,
    PaymentProfileStateResponse,
    PaymentProfileUpsert,
    ProvisioningStatus,
)
from services import (
    ensure_customer_record,
    provision_user,
    provision_user_by_id,
)
from services.chain import (
    EscrowError,
    InsufficientEscrowFunds,
    RelayerUnavailable,
    release_task_escrow,
)
from services.treasury import TreasuryError
from services.funding import (
    FundingError,
    ProfileIncomplete,
    create_crypto_deposit_address,
    create_fossapay_checkout,
    create_obiex_collection,
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


async def _latest_intent(
    job_id: int, db: AsyncSession
) -> PaymentIntent | None:
    result = await db.execute(
        select(PaymentIntent)
        .where(PaymentIntent.job_id == job_id)
        .order_by(PaymentIntent.id.desc())
    )
    return result.scalars().first()


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

    if profile and not (profile.bvn or profile.nin):
        # Obiex needs a Nigerian identity number before it can open a
        # collection for a customer.
        missing_fields.append("bvn_or_nin")

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


def _funding_state(job: Job, intent: PaymentIntent | None) -> FundingStateResponse:
    return FundingStateResponse(
        job_id=job.id,
        job_status=job.status,
        funding_status=job.funding_status,
        payer_type=job.payer_type,
        onchain_task_id=job.onchain_task_id,
        onchain_tx_hash=job.onchain_tx_hash,
        onchain_status=job.onchain_status,
        intent=(
            FundingIntentResponse.model_validate(intent) if intent else None
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
                detail="Your payment account is already provisioned. Contact support to change your identity details.",
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
            detail="Your payment account is already provisioned. Contact support to change your date of birth.",
        )

    if profile:
        profile.middle_name = data.middle_name
        profile.date_of_birth = data.date_of_birth
        profile.address = data.address
        profile.city = data.city
        profile.country = data.country
        profile.bvn = data.bvn
        profile.nin = data.nin
        profile.bank_code = data.bank_code
        profile.bank_account_number = data.bank_account_number
        profile.bank_account_name = data.bank_account_name
    else:
        profile = PaymentProfile(
            user_id=current_user.id,
            middle_name=data.middle_name,
            date_of_birth=data.date_of_birth,
            address=data.address,
            city=data.city,
            country=data.country,
            bvn=data.bvn,
            nin=data.nin,
            bank_code=data.bank_code,
            bank_account_number=data.bank_account_number,
            bank_account_name=data.bank_account_name,
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


@router.post("/jobs/{job_id}/collection", response_model=FundingIntentResponse)
async def create_job_collection(
    job_id: int,
    rail: FundingRail = FundingRail.OBIEX_FIAT,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Open a payment for a task.

    Model 1 funds the escrow when the task is created, so this is called
    while the job is still waiting for its funding.
    """
    job = (
        await db.execute(select(Job).where(Job.id == job_id))
    ).scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the job owner can pay")

    if job.funding_status == FundingStatus.FUNDED:
        raise HTTPException(
            status_code=400,
            detail="This task is already funded",
        )

    profile = await _get_profile(current_user.id, db)
    customer = await _get_customer(current_user.id, db)

    if not profile:
        raise HTTPException(
            status_code=400,
            detail="Complete your payment profile first",
        )

    try:
        if rail == FundingRail.CRYPTO:
            intent = await create_crypto_deposit_address(
                db, job=job, user=current_user
            )
        elif rail == FundingRail.FOSSAPAY_CHECKOUT:
            if not customer or customer.status != ProvisioningStatus.PROVISIONED:
                raise HTTPException(
                    status_code=400,
                    detail="Complete your payment profile first",
                )
            intent = await create_fossapay_checkout(
                db, job=job, customer=customer
            )
        else:
            intent = await create_obiex_collection(
                db, job=job, user=current_user, profile=profile
            )
    except HTTPException:
        raise
    except ProfileIncomplete as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except FundingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ObiexNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ObiexError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except FossaPayNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except FossaPayError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    job.funding_status = FundingStatus.PENDING

    await db.commit()
    await db.refresh(intent)

    return FundingIntentResponse.model_validate(intent)


@router.get("/jobs/{job_id}", response_model=FundingStateResponse)
async def get_job_funding(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    job = await _get_job_for_participant(job_id, current_user.id, db)
    intent = await _latest_intent(job.id, db)
    return _funding_state(job, intent)


@router.post("/jobs/{job_id}/release", response_model=ChainTransactionResponse)
async def release_job_payment(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Approve the work and release the escrow to the provider.

    The relayer signs `approve_work`; the program moves the escrow to the
    provider's token account.
    """
    job = (
        await db.execute(select(Job).where(Job.id == job_id))
    ).scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the job owner can release")

    if job.funding_status != FundingStatus.FUNDED:
        raise HTTPException(
            status_code=400,
            detail="This task has no funded escrow to release",
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

    provider = await db.get(User, application.applicant_id)

    provider_address = getattr(provider, "onchain_address", None)

    if not provider_address:
        raise HTTPException(
            status_code=400,
            detail=(
                "The provider has not added a Solana address yet, so the "
                "payment cannot be released"
            ),
        )

    try:
        transaction = await release_task_escrow(
            db,
            job,
            provider_address=provider_address,
        )
    except RelayerUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except InsufficientEscrowFunds as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except EscrowError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RelayerError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return ChainTransactionResponse.model_validate(transaction)


@router.post("/treasury/top-up")
async def top_up_treasury(
    required_units: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Move USDC from the provider into the on-chain escrow float.

    Normally the treasury tops itself up when a collection arrives and the
    float is short. This endpoint is for moving a balance deliberately, for
    example after a collection settles without anyone waiting on it.
    """
    from services import treasury
    from services.chain import retry_pending_fundings

    try:
        plan = await treasury.plan_top_up(required_units=required_units)
    except (RelayerUnavailable, ObiexNotConfigured, ObiexError) as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    if plan["withdraw_units"]:
        try:
            await treasury.request_withdrawal(
                db, amount_units=plan["withdraw_units"]
            )
        except TreasuryError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    funded = await retry_pending_fundings(db)

    return {
        "onchain_units": plan["onchain_units"],
        "provider_units": plan["provider_units"],
        "withdraw_units": plan["withdraw_units"],
        "funded_jobs": [job.id for job in funded],
    }


@router.get("/jobs/{job_id}/transactions", response_model=list[ChainTransactionResponse])
async def list_job_chain_transactions(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """The on-chain transactions recorded for a task."""
    from models import ChainTransaction

    job = await _get_job_for_participant(job_id, current_user.id, db)

    result = await db.execute(
        select(ChainTransaction)
        .where(ChainTransaction.job_id == job.id)
        .order_by(ChainTransaction.id.desc())
    )

    return [
        ChainTransactionResponse.model_validate(record)
        for record in result.scalars().all()
    ]
