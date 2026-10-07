# NCEP E2E Data Integrity Audit

**Audit date:** 7 October 2026  
**Scope:** Canonical ECG ingestion, artifact integrity, Signal Processing (SP), SP-to-report mapping, HTML/PDF value lineage, and failure behavior  
**Method:** Source inspection, existing test review, targeted pytest execution, complete relevant-suite execution, and runtime examination of the previously completed real WFDB E2E record  
**Production code modified by this audit:** None  
**Audit status:** **PASS WITH WARNING**

## 1. Executive Summary

The real WFDB flow is data-integrity verified for the supplied `s0017lre` record. The three original files were preserved with matching SHA-256 hashes; WFDB decoding produced 15 leads × 115,200 samples at 1,000 Hz; the stored canonical NPZ is numerically identical to the decoded WFDB physical signal (`array_equal=true`, maximum absolute difference `0.0`); the CSV export is also exact for this fixture; and every mandatory artifact passed manifest checksum verification.

The same stored canonical waveform was read through `WaveformReader`, processed by the real `analyze_waveform()` implementation, mapped into `GenerationContext.signal_processing`, and rendered to the generated HTML and PDF. The audited runtime produced 228 named SP metrics plus four result-envelope fields. All reportable measurements checked in the E2E document preserve their value lineage, with only documented presentation rounding and the explicit mV-to-µV conversion for RMS20/RMS40.

No reporting code independently calculates HR, RR, PR, QRS, QT, QTc, Tpeak–Tend, dispersion, P-wave measurements, SAECG measurements, rhythm, diagnosis, or clinical classifications. Missing authoritative output is represented as unavailable; no clinical threshold or interpretation is invented.

The principal release warnings are outside the verified WFDB numeric lineage:

1. The upload UI advertises PDF, EDF, PNG/JPEG and “Max 50MB,” while the canonical backend supports none of those formats and permits 200 MiB. It also advertises SCP-ECG without allowing `.scp`/`.scp-ecg` in the file chooser.
2. XML support is the documented NCEP generic XML profile, not arbitrary vendor ECG XML. SCP-ECG and DICOM have parser/test evidence but were not validated here with a real external vendor corpus.
3. The report SP adapter intentionally fails soft to an all-awaiting context on an unexpected SP exception. That preserves report availability but can produce a document without measurements rather than fail the report job.
4. Ingestion preprocessing artifacts are durable and valid, but reporting SP starts from the canonical raw NPZ and performs the SP package’s own preprocessing. `preprocessed.npz` is not the SP input.
5. The scientific stack emitted numerous third-party runtime/deprecation warnings. Tests still passed, but the warning volume should be tracked for future dependency upgrades.

### Final status by area

| Area | Status | Basis |
|---|---|---|
| Real WFDB ingestion and canonicalization | PASS | Runtime artifact and waveform comparison |
| Raw/canonical/stored/read-back integrity | PASS | Hashes, shapes, metadata, exact numeric comparison |
| Preprocessing artifact creation | PASS | Runtime artifacts and tests |
| Real SP execution from canonical artifacts | PASS | Runtime `analyze_waveform()` result, 228 metrics |
| SP-to-report value lineage | PASS | Context mapping, JSON, HTML and PDF checks |
| Missing-output governance | PASS | Source and tests; unavailable states preserved |
| Advertised format accuracy | FAIL | Frontend/backend mismatch |
| WFDB production readiness | PASS WITH WARNING | Numeric path verified; fail-soft SP and warning volume remain |
| All-format production readiness | NOT VERIFIED | No real vendor corpus for XML/DICOM/SCP-ECG |

## 2. Architecture and Data Flow

```text
POST /api/ecg-records/ingest
  -> UploadOrchestrator.create_session
  -> persistent ECGIngestJob (QUEUED)
  -> run_ingest_job (RUNNING)
  -> create_ecg_record
       -> FormatDetector.detect
       -> ParserFactory.get_parser
       -> parser.parse
       -> MetadataOrchestrator.extract
       -> ValidationOrchestrator.validate
       -> ECGRecordBuilder.build
       -> StorageOrchestrator.store
  -> PreprocessingOrchestrator.run
  -> FilesystemArtifactStore.finalize_artifact_manifest
  -> database ECGRecord commit

Report generation
  -> GenerationContextLoader.load
  -> ECGArtifactRepository.load_bundle (manifest/checksum verification)
  -> WaveformReader.read_from_artifacts (canonical waveform.npz)
  -> analyze_waveform (SP-owned preprocessing + P/QRS/T/QT/P-SAECG/QRS-SAECG)
  -> build_signal_processing_outputs
  -> GenerationContext.signal_processing
  -> SummaryReportBuilder / DetailedReportBuilder
  -> Jinja HTML
  -> Chromium PDF
```

Important boundary: ingestion’s `preprocessing/preprocessed.npz` is a durable ingestion output and supplies recording-quality provenance. Reporting/SP does **not** consume it. SP rereads `waveform/waveform.npz` and calls `app.signal_processing.preprocessing.preprocess_signal()` per lead. This is the actual implemented flow, not a signal-loss finding.

## 3. Ingestion Audit

