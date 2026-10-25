from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from .enums import ListingKind, ServiceStatus, ServiceRequestStatus
from datetime import datetime
from typing import Optional


class ServiceCreate(BaseModel):
    business_id: int

    title: str = Field(min_length=3, max_length=200)

    description: str

    price: float = Field(gt=0)

    kind: ListingKind

    stock: int | None = Field(default=None, ge=0)

    category_id: int

    latitude: float

    longitude: float

    location_name: str

    @model_validator(mode="after")
    def check_stock(self):
        if self.kind == ListingKind.GOOD and self.stock is None:
            raise ValueError("stock is required for goods")
        if self.kind == ListingKind.SERVICE:
            self.stock = None
        return self

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value):
        if not -90 <= value <= 90:
            raise ValueError("Latitude must be between -90 and 90.")
        return value

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value):
        if not -180 <= value <= 180:
            raise ValueError("Longitude must be between -180 and 180.")
        return value


class ServiceUpdate(BaseModel):

    title: Optional[str] = Field(default=None, min_length=3, max_length=200)

    description: Optional[str] = None

    price: Optional[float] = Field(default=None, gt=0)

    stock: Optional[int] = Field(default=None, ge=0)

    category_id: Optional[int] = None

    latitude: Optional[float] = None

    longitude: Optional[float] = None

    location_name: Optional[str] = None

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value):
        if value is not None and not -90 <= value <= 90:
            raise ValueError("Latitude must be between -90 and 90.")
        return value

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value):
        if value is not None and not -180 <= value <= 180:
            raise ValueError("Longitude must be between -180 and 180.")
        return value


class ServiceResponse(BaseModel):
    id: int

    business_id: int

    title: str
    description: str
    price: float

    kind: ListingKind

    stock: int | None = None

    status: ServiceStatus

    category_id: int

    location_name: str

    latitude: float
    longitude: float

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NearbyServiceQuery(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    radius: float = Field(10, gt=0)

    category_id: int | None = None
    kind: ListingKind | None = None
    q: str | None = Field(default=None, min_length=1, max_length=100)
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class ServiceRequestCreate(BaseModel):
    service_id: int

    message: str = Field(min_length=10, max_length=1000)

    proposed_price: float = Field(gt=0)

    latitude: float

    longitude: float

    location_name: str

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value):
        if not -90 <= value <= 90:
            raise ValueError("Latitude must be between -90 and 90.")
        return value

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value):
        if not -180 <= value <= 180:
            raise ValueError("Longitude must be between -180 and 180.")
        return value


class ServiceRequestResponse(BaseModel):
    id: int

    service_id: int

    requester_id: int

    provider_id: int

    message: str

    proposed_price: float

    status: ServiceRequestStatus

    location_name: str

    latitude: float

    longitude: float

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
