from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from DB.database import Base
from .mixins import TimeStampMixin

class Review(Base, TimeStampMixin):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)

    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    reviewed_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)

    service_id: Mapped[int | None] = mapped_column(ForeignKey("services.id"), nullable=True)

    rating: Mapped[int]

    comment: Mapped[str]

    reviewer: Mapped["User"] = relationship("User", foreign_keys=[reviewer_id])

    reviewed_user: Mapped["User"] = relationship("User", foreign_keys=[reviewed_user_id])

    job: Mapped["Job"] = relationship("Job", foreign_keys=[job_id])

    service: Mapped["Service"] = relationship("Service", foreign_keys=[service_id])
