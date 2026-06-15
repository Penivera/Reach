from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from DB.database import Base
from datetime import datetime

class EmailVerificationToken(Base):
    __tablename__  = "email_verification_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )

    token: Mapped[str]

    expires_at: Mapped[datetime]


class PasswordResetToken(Base):

    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )

    token: Mapped[str]

    expires_at: Mapped[datetime]