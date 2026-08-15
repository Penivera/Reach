"""merge near and business migrations

Revision ID: 8505d048d9ff
Revises: cfd439b3afcc, f544e9bab24b
Create Date: 2026-08-15 10:05:18.783414

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8505d048d9ff'
down_revision: Union[str, Sequence[str], None] = ('cfd439b3afcc', 'f544e9bab24b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
