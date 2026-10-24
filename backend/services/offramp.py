"""Provider naira off-ramp.

The provider keeps custody of their Solana wallet. Reach creates a unique
Obiex USDC-on-Solana deposit address, the provider sends USDC to it, Obiex
credits Reach's USDC wallet, and Reach swaps to NGNX and withdraws naira to
the provider's bank account.

This is deliberately a *deposit-address* off-ramp, not a custodial wallet:

* Reach never holds the provider's private key.
* The on-chain payout still goes to the provider's own wallet.
* The only custody is the brief period between the deposit and the bank
  payout, and every step is recorded against one row.

Live money movement is disabled by ``REACH_OFFRAMP_ENABLED`` until Obiex
confirms third-party bank payouts and USDC/SOL deposits on the business
account.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from decimal import ROUND_DOWN, Decimal, InvalidOperation
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core import settings
from core.obiex import ObiexError, ObiexNotConfigured, get_obiex_client
from models import OffRampWithdrawal, PaymentProfile, User
from payment_validation import (
    PaymentProfileValidationError,
    validate_solana_address,
)
from schemas.enums import OffRampStatus

USDC_UNIT = 10**6


class OffRampError(RuntimeError):
    pass


class OffRampDisabled(OffRampError):
    pass


class OffRampNotFound(OffRampError):
    pass


class OffRampConflict(OffRampError):
    pass


class OffRampAmountError(OffRampError):
    pass


class OffRampNotReady(OffRampError):
    pass


class OffRampPartialSwap(OffRampError):
    """A swap leg executed but Reach could not confirm the final naira amount.

    This is treated as held, not failed, because retrying could swap again
    from a wallet that no longer holds the original USDC.
    """

    def __init__(self, message: str, reference: str | None = None):
        super().__init__(message)
        self.reference = reference


def ensure_enabled() -> None:
    if not settings.REACH_OFFRAMP_ENABLED:
        raise OffRampDisabled(
            "Naira off-ramp is not enabled yet. Contact support to arrange a payout."
        )


def to_usdc_units_exact(amount) -> int:
    """Convert USDC to base units without silently rounding.

    A provider cannot ask for 1.0000001 USDC and have us pay 1.000000 USDC.
    """
    try:
        value = Decimal(str(amount))
    except (InvalidOperation, ValueError) as exc:
        raise OffRampAmountError("The USDC amount is not valid") from exc

    if value <= 0:
        raise OffRampAmountError("The USDC amount must be positive")

    units = value * USDC_UNIT
    if units != units.to_integral_value():
        raise OffRampAmountError(
            "The USDC amount can have at most 6 decimal places"
        )

    return int(units)


def _usdc_decimal(units: int) -> Decimal:
    return Decimal(units) / USDC_UNIT


def _kobo_exact(amount) -> int:
    """Convert a naira amount to kobo, rejecting sub-kobo precision."""
    try:
        value = Decimal(str(amount)) * 100
    except (InvalidOperation, ValueError) as exc:
        raise OffRampAmountError("The naira amount is not valid") from exc

    if value != value.to_integral_value():
        raise OffRampAmountError("The payout has sub-kobo precision")

    return int(value)


def _floor_kobo(amount: Decimal) -> int:
    return int((amount * 100).to_integral_value(rounding=ROUND_DOWN))


def _active_statuses() -> tuple[OffRampStatus, ...]:
    return (
        OffRampStatus.AWAITING_DEPOSIT,
        OffRampStatus.PARTIALLY_FUNDED,
        OffRampStatus.DEPOSIT_CONFIRMED,
        OffRampStatus.WITHDRAWING,
        OffRampStatus.HELD,
        OffRampStatus.FAILED,
        OffRampStatus.REFUNDING,
    )


async def _get_active(
    db: AsyncSession, user_id: int
) -> OffRampWithdrawal | None:
    result = await db.execute(
        select(OffRampWithdrawal)
        .where(
            OffRampWithdrawal.user_id == user_id,
            OffRampWithdrawal.status.in_(_active_statuses()),
        )
        .order_by(OffRampWithdrawal.id.desc())
    )
    return result.scalars().first()


async def _get_profile(
    db: AsyncSession, user_id: int
) -> PaymentProfile | None:
    result = await db.execute(
        select(PaymentProfile).where(PaymentProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_withdrawal(
    db: AsyncSession, withdrawal_id: int, *, user_id: int | None = None
) -> OffRampWithdrawal:
    withdrawal = await db.get(OffRampWithdrawal, withdrawal_id)
    if withdrawal is None:
        raise OffRampNotFound("That payout was not found")
    if user_id is not None and withdrawal.user_id != user_id:
        raise OffRampNotFound("That payout was not found")
    return withdrawal


async def list_withdrawals(
    db: AsyncSession, *, user_id: int
) -> list[OffRampWithdrawal]:
    result = await db.execute(
        select(OffRampWithdrawal)
        .where(OffRampWithdrawal.user_id == user_id)
        .order_by(OffRampWithdrawal.id.desc())
    )
    return list(result.scalars().all())


async def get_by_deposit_address(
    db: AsyncSession, address: str
) -> OffRampWithdrawal | None:
    result = await db.execute(
        select(OffRampWithdrawal).where(
            OffRampWithdrawal.deposit_address == address
        )
    )
    return result.scalar_one_or_none()


async def get_by_provider_reference(
    db: AsyncSession, reference: str
) -> OffRampWithdrawal | None:
    result = await db.execute(
        select(OffRampWithdrawal).where(
            OffRampWithdrawal.provider_reference == reference
        )
    )
    return result.scalar_one_or_none()


async def get_by_provider_transaction_id(
    db: AsyncSession, transaction_id: str
) -> OffRampWithdrawal | None:
    result = await db.execute(
        select(OffRampWithdrawal).where(
            OffRampWithdrawal.provider_withdrawal_id == transaction_id
        )
    )
    return result.scalar_one_or_none()


async def get_by_refund_reference(
    db: AsyncSession, reference: str
) -> OffRampWithdrawal | None:
    result = await db.execute(
        select(OffRampWithdrawal).where(
            OffRampWithdrawal.refund_reference == reference
        )
    )
    return result.scalar_one_or_none()


async def get_by_refund_transaction_id(
    db: AsyncSession, transaction_id: str
) -> OffRampWithdrawal | None:
    result = await db.execute(
        select(OffRampWithdrawal).where(
            OffRampWithdrawal.refund_transaction_id == transaction_id
        )
    )
    return result.scalar_one_or_none()


def _normalise_name(value: str | None) -> str:
    return re.sub(r"[^a-z]", "", (value or "").casefold())


def _name_tokens(value: str | None) -> set[str]:
    return {token for token in re.findall(r"[a-z]+", (value or "").casefold()) if token}


def names_match(user: User, resolved_name: str | None) -> bool:
    """Check the bank account belongs to the provider.

    Bank account names are often upper case, include middle names, or drop
    one of the names. Normalise first, then require both the first and last
    name to be present.
    """
    if not resolved_name:
        return False

    expected = _normalise_name(f"{user.first_name or ''}{user.last_name or ''}")
    actual = _normalise_name(resolved_name)

    if expected and (expected == actual or expected in actual or actual in expected):
        return True

    expected_tokens = _name_tokens(f"{user.first_name or ''} {user.last_name or ''}")
    actual_tokens = _name_tokens(resolved_name)

    return bool(expected_tokens) and expected_tokens.issubset(actual_tokens)


async def _sell_rate() -> Decimal:
    client = get_obiex_client()
    try:
        rates = await client.get_fiat_rates()
    except (ObiexError, ObiexNotConfigured) as exc:
        raise OffRampError(str(exc)) from exc

    for entry in rates or []:
        currency = str(entry.get("currency", "")).upper()
        if currency not in ("NGNX", "NGN"):
            continue
        rate = entry.get("sellRate")
        if rate is None:
            continue
        try:
            value = Decimal(str(rate))
        except InvalidOperation as exc:
            raise OffRampError("Obiex returned an invalid naira rate") from exc
        if value <= 0:
            raise OffRampError("Obiex returned an invalid naira rate")
        return value

    raise OffRampError("No naira rate is available right now")


async def quote_offramp(amount_usdc) -> dict:
    """An indicative quote. The final rate is the executed swap's rate."""
    ensure_enabled()

    units = to_usdc_units_exact(amount_usdc)
    _validate_amount(units)

    rate = await _sell_rate()
    gross = (_usdc_decimal(units) * rate)
    gross_kobo = _floor_kobo(gross)

    fee_kobo = min(settings.REACH_OFFRAMP_FIAT_FEE_KOBO, gross_kobo)
    net_kobo = max(gross_kobo - fee_kobo, 0)

    if net_kobo < settings.REACH_OFFRAMP_MIN_NGN_KOBO:
        minimum = settings.REACH_OFFRAMP_MIN_NGN_KOBO / 100
        raise OffRampAmountError(
            f"The payout after the estimated fee must be at least "
            f"NGN {minimum:,.2f}"
        )

    return {
        "amount_usdc_units": units,
        "rate_ngn_per_usdc": rate,
        "gross_ngn_kobo": gross_kobo,
        "fee_kobo": fee_kobo,
        "net_ngn_kobo": net_kobo,
        "min_ngn_kobo": settings.REACH_OFFRAMP_MIN_NGN_KOBO,
        "expires_at": datetime.now(timezone.utc)
        + timedelta(seconds=settings.REACH_OFFRAMP_QUOTE_TTL_SECONDS),
        "indicative": True,
    }