| Stage | Source file | Function/class | Input | Output | Validation/guard | Status |
|---|---|---|---|---|---|---|
| API upload | `backend/app/routers/ecg.py` | `ingest_ecg()` | multipart files, patient, metadata, idempotency header | HTTP 202 + `ECGIngestJobOut` | authentication, role and tenant/patient scope | PASS |
| Request identity | `backend/app/ingestion/idempotency.py` | `request_fingerprint()`, `effective_idempotency_key()` | patient and filename/content tuples | deterministic request/effective keys | prevents successful duplicate canonical records | PASS |
| Staging | `backend/app/ingestion/upload_orchestrator.py` | `UploadOrchestrator.create_session()` | filename/bytes pairs | isolated `UploadSession` | total size, duplicate filename, basename normalization | PASS WITH WARNING |
| Job creation | `backend/app/ingestion/job_service.py` | `create_or_get_ingest_job()` | session and request identity | persistent QUEUED job | unique idempotency key/race recovery | PASS |
| Worker | same | `run_ingest_job()` | staged upload ID | terminal job and, on success, DB record | stage tracking, rollback, artifact cleanup | PASS |
| Format detection | `backend/app/ingestion/detectors/format_detector.py` | `FormatDetector.detect()` | staged file set | one `ECGFormat` | extension/magic/content checks; rejects mixed formats | PASS |
| Parser selection | `backend/app/ingestion/factories/parser_factory.py` | `ParserFactory.get_parser()` | detected format | registered parser instance | only registered five formats | PASS |
| WFDB parsing | `backend/app/ingestion/parsers/wfdb/parser.py` | `WFDBParser.parse()` | `.hea` plus companions | `ParsedECG` | required header/data, WFDB decode, canonical lead resolution | PASS |
| CSV parsing | `backend/app/ingestion/parsers/csv/parser.py` | `CSVParser.parse()` | one CSV | `ParsedECG` | lead headers, numeric samples, sampling metadata/time axis | PASS WITH WARNING |
| XML parsing | `backend/app/ingestion/parsers/xml/parser.py` | `XMLParser.parse()` | NCEP-profile XML | `ParsedECG` | required `RecordingInfo`, leads and numeric samples | PASS WITH WARNING |
| DICOM parsing | `backend/app/ingestion/parsers/dicom/parser.py` | `DICOMParser.parse()` | waveform DICOM | `ParsedECG` | SOP/waveform sequence/channel definitions and sample metadata | PASS WITH WARNING |
| SCP-ECG parsing | `backend/app/ingestion/parsers/scp/parser.py` | `SCPParser.parse()` | `.scp`/`.scp-ecg` | `ParsedECG` | sections 0/1/3/6, lead IDs, lengths, supported encoding | PASS WITH WARNING |
| Metadata extraction | `backend/app/ingestion/metadata_extractor.py` | `MetadataOrchestrator.extract()` | `ParsedECG` | typed patient/ECG/clinical/device/quality/source metadata | required derivations and explicit missing metadata | PASS |
| Validation | `backend/app/ingestion/validator.py` | `ValidationOrchestrator.validate()` | parsed ECG + metadata | `ValidatedParsedECG` | format, files, waveform, leads, sampling, metadata, quality | PASS |
| Signal validation | `backend/app/ingestion/validation/signals/*` | `WaveformValidator`, `LeadValidator`, `SamplingRateValidator` | parsed waveform | issues / terminal failure | zero samples, all-nonfinite leads, lead consistency, positive rate/duration | PASS WITH WARNING |
| Canonical build | `backend/app/ingestion/builders/ecg_record_builder.py` | `ECGRecordBuilder.build()` | validated parsed ECG | immutable domain `ECGRecord` | builder accepts validated input only | PASS |
| Artifact generation | `backend/app/ingestion/storage/artifacts.py` | `ArtifactGenerator` | canonical record | NPZ, CSV, metadata and processing manifest | canonical lead order; no absent-lead zero filling | PASS |
| Atomic storage | `backend/app/ingestion/storage/orchestrator.py` | `StorageOrchestrator.store()` | record and raw files | record-scoped artifact tree | rollback on failure; raw copies made read-only | PASS |
| Ingestion preprocessing | `backend/app/preprocessing/pipeline.py` | `PreprocessingOrchestrator.run()` | canonical waveform | preprocessed leads, beats, quality result | per-lead preprocessing and quality | PASS |
| Durable manifest | `backend/app/storage/file/filesystem.py` | `finalize_artifact_manifest()` | required paths | checksummed `artifact_manifest.json` | existence, non-empty files, SHA-256 verification | PASS |
| DB commit | `backend/app/ingestion/job_service.py` | `_build_ecg_row()`, `run_ingest_job()` | record/artifact/preprocess results | DB `ECGRecord`; job SUCCEEDED | occurs only after durable verification | PASS |
| Report read-back | `backend/app/reporting/repositories/ecg_artifact_repository.py` | `ECGArtifactRepository.load_bundle()` | DB row + artifact manifest | verified `ECGArtifactBundle` | mandatory artifact and checksum verification | PASS |
| Waveform read-back | `backend/app/reporting/visualizations/waveform_reader.py` | `WaveformReader.read_from_artifacts()` | NPZ + metadata | typed waveform data | dimensions, lead names, sampling rate and unit conversion | PASS |
| SP input | `backend/app/reporting/context/signal_processing_builder.py` | `build_signal_processing_outputs()` | verified artifact bundle | `SignalProcessingOutputs` | canonical waveform only; fail-soft on read/SP exception | PASS WITH WARNING |

Warnings: partially nonfinite samples are accepted with `WARNING` (only an all-nonfinite lead fails); exact lead count is not fixed at 15; this is intentional multi-format behavior. The synchronous staging errors `UploadTooLargeError` and `DuplicateFilenameError` are not explicitly converted to an HTTP 4xx response in `ingest_ecg()` and no global ingestion exception handler exists; likely API behavior is 500, but this exact HTTP result was not runtime-tested in this audit.

## 4. Supported Format Matrix

