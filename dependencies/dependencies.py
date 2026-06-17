from DB import AsyncSessionLocal
from core import SECRET_KEY, ALGORITHM

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session