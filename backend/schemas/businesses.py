from pydantic import BaseModel, ConfigDict


class BusinessCreate(BaseModel):
    name: str
    description: str


class BusinessResponse(BaseModel):
    id: int
    owner_id: int
    name: str
    description: str | None = None
    model_config = ConfigDict(from_attributes=True)


class BusinessUpdate(BaseModel):
    name: str | None = None

    description: str | None = None
