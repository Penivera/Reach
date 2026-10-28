"""job urgency expiry and other category

Revision ID: 630262ee4fbe
Revises: d6e7f8a9b0c1
Create Date: 2026-10-28 08:31:15.056008

"""
from typing import Sequence, Union
from sqlalchemy.dialects import postgresql

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '630262ee4fbe'
down_revision: Union[str, Sequence[str], None] = 'd6e7f8a9b0c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    postgresql.ENUM('ASAP', 'THIS_WEEK', 'FLEXIBLE', name='joburgency').create(op.get_bind(), checkfirst=True)
    op.add_column('jobs', sa.Column(
        'urgency',
        postgresql.ENUM('ASAP', 'THIS_WEEK', 'FLEXIBLE', name='joburgency', create_type=False),
        nullable=False, server_default='FLEXIBLE'), if_not_exists=True)
    op.add_column('jobs', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True), if_not_exists=True)
    op.execute(
        "INSERT INTO categories (name, description) "
        "VALUES ('Other', 'Anything that does not fit another category') "
        "ON CONFLICT (name) DO NOTHING")

def downgrade():
    op.drop_column('jobs', 'expires_at')
    op.drop_column('jobs', 'urgency')
    postgresql.ENUM(name='joburgency').drop(op.get_bind(), checkfirst=True)
