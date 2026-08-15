from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dependencies import get_current_user, get_db
from models import Business, Media
from schemas import BusinessUpdate, BusinessResponse, BusinessCreate, MediaResponse, MediaType
from utils import upload_image

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

@router.post("/me/images", response_model=MediaResponse)
async def upload_business_image(file: UploadFile = File(...), db: AsyncSession = Depends(get_db),
                                current_user=Depends(get_current_user)):

    # Find the user's business
    result = await db.execute(select(Business).where(Business.owner_id == current_user.id))

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

@router.delete("/me")
async def delete_my_business():
    pass

