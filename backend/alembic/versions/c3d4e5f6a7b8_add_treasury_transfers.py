"""add treasury transfers

Withdrawals of USDC from the payment provider into the on-chain escrow float.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-10-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


treasurytransferstatus_enum = postgresql.ENUM(
    'PENDING',
    'SUBMITTED',
    'CONFIRMED',
    'FAILED',
    name='treasurytransferstatus',
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    treasurytransferstatus_enum.create(bind, checkfirst=True)

    op.create_table(
        'treasury_transfers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('reference', sa.String(length=150), nullable=True),
        sa.Column('amount_units', sa.BigInteger(), nullable=False),
        sa.Column(
            'currency',
            sa.String(length=10),
            nullable=False,
            server_default=sa.text("'USDC'"),
        ),
        sa.Column('network', sa.String(length=20), nullable=True),
        sa.Column('destination', sa.String(length=120), nullable=True),
        sa.Column(
            'status',
            treasurytransferstatus_enum,
            nullable=False,
            server_default=sa.text("'PENDING'"),
        ),
        sa.Column('tx_hash', sa.String(length=128), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_treasury_transfers_reference',
        'treasury_transfers',
        ['reference'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('ix_treasury_transfers_reference', table_name='treasury_transfers')
    op.drop_table('treasury_transfers')

    bind = op.get_bind()
    postgresql.ENUM(name='treasurytransferstatus').drop(bind, checkfirst=True)
