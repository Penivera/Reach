from fastapi import APIRouter, HTTPException, status, Depends
from models import User, Skill, UserSkill
from schemas import UserUpdate, UserPublicResponse, UserResponse, UserSkillUpdate, SkillResponse, LocationUpdate, FCMTokenUpdate
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from dependencies import get_current_user, get_db



router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserResponse)
async def get_profile(db:AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    return current_user

@router.patch("/me")
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
    return [user_skill.skill for user_skill in current_user.user_skill]

@router.put("/me/skills")
async def update_my_skills(data: UserSkillUpdate, 
                           db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    
    result = await db.execute(select(Skill).where(Skill.id.in_(data.skill_ids)))

    skills = result.scalars().all()

    if len(skills) != len(set(data.skill_ids)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="One or more skill do not exist")
    
    current_user.skills.clear()

    current_user.skills.extend(
        UserSkill(skill=skill)
        for skill in skills
    )

    try: 
        await db.commit()

        await db.refresh(current_user)
    
    except Exception:
        await db.rollback()
        raise

    return {"message": "Skills updated successfully"}

@router.put("/me/location")
async def update_location(data: LocationUpdate,
                          db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    current_user.latitude = data.latitude
    current_user.longitude = data.longitude
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
    current_user.is_delete = True
    
    try:
        await db.commit()

    except Exception:
        await db.rollback()
        raise

    return {"message": "Account deleted successfully"}