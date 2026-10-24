"""model 1 funding lifecycle

Adds the Model 1 funding model: a task is created waiting for its funding,
funding happens on a rail (Obiex collection, FossaPay checkout or a crypto
deposit), and the escrow is locked on-chain by the relayer.

Revision ID: a1b2c3d4e5f6
Revises: e3f4a5b6c7d8
Create Date: 2026-10-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'e3f4a5b6c7d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


fundingrail_enum = postgresql.ENUM(
    'OBIEX_FIAT',
    'FOSSAPAY_CHECKOUT',
    'CRYPTO',
    'WALLET',
    name='fundingrail',
    create_type=False,
)

fundingstatus_enum = postgresql.ENUM(
    'PENDING',
    'HELD',
    'PAID',
    'FUNDED',
    'FAILED',
    'EXPIRED',
    'REVERSED',
    name='fundingstatus',
    create_type=False,
)

payertype_enum = postgresql.ENUM(
    'WALLET',
    'CUSTODIAL',
    name='payertype',
    create_type=False,
)

chaintransactionstatus_enum = postgresql.ENUM(
    'PENDING',
    'SUBMITTED',
    'CONFIRMED',
    'FINALIZED',
    'FAILED',
    name='chaintransactionstatus',
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    # The old pay-after-acceptance status becomes the Model 1 status that
    # waits for funding. Renaming keeps any existing rows.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_enum
                JOIN pg_type ON pg_type.oid = pg_enum.enumtypid
                WHERE pg_type.typname = 'jobstatus' AND enumlabel = 'AWAITING_PAYMENT'
            ) THEN
                ALTER TYPE jobstatus RENAME VALUE 'AWAITING_PAYMENT' TO 'PENDING_FUNDING';
            END IF;
        END $$;
        """
    )

    op.execute("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'PENDING_FUNDING'")
    op.execute("ALTER TYPE paymentstatus ADD VALUE IF NOT EXISTS 'HELD'")

    for enum in (
        fundingrail_enum,
        fundingstatus_enum,
        payertype_enum,
        chaintransactionstatus_enum,
    ):
        enum.create(bind, checkfirst=True)

    op.add_column(
        'jobs',
        sa.Column(
            'funding_status',
            fundingstatus_enum,
            nullable=False,
            server_default=sa.text("'PENDING'"),
        ),
    )
    op.add_column('jobs', sa.Column('payer_type', payertype_enum, nullable=True))
    op.add_column(
        'jobs', sa.Column('onchain_status', sa.String(length=40), nullable=True)
    )

    op.add_column(
        'payment_intents',
        sa.Column(
            'rail',
            fundingrail_enum,
            nullable=False,
            server_default=sa.text("'OBIEX_FIAT'"),
        ),
    )
    op.add_column(
        'payment_intents', sa.Column('usdc_amount', sa.BigInteger(), nullable=True)
    )
    op.add_column(
        'payment_intents',
        sa.Column('provider_reference', sa.String(length=150), nullable=True),
    )
    op.add_column(
        'payment_intents',
        sa.Column('provider_customer_id', sa.String(length=100), nullable=True),
    )
    op.add_column(
        'payment_intents', sa.Column('network', sa.String(length=20), nullable=True)
    )
    op.add_column(
        'payment_intents',
        sa.Column('deposit_address', sa.String(length=120), nullable=True),
    )
    op.add_column(
        'payment_intents',
        sa.Column('failure_reason', sa.String(length=1000), nullable=True),
    )
    op.create_index(
        'ix_payment_intents_provider_reference',
        'payment_intents',
        ['provider_reference'],
        unique=True,
    )

    op.add_column(
        'payment_profiles', sa.Column('bvn', sa.String(length=20), nullable=True)
    )
    op.add_column(
        'payment_profiles', sa.Column('nin', sa.String(length=20), nullable=True)
    )
    op.add_column(
        'payment_profiles', sa.Column('bank_code', sa.String(length=20), nullable=True)
    )
    op.add_column(
        'payment_profiles',
        sa.Column('bank_account_number', sa.String(length=30), nullable=True),
    )
    op.add_column(
        'payment_profiles',
        sa.Column('bank_account_name', sa.String(length=150), nullable=True),
    )

    op.add_column(
        'fossapay_customers',
        sa.Column('crypto_wallet_id', sa.String(length=100), nullable=True),
    )
    op.add_column(
        'fossapay_customers',
        sa.Column('crypto_wallet_address', sa.String(length=120), nullable=True),
    )
    op.add_column(
        'fossapay_customers',
        sa.Column('crypto_network', sa.String(length=20), nullable=True),
    )
    op.create_index(
        'ix_fossapay_customers_crypto_wallet_id',
        'fossapay_customers',
        ['crypto_wallet_id'],
        unique=True,
    )

    op.create_table(
        'chain_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=True),
        sa.Column('kind', sa.String(length=40), nullable=False),
        sa.Column('idempotency_key', sa.String(length=120), nullable=False),
        sa.Column('signature', sa.String(length=128), nullable=True),
        sa.Column(
            'status',
            chaintransactionstatus_enum,
            nullable=False,
            server_default=sa.text("'PENDING'"),
        ),
        sa.Column('slot', sa.BigInteger(), nullable=True),
        sa.Column('error', sa.String(length=1000), nullable=True),
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
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_chain_transactions_job_id', 'chain_transactions', ['job_id'], unique=False
    )
    op.create_index(
        'ix_chain_transactions_idempotency_key',
        'chain_transactions',
        ['idempotency_key'],
        unique=True,
    )
    op.create_index(
        'ix_chain_transactions_signature',
        'chain_transactions',
        ['signature'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('ix_chain_transactions_signature', table_name='chain_transactions')
    op.drop_index(
        'ix_chain_transactions_idempotency_key', table_name='chain_transactions'
    )
    op.drop_index('ix_chain_transactions_job_id', table_name='chain_transactions')
    op.drop_table('chain_transactions')

    op.drop_index(
        'ix_fossapay_customers_crypto_wallet_id', table_name='fossapay_customers'
    )
    op.drop_column('fossapay_customers', 'crypto_network')
    op.drop_column('fossapay_customers', 'crypto_wallet_address')
    op.drop_column('fossapay_customers', 'crypto_wallet_id')

    op.drop_column('payment_profiles', 'bank_account_name')
    op.drop_column('payment_profiles', 'bank_account_number')
    op.drop_column('payment_profiles', 'bank_code')
    op.drop_column('payment_profiles', 'nin')
    op.drop_column('payment_profiles', 'bvn')

    op.drop_index(
        'ix_payment_intents_provider_reference', table_name='payment_intents'
    )
    op.drop_column('payment_intents', 'failure_reason')
    op.drop_column('payment_intents', 'deposit_address')
    op.drop_column('payment_intents', 'network')
    op.drop_column('payment_intents', 'provider_customer_id')
    op.drop_column('payment_intents', 'provider_reference')
    op.drop_column('payment_intents', 'usdc_amount')
    op.drop_column('payment_intents', 'rail')

    op.drop_column('jobs', 'onchain_status')
    op.drop_column('jobs', 'payer_type')
    op.drop_column('jobs', 'funding_status')

    bind = op.get_bind()
    for enum in (
        chaintransactionstatus_enum,
        payertype_enum,
        fundingstatus_enum,
        fundingrail_enum,
    ):
        postgresql.ENUM(name=enum.name).drop(bind, checkfirst=True)

    # PostgreSQL cannot remove single enum values: 'PENDING_FUNDING' on
    # jobstatus and 'HELD' on paymentstatus remain after a downgrade.
