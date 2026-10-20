from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from DB.database import Base
from schemas.enums import (
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

    status: Mapped[ProvisioningStatus] = mapped_column(
        Enum(ProvisioningStatus),
        nullable=False,
        default=ProvisioningStatus.PENDING,
    )

    last_error: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    user = relationship("User", back_populates="fossapay_customer")


class PaymentIntent(Base, TimeStampMixin):
    """One FossaPay checkout attempt for a job."""

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

    amount_kobo: Mapped[int] = mapped_column(BigInteger, nullable=False)

    amount_payable_kobo: Mapped[int] = mapped_column(BigInteger, nullable=False)

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
