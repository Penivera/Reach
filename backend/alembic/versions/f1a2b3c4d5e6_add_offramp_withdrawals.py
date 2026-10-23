"""add provider naira off-ramp withdrawals

Revision ID: f1a2b3c4d5e6
Revises: c3d4e5f6a7b8
Create Date: 2026-10-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


offrampstatus_enum = postgresql.ENUM(
    'AWAITING_DEPOSIT',
    'PARTIALLY_FUNDED',
    'DEPOSIT_CONFIRMED',
    'WITHDRAWING',
    'PAID',
    'HELD',
    'FAILED',
    'EXPIRED',
    'CANCELLED',
    'REFUNDING',
    'REFUNDED',
    name='offrampstatus',
    create_type=False,
)


def upgrade() -> None:
    offrampstatus_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'offramp_withdrawals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('reference', sa.String(length=100), nullable=False),
        sa.Column('idempotency_key', sa.String(length=100), nullable=True),
        sa.Column('status', offrampstatus_enum, nullable=False, server_default=sa.text("'AWAITING_DEPOSIT'")),
        sa.Column('amount_usdc_units', sa.BigInteger(), nullable=False),
        sa.Column('received_usdc_units', sa.BigInteger(), nullable=False, server_default=sa.text('0')),
        sa.Column('quoted_rate', sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column('gross_ngn_kobo', sa.BigInteger(), nullable=True),
        sa.Column('fee_kobo', sa.BigInteger(), nullable=False, server_default=sa.text('0')),
        sa.Column('net_ngn_kobo', sa.BigInteger(), nullable=True),
        sa.Column('bank_name', sa.String(length=100), nullable=True),
        sa.Column('bank_code', sa.String(length=20), nullable=True),
        sa.Column('bank_account_number', sa.String(length=30), nullable=True),
        sa.Column('bank_account_name', sa.String(length=150), nullable=True),
        sa.Column('deposit_address', sa.String(length=120), nullable=False),
        sa.Column('deposit_address_reference', sa.String(length=150), nullable=True),
        sa.Column('deposit_currency', sa.String(length=10), nullable=False, server_default=sa.text("'USDC'")),
        sa.Column('deposit_network', sa.String(length=20), nullable=False, server_default=sa.text("'SOL'")),
        sa.Column('deposit_provider_reference', sa.String(length=150), nullable=True),
        sa.Column('deposit_tx_hash', sa.String(length=128), nullable=True),
        sa.Column('swap_reference', sa.String(length=150), nullable=True),
        sa.Column('swap_rate', sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column('swapped_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('provider_withdrawal_id', sa.String(length=150), nullable=True),
        sa.Column('provider_reference', sa.String(length=150), nullable=True),
        sa.Column('failure_reason', sa.String(length=1000), nullable=True),
        sa.Column('refund_reference', sa.String(length=150), nullable=True),
        sa.Column('refund_transaction_id', sa.String(length=150), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deposit_confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('refunded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_index('ix_offramp_withdrawals_user_id', 'offramp_withdrawals', ['user_id'])
    op.create_index('ix_offramp_withdrawals_status', 'offramp_withdrawals', ['status'])
    op.create_index('ix_offramp_withdrawals_expires_at', 'offramp_withdrawals', ['expires_at'])
    op.create_index('ix_offramp_withdrawals_reference', 'offramp_withdrawals', ['reference'], unique=True)
    op.create_index('ix_offramp_withdrawals_idempotency_key', 'offramp_withdrawals', ['idempotency_key'], unique=True)
    op.create_index('ix_offramp_withdrawals_deposit_address', 'offramp_withdrawals', ['deposit_address'], unique=True)
    op.create_index('ix_offramp_withdrawals_deposit_provider_reference', 'offramp_withdrawals', ['deposit_provider_reference'])
    op.create_index('ix_offramp_withdrawals_provider_withdrawal_id', 'offramp_withdrawals', ['provider_withdrawal_id'], unique=True)
    op.create_index('ix_offramp_withdrawals_provider_reference', 'offramp_withdrawals', ['provider_reference'], unique=True)
    op.create_index('ix_offramp_withdrawals_refund_reference', 'offramp_withdrawals', ['refund_reference'])
    op.create_index('ix_offramp_withdrawals_refund_transaction_id', 'offramp_withdrawals', ['refund_transaction_id'])


def downgrade() -> None:
    op.drop_index('ix_offramp_withdrawals_refund_transaction_id', table_name='offramp_withdrawals')
    op.drop_index('ix_offramp_withdrawals_refund_reference', table_name='offramp_withdrawals')
    op.drop_index('ix_offramp_withdrawals_provider_reference', table_name='offramp_withdrawals')
    op.drop_index('ix_offramp_withdrawals_provider_withdrawal_id', table_name='offramp_withdrawals')
    op.drop_index('ix_offramp_withdrawals_deposit_provider_reference', table_name='offramp_withdrawals')
    op.drop_index('ix_offramp_withdrawals_deposit_address', table_name='offramp_withdrawals')
    op.drop_index('ix_offramp_withdrawals_idempotency_key', table_name='offramp_withdrawals')
    op.drop_index('ix_offramp_withdrawals_reference', table_name='offramp_withdrawals')
    op.drop_index('ix_offramp_withdrawals_user_id', table_name='offramp_withdrawals')
    op.drop_index('ix_offramp_withdrawals_expires_at', table_name='offramp_withdrawals')
    op.drop_index('ix_offramp_withdrawals_status', table_name='offramp_withdrawals')
    op.drop_table('offramp_withdrawals')
    offrampstatus_enum.drop(op.get_bind(), checkfirst=True)
