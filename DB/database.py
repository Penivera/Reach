from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.dialects.sqlite import *
from core import DATABASE_URL
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

engine = create_async_engine(DATABASE_URL,
                             echo = True,
                             future = True)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_ = AsyncSession,
    expire_on_commit= False,
    auto_flush=False
)

Base = declarative_base()