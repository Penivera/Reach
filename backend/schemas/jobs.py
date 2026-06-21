from pydantic import BaseModel, ConfigDict

class JobCreate(BaseModel):
    category_id: int
    title: str
    description: str
    budget: float


class JobUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    budget: float | None = None

class JobResponse(BaseModel):
    id: int
    title: str
    description: str
    budget: float
    status: str

    model_config = ConfigDict(from_attributes=True)

class JobApplicationCreate(BaseModel):
    pass

class JobApplicationUpdate(BaseModel):
    pass

class JobAppplicationResponse(BaseModel):
    pass