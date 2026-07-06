from pydantic import BaseModel, ConfigDict

class SkillCreate(BaseModel):
    name : str

class SkillUpdate(BaseModel):
    name: str | None = None

class SkillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str

class UserSkillUpdate(BaseModel):
    skill_ids : list[int]