from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'ce62615eece1'
down_revision: Union[str, Sequence[str], None] = '250b19ddb7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    jobstatus_enum = postgresql.ENUM(
        'OPEN', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED',
        name='jobstatus'
    )
    jobstatus_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        'jobs',
        sa.Column(
            'status',
            postgresql.ENUM(
                'OPEN', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED',
                name='jobstatus',
                create_type=False,
            ),
            nullable=False,
            server_default='OPEN',
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('jobs', 'status')
    postgresql.ENUM(name='jobstatus').drop(op.get_bind(), checkfirst=True)