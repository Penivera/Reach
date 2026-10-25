"""listing kind, price, stock

Revision ID: a64a1b2307d9
Revises: b3c4d5e6f7a8
Create Date: 2026-10-25 16:13:46.874928

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a64a1b2307d9'
down_revision: Union[str, Sequence[str], None] = 'b3c4d5e6f7a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    kind_enum = postgresql.ENUM("GOOD", "SERVICE", name="listingkind")
    kind_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "services",
        sa.Column(
            "kind",
            postgresql.ENUM("GOOD", "SERVICE", name="listingkind", create_type=False),
            nullable=False,
            server_default="SERVICE",
        ),
    )
    op.add_column("services", sa.Column("stock", sa.Integer(), nullable=True))
    op.alter_column("services", "starting_price", new_column_name="price")


def downgrade() -> None:
    op.alter_column("services", "price", new_column_name="starting_price")
    op.drop_column("services", "stock")
    op.drop_column("services", "kind")
    postgresql.ENUM(name="listingkind").drop(op.get_bind(), checkfirst=True)
