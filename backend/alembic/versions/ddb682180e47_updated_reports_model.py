"""updated reports model

Revision ID: ddb682180e47
Revises: c3629f3130ba
Create Date: 2026-08-28 10:45:14.734895

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'ddb682180e47'
down_revision: Union[str, Sequence[str], None] = 'c3629f3130ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    reportstatus_enum = postgresql.ENUM(
        'OPEN', 'UNDER_REVIEW', 'RESOLVED', 'DISMISSED',
        name='reportstatus'
    )
    reportstatus_enum.create(op.get_bind(), checkfirst=True)

    op.alter_column(
        'reports',
        'status',
        existing_type=sa.VARCHAR(),
        type_=reportstatus_enum,
        existing_nullable=False,
        postgresql_using='status::reportstatus'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'reports',
        'status',
        existing_type=postgresql.ENUM('OPEN', 'UNDER_REVIEW', 'RESOLVED', 'DISMISSED', name='reportstatus'),
        type_=sa.VARCHAR(),
        existing_nullable=False
    )
    postgresql.ENUM(name='reportstatus').drop(op.get_bind(), checkfirst=True)
