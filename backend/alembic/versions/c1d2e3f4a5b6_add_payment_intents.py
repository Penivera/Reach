"""add payment intents

Revision ID: c1d2e3f4a5b6
Revises: b7c1f2a9d4e6
Create Date: 2026-10-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = 'b7c1f2a9d4e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'AWAITING_PAYMENT'")

    paymentstatus_enum = postgresql.ENUM(
        'PENDING',
        'PAID',
        'FAILED',
        'EXPIRED',
        'REVERSED',
        name='paymentstatus',
        create_type=False,
    )
    paymentstatus_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'payment_intents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('reference', sa.String(length=100), nullable=False),
        sa.Column('amount_kobo', sa.BigInteger(), nullable=False),
        sa.Column('amount_payable_kobo', sa.BigInteger(), nullable=False),
        sa.Column('status', paymentstatus_enum, nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column('provider_checkout_id', sa.String(length=100), nullable=True),
        sa.Column('bank_name', sa.String(length=100), nullable=True),
        sa.Column('account_name', sa.String(length=150), nullable=True),
        sa.Column('account_number', sa.String(length=30), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_payment_intents_job_id', 'payment_intents', ['job_id'], unique=False)
    op.create_index('ix_payment_intents_reference', 'payment_intents', ['reference'], unique=True)
    op.create_index('ix_payment_intents_provider_checkout_id', 'payment_intents', ['provider_checkout_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_payment_intents_provider_checkout_id', table_name='payment_intents')
    op.drop_index('ix_payment_intents_reference', table_name='payment_intents')
    op.drop_index('ix_payment_intents_job_id', table_name='payment_intents')
    op.drop_table('payment_intents')

    postgresql.ENUM(name='paymentstatus').drop(op.get_bind(), checkfirst=True)
    # PostgreSQL cannot easily remove a single enum value; AWAITING_PAYMENT
    # remains on jobstatus after a downgrade.
