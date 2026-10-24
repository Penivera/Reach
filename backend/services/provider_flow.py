"""Provider-signed task lifecycle transactions.

The Anchor program requires the provider's own key for `apply` and
`complete_task`; the backend cannot sign those on the provider's behalf. The
flow is therefore:

1. the backend builds a legacy Solana transaction for the provider's wallet;
2. the provider signs it in Phantom / Solflare / Backpack;
3. the backend submits the signed bytes, checks that the transaction is the
   instruction it asked for, and mirrors the resulting on-chain state onto the
   job and application rows.

The creator's `accept` is different: for a custodial (relayer-funded) escrow the
relayer *is* the creator, so the backend signs it directly.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

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
from models import ChainTransaction, Job, User
from schemas.enums import (
    ChainTransactionStatus,
    FundingStatus,
    JobStatus,
    ProviderAction,
)

from .chain import _record_transaction, get_relayer
from .onchain_verify import OnchainVerificationError, verify_signed_transaction


class ProviderFlowError(RuntimeError):
    """The provider-signed lifecycle cannot proceed."""


class ProviderWalletMissing(ProviderFlowError):
    """The provider has not recorded a Solana payout address yet."""


class ProviderTransactionInvalid(ProviderFlowError):
    """The signed transaction is not the one the backend prepared."""


class ProviderStateError(ProviderFlowError):
    """The task is not in a state where this instruction can run."""


@dataclass(frozen=True)
class PreparedProviderTransaction:
    action: ProviderAction
    job_id: int
    task_id: int
    provider_address: str
    transaction: str | None
    recent_blockhash: str | None
    expires_at: int | None = None
    escrow_units: int | None = None
    already_done: bool = False


def _provider_pubkey(user: User) -> Pubkey:
    address = (getattr(user, "onchain_address", None) or "").strip()
    if not address:
        raise ProviderWalletMissing(
            "Add a Solana payout address before applying or completing work."
        )
    try:
        return Pubkey.from_string(address)
    except Exception as exc:  # noqa: BLE001 - solders raises ValueError
        raise ProviderWalletMissing(
            "The saved Solana payout address is not valid."
        ) from exc


def _idempotency_key(
    action: ProviderAction, job_id: int, provider: Pubkey
) -> str:
    # Several providers can apply to the same task, so the application
    # transaction is keyed by wallet as well as job.
    return f"provider-{action.value}-{job_id}-{provider}"


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


def _expected_instruction(
    relayer: Relayer,
    action: ProviderAction,
    *,
    task_id: int,
    provider: Pubkey,
    expires_at: int | None,
) -> Instruction:
    if action == ProviderAction.APPLY:
        return relayer.program.build_instruction(
            "apply",
            accounts={"provider": provider},
            args={"task_id": task_id, "expires_at": expires_at},
        )

    return relayer.program.build_instruction(
        "complete_task",
        accounts={"provider": provider},
        args={"task_id": task_id},
    )


def _verify_signed_transaction(
    raw: bytes,
    *,
    provider: Pubkey,
    expected: Instruction,
) -> Transaction:
    try:
        return verify_signed_transaction(
            raw,
            signer=provider,
            expected=expected,
            role="provider",
        )
    except OnchainVerificationError as exc:
        raise ProviderTransactionInvalid(str(exc)) from exc


async def _read_task_or_raise(relayer: Relayer, task_id: int):
    try:
        state = await relayer.read_task(task_id)
    except SolanaError as exc:
        raise ProviderStateError(f"Could not read the task from Solana: {exc}") from exc

    if state is None:
        raise ProviderStateError("The task has no on-chain state yet.")
    return state


async def _read_application_or_raise(
    relayer: Relayer, task_id: int, provider: Pubkey
):
    address, _ = relayer.program.application_address(task_id, provider)
    data = await relayer.rpc.get_account_info(address)
    if data is None:
        raise ProviderStateError(
            "The provider has not applied on-chain yet."
        )
    try:
        return decode_application_account(data)
    except SolanaError as exc:
        raise ProviderStateError(
            "The on-chain application could not be decoded."
        ) from exc


async def prepare_provider_transaction(
    db: AsyncSession,
    *,
    job: Job,
    user: User,
    action: ProviderAction,
) -> PreparedProviderTransaction:
    """Build the unsigned transaction the provider has to sign."""
    if job.onchain_task_id is None:
        raise ProviderStateError("The task is not on-chain yet.")

    try:
        relayer = get_relayer()
    except RelayerNotConfigured as exc:
        raise ProviderFlowError(str(exc)) from exc

    provider = _provider_pubkey(user)
    state = await _read_task_or_raise(relayer, job.id)

    if action == ProviderAction.APPLY:
        if job.funding_status != FundingStatus.FUNDED or state.status != "Open":
            raise ProviderStateError(
                "This task is not open for applications on-chain yet."
            )

        application, _ = relayer.program.application_address(job.id, provider)
        if await relayer.rpc.get_account_info(application) is not None:
            return PreparedProviderTransaction(
                action=action,
                job_id=job.id,
                task_id=job.id,
                provider_address=str(provider),
                transaction=None,
                recent_blockhash=None,
                escrow_units=state.creator_locked_balance,
                already_done=True,
            )

        expires_at = int(
            (
                datetime.now(timezone.utc)
                + timedelta(seconds=settings.REACH_APPLICATION_TTL_SECONDS)
            ).timestamp()
        )
        instruction = _expected_instruction(
            relayer,
            action,
            task_id=job.id,
            provider=provider,
            expires_at=expires_at,
        )
    else:
        if job.status != JobStatus.IN_PROGRESS:
            raise ProviderStateError("Only an in-progress task can be completed.")

        if state.status == "AwaitingApproval":
            return PreparedProviderTransaction(
                action=action,
                job_id=job.id,
                task_id=job.id,
                provider_address=str(provider),
                transaction=None,
                recent_blockhash=None,
                escrow_units=state.creator_locked_balance,
                already_done=True,
            )

        if state.status != "InProgress":
            raise ProviderStateError(
                f"The task is '{state.status}', so it cannot be completed yet."
            )

        if state.provider != provider:
            raise ProviderStateError(
                "The connected wallet is not the provider this task was accepted for."
            )

        expires_at = None
        instruction = _expected_instruction(
            relayer,
            action,
            task_id=job.id,
            provider=provider,
            expires_at=None,
        )

    blockhash = await relayer.rpc.get_latest_blockhash()
    transaction = build_legacy_transaction(provider, [instruction], blockhash)

    return PreparedProviderTransaction(
        action=action,
        job_id=job.id,
        task_id=job.id,
        provider_address=str(provider),
        transaction=base64.b64encode(bytes(transaction)).decode("ascii"),
        recent_blockhash=str(blockhash),
        expires_at=expires_at,
        escrow_units=state.creator_locked_balance,
    )


async def submit_provider_transaction(
    db: AsyncSession,
    *,
    job: Job,
    user: User,
    action: ProviderAction,
    signed_transaction: str,
) -> ChainTransaction:
    """Submit and verify a provider-signed `apply` / `complete_task`."""
    try:
        relayer = get_relayer()
    except RelayerNotConfigured as exc:
        raise ProviderFlowError(str(exc)) from exc

    provider = _provider_pubkey(user)
    idempotency_key = _idempotency_key(action, job.id, provider)

    existing = await _chain_record(db, idempotency_key)
    if _already_confirmed(existing):
        # A retry after a successful submit should still leave the DB row
        # consistent with the chain, even if the first response was lost.
        state = await _read_task_or_raise(relayer, job.id)
        if action == ProviderAction.APPLY:
            job.onchain_status = state.status
        elif state.status == "AwaitingApproval" and state.provider == provider:
            job.onchain_status = state.status
            job.worker_completed = True
        await db.commit()
        await db.refresh(job)
        return existing

    try:
        raw = base64.b64decode(signed_transaction, validate=True)
    except Exception as exc:  # noqa: BLE001
        raise ProviderTransactionInvalid(
            "The signed transaction is not valid base64."
        ) from exc

    # `apply` carries `expires_at` as an argument, so rebuild the expected
    # instruction from the values inside the signed transaction. That keeps the
    # check exact without trusting anything the client sends alongside it.
    expires_at: int | None = None
    if action == ProviderAction.APPLY:
        try:
            candidate = Transaction.from_bytes(raw)
            compiled = candidate.message.instructions[0]
            data = bytes(compiled.data)
        except Exception as exc:  # noqa: BLE001
            raise ProviderTransactionInvalid(
                "The signed transaction could not be decoded."
            ) from exc

        discriminator = bytes(relayer.program.instructions["apply"]["discriminator"])
        if len(data) < 24 or not data.startswith(discriminator):
            raise ProviderTransactionInvalid(
                "The signed transaction is not an apply instruction."
            )

        submitted_task_id = int.from_bytes(data[8:16], "little")
        if submitted_task_id != job.id:
            raise ProviderTransactionInvalid(
                "The signed transaction is for a different task."
            )
        expires_at = int.from_bytes(data[16:24], "little", signed=True)

    instruction = _expected_instruction(
        relayer,
        action,
        task_id=job.id,
        provider=provider,
        expires_at=expires_at,
    )
    transaction = _verify_signed_transaction(
        raw, provider=provider, expected=instruction
    )

    try:
        confirmation: TransactionConfirmation = await relayer.rpc.send_transaction(
            transaction
        )
        confirmation = await relayer.rpc.confirm_transaction(confirmation)
    except SolanaError as exc:
        await _record_transaction(
            db,
            job_id=job.id,
            kind=action.value,
            idempotency_key=idempotency_key,
            signature=None,
            status=ChainTransactionStatus.FAILED,
            error=str(exc)[:1000],
        )
        raise ProviderFlowError(str(exc)) from exc

    if confirmation.status == "failed":
        await _record_transaction(
            db,
            job_id=job.id,
            kind=action.value,
            idempotency_key=idempotency_key,
            signature=confirmation.signature,
            status=ChainTransactionStatus.FAILED,
            slot=confirmation.slot,
            error=(confirmation.error or "Transaction failed")[:1000],
        )
        raise ProviderFlowError(
            confirmation.error or "The transaction failed on-chain."
        )

    # Record the confirmation before the state read. If the RPC lags, the
    # signed transaction is not lost: a retry sees the confirmed record and
    # reconciles the job from chain state.
    transaction_record = await _record_transaction(
        db,
        job_id=job.id,
        kind=action.value,
        idempotency_key=idempotency_key,
        signature=confirmation.signature,
        status=(
            ChainTransactionStatus.FINALIZED
            if confirmation.status == "finalized"
            else ChainTransactionStatus.CONFIRMED
        ),
        slot=confirmation.slot,
    )

    # Confirm the state change before claiming success in Postgres.
    state = await _read_task_or_raise(relayer, job.id)

    if action == ProviderAction.APPLY:
        await _read_application_or_raise(relayer, job.id, provider)
        job.onchain_status = state.status
    else:
        if state.status != "AwaitingApproval" or state.provider != provider:
            raise ProviderFlowError(
                "The transaction confirmed but the task did not move to "
                "AwaitingApproval. Contact support."
            )
        job.onchain_status = state.status
        job.worker_completed = True

    await db.commit()
    await db.refresh(job)

    return transaction_record


async def accept_application_onchain(
    db: AsyncSession,
    *,
    job: Job,
    provider: User,
) -> ChainTransaction:
    """Accept a provider's on-chain application as the custodial creator."""
    try:
        relayer = get_relayer()
    except RelayerNotConfigured as exc:
        raise ProviderFlowError(str(exc)) from exc

    provider_address = _provider_pubkey(provider)

    state = await _read_task_or_raise(relayer, job.id)

    if state.creator != relayer.address:
        raise ProviderStateError(
            "This escrow was created by a wallet, not the relayer. The creator "
            "must accept the application from that wallet."
        )

    if state.status in ("InProgress", "AwaitingEscrow") and (
        state.provider == provider_address
    ):
        # Already accepted (for example a retry after the DB write failed).
        job.onchain_status = state.status
        job.status = JobStatus.IN_PROGRESS
        record = await _record_transaction(
            db,
            job_id=job.id,
            kind="accept_application",
            idempotency_key=f"accept-application-{job.id}-{provider_address}",
            signature=None,
            status=ChainTransactionStatus.CONFIRMED,
        )
        await db.commit()
        await db.refresh(job)
        return record

    if state.status != "Open":
        raise ProviderStateError(
            f"The task is '{state.status}', so it cannot accept an application."
        )

    onchain_application = await _read_application_or_raise(
        relayer, job.id, provider_address
    )
    if onchain_application.status != "Pending":
        raise ProviderStateError(
            "The provider's on-chain application is no longer pending."
        )

    try:
        confirmation = await relayer.accept_application(
            task_id=job.id,
            provider_address=provider_address,
            idempotency_key=f"accept-application-{job.id}-{provider_address}",
        )
    except RelayerError as exc:
        await _record_transaction(
            db,
            job_id=job.id,
            kind="accept_application",
            idempotency_key=f"accept-application-{job.id}-{provider_address}",
            signature=None,
            status=ChainTransactionStatus.FAILED,
            error=str(exc)[:1000],
        )
        raise ProviderFlowError(str(exc)) from exc

    if confirmation.status == "failed":
        await _record_transaction(
            db,
            job_id=job.id,
            kind="accept_application",
            idempotency_key=f"accept-application-{job.id}-{provider_address}",
            signature=confirmation.signature,
            status=ChainTransactionStatus.FAILED,
            slot=confirmation.slot,
            error=(confirmation.error or "The accept transaction failed")[:1000],
        )
        raise ProviderFlowError(
            confirmation.error or "The accept transaction failed on-chain."
        )

    state = await _read_task_or_raise(relayer, job.id)
    if state.provider != provider_address or state.status not in (
        "InProgress",
        "AwaitingEscrow",
    ):
        raise ProviderFlowError(
            "The transaction confirmed but the task did not accept the provider. "
            "Contact support."
        )

    job.onchain_status = state.status
    job.status = JobStatus.IN_PROGRESS

    record = await _record_transaction(
        db,
        job_id=job.id,
        kind="accept_application",
        idempotency_key=f"accept-application-{job.id}-{provider_address}",
        signature=confirmation.signature,
        status=(
            ChainTransactionStatus.FINALIZED
            if confirmation.status == "finalized"
            else ChainTransactionStatus.CONFIRMED
        ),
        slot=confirmation.slot,
    )

    await db.commit()
    await db.refresh(job)

    return record
