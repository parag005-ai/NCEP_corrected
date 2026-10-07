"""add patient_organisation_links

Revision ID: a7d3e91c4f22
Revises: f2a6c9d13e58
Create Date: 2026-08-18 22:50:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7d3e91c4f22'
down_revision: Union[str, None] = 'f2a6c9d13e58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'patient_organisation_links',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('patient_id', sa.String(), sa.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('organisation_id', sa.String(), sa.ForeignKey('organisations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('linked_by_user_id', sa.String(), nullable=False, server_default=''),
        sa.Column('linked_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('patient_id', 'organisation_id', name='uq_patient_org_link'),
    )
    op.create_index(
        'ix_patient_organisation_links_patient_id', 'patient_organisation_links', ['patient_id']
    )
    op.create_index(
        'ix_patient_organisation_links_organisation_id', 'patient_organisation_links', ['organisation_id']
    )


def downgrade() -> None:
    op.drop_index('ix_patient_organisation_links_organisation_id', table_name='patient_organisation_links')
    op.drop_index('ix_patient_organisation_links_patient_id', table_name='patient_organisation_links')
    op.drop_table('patient_organisation_links')