def _validate_amount(units: int) -> None:
    if units < settings.REACH_OFFRAMP_MIN_USDC_UNITS:
        minimum = settings.REACH_OFFRAMP_MIN_USDC_UNITS / USDC_UNIT
        raise OffRampAmountError(
            f"The minimum off-ramp is {minimum:g} USDC"
        )

    if units > settings.REACH_OFFRAMP_MAX_USDC_UNITS:
        maximum = settings.REACH_OFFRAMP_MAX_USDC_UNITS / USDC_UNIT
        raise OffRampAmountError(
            f"The maximum off-ramp is {maximum:g} USDC per request"
        )


async def _banks(client) -> list[dict]:
    try:
        return await client.get_naira_banks()
    except (ObiexError, ObiexNotConfigured) as exc:
        raise OffRampError(str(exc)) from exc


def _network_is_receivable(
    networks: dict, currency: str, network: str
) -> bool:
    """Check Obiex can receive this currency/network pair right now."""
    entry = None
    for key, value in (networks or {}).items():
        if str(key).upper() == currency.upper():
            entry = value
            break

    if not isinstance(entry, dict):
        return False

    for item in entry.get("networks") or []:
        if not isinstance(item, dict):
            continue
        code = str(item.get("networkCode") or item.get("networkName") or "").upper()
        if code == network.upper() and item.get("isReceivable") is True:
            return True

    return False


def _bank_code_matches(value, code: str) -> bool:
    candidate = str(value or "").strip()
    if candidate == code:
        return True
    if candidate.isdigit() and code.isdigit():
        return int(candidate) == int(code)
    return False


def _bank_for(banks: list[dict], bank_code: str) -> dict | None:
    code = str(bank_code).strip()
    for bank in banks or []:
        if _bank_code_matches(bank.get("sortCode"), code):
            return bank
        if str(bank.get("uuid") or "").strip() == code:
            return bank
    return None


