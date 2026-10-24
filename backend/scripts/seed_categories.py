"""Idempotently seed the core marketplace categories.

Usage (from ``backend/``):

    venv/bin/python -m scripts.seed_categories

The Alembic data migration ``b3c4d5e6f7a8`` does the same thing on deploy.
This script is for local databases created with ``build_tables.py`` or for
operators who need to repair a database without running migrations.
"""

import asyncio

from dotenv import load_dotenv


async def main() -> None:
    # Load the environment before importing the engine: DB.database reads
    # DATABASE_URL at import time.
    load_dotenv()

    from sqlalchemy.dialects.postgresql import insert

    from DB.database import AsyncSessionLocal
    from core.seed_data import CORE_CATEGORIES
    from models import Category

    async with AsyncSessionLocal() as db:
        statement = (
            insert(Category)
            .values(
                [
                    {"name": name, "description": description}
                    for name, description in CORE_CATEGORIES
                ]
            )
            .on_conflict_do_nothing(index_elements=["name"])
        )
        await db.execute(statement)
        await db.commit()

    print(f"Seeded {len(CORE_CATEGORIES)} core categories (existing names kept).")


if __name__ == "__main__":
    asyncio.run(main())
