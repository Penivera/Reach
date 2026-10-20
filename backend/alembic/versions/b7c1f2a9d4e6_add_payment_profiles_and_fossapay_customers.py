"""add payment profiles and fossapay customers

Revision ID: b7c1f2a9d4e6
Revises: ddb682180e47
Create Date: 2026-10-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b7c1f2a9d4e6'
down_revision: Union[str, Sequence[str], None] = 'ddb682180e47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    provisioningstatus_enum = postgresql.ENUM(
        'PENDING',
        'PROVISIONED',
        'FAILED',
        name='provisioningstatus',
        create_type=False,
    )
    provisioningstatus_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'payment_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('middle_name', sa.String(length=100), nullable=True),
        sa.Column('date_of_birth', sa.Date(), nullable=False),
        sa.Column('address', sa.String(length=255), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('country', sa.String(length=100), nullable=False, server_default='Nigeria'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_payment_profiles_user_id', 'payment_profiles', ['user_id'], unique=True)

    op.create_table(
        'fossapay_customers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('provider_customer_id', sa.String(length=100), nullable=True),
        sa.Column('wallet_id', sa.String(length=100), nullable=True),
        sa.Column('account_number', sa.String(length=30), nullable=True),
        sa.Column('account_name', sa.String(length=150), nullable=True),
        sa.Column('bank_name', sa.String(length=100), nullable=True),
        sa.Column('status', provisioningstatus_enum, nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column('last_error', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_fossapay_customers_user_id', 'fossapay_customers', ['user_id'], unique=True)
    op.create_index('ix_fossapay_customers_provider_customer_id', 'fossapay_customers', ['provider_customer_id'], unique=True)
    op.create_index('ix_fossapay_customers_wallet_id', 'fossapay_customers', ['wallet_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_fossapay_customers_wallet_id', table_name='fossapay_customers')
    op.drop_index('ix_fossapay_customers_provider_customer_id', table_name='fossapay_customers')
    op.drop_index('ix_fossapay_customers_user_id', table_name='fossapay_customers')
    op.drop_table('fossapay_customers')

    op.drop_index('ix_payment_profiles_user_id', table_name='payment_profiles')
    op.drop_table('payment_profiles')

    postgresql.ENUM(name='provisioningstatus').drop(op.get_bind(), checkfirst=True)
