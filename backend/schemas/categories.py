from pydantic import BaseModel, ConfigDict

class CategoryCreate(BaseModel):
    name: str

    description: str | None = None

class CategoryUpdate(BaseModel):
    name : str | None = None

    description : str | None = None

class CategoryResponse(BaseModel):
    id: int

    name: str

    description: str

    model_config = ConfigDict(from_attributes=True)