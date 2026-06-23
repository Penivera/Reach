from DB import AsyncSessionLocal
from core import settings
from fastapi import HTTPException, status, Depends
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer
from crud import get_user_by_id
from sqlalchemy.ext.asyncio  import AsyncSession

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(token:str=Depends(oauth2_scheme),
                           db: AsyncSession =Depends(get_db)):
    credential_exception = HTTPException(
        status_code=401, 
        detail="Could not validate credential",
        headers={"WWW-Authenticate": "Bearer"}
    )

    try: 
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        user_id = int(payload.get("sub"))

        if user_id is None:
            raise credential_exception
        
    except JWTError:
        raise credential_exception
    
    user = await get_user_by_id(user_id, db)

    if user is None:
        raise credential_exception
    
    return user