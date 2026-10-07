"""Report Generation API integration tests (Sprint 10).

The complete flow is exercised against a real database, a real ECG artifact
store and the real Workflow Orchestrator: authenticated user -> accessible
recording -> generation job -> background execution -> GeneratedReport ->
HTML/PDF artifacts -> authorized download. Only the PDF rendering engine is
substituted, and it has its own dedicated test.
"""

from __future__ import annotations



from app.reporting import models as reporting_models  # noqa: F401 -- registers reporting tables
from app.reporting.api import service as report_service
from app.reporting.constants import ArtifactType, JobStatus

from tests.reporting.conftest import API, generate

# ---------------------------------------------------------------------------
# Job creation
# ---------------------------------------------------------------------------


def test_requesting_a_report_returns_a_job_to_poll(env):
    response = env["client"].post(f"{API}/jobs", json={"ecgRecordId": "ecg-1"})

    assert response.status_code == 202
    body = response.json()
    assert body["ecgRecordId"] == "ecg-1"
    assert body["statusUrl"] == f"{API}/jobs/{body['id']}"
    assert body["progressPercent"] == 0
    assert body["reportId"] is None


def test_the_client_cannot_choose_the_tenant(env):
    """Organisation, patient and doctor are resolved from the recording."""
    response = env["client"].post(
        f"{API}/jobs",
        json={"ecgRecordId": "ecg-1", "organisationId": "org-2", "patientId": "pat-999"},
    )

    assert response.status_code == 202
    job = env["session"].get(reporting_models.ReportGenerationJob, response.json()["id"])
    assert job.organisation_id == "org-1"
    assert job.patient_id == "pat-1"
    assert job.requested_by_doctor_id == "doc-1"


def test_an_unknown_recording_is_not_found(env):
    response = env["client"].post(f"{API}/jobs", json={"ecgRecordId": "ecg-nope"})

    assert response.status_code == 404
    assert response.json()["detail"] == "ECG record not found"


def test_a_recording_in_another_organisation_is_refused(env):
    env["as_user"]("usr-other")

    response = env["client"].post(f"{API}/jobs", json={"ecgRecordId": "ecg-1"})

    assert response.status_code == 403
    assert env["session"].query(reporting_models.ReportGenerationJob).count() == 0


def test_a_patient_may_not_request_generation(env):
    env["as_user"]("usr-pat")

    response = env["client"].post(f"{API}/jobs", json={"ecgRecordId": "ecg-1"})

    assert response.status_code == 403


def test_a_request_without_a_recording_is_rejected(env):
    assert env["client"].post(f"{API}/jobs", json={}).status_code == 422
    assert env["client"].post(f"{API}/jobs", json={"ecgRecordId": ""}).status_code == 422


# ---------------------------------------------------------------------------
# The complete flow
# ---------------------------------------------------------------------------


def test_the_whole_flow_from_request_to_downloaded_pdf(env):
    job = generate(env)

    assert job["status"] == JobStatus.COMPLETED.value
    assert job["progressPercent"] == 100
    assert job["reportId"] is not None
    assert job["errorCode"] is None

    report = env["client"].get(job["reportUrl"]).json()
    assert report["version"] == 1
    assert report["ecgRecordId"] == "ecg-1"
    assert report["detailedTemplateId"] == "ncep-detailed-report"
    assert {a["artifactType"] for a in report["artifacts"]} == {
        ArtifactType.SUMMARY_JSON.value,
        ArtifactType.RAW_ECG_SVG.value,
        ArtifactType.DETAILED_HTML.value,
        ArtifactType.DETAILED_PDF.value,
    }

    html = env["client"].get(report["htmlUrl"])
    assert html.status_code == 200
    assert html.headers["content-type"].startswith("text/html")
    assert b'class="report-page"' in html.content

    pdf = env["client"].get(report["pdfUrl"])
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF-")


def test_a_completed_report_exposes_no_filesystem_location(env):
    job = generate(env)
    report = env["client"].get(job["reportUrl"]).json()

    body = str(report)
    assert "storageDir" not in body and "storage_dir" not in body
    assert "storageLocation" not in body and "storage_location" not in body
    assert str(env["report_store"].job_dir("ecg-1", job["id"])) not in body
    for artifact in report["artifacts"]:
        assert artifact["downloadUrl"].startswith(f"{API}/reports/")


def test_every_registered_artifact_is_downloadable(env):
    job = generate(env)
    report = env["client"].get(job["reportUrl"]).json()

    for artifact in report["artifacts"]:
        response = env["client"].get(artifact["downloadUrl"])
        assert response.status_code == 200
        assert len(response.content) == artifact["fileSizeBytes"]


# ---------------------------------------------------------------------------
# Versions and history
# ---------------------------------------------------------------------------


def test_regeneration_lists_both_versions_newest_first(env):
    generate(env)
    generate(env)

    reports = env["client"].get(f"{API}/reports", params={"ecgRecordId": "ecg-1"}).json()

    assert [r["version"] for r in reports] == [2, 1]
    assert reports[0]["id"] != reports[1]["id"]


