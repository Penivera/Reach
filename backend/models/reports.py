from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from DB.database import Base
from .mixins import TimeStampMixin

class Report(Base, TimeStampMixin):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)

    reporter_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
    )

    reported_user_id: Mapped[int | None]

    reported_job_id: Mapped[int | None]

    reason: Mapped[str]

    status: Mapped[str]