async def list_banks() -> list[dict]:
    # Listing banks is read-only. Keep it available even while live payouts
    # are disabled so the frontend can build the payout form.
    client = get_obiex_client()
    banks = await _banks(client)
    return [
        {
            "name": str(bank.get("name") or "").strip(),
            "code": str(bank.get("sortCode") or bank.get("uuid") or "").strip(),
            "bank_id": (
                str(bank.get("uuid")).strip() if bank.get("uuid") else None
            ),
        }
        for bank in banks
        if bank.get("name") and (bank.get("sortCode") or bank.get("uuid"))
    ]


async def resolve_account(
    *,
    bank_code: str,
    account_number: str,
) -> dict:
    """Resolve a Nigerian bank account without creating a payout.

    Obiex's OpenAPI documents ``sortCode`` while its Node SDK uses ``bankId``.
    Try the documented identifier first, then the SDK's identifier.
    """
    code = (bank_code or "").strip()
    number = (account_number or "").strip()
    if not code or not number:
        raise OffRampAmountError("A bank and account number are required")

    client = get_obiex_client()
    banks = await _banks(client)
    bank = _bank_for(banks, code)
    if bank is None:
        raise OffRampError("That bank is not supported for naira payouts")

    try:
        resolved = await client.resolve_naira_account(
            account_number=number,
            bank_code=code,
        )
        if not (resolved or {}).get("accountName"):
            resolved = await client.resolve_naira_account(
                account_number=number,
                bank_id=code,
            )
    except (ObiexError, ObiexNotConfigured) as exc:
        raise OffRampError(str(exc)) from exc

    resolved_name = (resolved or {}).get("accountName")
    if not resolved_name:
        raise OffRampError(
            "We could not verify that bank account. Check the bank and account number."
        )

    bank_name = str(bank.get("name") or "").strip()
    resolved_code = (
        code
        if _bank_code_matches(bank.get("sortCode"), code)
        else str(bank.get("sortCode") or code).strip()
    )

    return {
        "account_name": str(resolved_name),
        "account_number": str(resolved.get("accountNumber") or number),
        "bank_name": bank_name,
        "bank_code": resolved_code,
        "bank_id": str(bank.get("uuid")).strip() if bank.get("uuid") else None,
    }


