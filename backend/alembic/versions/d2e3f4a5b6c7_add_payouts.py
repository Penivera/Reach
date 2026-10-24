"""add payouts

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-10-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'd2e3f4a5b6c7'
down_revision: Union[str, Sequence[str], None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'fossapay_customers',
        sa.Column('bank_code', sa.String(length=20), nullable=True),
    )

    payoutstatus_enum = postgresql.ENUM(
        'PROCESSING',
        'COMPLETED',
        'FAILED',
        'REVERSED',
        name='payoutstatus',
        create_type=False,
    )
    payoutstatus_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'payouts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('payment_intent_id', sa.Integer(), nullable=False),
        sa.Column('payee_id', sa.Integer(), nullable=False),
        sa.Column('reference', sa.String(length=100), nullable=False),
        sa.Column('amount_kobo', sa.BigInteger(), nullable=False),
        sa.Column('commission_kobo', sa.BigInteger(), nullable=False),
        sa.Column('provider_payout_kobo', sa.BigInteger(), nullable=False),
        sa.Column('status', payoutstatus_enum, nullable=False, server_default=sa.text("'PROCESSING'")),
        sa.Column('provider_payout_id', sa.String(length=100), nullable=True),
        sa.Column('failure_reason', sa.String(length=1000), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['payment_intent_id'], ['payment_intents.id'], ),
        sa.ForeignKeyConstraint(['payee_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_payouts_payment_intent_id', 'payouts', ['payment_intent_id'], unique=True)
    op.create_index('ix_payouts_payee_id', 'payouts', ['payee_id'], unique=False)
    op.create_index('ix_payouts_reference', 'payouts', ['reference'], unique=True)
    op.create_index('ix_payouts_provider_payout_id', 'payouts', ['provider_payout_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_payouts_provider_payout_id', table_name='payouts')
    op.drop_index('ix_payouts_reference', table_name='payouts')
    op.drop_index('ix_payouts_payee_id', table_name='payouts')
    op.drop_index('ix_payouts_payment_intent_id', table_name='payouts')
    op.drop_table('payouts')

    postgresql.ENUM(name='payoutstatus').drop(op.get_bind(), checkfirst=True)

    op.drop_column('fossapay_customers', 'bank_code')
