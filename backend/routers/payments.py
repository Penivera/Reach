"""Payment and funding endpoints.

Model 1 funds a task when it is created, and settles it on-chain. The
endpoints here cover the two halves of that:

* **funding** — the customer opens a collection (naira), a deposit address
  (USDC) or a checkout, and the money arrives;
* **release** — the creator approves the work and the relayer signs
  `approve_work`, which pays the provider on-chain.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, status
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
    JobStatus,
    OffRampBankResponse,
    OffRampCreateRequest,
    OffRampQuoteRequest,
    OffRampQuoteResponse,
    OffRampWithdrawalResponse,
    PaymentProfileResponse,
    PaymentProfileStateResponse,
    PaymentProfileUpsert,
    ProvisioningStatus,
    UserRole,
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
from services import offramp
from services.funding import (
    FundingError,
    ProfileIncomplete,
    create_crypto_deposit_address,
    create_fossapay_checkout,
    create_obiex_collection,
    latest_pending_intent,
    missing_fields_for_rail,
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


@router.get("/requirements")
async def get_payment_requirements(
    rail: FundingRail = FundingRail.OBIEX_FIAT,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """What the customer has to provide before this rail can be opened.

    The payment profile is collected when the customer wants to pay, so the
    frontend calls this when they tap pay and asks for what is missing.
    """
    profile = await _get_profile(current_user.id, db)
    customer = await _get_customer(current_user.id, db)

    missing = missing_fields_for_rail(
        user=current_user,
        profile=profile,
        rail=rail,
        customer_provisioned=bool(
            customer and customer.status == ProvisioningStatus.PROVISIONED
        ),
    )

    return {
        "rail": rail,
        "can_pay": not missing,
        "missing_fields": missing,
        "profile_completed": profile is not None,
    }


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

    if job.funding_status in (FundingStatus.PAID, FundingStatus.HELD):
        raise HTTPException(
            status_code=400,
            detail="This task already has a payment being processed",
        )

    if job.status in (JobStatus.COMPLETED, JobStatus.CANCELLED):
        raise HTTPException(
            status_code=400,
            detail="This task is closed and cannot be funded",
        )

    pending = await latest_pending_intent(db, job.id)
    if pending is not None and pending.rail != rail:
        raise HTTPException(
            status_code=409,
            detail=(
                "A payment is already open for this task on another rail. "
                "Finish or cancel it before choosing a different payment method."
            ),
        )

    profile = await _get_profile(current_user.id, db)
    customer = await _get_customer(current_user.id, db)

    missing = missing_fields_for_rail(
        user=current_user,
        profile=profile,
        rail=rail,
        customer_provisioned=bool(
            customer and customer.status == ProvisioningStatus.PROVISIONED
        ),
    )

    if missing:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "We need a few more details before you can pay",
                "missing_fields": missing,
            },
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
                    detail={
                        "message": "Your payment account is not ready yet",
                        "missing_fields": ["provisioning"],
                    },
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


# -- provider naira off-ramp ------------------------------------------------


def _offramp_error(exc: offramp.OffRampError) -> HTTPException:
    if isinstance(exc, offramp.OffRampDisabled):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, offramp.OffRampNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, offramp.OffRampConflict):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, offramp.OffRampNotReady):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, offramp.OffRampAmountError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


def _require_admin(user: User) -> None:
    if getattr(user, "role", None) != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/offramp/banks", response_model=list[OffRampBankResponse])
async def list_offramp_banks(current_user=Depends(get_current_user)):
    """Nigerian banks Obiex can pay a naira withdrawal to."""
    try:
        return await offramp.list_banks()
    except offramp.OffRampError as exc:
        raise _offramp_error(exc)
    except (ObiexError, ObiexNotConfigured) as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.post("/offramp/quote", response_model=OffRampQuoteResponse)
async def quote_offramp(
    data: OffRampQuoteRequest,
    current_user=Depends(get_current_user),
):
    """Show the indicative naira amount before the provider sends USDC."""
    try:
        return await offramp.quote_offramp(data.amount_usdc)
    except offramp.OffRampError as exc:
        raise _offramp_error(exc)
    except (ObiexError, ObiexNotConfigured) as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.post("/offramp/reconcile")
async def reconcile_offramp(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Expire stale deposit requests and poll in-flight bank payouts."""
    _require_admin(current_user)
    try:
        return await offramp.reconcile(db)
    except offramp.OffRampError as exc:
        raise _offramp_error(exc)
    except (ObiexError, ObiexNotConfigured) as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.post("/offramp", response_model=OffRampWithdrawalResponse, status_code=201)
