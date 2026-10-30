from pydantic import BaseModel, ConfigDict
from .media import MediaResponse


class BusinessCreate(BaseModel):
    name: str
    description: str


class BusinessResponse(BaseModel):
    id: int
    owner_id: int
    name: str
    description: str | None = None
    model_config = ConfigDict(from_attributes=True)


class BusinessDetailResponse(BusinessResponse):
    images: list[MediaResponse] = []


class BusinessUpdate(BaseModel):
    name: str | None = None

    description: str | None = None
