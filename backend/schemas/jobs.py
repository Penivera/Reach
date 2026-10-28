from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
from .enums import ApplicationStatus, FundingStatus, JobUrgency, PayerType

class LocationBase(BaseModel):
    latitude: float
    longitude: float
    location_name: str

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value):
        if not -90 <= value <= 90:
            raise ValueError("Invalid latitude")
        return value
        
    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value):
        if not -180 <= value <= 180:
            raise ValueError("Invalide Longitude")
        return value


class JobCreate(LocationBase):
    category_id: int
    title: str 
    description: str
    budget: float = Field(...,gt=0)
    urgency: JobUrgency = JobUrgency.FLEXIBLE



class JobUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    budget: float | None = Field(None, gt=0)
    urgency: JobUrgency | None = None

    latitude: float | None = None
    longitude: float | None = None
    location_name: str | None = None

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value):
        if value is not None and not -90 <= value <= 90:
            raise ValueError("Invalid latitude")
        return value
        
    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value):
        if value is not None and not -180 <= value <= 180:
            raise ValueError("Invalide Longitude")
        return value

class JobResponse(BaseModel):
    id: int
    title: str
    description: str
    budget: float
    status: str
    urgency: JobUrgency
    expires_at: datetime | None = None

    category_id: int
    posted_by: int

    latitude: float
    longitude: float
    location_name: str

    onchain_task_id: int | None = None
    onchain_tx_hash: str | None = None
    near_task_id: int | None = Field(default=None, deprecated=True, description="Deprecated in favor of onchain_task_id")

    # Model 1 lifecycle: the escrow is funded before the task opens, and the
    # on-chain status is the canonical state the UI mirrors.
    funding_status: FundingStatus
    payer_type: PayerType | None = None
    onchain_status: str | None = None
    client_completed: bool = False
    worker_completed: bool = False

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class JobCompletionRequest(BaseModel):
    completed: bool

class JobApplicationCreate(BaseModel):
    proposal_text: str
    proposed_price: float = Field(..., gt=0)

class JobApplicationUpdate(BaseModel):
    proposal_text: str | None = None
    proposed_price: float | None = Field(None, gt=0)

class JobApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus

class JobAppplicationResponse(BaseModel):
    id: int
    job_id: int
    applicant_id: int
    proposal_text: str
    proposed_price: float
    status: ApplicationStatus

    onchain_application_id: int | None = None
    near_application_id: int | None = Field(default=None, deprecated=True, description="Deprecated in favor of onchain_application_id")

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class JobOnchainPrepareResponse(BaseModel):
    """An unsigned transaction a user's wallet has to sign."""

    action: str
    job_id: int
    task_id: int
    # The provider flow returns `provider_address`; the creator flow returns
    # `signer_address`. Both are optional so the same response works for both.
    signer_address: str | None = None
    provider_address: str | None = None
    transaction: str | None = None
    recent_blockhash: str | None = None
    expires_at: int | None = None
    amount_units: int | None = None
    escrow_units: int | None = None
    creation_fee_units: int | None = None
    already_done: bool = False
    application: JobAppplicationResponse | None = None


class JobOnchainFundRequest(BaseModel):
    """The USDC amount a client wants to lock in the task vault."""

    usdc_amount: Decimal = Field(gt=0)

    @field_validator("usdc_amount")
    @classmethod
    def validate_usdc_precision(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("USDC amounts must be finite")
        if value.as_tuple().exponent < -6:
            raise ValueError("USDC amounts support at most 6 decimal places")
        return value


class JobOnchainStateResponse(BaseModel):
    """The decoded on-chain task, useful for both parties."""

    task_id: int
    creator: str
    provider: str | None = None
    status: str
    labor_fee: int
    material_cost: int
    creator_locked_balance: int
    provider_locked_balance: int | None = None
    advanced_disbursed: bool = False
    created_at: int | None = None
    updated_at: int | None = None


class JobOnchainSubmitRequest(BaseModel):
    signed_transaction: str = Field(min_length=1)


class NearbyJobQuery(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    radius: float = Field(10, gt=0)

    category_id: int | None = None
