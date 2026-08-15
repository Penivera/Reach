"""add job and services relationship to media

Revision ID: 9777c3ebfa7c
Revises: 7eba913a2a56
Create Date: 2026-08-15 13:31:32.856536

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9777c3ebfa7c'
down_revision: Union[str, Sequence[str], None] = '7eba913a2a56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
