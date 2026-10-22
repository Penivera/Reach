import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv

from DB.database import Base
# We must import all models so SQLAlchemy registers them before building
from models import (User, UserSkill, Skill, EmailVerificationToken, PasswordResetToken, Service, ServiceRequest,
Job, JobApplication, Category, ConversationParticipant, Conversation, Message, Media, Notification, Report,
Review, TimeStampMixin, Business)

load_dotenv(override=True)
db_url = os.environ.get("DATABASE_URL")

async def build_tables():
    print("Commanding Supabase to build tables...")
    engine = create_async_engine(db_url)

    try:
        async with engine.begin() as conn:
            # This directly creates all tables that don't exist yet
            await conn.run_sync(Base.metadata.create_all)
        print("All tables created successfully!")
    except Exception as e:
        print(f"❌ Failed: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(build_tables())
