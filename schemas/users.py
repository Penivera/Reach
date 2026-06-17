from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from typing import Optional

class BaseUser(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    username: str
    phone: str


class UserCreate(BaseUser):
    password: str = Field(min_length=6)
    confirm_password: str = Field(min_length=6)

    @field_validator("confirm_password")
    async def password_match(cls, value, info):
        password = info.data.get("password")
        
        if password and value != password:
            raise ValueError("passwords do not match")
        
        return value


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr

    model_config = ConfigDict(from_attributes = True)



