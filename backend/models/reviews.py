from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from backend.DB.database import Base
from .mixins import TimeStampMixin

class Review(Base, TimeStampMixin):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)

    reviewer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )

    reviewed_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )

    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id"),
        nullable=True
    )

    service_id: Mapped[int | None] = mapped_column(
        ForeignKey("services.id"),
        nullable=True
    )

    rating: Mapped[int]

    comment: Mapped[str]