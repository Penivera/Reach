from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File
from models import User, Skill, UserSkill
from schemas import UserUpdate, UserPublicResponse, UserResponse, UserSkillUpdate, SkillResponse, LocationUpdate, FCMTokenUpdate, OnchainAddressUpdate
from payment_validation import PaymentProfileValidationError, validate_solana_address
from sqlalchemy import delete, select
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from dependencies import get_current_user, get_db
from utils import upload_image
from geoalchemy2.functions import ST_GeogFromText


router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserResponse)
async def get_profile(db:AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    return current_user

@router.patch("/me", response_model=UserResponse)
async def update_profile(data: UserUpdate, db: AsyncSession=Depends(get_db),
                         current_user=Depends(get_current_user)):

    update_data = data.model_dump(
        exclude_unset = True
    )

    for field, value in update_data.items():
        setattr(current_user, field, value)

    try:
        await db.commit()

        await db.refresh(current_user)

    except Exception:
        await db.rollback()
        raise

    return current_user

@router.get("/{user_id}", response_model=UserPublicResponse)
async def get_user(user_id:int, db:AsyncSession=Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))

    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    return user

@router.get("", response_model=list[UserPublicResponse])
async def get_users(db: AsyncSession=Depends(get_db)):
    result = await db.execute(select(User))

    users = result.scalars().all()

    return users

@router.get("/me/skills", response_model=list[SkillResponse])
async def get_my_skills(db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(
        select(UserSkill)
        .options(selectinload(UserSkill.skill))
        .where(UserSkill.user_id == current_user.id)
    )
    return [user_skill.skill for user_skill in result.scalars().all()]

@router.put("/me/skills")
async def update_my_skills(data: UserSkillUpdate,
                           db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):

    result = await db.execute(select(Skill).where(Skill.id.in_(data.skill_ids)))

    skills = result.scalars().all()

    if len(skills) != len(set(data.skill_ids)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="One or more skill do not exist")

    await db.execute(
        delete(UserSkill).where(UserSkill.user_id == current_user.id)
    )
    db.add_all(
        UserSkill(user_id=current_user.id, skill_id=skill.id)
        for skill in skills
    )

    try:
        await db.commit()

        await db.refresh(current_user)

    except Exception:
        await db.rollback()
        raise

    return {"message": "Skills updated successfully"}

@router.put("/me/onchain-address", response_model=UserResponse)
async def update_onchain_address(
    data: OnchainAddressUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Set the user's Solana wallet address.

    A provider needs this before they can apply or be paid. A client who funds
    an escrow from their own wallet uses the same field: that wallet becomes
    the on-chain creator and signs ``create_task``, ``accept`` and
    ``approve_work``.
    """
    try:
        address = validate_solana_address(data.onchain_address)
    except PaymentProfileValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    current_user.onchain_address = address

    try:
        await db.commit()
        await db.refresh(current_user)
    except Exception:
        await db.rollback()
        raise

    return current_user


@router.put("/me/location")
async def update_location(data: LocationUpdate, db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    if data.latitude is not None and data.longitude is not None:
        current_user.location = ST_GeogFromText(f"POINT({data.longitude} {data.latitude})")
    current_user.location_name = data.location_name
    current_user.location_updated_at = datetime.now(timezone.utc)

    try:
        await db.commit()

        await db.refresh(current_user)

    except Exception:
        await db.rollback()
        raise

    return {"message": "Location updated successfully"}


@router.put("/me/fcm-token")
async def update_fcm_token(data: FCMTokenUpdate, db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):

    current_user.fcm_token = data.fcm_token

    try:
        await db.commit()
        await db.refresh(current_user)
    except Exception:
        await db.rollback()
        raise

@router.delete("/me")
async def delete_me(db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    current_user.is_deleted = True

    try:
        await db.commit()

    except Exception:
        await db.rollback()
        raise

    return {"message": "Account deleted successfully"}

@router.put("/me/profile-image")
async def upload_profile_image(file: UploadFile = File(...), db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):

    #Upload image to Cloudinary
    image_url = await upload_image(file, folder=f"profiles/{current_user.id}")

    # Save URL to user
    current_user.profile_image = image_url

    try:
        await db.commit()
        await db.refresh(current_user)

    except Exception:
        await db.rollback()
        raise

    return {"message": "Profile image uploaded successfully", "profile_image": current_user.profile_image}
