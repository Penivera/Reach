from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from payment_validation import (
    PaymentProfileValidationError,
    normalize_phone_number,
    validate_date_of_birth,
    validate_single_name,
)

from .enums import PaymentStatus, PayoutStatus, ProvisioningStatus


class PaymentProfileUpsert(BaseModel):
    # Optional overrides so a compound name or local-format phone captured at
    # signup can be corrected in the payment-profile step.
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    phone_number: str | None = Field(default=None, max_length=20)
    middle_name: str | None = Field(default=None, max_length=100)
    date_of_birth: date
    address: str = Field(min_length=5, max_length=255)
    city: str = Field(min_length=2, max_length=100)
    country: str = Field(default="Nigeria", min_length=2, max_length=100)

    @field_validator("first_name", "last_name", "middle_name")
    @classmethod
    def validate_name_fields(cls, value, info):
        if value is None or not value.strip():
            return None
        try:
            return validate_single_name(value, info.field_name)
        except PaymentProfileValidationError as exc:
            raise ValueError(str(exc))

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, value):
        if value is None or not value.strip():
            return None
        try:
            return normalize_phone_number(value)
        except PaymentProfileValidationError as exc:
            raise ValueError(str(exc))

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, value):
        try:
            return validate_date_of_birth(value)
        except PaymentProfileValidationError as exc:
            raise ValueError(str(exc))

    @field_validator("address", "city", "country")
    @classmethod
    def strip_required_text(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("This field is required")
        return value


class PaymentProfileResponse(BaseModel):
    id: int
    user_id: int
    middle_name: str | None = None
    date_of_birth: date
    address: str
    city: str
    country: str

    model_config = ConfigDict(from_attributes=True)


class FossaPayAccountResponse(BaseModel):
    status: ProvisioningStatus
    provider_customer_id: str | None = None
    wallet_id: str | None = None
    account_number: str | None = None
    account_name: str | None = None
    bank_name: str | None = None
    bank_code: str | None = None
    last_error: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PaymentProfileStateResponse(BaseModel):
    profile_completed: bool
    can_pay: bool
    missing_fields: list[str] = Field(default_factory=list)
    profile: PaymentProfileResponse | None = None
    provisioning: FossaPayAccountResponse | None = None


class PaymentIntentResponse(BaseModel):
    id: int
    job_id: int
    reference: str
    amount_kobo: int
    amount_payable_kobo: int
    status: PaymentStatus
    provider_checkout_id: str | None = None
    bank_name: str | None = None
    account_name: str | None = None
    account_number: str | None = None
    expires_at: datetime | None = None
    paid_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PayoutResponse(BaseModel):
    id: int
    payment_intent_id: int
    reference: str
    amount_kobo: int
    commission_kobo: int
    provider_payout_kobo: int
    status: PayoutStatus
    provider_payout_id: str | None = None
    failure_reason: str | None = None
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
