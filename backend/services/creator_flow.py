"""Creator-signed escrow transactions for wallet-funded tasks.

When a client funds a task from their own Solana wallet, that wallet is the
on-chain creator. The Anchor program therefore requires the client's signature
for three lifecycle instructions:

* ``create_task`` — moves USDC from the client's token account into the task
  vault (plus the creation fee into the fee vault);
* ``accept`` — accepts a provider's on-chain application;
* ``approve_work`` — releases the task vault to the provider.

The flow mirrors the provider-signed flow: the backend prepares an unsigned
legacy transaction, the client signs it in Phantom / Solflare / Backpack, and
the backend verifies the signed bytes before submitting them.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from solders.instruction import Instruction
from solders.pubkey import Pubkey
from solders.transaction import Transaction
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import settings
from core.relayer import Relayer, RelayerError, RelayerNotConfigured
from core.solana import (
    SolanaError,
    TransactionConfirmation,
    build_legacy_transaction,
    decode_application_account,
)
from models import ChainTransaction, Job, JobApplication, PaymentIntent, User
from schemas.enums import (
    ApplicationStatus,
    ChainTransactionStatus,
    CreatorAction,
    FundingRail,
    FundingStatus,
    JobStatus,
    PaymentStatus,
    PayerType,
)

from .chain import (
    _record_transaction,
    build_terms,
    escrow_units_for,
    get_relayer,
    notify_nearby_providers,
)
from .funding import FundingError, budget_naira, to_kobo
from .onchain_verify import OnchainVerificationError, verify_signed_transaction


class CreatorFlowError(RuntimeError):
    """The creator-signed lifecycle cannot proceed."""


class CreatorWalletMissing(CreatorFlowError):
    """The client has not recorded a Solana wallet address yet."""


class CreatorTransactionInvalid(CreatorFlowError):
    """The signed transaction is not the one the backend prepared."""


class CreatorStateError(CreatorFlowError):
    """The task is not in a state where this instruction can run."""


@dataclass(frozen=True)
class PreparedCreatorTransaction:
    action: CreatorAction
    job_id: int
    task_id: int
    signer_address: str
    provider_address: str | None = None
    transaction: str | None = None
    recent_blockhash: str | None = None
    amount_units: int | None = None
    escrow_units: int | None = None
    creation_fee_units: int | None = None
    already_done: bool = False


def _wallet_pubkey(user: User) -> Pubkey:
    address = (getattr(user, "onchain_address", None) or "").strip()
    if not address:
        raise CreatorWalletMissing(
            "Add a Solana wallet address before funding this task."
        )
    try:
        return Pubkey.from_string(address)
    except Exception as exc:  # noqa: BLE001 - solders raises ValueError
        raise CreatorWalletMissing("The saved Solana wallet address is not valid.") from exc


def _idempotency_key(
    action: CreatorAction,
    job_id: int,
    wallet: Pubkey,
    provider: Pubkey | None = None,
) -> str:
    if action == CreatorAction.CREATE:
        return f"wallet-create-task-{job_id}"
    if action == CreatorAction.ACCEPT:
        return f"wallet-accept-{job_id}-{provider}"
    return f"wallet-approve-work-{job_id}"


def _already_confirmed(record: ChainTransaction | None) -> bool:
    return bool(
        record
        and record.status
        in (ChainTransactionStatus.CONFIRMED, ChainTransactionStatus.FINALIZED)
    )


async def _chain_record(
    db: AsyncSession, idempotency_key: str
) -> ChainTransaction | None:
    return (
        await db.execute(
            select(ChainTransaction).where(
                ChainTransaction.idempotency_key == idempotency_key
            )
        )
    ).scalar_one_or_none()


async def _read_task_optional(relayer: Relayer, task_id: int):
    try:
        return await relayer.read_task(task_id)
    except SolanaError as exc:
        raise CreatorFlowError(f"Could not read the task from Solana: {exc}") from exc


async def _read_task_or_raise(relayer: Relayer, task_id: int):
    try:
        state = await relayer.read_task(task_id)
    except SolanaError as exc:
        raise CreatorStateError(f"Could not read the task from Solana: {exc}") from exc

    if state is None:
        raise CreatorStateError("The task has no on-chain state yet.")
    return state


async def _read_application_or_raise(
    relayer: Relayer, task_id: int, provider: Pubkey
):
    address, _ = relayer.program.application_address(task_id, provider)
    data = await relayer.rpc.get_account_info(address)
    if data is None:
        raise CreatorStateError("The provider has not applied on-chain yet.")
    try:
        return decode_application_account(data)
    except SolanaError as exc:
        raise CreatorStateError(
            "The on-chain application could not be decoded."
        ) from exc


def _expected_create_task_instruction(
    relayer: Relayer,
    *,
    creator: Pubkey,
    task_id: int,
    terms,
    tag: str | None,
    desc: str | None,
) -> Instruction:
    return relayer.program.build_instruction(
        "create_task",
        accounts={"creator": creator, "stable_coin_mint": relayer.mint},
        args={
            "task_id": task_id,
            "terms": terms.to_dict(),
            "tag": tag,
            "desc": desc,
        },
    )


def _expected_accept_instruction(
    relayer: Relayer,
    *,
    owner: Pubkey,
    task_id: int,
    provider: Pubkey,
) -> Instruction:
    return relayer.program.build_instruction(
        "accept",
        accounts={"owner": owner},
        args={"task_id": task_id, "provider": provider},
    )


def _expected_approve_work_instruction(
    relayer: Relayer,
    *,
    creator: Pubkey,
    task_id: int,
    provider: Pubkey,
) -> Instruction:
    return relayer.program.build_instruction(
        "approve_work",
        accounts={
            "creator": creator,
            "provider_token_account": relayer.program.associated_token_address(
                provider, relayer.mint
            ),
            "stable_coin_mint": relayer.mint,
        },
        args={"task_id": task_id},
    )


def _decode_signed(raw_b64: str) -> bytes:
    try:
        return base64.b64decode(raw_b64, validate=True)
    except Exception as exc:  # noqa: BLE001
        raise CreatorTransactionInvalid(
            "The signed transaction is not valid base64."
        ) from exc


def _verify(
    raw: bytes,
    *,
    signer: Pubkey,
    expected: Instruction,
) -> Transaction:
    try:
        return verify_signed_transaction(
            raw,
            signer=signer,
            expected=expected,
            role="client",
        )
    except OnchainVerificationError as exc:
        raise CreatorTransactionInvalid(str(exc)) from exc


def _amounts(total_units: int) -> tuple[int, int]:
    """Return (escrow_units, creation_fee_units) for a total spend."""
    escrow_units = escrow_units_for(total_units, settings.REACH_CREATION_FEE_BPS)
    fee_units = escrow_units * settings.REACH_CREATION_FEE_BPS // 10_000
    return escrow_units, fee_units


async def _latest_wallet_intent(
    db: AsyncSession, job_id: int
) -> PaymentIntent | None:
    return (
        await db.execute(
            select(PaymentIntent)
            .where(
                PaymentIntent.job_id == job_id,
                PaymentIntent.rail == FundingRail.WALLET,
            )
            .order_by(PaymentIntent.id.desc())
        )
    ).scalars().first()


async def _prepare_wallet_intent(
    db: AsyncSession, job: Job, total_units: int
) -> PaymentIntent:
    pending = (
        await db.execute(
            select(PaymentIntent)
            .where(
                PaymentIntent.job_id == job.id,
                PaymentIntent.status == PaymentStatus.PENDING,
            )
            .order_by(PaymentIntent.id.desc())
        )
    ).scalars().all()

    for intent in pending:
        if intent.rail != FundingRail.WALLET:
            raise CreatorStateError(
                "A payment is already open for this task on another rail. "
                "Finish or cancel it before funding from a wallet."
            )

    try:
        naira = budget_naira(job.budget)
        amount_kobo = to_kobo(naira)
    except FundingError as exc:
        raise CreatorStateError(str(exc)) from exc

    wallet_intent = next(
        (intent for intent in pending if intent.rail == FundingRail.WALLET),
        None,
    )

    if wallet_intent is None:
        wallet_intent = PaymentIntent(
            job_id=job.id,
            reference=f"wallet-job-{job.id}-{uuid4().hex[:10]}",
            rail=FundingRail.WALLET,
            amount_kobo=amount_kobo,
            amount_payable_kobo=amount_kobo,
            usdc_amount=total_units,
            status=PaymentStatus.PENDING,
            network="SOL",
        )
        db.add(wallet_intent)
    else:
        wallet_intent.amount_kobo = amount_kobo
        wallet_intent.amount_payable_kobo = amount_kobo
        wallet_intent.usdc_amount = total_units
        wallet_intent.network = "SOL"

    await db.commit()
    await db.refresh(wallet_intent)
    return wallet_intent


async def _mark_funded(
    db: AsyncSession,
    job: Job,
    *,
    signature: str | None,
    state,
    intent: PaymentIntent | None = None,
) -> None:
    job.onchain_task_id = job.id
    if signature:
        job.onchain_tx_hash = signature
    job.payer_type = PayerType.WALLET
    job.funding_status = FundingStatus.FUNDED
    job.onchain_status = state.status
    job.status = JobStatus.OPEN

    if intent is None:
        intent = await _latest_wallet_intent(db, job.id)
    if intent is not None:
        # The on-chain task is canonical. If a reconciliation is correcting a
        # lost DB write, make the intent reflect the amount that actually
        # landed in the vault.
        intent.usdc_amount = state.labor_fee + (
            state.labor_fee * settings.REACH_CREATION_FEE_BPS // 10_000
        )
        intent.status = PaymentStatus.PAID
        intent.paid_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(job)


async def prepare_create_task(
    db: AsyncSession,
    *,
    job: Job,
    user: User,
    usdc_units: int,
) -> PreparedCreatorTransaction:
    """Build the unsigned ``create_task`` transaction for the client."""
    if job.owner_id != user.id:
        raise CreatorStateError("Only the job owner can fund this task.")

    try:
        relayer = get_relayer()
    except RelayerNotConfigured as exc:
        raise CreatorFlowError(str(exc)) from exc

    wallet = _wallet_pubkey(user)
    state = await _read_task_optional(relayer, job.id)

    if state is not None:
        if state.creator != wallet:
            raise CreatorStateError(
                "This task id is already on-chain with a different creator."
            )
        if state.status != "Open":
            raise CreatorStateError(
                f"The task is already '{state.status}' on-chain."
            )
        await _mark_funded(db, job, signature=None, state=state)
        escrow_units = state.labor_fee
        fee_units = escrow_units * settings.REACH_CREATION_FEE_BPS // 10_000
        return PreparedCreatorTransaction(
            action=CreatorAction.CREATE,
            job_id=job.id,
            task_id=job.id,
            signer_address=str(wallet),
            amount_units=escrow_units + fee_units,
            escrow_units=escrow_units,
            creation_fee_units=fee_units,
            already_done=True,
        )

    if job.status != JobStatus.PENDING_FUNDING:
        raise CreatorStateError(
            "This task is not waiting for funding. Only a pending-funding "
            "task can be escrowed from a wallet."
        )

    if job.funding_status in (FundingStatus.FUNDED, FundingStatus.PAID):
        raise CreatorStateError(
            "This task is already marked as funded but has no on-chain task."
        )

    if usdc_units < settings.REACH_MIN_ESCROW_UNITS:
        raise CreatorStateError(
            f"The minimum escrow is {settings.REACH_MIN_ESCROW_UNITS / 1_000_000:g} USDC."
        )

    if usdc_units > 2**64 - 1:
        raise CreatorStateError("The USDC amount is too large.")

    escrow_units, fee_units = _amounts(usdc_units)
    terms = build_terms(escrow_units)

    try:
        relayer.check_policy(task_id=job.id, terms=terms)
    except RelayerNotConfigured:
        raise
    except RelayerError as exc:
        raise CreatorStateError(str(exc)) from exc

    # The program expects the creator's associated token account to exist.
    # Create it with the relayer so the client only signs one instruction.
    try:
        ata = await relayer.ensure_token_account(wallet)
    except (RelayerError, SolanaError) as exc:
        raise CreatorFlowError(
            f"Could not prepare the client's USDC token account: {exc}"
        ) from exc
    balance = await relayer.rpc.get_token_account_balance(ata)
    available = int(balance["value"]["amount"]) if balance else 0
    required = escrow_units + fee_units
    if available < required:
        raise CreatorStateError(
            f"Add at least {required / 1_000_000:g} USDC to the wallet "
            "before funding this task."
        )

    await _prepare_wallet_intent(db, job, usdc_units)

    instruction = _expected_create_task_instruction(
        relayer,
        creator=wallet,
        task_id=job.id,
        terms=terms,
        tag=(job.title or "")[:30],
        desc=(job.description or "")[:200],
    )
    blockhash = await relayer.rpc.get_latest_blockhash()
    transaction = build_legacy_transaction(wallet, [instruction], blockhash)

    return PreparedCreatorTransaction(
        action=CreatorAction.CREATE,
        job_id=job.id,
        task_id=job.id,
        signer_address=str(wallet),
        transaction=base64.b64encode(bytes(transaction)).decode("ascii"),
        recent_blockhash=str(blockhash),
        amount_units=usdc_units,
        escrow_units=escrow_units,
        creation_fee_units=fee_units,
    )


async def submit_create_task(
    db: AsyncSession,
    *,
    job: Job,
    user: User,
    signed_transaction: str,
) -> ChainTransaction:
    """Verify, submit and mirror a client-signed ``create_task``."""
    if job.owner_id != user.id:
        raise CreatorStateError("Only the job owner can fund this task.")

    try:
        relayer = get_relayer()
    except RelayerNotConfigured as exc:
        raise CreatorFlowError(str(exc)) from exc

    wallet = _wallet_pubkey(user)
    idempotency_key = _idempotency_key(CreatorAction.CREATE, job.id, wallet)

    existing = await _chain_record(db, idempotency_key)
    if _already_confirmed(existing):
        state = await _read_task_or_raise(relayer, job.id)
        await _mark_funded(db, job, signature=existing.signature, state=state)
        return existing

    # A previous submit may have confirmed before the process could write the
    # chain_transactions row. Reconcile from the task instead of trying to
    # create the same PDA a second time.
    state = await _read_task_optional(relayer, job.id)
    if state is not None:
        if state.creator != wallet:
            raise CreatorStateError(
                "This task id is already on-chain with a different creator."
            )
        if state.status != "Open":
            raise CreatorStateError(
                f"The task is already '{state.status}' on-chain."
            )
        record = await _record_transaction(
            db,
            job_id=job.id,
            kind="create_task",
            idempotency_key=idempotency_key,
            signature=None,
            status=ChainTransactionStatus.CONFIRMED,
        )
        await _mark_funded(db, job, signature=None, state=state)
        return record

    intent = await _latest_wallet_intent(db, job.id)
    if intent is None or intent.usdc_amount is None:
        raise CreatorStateError(
            "Start the wallet funding flow before submitting it."
        )

    total_units = int(intent.usdc_amount)
    escrow_units, _ = _amounts(total_units)
    terms = build_terms(escrow_units)
    instruction = _expected_create_task_instruction(
        relayer,
        creator=wallet,
        task_id=job.id,
        terms=terms,
        tag=(job.title or "")[:30],
        desc=(job.description or "")[:200],
    )

    raw = _decode_signed(signed_transaction)
    transaction = _verify(raw, signer=wallet, expected=instruction)

    try:
        confirmation: TransactionConfirmation = await relayer.rpc.send_transaction(
            transaction
        )
        confirmation = await relayer.rpc.confirm_transaction(confirmation)
    except SolanaError as exc:
        await _record_transaction(
            db,
            job_id=job.id,
            kind="create_task",
            idempotency_key=idempotency_key,
            signature=None,
            status=ChainTransactionStatus.FAILED,
            error=str(exc)[:1000],
        )
        raise CreatorFlowError(str(exc)) from exc

    if confirmation.status == "failed":
        await _record_transaction(
            db,
            job_id=job.id,
            kind="create_task",
            idempotency_key=idempotency_key,
            signature=confirmation.signature,
            status=ChainTransactionStatus.FAILED,
            slot=confirmation.slot,
            error=(confirmation.error or "The create_task transaction failed")[:1000],
        )
        raise CreatorFlowError(
            confirmation.error or "The create_task transaction failed on-chain."
        )

    record = await _record_transaction(
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

    state = await _read_task_or_raise(relayer, job.id)
    if (
        state.creator != wallet
        or state.id != job.id
        or state.status != "Open"
        or state.stable_coin_mint != relayer.mint
        or state.labor_fee != escrow_units
        or state.material_cost != 0
    ):
        raise CreatorFlowError(
            "The transaction confirmed but the on-chain task does not match "
            "the prepared escrow. Contact support."
        )

    await _mark_funded(
        db,
        job,
        signature=confirmation.signature,
        state=state,
        intent=intent,
    )
    await notify_nearby_providers(db, job)

    return record


async def prepare_accept(
    db: AsyncSession,
    *,
    job: Job,
    application: JobApplication,
    user: User,
    provider: User,
) -> PreparedCreatorTransaction:
    """Build the unsigned ``accept`` transaction for the client."""
    if job.owner_id != user.id:
        raise CreatorStateError("Only the job owner can accept an application.")

    if job.payer_type != PayerType.WALLET:
        raise CreatorStateError(
            "This is a custodial escrow. Use the normal application status "
            "endpoint; the relayer accepts for the creator."
        )

    if job.funding_status != FundingStatus.FUNDED or job.onchain_status != "Open":
        raise CreatorStateError("This task is not open for acceptance on-chain.")

    try:
        relayer = get_relayer()
    except RelayerNotConfigured as exc:
        raise CreatorFlowError(str(exc)) from exc

    wallet = _wallet_pubkey(user)
    provider_pubkey = _wallet_pubkey(provider)
    state = await _read_task_or_raise(relayer, job.id)

    if state.creator != wallet:
        raise CreatorStateError(
            "The connected wallet is not the creator of this escrow."
        )

    if state.status in ("InProgress", "AwaitingEscrow") and (
        state.provider == provider_pubkey
    ):
        await _apply_acceptance(
            db,
            job=job,
            application=application,
            state=state,
        )
        return PreparedCreatorTransaction(
            action=CreatorAction.ACCEPT,
            job_id=job.id,
            task_id=job.id,
            signer_address=str(wallet),
            provider_address=str(provider_pubkey),
            already_done=True,
        )

    if application.status != ApplicationStatus.PENDING:
        raise CreatorStateError("Only pending applications can be accepted.")

    if state.status != "Open" or state.provider is not None:
        raise CreatorStateError(
            f"The task is '{state.status}', so it cannot accept an application."
        )

    onchain_application = await _read_application_or_raise(
        relayer, job.id, provider_pubkey
    )
    if onchain_application.status != "Pending":
        raise CreatorStateError(
            "The provider's on-chain application is no longer pending."
        )

    instruction = _expected_accept_instruction(
        relayer,
        owner=wallet,
        task_id=job.id,
        provider=provider_pubkey,
    )
    blockhash = await relayer.rpc.get_latest_blockhash()
    transaction = build_legacy_transaction(wallet, [instruction], blockhash)

    return PreparedCreatorTransaction(
        action=CreatorAction.ACCEPT,
        job_id=job.id,
        task_id=job.id,
        signer_address=str(wallet),
        provider_address=str(provider_pubkey),
        transaction=base64.b64encode(bytes(transaction)).decode("ascii"),
        recent_blockhash=str(blockhash),
    )


async def _apply_acceptance(
    db: AsyncSession,
    *,
    job: Job,
    application: JobApplication,
    state,
) -> None:
    application.status = ApplicationStatus.ACCEPTED

    others = (
        await db.execute(
            select(JobApplication).where(
                JobApplication.job_id == job.id,
                JobApplication.id != application.id,
                JobApplication.status == ApplicationStatus.PENDING,
            )
        )
    ).scalars().all()
    for other in others:
        other.status = ApplicationStatus.REJECTED

    job.onchain_status = state.status
    job.status = (
        JobStatus.IN_PROGRESS
        if state.status in ("InProgress", "AwaitingEscrow")
        else job.status
    )

    await db.commit()
    await db.refresh(job)


async def submit_accept(
    db: AsyncSession,
    *,
    job: Job,
    application: JobApplication,
    user: User,
    provider: User,
    signed_transaction: str,
) -> ChainTransaction:
    """Verify, submit and mirror a client-signed ``accept``."""
    if job.owner_id != user.id:
        raise CreatorStateError("Only the job owner can accept an application.")

    if job.payer_type != PayerType.WALLET:
        raise CreatorStateError(
            "This is a custodial escrow. Use the normal application status "
            "endpoint; the relayer accepts for the creator."
        )

    try:
        relayer = get_relayer()
    except RelayerNotConfigured as exc:
        raise CreatorFlowError(str(exc)) from exc

    wallet = _wallet_pubkey(user)
    provider_pubkey = _wallet_pubkey(provider)
    idempotency_key = _idempotency_key(
        CreatorAction.ACCEPT, job.id, wallet, provider_pubkey
    )

    existing = await _chain_record(db, idempotency_key)
    if _already_confirmed(existing):
        state = await _read_task_or_raise(relayer, job.id)
        await _apply_acceptance(
            db,
            job=job,
            application=application,
            state=state,
        )
        return existing

    # Reconcile a submit that confirmed before the DB row was written.
    state = await _read_task_optional(relayer, job.id)
    if state is None:
        raise CreatorStateError("The task is not on-chain yet.")
    if state.provider == provider_pubkey and state.status in (
        "InProgress",
        "AwaitingEscrow",
    ):
        record = await _record_transaction(
            db,
            job_id=job.id,
            kind="accept_application",
            idempotency_key=idempotency_key,
            signature=None,
            status=ChainTransactionStatus.CONFIRMED,
        )
        await _apply_acceptance(
            db,
            job=job,
            application=application,
            state=state,
        )
        return record
    if state.provider is not None and state.provider != provider_pubkey:
        raise CreatorStateError(
            "The task has already accepted a different provider."
        )
    if state.status != "Open":
        raise CreatorStateError(
            f"The task is '{state.status}', so it cannot accept an application."
        )

    if application.status != ApplicationStatus.PENDING:
        raise CreatorStateError("Only pending applications can be accepted.")

    instruction = _expected_accept_instruction(
        relayer,
        owner=wallet,
        task_id=job.id,
        provider=provider_pubkey,
    )
    raw = _decode_signed(signed_transaction)
    transaction = _verify(raw, signer=wallet, expected=instruction)

    try:
        confirmation: TransactionConfirmation = await relayer.rpc.send_transaction(
            transaction
        )
        confirmation = await relayer.rpc.confirm_transaction(confirmation)
    except SolanaError as exc:
        await _record_transaction(
            db,
            job_id=job.id,
            kind="accept_application",
            idempotency_key=idempotency_key,
            signature=None,
            status=ChainTransactionStatus.FAILED,
            error=str(exc)[:1000],
        )
        raise CreatorFlowError(str(exc)) from exc

    if confirmation.status == "failed":
        await _record_transaction(
            db,
            job_id=job.id,
            kind="accept_application",
            idempotency_key=idempotency_key,
            signature=confirmation.signature,
            status=ChainTransactionStatus.FAILED,
            slot=confirmation.slot,
            error=(confirmation.error or "The accept transaction failed")[:1000],
        )
        raise CreatorFlowError(
            confirmation.error or "The accept transaction failed on-chain."
        )

    record = await _record_transaction(
        db,
        job_id=job.id,
        kind="accept_application",
        idempotency_key=idempotency_key,
        signature=confirmation.signature,
        status=(
            ChainTransactionStatus.FINALIZED
            if confirmation.status == "finalized"
            else ChainTransactionStatus.CONFIRMED
        ),
        slot=confirmation.slot,
    )

    state = await _read_task_or_raise(relayer, job.id)
    if state.provider != provider_pubkey or state.status not in (
        "InProgress",
        "AwaitingEscrow",
    ):
        raise CreatorFlowError(
            "The transaction confirmed but the task did not accept the "
            "provider. Contact support."
        )

    await _apply_acceptance(
        db,
        job=job,
        application=application,
        state=state,
    )

    return record


async def prepare_release(
    db: AsyncSession,
    *,
    job: Job,
    application: JobApplication,
    user: User,
    provider: User,
) -> PreparedCreatorTransaction:
    """Build the unsigned ``approve_work`` transaction for the client."""
    if job.owner_id != user.id:
        raise CreatorStateError("Only the job owner can release the escrow.")

    if job.payer_type != PayerType.WALLET:
        raise CreatorStateError(
            "This is a custodial escrow. Use POST /payments/jobs/{id}/release."
        )

    if job.funding_status != FundingStatus.FUNDED:
        raise CreatorStateError("This task has no funded escrow to release.")

    if not (job.client_completed and job.worker_completed):
        raise CreatorStateError(
            "Both the client and the provider must confirm completion before "
            "the escrow can be released."
        )

    if application.status != ApplicationStatus.ACCEPTED:
        raise CreatorStateError("The accepted provider could not be found.")

    try:
        relayer = get_relayer()
    except RelayerNotConfigured as exc:
        raise CreatorFlowError(str(exc)) from exc

    wallet = _wallet_pubkey(user)
    provider_pubkey = _wallet_pubkey(provider)
    state = await _read_task_or_raise(relayer, job.id)

    if state.status == "Completed" and state.provider == provider_pubkey:
        job.onchain_status = "Completed"
        job.status = JobStatus.COMPLETED
        await db.commit()
        await db.refresh(job)
        return PreparedCreatorTransaction(
            action=CreatorAction.RELEASE,
            job_id=job.id,
            task_id=job.id,
            signer_address=str(wallet),
            provider_address=str(provider_pubkey),
            already_done=True,
        )

    if state.creator != wallet:
        raise CreatorStateError(
            "The connected wallet is not the creator of this escrow."
        )

    if state.status != "AwaitingApproval" or state.provider != provider_pubkey:
        raise CreatorStateError(
            f"The task is '{state.status}', so it cannot be released yet."
        )

    # The payout account must exist before the client signs; otherwise the
    # program's provider-token-account check fails. The relayer pays the rent.
    try:
        await relayer.ensure_token_account(provider_pubkey)
    except (RelayerError, SolanaError) as exc:
        raise CreatorFlowError(
            f"Could not prepare the provider's USDC token account: {exc}"
        ) from exc

    instruction = _expected_approve_work_instruction(
        relayer,
        creator=wallet,
        task_id=job.id,
        provider=provider_pubkey,
    )
    blockhash = await relayer.rpc.get_latest_blockhash()
    transaction = build_legacy_transaction(wallet, [instruction], blockhash)

    return PreparedCreatorTransaction(
        action=CreatorAction.RELEASE,
        job_id=job.id,
        task_id=job.id,
        signer_address=str(wallet),
        provider_address=str(provider_pubkey),
        transaction=base64.b64encode(bytes(transaction)).decode("ascii"),
        recent_blockhash=str(blockhash),
    )


async def submit_release(
    db: AsyncSession,
    *,
    job: Job,
    application: JobApplication,
    user: User,
    provider: User,
    signed_transaction: str,
) -> ChainTransaction:
    """Verify, submit and mirror a client-signed ``approve_work``."""
    if job.owner_id != user.id:
        raise CreatorStateError("Only the job owner can release the escrow.")

    if job.payer_type != PayerType.WALLET:
        raise CreatorStateError(
            "This is a custodial escrow. Use POST /payments/jobs/{id}/release."
        )

    if job.funding_status != FundingStatus.FUNDED:
        raise CreatorStateError("This task has no funded escrow to release.")

    if not (job.client_completed and job.worker_completed):
        raise CreatorStateError(
            "Both the client and the provider must confirm completion before "
            "the escrow can be released."
        )

    if application.status != ApplicationStatus.ACCEPTED:
        raise CreatorStateError("The accepted provider could not be found.")

    try:
        relayer = get_relayer()
    except RelayerNotConfigured as exc:
        raise CreatorFlowError(str(exc)) from exc

    wallet = _wallet_pubkey(user)
    provider_pubkey = _wallet_pubkey(provider)
    idempotency_key = _idempotency_key(
        CreatorAction.RELEASE, job.id, wallet, provider_pubkey
    )

    existing = await _chain_record(db, idempotency_key)
    if _already_confirmed(existing):
        state = await _read_task_or_raise(relayer, job.id)
        if state.status == "Completed":
            job.onchain_status = "Completed"
            job.status = JobStatus.COMPLETED
            await db.commit()
            await db.refresh(job)
        return existing

    # Reconcile a submit that confirmed before the DB row was written.
    state = await _read_task_optional(relayer, job.id)
    if state is None:
        raise CreatorStateError("The task is not on-chain yet.")
    if state.status == "Completed" and state.provider == provider_pubkey:
        record = await _record_transaction(
            db,
            job_id=job.id,
            kind="approve_work",
            idempotency_key=idempotency_key,
            signature=None,
            status=ChainTransactionStatus.CONFIRMED,
        )
        job.onchain_status = "Completed"
        job.status = JobStatus.COMPLETED
        await db.commit()
        await db.refresh(job)
        return record
    if state.status != "AwaitingApproval":
        raise CreatorStateError(
            f"The task is '{state.status}', so it cannot be released yet."
        )
    if state.provider != provider_pubkey:
        raise CreatorStateError(
            "The accepted provider does not match the on-chain task."
        )

    instruction = _expected_approve_work_instruction(
        relayer,
        creator=wallet,
        task_id=job.id,
        provider=provider_pubkey,
    )
    raw = _decode_signed(signed_transaction)
    transaction = _verify(raw, signer=wallet, expected=instruction)

    try:
        confirmation: TransactionConfirmation = await relayer.rpc.send_transaction(
            transaction
        )
        confirmation = await relayer.rpc.confirm_transaction(confirmation)
    except SolanaError as exc:
        await _record_transaction(
            db,
            job_id=job.id,
            kind="approve_work",
            idempotency_key=idempotency_key,
            signature=None,
            status=ChainTransactionStatus.FAILED,
            error=str(exc)[:1000],
        )
        raise CreatorFlowError(str(exc)) from exc

    if confirmation.status == "failed":
        await _record_transaction(
            db,
            job_id=job.id,
            kind="approve_work",
            idempotency_key=idempotency_key,
            signature=confirmation.signature,
            status=ChainTransactionStatus.FAILED,
            slot=confirmation.slot,
            error=(confirmation.error or "The approve_work transaction failed")[:1000],
        )
        raise CreatorFlowError(
            confirmation.error or "The approve_work transaction failed on-chain."
        )

    record = await _record_transaction(
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

    state = await _read_task_or_raise(relayer, job.id)
    if state.status != "Completed" or state.provider != provider_pubkey:
        raise CreatorFlowError(
            "The transaction confirmed but the task did not complete. "
            "Contact support."
        )

    job.onchain_status = "Completed"
    job.status = JobStatus.COMPLETED
    await db.commit()
    await db.refresh(job)

    return record


async def read_task_state(relayer: Relayer, task_id: int):
    try:
        return await relayer.read_task(task_id)
    except SolanaError as exc:
        raise CreatorStateError(f"Could not read the task from Solana: {exc}") from exc
