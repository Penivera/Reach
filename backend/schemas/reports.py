from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class ReportCreate(BaseModel):
    reported_user_id: int | None = None
    reported_job_id: int | None = None

    reason: str = Field(
        min_length=2,
        max_length=100
    )

    description: str | None = Field(
        default=None,
        max_length=1000
    )


class ReportResponse(BaseModel):
    id: int
    reporter_id: int
    reported_user_id: int | None
    reported_job_id: int | None
    reason: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)