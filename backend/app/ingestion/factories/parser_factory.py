"""Parser Factory.

Purpose:
    Select and instantiate the parser responsible for a detected ECG format
    (Implementation Spec 3.5 / 7.5).

Responsibilities:
    - Receive a detected ECGFormat.
    - Return the registered parser instance for that format.

Shall NOT:
    - Parse ECG signals.
    - Detect format.

Input:
    ECGFormat

Output:
    ParserInterface instance

Exceptions:
    UnsupportedFormatError -- raised when no parser is registered for the
    detected format (Parser Extension Policy 10.16: adding a format never
    requires downstream changes, only a new parser plus a registration
    here).
"""

from __future__ import annotations

from app.ecg.constants import ECGFormat
from app.ingestion.exceptions import UnsupportedFormatError
from app.ingestion.parsers.csv.parser import CSVParser
from app.ingestion.parsers.dicom.parser import DICOMParser
from app.ingestion.parsers.scp.parser import SCPParser
from app.ingestion.parsers.wfdb.parser import WFDBParser
from app.ingestion.parsers.xml.parser import XMLParser
from app.interfaces.parser import ParserInterface

_PARSER_REGISTRY: dict[ECGFormat, type[ParserInterface]] = {
    ECGFormat.WFDB: WFDBParser,
    ECGFormat.CSV: CSVParser,
    ECGFormat.XML: XMLParser,
    ECGFormat.DICOM: DICOMParser,
    ECGFormat.SCP_ECG: SCPParser,
}


def get_parser(source_format: ECGFormat) -> ParserInterface:
    """Return a new parser instance for the given detected format.

    Raises:
        UnsupportedFormatError: if no parser is registered for the format.
    """
    parser_cls = _PARSER_REGISTRY.get(source_format)
    if parser_cls is None:
        raise UnsupportedFormatError(f"No parser is registered for format {source_format.value}.")
    return parser_cls()