| Format/claim | Frontend | Detector/registry | Parser | Test evidence | Audit result |
|---|---|---|---|---|---|
| WFDB | Advertised; chooser `.hea,.dat,.xyz,.atr,.qrs,.ecg` | Registered | Real `wfdb.rdrecord`; annotations optional | detector, parser, E2E unit tests; real 15-lead E2E | PASS |
| CSV | Advertised; `.csv` | Registered | generic lead-column CSV; requires explicit/inferable sampling | parser and E2E tests | PASS WITH WARNING |
| XML | Advertised; `.xml` | Registered | only documented NCEP `<ECG><RecordingInfo/><Leads/>` profile | parser and E2E tests | PASS WITH WARNING |
| DICOM | Advertised; chooser `.dcm` only | `.dcm`, `.dicom` and `DICM` magic | first waveform sequence, channel conversion | parser and E2E synthetic tests | PASS WITH WARNING |
| SCP-ECG | Text advertises it; chooser omits `.scp,.scp-ecg` | Registered | uncompressed/difference-order 0/1/2, core 12 leads; Huffman/bimodal unsupported | synthetic parser/E2E tests | PASS WITH WARNING |
| PDF | chooser `.pdf` | Not registered | none | none | FAIL |
| EDF | advertised and chooser `.edf` | Not registered | none | none | FAIL |
| PNG/JPEG | chooser `.png,.jpg,.jpeg` | Not registered | none | none | FAIL |

Additional mismatch: frontend text says “Max 50MB”; `MAX_UPLOAD_SIZE_BYTES` is `200 * 1024 * 1024` (200 MiB). Backend supports `.dicom`, but the chooser lists only `.dcm`.

“PASS WITH WARNING” for XML/DICOM/SCP means the implemented profile passes repository tests, not that arbitrary vendor files are interoperable. No real multi-vendor corpus was supplied or run.

## 5. Failure-Path Matrix

Unless noted as runtime, the matrix describes behavior proven by source and repository tests.

| Failure | API/job result | DB/artifacts | SP/report reachability | Error/retry assessment | Status |
|---|---|---|---|---|---|
| Unsupported extension | initial request normally 202; job FAILED at detection | failed job retained; no ECG row; staged/canonical files cleaned | not reached | actionable `FormatDetectionError`/`UnsupportedFormatError`; safe retry | PASS |
| Mixed recognized formats | 202 then FAILED | no ECG row; cleanup | not reached | explicitly rejected as ambiguous | PASS |
| Corrupt/empty content | 202 then FAILED at parser/validation | no ECG row; cleanup | not reached | format-specific message; safe retry | PASS |
| Missing WFDB `.hea` | 202 then FAILED at detection | no ECG row; cleanup | not reached | companion-only bundle cannot establish WFDB record | PASS |
| Missing WFDB `.dat` | 202 then FAILED in `WFDBParser` | no ECG row; cleanup | not reached | `MissingRequiredFileError`; safe retry | PASS |
| Malformed WFDB | 202 then FAILED in WFDB decode | no ECG row; cleanup | not reached | parser wraps malformed source | PASS |
| Invalid CSV | 202 then FAILED in parser or validation | no ECG row; cleanup | not reached | missing leads/rate and all-invalid samples rejected; partial NaN only warns | PASS WITH WARNING |
| Invalid XML | 202 then FAILED | no ECG row; cleanup | not reached | required element/attribute/sample messages | PASS |
| Invalid DICOM | 202 then FAILED | no ECG row; cleanup | not reached | waveform/channel/sample metadata checked | PASS |
| Invalid/unsupported SCP encoding | 202 then FAILED | no ECG row; cleanup | not reached | section/encoding/truncation errors are explicit | PASS |
| Metadata absent | may continue with WARNING when nonfatal | ECG row and artifacts created | reachable | missing patient metadata preserved as validation warning | PASS |
| Metadata fatal inconsistency | 202 then FAILED validation | no ECG row; cleanup | not reached | aggregated validation issues | PASS |
| Sampling rate ≤ 0 | 202 then FAILED validation (or parser model rejection) | no ECG row; cleanup | not reached | explicit positive-rate message | PASS |
| Zero leads | 202 then FAILED validation/model construction | no ECG row; cleanup | not reached | explicit canonical-lead message | PASS |
| Non-15 lead count | accepted if internally consistent | ECG row/artifacts created | reachable | intentional; platform supports available canonical subset | PASS |
| Missing mandatory artifact during commit | job FAILED in durable verification | canonical directory removed; no ECG row | not reached | exact relative path identified | PASS |
| Missing artifact during report | report context load fails | ECG row remains; no successful new report | SP not reached | exact required artifact message | PASS |
| Corrupt checksummed artifact | report context load fails integrity verification | ECG row remains | SP not reached | checksum mismatch tested | PASS |
| SP unexpected failure | report continues with all-awaiting SP context | report may still be created | builders reached without SP values | availability preserved, but fail-soft can hide operational defects | PASS WITH WARNING |
| Duplicate payload, derived key | existing nonfailed job returned | no duplicate ECG record | existing result reused | retry/idempotency safe | PASS |
| Supplied idempotency key reused with different payload | HTTP 409 | unchanged | not reached | clear conflict | PASS |
| Retry after failed job | same job ID is restaged/queued | cannot create a second successful record for same operation | reached only after successful retry | safe by design | PASS |
| Duplicate filenames / >200 MiB | thrown before job creation | no job/ECG row; staging not retained | not reached | domain error good; HTTP mapping not verified and likely 500 | NOT VERIFIED |
| Unknown patient/out-of-scope patient | HTTP 404 | no job/artifacts | not reached | tenant-safe response; safe retry with correct patient | PASS |

## 6. Artifact Integrity

### Real fixture identity

| Item | Observed value | Result |
|---|---:|---|
| Source files | `s0017lre.hea`, `s0017lre.dat`, `s0017lre.xyz` | PASS |
| Canonical record ID | `8b6ae9a2-3874-4c14-b45b-8abe8ecf26b3` | PASS |
| ECG database ID | `ecg-c157db02` | PASS |
| Upload ID | `7889469a-d244-4a7f-89ab-a59aab2fc7a3` | PASS |
| Processing ID | `3dc0954a-0631-44f5-84ad-ed9221a48d58` | PASS |
| Parser / format | `WFDBParser` / `WFDB` | PASS |
| Validation | `WARNING` only for absent source patient metadata | PASS WITH WARNING |

### Signal preservation

