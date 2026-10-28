"""job schedule address and required expiry

Revision ID: 9cfd05c41eb8
Revises: 630262ee4fbe
Create Date: 2026-10-28 12:13:56.912650

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9cfd05c41eb8'
down_revision: Union[str, Sequence[str], None] = '630262ee4fbe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # match the Python enum name UrgencyLevel (skip if you kept JobUrgency)
    op.execute("""
    DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'joburgency')
         AND NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'urgencylevel') THEN
        ALTER TYPE joburgency RENAME TO urgencylevel;
      END IF;
    END $$;
    """)
    op.add_column('jobs', sa.Column('scheduled_for', sa.DateTime(timezone=True), nullable=True))
    op.add_column('jobs', sa.Column('address_details', sa.String(300), nullable=True))
    op.execute("UPDATE jobs SET expires_at = now() + interval '30 days' WHERE expires_at IS NULL")
    op.alter_column('jobs', 'expires_at', existing_type=sa.DateTime(timezone=True), nullable=False)
    op.create_index('ix_jobs_expires_at', 'jobs', ['expires_at'])
    op.execute(
        "INSERT INTO categories (name, description) "
        "VALUES ('Other', 'Anything that does not fit another category') "
        "ON CONFLICT (name) DO NOTHING")

def downgrade():
    op.drop_index('ix_jobs_expires_at', table_name='jobs')
    op.alter_column('jobs', 'expires_at', existing_type=sa.DateTime(timezone=True), nullable=True)
    op.drop_column('jobs', 'address_details')
    op.drop_column('jobs', 'scheduled_for')
