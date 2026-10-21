"""Escrow orchestration against the Reach Solana program.

Model 1 makes the Anchor program the source of truth for a task's escrow.
This module is the bridge between the backend's records and the chain:

* it locks a task's escrow with `create_task` once the money has arrived;
* it releases the escrow with `approve_work` when the creator approves;
* it mirrors the program's task status back onto the job row.

Every transaction is recorded in `chain_transactions` with an idempotency key
so a retry can never lock or release the same escrow twice.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.relayer import (
    FinancialTerms,
    Relayer,
    RelayerConfig,
    RelayerError,
    RelayerNotConfigured,
)
from core.solana import SolanaError, TaskState
from models import ChainTransaction, Job
from schemas.enums import (
    ChainTransactionStatus,
    FundingStatus,
    JobStatus,
    PayerType,
)

# USDC has six decimals.
USDC_DECIMALS = 6
USDC_UNIT = 10**USDC_DECIMALS


class EscrowError(RuntimeError):
    pass


class RelayerUnavailable(EscrowError):
    """The relayer is not configured, so the escrow cannot be touched."""


class InsufficientEscrowFunds(EscrowError):
    """The relayer does not hold enough USDC to back the task."""


# How the program's task status maps onto the backend's job status.
ONCHAIN_STATUS_TO_JOB_STATUS = {
    "Open": JobStatus.OPEN,
    "InProgress": JobStatus.IN_PROGRESS,
    "AwaitingEscrow": JobStatus.IN_PROGRESS,
    "AwaitingApproval": JobStatus.IN_PROGRESS,
    "Completed": JobStatus.COMPLETED,
    "Disputed": JobStatus.IN_PROGRESS,
    "Refunded": JobStatus.CANCELLED,
}


def get_relayer() -> Relayer:
    """Build the relayer from the environment."""
    config = RelayerConfig.from_env()

    if not config.rpc_url:
        raise RelayerNotConfigured("REACH_SOLANA_RPC_URL is not set")

    if not config.secret_key:
        raise RelayerNotConfigured("REACH_RELAYER_SECRET_KEY is not set")

    if not config.stable_mint:
        raise RelayerNotConfigured("REACH_STABLE_MINT is not set")

    return Relayer(config)


def escrow_units_for(amount_units: int, creation_fee_bps: int) -> int:
    """How much escrow can be locked with `amount_units` of USDC.

    The program charges the creation fee on top of the escrow, so the escrow
    has to be scaled down to leave room for the fee.
    """
    if amount_units <= 0:
        raise EscrowError("The funded amount must be positive")

    return (amount_units * 10000) // (10000 + creation_fee_bps)


def build_terms(escrow_units: int) -> FinancialTerms:
    """Split a funded amount into the program's financial terms.

    Reach sells one job price, so the whole budget is treated as labour
    until the product grows material and collateral terms.
    """
    return FinancialTerms(
        labor_fee=escrow_units,
        material_cost=0,
        upfront_release_pct=0,
        required_provider_collateral=0,
    )


async def _record_transaction(
    db: AsyncSession,
    *,
    job_id: int | None,
    kind: str,
    idempotency_key: str,
    signature: str | None,
    status: ChainTransactionStatus,
    slot: int | None = None,
    error: str | None = None,
) -> ChainTransaction:
    result = await db.execute(
        select(ChainTransaction).where(
            ChainTransaction.idempotency_key == idempotency_key
        )
    )
    record = result.scalar_one_or_none()

    if record is None:
        record = ChainTransaction(
            job_id=job_id,
            kind=kind,
            idempotency_key=idempotency_key,
            status=status,
        )
        db.add(record)

    record.signature = signature or record.signature
    record.status = status
    record.slot = slot
    record.error = error
    record.processed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(record)
    return record


async def notify_nearby_providers(db: AsyncSession, job: Job) -> None:
    """Tell nearby providers the task is open.

    The architecture doc puts this after the escrow is locked, not when the
    task is drafted: providers should only see tasks that are funded.
    """
    try:
        from geoalchemy2.functions import ST_DWithin, ST_GeogFromText

        from models import User
        from utils import send_job_notification

        radius = 30000  # 30km
        point = ST_GeogFromText(f"POINT({job.longitude} {job.latitude})")

        result = await db.execute(
            select(User).where(
                ST_DWithin(User.location, point, radius),
                User.id != job.owner_id,
                User.location.is_not(None),
            )
        )

        for user in result.scalars().all():
            if user.fcm_token:
                send_job_notification(
                    user.fcm_token, job.title, job.location_name, job.id
                )
    except Exception:  # pragma: no cover - notifications are best effort
        return


async def fund_task_escrow(
    db: AsyncSession,
    job: Job,
    *,
    funded_units: int,
    creation_fee_bps: int,
    tag: str | None = None,
    desc: str | None = None,
) -> ChainTransaction:
    """Lock the task's escrow on-chain with `create_task`."""
    relayer = get_relayer()

    escrow_units = escrow_units_for(funded_units, creation_fee_bps)
    terms = build_terms(escrow_units)

    await relayer.ensure_token_account()

    balance = await relayer.token_balance()
    if balance < escrow_units:
        raise InsufficientEscrowFunds(
            "The relayer does not hold enough USDC to fund this task"
        )

    idempotency_key = f"create-task-{job.id}"

    existing = (
        await db.execute(
            select(ChainTransaction).where(
                ChainTransaction.idempotency_key == idempotency_key
            )
        )
    ).scalar_one_or_none()

    if existing and existing.status in (
        ChainTransactionStatus.CONFIRMED,
        ChainTransactionStatus.FINALIZED,
    ):
        # The escrow is already locked; never lock it twice.
        return existing

    try:
        confirmation = await relayer.create_task(
            task_id=job.id,
            terms=terms,
            tag=tag,
            desc=desc,
            idempotency_key=idempotency_key,
        )
    except RelayerError as exc:
        await _record_transaction(
            db,
            job_id=job.id,
            kind="create_task",
            idempotency_key=idempotency_key,
            signature=None,
            status=ChainTransactionStatus.FAILED,
            error=str(exc)[:1000],
        )
        raise

    transaction = await _record_transaction(
        db,
        job_id=job.id,
        kind="create_task",
        idempotency_key=idempotency_key,
        signature=confirmation.signature,
        status=(
            ChainTransactionStatus.FINALIZED
            if confirmation.status == "finalized"
            else ChainTransactionStatus.CONFIRMED
        ),
        slot=confirmation.slot,
    )

    job.onchain_task_id = job.id
    job.onchain_tx_hash = confirmation.signature
    job.onchain_status = "Open"
    job.payer_type = PayerType.CUSTODIAL
    job.funding_status = FundingStatus.FUNDED
    job.status = JobStatus.OPEN

    await db.commit()
    await db.refresh(job)

    await notify_nearby_providers(db, job)

    return transaction


