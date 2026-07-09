from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import User

async def get_user_by_id(user_id:int, db: AsyncSession):
    result = await db.execute(select(User).where(User.id == user_id, User.is_deleted.is_(False)))

    db_user = result.scalar_one_or_none()
    
    return db_user
