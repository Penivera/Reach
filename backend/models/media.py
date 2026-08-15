from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from DB.database import Base
from schemas import MediaType
from .mixins import TimeStampMixin



class Media(Base, TimeStampMixin):
    __tablename__ = "media"

    id: Mapped[int] = mapped_column(primary_key=True)

    url: Mapped[str]

    media_type: Mapped[MediaType]

    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))

    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)

    service_id: Mapped[int | None] = mapped_column(ForeignKey("services.id"), nullable= True)

    business_id: Mapped[int | None] = mapped_column(ForeignKey("businesses.id"), nullable=True)

    business = relationship("Business", back_populates="media")

    service = relationship("Service", back_populates="media")

    job = relationship("Job", back_populates="media")