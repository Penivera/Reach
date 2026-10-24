"""seed core marketplace categories

Revision ID: b3c4d5e6f7a8
Revises: f1a2b3c4d5e6
Create Date: 2026-10-24 00:00:00.000000

The frontend needs stable category ids on a fresh database. This is a data
migration rather than a model change; it is idempotent, so re-running it is
safe even if an operator has already created some of these names.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from core.seed_data import CORE_CATEGORIES


revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _categories_table():
    return sa.table(
        "categories",
        sa.column("name", sa.String),
        sa.column("description", sa.String),
    )


def upgrade() -> None:
    categories = _categories_table()
    op.execute(
        postgresql.insert(categories)
        .values(
            [
                {"name": name, "description": description}
                for name, description in CORE_CATEGORIES
            ]
        )
        .on_conflict_do_nothing(index_elements=["name"])
    )


def downgrade() -> None:
    # Do not remove a category that is already referenced by a job or service.
    # The database will reject the delete in that case, which is safer than
    # deleting marketplace data on a rollback.
    categories = _categories_table()
    names = [name for name, _ in CORE_CATEGORIES]
    op.execute(categories.delete().where(categories.c.name.in_(names)))
