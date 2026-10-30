from sqlalchemy import Boolean, ForeignKey, String, false
from sqlalchemy.orm import Mapped, mapped_column, relationship
from DB.database import Base
from .mixins import TimeStampMixin


class Business(Base, TimeStampMixin):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(primary_key=True)

    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True, nullable=False)

    name: Mapped[str] = mapped_column(String(150), nullable=False)

    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )

    owner = relationship("User", back_populates="business")

    services = relationship("Service", back_populates="business")

    media = relationship("Media", back_populates="business", cascade="all, delete-orphan")

    @property
    def images(self):
        return self.media
