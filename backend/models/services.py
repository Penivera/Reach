from sqlalchemy import String, Integer, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from DB.database import Base
from schemas import ServiceStatus, ServiceRequestStatus
from .mixins import TimeStampMixin

class Service(Base, TimeStampMixin):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True)

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True
    )

    title: Mapped[str]

    description: Mapped[str]

    min_price: Mapped[float]

    max_price: Mapped[float]

    status: Mapped[ServiceStatus]

    owner = relationship(
        "User",
        back_populates = "services"
    )


class ServiceRequest(Base, TimeStampMixin):
    __tablename__ = "service_requests"

    id: Mapped[int] = mapped_column(primary_key=True)

    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id")
    )

    requester_id: Mapped[int] = mapped_column(
        ForeignKey("services.id")
    )

    provider_id: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )

    provider_id: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )

    message: Mapped[str]

    proposed_price: Mapped[float]

    status: Mapped[ServiceRequestStatus]

    