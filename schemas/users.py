from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional

class BaseUser(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    username: str
    phone: str


class UserCreate(BaseUser):
    password: str


class UserLogin(BaseModel):
    username: str
    password: str

class UserUpdate(BaseModel):
    pass

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr

