from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from DB.database import Base
from schemas import ApplicationStatus

class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True
    )

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"),
        index=True
    )

    title: Mapped[str]

    description: Mapped[str]

    owner = relationship(
        "User",
        back_populates="jobs"
    )

    application = relationship(
        "JobApplication",
        back_populates="job"
    )


class JobApplication(Base):
    __tablename__ = "job_applications"

    id: Mapped[int] = mapped_column(primary_key=True)

    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id"),

    )

    applicant_id: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )

    proposal_text: Mapped[str]

    proposed_price: Mapped[float]

    status: Mapped[ApplicationStatus]

    job = relationship(
        "Job",
        back_populates="application"
    )

    applicant = relationship("User")