async def create_offramp(
    data: OffRampCreateRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a unique USDC deposit address and a pending naira payout."""
    try:
        return await offramp.create_withdrawal(
            db,
            user=current_user,
            amount_usdc=data.amount_usdc,
            bank_code=data.bank_code,
            bank_account_number=data.bank_account_number,
            bank_account_name=data.bank_account_name,
            idempotency_key=idempotency_key,
        )
    except offramp.OffRampError as exc:
        raise _offramp_error(exc)
    except (ObiexError, ObiexNotConfigured) as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/offramp", response_model=list[OffRampWithdrawalResponse])
async def list_offramp(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await offramp.list_withdrawals(db, user_id=current_user.id)


@router.get("/offramp/{withdrawal_id}", response_model=OffRampWithdrawalResponse)
async def get_offramp(
    withdrawal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    owner = None if getattr(current_user, "role", None) == UserRole.ADMIN else current_user.id
    try:
        return await offramp.get_withdrawal(
            db, withdrawal_id, user_id=owner
        )
    except offramp.OffRampError as exc:
        raise _offramp_error(exc)


@router.post(
    "/offramp/{withdrawal_id}/cancel",
    response_model=OffRampWithdrawalResponse,
)
async def cancel_offramp(
    withdrawal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        withdrawal = await offramp.get_withdrawal(
            db, withdrawal_id, user_id=current_user.id
        )
        return await offramp.cancel_withdrawal(db, withdrawal)
    except offramp.OffRampError as exc:
        raise _offramp_error(exc)


@router.post(
    "/offramp/{withdrawal_id}/retry",
    response_model=OffRampWithdrawalResponse,
)
async def retry_offramp(
    withdrawal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Re-run settlement for a deposit that stopped before the bank payout."""
    _require_admin(current_user)

    try:
        withdrawal = await offramp.get_withdrawal(db, withdrawal_id)
    except offramp.OffRampError as exc:
        raise _offramp_error(exc)

    if not withdrawal.received_usdc_units:
        raise HTTPException(
            status_code=409,
            detail="No USDC has arrived on this payout yet",
        )

    if withdrawal.provider_reference:
        # Never create a second bank payout while the first one may still be
        # live. Poll it first. Only a terminal FAILED/REJECTED provider state
        # clears the reference and allows a fresh payout from the NGNX that
        # is already in the wallet.
        try:
            refreshed = await offramp.refresh_withdrawal(db, withdrawal)
        except offramp.OffRampError as exc:
            raise _offramp_error(exc)
        except (ObiexError, ObiexNotConfigured) as exc:
            raise HTTPException(status_code=503, detail=str(exc))

        if refreshed.status != offramp.OffRampStatus.FAILED:
            return refreshed

        withdrawal.provider_reference = None
        withdrawal.provider_withdrawal_id = None
        withdrawal.failure_reason = None

    try:
        offramp.ensure_enabled()
    except offramp.OffRampError as exc:
        raise _offramp_error(exc)

    if withdrawal.status != offramp.OffRampStatus.FAILED:
        raise HTTPException(
            status_code=409,
            detail=(
                "Only a failed payout can be retried. A held payout needs "
                "manual review before money moves."
            ),
        )

    withdrawal.status = offramp.OffRampStatus.DEPOSIT_CONFIRMED
    withdrawal.failure_reason = None
    await db.commit()

    try:
        return await offramp.settle_withdrawal(db, withdrawal)
    except offramp.OffRampError as exc:
        raise _offramp_error(exc)
    except (ObiexError, ObiexNotConfigured) as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.post(
    "/offramp/{withdrawal_id}/refund",
    response_model=OffRampWithdrawalResponse,
)
async def refund_offramp(
    withdrawal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return deposited USDC to the provider's Solana address."""
    _require_admin(current_user)

    try:
        withdrawal = await offramp.get_withdrawal(db, withdrawal_id)
        return await offramp.refund_withdrawal(db, withdrawal)
    except offramp.OffRampError as exc:
        raise _offramp_error(exc)
    except (ObiexError, ObiexNotConfigured) as exc:
        raise HTTPException(status_code=503, detail=str(exc))
