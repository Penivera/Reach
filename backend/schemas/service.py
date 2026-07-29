from pydantic import BaseModel, Field, ConfigDict, field_validator
from .enums import ServiceStatus
from datetime import datetime
from typing import Optional


class ServiceCreate(BaseModel):
    business_name: str = Field(min_length=2, max_length=150)

    title: str = Field(min_length=3, max_length=200)

    description: str

    starting_price: float = Field(gt=0)

    category_id: int

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


class ServiceUpdate(BaseModel):
    business_name: Optional[str] = Field(default=None, min_length=2, max_length=150)

    title: Optional[str] = Field(default=None, min_length=3, max_length=200)

    description: Optional[str] = None

    starting_price: Optional[float] = Field(default=None, gt=0)

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

    business_name: str

    title: str

    description: str

    starting_price: float

    status: ServiceStatus

    category_id: int

    owner_id: int

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


class ServiceRequestCreate(BaseModel):
    pass


class ServiceRequestUpdate(BaseModel):
    pass

class ServiceRequestResponse(BaseModel):
    pass

