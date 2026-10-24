"""add webhook events

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-10-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'e3f4a5b6c7d8'
down_revision: Union[str, Sequence[str], None] = 'd2e3f4a5b6c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    webhookstatus_enum = postgresql.ENUM(
        'RECEIVED',
        'PROCESSED',
        'FAILED',
        'REJECTED',
        'IGNORED',
        name='webhookstatus',
        create_type=False,
    )
    webhookstatus_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'webhook_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.String(length=150), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=True),
        sa.Column('reference', sa.String(length=100), nullable=True),
        sa.Column('provider_object_id', sa.String(length=100), nullable=True),
        sa.Column('signature_valid', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('status', webhookstatus_enum, nullable=False, server_default=sa.text("'RECEIVED'")),
        sa.Column('last_error', sa.String(length=1000), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider_object_id', 'event_type', name='uq_webhook_provider_object_event'),
    )
    op.create_index('ix_webhook_events_event_id', 'webhook_events', ['event_id'], unique=True)
    op.create_index('ix_webhook_events_reference', 'webhook_events', ['reference'], unique=False)
    op.create_index('ix_webhook_events_provider_object_id', 'webhook_events', ['provider_object_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_webhook_events_provider_object_id', table_name='webhook_events')
    op.drop_index('ix_webhook_events_reference', table_name='webhook_events')
    op.drop_index('ix_webhook_events_event_id', table_name='webhook_events')
    op.drop_table('webhook_events')
    postgresql.ENUM(name='webhookstatus').drop(op.get_bind(), checkfirst=True)
