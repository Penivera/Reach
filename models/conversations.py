from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from DB.database import Base

class Coversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)




class ConversationParticipant(Base):
    __tablename__ = "conversation_participants"

    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id"),
        primary_key = True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        primary_key = True
    )


    
class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)

    conversation_id = Mapped[int] = mapped_column(
        ForeignKey 
    )

    sender_id: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )

    content: Mapped[str]

    is_read: Mapped[bool] = mapped_column(
        default=False
    )

    