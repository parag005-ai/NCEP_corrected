"""Database fixtures for the Report Generation persistence tests.

Each test gets its own in-memory SQLite database built from the shared
``Base`` metadata, with foreign key enforcement switched on so that the
lineage constraints declared by the reporting tables are actually exercised
(SQLite ignores foreign keys unless the pragma is set per connection).

No real patient data is used: the upstream rows below are synthetic.
"""

from __future__ import annotations

import io
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, get_db
from app.models import Doctor, ECGRecord, Organisation, Patient, User
from app.reporting.api import routes as report_routes
from app.reporting.api import service as report_service
from app.reporting.repositories import ECGArtifactRepository
from app.reporting.storage import ReportArtifactStore
from app.security import get_current_user
from app.reporting.repositories.ecg_artifact_repository import (
    MANIFEST_ARTIFACT,
    METADATA_CATEGORIES,
    PREPROCESSING_REPORT_ARTIFACT,
    PREPROCESSING_SIGNAL_ARTIFACT,
    WAVEFORM_ARTIFACT,
    WAVEFORM_CSV_ARTIFACT,
    WAVEFORM_DESCRIPTOR_ARTIFACT,
)
from app.storage.file.filesystem import FilesystemArtifactStore

# Registers the reporting tables on Base.metadata.
from app.reporting import models as reporting_models  # noqa: F401

#: Canonical record identifiers the ingestion pipeline would have assigned.
CANONICAL_RECORD_IDS = {"ecg-1": "rec-0001", "ecg-2": "rec-0002"}


@dataclass(frozen=True)
class UpstreamFixture:
    """Identifiers of the synthetic upstream rows a report generation references."""

    organisation_id: str
    user_id: str
    doctor_id: str
    patient_id: str
    ecg_record_id: str
    other_ecg_record_id: str
    canonical_record_id: str


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, future=True)

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


@pytest.fixture
def upstream(session: Session) -> UpstreamFixture:
    """Seeds one organisation, user, doctor, patient and two ECG recordings.

    Rows are flushed one at a time in foreign key dependency order: the
    upstream models declare no ORM relationships, so SQLAlchemy cannot infer
    an insert order for them on its own.
    """
    now = datetime.now(timezone.utc)

    rows = [
        Organisation(id="org-1", name="Test Hospital", created_at=now),
        User(id="usr-1", email="doctor@example.test", name="Test Doctor", role="doctor",
             organisation_id="org-1", created_at=now),
        Doctor(id="doc-1", user_id="usr-1", name="Test Doctor", email="doctor@example.test",
               organisation_id="org-1", created_at=now),
        Patient(id="pat-1", name="Test Patient", email="patient@example.test",
                assigned_doctor_id="doc-1", organisation_id="org-1", created_at=now),
    ]
    rows += [
        ECGRecord(id=ecg_id, patient_id="pat-1", patient_name="Test Patient", doctor_id="doc-1",
                  organisation_id="org-1", file_name=f"{ecg_id}.dat", file_type="WFDB",
                  recording_date=date(2026, 7, 1), uploaded_at=now, uploaded_by="Test Doctor",
                  storage_path=f"/ingested/{canonical_id}/waveform/waveform.csv",
                  source_format="WFDB", sampling_rate_hz=1000.0, lead_count=3,
                  available_leads=["I", "II", "V1"], xyz_available=False,
                  duration_seconds=10.0, sample_count=10_000, units="mV",
                  record_id=canonical_id, record_dir=f"/ingested/{canonical_id}",
                  validation_status="PASS", validation_issues=[],
                  quality_score=0.93, quality_flags=["baseline_drift"], beat_count=12,
                  notes="Routine follow-up recording")
        for ecg_id, canonical_id in CANONICAL_RECORD_IDS.items()
    ]
    for row in rows:
        session.add(row)
        session.flush()
    session.commit()

    return UpstreamFixture(
        organisation_id="org-1",
        user_id="usr-1",
        doctor_id="doc-1",
        patient_id="pat-1",
        ecg_record_id="ecg-1",
        other_ecg_record_id="ecg-2",
        canonical_record_id=CANONICAL_RECORD_IDS["ecg-1"],
    )


