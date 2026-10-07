"""add async ingest jobs and canonical artifact manifest

Revision ID: 9f42a81ce310
Revises: a7d3e91c4f22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "9f42a81ce310"
down_revision: Union[str, None] = "a7d3e91c4f22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ecg_records", sa.Column("artifact_manifest", sa.JSON(), nullable=True))
    op.create_table(
        "ecg_ingest_jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("request_fingerprint", sa.String(), nullable=False),
        sa.Column("patient_id", sa.String(), nullable=False),
        sa.Column("doctor_id", sa.String(), nullable=False),
        sa.Column("organisation_id", sa.String(), nullable=False),
        sa.Column("requested_by_user_id", sa.String(), nullable=False),
        sa.Column("uploaded_by", sa.String(), nullable=False),
        sa.Column("upload_id", sa.String(), nullable=False),
        sa.Column("file_names", sa.JSON(), nullable=False),
        sa.Column("request_metadata", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("current_stage", sa.String(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("ecg_record_id", sa.String(), nullable=True),
        sa.Column("error_code", sa.String(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["ecg_record_id"], ["ecg_records.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_ecg_ingest_jobs_idempotency_key"),
    )
    for column in ("idempotency_key", "request_fingerprint", "patient_id", "organisation_id", "requested_by_user_id", "status", "ecg_record_id"):
        op.create_index(f"ix_ecg_ingest_jobs_{column}", "ecg_ingest_jobs", [column])


def downgrade() -> None:
    op.drop_table("ecg_ingest_jobs")
    op.drop_column("ecg_records", "artifact_manifest")
