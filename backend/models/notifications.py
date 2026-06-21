from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from backend.DB.database import Base
from backend.schemas import NotificationType

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True
    )

    type: Mapped[NotificationType]

    title: Mapped[str]

    message: Mapped[str]
    
    is_read: Mapped[bool] = mapped_column(
        default=False
    )