from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from DB.database import Base
from schemas.enums import (
    ChainTransactionStatus,
    FundingRail,
    OffRampStatus,
    TreasuryTransferStatus,
    PaymentStatus,
    PayoutStatus,
    ProvisioningStatus,
    WebhookStatus,
)

from .mixins import TimeStampMixin


class PaymentProfile(Base, TimeStampMixin):
    """The extra identity fields FossaPay needs before we can provision a customer."""

    __tablename__ = "payment_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        unique=True,
        index=True,
        nullable=False,
    )

    middle_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)

    address: Mapped[str] = mapped_column(String(255), nullable=False)

    city: Mapped[str] = mapped_column(String(100), nullable=False)

    country: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Nigeria",
    )

    # Nigerian identity. Obiex Business Collections need a BVN or NIN to
    # open a collection for a customer.
    bvn: Mapped[str | None] = mapped_column(String(20), nullable=True)

    nin: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Bank details, used when a provider's USDC is cashed out to NGN.
    bank_code: Mapped[str | None] = mapped_column(String(20), nullable=True)

    bank_account_number: Mapped[str | None] = mapped_column(String(30), nullable=True)

    bank_account_name: Mapped[str | None] = mapped_column(String(150), nullable=True)

    user = relationship("User", back_populates="payment_profile")


class FossaPayCustomer(Base, TimeStampMixin):
    """Maps a Reach user to their FossaPay customer, NGN wallet, and virtual account."""

    __tablename__ = "fossapay_customers"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        unique=True,
        index=True,
        nullable=False,
    )

    provider_customer_id: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=True,
    )

    wallet_id: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=True,
    )

    account_number: Mapped[str | None] = mapped_column(String(30), nullable=True)

    account_name: Mapped[str | None] = mapped_column(String(150), nullable=True)

    bank_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    bank_code: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # The customer's Solana address, held by FossaPay. This is where a
    # provider's USDC payout lands, and the address the relayer signs for.
    crypto_wallet_id: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=True,
    )

    crypto_wallet_address: Mapped[str | None] = mapped_column(String(120), nullable=True)

    crypto_network: Mapped[str | None] = mapped_column(String(20), nullable=True)

    status: Mapped[ProvisioningStatus] = mapped_column(
        Enum(ProvisioningStatus),
        nullable=False,
        default=ProvisioningStatus.PENDING,
    )

    last_error: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    user = relationship("User", back_populates="fossapay_customer")


