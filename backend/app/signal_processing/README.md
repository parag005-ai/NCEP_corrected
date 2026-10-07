# Signal Processing (biomedical team's ECG pipeline)

Vendored, unmodified analysis code from the biomedical team's ECG signal
processing pipeline:

- Source: `github.com/22Neuro-Transcend-Discoveries-Pvt-Ltd/NCEP`,
  branch `vaishnavi-kharade`, path `ECG_Pipeline` (the branch's history was
  rewritten and the pipeline moved here from the original `integration/
  ECG_Pipeline` -- same team, same modules, new location), commit
  `7ca6b2e35cb27c6f07f33f825012c5a5a8d1bf66`.
- `qrs_module.py`, `qt_module.py` and `qrs_saecg_module.py` are that
  commit's versions: more defensive formatting/docstrings throughout, and
  for `qrs_saecg_module.py` specifically a real methodology change -- the
  beat-extraction window around each R-peak moved from 200ms/400ms to
  100ms/120ms, with revised QC constants. Verified before adopting it: the
  external interface (function signature, result dict keys) this
  integration depends on is unchanged, so no adapter code needed updating.
  `preprocessing.py`, `p_wave_module.py`, `t_wave_module.py`,
  `p_saecg_module.py` are unchanged from the original delivery.
- Not vendored: that commit also added `average_ecg.py`, `check_saecg.py`,
  `debug_lp.py` -- standalone dev/diagnostic scripts (hardcoded test
  patients, local WFDB file reads, matplotlib plots saved to disk), the
  same batch-file-based pattern as `pipeline.py`/`scoring.py` below, not
  reusable single-record analysis functions. Say so if any of that should
  be ported in too.
- Every module here is untouched analysis logic: no thresholds, no
  classification, no interpretation was added or altered. `analysis.py` is
  the only new file, and it is a pure adapter (waveform format conversion +
  orchestration) -- it contains no clinical logic itself.

## What this integration deliberately does NOT include

Per explicit instruction: anything that requires clinical judgment must come
from the medical team, not be authored here. Specifically excluded:

- **Signal Quality Score** -- the biomedical team's own `scoring.py` marks
  this `"Not Implemented"`; no formula exists anywhere in what was delivered.
- **Normal/Abnormal classification** (`scoring.py`'s 24-metric thresholds) --
  several of its own thresholds are flagged by the team as unconfirmed
  assumptions (sex-dependent QTc cutoff, beat-count cutoffs, range-threshold
  bounds). Not wired in until the medical team confirms them.
- **Clinical interpretation / narrative text** -- the pipeline outputs
  numbers and (unused, for now) flags only. No interpretive sentences are
  generated anywhere in this integration.
- **SAECG on Frank X/Y/Z vector magnitude** -- the delivered modules analyze
  a single reference lead (lead II by default). NCEP's ingested recordings
  do carry X/Y/Z; using vector magnitude instead of a single lead is a
  methodology question for the medical team, not decided here.

These map exactly onto `GenerationContext.signal_processing.clinical_findings`,
which stays `AWAITING_SIGNAL_PROCESSING` -- see `context/loader.py`.

## What this integration does include

Raw, computed measurements only: preprocessing, QRS/P-wave/T-wave/QT/QTc
timing, and the two SAECG late-potential analyses (atrial + ventricular).
These populate `GenerationContext.signal_processing`'s other five sections
(`ecg_parameters`, `clinical_measurements`, `signal_quality_metrics`,
`beat_selection`; `waveform_annotations` stays awaiting -- no plotting code
was delivered), which the report's measurement sections (Rhythm & Intervals,
Conventional Measurements, Atrial Measurements, SAECG Processing/Parameters,
Repolarization) read from. Sections requiring classification or narrative
(Clinical Flags, Clinical Findings, all four `*_INTERPRETATION` sections,
`VLP_VERDICT`, `DOMAIN_EVIDENCE_SUMMARY`, ...) are untouched and still show
the standard "Awaiting Signal Processing Results" placeholder.

## Adapting to NCEP's data model

The biomedical team's `pipeline.py` reads WFDB files from disk and loops over
many patients; NCEP already has one recording's waveform parsed and reusable
in memory (`app.reporting.visualizations.waveform_reader.WaveformReader`).
`analysis.py` mirrors `pipeline.py`'s per-patient logic (same call order,
same reference-lead selection) but takes that already-loaded `WaveformData`
instead of a WFDB path, and normalizes NCEP's lead names (`aVR`/`aVL`/`aVF`)
to the upper-case form (`AVR`/`AVL`/`AVF`) these modules expect.
