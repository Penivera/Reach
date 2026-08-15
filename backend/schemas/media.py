from datetime import datetime

from pydantic import BaseModel, ConfigDict

from .enums import MediaType


class MediaResponse(BaseModel):
    id: int
    url: str
    media_type: MediaType
    uploaded_by: int
    job_id: int | None = None
    service_id: int | None = None
    business_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)