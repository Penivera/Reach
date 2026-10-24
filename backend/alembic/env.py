import asyncio
import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from DB.database import Base
from models import (  # noqa: F401 - imported so Base.metadata is complete
    Business,
    Category,
    Conversation,
    ConversationParticipant,
    EmailVerificationToken,
    FossaPayCustomer,
    Job,
    JobApplication,
    Media,
    Message,
    Notification,
    PasswordResetToken,
    PaymentIntent,
    PaymentProfile,
    Payout,
    Report,
    Review,
    Service,
    ServiceRequest,
    Skill,
    TimeStampMixin,
    User,
    UserSkill,
    WebhookEvent,
)

config = context.config

# Load backend/.env even when alembic is invoked from the backend directory.
load_dotenv(override=True)

db_url = os.environ.get("DATABASE_URL")
if not db_url:
    raise ValueError(
        "DATABASE_URL is missing! Make sure your .env file is in the right place."
    )

config.set_main_option("sqlalchemy.url", db_url.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a DB connection (`alembic upgrade --sql`)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
