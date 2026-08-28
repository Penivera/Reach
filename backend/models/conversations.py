from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from DB.database import Base
from .mixins import TimeStampMixin


class Conversation(Base, TimeStampMixin):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)

    participants = relationship("ConversationParticipant", back_populates="conversation", cascade="all, delete-orphan")

    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class ConversationParticipant(Base, TimeStampMixin):
    __tablename__ = "conversation_participants"

    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)

    conversation = relationship("Conversation", back_populates="participants")

    user = relationship("User", back_populates="conversations")


class Message(Base, TimeStampMixin):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)

    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), nullable=False)

    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    content: Mapped[str] = mapped_column(nullable=False)

    is_read: Mapped[bool] = mapped_column(default=False, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")

    sender = relationship("User", back_populates="messages")