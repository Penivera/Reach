from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from typing import Optional
from datetime import datetime

class BaseUser(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    username: str
    phone_number: str
    

class UserCreate(BaseUser):
    hashed_password: str = Field(min_length=6)
    confirm_password: str = Field(min_length=6)

    @model_validator(mode="after")
    def password_match(self):
        if self.hashed_password != self.confirm_password:
            raise ValueError("Password do not match")
        return self
    
class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    bio: str | None = None
    location: str | None = None
    phone_number: str | None = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserSignUpResponse(BaseModel):
    id: int
    username: str
    email: EmailStr

    model_config = ConfigDict(from_attributes = True)


class UserResponse(BaseModel):

    id: int
    username: str
    email: EmailStr

    first_name: str | None = None
    last_name: str | None = None

    bio: str | None = None
    phone_number: str | None = None
    location: str | None = None

    profile_picture: str | None = None

    is_email_verified: bool

    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6)
    confirm_password: str = Field(min_length=6)

    @model_validator(mode="after")
    def password_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("Password do not match")
        return self
    

class UserPublicResponse(BaseModel):

    id: int

    username: str

    first_name: str | None = None

    last_name: str | None = None

    bio: str | None = None

    location: str | None = None

    profile_picture: str | None = None

    model_config = ConfigDict(from_attributes=True)