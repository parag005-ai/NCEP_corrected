# Canonical Artifact Storage Flow

## Mandatory artifact contract

Canonical ECG success requires all uploaded raw companions and:

```text
waveform/waveform.npz
waveform/waveform.csv
waveform/waveform_meta.json
metadata/patient_metadata.json
metadata/ecg_metadata.json
metadata/clinical_metadata.json
metadata/device_metadata.json
metadata/quality_metadata.json
metadata/annotations.json
metadata/source_information.json
manifest/manifest.json
preprocessing/preprocessed.npz
preprocessing/preprocessing_report.json
manifest/artifact_manifest.json
```

## Write and verification path

```text
Artifact producer
  → FilesystemArtifactStore.write_*
       → write local staging/cache copy
       → production cloudinary mode:
            upload private raw object (required)
            propagate any error
  → finalize_artifact_manifest
       → materialize each mandatory path
       → cloudinary mode: download each object
       → compare durable bytes to local bytes
       → calculate SHA-256 and size
       → write manifest/artifact_manifest.json
       → download and compare manifest
  → only then insert ECGRecord and mark ingest SUCCEEDED
```

## Manifest record

```json
{
  "schemaVersion": "1.0",
  "recordId": "canonical-uuid",
  "durableStorageMode": "cloudinary",
  "verifiedAt": "timestamp",
  "artifacts": [
    {
      "relativePath": "waveform/waveform.npz",
      "sizeBytes": 123,
      "checksumSha256": "...",
      "mandatory": true,
      "durableReference": "private internal reference"
    }
  ]
}
```

The database retains the complete manifest. The manifest API removes `durableReference` before returning data.

## Read path

```text
Authorized waveform/report consumer
  → ECGArtifactRepository.load_bundle(ECGRecord)
  → read database or stored artifact manifest
  → verify every mandatory artifact checksum
  → FilesystemArtifactStore.materialize(exact relative path)
       local cache hit → use it
       cache miss → deterministic private object download with timeout
       download failure → FileStorageError
  → repository returns bundle or ECGArtifactUnavailableError
```

No prefix listing is needed for normal canonical reads. The waveform route and canonical download route no longer call `os.path.exists(record.storage_path)` as their source of truth.

## Storage modes

- `auto`: Cloudinary in production, filesystem outside production.
- `cloudinary`: private raw object storage is mandatory.
- `filesystem`: valid only when the configured root is a durable mounted volume or for local tests.

## Existing records

- Existing canonical records can still be read through deterministic paths when their durable objects exist.
- A row without a canonical record ID returns a legacy/unavailable state.
- A missing or corrupt mandatory artifact returns 409 to waveform clients and terminal failure to report jobs.
- No existing record or artifact is deleted by the migration.

