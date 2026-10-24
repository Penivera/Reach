"""The treasury behind the custodial escrow.

A fiat collection settles into Obiex's USDC balance. Before a fiat-funded
escrow can be locked, that USDC has to be on Solana with the relayer, so it is
withdrawn from Obiex to the relayer's token account.

The withdrawals are **batched**. Obiex charges about 1 per withdrawal, with a
minimum around 10, so withdrawing per job would cost more than the job is
worth. Instead the treasury keeps a float on-chain and sweeps the provider
balance down to a target when it runs low.

Two balances matter:

* the **on-chain** balance — USDC in the relayer's token account, which is
  what funds escrows;
* the **provider** balance — USDC in our Obiex wallet, which is what the next
  withdrawal is made from.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import settings
from core.obiex import ObiexError, ObiexNotConfigured, get_obiex_client
from core.relayer import relayer_from_env
from models import TreasuryTransfer
from schemas.enums import TreasuryTransferStatus

USDC_UNIT = 10**6


class TreasuryError(RuntimeError):
    pass


def to_units(amount) -> int:
    """Convert a decimal amount of USDC into base units."""
    try:
        value = Decimal(str(amount))
    except Exception as exc:  # pragma: no cover - defensive
        raise TreasuryError("Invalid USDC amount") from exc

    return int((value * USDC_UNIT).to_integral_value())


def _balance_from(payload: dict) -> int:
    """Read a balance out of Obiex's wallet response.

    The response nests the wallet and reports the balance under a few
    different names, so the first numeric one wins.
    """
    candidates = [
        payload.get("availableBalance"),
        payload.get("balance"),
        payload.get("totalSwappableBalance"),
    ]

    wallet = payload.get("wallet")
    if isinstance(wallet, dict):
        candidates.extend(
            [
                wallet.get("availableBalance"),
                wallet.get("balance"),
            ]
        )

    for candidate in candidates:
        if candidate is None:
            continue
        try:
            return to_units(candidate)
        except TreasuryError:
            continue

    return 0


async def onchain_balance() -> int:
    """USDC held by the relayer on Solana."""
    relayer = relayer_from_env()
    return await relayer.token_balance()


async def provider_balance() -> int:
    """USDC held in our Obiex wallet."""
    client = get_obiex_client()
    balance = await client.get_wallet_balance(settings.OBiex_COLLECTION_CURRENCY)
    return _balance_from(balance)


async def relayer_address() -> str:
    return str(relayer_from_env().address)


async def request_withdrawal(
    db: AsyncSession,
    *,
    amount_units: int,
    address: str | None = None,
) -> TreasuryTransfer:
    """Withdraw USDC from Obiex to the relayer's Solana address."""
    if amount_units <= 0:
        raise TreasuryError("The withdrawal amount must be positive")

    minimum = settings.REACH_TREASURY_MIN_WITHDRAWAL_UNITS
    if amount_units < minimum:
        raise TreasuryError(
            f"Obiex withdrawals start at {minimum / USDC_UNIT:g} USDC"
        )

    client = get_obiex_client()
    destination = address or await relayer_address()

    try:
        withdrawal = await client.request_crypto_withdrawal(
            currency=settings.OBiex_COLLECTION_CURRENCY,
            amount=amount_units / USDC_UNIT,
            address=destination,
            network=settings.OBiex_WITHDRAWAL_NETWORK,
            narration="Reach escrow float",
        )
    except (ObiexNotConfigured, ObiexError) as exc:
        raise TreasuryError(str(exc)) from exc

    reference = (
        withdrawal.get("reference")
        or withdrawal.get("id")
        or (withdrawal.get("payout") or {}).get("id")
    )

    record = TreasuryTransfer(
        reference=str(reference) if reference else None,
        amount_units=amount_units,
        currency=settings.OBiex_COLLECTION_CURRENCY,
        network=settings.OBiex_WITHDRAWAL_NETWORK,
        destination=destination,
        status=TreasuryTransferStatus.PENDING,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return record


async def plan_top_up(
    *,
    required_units: int,
    onchain: int | None = None,
    provider: int | None = None,
) -> dict:
    """Work out what the treasury should do.

    Returns the on-chain balance, the provider balance, the shortfall, and the
    amount to withdraw. Nothing is withdrawn here: a withdrawal is a money
    movement and is only made by `top_up`.
    """
    onchain = onchain if onchain is not None else await onchain_balance()
    provider = provider if provider is not None else await provider_balance()

    shortfall = max(required_units - onchain, 0)
    target = settings.REACH_TREASURY_TARGET_UNITS

    # Sweep down to the target rather than taking exactly the shortfall, so
    # the next few jobs do not each need their own withdrawal.
    withdraw = max(provider - target, 0)
    if withdraw < shortfall:
        withdraw = min(provider, max(shortfall, target))

    minimum = settings.REACH_TREASURY_MIN_WITHDRAWAL_UNITS
    if withdraw < minimum:
        withdraw = 0

    return {
        "onchain_units": onchain,
        "provider_units": provider,
        "required_units": required_units,
        "shortfall_units": shortfall,
        "withdraw_units": withdraw,
        "ready": onchain >= required_units,
    }


async def top_up(db: AsyncSession, *, required_units: int) -> dict:
    """Top the on-chain float up if it cannot cover `required_units`."""
    plan = await plan_top_up(required_units=required_units)

    if plan["ready"]:
        return plan

    if not plan["withdraw_units"]:
        return plan

    record = await request_withdrawal(
        db, amount_units=plan["withdraw_units"], address=None
    )

    plan["transfer_id"] = record.id
    plan["transfer_reference"] = record.reference
    return plan


async def get_transfer(
    db: AsyncSession, reference: str
) -> TreasuryTransfer | None:
    result = await db.execute(
        select(TreasuryTransfer).where(TreasuryTransfer.reference == reference)
    )
    return result.scalar_one_or_none()


async def mark_transfer(
    db: AsyncSession,
    transfer: TreasuryTransfer,
    *,
    status: TreasuryTransferStatus,
    tx_hash: str | None = None,
) -> TreasuryTransfer:
    transfer.status = status
    if tx_hash:
        transfer.tx_hash = tx_hash
    transfer.processed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(transfer)
    return transfer
