from passlib.context import CryptContext
import hashlib
from datetime import datetime, timedelta
from jose import jwt, JWTError
from core import ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def hash_password(password: str) -> str:

    password = hashlib.sha256(password.encode()).hexdigest()

    return pwd_context.hash(password)

async def verify_password(plain_password : str, hashed_password : str) -> bool:
    
    plain_password = hashlib.sha256(plain_password.encode()).hexdigest()

    return pwd_context.verify(plain_password, hashed_password)


# access token for logged in user
def create_access_token(data: dict):
    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    #update the data dictionary to include expire or add iat time stamp
    to_encode.update({"exp": expire})

    #Generate jwt signed token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt