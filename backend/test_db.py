import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

# Load the .env file
load_dotenv(override=True)
db_url = os.environ.get("DATABASE_URL")

async def test_connection():
    print(f"Attempting connection to: {db_url}\n")

    # We use the raw URL here (no need for the %% configparser hack)
    engine = create_async_engine(db_url)

    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version();"))
            print("SUCCESS! Connected to Supabase!")
            print(f"Database info: {result.scalar()}")
    except Exception as e:
        print("❌ CONNECTION FAILED!")
        print(f"Error: {e}")
    finally:
        await engine.dispose()

asyncio.run(test_connection())
