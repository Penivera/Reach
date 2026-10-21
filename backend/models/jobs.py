from sqlalchemy import String, Integer, ForeignKey, Enum, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from DB.database import Base
from schemas import ApplicationStatus, JobStatus
from .mixins import TimeStampMixin
from geoalchemy2 import Geography
from geoalchemy2.elements import WKBElement
from geoalchemy2.shape import to_shape

class Job(Base, TimeStampMixin):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"),index=True)

    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"),index=True)

    title: Mapped[str]
    description: Mapped[str]
    budget: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), nullable=False, default=JobStatus.OPEN)

    location: Mapped[WKBElement] = mapped_column(Geography(geometry_type="POINT", srid=4326, spatial_index=False, nullable=False))

    location_name: Mapped[str]

    client_completed = mapped_column(Boolean, default=False, nullable=False)

    worker_completed = mapped_column(Boolean, default=False, nullable=False)

    # On-chain tracking (Model 1: Solana Anchor program is canonical)
    onchain_task_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    onchain_tx_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    @property
    def near_task_id(self) -> int | None:
        """Deprecated alias for onchain_task_id (Model 1: Solana is canonical)."""
        return self.onchain_task_id

    @near_task_id.setter
    def near_task_id(self, value: int | None):
        self.onchain_task_id = value

    owner = relationship("User", back_populates="jobs")

    application = relationship("JobApplication", back_populates="job")

    category = relationship("Category", back_populates="jobs")

    media = relationship("Media", back_populates="job", cascade="all, delete-orphan")

    @property
    def latitude(self) -> float:
        return to_shape(self.location).y

    @property
    def longitude(self) -> float:
        return to_shape(self.location).x

    @property
    def posted_by(self) -> int:
        return self.owner_id


class JobApplication(Base, TimeStampMixin):
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

    status: Mapped[ApplicationStatus] = mapped_column(Enum(ApplicationStatus), nullable=False, default=ApplicationStatus.PENDING)

    # On-chain tracking (Model 1: Solana Anchor program is canonical)
    onchain_application_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    @property
    def near_application_id(self) -> int | None:
        """Deprecated alias for onchain_application_id (Model 1: Solana is canonical)."""
        return self.onchain_application_id

    @near_application_id.setter
    def near_application_id(self, value: int | None):
        self.onchain_application_id = value

    job = relationship(
        "Job",
        back_populates="application"
    )

    applicant = relationship("User")