class PaymentIntent(Base, TimeStampMixin):
    """One attempt to fund a task's escrow.

    The intent is the customer-facing side of Model 1: it records what the
    customer was asked to pay, on which rail, and whether the money made it
    all the way into the on-chain escrow.
    """

    __tablename__ = "payment_intents"

    id: Mapped[int] = mapped_column(primary_key=True)

    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id"),
        index=True,
        nullable=False,
    )

    reference: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    rail: Mapped[FundingRail] = mapped_column(
        Enum(FundingRail),
        nullable=False,
        default=FundingRail.OBIEX_FIAT,
    )

    amount_kobo: Mapped[int] = mapped_column(BigInteger, nullable=False)

    amount_payable_kobo: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # The escrow amount in USDC base units (6 decimals).
    usdc_amount: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus),
        nullable=False,
        default=PaymentStatus.PENDING,
    )

    provider_checkout_id: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=True,
    )

    # Provider-side identifiers: the Obiex collection reference, the FossaPay
    # checkout id, or the deposit address the customer paid into.
    provider_reference: Mapped[str | None] = mapped_column(
        String(150),
        unique=True,
        index=True,
        nullable=True,
    )

    provider_customer_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    network: Mapped[str | None] = mapped_column(String(20), nullable=True)

    deposit_address: Mapped[str | None] = mapped_column(String(120), nullable=True)

    bank_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    account_name: Mapped[str | None] = mapped_column(String(150), nullable=True)

    account_number: Mapped[str | None] = mapped_column(String(30), nullable=True)

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    failure_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class TreasuryTransfer(Base, TimeStampMixin):
    """A withdrawal of USDC from the payment provider into the escrow float.

    A fiat collection settles as USDC in the provider's wallet. The escrow is
    funded from the relayer's balance on Solana, so the money is withdrawn to
    it. Withdrawals are batched: the provider charges a fee per withdrawal.
    """

    __tablename__ = "treasury_transfers"

    id: Mapped[int] = mapped_column(primary_key=True)

    reference: Mapped[str | None] = mapped_column(
        String(150),
        unique=True,
        index=True,
        nullable=True,
    )

    amount_units: Mapped[int] = mapped_column(BigInteger, nullable=False)

    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="USDC",
    )

    network: Mapped[str | None] = mapped_column(String(20), nullable=True)

    destination: Mapped[str | None] = mapped_column(String(120), nullable=True)

    status: Mapped[TreasuryTransferStatus] = mapped_column(
        Enum(TreasuryTransferStatus),
        nullable=False,
        default=TreasuryTransferStatus.PENDING,
    )

    tx_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class ChainTransaction(Base, TimeStampMixin):
    """A transaction the relayer signed against the Reach program."""

    __tablename__ = "chain_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)

    job_id: Mapped[int | None] = mapped_column(
        ForeignKey("jobs.id"),
        index=True,
        nullable=True,
    )

    kind: Mapped[str] = mapped_column(String(40), nullable=False)

    idempotency_key: Mapped[str] = mapped_column(
        String(120),
        unique=True,
        index=True,
        nullable=False,
    )

    signature: Mapped[str | None] = mapped_column(
        String(128),
        unique=True,
        index=True,
        nullable=True,
    )

    status: Mapped[ChainTransactionStatus] = mapped_column(
        Enum(ChainTransactionStatus),
        nullable=False,
        default=ChainTransactionStatus.PENDING,
    )

    slot: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    error: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class Payout(Base, TimeStampMixin):
    """Release of a funded job to the provider's FossaPay wallet."""

    __tablename__ = "payouts"

    id: Mapped[int] = mapped_column(primary_key=True)

    payment_intent_id: Mapped[int] = mapped_column(
        ForeignKey("payment_intents.id"),
        unique=True,
        index=True,
        nullable=False,
    )

    payee_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
        nullable=False,
    )

    reference: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    amount_kobo: Mapped[int] = mapped_column(BigInteger, nullable=False)

    commission_kobo: Mapped[int] = mapped_column(BigInteger, nullable=False)

    provider_payout_kobo: Mapped[int] = mapped_column(BigInteger, nullable=False)

    status: Mapped[PayoutStatus] = mapped_column(
        Enum(PayoutStatus),
        nullable=False,
        default=PayoutStatus.PROCESSING,
    )

    provider_payout_id: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=True,
    )

    failure_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class OffRampWithdrawal(Base, TimeStampMixin):
    """A provider's USDC-to-NGN payout request.

    The provider sends USDC to a unique Obiex deposit address. Obiex credits
    Reach's USDC wallet, then Reach swaps to NGNX and withdraws naira to the
    provider's bank account. The row is the reconciliation record for every
    provider reference in that chain.
    """

    __tablename__ = "offramp_withdrawals"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
        nullable=False,
    )

    reference: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    # Optional client-supplied key so a retried POST does not create two
    # deposit addresses.
    idempotency_key: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=True,
    )

    status: Mapped[OffRampStatus] = mapped_column(
        Enum(OffRampStatus),
        nullable=False,
        default=OffRampStatus.AWAITING_DEPOSIT,
        index=True,
    )

    amount_usdc_units: Mapped[int] = mapped_column(BigInteger, nullable=False)

    received_usdc_units: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
    )

    quoted_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 6),
        nullable=True,
    )

    gross_ngn_kobo: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    fee_kobo: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    net_ngn_kobo: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Snapshot of the destination. The account name is the one Obiex resolved,
    # not whatever the client typed.
    bank_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bank_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    bank_account_number: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )
    bank_account_name: Mapped[str | None] = mapped_column(
        String(150), nullable=True
    )

    deposit_address: Mapped[str] = mapped_column(
        String(120),
        unique=True,
        index=True,
        nullable=False,
    )

    deposit_address_reference: Mapped[str | None] = mapped_column(
        String(150), nullable=True
    )

    deposit_currency: Mapped[str] = mapped_column(
        String(10), nullable=False, default="USDC"
    )

    deposit_network: Mapped[str] = mapped_column(
        String(20), nullable=False, default="SOL"
    )

    deposit_provider_reference: Mapped[str | None] = mapped_column(
        String(150), index=True, nullable=True
    )

    deposit_tx_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    swap_reference: Mapped[str | None] = mapped_column(String(150), nullable=True)

    swap_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 6),
        nullable=True,
    )

    # Set once the USDC has been swapped. A retry after a failed bank payout
    # must reuse the naira already in the wallet, never swap the USDC twice.
    swapped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    provider_withdrawal_id: Mapped[str | None] = mapped_column(
        String(150),
        unique=True,
        index=True,
        nullable=True,
    )

    provider_reference: Mapped[str | None] = mapped_column(
        String(150),
        unique=True,
        index=True,
        nullable=True,
    )

    failure_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    refund_reference: Mapped[str | None] = mapped_column(
        String(150), index=True, nullable=True
    )

    # Obiex's transaction id, which is what GET /transactions/{id} expects.
    # `refund_reference` is the webhook/reference field and is not always the
    # same value.
    refund_transaction_id: Mapped[str | None] = mapped_column(
        String(150), index=True, nullable=True
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    deposit_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    refunded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class WebhookEvent(Base, TimeStampMixin):
    """Minimal audit/dedupe record. Does not store the raw payload."""

    __tablename__ = "webhook_events"
    __table_args__ = (
        UniqueConstraint(
            "provider_object_id",
            "event_type",
            name="uq_webhook_provider_object_event",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    event_id: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        index=True,
        nullable=False,
    )

    event_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    reference: Mapped[str | None] = mapped_column(
        String(100),
        index=True,
        nullable=True,
    )

    provider_object_id: Mapped[str | None] = mapped_column(
        String(100),
        index=True,
        nullable=True,
    )

    signature_valid: Mapped[bool] = mapped_column(nullable=False, default=False)

    status: Mapped[WebhookStatus] = mapped_column(
        Enum(WebhookStatus),
        nullable=False,
        default=WebhookStatus.RECEIVED,
    )

    last_error: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
