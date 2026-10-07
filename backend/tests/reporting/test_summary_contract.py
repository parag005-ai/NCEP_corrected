"""The Summary Report delivery contract, end to end.

The Summary is composed by the Summary builder during a generation, persisted
as a structured-data artifact of that report version, and served from that
artifact -- never recomposed on read.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.reporting.builders import SummaryReportBuilder
from app.reporting.builders.serialization import SUMMARY_CONTRACT_VERSION, document_to_dict
from app.reporting.constants import ArtifactStatus, ArtifactType
from app.reporting.orchestrator.rendering_stage import SUMMARY_JSON_LOCATION
from app.reporting.repositories import GeneratedReportRepository, ReportArtifactRepository

from tests.reporting.conftest import API, generate


def _pending_from(report, session):
    """The stored ECG figure of a report, as the builder received it."""
    from app.reporting.models.pending_artifact import PendingReportArtifact

    artifact = ReportArtifactRepository(session).list_for_report(
        report.id, artifact_type=ArtifactType.RAW_ECG_SVG
    )[0]
    return PendingReportArtifact(
        artifact_type=ArtifactType.RAW_ECG_SVG,
        content_type=artifact.content_type,
        storage_location=artifact.storage_location,
        absolute_path=str(Path(report.storage_dir) / artifact.storage_location),
        file_size_bytes=artifact.file_size_bytes,
        checksum_sha256=artifact.checksum_sha256,
        generated_at=artifact.generated_at,
        artifact_metadata=dict(artifact.artifact_metadata or {}),
    )


def summary_artifact(session, report):
    artifacts = ReportArtifactRepository(session).list_for_report(
        report.id, artifact_type=ArtifactType.SUMMARY_JSON
    )
    assert len(artifacts) == 1
    return artifacts[0]


# ---------------------------------------------------------------------------
# Generation and registration
# ---------------------------------------------------------------------------


def test_a_generation_produces_and_registers_a_summary_artifact(env):
    job = generate(env)
    report = GeneratedReportRepository(env["session"]).get(job["reportId"])

    artifact = summary_artifact(env["session"], report)

    assert artifact.content_type == "application/json; charset=utf-8"
    assert artifact.storage_location == SUMMARY_JSON_LOCATION
    assert artifact.checksum_sha256
    assert artifact.file_size_bytes > 0
    assert artifact.artifact_metadata["report_type"] == "SUMMARY"
    assert artifact.artifact_metadata["contract_version"] == SUMMARY_CONTRACT_VERSION


def test_the_summary_artifact_is_verified_and_released_like_any_other(env):
    """It joins the existing lifecycle: verified, then made available."""
    job = generate(env)
    report = GeneratedReportRepository(env["session"]).get(job["reportId"])

    artifact = summary_artifact(env["session"], report)

    assert artifact.status == ArtifactStatus.AVAILABLE.value
    stored = Path(report.storage_dir) / artifact.storage_location
    assert stored.stat().st_size == artifact.file_size_bytes


def test_the_summary_appears_among_the_reports_artifacts(env):
    job = generate(env)

    report = env["client"].get(job["reportUrl"]).json()

    assert {a["artifactType"] for a in report["artifacts"]} == {
        ArtifactType.SUMMARY_JSON.value,
        ArtifactType.RAW_ECG_SVG.value,
        ArtifactType.DETAILED_HTML.value,
        ArtifactType.DETAILED_PDF.value,
    }
    assert report["summaryUrl"] == f"{API}/reports/{report['id']}/summary"


# ---------------------------------------------------------------------------
# The served contract
# ---------------------------------------------------------------------------


def test_the_summary_survives_retrieval_with_its_structure_intact(env):
    job = generate(env)

    summary = env["client"].get(f"{API}/reports/{job['reportId']}/summary").json()

    assert summary["contractVersion"] == SUMMARY_CONTRACT_VERSION
    assert summary["reportId"] == job["reportId"]
    assert summary["reportType"] == "SUMMARY"
    assert summary["generation"]["ecgRecordId"] == "ecg-1"
    assert summary["generation"]["reportVersion"] == 1
    assert summary["generation"]["jobId"] == job["id"]

    section_ids = [s["id"] for s in summary["sections"]]
    assert section_ids[0] == "REPORT_HEADER"
    assert section_ids[-1] == "REPORT_FOOTER"
    assert "RAW_ECG_VISUALIZATION" in section_ids


def test_the_served_summary_matches_the_builder_output(env):
    """What is served is exactly what the Summary builder composed."""
    from app.reporting.context import GenerationContextLoader
    from app.reporting.repositories import ECGArtifactRepository, ReportGenerationJobRepository

    job = generate(env)
    session = env["session"]
    report = GeneratedReportRepository(session).get(job["reportId"])

    # Recompose from the same recording and compare the contract projection.
    stored_job = ReportGenerationJobRepository(session).get(job["id"])
    loader = GenerationContextLoader(
        session, artifacts=ECGArtifactRepository(store=env["ecg_store"])
    )
    recomposed = document_to_dict(
        SummaryReportBuilder().build(
            loader.load(stored_job), visualization=_pending_from(report, session)
        ),
        report_id=report.id,
    )
    served = env["client"].get(f"{API}/reports/{report.id}/summary").json()

    # The header and footer carry the generation stamp, which a rebuild
    # necessarily recomputes (a fresh timestamp and the next free version), so
    # those two are compared structurally and the rest value for value.
    stamped = {"REPORT_HEADER", "REPORT_FOOTER"}
    assert served["reportType"] == recomposed["reportType"]
    assert served["title"] == recomposed["title"]
    assert [s["id"] for s in served["sections"]] == [s["id"] for s in recomposed["sections"]]

    for served_section, rebuilt_section in zip(served["sections"], recomposed["sections"]):
        if served_section["id"] in stamped:
            assert served_section["title"] == rebuilt_section["title"]
            assert [v["label"] for v in served_section["values"]] == [
                v["label"] for v in rebuilt_section["values"]
            ]
        else:
            assert served_section == rebuilt_section


def test_the_summary_is_read_from_storage_not_recomposed(env):
    """Editing the stored artifact changes what is served, proving its origin."""
    job = generate(env)
    report = GeneratedReportRepository(env["session"]).get(job["reportId"])
    stored = Path(report.storage_dir) / SUMMARY_JSON_LOCATION

    document = json.loads(stored.read_text(encoding="utf-8"))
    document["title"] = "Persisted, not regenerated"
    stored.write_text(json.dumps(document), encoding="utf-8")

    served = env["client"].get(f"{API}/reports/{report.id}/summary").json()
    assert served["title"] == "Persisted, not regenerated"


def test_summary_and_detailed_state_the_same_facts(env):
    job = generate(env)
    summary = env["client"].get(f"{API}/reports/{job['reportId']}/summary").json()
    html = env["client"].get(f"{API}/reports/{job['reportId']}/html").text

    patient = next(s for s in summary["sections"] if s["id"] == "PATIENT_INFORMATION")
    name = next(v for v in patient["values"] if v["label"] == "Name")
    assert name["displayValue"] == "Patient One"
    assert "Patient One" in html  # the Detailed document says the same

    footer = next(s for s in summary["sections"] if s["id"] == "REPORT_FOOTER")
    version = next(v for v in footer["values"] if v["label"] == "Report version")
    assert version["displayValue"] == "1"


def test_availability_and_placeholders_are_preserved(env):
    """A field no vendored Signal Processing module computes must arrive
    marked, not silently blank -- even inside an otherwise-populated section
    (Sprint 5.7 Phase 2 -- see app/signal_processing/README.md)."""
    summary = env["client"].get(f"{API}/reports/{generate(env)['reportId']}/summary").json()

    rhythm = next(s for s in summary["sections"] if s["id"] == "RHYTHM_METRICS")
    assert rhythm["availability"] == "AVAILABLE"
    assert rhythm["isAvailable"] is True

    rate = next(v for v in rhythm["values"] if v["label"] == "Rate")
    assert rate["value"] is not None

    for label in ("Rhythm", "PR"):
        value = next(v for v in rhythm["values"] if v["label"] == label)
        assert value["value"] is None
        assert value["displayValue"] == "Not produced by Signal Processing"
        assert value["availability"] == "NOT_AVAILABLE"
        assert value["isAvailable"] is False


def test_figures_are_referenced_by_type_never_by_location(env):
    summary = env["client"].get(f"{API}/reports/{generate(env)['reportId']}/summary").json()

    section = next(s for s in summary["sections"] if s["id"] == "RAW_ECG_VISUALIZATION")
    figure = section["figures"][0]

    assert figure["artifactType"] == ArtifactType.RAW_ECG_SVG.value
    assert figure["mediaType"] == "image/svg+xml"
    assert figure["figureMetadata"]["lead"] == "II"
    assert "storageLocation" not in figure and "absolutePath" not in figure


def test_the_summary_exposes_no_filesystem_location(env):
    job = generate(env)
    body = env["client"].get(f"{API}/reports/{job['reportId']}/summary").text

    assert "storage_dir" not in body and "storageDir" not in body
    assert "absolute_path" not in body and "absolutePath" not in body
    assert "storage_location" not in body and "storageLocation" not in body
    assert str(env["report_store"].job_dir("ecg-1", job["id"])) not in body


# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------


def test_each_report_version_owns_an_independent_summary(env):
    first = generate(env)
    second = generate(env)

    first_summary = env["client"].get(f"{API}/reports/{first['reportId']}/summary").json()
    second_summary = env["client"].get(f"{API}/reports/{second['reportId']}/summary").json()

    assert first_summary["generation"]["reportVersion"] == 1
    assert second_summary["generation"]["reportVersion"] == 2
    assert first_summary["reportId"] == first["reportId"]
    assert second_summary["reportId"] == second["reportId"]
    assert first_summary["generation"]["jobId"] != second_summary["generation"]["jobId"]


def test_one_versions_summary_is_never_served_for_another(env):
    first = generate(env)
    second = generate(env)
    session = env["session"]

    v1 = summary_artifact(session, GeneratedReportRepository(session).get(first["reportId"]))
    response = env["client"].get(f"{API}/reports/{second['reportId']}/artifacts/{v1.id}")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


def test_another_tenant_cannot_read_the_summary(env):
    job = generate(env)
    env["as_user"]("usr-other")

    assert env["client"].get(f"{API}/reports/{job['reportId']}/summary").status_code == 404


def test_a_patient_cannot_read_the_summary(env):
    job = generate(env)
    env["as_user"]("usr-pat")

    assert env["client"].get(f"{API}/reports/{job['reportId']}/summary").status_code == 403


def test_a_superadmin_can_read_the_summary(env):
    job = generate(env)
    env["as_user"]("usr-super")

    assert env["client"].get(f"{API}/reports/{job['reportId']}/summary").status_code == 200


# ---------------------------------------------------------------------------
# Absence
# ---------------------------------------------------------------------------


def test_an_unknown_report_has_no_summary(env):
    assert env["client"].get(f"{API}/reports/grp-nope/summary").status_code == 404


def test_a_missing_summary_artifact_is_not_found(env):
    """A report generated before this contract existed has no Summary to serve."""
    job = generate(env)
    session = env["session"]
    report = GeneratedReportRepository(session).get(job["reportId"])
    session.delete(summary_artifact(session, report))
    session.commit()

    assert env["client"].get(f"{API}/reports/{report.id}/summary").status_code == 404


def test_a_summary_whose_file_is_gone_is_not_found(env):
    job = generate(env)
    report = GeneratedReportRepository(env["session"]).get(job["reportId"])
    (Path(report.storage_dir) / SUMMARY_JSON_LOCATION).unlink()

    assert env["client"].get(f"{API}/reports/{report.id}/summary").status_code == 404


def test_a_failed_generation_leaves_no_summary_artifact(env):
    """The existing rollback removes it with everything else."""
    from app.reporting.models.report_artifact import ReportArtifact

    job = generate(env, ecg_record_id="ecg-bare")

    assert job["status"] == "FAILED"
    assert (
        env["session"]
        .query(ReportArtifact)
        .filter(ReportArtifact.artifact_type == ArtifactType.SUMMARY_JSON.value)
        .count()
        == 0
    )
