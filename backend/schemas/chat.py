from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class ConversationCreate(BaseModel):
    participant_id: int


class ConversationResponse(BaseModel):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_id: int
    content: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ChatUser(BaseModel):
    id: int
    username: str
    first_name: str
    last_name: str
    profile_image: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ConversationListItem(BaseModel):
    id: int
    created_at: datetime
    updated_at: datetime
    other_user: ChatUser | None = None
    last_message: MessageResponse | None = None
    unread_count: int = 0

    model_config = ConfigDict(from_attributes=True)
