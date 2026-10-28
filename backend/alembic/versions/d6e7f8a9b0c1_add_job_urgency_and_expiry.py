"""add job urgency and expiry

Revision ID: d6e7f8a9b0c1
Revises: a64a1b2307d9
Create Date: 2026-10-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "d6e7f8a9b0c1"
down_revision: Union[str, Sequence[str], None] = "a64a1b2307d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    urgency_enum = postgresql.ENUM(
        "ASAP",
        "THIS_WEEK",
        "FLEXIBLE",
        name="joburgency",
    )
    urgency_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "jobs",
        sa.Column(
            "urgency",
            postgresql.ENUM(
                "ASAP",
                "THIS_WEEK",
                "FLEXIBLE",
                name="joburgency",
                create_type=False,
            ),
            nullable=False,
            server_default="FLEXIBLE",
        ),
    )
    op.add_column(
        "jobs",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("jobs", "expires_at")
    op.drop_column("jobs", "urgency")
    postgresql.ENUM(name="joburgency").drop(op.get_bind(), checkfirst=True)