async def create_withdrawal(
    db: AsyncSession,
    *,
    user: User,
    amount_usdc,
    bank_code: str | None = None,
    bank_account_number: str | None = None,
    bank_account_name: str | None = None,
    idempotency_key: str | None = None,
) -> OffRampWithdrawal:
    """Create a unique deposit address and a pending off-ramp row."""
    ensure_enabled()

    if idempotency_key is not None:
        idempotency_key = idempotency_key.strip() or None

    if idempotency_key and len(idempotency_key) > 100:
        raise OffRampError("The idempotency key is too long")

    if idempotency_key:
        existing = (
            await db.execute(
                select(OffRampWithdrawal).where(
                    OffRampWithdrawal.idempotency_key == idempotency_key
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            if existing.user_id != user.id:
                raise OffRampConflict("That idempotency key is already in use")
            return existing

    units = to_usdc_units_exact(amount_usdc)
    _validate_amount(units)

    active = await _get_active(db, user.id)
    if active is not None:
        raise OffRampConflict(
            "You already have a payout in progress "
            f"({active.reference}). Finish or cancel it first."
        )

    profile = await _get_profile(db, user.id)
    if profile is None:
        raise OffRampNotReady(
            "Complete your payment profile, including your bank details, first"
        )

    if not (user.first_name or "").strip() or not (user.last_name or "").strip():
        raise OffRampNotReady(
            "Add your first and last name before requesting a naira payout"
        )

    if not (getattr(user, "onchain_address", None) or "").strip():
        raise OffRampNotReady(
            "Add your Solana wallet address before requesting a naira payout"
        )

    try:
        validate_solana_address(str(user.onchain_address))
    except PaymentProfileValidationError as exc:
        raise OffRampNotReady(str(exc)) from exc

    code = (bank_code or profile.bank_code or "").strip()
    account_number = (
        bank_account_number or profile.bank_account_number or ""
    ).strip()

    if not code or not account_number:
        raise OffRampNotReady(
            "Add a bank code and account number before requesting a payout"
        )

    client = get_obiex_client()

    try:
        resolved = await client.resolve_naira_account(
            account_number=account_number,
            bank_code=code,
        )
        if not (resolved or {}).get("accountName"):
            # The public OpenAPI documents `sortCode`; the Node SDK uses
            # `bankId`. Try the other identifier before rejecting the account.
            resolved = await client.resolve_naira_account(
                account_number=account_number,
                bank_id=code,
            )
    except (ObiexError, ObiexNotConfigured) as exc:
        raise OffRampError(str(exc)) from exc

    resolved_name = (resolved or {}).get("accountName")
    if not resolved_name:
        raise OffRampError(
            "We could not verify that bank account. Check the bank and account number."
        )

    if settings.REACH_OFFRAMP_REQUIRE_NAME_MATCH and not names_match(
        user, resolved_name
    ):
        raise OffRampError(
            "The bank account name must match your Reach name. "
            "Use an account in your own name."
        )

    banks = await _banks(client)
    bank = _bank_for(banks, code)
    if bank is None:
        raise OffRampError("That bank is not supported for naira payouts")

    bank_name = str(bank.get("name") or "").strip()
    bank_code_value = (
        code
        if _bank_code_matches(bank.get("sortCode"), code)
        else str(bank.get("sortCode") or code).strip()
    )

    try:
        active_networks = await client.get_active_networks()
    except (ObiexError, ObiexNotConfigured) as exc:
        raise OffRampError(str(exc)) from exc

    if not _network_is_receivable(
        active_networks,
        settings.REACH_OFFRAMP_SOURCE_CURRENCY,
        settings.REACH_OFFRAMP_NETWORK,
    ):
        raise OffRampNotReady(
            f"Obiex cannot receive "
            f"{settings.REACH_OFFRAMP_SOURCE_CURRENCY} on "
            f"{settings.REACH_OFFRAMP_NETWORK} right now"
        )

    quote = await quote_offramp(_usdc_decimal(units))

    if quote["net_ngn_kobo"] < settings.REACH_OFFRAMP_MIN_NGN_KOBO:
        minimum = settings.REACH_OFFRAMP_MIN_NGN_KOBO / 100
        raise OffRampAmountError(
            f"The payout would be below the ₦{minimum:,.0f} minimum"
        )

    reference = f"offramp-{uuid4().hex}"
    identifier = f"reach-{reference}"

    try:
        address = await client.create_deposit_address(
            unique_user_identifier=identifier,
            currency=settings.REACH_OFFRAMP_SOURCE_CURRENCY,
            network=settings.REACH_OFFRAMP_NETWORK,
        )
    except (ObiexError, ObiexNotConfigured) as exc:
        raise OffRampError(str(exc)) from exc

    deposit_address = (address or {}).get("value")
    if not deposit_address:
        raise OffRampError("Obiex did not return a deposit address")

    withdrawal = OffRampWithdrawal(
        user_id=user.id,
        reference=reference,
        idempotency_key=idempotency_key,
        status=OffRampStatus.AWAITING_DEPOSIT,
        amount_usdc_units=units,
        received_usdc_units=0,
        quoted_rate=quote["rate_ngn_per_usdc"],
        gross_ngn_kobo=quote["gross_ngn_kobo"],
        fee_kobo=quote["fee_kobo"],
        net_ngn_kobo=quote["net_ngn_kobo"],
        bank_name=bank_name,
        bank_code=bank_code_value,
        bank_account_number=str(resolved.get("accountNumber") or account_number),
        bank_account_name=str(resolved_name),
        deposit_address=str(deposit_address),
        deposit_address_reference=(
            str(address.get("reference") or address.get("id"))
            if address.get("reference") or address.get("id")
            else None
        ),
        deposit_currency=settings.REACH_OFFRAMP_SOURCE_CURRENCY,
        deposit_network=settings.REACH_OFFRAMP_NETWORK,
        expires_at=datetime.now(timezone.utc)
        + timedelta(seconds=settings.REACH_OFFRAMP_DEPOSIT_TTL_SECONDS),
    )

    db.add(withdrawal)
    try:
        await db.commit()
        await db.refresh(withdrawal)
    except IntegrityError as exc:
        await db.rollback()
        if idempotency_key:
            existing = (
                await db.execute(
                    select(OffRampWithdrawal).where(
                        OffRampWithdrawal.idempotency_key == idempotency_key,
                        OffRampWithdrawal.user_id == user.id,
                    )
                )
            ).scalar_one_or_none()
            if existing is not None:
                return existing
        raise OffRampConflict(
            "Could not create a unique payout request. Please retry."
        ) from exc

    return withdrawal


def _pair_has(pairs: list[dict], source: str, target: str) -> bool:
    for pair in pairs or []:
        if not isinstance(pair, dict):
            continue
        pair_source = pair.get("source")
        pair_target = pair.get("target")
        source_code = (
            pair_source.get("code") if isinstance(pair_source, dict) else pair_source
        )
        target_code = (
            pair_target.get("code") if isinstance(pair_target, dict) else pair_target
        )
        if (
            str(source_code or "").upper() == source.upper()
            and str(target_code or "").upper() == target.upper()
        ):
            return True
    return False


def _swap_received(payload: dict) -> Decimal:
    for key in ("amountReceived", "targetAmount", "received"):
        value = payload.get(key)
        if value is None:
            continue
        try:
            return Decimal(str(value))
        except InvalidOperation as exc:
            raise OffRampError("Obiex returned an invalid swap amount") from exc
    raise OffRampError("Obiex did not return the swapped naira amount")


def _swap_reference(payload: dict) -> str | None:
    quote = payload.get("quote")
    quote_id = quote.get("id") if isinstance(quote, dict) else None
    value = payload.get("id") or payload.get("reference") or quote_id
    return str(value) if value else None


async def _swap_to_naira(
    client, units: int
) -> tuple[Decimal, str | None, Decimal | None]:
    """Swap USDC to NGNX, falling back through USDT if there is no direct pair."""
    amount = float(_usdc_decimal(units))
    source = settings.REACH_OFFRAMP_SOURCE_CURRENCY
    target = settings.REACH_OFFRAMP_TARGET_CURRENCY
    fallback = settings.REACH_OFFRAMP_FALLBACK_CURRENCY

    pairs = []
    try:
        pairs = await client.get_trade_pairs()
    except (ObiexError, ObiexNotConfigured):
        # If pair discovery is unavailable, try the direct pair anyway.
        pairs = []

    direct = not pairs or _pair_has(pairs, source, target)
    fallback_possible = _pair_has(pairs, source, fallback) and _pair_has(
        pairs, fallback, target
    )

    if direct:
        try:
            payload = await client.instant_swap(
                source_id=source,
                target_id=target,
                amount=amount,
            )
        except (ObiexError, ObiexNotConfigured):
            if not fallback_possible:
                raise
        else:
            try:
                received = _swap_received(payload)
            except OffRampError as exc:
                raise OffRampPartialSwap(
                    str(exc), reference=_swap_reference(payload)
                ) from exc

            rate_value = None
            if payload.get("rate") is not None:
                try:
                    rate_value = Decimal(str(payload["rate"]))
                except InvalidOperation:
                    rate_value = None

            return received, _swap_reference(payload), rate_value

    if not fallback_possible:
        raise OffRampError(
            f"Obiex has no {source}->{target} swap route right now"
        )

    first = await client.instant_swap(
        source_id=source,
        target_id=fallback,
        amount=amount,
    )
    first_reference = _swap_reference(first)

    try:
        intermediate = _swap_received(first)
    except OffRampError as exc:
        raise OffRampPartialSwap(
            f"The {source}->{fallback} swap executed but its amount was not readable",
            reference=first_reference,
        ) from exc

    try:
        second = await client.instant_swap(
            source_id=fallback,
            target_id=target,
            amount=float(intermediate),
        )
    except (ObiexError, ObiexNotConfigured) as exc:
        raise OffRampPartialSwap(
            f"The {source}->{fallback} swap executed, but the "
            f"{fallback}->{target} swap failed",
            reference=first_reference,
        ) from exc

    second_reference = _swap_reference(second)
    references = [first_reference, second_reference]
    reference = " -> ".join(ref for ref in references if ref) or None

    try:
        received = _swap_received(second)
    except OffRampError as exc:
        raise OffRampPartialSwap(
            f"The {fallback}->{target} swap executed but its amount was not readable",
            reference=reference,
        ) from exc

    rate = received / _usdc_decimal(units) if units else None
    return received, reference, rate


def _available_ngn(payload: dict) -> Decimal | None:
    candidates = [
        payload.get("availableBalance"),
        payload.get("balance"),
        (payload.get("wallet") or {}).get("availableBalance")
        if isinstance(payload.get("wallet"), dict)
        else None,
    ]
    for candidate in candidates:
        if candidate is None:
            continue
        try:
            return Decimal(str(candidate))
        except InvalidOperation:
            continue
    return None


async def settle_withdrawal(
    db: AsyncSession, withdrawal: OffRampWithdrawal
) -> OffRampWithdrawal:
    """Swap the received USDC and send naira to the provider's bank."""
    if withdrawal.status in (OffRampStatus.PAID, OffRampStatus.REFUNDED):
        return withdrawal

    if withdrawal.received_usdc_units < withdrawal.amount_usdc_units:
        raise OffRampError("The deposit is not complete yet")

    if withdrawal.provider_reference:
        raise OffRampConflict(
            "A bank payout request already exists for this off-ramp. "
            "Reconcile it instead of creating another payout."
        )

    try:
        client = get_obiex_client()
    except (ObiexError, ObiexNotConfigured) as exc:
        withdrawal.status = OffRampStatus.FAILED
        withdrawal.failure_reason = str(exc)[:1000]
        await db.commit()
        raise OffRampError(str(exc)) from exc

    if withdrawal.swapped_at:
        # A previous attempt already swapped the USDC. Reuse the naira in the
        # wallet so a bank-payout retry cannot swap the same USDC twice.
        if not withdrawal.gross_ngn_kobo:
            raise OffRampError(
                "The swap was recorded without a naira amount; support must reconcile it"
            )
        gross_kobo = int(withdrawal.gross_ngn_kobo)
        received_ngn = Decimal(gross_kobo) / 100
    else:
        try:
            received_ngn, swap_reference, swap_rate = await _swap_to_naira(
                client, withdrawal.received_usdc_units
            )
        except OffRampPartialSwap as exc:
            withdrawal.status = OffRampStatus.HELD
            withdrawal.swapped_at = datetime.now(timezone.utc)
            withdrawal.swap_reference = exc.reference
            withdrawal.failure_reason = (
                f"{exc}. The USDC has already been converted; support must "
                "finish or reverse the swap before another payout."
            )[:1000]
            await db.commit()
            raise
        except OffRampError as exc:
            withdrawal.status = OffRampStatus.HELD
            withdrawal.failure_reason = str(exc)[:1000]
            await db.commit()
            raise
        except (ObiexError, ObiexNotConfigured) as exc:
            withdrawal.status = OffRampStatus.FAILED
            withdrawal.failure_reason = str(exc)[:1000]
            await db.commit()
            raise OffRampError(str(exc)) from exc

        try:
            gross_kobo = _kobo_exact(received_ngn)
        except OffRampAmountError as exc:
            # The swap already happened. Persist that fact even though the
            # amount could not be represented exactly, so a retry cannot swap
            # the same USDC again.
            withdrawal.status = OffRampStatus.HELD
            withdrawal.swapped_at = datetime.now(timezone.utc)
            withdrawal.swap_reference = swap_reference
            withdrawal.swap_rate = swap_rate
            withdrawal.failure_reason = (
                f"The swap returned an amount Reach cannot settle ({exc}). "
                "The USDC has already been converted; support must finish or "
                "reverse the swap."
            )[:1000]
            await db.commit()
            raise OffRampPartialSwap(str(exc), reference=swap_reference) from exc

        withdrawal.gross_ngn_kobo = gross_kobo
        withdrawal.swap_reference = swap_reference
        withdrawal.swap_rate = swap_rate
        withdrawal.swapped_at = datetime.now(timezone.utc)
        await db.commit()

    if gross_kobo < settings.REACH_OFFRAMP_MIN_NGN_KOBO:
        withdrawal.status = OffRampStatus.HELD
        withdrawal.failure_reason = (
            "The converted payout is below the minimum naira payout. "
            "Support will reverse the swap or arrange the payout."
        )
        await db.commit()
        return withdrawal

    estimated_fee = min(
        withdrawal.fee_kobo or settings.REACH_OFFRAMP_FIAT_FEE_KOBO,
        gross_kobo,
    )
    if gross_kobo - estimated_fee < settings.REACH_OFFRAMP_MIN_NGN_KOBO:
        withdrawal.status = OffRampStatus.HELD
        withdrawal.failure_reason = (
            "The payout after the estimated bank fee is below the minimum "
            "naira payout. Support will review it."
        )
        await db.commit()
        return withdrawal

    if withdrawal.quoted_rate:
        expected_gross = (
            _usdc_decimal(withdrawal.received_usdc_units)
            * Decimal(withdrawal.quoted_rate)
            * 100
        )
        floor = expected_gross * (
            Decimal(10000 - settings.REACH_OFFRAMP_SLIPPAGE_BPS) / Decimal(10000)
        )
        if Decimal(gross_kobo) < floor:
            withdrawal.status = OffRampStatus.HELD
            withdrawal.failure_reason = (
                "The executed rate moved beyond the slippage limit. "
                "Support will review the converted funds."
            )
            await db.commit()
            return withdrawal

    try:
        balance = await client.get_wallet_balance(
            settings.REACH_OFFRAMP_TARGET_CURRENCY
        )
        available = _available_ngn(balance)
        if available is not None and available < received_ngn:
            raise OffRampError("The naira wallet balance is too low for this payout")
    except (ObiexError, ObiexNotConfigured) as exc:
        withdrawal.status = OffRampStatus.FAILED
        withdrawal.failure_reason = str(exc)[:1000]
        await db.commit()
        raise OffRampError(str(exc)) from exc
    except OffRampError as exc:
        withdrawal.status = OffRampStatus.FAILED
        withdrawal.failure_reason = str(exc)[:1000]
        await db.commit()
        raise

    try:
        payout = await client.request_fiat_withdrawal(
            currency=settings.REACH_OFFRAMP_TARGET_CURRENCY,
            amount=float(received_ngn),
            account_number=withdrawal.bank_account_number,
            account_name=withdrawal.bank_account_name,
            bank_name=withdrawal.bank_name,
            bank_code=withdrawal.bank_code,
            narration=f"Reach payout {withdrawal.reference}",
        )
    except (ObiexError, ObiexNotConfigured) as exc:
        withdrawal.status = OffRampStatus.FAILED
        withdrawal.failure_reason = str(exc)[:1000]
        await db.commit()
        raise OffRampError(str(exc)) from exc

    payout_data = payout.get("payout") if isinstance(payout.get("payout"), dict) else {}

    # Store the provider identifiers before parsing any money fields. If the
    # response is malformed after this point, the payout can still be
    # reconciled instead of being submitted a second time.
    reference_value = (
        payout.get("reference")
        or payout_data.get("transactionId")
        or payout.get("id")
    )
    withdrawal.provider_reference = (
        str(reference_value) if reference_value else None
    )
    withdrawal.provider_withdrawal_id = (
        str(payout.get("id"))
        if payout.get("id")
        else (
            str(payout_data.get("transactionId"))
            if payout_data.get("transactionId")
            else (
                str(payout_data.get("id"))
                if payout_data.get("id")
                else None
            )
        )
    )

    provider_status = str(
        payout_data.get("status") or payout.get("status") or ""
    ).upper()

    try:
        fee_kobo = _kobo_exact(
            payout_data.get("fee", payout.get("fee", 0)) or 0
        )
        paid_ngn = payout_data.get("payoutAmount", payout.get("payoutAmount"))
        net_kobo = (
            _kobo_exact(paid_ngn)
            if paid_ngn is not None
            else max(gross_kobo - fee_kobo, 0)
        )
    except OffRampAmountError as exc:
        withdrawal.status = OffRampStatus.HELD
        withdrawal.failure_reason = (
            "Obiex accepted the bank payout but returned an amount Reach "
            f"cannot settle ({exc}). Support must reconcile it."
        )[:1000]
        await db.commit()
        raise OffRampError(
            "The bank payout was submitted but its amount needs manual review"
        ) from exc

    withdrawal.fee_kobo = fee_kobo
    withdrawal.net_ngn_kobo = net_kobo

    if provider_status == "SUCCESSFUL":
        withdrawal.status = OffRampStatus.PAID
        withdrawal.paid_at = datetime.now(timezone.utc)
    elif provider_status in ("FAILED", "REJECTED"):
        withdrawal.status = OffRampStatus.FAILED
        withdrawal.failure_reason = (
            f"Obiex rejected the bank payout ({provider_status})."
        )
    elif not withdrawal.provider_reference:
        withdrawal.status = OffRampStatus.HELD
        withdrawal.failure_reason = (
            "Obiex accepted the bank payout but returned no reference. "
            "Support must reconcile it before another payout."
        )
    else:
        withdrawal.status = OffRampStatus.WITHDRAWING

    await db.commit()
    return withdrawal


async def handle_deposit(
    db: AsyncSession, withdrawal: OffRampWithdrawal, payload: dict
) -> OffRampWithdrawal:
    """Record a confirmed USDC deposit and start the payout."""
    if payload.get("status") != "CONFIRMED":
        return withdrawal

    transaction_id = str(
        payload.get("transactionId")
        or payload.get("reference")
        or payload.get("hash")
        or ""
    ).strip()

    if (
        transaction_id
        and withdrawal.deposit_provider_reference == transaction_id
    ):
        return withdrawal

    currency = str(payload.get("currency") or "").upper()
    expected_currency = (
        withdrawal.deposit_currency or settings.REACH_OFFRAMP_SOURCE_CURRENCY
    ).upper()
    if currency and currency != expected_currency:
        withdrawal.status = OffRampStatus.HELD
        withdrawal.failure_reason = (
            f"The deposit was {currency}, not {expected_currency}. "
            "Support will review it."
        )
        await db.commit()
        return withdrawal

    amount = payload.get("amount")
    if amount is None:
        raise OffRampError("The deposit has no amount")

    units = to_usdc_units_exact(amount)
    withdrawal.received_usdc_units = (withdrawal.received_usdc_units or 0) + units
    withdrawal.deposit_provider_reference = transaction_id or None
    withdrawal.deposit_tx_hash = (
        str(payload.get("hash")) if payload.get("hash") else None
    )

    # Once a payout has started (or has already finished), a new deposit is
    # never rolled into an automatic payout. Hold it for review or refund.
    if withdrawal.status in (OffRampStatus.PAID, OffRampStatus.REFUNDED):
        withdrawal.failure_reason = (
            "A late USDC deposit arrived after this payout closed. "
            "Support will review or refund it."
        )
        await db.commit()
        return withdrawal

    if withdrawal.status in (
        OffRampStatus.CANCELLED,
        OffRampStatus.EXPIRED,
        OffRampStatus.DEPOSIT_CONFIRMED,
        OffRampStatus.WITHDRAWING,
        OffRampStatus.HELD,
        OffRampStatus.FAILED,
        OffRampStatus.REFUNDING,
    ):
        withdrawal.status = OffRampStatus.HELD
        withdrawal.failure_reason = (
            "USDC arrived after the payout was already in progress or closed. "
            "Support will review or refund it."
        )
        await db.commit()
        return withdrawal

    tolerance = max(USDC_UNIT, withdrawal.amount_usdc_units // 100)

    if withdrawal.received_usdc_units < withdrawal.amount_usdc_units:
        withdrawal.status = OffRampStatus.PARTIALLY_FUNDED
        withdrawal.failure_reason = (
            "The deposit is below the requested amount. Send the remainder to "
            "the same address or contact support for a refund."
        )
        await db.commit()
        return withdrawal

    if withdrawal.received_usdc_units > withdrawal.amount_usdc_units + tolerance:
        withdrawal.status = OffRampStatus.HELD
        withdrawal.failure_reason = (
            "The deposit is larger than requested. Support will review or "
            "refund the excess."
        )
        await db.commit()
        return withdrawal

    withdrawal.status = OffRampStatus.DEPOSIT_CONFIRMED
    withdrawal.deposit_confirmed_at = datetime.now(timezone.utc)
    withdrawal.failure_reason = None
    await db.commit()

    return await settle_withdrawal(db, withdrawal)


def _payload_status(payload: dict) -> str:
    status = payload.get("status")
    if not status and isinstance(payload.get("payout"), dict):
        status = payload["payout"].get("status")
    return str(status or "").upper()


async def handle_withdrawal(
    db: AsyncSession, withdrawal: OffRampWithdrawal, payload: dict
) -> OffRampWithdrawal:
    """Apply an Obiex WITHDRAWAL webhook to an off-ramp row."""
    if withdrawal.status in (OffRampStatus.PAID, OffRampStatus.REFUNDED):
        return withdrawal

    status = _payload_status(payload)

    if status == "SUCCESSFUL":
        if (
            withdrawal.status == OffRampStatus.FAILED
            and "rejected the bank payout"
            in (withdrawal.failure_reason or "")
        ):
            withdrawal.status = OffRampStatus.HELD
            withdrawal.failure_reason = (
                "Obiex reported this payout as rejected earlier and now as "
                "successful. Support must reconcile it before another payout."
            )
            await db.commit()
            return withdrawal

        preserve_note = (withdrawal.failure_reason or "").startswith(
            ("A late USDC", "USDC arrived after")
        )
        withdrawal.status = OffRampStatus.PAID
        withdrawal.paid_at = datetime.now(timezone.utc)
        # Keep a manual-review note (for example, a late deposit) if present.
        if not preserve_note:
            withdrawal.failure_reason = None
    elif status in ("FAILED", "REJECTED"):
        withdrawal.status = OffRampStatus.FAILED
        withdrawal.failure_reason = str(
            payload.get("message")
            or payload.get("reason")
            or f"Obiex reported {status}"
        )[:1000]
    else:
        withdrawal.status = OffRampStatus.WITHDRAWING

    await db.commit()
    return withdrawal


async def handle_refund(
    db: AsyncSession, withdrawal: OffRampWithdrawal, payload: dict
) -> OffRampWithdrawal:
    """Apply an Obiex WITHDRAWAL webhook to a USDC refund."""
    if withdrawal.status == OffRampStatus.REFUNDED:
        return withdrawal

    status = _payload_status(payload)

    if status == "SUCCESSFUL":
        withdrawal.status = OffRampStatus.REFUNDED
        withdrawal.refunded_at = datetime.now(timezone.utc)
        withdrawal.failure_reason = "USDC refunded to the provider wallet"
    elif status in ("FAILED", "REJECTED"):
        withdrawal.status = OffRampStatus.HELD
        withdrawal.failure_reason = str(
            payload.get("message") or "The USDC refund failed"
        )[:1000]
    else:
        withdrawal.status = OffRampStatus.REFUNDING

    await db.commit()
    return withdrawal


async def refresh_withdrawal(
    db: AsyncSession, withdrawal: OffRampWithdrawal
) -> OffRampWithdrawal:
    """Poll Obiex for a payout that already has a provider reference."""
    if not withdrawal.provider_reference:
        return withdrawal

    try:
        client = get_obiex_client()
    except (ObiexError, ObiexNotConfigured) as exc:
        raise OffRampError(str(exc)) from exc

    try:
        transaction = await client.get_transaction(
            str(withdrawal.provider_withdrawal_id or withdrawal.provider_reference)
        )
    except (ObiexError, ObiexNotConfigured) as exc:
        raise OffRampError(str(exc)) from exc

    if not isinstance(transaction, dict):
        raise OffRampError("Obiex returned no transaction state")

    return await handle_withdrawal(db, withdrawal, transaction)


async def cancel_withdrawal(
    db: AsyncSession, withdrawal: OffRampWithdrawal
) -> OffRampWithdrawal:
    if withdrawal.status not in (
        OffRampStatus.AWAITING_DEPOSIT,
        OffRampStatus.PARTIALLY_FUNDED,
    ):
        raise OffRampConflict("This payout can no longer be cancelled")

    if withdrawal.received_usdc_units:
        raise OffRampConflict(
            "USDC has already arrived. Contact support to refund it."
        )

    withdrawal.status = OffRampStatus.CANCELLED
    withdrawal.failure_reason = "Cancelled by the provider"
    await db.commit()
    return withdrawal


async def refund_withdrawal(
    db: AsyncSession, withdrawal: OffRampWithdrawal
) -> OffRampWithdrawal:
    """Return deposited USDC to the provider's own Solana address."""
    if withdrawal.status == OffRampStatus.PAID:
        raise OffRampConflict("This payout has already been paid to the bank")
    if withdrawal.status in (OffRampStatus.REFUNDED, OffRampStatus.REFUNDING):
        return withdrawal
    if (
        withdrawal.status == OffRampStatus.HELD
        and "refund but returned no reference"
        in (withdrawal.failure_reason or "")
    ):
        raise OffRampNotReady(
            "A refund was already submitted without a usable reference. "
            "Support must reconcile it before another refund."
        )
    if not withdrawal.received_usdc_units:
        withdrawal.status = OffRampStatus.REFUNDED
        withdrawal.refunded_at = datetime.now(timezone.utc)
        await db.commit()
        return withdrawal

    if withdrawal.swapped_at:
        raise OffRampNotReady(
            "This payout was already swapped to NGNX. Support must reverse the "
            "swap before returning USDC; retry the bank payout instead."
        )

    user = await db.get(User, withdrawal.user_id)
    address = getattr(user, "onchain_address", None)
    if not address:
        raise OffRampNotReady(
            "The provider has no Solana address for the refund"
        )

    try:
        address = validate_solana_address(str(address))
    except PaymentProfileValidationError as exc:
        raise OffRampNotReady(str(exc)) from exc

    try:
        client = get_obiex_client()
    except (ObiexError, ObiexNotConfigured) as exc:
        raise OffRampError(str(exc)) from exc

    amount = float(_usdc_decimal(withdrawal.received_usdc_units))

    try:
        refund = await client.request_crypto_withdrawal(
            currency=settings.REACH_OFFRAMP_SOURCE_CURRENCY,
            amount=amount,
            address=address,
            network=settings.REACH_OFFRAMP_NETWORK,
            narration=f"Reach off-ramp refund {withdrawal.reference}",
        )
    except (ObiexError, ObiexNotConfigured) as exc:
        raise OffRampError(str(exc)) from exc

    refund_payout = (
        refund.get("payout") if isinstance(refund.get("payout"), dict) else {}
    )
    reference_value = (
        refund.get("reference")
        or refund_payout.get("transferReference")
        or refund.get("id")
    )
    withdrawal.refund_reference = (
        str(reference_value) if reference_value else None
    )

    transaction_value = (
        refund.get("id")
        or refund_payout.get("transactionId")
        or refund_payout.get("id")
    )
    withdrawal.refund_transaction_id = (
        str(transaction_value) if transaction_value else None
    )

    if (
        not withdrawal.refund_reference
        and not withdrawal.refund_transaction_id
    ):
        withdrawal.status = OffRampStatus.HELD
        withdrawal.failure_reason = (
            "Obiex accepted the refund but returned no reference. "
            "Support must reconcile it before another refund."
        )
        await db.commit()
        raise OffRampError(
            "The refund was submitted but has no provider reference"
        )

    refund_status = str(
        refund_payout.get("status") or refund.get("status") or ""
    ).upper()

    if refund_status == "SUCCESSFUL":
        withdrawal.status = OffRampStatus.REFUNDED
        withdrawal.refunded_at = datetime.now(timezone.utc)
        withdrawal.failure_reason = "USDC refunded to the provider wallet"
    else:
        withdrawal.status = OffRampStatus.REFUNDING
        withdrawal.failure_reason = "USDC refund submitted to the provider wallet"

    await db.commit()
    return withdrawal


async def reconcile(db: AsyncSession) -> dict:
    """Expire stale deposit requests and poll in-flight bank payouts.

    Webhooks are the primary path; this is the safety net for a missed
    delivery. It also has to work when the feature flag is turned off after a
    payout was already in flight.
    """
    now = datetime.now(timezone.utc)
    expired = 0
    updated = 0

    result = await db.execute(
        select(OffRampWithdrawal).where(
            OffRampWithdrawal.status.in_(
                (OffRampStatus.AWAITING_DEPOSIT, OffRampStatus.PARTIALLY_FUNDED)
            ),
            OffRampWithdrawal.expires_at.is_not(None),
            OffRampWithdrawal.expires_at < now,
        )
    )

    for withdrawal in result.scalars().all():
        if withdrawal.received_usdc_units:
            continue
        withdrawal.status = OffRampStatus.EXPIRED
        withdrawal.failure_reason = "No USDC arrived before the deposit window closed"
        expired += 1

    # Persist expirations even if the provider client is unavailable.
    await db.commit()

    result = await db.execute(
        select(OffRampWithdrawal).where(
            OffRampWithdrawal.status.in_(
                (OffRampStatus.WITHDRAWING, OffRampStatus.HELD)
            ),
            OffRampWithdrawal.provider_reference.is_not(None),
        )
    )
    payouts = list(result.scalars().all())

    result = await db.execute(
        select(OffRampWithdrawal).where(
            OffRampWithdrawal.status.in_(
                (OffRampStatus.REFUNDING, OffRampStatus.HELD)
            ),
            OffRampWithdrawal.refund_reference.is_not(None),
        )
    )
    refunds = list(result.scalars().all())

    if not payouts and not refunds:
        return {"expired": expired, "updated": updated}

    try:
        client = get_obiex_client()
    except (ObiexError, ObiexNotConfigured) as exc:
        raise OffRampError(str(exc)) from exc

    for withdrawal in payouts:
        try:
            transaction = await client.get_transaction(
                str(
                    withdrawal.provider_withdrawal_id
                    or withdrawal.provider_reference
                )
            )
        except (ObiexError, ObiexNotConfigured):
            continue

        if not isinstance(transaction, dict):
            continue

        await handle_withdrawal(db, withdrawal, transaction)
        updated += 1

    for withdrawal in refunds:
        try:
            transaction = await client.get_transaction(
                str(
                    withdrawal.refund_transaction_id
                    or withdrawal.refund_reference
                )
            )
        except (ObiexError, ObiexNotConfigured):
            continue

        if not isinstance(transaction, dict):
            continue

        await handle_refund(db, withdrawal, transaction)
        updated += 1

    await db.commit()
    return {"expired": expired, "updated": updated}
