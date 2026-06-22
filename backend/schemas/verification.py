from pydantic import BaseModel

class EmailVerificationRequest(BaseModel):
    token: str