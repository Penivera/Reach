from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import selectinload
from dependencies import get_current_user, get_db
from models import Business, Media, Order
from models.services import Service
from schemas import (
    BusinessCreate,
    BusinessDetailResponse,
    BusinessResponse,
    BusinessUpdate,
    MediaResponse,
    MediaType,
)
from utils import upload_image
from schemas.enums import OrderStatus, ServiceStatus

router = APIRouter(prefix="/businesses", tags=["businesses"])


@router.post("", response_model=BusinessResponse)
async def create_business(business_data: BusinessCreate, db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(Business).where(Business.owner_id == current_user.id))

    business_exist = result.scalar_one_or_none()

    if business_exist and not business_exist.is_deleted:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="you already have a business")

    if business_exist:  # soft-deleted shop: reuse the row
        business_exist.name = business_data.name
        business_exist.description = business_data.description
        business_exist.is_deleted = False
        business = business_exist
    else:
        business = Business(**business_data.model_dump(), owner_id=current_user.id)
        db.add(business)

    try:
        await db.commit()
        await db.refresh(business)
    except Exception:
        await db.rollback()
        raise

    return business


@router.get("/me", response_model=BusinessDetailResponse)
async def get_my_business(db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(
        select(Business)
        .options(selectinload(Business.media))
        .where(Business.owner_id == current_user.id, Business.is_deleted == False)
    )

    business = result.scalar_one_or_none()

    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="business not found")

    return business


@router.patch("/me", response_model=BusinessResponse)
async def update_my_business(business_data: BusinessUpdate, db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(
        select(Business).where(
            Business.owner_id == current_user.id, Business.is_deleted == False
        )
    )

    business = result.scalar_one_or_none()

    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="business not found")

    update_data = business_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(business, field, value)

    try:
        await db.commit()
        await db.refresh(business)
    except Exception:
        await db.rollback()
        raise

    return business

@router.post("/me/images", response_model=MediaResponse)
async def upload_business_image(file: UploadFile = File(...), db: AsyncSession = Depends(get_db),
                                current_user=Depends(get_current_user)):

    # Find the user's business
    result = await db.execute(
        select(Business).where(
            Business.owner_id == current_user.id, Business.is_deleted == False
        )
    )

    business = result.scalar_one_or_none()

    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")

    # Make sure the uploaded file is an image
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only image files are allowed")

    #Upload image to Cloudinary
    image_url = await upload_image(file, folder=f"businesses/{business.id}")

    #Create Media database record
    media = Media(url=image_url, media_type=MediaType.BUSINESS,
                  uploaded_by=current_user.id, business_id=business.id)

    db.add(media)

    try:
        await db.commit()
        await db.refresh(media)

    except Exception:
        await db.rollback()
        raise

    return media

@router.get("/me/exists")
async def has_business(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(
        select(Business.id).where(
            Business.owner_id == current_user.id, Business.is_deleted == False
        )
    )
    business_id = result.scalar_one_or_none()
    return {"has_business": business_id is not None, "business_id": business_id}

@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_business(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    business = (
        await db.execute(
            select(Business).where(
                Business.owner_id == current_user.id, Business.is_deleted == False
            )
        )
    ).scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=404, detail="business not found")

    open_orders = (
        await db.execute(
            select(func.count())
            .select_from(Order)
            .where(
                Order.seller_id == current_user.id,
                Order.status.in_(
                    [OrderStatus.PENDING, OrderStatus.ACCEPTED, OrderStatus.FULFILLED]
                ),
            )
        )
    ).scalar_one()
    if open_orders:
        raise HTTPException(
            status_code=400,
            detail="Finish or decline your open orders before deleting your shop",
        )

    await db.execute(
        update(Service)
        .where(Service.business_id == business.id)
        .values(status=ServiceStatus.ARCHIVED)
    )
    await db.execute(delete(Media).where(Media.business_id == business.id))
    business.is_deleted = True
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@router.get("/{business_id}", response_model=BusinessDetailResponse)
async def get_business(business_id: int, db: AsyncSession = Depends(get_db)):
    business = (
        await db.execute(
            select(Business)
            .options(selectinload(Business.media))
            .where(Business.id == business_id, Business.is_deleted == False)
        )
    ).scalar_one_or_none()
    if not business or business.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="business not found")
    return business


@router.get("", response_model=list[BusinessDetailResponse])
async def list_businesses(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Business)
        .options(selectinload(Business.media))
        .where(Business.is_deleted == False)
    )
    return result.scalars().all()
