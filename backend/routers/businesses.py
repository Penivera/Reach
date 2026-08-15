from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dependencies import get_current_user, get_db
from models import Business
from schemas import BusinessUpdate, BusinessResponse, BusinessCreate

router = APIRouter(prefix="/businesses", tags=["businesses"])

@router.post("/", response_model=BusinessResponse)
async def create_business(business_data: BusinessCreate, db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(Business).where(Business.owner_id == current_user.id))

    business_exist = result.scalar_one_or_none()

    if business_exist:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="you already have a business")

    business = Business(**business_data.model_dump())

    await db.add(business)

    try:
        await db.commit()
        await db.refresh(business)
    except Exception:
        await db.rollback()
        raise

    return business


@router.get("/me", response_model=BusinessResponse)
async def get_my_business(db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(Business).where(Business.owner_id == current_user.id))

    business = result.scalar_one_or_none()

    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="business not found")

    return business


@router.patch("/me", response_model=BusinessResponse)
async def update_my_business(business_data: BusinessUpdate, db:AsyncSession=Depends(get_db), current_user=Depends(get_db)):
    result = await db.execute(select(Business).where(Business.owner_id == current_user.id))

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


@router.delete("/me")
async def delete_my_business():
    pass