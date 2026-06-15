from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Float, Boolean
from DB.database import Base
from schemas.enums import UserRole, VerificationStatus
from sqlalchemy.orm import func, relationship, Mapped, mapped_column
from DB.database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id : Mapped[int] = mapped_column(primary_key=True)

    email: Mapped[str] = mapped_column(
        String(225),
        unique=True,
        index=True
    )

    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index = True
    )

    password: Mapped[str]

    first_name: Mapped[str | None]

    last_name: Mapped[str | None]

    bio: Mapped[str | None]

    phone_number: Mapped[str | None]

    location: Mapped[str | None]

    profile_image: Mapped[str | None]

    average_rating: Mapped[float] = mapped_column(
        Float,
        default=0
    )

    total_reviews: Mapped[int] = mapped_column(default=0)

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    is_email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    role: Mapped[UserRole]

    verification_status: Mapped[VerificationStatus]

    jobs = relationship("job", back_populates="owner")
    services = relationship("Service", back_populates="owner")