| Check | Source | Canonical/stored | Result |
|---|---:|---:|---|
| Sampling rate | 1,000 Hz | 1,000 Hz | PASS |
| Samples per lead | 115,200 | 115,200 | PASS |
| Duration | 115.2 s | 115.2 s | PASS |
| Lead count | 15 | 15 | PASS |
| Leads | I, II, III, aVR, aVL, aVF, V1–V6, X, Y, Z | same canonical order | PASS |
| Units | mV for every WFDB signal | mV | PASS |
| NPZ matrix | source `p_signal` shape `(115200,15)` | stacked NPZ `(115200,15)` | PASS |
| NPZ values | WFDB physical values | `array_equal=true`; max absolute difference `0.0` | PASS |
| CSV dimensions | 115,200 rows of signal | `(115200,17)` including index/time | PASS |
| CSV signals | WFDB physical values | max absolute difference `0.0` for fixture | PASS |
| CSV index/time | expected index and `index/1000` | exact for fixture | PASS |
| Raw files | original SHA-256 | stored raw SHA-256 matches for all 3 files | PASS |

The CSV serializer uses six decimal places. It happened to be lossless for this fixture, but NPZ is the authoritative binary numeric artifact and should remain the downstream source when arbitrary higher-precision input is involved.

### Durable artifacts

The current artifact manifest contains 16 mandatory entries and all checksums verified:

- `raw/s0017lre.hea`, `.dat`, `.xyz`
- `waveform/waveform.npz`, `waveform.csv`, `waveform_meta.json`
- patient, ECG, clinical, device, quality, annotation and source metadata JSON
- `manifest/manifest.json`
- `preprocessing/preprocessed.npz`, `preprocessing/preprocessing_report.json`

`preprocessed.npz` contains all 15 leads, each with shape `(115200,)`. The preprocessing report records 139 accepted beats, quality score `0.12072024544664771`, and `low_snr`. This differs from the SP result’s 138 R peaks because these are two distinct detector/preprocessing paths; the report correctly labels ingestion quality as ingestion-derived and SP beat counts as SP-derived.

## 7. SP Output Inventory

Runtime source: `WaveformReader` output from the canonical NPZ above, passed to `app.signal_processing.analysis.analyze_waveform(..., 1000.0)`. Result: reference lead II, preprocessing `success`, 15 analyzed leads, 138 R peaks, 228 metric dictionary entries.

The tables use field-family notation only where it exhaustively expands a fixed set of concrete keys. `{L15}` means `I, II, III, AVR, AVL, AVF, V1, V2, V3, V4, V5, V6, X, Y, Z`. `{L12}` means the same set without X/Y/Z. Therefore every emitted key is inventoried, not sampled.

### Result envelope (4 fields)

| Field | Type | Source | Meaning | Units | E2E example |
|---|---|---|---|---|---|
| `reference_lead` | string | `analyze_waveform` | lead used for reference-lead modules | lead code | `II` |
| `preprocessing_status` | string | `_preprocess_leads` / `analyze_waveform` | all/partial/no lead preprocessing success | status | `success` |
| `leads_analyzed` | tuple[string] | `analyze_waveform` | successfully preprocessed leads | lead codes | all 15 |
| `r_peak_count` | integer | `analyze_qrs` return peaks | number of reference-lead R peaks | beats | `138` |

### Metrics dictionary (228 fields)

