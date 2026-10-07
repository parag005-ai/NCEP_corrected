"""Seed the database with the same demo data the frontend previously kept in localStorage.

Run:  python -m app.seed
Every account logs in with the DEMO_PASSWORD (default: "password").
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import (
    AuditLog,
    ClinicalReport,
    Doctor,
    ECGRecord,
    Organisation,
    Patient,
    User,
)
from app.security import hash_password


def _coerce_dates(
    records: list[dict], date_fields: tuple[str, ...] = (), datetime_fields: tuple[str, ...] = ()
) -> list[dict]:
    """Seed data is written as readable ISO strings; convert to real date/datetime
    objects here (once) to match the typed DateTime/Date columns."""
    out = []
    for record in records:
        record = dict(record)
        for field in date_fields:
            if record.get(field):
                record[field] = date.fromisoformat(record[field])
        for field in datetime_fields:
            value = record.get(field)
            record[field] = (
                datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
                if value and value != "—"
                else None
            )
        out.append(record)
    return out

ORGANISATIONS = [
    dict(id="org-001", name="City General Hospital", address="12 MG Road, Mumbai 400001", contact="+91 22 2345 6789", admin_id="user-admin-001", status="Active", created_at="2025-01-15", total_users=48, total_patients=312),
    dict(id="org-002", name="National Cardiology Institute", address="45 Nehru Place, New Delhi 110019", contact="+91 11 4567 8901", admin_id="user-admin-002", status="Active", created_at="2025-03-20", total_users=62, total_patients=540),
    dict(id="org-003", name="Apollo Neuro Sciences", address="78 Anna Nagar, Chennai 600040", contact="+91 44 5678 9012", admin_id="user-admin-003", status="Active", created_at="2025-06-10", total_users=35, total_patients=198),
]

USERS = [
    dict(id="user-patient-001", email="patient@ncep.demo", name="Anaya Rao", role="patient", organisation_id="org-001", status="Active", last_active="2026-07-12", created_at="2025-08-10"),
    dict(id="user-patient-002", email="rohan.mehta@example.com", name="Rohan Mehta", role="patient", organisation_id="org-001", status="Active", last_active="2026-07-11", created_at="2025-09-05"),
    dict(id="user-patient-003", email="sara.thomas@example.com", name="Sara Thomas", role="patient", organisation_id="org-001", status="Active", last_active="2026-07-10", created_at="2025-10-12"),
    dict(id="user-patient-004", email="vikram.nair@example.com", name="Vikram Nair", role="patient", organisation_id="org-002", status="Active", last_active="2026-07-08", created_at="2025-11-01"),
    dict(id="user-doctor-001", email="doctor@ncep.demo", name="Dr. Meera Shah", role="doctor", organisation_id="org-001", status="Active", last_active="2026-07-12", created_at="2025-01-20"),
    dict(id="user-doctor-002", email="karan.iyer@ncep.demo", name="Dr. Karan Iyer", role="doctor", organisation_id="org-001", status="Active", last_active="2026-07-11", created_at="2025-02-15"),
    dict(id="user-doctor-003", email="priya.nair@ncep.demo", name="Dr. Priya Nair", role="doctor", organisation_id="org-002", status="Active", last_active="2026-07-10", created_at="2025-04-22"),
    dict(id="user-tech-001", email="rahul.tech@ncep.demo", name="Rahul Kumar", role="doctor", organisation_id="org-001", status="Active", last_active="2026-07-09", created_at="2025-05-18"),
    dict(id="user-admin-001", email="admin@ncep.demo", name="Sanjay Patel", role="admin", organisation_id="org-001", status="Active", last_active="2026-07-12", created_at="2025-01-15"),
    dict(id="user-admin-002", email="neha.sharma@ncep.demo", name="Neha Sharma", role="admin", organisation_id="org-002", status="Active", last_active="2026-07-11", created_at="2025-03-20"),
    dict(id="user-admin-003", email="amit.gupta@ncep.demo", name="Amit Gupta", role="admin", organisation_id="org-003", status="Invited", last_active="—", created_at="2026-06-25"),
    dict(id="user-superadmin-001", email="superadmin@ncep.demo", name="Platform Admin", role="superadmin", organisation_id="org-001", status="Active", last_active="2026-07-12", created_at="2024-12-01"),
]

DOCTORS = [
    dict(id="doc-001", user_id="user-doctor-001", name="Dr. Meera Shah", email="doctor@ncep.demo", staff_id="STF-1001", role="Doctor", speciality="Cardiac Electrophysiology", organisation_id="org-001", status="Active", assigned_patient_count=3, last_active="2026-07-12", created_at="2025-01-20"),
    dict(id="doc-002", user_id="user-doctor-002", name="Dr. Karan Iyer", email="karan.iyer@ncep.demo", staff_id="STF-1002", role="Doctor", speciality="Neurology", organisation_id="org-001", status="Active", assigned_patient_count=2, last_active="2026-07-11", created_at="2025-02-15"),
    dict(id="doc-003", user_id="user-doctor-003", name="Dr. Priya Nair", email="priya.nair@ncep.demo", staff_id="STF-2001", role="Doctor", speciality="Cardiology", organisation_id="org-002", status="Active", assigned_patient_count=4, last_active="2026-07-10", created_at="2025-04-22"),
    dict(id="doc-004", user_id="user-tech-001", name="Rahul Kumar", email="rahul.tech@ncep.demo", staff_id="STF-1003", role="Technician", speciality="ECG Technology", organisation_id="org-001", status="Active", assigned_patient_count=0, last_active="2026-07-09", created_at="2025-05-18"),
]

PATIENTS = [
    dict(id="pat-001", name="Anaya Rao", date_of_birth="1984-03-15", age=42, gender="Female", email="patient@ncep.demo", phone="+91 98765 43210", address="23 Koramangala, Bangalore 560034", assigned_doctor_id="doc-001", assigned_doctor="Dr. Meera Shah", organisation_id="org-001", status="Review Required", medical_notes="Palpitations and intermittent dizziness. ECG uploaded for clinician review.", created_at="2025-08-10"),
    dict(id="pat-002", name="Rohan Mehta", date_of_birth="1968-07-22", age=58, gender="Male", email="rohan.mehta@example.com", phone="+91 99887 77665", address="56 Bandra West, Mumbai 400050", assigned_doctor_id="doc-002", assigned_doctor="Dr. Karan Iyer", organisation_id="org-001", status="Stable", medical_notes="Follow-up review after routine electrophysiology screening.", created_at="2025-09-05"),
    dict(id="pat-003", name="Sara Thomas", date_of_birth="1991-11-08", age=35, gender="Female", email="sara.thomas@example.com", phone="+91 90123 45678", address="12 MG Road, Pune 411001", assigned_doctor_id="doc-001", assigned_doctor="Dr. Meera Shah", organisation_id="org-001", status="Pending Upload", medical_notes="Patient registration completed. ECG upload pending.", created_at="2025-10-12"),
    dict(id="pat-004", name="Vikram Nair", date_of_birth="1975-05-30", age=51, gender="Male", email="vikram.nair@example.com", phone="+91 91234 56789", address="89 Connaught Place, New Delhi 110001", assigned_doctor_id="doc-003", assigned_doctor="Dr. Priya Nair", organisation_id="org-002", status="Stable", medical_notes="Annual cardiac screening. No acute concerns.", created_at="2025-11-01"),
    dict(id="pat-005", name="Lakshmi Devi", date_of_birth="1960-12-02", age=65, gender="Female", email="lakshmi.devi@example.com", phone="+91 98765 12345", address="34 T Nagar, Chennai 600017", assigned_doctor_id="doc-003", assigned_doctor="Dr. Priya Nair", organisation_id="org-002", status="Critical", medical_notes="Chronic atrial fibrillation. Urgent electrophysiology review needed.", created_at="2025-12-20"),
]

ECG_RECORDS = [
    dict(id="ecg-001", patient_id="pat-001", patient_name="Anaya Rao", doctor_id="doc-001", organisation_id="org-001", file_name="resting-ecg-lead-II.pdf", file_type="PDF", recording_date="2026-07-09", device_source="CardioNexus ECG 3000", notes="Resting 12-lead ECG", status="Reviewed", uploaded_at="2026-07-09T10:30:00", uploaded_by="Dr. Meera Shah"),
    dict(id="ecg-002", patient_id="pat-001", patient_name="Anaya Rao", doctor_id="doc-001", organisation_id="org-001", file_name="stress-ecg-recording.csv", file_type="CSV", recording_date="2026-07-08", device_source="CardioNexus ECG 3000", notes="Stress test during treadmill exercise", status="Ready", uploaded_at="2026-07-08T14:15:00", uploaded_by="Rahul Kumar"),
    dict(id="ecg-003", patient_id="pat-002", patient_name="Rohan Mehta", doctor_id="doc-002", organisation_id="org-001", file_name="holter-24hr-export.xml", file_type="XML", recording_date="2026-07-07", device_source="Holter Monitor H200", notes="24-hour Holter monitoring", status="Reviewed", uploaded_at="2026-07-07T09:00:00", uploaded_by="Dr. Karan Iyer"),
    dict(id="ecg-004", patient_id="pat-003", patient_name="Sara Thomas", doctor_id="doc-001", organisation_id="org-001", file_name="initial-screening.edf", file_type="EDF", recording_date="2026-07-06", device_source="CardioNexus ECG 3000", notes="Initial screening ECG", status="Uploaded", uploaded_at="2026-07-06T11:45:00", uploaded_by="Rahul Kumar"),
    dict(id="ecg-005", patient_id="pat-004", patient_name="Vikram Nair", doctor_id="doc-003", organisation_id="org-002", file_name="annual-ecg-checkup.pdf", file_type="PDF", recording_date="2026-07-05", device_source="CardioScan Pro", notes="Annual cardiac screening", status="Reviewed", uploaded_at="2026-07-05T16:20:00", uploaded_by="Dr. Priya Nair"),
]

REPORTS = [
    dict(id="rpt-001", title="Cardiac Rhythm Analysis – Anaya Rao", patient_id="pat-001", patient_name="Anaya Rao", doctor_id="doc-001", doctor_name="Dr. Meera Shah", organisation_id="org-001", ecg_record_id="ecg-001", clinical_observations="Irregular R-R intervals noted. No ST-segment elevation.", findings="Intermittent supraventricular ectopy observed in leads II and V1.", interpretation="Findings consistent with paroxysmal supraventricular tachycardia (PSVT). Benign pattern with no evidence of ischaemia.", recommendations="Recommend 24-hour Holter monitoring for further evaluation. Consider beta-blocker trial if symptoms persist.", status="In Review", reviewed_by="Dr. Meera Shah", created_at="2026-07-09", updated_at="2026-07-10", shared_with_patient=False),
    dict(id="rpt-002", title="Electrophysiology Screening – Rohan Mehta", patient_id="pat-002", patient_name="Rohan Mehta", doctor_id="doc-002", doctor_name="Dr. Karan Iyer", organisation_id="org-001", ecg_record_id="ecg-003", clinical_observations="Normal sinus rhythm. Heart rate 72 bpm. Normal axis.", findings="No significant arrhythmia detected. QT interval within normal limits.", interpretation="Normal electrophysiology screening. No cardiac conduction abnormalities.", recommendations="Routine follow-up in 12 months. Maintain current medication regimen.", status="Approved", reviewed_by="Dr. Karan Iyer", created_at="2026-07-08", updated_at="2026-07-09", shared_with_patient=True),
    dict(id="rpt-003", title="Initial ECG Assessment – Sara Thomas", patient_id="pat-003", patient_name="Sara Thomas", doctor_id="doc-001", doctor_name="Dr. Meera Shah", organisation_id="org-001", ecg_record_id="ecg-004", clinical_observations="", findings="", interpretation="", recommendations="", status="Draft", reviewed_by="Pending", created_at="2026-07-07", updated_at="2026-07-07", shared_with_patient=False),
    dict(id="rpt-004", title="Annual Cardiac Review – Vikram Nair", patient_id="pat-004", patient_name="Vikram Nair", doctor_id="doc-003", doctor_name="Dr. Priya Nair", organisation_id="org-002", ecg_record_id="ecg-005", clinical_observations="Resting ECG shows normal sinus rhythm. Blood pressure 128/82 mmHg.", findings="No significant ST-T wave changes. Normal QRS morphology.", interpretation="Normal cardiac function. No evidence of ischaemia or arrhythmia.", recommendations="Continue annual screening. Lifestyle modifications for borderline hypertension.", status="Shared", reviewed_by="Dr. Priya Nair", created_at="2026-07-05", updated_at="2026-07-06", shared_with_patient=True),
]

AUDIT_LOGS = [
    dict(id="log-001", event="User login", event_type="login", actor_id="user-superadmin-001", actor_name="Platform Admin", actor_role="superadmin", organisation_id="org-001", organisation_name="City General Hospital", resource="Auth System", result="Success", ip_address="192.168.1.100", timestamp="2026-07-12T10:42:00", details="Successful platform admin login"),
    dict(id="log-002", event="Report shared with patient", event_type="report_shared", actor_id="user-doctor-001", actor_name="Dr. Meera Shah", actor_role="doctor", organisation_id="org-001", organisation_name="City General Hospital", resource="Report RPT-002", result="Success", ip_address="192.168.1.45", timestamp="2026-07-12T09:18:00", details="Report for Rohan Mehta shared with patient portal"),
    dict(id="log-003", event="Organisation settings updated", event_type="settings_changed", actor_id="user-admin-001", actor_name="Sanjay Patel", actor_role="admin", organisation_id="org-001", organisation_name="City General Hospital", resource="Org Settings", result="Success", ip_address="192.168.1.50", timestamp="2026-07-11T17:03:00", details="Updated notification preferences"),
    dict(id="log-004", event="New patient registered", event_type="patient_created", actor_id="user-doctor-002", actor_name="Dr. Karan Iyer", actor_role="doctor", organisation_id="org-001", organisation_name="City General Hospital", resource="Patient pat-003", result="Success", ip_address="192.168.1.45", timestamp="2026-07-11T14:22:00", details="Sara Thomas registered as new patient"),
    dict(id="log-005", event="ECG file uploaded", event_type="ecg_uploaded", actor_id="user-tech-001", actor_name="Rahul Kumar", actor_role="doctor", organisation_id="org-001", organisation_name="City General Hospital", resource="ECG ecg-004", result="Success", ip_address="192.168.1.60", timestamp="2026-07-11T11:45:00", details="Initial screening ECG uploaded for Sara Thomas"),
    dict(id="log-006", event="Admin role updated", event_type="user_updated", actor_id="user-superadmin-001", actor_name="Platform Admin", actor_role="superadmin", organisation_id="org-002", organisation_name="National Cardiology Institute", resource="User user-admin-002", result="Success", ip_address="192.168.1.100", timestamp="2026-07-10T16:30:00", details="Neha Sharma promoted to Organisation Admin"),
    dict(id="log-007", event="Report approved", event_type="report_approved", actor_id="user-doctor-002", actor_name="Dr. Karan Iyer", actor_role="doctor", organisation_id="org-001", organisation_name="City General Hospital", resource="Report RPT-002", result="Success", ip_address="192.168.1.45", timestamp="2026-07-10T10:15:00", details="Electrophysiology screening report approved"),
    dict(id="log-008", event="Unauthorised access attempt", event_type="access_denied", actor_id="user-patient-002", actor_name="Rohan Mehta", actor_role="patient", organisation_id="org-001", organisation_name="City General Hospital", resource="Admin Dashboard", result="Failure", ip_address="192.168.1.70", timestamp="2026-07-10T08:05:00", details="Patient attempted to access admin dashboard"),
    dict(id="log-009", event="New organisation created", event_type="org_created", actor_id="user-superadmin-001", actor_name="Platform Admin", actor_role="superadmin", organisation_id="org-003", organisation_name="Apollo Neuro Sciences", resource="Organisation org-003", result="Success", ip_address="192.168.1.100", timestamp="2026-07-09T14:00:00", details="Apollo Neuro Sciences onboarded"),
    dict(id="log-010", event="User deactivated", event_type="user_deactivated", actor_id="user-admin-001", actor_name="Sanjay Patel", actor_role="admin", organisation_id="org-001", organisation_name="City General Hospital", resource="User user-tech-002", result="Success", ip_address="192.168.1.50", timestamp="2026-07-09T09:30:00", details="Former technician account deactivated"),
    dict(id="log-011", event="Doctor account created", event_type="user_created", actor_id="user-admin-002", actor_name="Neha Sharma", actor_role="admin", organisation_id="org-002", organisation_name="National Cardiology Institute", resource="User user-doctor-003", result="Success", ip_address="10.0.0.15", timestamp="2026-07-08T11:20:00", details="Dr. Priya Nair onboarded"),
    dict(id="log-012", event="System settings changed", event_type="settings_changed", actor_id="user-superadmin-001", actor_name="Platform Admin", actor_role="superadmin", organisation_id="org-001", organisation_name="City General Hospital", resource="System Settings", result="Success", ip_address="192.168.1.100", timestamp="2026-07-07T15:45:00", details="Updated session timeout to 30 minutes"),
]


def seed_db(db: Session, *, force: bool = False) -> bool:
    """Inserts the fixed demo dataset using the given session.

    Callers that already hold a Session (e.g. a request-scoped `db` from
    Depends(get_db)) must pass it in rather than going through `seed()`,
    which opens its own session against SessionLocal -- using SessionLocal
    from inside a request would silently write to a different database than
    the one that request is actually connected to under test overrides.
    Returns False (no-op) if the database already has users and `force` is
    not set.
    """
    if not force and db.scalar(select(User).limit(1)) is not None:
        return False

    pw = hash_password(settings.demo_password)

    orgs = _coerce_dates(ORGANISATIONS, datetime_fields=("created_at",))
    users = _coerce_dates(USERS, datetime_fields=("created_at", "last_active"))
    doctors = _coerce_dates(DOCTORS, datetime_fields=("created_at", "last_active"))
    patients = _coerce_dates(PATIENTS, date_fields=("date_of_birth",), datetime_fields=("created_at",))
    ecgs = _coerce_dates(ECG_RECORDS, date_fields=("recording_date",), datetime_fields=("uploaded_at",))
    reports = _coerce_dates(REPORTS, datetime_fields=("created_at", "updated_at"))
    logs = _coerce_dates(AUDIT_LOGS, datetime_fields=("timestamp",))

    # Flushed tier-by-tier along the FK dependency chain (Organisation -> User
    # -> Doctor -> Patient -> {ECGRecord, ClinicalReport}) rather than one
    # bulk add_all()+commit(): SQLAlchemy's flush doesn't guarantee it emits
    # INSERTs in add() call order across unrelated mapped classes (there are
    # no relationship()s wiring these models together, only FK columns), so
    # without intermediate flushes a real FK-enforcing database (Postgres)
    # can try to insert e.g. a report before its patient exists. SQLite
    # doesn't enforce FKs by default, which is why this went unnoticed there.
    db.add_all(Organisation(**o) for o in orgs)
    db.flush()
    db.add_all(User(password_hash=pw, **u) for u in users)
    db.flush()
    db.add_all(Doctor(**d) for d in doctors)
    db.flush()
    db.add_all(Patient(**p) for p in patients)
    db.flush()
    db.add_all(ECGRecord(**e) for e in ecgs)
    db.add_all(ClinicalReport(**r) for r in reports)
    db.add_all(AuditLog(**a) for a in logs)
    db.commit()
    return True


def seed() -> None:
    db = SessionLocal()
    try:
        if not seed_db(db):
            print("Database already seeded — skipping. (Delete rows or the DB to re-seed.)")
            return
        print(
            f"Seeded {len(ORGANISATIONS)} orgs, {len(USERS)} users, {len(DOCTORS)} doctors, "
            f"{len(PATIENTS)} patients, {len(ECG_RECORDS)} ECGs, {len(REPORTS)} reports, "
            f"{len(AUDIT_LOGS)} audit logs."
        )
        print(f'All accounts log in with password: "{settings.demo_password}"')
    finally:
        db.close()


if __name__ == "__main__":
    seed()
