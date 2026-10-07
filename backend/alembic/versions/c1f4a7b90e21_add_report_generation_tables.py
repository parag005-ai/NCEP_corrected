"""add report generation tables

Creates the three Report Generation subsystem entities (Sprint 2.17):
report_generation_jobs, generated_reports and report_artifacts.

Purely additive: no existing table is altered, so the legacy `reports` table
and every existing API keep working unchanged.

Revision ID: c1f4a7b90e21
Revises: c58e14a2f301
Create Date: 2026-08-05 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1f4a7b90e21'
down_revision: Union[str, None] = 'c58e14a2f301'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'report_generation_jobs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('ecg_record_id', sa.String(), nullable=False),
        sa.Column('patient_id', sa.String(), nullable=False),
        sa.Column('organisation_id', sa.String(), nullable=False),
        sa.Column('requested_by_user_id', sa.String(), nullable=False),
        sa.Column('requested_by_doctor_id', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('current_stage', sa.String(), nullable=True),
        sa.Column('progress_percent', sa.Integer(), nullable=False),
        sa.Column('attempt_count', sa.Integer(), nullable=False),
        sa.Column('stage_history', sa.JSON(), nullable=False),
        sa.Column('failed_stage', sa.String(), nullable=True),
        sa.Column('error_code', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('pipeline_version', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['ecg_record_id'], ['ecg_records.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['organisation_id'], ['organisations.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['requested_by_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['requested_by_doctor_id'], ['doctors.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_report_generation_jobs_ecg_record_id', 'report_generation_jobs', ['ecg_record_id'])
    op.create_index('ix_report_generation_jobs_patient_id', 'report_generation_jobs', ['patient_id'])
    op.create_index('ix_report_generation_jobs_organisation_id', 'report_generation_jobs', ['organisation_id'])
    op.create_index('ix_report_generation_jobs_requested_by_user_id', 'report_generation_jobs', ['requested_by_user_id'])
    op.create_index('ix_report_generation_jobs_requested_by_doctor_id', 'report_generation_jobs', ['requested_by_doctor_id'])
    op.create_index('ix_report_generation_jobs_status', 'report_generation_jobs', ['status'])

    op.create_table(
        'generated_reports',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('job_id', sa.String(), nullable=False),
        sa.Column('ecg_record_id', sa.String(), nullable=False),
        sa.Column('patient_id', sa.String(), nullable=False),
        sa.Column('organisation_id', sa.String(), nullable=False),
        sa.Column('doctor_id', sa.String(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('summary_template_id', sa.String(), nullable=False),
        sa.Column('summary_template_version', sa.String(), nullable=False),
        sa.Column('detailed_template_id', sa.String(), nullable=False),
        sa.Column('detailed_template_version', sa.String(), nullable=False),
        sa.Column('pipeline_version', sa.String(), nullable=False),
        sa.Column('schema_version', sa.String(), nullable=False),
        sa.Column('software_version', sa.String(), nullable=False),
        sa.Column('rules_version', sa.String(), nullable=True),
        sa.Column('narrative_model_version', sa.String(), nullable=True),
        sa.Column('storage_dir', sa.String(), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['report_generation_jobs.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['ecg_record_id'], ['ecg_records.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['organisation_id'], ['organisations.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id'),
        sa.UniqueConstraint('ecg_record_id', 'version', name='uq_generated_reports_ecg_record_version'),
    )
    op.create_index('ix_generated_reports_ecg_record_id', 'generated_reports', ['ecg_record_id'])
    op.create_index('ix_generated_reports_patient_id', 'generated_reports', ['patient_id'])
    op.create_index('ix_generated_reports_organisation_id', 'generated_reports', ['organisation_id'])
    op.create_index('ix_generated_reports_doctor_id', 'generated_reports', ['doctor_id'])
    op.create_index('ix_generated_reports_status', 'generated_reports', ['status'])

    op.create_table(
        'report_artifacts',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('report_id', sa.String(), nullable=False),
        sa.Column('ecg_record_id', sa.String(), nullable=False),
        sa.Column('artifact_type', sa.String(), nullable=False),
        sa.Column('content_type', sa.String(), nullable=False),
        sa.Column('storage_location', sa.String(), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('checksum_sha256', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['report_id'], ['generated_reports.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['ecg_record_id'], ['ecg_records.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('report_id', 'storage_location', name='uq_report_artifacts_report_location'),
    )
    op.create_index('ix_report_artifacts_report_id', 'report_artifacts', ['report_id'])
    op.create_index('ix_report_artifacts_ecg_record_id', 'report_artifacts', ['ecg_record_id'])
    op.create_index('ix_report_artifacts_report_id_artifact_type', 'report_artifacts', ['report_id', 'artifact_type'])


def downgrade() -> None:
    op.drop_index('ix_report_artifacts_report_id_artifact_type', table_name='report_artifacts')
    op.drop_index('ix_report_artifacts_ecg_record_id', table_name='report_artifacts')
    op.drop_index('ix_report_artifacts_report_id', table_name='report_artifacts')
    op.drop_table('report_artifacts')

    op.drop_index('ix_generated_reports_status', table_name='generated_reports')
    op.drop_index('ix_generated_reports_doctor_id', table_name='generated_reports')
    op.drop_index('ix_generated_reports_organisation_id', table_name='generated_reports')
    op.drop_index('ix_generated_reports_patient_id', table_name='generated_reports')
    op.drop_index('ix_generated_reports_ecg_record_id', table_name='generated_reports')
    op.drop_table('generated_reports')

    op.drop_index('ix_report_generation_jobs_status', table_name='report_generation_jobs')
    op.drop_index('ix_report_generation_jobs_requested_by_doctor_id', table_name='report_generation_jobs')
    op.drop_index('ix_report_generation_jobs_requested_by_user_id', table_name='report_generation_jobs')
    op.drop_index('ix_report_generation_jobs_organisation_id', table_name='report_generation_jobs')
    op.drop_index('ix_report_generation_jobs_patient_id', table_name='report_generation_jobs')
    op.drop_index('ix_report_generation_jobs_ecg_record_id', table_name='report_generation_jobs')
    op.drop_table('report_generation_jobs')
