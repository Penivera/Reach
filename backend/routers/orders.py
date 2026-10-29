from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from geoalchemy2.functions import ST_GeogFromText

from DB.database import get_db
from dependencies import get_current_user
from models import User, Business, Order
from models.services import Service # Assuming this is where your Service model lives
from schemas.enums import OrderStatus, ListingKind, ServiceStatus
from schemas.orders import OrderCreate, OrderStatusNote, OrderResponse

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("", response_model=OrderResponse)
async def place_order(
    order_data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Lock listing
    listing = (await db.execute(
        select(Service).where(Service.id == order_data.listing_id).with_for_update()
    )).scalar_one_or_none()

    if not listing or listing.status != ServiceStatus.ACTIVE:
        raise HTTPException(status_code=404, detail="Listing not found or not active")
    if (order_data.latitude is not None and order_data.longitude is None) or \
        (order_data.latitude is None and order_data.longitude is not None):
        raise HTTPException(status_code=400, detail="Latitude and longitude must be provided together")

    business = (await db.execute(select(Business).where(Business.id == listing.business_id))).scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    if business.owner_id == current_user.id:
        raise HTTPException(status_code=403, detail="You cannot order your own listing")


    if listing.kind == ListingKind.SERVICE:
        if order_data.quantity != 1:
            raise HTTPException(status_code=400, detail="Services can only be ordered with quantity 1")

        existing_order = (await db.execute(
            select(Order).where(
                Order.buyer_id == current_user.id,
                Order.listing_id == listing.id,
                Order.status.in_([OrderStatus.PENDING, OrderStatus.ACCEPTED, OrderStatus.FULFILLED])
            )
        )).scalar_one_or_none()
        if existing_order:
            raise HTTPException(status_code=400, detail="You already have an open order for this service")

    elif listing.kind == ListingKind.GOOD:
        if listing.stock is None or order_data.quantity > listing.stock:
            raise HTTPException(status_code=400, detail=f"Only {listing.stock or 0} in stock")
        listing.stock -= order_data.quantity

    point = None
    if order_data.latitude is not None and order_data.longitude is not None:
        point = ST_GeogFromText(f"POINT({order_data.longitude} {order_data.latitude})")


    unit_price = listing.price
    total_price = unit_price * order_data.quantity

    new_order = Order(
        listing_id=listing.id,
        buyer_id=current_user.id,
        seller_id=business.owner_id,
        business_id=business.id,
        kind=listing.kind,
        listing_title=listing.title,
        quantity=order_data.quantity,
        unit_price=unit_price,
        total_price=total_price,
        note=order_data.note,
        scheduled_for=order_data.scheduled_for,
        location=point,
        location_name=order_data.location_name,
        address_details=order_data.address_details,
        status=OrderStatus.PENDING,
    )

    db.add(new_order)
    try:
        await db.commit()
        await db.refresh(new_order)
    except Exception:
        await db.rollback()
        raise

    return new_order

@router.get("/me", response_model=list[OrderResponse])
async def get_my_orders(
    status: OrderStatus | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Order).where(Order.buyer_id == current_user.id).order_by(Order.created_at.desc())
    if status:
        query = query.where(Order.status == status)

    result = await db.execute(query)
    return result.scalars().all()

@router.get("/received", response_model=list[OrderResponse])
async def get_received_orders(
    status: OrderStatus | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Order).where(Order.seller_id == current_user.id).order_by(Order.created_at.desc())
    if status:
        query = query.where(Order.status == status)

    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{id}", response_model=OrderResponse)
async def get_order(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    order = (await db.execute(select(Order).where(Order.id == id))).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.buyer_id != current_user.id and order.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this order")

    return order

# Lifecycle transitions

async def _transition_order(id: int, user_id: int, db: AsyncSession, expected_status: OrderStatus, new_status: OrderStatus, role: str, status_note: str | None = None):
    order = (await db.execute(select(Order).where(Order.id == id).with_for_update())).scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    is_buyer = order.buyer_id == user_id
    is_seller = order.seller_id == user_id

    if role == "seller" and not is_seller:
        raise HTTPException(status_code=403, detail="Only the seller can perform this action")
    if role == "buyer" and not is_buyer:
        raise HTTPException(status_code=403, detail="Only the buyer can perform this action")

    if order.status != expected_status:
        raise HTTPException(status_code=400, detail=f"Order must be {expected_status.value} to be {new_status.value}")

    order.status = new_status
    if status_note:
        order.status_note = status_note

    # Manage timestamps & stock restorations
    now = datetime.now(timezone.utc)
    if new_status == OrderStatus.ACCEPTED:
        order.accepted_at = now
    elif new_status == OrderStatus.FULFILLED:
        order.fulfilled_at = now
    elif new_status == OrderStatus.COMPLETED:
        order.completed_at = now
    elif new_status in (OrderStatus.DECLINED, OrderStatus.CANCELLED):
        if new_status == OrderStatus.DECLINED:
            order.cancelled_at = now  # Or you can add a declined_at if you prefer, mapping to cancelled_at is standard
        else:
            order.cancelled_at = now

        # Restore stock for goods
        if order.kind == ListingKind.GOOD:
            listing = (await db.execute(select(Service).where(Service.id == order.listing_id).with_for_update())).scalar_one_or_none()
            if listing and listing.stock is not None:
                listing.stock += order.quantity

    try:
        await db.commit()
        await db.refresh(order)
    except Exception:
        await db.rollback()
        raise

    return order

@router.patch("/{id}/accept", response_model=OrderResponse)
async def accept_order(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await _transition_order(id, current_user.id, db, OrderStatus.PENDING, OrderStatus.ACCEPTED, "seller")

@router.patch("/{id}/decline", response_model=OrderResponse)
async def decline_order(id: int, payload: OrderStatusNote = OrderStatusNote(), db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await _transition_order(id, current_user.id, db, OrderStatus.PENDING, OrderStatus.DECLINED, "seller", payload.status_note)

@router.patch("/{id}/cancel", response_model=OrderResponse)
async def cancel_order(id: int, payload: OrderStatusNote = OrderStatusNote(), db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await _transition_order(id, current_user.id, db, OrderStatus.PENDING, OrderStatus.CANCELLED, "buyer", payload.status_note)

@router.patch("/{id}/fulfil", response_model=OrderResponse)
async def fulfil_order(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await _transition_order(id, current_user.id, db, OrderStatus.ACCEPTED, OrderStatus.FULFILLED, "seller")

@router.patch("/{id}/complete", response_model=OrderResponse)
async def complete_order(id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await _transition_order(id, current_user.id, db, OrderStatus.FULFILLED, OrderStatus.COMPLETED, "buyer")
