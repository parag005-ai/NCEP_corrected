"""add phone, plan, avatar_url session field

Revision ID: bb12d2d5820c
Revises: d4def27b9fa6
Create Date: 2026-07-31 22:22:59.397761
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bb12d2d5820c'
down_revision: Union[str, None] = 'd4def27b9fa6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Note: autogenerate also proposed dropping/recreating the doctors.email
    # and patients.email indexes as plain unique indexes -- that's a false
    # diff against the hand-written partial unique indexes from migration
    # d4def27b9fa6 (`ix_doctors_email_unique` / `ix_patients_email_unique`,
    # WHERE email <> ''), which intentionally allow multiple blank emails.
    # Reverting to a plain unique index would reintroduce that bug, so only
    # the genuinely new columns are included here.
    op.add_column('doctors', sa.Column('phone', sa.String(), nullable=True))
    op.add_column('organisations', sa.Column('plan', sa.String(), nullable=True))
    op.add_column('users', sa.Column('phone', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'phone')
    op.drop_column('organisations', 'plan')
    op.drop_column('doctors', 'phone')
