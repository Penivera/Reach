from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    reviewed_user_id: int

    job_id: int | None = None
    service_id: int | None = None

    rating: int = Field(..., ge=1, le=5)

    comment: str = Field(..., min_length=3, max_length=1000)


class ReviewResponse(BaseModel):
    id: int
    reviewer_id: int
    reviewed_user_id: int

    job_id: int | None
    service_id: int | None

    rating: int
    comment: str

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)