#: A minimal but valid PDF document.
MINIMAL_PDF = b"%PDF-1.4\n%stub document\n"


class FakePDFRenderer:
    """A document renderer that records its input, without launching a browser.

    Used wherever a test exercises the pipeline rather than the real rendering
    engine, which has its own dedicated test.
    """

    engine = "fake"
    engine_version = "1.0"

    def __init__(self, output: bytes = MINIMAL_PDF, error: Exception | None = None) -> None:
        self.output = output
        self.error = error
        self.seen: list[str] = []

    def render(self, html: str) -> bytes:
        self.seen.append(html)
        if self.error is not None:
            raise self.error
        return self.output


@pytest.fixture
def artifact_store(tmp_path: Path) -> FilesystemArtifactStore:
    """An isolated ECG artifact store standing in for the ingestion output root."""
    return FilesystemArtifactStore(root=tmp_path / "ecg_storage")


def build_waveform_npz(
    leads: Mapping[str, np.ndarray] | None = None,
    *,
    sample_count: int = 10_000,
    sampling_rate_hz: float = 1000.0,
) -> bytes:
    """A canonical waveform archive in the format ingestion writes.

    The default signal is a deterministic synthetic trace — a slow baseline
    plus a periodic spike — so rendered output is stable across runs. It is
    not, and does not pretend to be, a physiological ECG.
    """
    if leads is None:
        t = np.arange(sample_count, dtype=np.float64) / sampling_rate_hz
        beat_phase = (t * 1.2) % 1.0
        spike = np.where(beat_phase < 0.02, 1.2, 0.0)
        leads = {
            "I": 0.1 * np.sin(2 * np.pi * 0.3 * t) + 0.6 * spike,
            "II": 0.15 * np.sin(2 * np.pi * 0.3 * t) + spike,
            "V1": 0.05 * np.sin(2 * np.pi * 0.3 * t) - 0.4 * spike,
        }

    buffer = io.BytesIO()
    np.savez_compressed(buffer, **leads)
    return buffer.getvalue()


def write_canonical_artifacts(
    store: FilesystemArtifactStore,
    canonical_record_id: str,
    *,
    include_optional: bool = True,
    waveform_bytes: bytes | None = None,
    units: str = "mV",
) -> None:
    """Writes the artifact set the ECG ingestion pipeline produces for a recording.

    Mirrors `StorageOrchestrator` plus the preprocessing outputs written by the
    ingest endpoint.
    """
    store.write_bytes(
        canonical_record_id,
        WAVEFORM_ARTIFACT,
        waveform_bytes if waveform_bytes is not None else build_waveform_npz(),
    )
    store.write_json(
        canonical_record_id,
        WAVEFORM_DESCRIPTOR_ARTIFACT,
        {
            "sampling_rate_hz": 1000.0,
            "units": units,
            "sample_count": 10_000,
            "duration_seconds": 10.0,
            "available_leads": ["I", "II", "V1"],
            "xyz_available": False,
        },
    )
    if not include_optional:
        return

    store.write_bytes(canonical_record_id, WAVEFORM_CSV_ARTIFACT, b"sample_index,time_s,I\n0,0.000000,0.1\n")
    for category in METADATA_CATEGORIES:
        store.write_json(canonical_record_id, f"metadata/{category}.json", {"category": category})
    store.write_json(
        canonical_record_id,
        MANIFEST_ARTIFACT,
        {
            "record_id": canonical_record_id,
            "source_format": "WFDB",
            "validation_status": "PASS",
            "validation_issues": [{"code": "NONE", "severity": "INFO"}],
        },
    )
    store.write_bytes(canonical_record_id, PREPROCESSING_SIGNAL_ARTIFACT, b"npz-preprocessed-bytes")
    store.write_json(
        canonical_record_id,
        PREPROCESSING_REPORT_ARTIFACT,
        {"quality_score": 0.93, "beat_count": 12, "quality_flags": ["baseline_drift"]},
    )


# ---------------------------------------------------------------------------
# Report Generation API
# ---------------------------------------------------------------------------

API = "/api/report-generation"


