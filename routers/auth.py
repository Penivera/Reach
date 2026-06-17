from fastapi import APIRouter, HTTPException, status, Depends
from models import User
from schemas import UserCreate, UserResponse
from utils import hash_password, verify_password, create_access_token
from dependencies import get_db
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/create_user", response_model=UserResponse)
async def create_user(user_data: UserCreate, db: AsyncSession =Depends(get_db())):
    
    try:
        result = await db.execute(select(User).where(User.username == user_data.username))

        user_exist = result.scalar_one_or_none()

        if user_exist:
            raise HTTPException(status_code=400, detail="Username is taken")
        
        data = user_data.model_dump()
        data.pop("confirm_password")

        data["password"] = hash_password(data["password"])

        new_user = User(**data)

        db.add(new_user)

        await db.commit()
        await db.refresh(new_user)

        return new_user
    
    except Exception:
        await db.rollback()
        raise

@router.post("/login")
async def login_user(form_data: OAuth2PasswordRequestForm, db: AsyncSession=Depends(get_db)):
    result = await db.execute(select(User).where(User.username == form_data.username))

    db_user = result.scalar_one_or_none()

    if not (db_user and verify_password(form_data.passord, db_user.password)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credential")
    
    token = create_access_token(data={"sub": str(db_user.id)})

    return {"access_token": token, "token_type": "bearer"}







                              

@router.post("/login")
async def login():
    pass

@router.post("/forgot_password")
async def forgot_password():
    pass

@router.post("/reset_password")
async def reset_password():
    pass

