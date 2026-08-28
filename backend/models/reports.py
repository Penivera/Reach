from sqlalchemy import String, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from DB.database import Base
from schemas import ReportStatus
from .mixins import TimeStampMixin


class Report(Base, TimeStampMixin):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)

    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    reported_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    reported_job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)

    reason: Mapped[str] = mapped_column(String(100), nullable=False)

    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    status: Mapped[ReportStatus] = mapped_column( Enum(ReportStatus), default=ReportStatus.OPEN, nullable=False)

    reporter = relationship("User", foreign_keys=[reporter_id])

    reported_user = relationship("User", foreign_keys=[reported_user_id])

    reported_job = relationship("Job", foreign_keys=[reported_job_id])