"""add near chain ids to jobs and applications

Revision ID: cfd439b3afcc
Revises: 8bff32d101ed
Create Date: 2026-08-12 09:57:21.459451

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cfd439b3afcc'
down_revision: Union[str, Sequence[str], None] = '8bff32d101ed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column("jobs", sa.Column("near_task_id", sa.Integer(), nullable=True))
    op.add_column("job_applications", sa.Column("near_application_id", sa.Integer(), nullable=True))

def downgrade():
    op.drop_column("jobs", "near_task_id")
    op.drop_column("job_applications", "near_application_id")
