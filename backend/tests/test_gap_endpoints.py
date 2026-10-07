"""Router-level tests for the endpoints added to close the frontend/backend
integration gaps: legal consents, usage records, organisation DELETE/PUT
upsert, GET+PATCH auth/session, and the pipeline-report view of a report.

Uses an isolated in-memory SQLite database per test (via dependency override),
independent of the ingestion/preprocessing suite's fixtures.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import ECGRecord, Organisation, Patient, User
from app.rate_limit import limiter
from app.security import hash_password


@pytest.fixture()
def client():
    # The login rate limit is keyed by remote address and shared process-wide;
    # TestClient always reports the same address, so tests would otherwise
    # trip each other's 10/minute budget.
    limiter.reset()

    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    db = TestingSessionLocal()
    now = datetime.now(timezone.utc)
    db.add(Organisation(id="org-001", name="Test Hospital", created_at=now, total_users=0, total_patients=0))
    db.add(
        User(
            id="user-super-1",
            email="super@test.demo",
            name="Super Admin",
            role="superadmin",
            organisation_id="org-001",
            status="Active",
            created_at=now,
            password_hash=hash_password("password"),
        )
    )
    db.add(
        Patient(
            id="pat-001",
            name="Test Patient",
            age=40,
            gender="Female",
            email="patient@test.demo",
            organisation_id="org-001",
            created_at=now,
        )
    )
    db.add(
        ECGRecord(
            id="ecg-001",
            patient_id="pat-001",
            organisation_id="org-001",
            uploaded_at=now,
            quality_score=72.5,
            beat_count=48,
            validation_status="valid",
            available_leads=["I", "II"],
            duration_seconds=10.0,
        )
    )
    db.commit()
    db.close()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def auth_headers(client: TestClient) -> dict:
    """Logs in and returns {} -- the session cookie set on `client` is what
    actually authenticates subsequent requests through the same client."""
    resp = client.post("/api/auth/login", json={"email": "super@test.demo", "password": "password"})
    assert resp.status_code == 200, resp.text
    return {}


class TestLegalConsents:
    def test_unaccepted_by_default(self, client):
        resp = client.get("/api/legal-consents/current", headers=auth_headers(client))
        assert resp.status_code == 200
        assert resp.json() == {"accepted": False, "version": "1", "acceptedAt": None}

    def test_accept_then_reflects_true(self, client):
        headers = auth_headers(client)
        post_resp = client.post("/api/legal-consents/current", headers=headers)
        assert post_resp.status_code == 200
        assert post_resp.json()["accepted"] is True

        get_resp = client.get("/api/legal-consents/current", headers=headers)
        assert get_resp.json()["accepted"] is True

    def test_requires_auth(self, client):
        resp = client.get("/api/legal-consents/current")
        assert resp.status_code == 401


class TestUsage:
    def test_create_then_list_scoped_to_own_org(self, client):
        headers = auth_headers(client)
        create_resp = client.post(
            "/api/usage", json={"action": "ECG processed", "creditsUsed": 3, "status": "Success"}, headers=headers
        )
        assert create_resp.status_code == 201
        body = create_resp.json()
        assert body["organisationId"] == "org-001"
        assert body["organisationName"] == "Test Hospital"

        list_resp = client.get("/api/usage", headers=headers)
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1

    def test_query_param_filters_by_organisation(self, client):
        headers = auth_headers(client)
        client.post("/api/usage", json={"action": "x", "creditsUsed": 1}, headers=headers)
        resp = client.get("/api/usage?organisationId=org-does-not-exist", headers=headers)
        # superadmin has no forced org scope, so the query param is honored.
        assert resp.json() == []


class TestOrganisationDeleteAndUpsert:
    def test_put_creates_new_organisation(self, client):
        headers = auth_headers(client)
        resp = client.put("/api/organisations/org-new", json={"name": "New Org", "status": "Active"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == "org-new"
        assert resp.json()["name"] == "New Org"

    def test_put_updates_existing_organisation(self, client):
        headers = auth_headers(client)
        resp = client.put(
            "/api/organisations/org-001", json={"name": "Renamed Hospital", "status": "Active"}, headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed Hospital"

    def test_delete_empty_organisation_succeeds(self, client):
        headers = auth_headers(client)
        client.put("/api/organisations/org-empty", json={"name": "Empty Org", "status": "Active"}, headers=headers)
        resp = client.delete("/api/organisations/org-empty", headers=headers)
        assert resp.status_code == 204

    def test_delete_organisation_with_dependents_conflicts(self, client):
        headers = auth_headers(client)
        resp = client.delete("/api/organisations/org-001", headers=headers)
        assert resp.status_code == 409

    def test_delete_requires_superadmin(self, client):
        headers = auth_headers(client)
        client.put("/api/organisations/org-empty2", json={"name": "Empty Org 2", "status": "Active"}, headers=headers)
        admin_resp = client.post(
            "/api/users",
            json={
                "email": "org-admin@test.demo",
                "name": "Org Admin",
                "role": "admin",
                "organisationId": "org-001",
                "status": "Active",
                "password": "password",
            },
            headers=headers,
        )
        assert admin_resp.status_code == 201
        # Logging in again on the same client overwrites its session cookie
        # with the org-admin's, which is what authenticates the delete below.
        login_resp = client.post(
            "/api/auth/login", json={"email": "org-admin@test.demo", "password": "password"}
        )
        assert login_resp.status_code == 200
        resp = client.delete("/api/organisations/org-empty2")
        assert resp.status_code == 403


class TestAuthSession:
    def test_get_session_matches_me(self, client):
        headers = auth_headers(client)
        session_resp = client.get("/api/auth/session", headers=headers)
        me_resp = client.get("/api/auth/me", headers=headers)
        assert session_resp.json() == me_resp.json()

    def test_patch_session_updates_name_only(self, client):
        headers = auth_headers(client)
        session = client.get("/api/auth/session", headers=headers).json()
        session["name"] = "Renamed"
        session["role"] = "patient"  # attempted privilege escalation via body -- must be ignored
        resp = client.patch("/api/auth/session", json=session, headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Renamed"
        assert body["role"] == "superadmin"


class TestPipelineReport:
    def test_pipeline_report_uses_real_preprocessing_output_not_fabricated_values(self, client):
        headers = auth_headers(client)
        client.post(
            "/api/reports",
            json={
                "id": "rpt-001",
                "title": "Test Report",
                "patientId": "pat-001",
                "patientName": "Test Patient",
                "organisationId": "org-001",
                "ecgRecordId": "ecg-001",
            },
            headers=headers,
        )
        resp = client.get("/api/reports/rpt-001/pipeline", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["signalQualityScore"] == 72.5
        assert body["rPeakCount"] == 48
        assert body["preprocessingStatus"] == "Completed"
        # Not computed by this pipeline -- must be null/empty, never invented.
        assert body["qtInterval"] is None
        assert body["saecgParameters"] == []

    def test_pipeline_report_404_for_unknown_report(self, client):
        resp = client.get("/api/reports/does-not-exist/pipeline", headers=auth_headers(client))
        assert resp.status_code == 404


class TestApplicationDataReset:
    def test_reset_wipes_then_reseeds_and_caller_can_still_log_in(self, client):
        headers = auth_headers(client)
        client.post("/api/usage", json={"action": "x", "creditsUsed": 1}, headers=headers)

        resp = client.post("/api/admin/application-data", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        # The fixture's ad-hoc org-001 test data is gone...
        assert client.get("/api/usage", headers=headers).status_code == 401  # old token's user was wiped

        # ...but the standard seeded superadmin account exists again and can log in.
        login = client.post("/api/auth/login", json={"email": "superadmin@ncep.demo", "password": "password"})
        assert login.status_code == 200

    def test_reset_requires_superadmin(self, client):
        headers = auth_headers(client)
        client.post(
            "/api/users",
            json={
                "email": "not-super@test.demo",
                "name": "Org Admin",
                "role": "admin",
                "organisationId": "org-001",
                "status": "Active",
                "password": "password",
            },
            headers=headers,
        )
        login_resp = client.post(
            "/api/auth/login", json={"email": "not-super@test.demo", "password": "password"}
        )
        assert login_resp.status_code == 200
        resp = client.post("/api/admin/application-data")
        assert resp.status_code == 403
