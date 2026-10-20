from enum import Enum

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


class VerificationStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "virified"
    REJECTED = "rejected"

class JobStatus(str, Enum):
    OPEN = "open"
    AWAITING_PAYMENT = "awaiting_payment"
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