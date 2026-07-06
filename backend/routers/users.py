from fastapi import APIRouter, HTTPException, status, Depends
from models import User
from schemas import UserUpdate, UserPublicResponse, UserResponse
from sqlalchemy import select, delete
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

@router.delete("/me")
async def delete_me(db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    current_user.is_delete = True
    
    try:
        await db.commit()

    except Exception:
        await db.rollback()
        raise

    return {"message": "Account deleted successfully"}