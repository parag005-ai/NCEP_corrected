"""Format Detector.

Purpose:
    Identify which ECG format an uploaded set of files represents
    (Implementation Spec 3.4). The detector only determines the format --
    it never parses waveform or metadata content.

Responsibilities:
    - Inspect uploaded file names, extensions, and light binary/content
      signatures.
    - Determine the ECGFormat shared by the whole upload.

Shall NOT:
    - Parse ECG signals.
    - Validate file contents.

Input:
    A collection of uploaded file paths (one Upload Session).

Output:
    ECGFormat

Exceptions:
    FormatDetectionError -- raised when the files cannot be identified as a
    supported, single, unambiguous format (Business Rule 8.12). This
    includes uploads that mix files belonging to more than one supported
    format (e.g. a WFDB `.hea`/`.dat` pair alongside an unrelated `.csv`
    file) -- such uploads are rejected outright rather than silently
    resolved to whichever format happens to be checked first.
"""

from __future__ import annotations

from pathlib import Path
from collections.abc import Iterable

from app.ecg.constants import ECGFormat
from app.ingestion.exceptions import FormatDetectionError

_DICOM_MAGIC = b"DICM"
_DICOM_PREAMBLE_LEN = 128

# WFDB companion-file extensions that belong to a WFDB recording but do not
# themselves indicate a format on their own (they are meaningless without an
# accompanying .hea header). Excluded from ambiguity checks so a WFDB upload
# whose signal/annotation files happen to share an extension with another
# format's marker never trips a false-positive "mixed format" rejection.
_WFDB_COMPANION_EXTS = {".dat", ".atr", ".qrs", ".ecg", ".xyz"}


def _looks_like_dicom(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            fh.seek(_DICOM_PREAMBLE_LEN)
            return fh.read(len(_DICOM_MAGIC)) == _DICOM_MAGIC
    except OSError:
        return False


def _looks_like_xml(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            head = fh.read(256).lstrip()
        return head.startswith(b"<?xml") or head.startswith(b"<")
    except OSError:
        return False


def _detected_formats(file_list: list[Path]) -> dict[ECGFormat, list[Path]]:
    """Returns every supported format that at least one uploaded file matches.

    Each file is matched by its own marker (extension or binary signature),
    independent of the others -- this is what lets `detect_format` notice
    when an upload contains files belonging to more than one format.
    """
    matches: dict[ECGFormat, list[Path]] = {}

    def add(fmt: ECGFormat, path: Path) -> None:
        matches.setdefault(fmt, []).append(path)

    for path in file_list:
        ext = path.suffix.lower()

        if ext == ".hea":
            add(ECGFormat.WFDB, path)
            continue
        if ext in _WFDB_COMPANION_EXTS:
            # Only meaningful alongside a .hea file; never registers a format
            # by itself, so it cannot cause a false ambiguity match.
            continue
        if ext in (".dcm", ".dicom") or _looks_like_dicom(path):
            add(ECGFormat.DICOM, path)
            continue
        if ext in (".scp", ".scp-ecg"):
            add(ECGFormat.SCP_ECG, path)
            continue
        if ext == ".xml" and _looks_like_xml(path):
            add(ECGFormat.XML, path)
            continue
        if ext == ".csv":
            add(ECGFormat.CSV, path)
            continue

    return matches


def detect_format(files: Iterable[Path]) -> ECGFormat:
    """Detect the ECGFormat represented by a set of uploaded files.

    Raises:
        FormatDetectionError: if no supported format can be identified, or
            if the files belong to more than one supported format.
    """
    file_list = [Path(f) for f in files]
    if not file_list:
        raise FormatDetectionError("No files were provided to the format detector.")

    matches = _detected_formats(file_list)

    if not matches:
        orphaned_companions = [f.name for f in file_list if f.suffix.lower() in _WFDB_COMPANION_EXTS]
        if orphaned_companions:
            raise FormatDetectionError(
                f"{', '.join(orphaned_companions)} belong to a WFDB recording, but no matching .hea "
                "header file was uploaded alongside them -- a WFDB recording cannot be identified "
                "without it. Select the .hea file together with these when uploading."
            )
        raise FormatDetectionError(
            f"Unable to identify a supported ECG format for uploaded files: {[f.name for f in file_list]}"
        )

    if len(matches) > 1:
        detail = ", ".join(
            f"{fmt.value} ({', '.join(p.name for p in paths)})" for fmt, paths in sorted(matches.items())
        )
        raise FormatDetectionError(
            f"Uploaded files belong to more than one ECG format and cannot be processed as a single "
            f"recording: {detail}."
        )

    (source_format,) = matches.keys()
    return source_format
