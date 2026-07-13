from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
from .enums import ApplicationStatus

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



class JobUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    budget: float | None = Field(None, gt=0)

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

    category_id: int
    posted_by: int

    latitude: float
    longitude: float
    location_name: str

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)



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

    created_at: datetime
    updaated_at: datetime

    model_config = ConfigDict(from_attributes=True)