async def release_task_escrow(
    db: AsyncSession,
    job: Job,
    *,
    provider_address: str,
) -> ChainTransaction:
    """Release the escrow to the provider with `approve_work`."""
    relayer = get_relayer()

    from solders.pubkey import Pubkey

    try:
        provider = Pubkey.from_string(provider_address)
    except Exception as exc:
        raise EscrowError("The provider does not have a valid Solana address") from exc

    idempotency_key = f"approve-work-{job.id}"

    try:
        confirmation = await relayer.approve_work(
            task_id=job.id,
            provider_address=provider,
            idempotency_key=idempotency_key,
        )
    except RelayerError as exc:
        await _record_transaction(
            db,
            job_id=job.id,
            kind="approve_work",
            idempotency_key=idempotency_key,
            signature=None,
            status=ChainTransactionStatus.FAILED,
            error=str(exc)[:1000],
        )
        raise

    transaction = await _record_transaction(
        db,
        job_id=job.id,
        kind="approve_work",
        idempotency_key=idempotency_key,
        signature=confirmation.signature,
        status=(
            ChainTransactionStatus.FINALIZED
            if confirmation.status == "finalized"
            else ChainTransactionStatus.CONFIRMED
        ),
        slot=confirmation.slot,
    )

    job.onchain_status = "Completed"
    job.status = JobStatus.COMPLETED

    await db.commit()
    await db.refresh(job)

    return transaction


async def sync_job_from_chain(db: AsyncSession, job: Job) -> TaskState | None:
    """Read the task's state from the program and mirror it onto the job."""
    relayer = get_relayer()

    try:
        state = await relayer.read_task(job.id)
    except SolanaError:
        return None

    if state is None:
        return None

    job.onchain_status = state.status
    job.onchain_task_id = job.onchain_task_id or job.id

    mapped = ONCHAIN_STATUS_TO_JOB_STATUS.get(state.status)
    if mapped is not None:
        job.status = mapped

    await db.commit()
    await db.refresh(job)

    return state
