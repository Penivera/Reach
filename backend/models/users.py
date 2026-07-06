from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Float, Boolean, func
from DB.database import Base
from schemas.enums import UserRole, VerificationStatus
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Float, Boolean, func, Enum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from DB.database import Base
from datetime import datetime
from schemas import UserRole
from .mixins import TimeStampMixin


class User(Base, TimeStampMixin):
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

    hashed_password: Mapped[str] = mapped_column(String(255))

    first_name: Mapped[str | None] = mapped_column(String(100))

    last_name: Mapped[str | None] = mapped_column(String(100))

    bio: Mapped[str | None] = mapped_column(String(500))

    phone_number: Mapped[str | None] = mapped_column(String(20))

    location: Mapped[str | None] = mapped_column(String(255))

    profile_image: Mapped[str | None] = mapped_column(String(500))

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

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER)

    verification_status: Mapped[VerificationStatus] = mapped_column(Enum(VerificationStatus), default=VerificationStatus.PENDING)

    jobs = relationship("Job", back_populates="owner")
    services = relationship("Service", back_populates="owner")
    verification_tokens = relationship("EmailVerificationToken", back_populates="user", cascade="all, delete-orphan")

    user_skills = relationship("UserSkill", back_populates="user", cascade="all, delete-orphan")

    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")

    

