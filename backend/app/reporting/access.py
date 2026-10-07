"""Tenant and ownership rules for reporting (Sprint 10.10 / 10.24).

Reporting implements no authentication of its own. It re-applies the
platform's existing ownership rules to the records it is asked to work on, so
that identity always comes from the authenticated session and never from the
request body.

One rule, used in two places: the API applies it before accepting a request,
and the Generation Context Loader applies it again before building a context.
Keeping it here means the two can never drift apart.

Ownership is separate from capability. These functions answer "may this user
see this recording at all", not "may this user generate reports" -- the second
is a role check the API layer makes with the platform's own ``require_roles``.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import ECGRecord, User
from app.reporting.exceptions import ECGRecordNotFoundError, ReportAccessDeniedError
from app.reporting.models.generated_report import GeneratedReport
from app.security import resolve_patient_id, user_can_access_patient_data

#: Roles whose access is limited to their own organisation.
ORGANISATION_SCOPED_ROLES = ("admin", "doctor")


def authorize_ecg_access(user: User, record: ECGRecord, session: Session) -> None:
    """Refuses a user who may not see this recording.

    Mirrors the rule the ECG module enforces on reads: a superadmin sees every
    tenant, organisation-scoped staff see only their own, and a patient reaches
    only their own recordings.

    Raises:
        ReportAccessDeniedError: the recording is outside the user's reach.
    """
    if user.role == "superadmin":
        return
    if user.role in ORGANISATION_SCOPED_ROLES:
        if not user_can_access_patient_data(
            user, record.patient_id, session, home_organisation_id=record.organisation_id
        ):
            raise ReportAccessDeniedError(
                f"User {user.id!r} may not access ECG record {record.id!r}: "
                "the recording belongs to another organisation"
            )
        return
    if user.role == "patient":
        if resolve_patient_id(user, session) != record.patient_id:
            raise ReportAccessDeniedError(
                f"User {user.id!r} may not access ECG record {record.id!r}: "
                "the recording belongs to another patient"
            )
        return
    raise ReportAccessDeniedError(f"Role {user.role!r} may not access ECG recordings")


def resolve_accessible_ecg(session: Session, user: User, ecg_record_id: str) -> ECGRecord:
    """The recording, if it exists and this user may see it.

    Raises:
        ECGRecordNotFoundError: no such recording.
        ReportAccessDeniedError: the recording is outside the user's reach.
    """
    record = session.get(ECGRecord, ecg_record_id)
    if record is None:
        raise ECGRecordNotFoundError(f"ECG record {ecg_record_id!r} does not exist")
    authorize_ecg_access(user, record, session)
    return record


def authorize_report_access(user: User, report: GeneratedReport, session: Session) -> None:
    """Refuses a user who may not see this generated report.

    A report is reachable exactly when its recording is: reports never widen
    access beyond the recording they were generated from.
    """
    if user.role == "superadmin":
        return
    if user.role in ORGANISATION_SCOPED_ROLES:
        if not user_can_access_patient_data(
            user, report.patient_id, session, home_organisation_id=report.organisation_id
        ):
            raise ReportAccessDeniedError(
                f"User {user.id!r} may not access report {report.id!r}: "
                "the report belongs to another organisation"
            )
        return
    if user.role == "patient":
        if resolve_patient_id(user, session) != report.patient_id:
            raise ReportAccessDeniedError(
                f"User {user.id!r} may not access report {report.id!r}: "
                "the report belongs to another patient"
            )
        return
    raise ReportAccessDeniedError(f"Role {user.role!r} may not access generated reports")
