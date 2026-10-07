"""Ingest the real sample SAECG bundle (backend/sample_file) so the demo shows
real waveform data out of the box — no manual upload needed.

Run (after seeding the base demo data):  python -m app.seed_sample
Attaches the recording to patient pat-001 (Anaya Rao).
"""
from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import date, datetime, timezone

from app.database import SessionLocal
from app.models import ECGRecord, Patient
from app.routers.ecg import UPLOAD_DIR
from app.waveform import build_meta

SAMPLE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_file")
TARGET_PATIENT_ID = "pat-001"


def seed_sample() -> None:
    csv_src = os.path.join(SAMPLE_DIR, "waveform.csv")
    if not os.path.exists(csv_src):
        print(f"No sample bundle at {SAMPLE_DIR} — skipping.")
        return

    db = SessionLocal()
    try:
        patient = db.get(Patient, TARGET_PATIENT_ID)
        if patient is None:
            print(f"Patient {TARGET_PATIENT_ID} not found — run `python -m app.seed` first.")
            return
        if db.query(ECGRecord).filter_by(file_name="waveform.csv").first():
            print("Sample SAECG already ingested — skipping.")
            return

        ecg_meta = {}
        meta_path = os.path.join(SAMPLE_DIR, "ecg_metadata.json")
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                ecg_meta = json.load(f)

        os.makedirs(UPLOAD_DIR, exist_ok=True)
        ecg_id = f"ecg-{uuid.uuid4().hex[:8]}"
        storage_path = os.path.join(UPLOAD_DIR, f"{ecg_id}.csv")
        shutil.copy2(csv_src, storage_path)

        meta = build_meta(storage_path, ecg_meta)
        obj = ECGRecord(
            id=ecg_id,
            patient_id=patient.id,
            patient_name=patient.name,
            doctor_id=patient.assigned_doctor_id,
            organisation_id=patient.organisation_id,
            file_name="waveform.csv",
            file_type="CSV",
            recording_date=date.today(),
            device_source=ecg_meta.get("device_model") or "SAECG Recorder",
            notes="Signal-averaged ECG (15-lead, Frank XYZ) — late-potential study.",
            status="Ready",
            uploaded_at=datetime.now(timezone.utc),
            uploaded_by="Dr. Meera Shah",
            storage_path=storage_path,
            source_format=meta.source_format,
            sampling_rate_hz=meta.sampling_rate_hz,
            lead_count=meta.lead_count,
            available_leads=meta.available_leads,
            xyz_available=meta.xyz_available,
            duration_seconds=meta.duration_seconds,
            sample_count=meta.sample_count,
            units=meta.units,
            record_id=meta.record_id,
        )
        db.add(obj)
        db.commit()
        print(
            f"Ingested sample SAECG {obj.id} → {TARGET_PATIENT_ID} "
            f"({meta.lead_count} leads, {meta.sampling_rate_hz} Hz, {meta.duration_seconds}s)."
        )
    finally:
        db.close()


if __name__ == "__main__":
    seed_sample()
