from pydantic import BaseModel, Field, ConfigDict, model_validator
from .enums import ServiceStatus
from datetime import datetime


class ServiceCreate(BaseModel):
    title: str
    description: str
    category_id: int

    min_price: float = Field(gt=0)
    max_price: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_price_range(self):
        if self.min_price > self.max_price:
            raise ValueError("minimum price cannot be greater than max price")
        
        return self


class ServiceUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=150)

    description: str | None = Field(default=None,
        min_length=10,
        max_length=5000
    )

    category_id: int | None = None

    min_price: float | None = Field(default=None, gt=0)
    max_price: float | None = Field(default=None, gt=0)

    status: ServiceStatus | None = None

    @model_validator(mode="after")
    def validate_price_range(self):
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError(
                "Minimum price cannot be greater than maximum price."
            )
        return self

class ServiceResponse(BaseModel):

    id: int

    owner_id: int

    category_id: int

    title: str

    description: str

    min_price: float

    max_price: float

    status: ServiceStatus

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ServiceRequestCreate(BaseModel):
    pass


class ServiceRequestUpdate(BaseModel):
    pass

class ServiceRequestResponse(BaseModel):
    pass

