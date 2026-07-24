from fastapi import APIRouter, HTTPException, status, Depends, Response
from models import User, EmailVerificationToken, PasswordResetToken
from schemas import (UserCreate, UserResponse, EmailVerificationRequest, 
                     ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest, ResendEmailVerificationRequest, UserSignUpResponse)
from utils import hash_password, verify_password, create_access_token, generate_token, send_verification_email, send_reset_password_email
from dependencies import get_db, get_current_user
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta, datetime
from geoalchemy2.functions import ST_GeogFromText


router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/create-user", response_model=UserSignUpResponse)
async def create_user(user_data: UserCreate, db: AsyncSession =Depends(get_db)):
    
    result = await db.execute(select(User).where(User.username == user_data.username))

    user_exist = result.scalar_one_or_none()

    if user_exist:
        raise HTTPException(status_code=400, detail="Username is taken")


    result = await db.execute(select(User).where(User.email == user_data.email))

    email_exist = result.scalar_one_or_none()

    if email_exist:
        raise HTTPException(status_code=400, detail="Email already has an account")
    
    point = None

    if user_data.longitude is not None and user_data.latitude is not None:

        point = ST_GeogFromText(f"POINT({user_data.longitude} {user_data.latitude})")

    data = user_data.model_dump()
    data.pop("confirm_password")
    data.pop("latitude")
    data.pop("longitude")

    data["hashed_password"] = await hash_password(data["hashed_password"])
    data["location"] = point

    new_user = User(**data)
    
    try:
        db.add(new_user)

        await db.flush()

        token = await generate_token()

        verification_token = EmailVerificationToken(
            user_id = new_user.id,
            token = token,
            expires_at=datetime.utcnow() + timedelta(hours=24)

        )

        db.add(verification_token)
        await db.commit()

    except Exception:
        await db.rollback()
        raise

    return new_user

@router.get("/verify-email")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(EmailVerificationToken).where(EmailVerificationToken.token == token)
    )
    verification_token = result.scalar_one_or_none()

    if not verification_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token")

    if verification_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Expired verification token")

    result = await db.execute(
        select(User).where(User.id == verification_token.user_id, User.is_deleted.is_(False))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_email_verified = True
    await db.delete(verification_token)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return {"message": "email verified successfully"}

@router.post("/resend-verification")
async def resend_verification(data: ResendEmailVerificationRequest, db: AsyncSession = Depends(get_db)):


    result = await db.execute(select(User).where(User.email == data.email, 
                                                 User.is_deleted.is_(False)))

    user = result.scalar_one_or_none()

    if not user:
        return {"message": "check your email for verification link"}
    
    if user.is_email_verified:
        raise HTTPException(status_code=400, detail="email is already verified")
    
    await db.execute(delete(EmailVerificationToken).where(EmailVerificationToken.user_id == user.id))



    token = await generate_token()

    verification_token = EmailVerificationToken(user_id = user.id,
                                                token = token,
                                                expires_at = datetime.utcnow() + timedelta(hours=20))
    
    db.add(verification_token)
    
    try:

        await db.commit()
    
    except Exception:
        await db.rollback()
        raise

    await send_verification_email(user.email, token)

    return {"message": "check your email for verification link"}

@router.post("/login")
async def login_user(response: Response, form_data: OAuth2PasswordRequestForm=Depends(), db: AsyncSession=Depends(get_db)):
    result = await db.execute(select(User).where(User.username == form_data.username,
                                                  User.is_deleted.is_(False)))

    db_user = result.scalar_one_or_none()

    if not (db_user and await verify_password(form_data.password, db_user.hashed_password)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Credential")
    
    if not db_user.is_email_verified:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Pease verify your email before logging in")
    
    token = create_access_token(data={"sub": str(db_user.id)})

    response.set_cookie(
    key="access_token",
    value=token,
    httponly=True,
    samesite="lax",
    max_age=60 * 15
    )

    return {"message": "Logged in"}

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    response.delete_cookie(
        key="access_token",
        httponly=True,
        samesite="lax",
        path="/",
    )


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):

    result = await db.execute(select(User).where(User.email == data.email,
                                                  User.is_deleted.is_(False)))

    user_exist = result.scalar_one_or_none()

    if not user_exist:
        return {"message": "password reset link has been sent to your email"}
    
    await db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user_exist.id))


    token = await generate_token()

    password_reset_token = PasswordResetToken(user_id = user_exist.id,
                                                token = token,
                                            expires_at = datetime.utcnow() + timedelta(minutes=20))

    db.add(password_reset_token)

    try:
        await db.commit()
    
    except Exception:
        await db.rollback()
        raise

    await send_reset_password_email(user_exist.email, token)

    return {"message": "password reset link has been sent to your email"}

@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    
    result = await db.execute(select(PasswordResetToken).where(PasswordResetToken.token == data.token))

    reset_token = result.scalar_one_or_none()

    if not reset_token:
        raise HTTPException(status_code = 400, detail="Invalid password reset token")
    
    if reset_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code = 400, detail="Expired password reset token")
    

    result = await db.execute(select(User).where(User.id == reset_token.user_id,
                                                 User.is_deleted.is_(False)))
    
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code = 404, detail="User doesn't exist")
    

    hashed_password = await hash_password(data.new_password)

    user.hashed_password = hashed_password

    await db.delete(reset_token)

    try:
        await db.commit()
    
    except Exception:
        await db.rollback()
        raise

    return {"message": "password reset successfully"}

@router.post("/change-password")
async def change_password(data: ChangePasswordRequest,
                           db: AsyncSession=Depends(get_db),
                          current_user=Depends(get_current_user)):
    
    db_user = current_user

    if not db_user:
        raise HTTPException(status_code=404, detail="user not found!")
    
    if not await verify_password(data.old_password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="incorrect password")
    
    if await verify_password(data.new_password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="New password must be different from the current password")
    
    hashed_password = await hash_password(data.new_password)

    db_user.hashed_password = hashed_password

    try:

        await db.commit()
    
    except Exception:
        await db.rollback()    
        raise

    return {"message": "password changed successfully"}

