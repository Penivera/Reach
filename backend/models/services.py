from sqlalchemy import String, Integer, ForeignKey, Float, Enum
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

    title: Mapped[str] = mapped_column(String, nullable=False)

    description: Mapped[str] = mapped_column(String, nullable=False)

    min_price: Mapped[float] = mapped_column(Float, nullable=False)

    max_price: Mapped[float] = mapped_column(Float, nullable=False)

    status: Mapped[ServiceStatus] = mapped_column(Enum(ServiceStatus), nullable=False, default= ServiceStatus.ACTIVE)

    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"),index=True, nullable=False)

    category = relationship("Category",back_populates="services")

    owner = relationship("User",back_populates = "services")

    requests = relationship("ServiceRequest", back_populates="service",cascade="all, delete-orphan")


class ServiceRequest(Base, TimeStampMixin):
    __tablename__ = "service_requests"

    id: Mapped[int] = mapped_column(primary_key=True)

    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"),index=True)

    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id"),index=True)

    provider_id: Mapped[int] = mapped_column(ForeignKey("users.id"),index=True)

    message: Mapped[str] = mapped_column(String, nullable=False)

    proposed_price: Mapped[float] = mapped_column(Float, nullable=False)

    status: Mapped[ServiceRequestStatus] = mapped_column(Enum(ServiceRequestStatus), nullable=False, default=ServiceRequestStatus.PENDING)

    service = relationship("Service",back_populates="requests")

    requester = relationship(
        "User",
        foreign_keys=[requester_id],
        back_populates="service_requests"
    )

    provider = relationship(
        "User",
        foreign_keys=[provider_id],
        back_populates="received_service_requests"
    )