| Concrete field(s) | Count | Type | Source function | Meaning | Units | E2E example |
|---|---:|---|---|---|---|---|
| `P_Duration_{L15}_ms` | 15 | float/NaN | `analyze_pwave` | per-lead mean P duration | ms | II `86.1231884057971`; I `100.6159420289855` |
| `P_Wave_Dispersion_ms` | 1 | float/NaN | `analyze_pwave` | max–min valid per-lead P duration | ms | `43.97826086956521` |
| `P_Duration_mean_ms` | 1 | float/NaN | `analyze_pwave` | reference-lead mean P duration | ms | `86.1231884057971` |
| `P_Duration_std_ms` | 1 | float/NaN | `analyze_pwave` | reference-lead P-duration standard deviation | ms | `34.54412278260335` |
| `P_Wave_Count` | 1 | integer | `analyze_pwave` | accepted P-wave durations | beats | `138` |
| `QRS_Duration_median_ms` | 1 | float/NaN | `analyze_qrs` | median valid QRS duration | ms | `82.0` |
| `QRS_Duration_mean_ms` | 1 | float/NaN | `analyze_qrs` | mean valid QRS duration | ms | `81.90579710144928` |
| `QRS_Duration_std_ms` | 1 | float/NaN | `analyze_qrs` | QRS-duration standard deviation | ms | `0.833081…` |
| `QRS_Valid_Beat_Count` | 1 | integer | `analyze_qrs` | beats with valid QRS delineation | beats | `138` |
| `R_Peak_Count` | 1 | integer | `analyze_qrs` | detected R peaks | beats | `138` |
| `R_Amplitude_median` | 1 | float/NaN | `analyze_qrs` | median R amplitude | source signal unit | `0.26506985718318576` |
| `R_Amplitude_mean` | 1 | float/NaN | `analyze_qrs` | mean R amplitude | source signal unit | `0.26434073776233935` |
| `Heart_Rate_bpm` | 1 | float/NaN | `analyze_qrs` | mean heart rate from R peaks | bpm | `72.28915662650603` |
| `QRS_QC_Status` | 1 | string | `analyze_qrs` | QRS result QC state | status | `Valid` |
| `QRS_Delineation_Method` | 1 | string | `analyze_qrs` | selected delineation method | identifier | `prominence` |
| `QRS_Duration_min_ms` | 1 | float/NaN | `analyze_qrs` | minimum valid QRS duration | ms | `80.0` |
| `QRS_Duration_max_ms` | 1 | float/NaN | `analyze_qrs` | maximum valid QRS duration | ms | `84.0` |
| `T_Duration_{L15}_ms` | 15 | float/NaN | `analyze_twave` | per-lead mean T duration | ms | II `148.1818181818182`; some leads NaN |
| `T_Late_RMS_{L15}_mV` | 15 | float/NaN | `analyze_twave` | late-T RMS amplitude | mV | real per-lead values emitted |
| `T_Late_PTP_{L15}_mV` | 15 | float/NaN | `analyze_twave` | late-T peak-to-peak amplitude | mV | real per-lead values emitted |
| `T_Late_Flag_Rate_{L15}` | 15 | float/NaN | `analyze_twave` | fraction of beats flagged by module | ratio | real per-lead values emitted |
| `T_Wave_Dispersion_ms` | 1 | float/NaN | `analyze_twave` | max–min valid T duration | ms | `52.291139240506325` |
| `Avg_QT_{L12}_ms` | 12 | float/NaN | `analyze_qt` | mean QT by lead | ms | II `401.2421875`; range `393.382…–429.909…` |
| `Avg_RR_{L12}_ms` | 12 | float/NaN | `analyze_qt` | mean RR by lead | ms | II `831.0078125` |
| `Avg_QTc_Bazett_{L12}_ms` | 12 | float/NaN | `analyze_qt` | mean Bazett-corrected QT by lead | ms | II `440.1685567499637` |
| `Avg_QTc_Fridericia_{L12}_ms` | 12 | float/NaN | `analyze_qt` | mean Fridericia-corrected QT by lead | ms | II `426.78199214607935` |
| `Beats_{L12}` | 12 | integer | `analyze_qt` | valid QT beats by lead | beats | lead II valid-beat set used for aggregate |
| `Avg_Tpe_{L12}_ms` | 12 | float/NaN | `analyze_qt` | mean Tpeak–Tend by lead | ms | II `77.4765625` |
| `Avg_Tpe_Qt_ratio_{L12}` | 12 | float/NaN | `analyze_qt` | per-lead Tpe/QT ratio | ratio | II `0.19750979651166747` |
| `QT_max_{L12}_ms` | 12 | float/NaN | `analyze_qt` | maximum accepted QT by lead | ms | II `467.0` |
| `QT_min_{L12}_ms` | 12 | float/NaN | `analyze_qt` | minimum accepted QT by lead | ms | II `372.0` |
| `QT_disp_{L12}_ms` | 12 | float/NaN | `analyze_qt` | within-lead max–min QT | ms | II `95.0` |
| `QT_max_global_ms` | 1 | float/NaN | `analyze_qt` | maximum QT across leads | ms | `483.0` |
| `QT_min_global_ms` | 1 | float/NaN | `analyze_qt` | minimum QT across leads | ms | `285.0` |
| `QT_dispersion_global_ms` | 1 | float/NaN | `analyze_qt` | global max–min QT | ms | `198.0` |
| `Avg_Tpe_Qt_ratio_GLOBAL` | 1 | float/NaN | `analyze_qt` | aggregate Tpe/QT ratio | ratio | `0.21462137140728518` |
| `Filtered_P_Duration_ms` | 1 | float/NaN | `analyze_p_saecg` | filtered P duration | ms | `39.0` |
| `RMS20_mV` | 1 | float/NaN | `analyze_p_saecg` | terminal 20 ms RMS | mV | `0.004165` |
| `LAS20_ms` | 1 | float/NaN | `analyze_p_saecg` | low-amplitude terminal P duration | ms | `3.0` |
| `P_SAECG_SNR_dB` | 1 | float/NaN | `analyze_p_saecg` | P-SAECG averaged-beat SNR | dB | `6.804593174152308` |
| `P_SAECG_Beats_Used` | 1 | integer | `analyze_p_saecg` | beats retained in P-SAECG average | beats | `138` |
| `QRS_SAECG_Beats_Extracted` | 1 | integer | `analyze_qrs_saecg` | candidate QRS beats | beats | `138` |
| `QRS_SAECG_Beats_Used` | 1 | integer | `analyze_qrs_saecg` | retained QRS beats | beats | `138` |
| `QRS_SAECG_Beats_Rejected` | 1 | integer | `analyze_qrs_saecg` | rejected QRS beats | beats | `0` |
| `QRS_SAECG_SNR_dB` | 1 | float/NaN | `analyze_qrs_saecg` | QRS-SAECG averaged-beat SNR | dB | `14.115508199208062` |
| `Filtered_QRS_Duration_ms` | 1 | float/NaN | `analyze_qrs_saecg` | filtered QRS duration | ms | `89.0` |
| `QRS_RMS40_mV` | 1 | float/NaN | `analyze_qrs_saecg` | terminal 40 ms RMS | mV | `0.09494367097539111` |
| `QRS_LAS40_ms` | 1 | float/NaN | `analyze_qrs_saecg` | low-amplitude terminal QRS duration | ms | `0.0` |

Count check: P 19 + QRS 12 + T 61 + QT 124 + P-SAECG 5 + QRS-SAECG 7 = **228** metrics.

## 8. SP → Report Mapping Matrix

Status definitions are exactly those requested: **A MAPPED_TO_REPORT**, **B MAPPED_TO_TECHNICAL_APPENDIX**, **C INTENTIONALLY_NOT_EXPOSED**, **D LOST / UNMAPPED**, **E INCORRECTLY_RECALCULATED**. No field was found in category E. This matrix is exhaustive via the same concrete field-family expansion used above.

