## ECGRecord Contract

Every ingestion parser must produce exactly one internal `ECGRecord`.

`ECGRecord` is the only normalized ECG object exchanged between ingestion, validation, preprocessing, analysis, reporting, storage, and background tasks.

Downstream modules must never depend on source-specific concepts such as XML, DICOM, WFDB, SCP-ECG, CSV, or vendor-native structures.

Source-specific parsing details must terminate at the ingestion boundary before an `ECGRecord` is emitted.
