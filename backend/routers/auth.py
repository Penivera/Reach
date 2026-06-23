from fastapi import APIRouter, HTTPException, status, Depends
from models import User, EmailVerificationToken
from schemas import UserCreate, UserResponse, EmailVerificationRequest
from utils import hash_password, verify_password, create_access_token, generate_token, send_verification_email
from dependencies import get_db, get_current_user
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta, datetime
from pydantic import EmailStr

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/create-user", response_model=UserResponse)
async def create_user(user_data: UserCreate, db: AsyncSession =Depends(get_db)):
    
    try:
        result = await db.execute(select(User).where(User.username == user_data.username))

        user_exist = result.scalar_one_or_none()

        if user_exist:
            raise HTTPException(status_code=400, detail="Username is taken")

        
        data = user_data.model_dump()
        data.pop("confirm_password")

        data["hashed_password"] = await hash_password(data["hashed_password"])

        new_user = User(**data)

        db.add(new_user)

        await db.commit()
        await db.refresh(new_user)

        token = await generate_token()

        verification_token = EmailVerificationToken(
            user_id = new_user.id,
            token = token,
            expires_at=datetime.utcnow() + timedelta(hours=24)

        )

        db.add(verification_token)
        await db.commit()

        await send_verification_email(new_user.email, token)

        return new_user

        
    
    except Exception:
        await db.rollback()
        raise

@router.post("/verify-email")
async def verify_email(data: EmailVerificationRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EmailVerificationToken).where(EmailVerificationToken.token == data.token))

    verification_token = result.scalar_one_or_none()

    if not verification_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token")
    

    if verification_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Expired verification token")
    
    user = await db.get(User, verification_token.user_id)

    user.is_email_verified = True

    await db.delete(verification_token)
    await db.commit()

    return {"message": "email verified successful"}

@router.post("/resend-verification")
async def resend_verification(email: EmailStr, db: AsyncSession = Depends(get_db)):
    pass

@router.post("/login")
async def login_user(form_data: OAuth2PasswordRequestForm=Depends(), db: AsyncSession=Depends(get_db)):
    result = await db.execute(select(User).where(User.username == form_data.username))

    db_user = result.scalar_one_or_none()

    if not (db_user and await verify_password(form_data.password, db_user.hashed_password)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credential")
    
    if not db_user.is_email_verified:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Pease verify your email before logging in")
    
    token = create_access_token(data={"sub": str(db_user.id)})

    return {"access_token": token, "token_type": "bearer"}


@router.post("/forgot-password")
async def forgot_password(email: EmailStr, db: AsyncSession = Depends(get_db)):
    pass

@router.post("/reset-password")
async def reset_password(token: str, new_password: str, db: AsyncSession = Depends(get_db)):
    pass

@router.post("/change-password")
async def change_password(current_user=Depends(get_current_user)):
    pass