| SP field(s) | GenerationContext field | Report location | Transformation | Status | Evidence |
|---|---|---|---|---|---|
| `reference_lead` | `ecg_parameters.reference_lead` | Technical Appendix | string copy | B | `_ecg_parameters`; technical builder |
| `preprocessing_status` | `signal_quality_metrics.preprocessing_status` | Technical Appendix | string copy | B | `_signal_quality_metrics` |
| `leads_analyzed` | `signal_quality_metrics.leads_analyzed` | Technical Appendix | list/join only | B | same |
| `r_peak_count` | `signal_quality_metrics.r_peak_count` | Technical Appendix | integer formatting | B | same |
| `P_Duration_{L15}_ms` | none except aggregate | none | none | D | builder only requests `P_Duration_mean_ms` |
| `P_Wave_Dispersion_ms` | `clinical_measurements.p_wave_dispersion_ms` | Atrial, repolarization appendix measurement set | integer display rounding | A | `_clinical_measurements` and section builders |
| `P_Duration_mean_ms` | `clinical_measurements.p_duration_ms` | Atrial / measurement appendix | integer display rounding | A | same |
| `P_Duration_std_ms`, `P_Wave_Count` | none | none | none | D | no mapping key |
| `QRS_Duration_median_ms` | `ecg_parameters.qrs_duration_median_ms` | Rhythm, Conventional, Technical measurement inventory | integer display rounding | A | `_ecg_parameters` and builders |
| `QRS_Duration_mean_ms` | `ecg_parameters.qrs_duration_mean_ms` | none | copied to context only | D | no section-builder read |
| `QRS_Duration_std_ms`, `QRS_Valid_Beat_Count`, `R_Amplitude_median`, `R_Amplitude_mean`, `QRS_Duration_min_ms`, `QRS_Duration_max_ms` | none | none | none | D | no mapping key |
| `R_Peak_Count` | none; envelope `r_peak_count` is used instead | none directly | redundant count not selected | D | `_signal_quality_metrics` uses result attribute |
| `Heart_Rate_bpm` | `ecg_parameters.heart_rate_bpm` | Rhythm, Conventional, Technical measurement inventory | integer display rounding | A | direct mapping |
| `QRS_QC_Status` | `signal_quality_metrics.qrs_qc_status` | Technical Appendix | string copy | B | direct mapping |
| `QRS_Delineation_Method` | `signal_quality_metrics.qrs_delineation_method` | Technical Appendix | string copy | B | direct mapping |
| `T_Duration_{L15}_ms`, `T_Late_RMS_{L15}_mV`, `T_Late_PTP_{L15}_mV`, `T_Late_Flag_Rate_{L15}` | none | none | none | D | no mapping keys |
| `T_Wave_Dispersion_ms` | `ecg_parameters.t_wave_dispersion_ms` | Repolarization / Technical measurement inventory | integer display rounding | A | direct mapping |
| `Avg_QT_II_ms` | `ecg_parameters.qt_interval_ms` | Conventional, Repolarization, Technical measurement inventory | reference-lead selection + rounding | A | E2E reference lead II |
| `Avg_RR_II_ms` | `ecg_parameters.rr_interval_ms` | Rhythm, Conventional, Technical measurement inventory | reference-lead selection + rounding | A | same |
| `Avg_QTc_Bazett_II_ms` | `ecg_parameters.qtc_bazett_ms` | Rhythm, Conventional, Repolarization, Technical inventory | reference-lead selection + rounding | A | same |
| `Avg_QTc_Fridericia_II_ms` | `ecg_parameters.qtc_fridericia_ms` | Technical measurement inventory | reference-lead selection + rounding | A | same |
| `Avg_Tpe_II_ms` | `ecg_parameters.tpe_ms` | Repolarization / Technical inventory | reference-lead selection + rounding | A | same |
| The corresponding five fields for `{L12}` except active reference lead II | none for this E2E execution | none | none | D | adapter dynamically selects only `result.reference_lead` |
| `Beats_{L12}` | none | none | none | D | no mapping key |
| `Avg_Tpe_Qt_ratio_{L12}` | none | none | none | D | no mapping key |
| `QT_max_{L12}_ms`, `QT_min_{L12}_ms`, `QT_disp_{L12}_ms` | none | none | none | D | no mapping key |
| `QT_max_global_ms`, `QT_min_global_ms` | none | none | none | D | no mapping key |
| `QT_dispersion_global_ms` | `ecg_parameters.qt_dispersion_global_ms` | Repolarization / Technical inventory | integer display rounding | A | direct mapping |
| `Avg_Tpe_Qt_ratio_GLOBAL` | `ecg_parameters.tpe_qt_ratio_global` | none | copied to context only | D | no section-builder read |
| `Filtered_P_Duration_ms` | `clinical_measurements.filtered_p_duration_ms` | Atrial / Technical measurement inventory | integer display rounding | A | direct mapping |
| `RMS20_mV` | `clinical_measurements.rms20_uv` | Atrial / Technical measurement inventory | **×1000 mV→µV**, 1-decimal display | A | `_to_uv()` |
| `LAS20_ms` | `clinical_measurements.las20_ms` | Atrial / Technical measurement inventory | integer display rounding | A | direct mapping |
| `P_SAECG_SNR_dB`, `P_SAECG_Beats_Used` | `beat_selection.p_saecg_*` | Technical Appendix | SNR 1-decimal display; integer beats | B | `_beat_selection` |
| `QRS_SAECG_Beats_Extracted`, `...Used`, `...Rejected`, `QRS_SAECG_SNR_dB` | `beat_selection.qrs_saecg_*` | Technical Appendix | display formatting only | B | `_beat_selection` |
| `Filtered_QRS_Duration_ms` | `clinical_measurements.filtered_qrs_duration_ms` | Ventricular / Technical inventory | integer display rounding | A | direct mapping |
| `QRS_RMS40_mV` | `clinical_measurements.rms40_uv` | Ventricular / Technical inventory | **×1000 mV→µV**, 1-decimal display | A | `_to_uv()` |
| `QRS_LAS40_ms` | `clinical_measurements.las40_ms` | Ventricular / Technical inventory | integer display rounding | A | direct mapping |

No emitted field is category C because the current source does not contain an explicit policy enumerating the unused numeric fields as intentionally excluded. The audit therefore conservatively classifies those values as D rather than inferring intent. Clinical classifications, interpretations and decision limits are intentionally not exposed, but they are not SP output fields in this implementation and therefore are not rows in this 228-field mapping.