@pytest.fixture
def env(tmp_path: Path, monkeypatch) -> Iterator[dict]:
    """A running API wired to isolated storage, with one ingested recording.

    Two organisations are seeded so cross-tenant access can be exercised.
    """
    engine = create_engine(
        f"sqlite:///{tmp_path / 'api.db'}", connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection, _record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, future=True)
    session = factory()
    now = datetime.now(timezone.utc)
    for row in (
        Organisation(id="org-1", name="Hospital One", created_at=now),
        Organisation(id="org-2", name="Hospital Two", created_at=now),
        User(id="usr-doc", email="doc@one.test", name="Dr One", role="doctor",
             organisation_id="org-1", created_at=now),
        User(id="usr-other", email="doc@two.test", name="Dr Two", role="doctor",
             organisation_id="org-2", created_at=now),
        User(id="usr-super", email="super@x.test", name="Super", role="superadmin",
             organisation_id="org-1", created_at=now),
        User(id="usr-pat", email="patient@one.test", name="Pat", role="patient",
             organisation_id="org-1", created_at=now),
        Doctor(id="doc-1", user_id="usr-doc", name="Dr One", email="doc@one.test",
               organisation_id="org-1", created_at=now),
        Patient(id="pat-1", name="Patient One", email="patient@one.test",
                assigned_doctor_id="doc-1", organisation_id="org-1", created_at=now),
        ECGRecord(id="ecg-1", patient_id="pat-1", patient_name="Patient One", doctor_id="doc-1",
                  organisation_id="org-1", file_name="rec.dat", file_type="WFDB",
                  recording_date=date(2026, 7, 1), uploaded_at=now, uploaded_by="Dr One",
                  source_format="WFDB", sampling_rate_hz=1000.0, lead_count=3,
                  available_leads=["I", "II", "V1"], duration_seconds=10.0, sample_count=10_000,
                  units="mV", record_id="rec-0001", quality_score=0.93, beat_count=12,
                  validation_status="PASS", validation_issues=[]),
        # A recording that was never ingested through the canonical pipeline.
        ECGRecord(id="ecg-bare", patient_id="pat-1", organisation_id="org-1", file_name="x.csv",
                  file_type="CSV", recording_date=date(2026, 7, 2), uploaded_at=now,
                  uploaded_by="Dr One"),
    ):
        session.add(row)
        session.flush()
    session.commit()

    ecg_store = FilesystemArtifactStore(root=tmp_path / "ecg_storage")
    write_canonical_artifacts(ecg_store, "rec-0001")
    report_store = ReportArtifactStore(root=tmp_path / "report_storage")

    # The pipeline the API builds, pointed at the isolated stores. Real
    # orchestrator, real stages; only the browser is substituted.
    def build_orchestrator(db, **_):
        from app.reporting.orchestrator import (
            WorkflowOrchestrator,
            build_failure_cleanup,
            build_report_pipeline,
        )

        return WorkflowOrchestrator(
            db,
            build_report_pipeline(
                db,
                ecg_artifacts=ECGArtifactRepository(store=ecg_store),
                artifact_store=report_store,
                pdf_renderer=FakePDFRenderer(),
            ),
            cleanup=build_failure_cleanup(db, artifact_store=report_store),
        )

    monkeypatch.setattr(report_service, "build_orchestrator", build_orchestrator)
    monkeypatch.setattr(report_routes, "build_orchestrator", build_orchestrator)
    # The background runner opens its own session, as it does in production.
    monkeypatch.setattr(report_service, "SessionLocal", factory)

    app = FastAPI()
    app.include_router(report_routes.router)
    app.dependency_overrides[get_db] = lambda: session

    state = {"user": "usr-doc"}
    app.dependency_overrides[get_current_user] = lambda: session.get(User, state["user"])

    with TestClient(app, raise_server_exceptions=False) as client:
        yield {
            "client": client,
            "session": session,
            "as_user": lambda uid: state.__setitem__("user", uid),
            "report_store": report_store,
            "ecg_store": ecg_store,
        }
    session.close()
    engine.dispose()


def generate(env, ecg_record_id: str = "ecg-1"):
    """Requests a report and returns the completed job payload."""
    created = env["client"].post(f"{API}/jobs", json={"ecgRecordId": ecg_record_id})
    assert created.status_code == 202, created.text
    job_id = created.json()["id"]
    return env["client"].get(f"{API}/jobs/{job_id}").json()
