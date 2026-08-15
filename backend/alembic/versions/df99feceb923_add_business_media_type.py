"""add business media type

Revision ID: df99feceb923
Revises: 9777c3ebfa7c
Create Date: 2026-08-15 20:39:01.898854

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from alembic import op




# revision identifiers, used by Alembic.
revision: str = 'df99feceb923'
down_revision: Union[str, Sequence[str], None] = '9777c3ebfa7c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute(
        "ALTER TYPE mediatype ADD VALUE IF NOT EXISTS 'BUSINESS'"
    )


def downgrade():
    pass
