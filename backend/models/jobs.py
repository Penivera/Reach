from sqlalchemy import String, Integer, ForeignKey, Enum, Float
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

    owner = relationship("User", back_populates="jobs")

    application = relationship("JobApplication", back_populates="job")

    category = relationship("Category", back_populates="jobs")

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

    job = relationship(
        "Job",
        back_populates="application"
    )

    applicant = relationship("User")

