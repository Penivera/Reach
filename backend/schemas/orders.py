from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field, field_validator
from schemas.enums import ListingKind, OrderStatus, PaymentStatus

class OrderCreate(BaseModel):
    listing_id: int
    quantity: int = Field(default=1, ge=1)
    note: str | None = None
    scheduled_for: datetime | None = None
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    location_name: str | None = None
    address_details: str | None = Field(None, max_length=300)

    @field_validator("scheduled_for")
    @classmethod
    def scheduled_in_future(cls, v):
        if v is None:
            return v
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v <= datetime.now(timezone.utc):
            raise ValueError("scheduled_for must be in the future")
        return v

class OrderStatusNote(BaseModel):
    status_note: str | None = Field(None, max_length=300)

class OrderResponse(BaseModel):
    id: int
    listing_id: int
    buyer_id: int
    seller_id: int
    business_id: int
    kind: ListingKind
    listing_title: str
    quantity: int
    unit_price: float
    total_price: float
    note: str | None = None
    scheduled_for: datetime | None = None

    latitude: float | None = None
    longitude: float | None = None
    location_name: str | None = None
    address_details: str | None = None

    status: OrderStatus
    status_note: str | None = None
    payment_status: PaymentStatus
    escrow_reference: str | None = None

    paid_at: datetime | None = None
    accepted_at: datetime | None = None
    fulfilled_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