## 9. Exact Value Lineage

Generated-report evidence: ECG `ecg-c157db02`, generation job `rgj-6cd37ca994e0`, report `grp-473a507d6dd8`, canonical record `8b6ae9a2-3874-4c14-b45b-8abe8ecf26b3`.

| Measurement | SP raw | GenerationContext | JSON/HTML/PDF | Transformation | Result |
|---|---:|---:|---:|---|---|
| Heart rate | 72.28915662650603 bpm | 72.28915662650603 | 72 bpm | integer presentation rounding | PASS |
| RR | 831.0078125 ms | 831.0078125 | 831 ms | integer presentation rounding | PASS |
| QRS median | 82.0 ms | 82.0 | 82 ms | integer presentation formatting | PASS |
| QT | 401.2421875 ms | 401.2421875 | 401 ms | integer presentation rounding | PASS |
| QTc Bazett | 440.1685567499637 ms | 440.1685567499637 | 440 ms | integer presentation rounding | PASS |
| QTc Fridericia | 426.78199214607935 ms | 426.78199214607935 | 427 ms where displayed | integer presentation rounding | PASS |
| Tpeak–Tend | 77.4765625 ms | 77.4765625 | 77 ms | Python `round`, ties not implicated | PASS |
| Global QT dispersion | 198.0 ms | 198.0 | 198 ms | integer presentation formatting | PASS |
| T-wave dispersion | 52.291139240506325 ms | same | 52 ms | integer presentation rounding | PASS |
| P duration | 86.1231884057971 ms | same | 86 ms | integer presentation rounding | PASS |
| P dispersion | 43.97826086956521 ms | same | 44 ms | integer presentation rounding | PASS |
| Filtered P duration | 39.0 ms | 39.0 | 39 ms | integer formatting | PASS |
| LAS20 | 3.0 ms | 3.0 | 3 ms | integer formatting | PASS |
| RMS20 | 0.004165 mV | 4.165 µV | 4.2 µV | explicit ×1000, then one decimal | PASS |
| Filtered QRS | 89.0 ms | 89.0 | 89 ms | integer formatting | PASS |
| LAS40 | 0.0 ms | 0.0 | 0 ms | genuine SP zero, not fallback | PASS |
| RMS40 | 0.09494367097539111 mV | 94.94367097539111 µV | 94.9 µV | explicit ×1000, then one decimal | PASS |

The PDF text and HTML show the same formatted values as the section models/summary JSON. No hardcoded replacement or unexplained substitution was found.

## 10. Reporting Calculation Audit

| Reporting operation | Location | Classification | Result |
|---|---|---|---|
| RMS20/RMS40 `mV * 1000` | `context/signal_processing_builder.py::_to_uv` | legitimate unit conversion | PASS |
| `_number()` integer/decimal formatting | `builders/section_builders.py` | presentation rounding only | PASS |
| recording duration to `mm:ss` | `builders/section_builders.py::_duration` | nonclinical presentation formatting | PASS |
| dates/times formatting | `_moment` | presentation formatting | PASS |
| HR/RR/QRS/QT/QTc/Tpe/dispersion/P/SAECG | context builder lookup + section builder formatting | directly consumes SP output | PASS |
| PR, rhythm, axes | unavailable values | no calculation or substitution | PASS |
| rhythm/clinical flags/interpretation/recommendations | governed unavailable state | no classification formula | PASS |
| report progress percentage / job duration | workflow/execution models | operational, not clinical | PASS |
| SVG grid/window index calculations | visualization modules | display geometry, not clinical measurement | PASS |

Searches across `backend/app/reporting` found no independent clinical formula for the audited measurements. QTc formulas exist only in `backend/app/signal_processing/qt_module.py`, the authoritative SP package.

## 11. Missing Output Behavior

`SignalProcessingResult.get()` returns `None` for a missing key or floating NaN. `_measurement()` passes `None` through to an unavailable `ReportValue`; it does not convert it to zero. Explicitly unproduced fields such as rhythm, PR and axes use “Not produced by Signal Processing.” Clinical outputs use “Clinical result unavailable: approved decision limits are not configured.” Waveform annotation similarly remains unavailable.

Runtime checks show `QRS_LAS40_ms = 0.0` is preserved as 0 because SP actually emitted zero. This is correct lineage, not an unavailable-value default. The P-SAECG module itself also has algorithm-defined zero-return branches; these originate in SP and reporting must not reinterpret them.

Unexpected waveform/SP exceptions in `build_signal_processing_outputs()` return `SignalProcessingOutputs.awaiting_signal_processing()`. This behavior neither invents values nor diagnoses the ECG, but it makes an operational SP failure nonfatal to report generation. Logs are therefore essential evidence when an all-awaiting report appears.

Clinical interpretation, risk, VLP/ALP verdicts, flags, decision limits and recommendations are not generated because no approved authoritative clinical source exists. **Status: PASS.**

## 12. End-to-End Trace

```text
s0017lre.hea + s0017lre.dat + s0017lre.xyz
  PASS -> UploadOrchestrator session 7889469a-d244-4a7f-89ab-a59aab2fc7a3
  PASS -> FormatDetector: WFDB
  PASS -> WFDBParser (wfdb.rdrecord): 15 × 115200, 1000 Hz, mV
  PASS -> metadata extraction + validation (WARNING: source patient metadata absent)
  PASS -> canonical ECGRecord 8b6ae9a2-3874-4c14-b45b-8abe8ecf26b3
  PASS -> raw + waveform + metadata storage
  PASS -> artifact_manifest.json, 16 mandatory checksums verified
  PASS -> ingestion preprocessing artifacts (all 15 leads)
  PASS -> DB ECG ecg-c157db02
  PASS -> ECGArtifactRepository.load_bundle
  PASS -> WaveformReader.read_from_artifacts(waveform.npz)
  PASS -> SP-owned preprocess_signal on 15 leads
  PASS -> analyze_waveform(), reference II, 138 R peaks, 228 metrics
  PASS -> SignalProcessingResult
  PASS -> build_signal_processing_outputs()
  PASS -> GenerationContext.signal_processing
  PASS -> SummaryReportBuilder / DetailedReportBuilder
  PASS -> generation job rgj-6cd37ca994e0
  PASS -> generated report grp-473a507d6dd8
  PASS -> detailed_report.html
  PASS -> detailed_report.pdf (8 A4 pages in current validated artifact)
```

