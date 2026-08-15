from pydantic import BaseModel, ConfigDict


class BusinessCreate(BaseModel):
    name: str
    description: str


class BusinessResponse(BaseModel):
    id: int
    owner_id: int
    description: str
    model_config = ConfigDict(from_attributes=True)


class BusinessUpdate(BaseModel):
    name: str | None = None

    description: str | None = None