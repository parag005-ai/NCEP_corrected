"""XML Parser.

Purpose:
    Interprets an XML ECG document, extracts waveform and metadata, and
    constructs a ParsedECG (Implementation Spec 10.10).

Supported schema (Phase 1):
    There is no single universal "XML ECG" standard -- vendors diverge
    (HL7 aECG, proprietary MUSE-style exports, SierraECG, etc.). Phase 1
    ships one documented, generic schema (below) as the reference profile.
    No reference dataset was provided for XML during Phase 1, unlike WFDB
    (PTB Diagnostic ECG Database), so this profile is the verifiable
    contract rather than a best-effort guess at a vendor format.

    <ECG>
        <RecordingInfo samplingRateHz="500" units="mV" recordId="..."
                        acquisitionTimestamp="2024-01-01T10:00:00"
                        deviceManufacturer="..." deviceModel="..."
                        gain="..." baseline="..." filterSettings="..."/>
        <Patient patientId="..." name="..." dateOfBirth="1990-01-01"
                 age="34" sex="M" hospital="..." clinician="..."
                 clinicalHistory="..."/>
        <Clinical diagnosis="..." reasonForExamination="..."
                  procedureNotes="..." clinicalComments="...">
            <Medications><Medication>...</Medication></Medications>
        </Clinical>
        <Leads>
            <Lead name="I">0.01,0.02,0.03,...</Lead>
            <Lead name="II">...</Lead>
        </Leads>
        <Annotations>
            <Annotation type="beat" label="N" sampleIndex="120" lead="II"/>
        </Annotations>
    </ECG>

    Additional vendor profiles can be added by extending `_PROFILES` with
    another interpreter callable without modifying downstream modules
    (Parser Extension Policy 10.16).

Shall NOT:
    - Validate the ECG.
    - Filter the signal.
    - Leak XML-specific structures (Element objects, tag names) beyond
      this module.

Input:
    A single uploaded .xml file.

Output:
    ParsedECG

Exceptions:
    MissingRequiredFileError, MalformedFileError, UnmappableLeadError
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from app.ecg.constants import DEFAULT_SIGNAL_UNITS, ECGFormat, CanonicalLead
from app.ecg.lead_mapping import resolve_canonical_lead
from app.ecg.models.annotations import Annotation, AnnotationType
from app.ecg.models.waveform import LeadSignal, Waveform
from app.ingestion.exceptions import MalformedFileError, MissingRequiredFileError
from app.ingestion.parsers.shared.parsed_ecg import ParsedECG
from app.interfaces.parser import ParserInterface


class XMLParser(ParserInterface):
    """Parses XML ECG documents into ParsedECG using the generic NCEP XML schema."""

    format = ECGFormat.XML

    def can_parse(self, files: Sequence[Path]) -> bool:
        return any(Path(f).suffix.lower() == ".xml" for f in files)

    def parse(self, files: Sequence[Path]) -> ParsedECG:
        file_list = [Path(f) for f in files]
        xml_files = [f for f in file_list if f.suffix.lower() == ".xml"]

        if not xml_files:
            raise MissingRequiredFileError("XML parsing requires at least one .xml file.")
        if len(xml_files) > 1:
            raise MalformedFileError(
                "Multiple .xml files were provided; one XML upload must represent exactly one recording."
            )
        xml_file = xml_files[0]

        try:
            root = ET.parse(xml_file).getroot()
        except ET.ParseError as exc:
            raise MalformedFileError(f"Failed to parse XML file {xml_file.name}: {exc}") from exc

        leads_el = root.find("Leads")
        if leads_el is None or not len(leads_el):
            raise MalformedFileError(f"XML file {xml_file.name} contains no <Leads> data.")

        leads: dict[CanonicalLead, LeadSignal] = {}
        for lead_el in leads_el.findall("Lead"):
            name = lead_el.get("name")
            if not name:
                raise MalformedFileError(f"<Lead> element missing 'name' attribute in {xml_file.name}.")
            canonical = resolve_canonical_lead(name)
            if canonical in leads:
                raise MalformedFileError(f"Duplicate canonical lead {canonical.value} in {xml_file.name}.")
            samples = self._parse_samples(lead_el.text or "", xml_file, name)
            leads[canonical] = LeadSignal(canonical, samples)

        recording_info_el = root.find("RecordingInfo")
        sampling_rate_hz = self._require_float(recording_info_el, "samplingRateHz", xml_file)
        units = (recording_info_el.get("units") if recording_info_el is not None else None) or DEFAULT_SIGNAL_UNITS

        waveform = Waveform(leads=leads, sampling_rate_hz=sampling_rate_hz, units=units)

        raw_recording_info = dict(recording_info_el.attrib) if recording_info_el is not None else {}

        patient_el = root.find("Patient")
        raw_patient_info = dict(patient_el.attrib) if patient_el is not None else {}

        clinical_el = root.find("Clinical")
        raw_clinical_info: dict[str, object] = dict(clinical_el.attrib) if clinical_el is not None else {}
        if clinical_el is not None:
            medications_el = clinical_el.find("Medications")
            if medications_el is not None:
                raw_clinical_info["medications"] = [
                    (med.text or "").strip() for med in medications_el.findall("Medication") if (med.text or "").strip()
                ]

        annotations = self._parse_annotations(root.find("Annotations"))

        return ParsedECG(
            source_format=ECGFormat.XML,
            source_files=tuple(file_list),
            parser_name="XMLParser",
            waveform=waveform,
            raw_patient_info=raw_patient_info,
            raw_recording_info=raw_recording_info,
            raw_clinical_info=raw_clinical_info,
            raw_device_info={},
            raw_quality_info={},
            raw_annotations=annotations,
        )

    # -- internal helpers ---------------------------------------------------

    @staticmethod
    def _parse_samples(text: str, xml_file: Path, lead_name: str) -> np.ndarray:
        raw_values = [v for v in text.replace(",", " ").split() if v]
        if not raw_values:
            raise MalformedFileError(f"Lead {lead_name!r} in {xml_file.name} contains no sample values.")
        try:
            return np.array([float(v) for v in raw_values], dtype=np.float64)
        except ValueError as exc:
            raise MalformedFileError(f"Lead {lead_name!r} in {xml_file.name} contains non-numeric samples: {exc}") from exc

    @staticmethod
    def _require_float(element: ET.Element | None, attribute: str, xml_file: Path) -> float:
        if element is None or element.get(attribute) is None:
            raise MalformedFileError(
                f"XML file {xml_file.name} is missing required <RecordingInfo {attribute}=...> attribute."
            )
        try:
            return float(element.get(attribute))
        except ValueError as exc:
            raise MalformedFileError(f"XML file {xml_file.name} has a non-numeric {attribute} value: {exc}") from exc

    @staticmethod
    def _parse_annotations(annotations_el: ET.Element | None) -> tuple[Annotation, ...]:
        if annotations_el is None:
            return ()
        annotations: list[Annotation] = []
        for ann_el in annotations_el.findall("Annotation"):
            raw_type = ann_el.get("type", "event").lower()
            try:
                annotation_type = AnnotationType(raw_type)
            except ValueError:
                annotation_type = AnnotationType.VENDOR
            lead_name = ann_el.get("lead")
            annotations.append(
                Annotation(
                    annotation_type=annotation_type,
                    label=ann_el.get("label", ""),
                    sample_index=(int(ann_el.attrib["sampleIndex"]) if "sampleIndex" in ann_el.attrib else None),
                    time_offset_seconds=(
                        float(ann_el.attrib["timeOffsetSeconds"]) if "timeOffsetSeconds" in ann_el.attrib else None
                    ),
                    lead=resolve_canonical_lead(lead_name) if lead_name else None,
                    source="xml",
                )
            )
        return tuple(annotations)
