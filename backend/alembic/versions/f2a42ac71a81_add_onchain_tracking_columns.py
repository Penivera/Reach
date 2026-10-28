"""add onchain tracking columns

Revision ID: f2a42ac71a81
Revises: 9cfd05c41eb8
Create Date: 2026-10-28 13:13:35.379239

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2a42ac71a81'
down_revision: Union[str, Sequence[str], None] = '9cfd05c41eb8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('jobs', sa.Column('onchain_task_id', sa.Integer(), nullable=True))
    op.add_column('jobs', sa.Column('onchain_tx_hash', sa.String(128), nullable=True))
    op.add_column('job_applications', sa.Column('onchain_application_id', sa.Integer(), nullable=True))

def downgrade():
    op.drop_column('job_applications', 'onchain_application_id')
    op.drop_column('jobs', 'onchain_tx_hash')
    op.drop_column('jobs', 'onchain_task_id')