## 13. Test Results

### Targeted audit suite

Command scope: detector, parsers, ingestion, storage, preprocessing, P0/idempotency remediation, SP mapping, artifact repository and context loader.

```text
110 passed, 0 failed, 1082 warnings in 15.17s
```

### Complete relevant ingestion/reporting suite

Command scope: ECG domain/builder, format detection, ingestion, metadata/validation, remediation, all parsers, preprocessing, storage, upload orchestration, and the full `backend/tests/reporting` directory.

```text
390 passed, 0 failed, 13697 warnings in 194.45s (0:03:14)
```

The warning count is dominated by repeated third-party warnings:

- NumPy “degrees of freedom <= 0” for small/empty slices in synthetic fixtures.
- NeuroKit2 mean-of-empty-slice warnings.
- NeuroKit2/Pandas chained-assignment future and copy warnings.
- A few all-NaN preprocessing warnings in deliberate undrawable-waveform tests.
- Pydicom deprecations and one Starlette/AnyIO deprecation.

Warnings did not fail tests, but they are not treated as evidence-free noise; dependency evolution could change behavior and should be monitored.

## 14. Defect Register

| ID | Severity | Finding | Evidence | Impact | Status |
|---|---|---|---|---|---|
| DI-001 | P1 High | Frontend advertises/accepts PDF, EDF and image files unsupported by canonical backend | upload pages vs detector/registry | users can select formats guaranteed to fail asynchronously | FAIL |
| DI-002 | P1 High | SCP-ECG advertised but `.scp/.scp-ecg` absent from chooser | upload page `accept` vs detector | advertised supported format cannot normally be selected | FAIL |
| DI-003 | P2 Medium | UI says max 50MB; backend limit is 200 MiB | upload pages vs `MAX_UPLOAD_SIZE_BYTES` | inconsistent expectation and client-side workflow | FAIL |
| DI-004 | P2 Medium | XML/DICOM/SCP claims exceed verified interoperability scope | parser constraints and synthetic-only tests | vendor files may fail despite generic format label | PASS WITH WARNING |
| DI-005 | P2 Medium | Unexpected SP error degrades to all-awaiting and report may complete | `build_signal_processing_outputs()` broad exception fallback | report success can mask SP operational failure | PASS WITH WARNING |
| DI-006 | P2 Medium | Duplicate filename/oversize staging errors lack explicit HTTP mapping | router and `main.py` handler inspection | likely 500 rather than governed 4xx; exact runtime behavior not tested | NOT VERIFIED |
| DI-007 | P3 Low | Many SP diagnostic/per-lead fields are not exposed or persisted in report context | exhaustive mapping table | loss of diagnostic provenance/inspectability; displayed patient-level values unaffected | PASS WITH WARNING |
| DI-008 | P3 Low | Two preprocessing/detector paths yield 139 ingestion beats vs 138 SP R peaks | preprocessing report and SP runtime | potential user confusion if provenance labels are ignored | PASS WITH WARNING |
| DI-009 | P3 Low | SP README contains stale “awaiting” statements after current unavailable-state integration | README vs current builder/runtime report | documentation inconsistency only | PASS WITH WARNING |
| DI-010 | P3 Low | Scientific dependency warnings are extremely numerous | pytest output | upgrade/maintenance risk; no current test failure | PASS WITH WARNING |

No P0 defect was identified. No defect was fixed during this audit.

## 15. Severity Definitions

| Severity | Definition |
|---|---|
| P0 Critical | proven corruption, fabricated clinical output, security/tenant breach, or complete critical-flow failure |
| P1 High | material user-facing or workflow defect likely to prevent a supported clinical operation |
| P2 Medium | important reliability, interoperability, error-governance or observability issue with a workaround or limited scope |
| P3 Low | documentation, maintainability, provenance clarity or future-compatibility concern without current numeric corruption |

## 16. Final Release Assessment

### Overall: PASS WITH WARNING

The verified WFDB path is suitable for continued controlled validation: source signal preservation, canonical storage, manifest integrity, read-back, real SP execution, report mapping and rendered-value lineage all passed. No reporting-side clinical recalculation or fabricated clinical value was found.

This audit does **not** support an unconditional claim that every format advertised in the UI is production-supported. Before a broad-format release claim, correct the frontend/backend contract and validate XML/DICOM/SCP-ECG against an approved representative vendor corpus. Before treating “report completed” as proof that SP completed, address or operationally govern the fail-soft SP state.

Release statements should therefore be scoped as follows:

- **WFDB → canonical artifacts → SP → HTML/PDF:** PASS WITH WARNING.
- **Numeric integrity for the supplied real WFDB fixture:** PASS.
- **All advertised upload formats:** FAIL.
- **Real-world XML/DICOM/SCP vendor interoperability:** NOT VERIFIED.
- **Clinical classification/diagnosis/recommendations:** NOT IMPLEMENTED BY DESIGN; no release claim should imply otherwise.

---

### Evidence boundary

Runtime-verified evidence in this report: supplied WFDB hashes and decoded values, stored artifacts, manifest checksums, preprocessing artifacts, real SP execution, current generated JSON/HTML/PDF, and the two pytest runs. Static-only evidence: exact HTTP response for pre-job duplicate/oversize staging errors and external vendor interoperability. Those items are explicitly marked `NOT VERIFIED` or `PASS WITH WARNING`; they are not promoted to PASS.
