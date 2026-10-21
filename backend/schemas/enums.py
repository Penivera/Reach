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
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
   # CLOSED = "closed"

class ApplicationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"

class ServiceStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"

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


class PayoutStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REVERSED = "reversed"


class WebhookStatus(str, Enum):
    RECEIVED = "received"
    PROCESSED = "processed"
    FAILED = "failed"
    REJECTED = "rejected"
    IGNORED = "ignored"
