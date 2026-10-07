"""typed timestamps, foreign keys, and email uniqueness

Revision ID: d4def27b9fa6
Revises: b371523583d0
Create Date: 2026-07-30 18:21:12.615468
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4def27b9fa6'
down_revision: Union[str, None] = 'b371523583d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── String -> real DateTime/Date columns (existing values are ISO strings,
    # except one seeded "—" placeholder in users.last_active, coerced to NULL) ──
    op.execute("ALTER TABLE organisations ALTER COLUMN created_at TYPE timestamptz USING created_at::timestamptz")

    op.execute("ALTER TABLE users ALTER COLUMN created_at TYPE timestamptz USING created_at::timestamptz")
    op.alter_column("users", "last_active", nullable=True)
    op.execute(
        "ALTER TABLE users ALTER COLUMN last_active TYPE timestamptz USING "
        "(CASE WHEN last_active IS NULL OR last_active IN ('', '—') THEN NULL "
        "ELSE last_active::timestamptz END)"
    )

    op.execute("ALTER TABLE doctors ALTER COLUMN created_at TYPE timestamptz USING created_at::timestamptz")
    op.alter_column("doctors", "last_active", nullable=True)
    op.execute(
        "ALTER TABLE doctors ALTER COLUMN last_active TYPE timestamptz USING "
        "(CASE WHEN last_active IS NULL OR last_active = '' THEN NULL ELSE last_active::timestamptz END)"
    )
    op.alter_column("doctors", "user_id", nullable=True)

    op.execute("ALTER TABLE patients ALTER COLUMN created_at TYPE timestamptz USING created_at::timestamptz")
    op.alter_column("patients", "date_of_birth", nullable=True)
    op.execute(
        "ALTER TABLE patients ALTER COLUMN date_of_birth TYPE date USING "
        "(CASE WHEN date_of_birth IS NULL OR date_of_birth = '' THEN NULL ELSE date_of_birth::date END)"
    )
    op.alter_column("patients", "assigned_doctor_id", nullable=True)

    op.execute("ALTER TABLE ecg_records ALTER COLUMN uploaded_at TYPE timestamptz USING uploaded_at::timestamptz")
    op.alter_column("ecg_records", "recording_date", nullable=True)
    op.execute(
        "ALTER TABLE ecg_records ALTER COLUMN recording_date TYPE date USING "
        "(CASE WHEN recording_date IS NULL OR recording_date = '' THEN NULL ELSE recording_date::date END)"
    )

    op.execute("ALTER TABLE reports ALTER COLUMN created_at TYPE timestamptz USING created_at::timestamptz")
    op.execute("ALTER TABLE reports ALTER COLUMN updated_at TYPE timestamptz USING updated_at::timestamptz")

    op.execute("ALTER TABLE audit_logs ALTER COLUMN timestamp TYPE timestamptz USING timestamp::timestamptz")

    # ── Foreign keys (existing data verified orphan-free before writing this migration) ──
    op.create_foreign_key("fk_users_organisation_id", "users", "organisations", ["organisation_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_doctors_user_id", "doctors", "users", ["user_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_doctors_organisation_id", "doctors", "organisations", ["organisation_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_patients_assigned_doctor_id", "patients", "doctors", ["assigned_doctor_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_patients_organisation_id", "patients", "organisations", ["organisation_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_ecg_records_patient_id", "ecg_records", "patients", ["patient_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_ecg_records_organisation_id", "ecg_records", "organisations", ["organisation_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_reports_patient_id", "reports", "patients", ["patient_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_reports_organisation_id", "reports", "organisations", ["organisation_id"], ["id"], ondelete="RESTRICT")

    # ── Email uniqueness (partial: email is optional, so blank values don't collide) ──
    op.create_index("ix_doctors_email_unique", "doctors", ["email"], unique=True, postgresql_where=sa.text("email <> ''"))
    op.create_index("ix_patients_email_unique", "patients", ["email"], unique=True, postgresql_where=sa.text("email <> ''"))


def downgrade() -> None:
    op.drop_index("ix_patients_email_unique", table_name="patients")
    op.drop_index("ix_doctors_email_unique", table_name="doctors")

    op.drop_constraint("fk_reports_organisation_id", "reports", type_="foreignkey")
    op.drop_constraint("fk_reports_patient_id", "reports", type_="foreignkey")
    op.drop_constraint("fk_ecg_records_organisation_id", "ecg_records", type_="foreignkey")
    op.drop_constraint("fk_ecg_records_patient_id", "ecg_records", type_="foreignkey")
    op.drop_constraint("fk_patients_organisation_id", "patients", type_="foreignkey")
    op.drop_constraint("fk_patients_assigned_doctor_id", "patients", type_="foreignkey")
    op.drop_constraint("fk_doctors_organisation_id", "doctors", type_="foreignkey")
    op.drop_constraint("fk_doctors_user_id", "doctors", type_="foreignkey")
    op.drop_constraint("fk_users_organisation_id", "users", type_="foreignkey")

    op.execute("ALTER TABLE audit_logs ALTER COLUMN timestamp TYPE varchar USING timestamp::varchar")

    op.execute("ALTER TABLE reports ALTER COLUMN updated_at TYPE varchar USING updated_at::varchar")
    op.execute("ALTER TABLE reports ALTER COLUMN created_at TYPE varchar USING created_at::varchar")

    # Data first (fill NULLs back to the original "" sentinel), then TYPE, then NOT NULL --
    # each step must leave the column satisfying the next step's constraint.
    op.execute("ALTER TABLE ecg_records ALTER COLUMN recording_date TYPE varchar USING COALESCE(recording_date::varchar, '')")
    op.alter_column("ecg_records", "recording_date", nullable=False, server_default="")
    op.execute("ALTER TABLE ecg_records ALTER COLUMN uploaded_at TYPE varchar USING uploaded_at::varchar")

    op.execute("UPDATE patients SET assigned_doctor_id = '' WHERE assigned_doctor_id IS NULL")
    op.alter_column("patients", "assigned_doctor_id", nullable=False, server_default="")
    op.execute("ALTER TABLE patients ALTER COLUMN date_of_birth TYPE varchar USING COALESCE(date_of_birth::varchar, '')")
    op.alter_column("patients", "date_of_birth", nullable=False, server_default="")
    op.execute("ALTER TABLE patients ALTER COLUMN created_at TYPE varchar USING created_at::varchar")

    op.execute("UPDATE doctors SET user_id = '' WHERE user_id IS NULL")
    op.alter_column("doctors", "user_id", nullable=False, server_default="")
    op.execute("ALTER TABLE doctors ALTER COLUMN last_active TYPE varchar USING COALESCE(last_active::varchar, '')")
    op.alter_column("doctors", "last_active", nullable=False, server_default="")
    op.execute("ALTER TABLE doctors ALTER COLUMN created_at TYPE varchar USING created_at::varchar")

    op.execute("ALTER TABLE users ALTER COLUMN last_active TYPE varchar USING COALESCE(last_active::varchar, '')")
    op.alter_column("users", "last_active", nullable=False, server_default="")
    op.execute("ALTER TABLE users ALTER COLUMN created_at TYPE varchar USING created_at::varchar")

    op.execute("ALTER TABLE organisations ALTER COLUMN created_at TYPE varchar USING created_at::varchar")
