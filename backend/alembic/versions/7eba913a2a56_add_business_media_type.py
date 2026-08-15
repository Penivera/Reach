"""add business media type

Revision ID: 7eba913a2a56
Revises: 7ec44a13ae47
Create Date: 2026-08-15 12:39:15.530524

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7eba913a2a56'
down_revision: Union[str, Sequence[str], None] = '7ec44a13ae47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
