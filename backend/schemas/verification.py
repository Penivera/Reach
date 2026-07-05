from pydantic import BaseModel, EmailStr

class EmailVerificationRequest(BaseModel):
    token: str

class ResendEmailVerificationRequest(BaseModel):
    email: EmailStr

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

