from datetime import datetime
from sqlalchemy import Integer, String, Float, ForeignKey, Enum, Text, Boolean, DateTime, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from DB.database import Base
from models.mixins import TimeStampMixin
from schemas.enums import ListingKind, OrderStatus, PaymentStatus
from geoalchemy2 import Geography
from geoalchemy2.elements import WKBElement
from geoalchemy2.shape import to_shape

class Order(Base, TimeStampMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("services.id"), index=True, nullable=False)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True, nullable=False)

    # Snapshots
    kind: Mapped[ListingKind] = mapped_column(Enum(ListingKind, name="listingkind", create_type=False), nullable=False)
    listing_title: Mapped[str] = mapped_column(String(200), nullable=False)

    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    total_price: Mapped[float] = mapped_column(Float, nullable=False)

    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    location: Mapped[WKBElement | None] = mapped_column(Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=True)
    location_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_details: Mapped[str | None] = mapped_column(String(300), nullable=True)

    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus, name="orderstatus", create_type=True), default=OrderStatus.PENDING, nullable=False)
    status_note: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # Placeholders for payments branch
    payment_status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus, name="paymentstatus", create_type=False), default=PaymentStatus.PENDING, nullable=False)
    escrow_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fulfilled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("quantity >= 1", name="check_order_quantity_min"),
        CheckConstraint("total_price > 0", name="check_order_total_price_min"),
        CheckConstraint("buyer_id <> seller_id", name="check_order_buyer_seller_diff"),
        CheckConstraint("kind <> 'SERVICE' OR quantity = 1", name="check_order_service_quantity"),
        Index("ix_order_buyer_status", "buyer_id", "status"),
        Index("ix_order_seller_status", "seller_id", "status"),
    )

    @property
    def latitude(self) -> float | None:
        if self.location is None:
            return None
        return to_shape(self.location).y

    @property
    def longitude(self) -> float | None:
        if self.location is None:
            return None
        return to_shape(self.location).x
