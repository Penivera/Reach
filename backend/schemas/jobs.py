from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from .enums import ApplicationStatus

class JobCreate(BaseModel):
    category_id: int
    title: str 
    description: str
    budget: float = Field(...,gt=0)


class JobUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    budget: float | None = Field(None, gt=0)

class JobResponse(BaseModel):
    id: int
    title: str
    description: str
    budget: float
    status: str

    category_id: int
    posted_by: int

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