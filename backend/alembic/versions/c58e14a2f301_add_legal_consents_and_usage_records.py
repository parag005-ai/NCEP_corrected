"""add legal_consents and usage_records tables

Revision ID: c58e14a2f301
Revises: bb12d2d5820c
Create Date: 2026-08-09 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c58e14a2f301'
down_revision: Union[str, None] = 'bb12d2d5820c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'legal_consents',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_legal_consents_user_id'), 'legal_consents', ['user_id'], unique=False)

    op.create_table(
        'usage_records',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('credits_used', sa.Float(), nullable=False),
        sa.Column('organisation_id', sa.String(), nullable=False),
        sa.Column('organisation_name', sa.String(), nullable=False),
        sa.Column('doctor_id', sa.String(), nullable=True),
        sa.Column('doctor_name', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organisation_id'], ['organisations.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_usage_records_organisation_id'), 'usage_records', ['organisation_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_usage_records_organisation_id'), table_name='usage_records')
    op.drop_table('usage_records')
    op.drop_index(op.f('ix_legal_consents_user_id'), table_name='legal_consents')
    op.drop_table('legal_consents')
