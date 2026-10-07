"""add artifact metadata to report artifacts

Sprint 4.12 requires a generated visualization to record the facts specific to
it -- visualization type, lead name and time window -- alongside its location
and checksum. Those facts do not apply to every artifact type, so they are
stored as a nullable JSON document rather than as columns.

Additive and nullable: existing report_artifacts rows keep working unchanged.

Revision ID: e7b3d81c5f40
Revises: c1f4a7b90e21
Create Date: 2026-08-06 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7b3d81c5f40'
down_revision: Union[str, None] = 'c1f4a7b90e21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('report_artifacts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('artifact_metadata', sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('report_artifacts', schema=None) as batch_op:
        batch_op.drop_column('artifact_metadata')
