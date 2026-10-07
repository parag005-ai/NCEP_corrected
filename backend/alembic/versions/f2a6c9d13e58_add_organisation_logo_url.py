"""add organisation logo_url

Revision ID: f2a6c9d13e58
Revises: e7b3d81c5f40
Create Date: 2026-08-14 19:40:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2a6c9d13e58'
down_revision: Union[str, None] = 'e7b3d81c5f40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('organisations', sa.Column('logo_url', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('organisations', 'logo_url')
