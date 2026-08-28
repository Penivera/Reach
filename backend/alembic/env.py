from logging.config import fileConfig
from core.configs import settings
from DB.database import Base
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
import asyncio

from models import (User, UserSkill, Skill, EmailVerificationToken, PasswordResetToken, Service, ServiceRequest,
Job, JobApplication, Category, ConversationParticipant, Conversation, Message, Media, Notification, Report,
Review, TimeStampMixin, Business)
from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

config.set_main_option(
    "sqlalchemy.url",
    settings.DATABASE_URL,
)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata


def include_object(object, name, type_, reflected, compare_to):
    """
    Whitelist-based filter for autogenerate.

    Instead of trying to enumerate every table that PostGIS / tiger
    geocoder / postgis_topology might create (spatial_ref_sys, edges,
    faces, featnames, state, county, tabblock, topology, layer, ...),
    we only ever consider a reflected table if it's one WE defined in
    our own SQLAlchemy models (i.e. present in target_metadata.tables).

    Anything reflected from the database that isn't one of our own
    tables is excluded automatically, regardless of what extension
    created it or what it's named, now or in the future.
    """
    if type_ == "table":
        if reflected and name not in target_metadata.tables:
            return False
        return True

    # For non-table objects (columns, indexes, constraints, etc.),
    # only evaluate them if they belong to a table we actually track.
    if hasattr(object, "table") and object.table.name not in target_metadata.tables:
        return False

    return True


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:

        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())