def test_job_history_is_listed_for_a_recording(env):
    generate(env)
    generate(env)

    jobs = env["client"].get(f"{API}/jobs", params={"ecgRecordId": "ecg-1"}).json()

    assert len(jobs) == 2
    assert all(j["status"] == JobStatus.COMPLETED.value for j in jobs)


def test_listing_for_an_inaccessible_recording_is_refused(env):
    env["as_user"]("usr-other")

    assert env["client"].get(f"{API}/reports", params={"ecgRecordId": "ecg-1"}).status_code == 403
    assert env["client"].get(f"{API}/jobs", params={"ecgRecordId": "ecg-1"}).status_code == 403


# ---------------------------------------------------------------------------
# Failure
# ---------------------------------------------------------------------------


def test_a_recording_without_artifacts_fails_with_a_safe_message(env):
    """The internal failure names a filesystem path; the client must not see it."""
    job = generate(env, ecg_record_id="ecg-bare")

    assert job["status"] == JobStatus.FAILED.value
    assert job["errorCode"] == "ECGArtifactUnavailableError"
    assert job["errorMessage"] == "The ECG recording has no report-ready artifacts."
    assert "ecg_storage" not in job["errorMessage"]
    assert job["reportId"] is None


def test_a_failed_generation_leaves_no_report_to_fetch(env):
    generate(env, ecg_record_id="ecg-bare")

    reports = env["client"].get(f"{API}/reports", params={"ecgRecordId": "ecg-bare"}).json()

    assert reports == []


# ---------------------------------------------------------------------------
# Authorization on retrieval
# ---------------------------------------------------------------------------


def test_another_tenant_cannot_reach_a_report_or_its_documents(env):
    job = generate(env)
    report = env["client"].get(job["reportUrl"]).json()
    artifact_url = report["artifacts"][0]["downloadUrl"]

    env["as_user"]("usr-other")

    assert env["client"].get(job["reportUrl"]).status_code == 404
    assert env["client"].get(report["htmlUrl"]).status_code == 404
    assert env["client"].get(report["pdfUrl"]).status_code == 404
    assert env["client"].get(artifact_url).status_code == 404
    assert env["client"].get(job["statusUrl"]).status_code == 404


def test_a_superadmin_reaches_reports_across_organisations(env):
    job = generate(env)
    env["as_user"]("usr-super")

    assert env["client"].get(job["statusUrl"]).status_code == 200
    assert env["client"].get(job["reportUrl"]).status_code == 200


def test_a_patient_may_not_read_generated_reports(env):
    job = generate(env)
    env["as_user"]("usr-pat")

    assert env["client"].get(job["reportUrl"]).status_code == 403
    assert env["client"].get(job["statusUrl"]).status_code == 403


def test_an_artifact_of_another_report_is_not_served(env):
    first = generate(env)
    second = generate(env)
    other_report = env["client"].get(second["reportUrl"]).json()
    foreign_artifact_id = other_report["artifacts"][0]["id"]

    response = env["client"].get(
        f"{API}/reports/{first['reportId']}/artifacts/{foreign_artifact_id}"
    )

    assert response.status_code == 404


def test_unknown_reports_and_jobs_are_not_found(env):
    assert env["client"].get(f"{API}/reports/grp-nope").status_code == 404
    assert env["client"].get(f"{API}/jobs/rgj-nope").status_code == 404
    assert env["client"].get(f"{API}/reports/grp-nope/pdf").status_code == 404


# ---------------------------------------------------------------------------
# Cancellation
# ---------------------------------------------------------------------------


def test_a_finished_job_cannot_be_cancelled(env):
    job = generate(env)

    response = env["client"].post(f"{API}/jobs/{job['id']}/cancel")

    assert response.status_code == 409
    assert "COMPLETED" in response.json()["detail"]


def test_cancelling_an_unknown_job_is_not_found(env):
    assert env["client"].post(f"{API}/jobs/rgj-nope/cancel").status_code == 404


def test_a_patient_may_not_cancel_a_job(env):
    job = generate(env)
    env["as_user"]("usr-pat")

    assert env["client"].post(f"{API}/jobs/{job['id']}/cancel").status_code == 403


# ---------------------------------------------------------------------------
# Concurrent requests
# ---------------------------------------------------------------------------


def test_two_requests_produce_two_independent_versions(env):
    first = generate(env)
    second = generate(env)

    assert first["id"] != second["id"]
    assert first["reportId"] != second["reportId"]
    first_report = env["client"].get(first["reportUrl"]).json()
    second_report = env["client"].get(second["reportUrl"]).json()
    assert {first_report["version"], second_report["version"]} == {1, 2}


def test_a_job_already_executed_is_not_run_twice(env):
    """Re-running a finished job is refused by the state machine."""
    job = generate(env)
    stored = env["session"].get(reporting_models.ReportGenerationJob, job["id"])

    report_service.run_generation_job(stored.id)  # must not raise

    env["session"].expire_all()
    assert env["session"].get(reporting_models.ReportGenerationJob, job["id"]).status == (
        JobStatus.COMPLETED.value
    )
