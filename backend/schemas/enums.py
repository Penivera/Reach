import enum
from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


class VerificationStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"

class JobStatus(str, Enum):
    # Model 1: escrow is locked when the task is created, so a job starts life
    # waiting for its funding before it can accept providers.
    PENDING_FUNDING = "pending_funding"
    OPEN = "open"
    AWAITING_PAYMENT = "awaiting_payment"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
   # CLOSED = "closed"

class OrderStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    FULFILLED = "fulfilled"
    COMPLETED = "completed"
    DECLINED = "declined"
    CANCELLED = "cancelled"

class UrgencyLevel(str, Enum):
    ASAP = "asap"
    THIS_WEEK = "this_week"
    FLEXIBLE = "flexible"

class ApplicationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"

class ServiceStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class ListingKind(str, enum.Enum):
    GOOD = "good"
    SERVICE = "service"


class ServiceRequestStatus(str, Enum):
    START = "start"
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class NotificationType(str, Enum):
    APPLICATION_RECEIVED = "application_received"
    JOB_ACCEPTED = "job_accepted"
    MESSAGE_RECEIVED = "message_received"
    REVIEW_RECEIVED = "review_received"

class ReportStatus(str, Enum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"

class MediaType(str, Enum):
    PROFILE = "profile"
    JOB = "job"
    SERVICE = "service"
    BUSINESS = "business"


class ProvisioningStatus(str, Enum):
    PENDING = "pending"
    PROVISIONED = "provisioned"
    FAILED = "failed"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    EXPIRED = "expired"
    REVERSED = "reversed"
    HELD = "held"  # collected, but awaiting a manual review (name mismatch)


class FundingRail(str, Enum):
    """How the customer funded (or is funding) the task."""

    OBIEX_FIAT = "obiex_fiat"  # NGN collected into a virtual account, settled as USDC
    FOSSAPAY_CHECKOUT = "fossapay_checkout"  # NGN bank transfer checkout
    CRYPTO = "crypto"  # USDC sent to a per-user Solana deposit address
    WALLET = "wallet"  # the user signed the Anchor transaction themselves


class FundingStatus(str, Enum):
    """The state of a task's funding."""

    PENDING = "pending"
    HELD = "held"
    PAID = "paid"  # the money arrived with the provider
    FUNDED = "funded"  # the escrow is locked on-chain
    FAILED = "failed"
    EXPIRED = "expired"
    REVERSED = "reversed"


class PayerType(str, Enum):
    """Who controlled the key that locked the escrow."""

    WALLET = "wallet"  # the user signed with their own wallet
    CUSTODIAL = "custodial"  # the server relayer signed for them


class ChainTransactionStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    FINALIZED = "finalized"
    FAILED = "failed"


class ProviderAction(str, Enum):
    """A task-lifecycle instruction the provider has to sign themselves."""

    APPLY = "apply"
    COMPLETE = "complete"


class CreatorAction(str, Enum):
    """A creator-side instruction a wallet-funded client has to sign."""

    CREATE = "create_task"
    ACCEPT = "accept"
    RELEASE = "approve_work"


class TreasuryTransferStatus(str, Enum):
    """A withdrawal of USDC from the provider into the on-chain float."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class PayoutStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REVERSED = "reversed"


class OffRampStatus(str, Enum):
    """A provider's USDC-to-NGN payout request.

    The provider sends USDC to a unique Obiex deposit address. Obiex confirms
    the deposit, Reach swaps it to NGNX, then withdraws NGN to the provider's
    bank account.
    """

    AWAITING_DEPOSIT = "awaiting_deposit"
    PARTIALLY_FUNDED = "partially_funded"
    DEPOSIT_CONFIRMED = "deposit_confirmed"
    WITHDRAWING = "withdrawing"
    PAID = "paid"
    HELD = "held"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    REFUNDING = "refunding"
    REFUNDED = "refunded"


class WebhookStatus(str, Enum):
    RECEIVED = "received"
    PROCESSED = "processed"
    FAILED = "failed"
    REJECTED = "rejected"
    IGNORED = "ignored"
