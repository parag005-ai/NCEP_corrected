# SP Report Output Governance Audit

## 1. Purpose

This document audits the current NCEP/CardioNexus path from `SignalProcessingResult` into report context and rendered reports. It does not change SP, report mappings, report layout, clinical rules, or failure semantics.

The companion machine-readable matrix is [`SP_REPORT_OUTPUT_GOVERNANCE.matrix.json`](SP_REPORT_OUTPUT_GOVERNANCE.matrix.json). It contains one explicit object for each of the 228 metric keys produced by the current SP implementation.

**Audit outcome:** governance is incomplete and materially ambiguous. Per the task instruction, implementation stops at this matrix. No mapping change is safe until the unresolved policy decisions in sections 6 and 10 are approved.

## 2. Files inspected

- `backend/app/signal_processing/analysis.py`
- `backend/app/signal_processing/p_wave_module.py`
- `backend/app/signal_processing/qrs_module.py`
- `backend/app/signal_processing/t_wave_module.py`
- `backend/app/signal_processing/qt_module.py`
- `backend/app/signal_processing/p_saecg_module.py`
- `backend/app/signal_processing/qrs_saecg_module.py`
- `backend/app/signal_processing/README.md`
- `backend/app/reporting/context/signal_processing_builder.py`
- `backend/app/reporting/context/generation_context.py`
- `backend/app/reporting/constants.py`
- `backend/app/reporting/builders/section_builders.py`
- `backend/app/reporting/builders/report_builders.py`
- `backend/app/reporting/builders/sections.py`
- `backend/app/reporting/builders/serialization.py`
- `backend/app/reporting/models/*`
- `backend/app/reporting/repositories/*`
- `backend/app/reporting/orchestrator/*`
- `backend/app/reporting/templates/detailed_report.html.j2`
- `backend/tests/reporting/test_signal_processing_mapping.py`
- `backend/tests/reporting/test_context_loader.py`
- `backend/tests/reporting/test_report_builders.py`
- `backend/tests/reporting/test_summary_contract.py`
- `backend/tests/reporting/test_report_pipeline.py`
- Current real E2E artifacts for ECG `ecg-c157db02` and canonical record `8b6ae9a2-3874-4c14-b45b-8abe8ecf26b3`

## 3. SP output inventory

The authoritative runtime result contains four envelope fields and 228 metric-dictionary fields:

| Output family | Count | Source |
|---|---:|---|
| P-wave | 19 | `analyze_pwave()` |
| QRS | 12 | `analyze_qrs()` |
| T-wave | 61 | `analyze_twave()` |
| QT/QTc/Tpe | 124 | `analyze_qt()` |
| P-SAECG | 5 | `analyze_p_saecg()` |
| QRS-SAECG | 7 | `analyze_qrs_saecg()` |
| **Total metrics** | **228** | `SignalProcessingResult.metrics` |

The four envelope fields are `reference_lead`, `preprocessing_status`, `leads_analyzed`, and `r_peak_count`. They are outside the 228 metric count and already reach technical/provenance sections.

Concrete lead sets used by SP:

- 15-lead P/T families: `I, II, III, AVR, AVL, AVF, V1, V2, V3, V4, V5, V6, X, Y, Z`.
- 12-lead QT families: `I, II, III, AVR, AVL, AVF, V1, V2, V3, V4, V5, V6`.

The JSON matrix expands every family into its concrete keys. Its object count was checked as exactly 228.

## 4. Category definitions

| Final category | Intended meaning |
|---|---|
| `REPORT` | A governed clinical/technical measurement rendered in an existing report section. |
| `TECHNICAL_APPENDIX` | Technical, QC, method, beat-selection, or provenance information rendered outside the main clinical narrative. |
| `PERSISTED_ONLY` | A value durably stored in a defined SP-result persistence record but not rendered. |
| `INTENTIONALLY_NOT_EXPOSED` | A reviewed field with an explicit documented reason not to persist or render it. |

`UNRESOLVED_CURRENT_STATE` appears only in the audit matrix. It is not a proposed final governance category. It records that the current code supplies no evidence sufficient to choose one of the four final categories.

## 5. Current-state complete matrix summary

| Current audit classification | Count | Explanation |
|---|---:|---|
| `REPORT` | 17 | Currently rendered measurements with direct SP lineage. |
| `TECHNICAL_APPENDIX` | 8 | Currently rendered QC/method/beat-selection metrics. |
| `PERSISTED_ONLY` | 0 | No durable full-SP-result persistence layer exists. |
| `INTENTIONALLY_NOT_EXPOSED` | 0 | No source-level 228-field governance registry documents deliberate exclusions. |
| `UNRESOLVED_CURRENT_STATE` | 203 | Not rendered/persisted, or transiently mapped without a destination. |
| **Total** | **228** | Exact machine-readable expansion in the companion JSON. |

### Family-level human-readable matrix

| SP output family | Count | Current destination | Unit | Transformation | Current status |
|---|---:|---|---|---|---|
| `P_Duration_{15 leads}_ms` | 15 | only `P_Duration_mean_ms` is rendered; individual leads absent | ms | none | 15 unresolved |
| `P_Wave_Dispersion_ms` | 1 | atrial/main measurement | ms | display rounding | REPORT |
| `P_Duration_mean_ms` | 1 | atrial/main measurement | ms | display rounding | REPORT |
| `P_Duration_std_ms`, `P_Wave_Count` | 2 | none | ms / beats | none | unresolved |
| QRS duration/amplitude/count family | 8 | median rendered; mean context-only; remaining absent | ms / source unit / beats | display rounding only for median | 1 REPORT, 7 unresolved |
| `Heart_Rate_bpm` | 1 | rhythm/conventional/clinical measurement | bpm | display rounding | REPORT |
| `QRS_QC_Status`, `QRS_Delineation_Method` | 2 | quality/technical provenance | status / identifier | direct | TECHNICAL_APPENDIX |
| `QRS_Duration_min_ms`, `QRS_Duration_max_ms` | 2 | none | ms | none | unresolved |
| `T_Duration_{15 leads}_ms` | 15 | none | ms | none | unresolved |
| `T_Late_RMS_{15 leads}_mV` | 15 | none | mV | none | unresolved |
| `T_Late_PTP_{15 leads}_mV` | 15 | none | mV | none | unresolved |
| `T_Late_Flag_Rate_{15 leads}` | 15 | none | ratio | none | unresolved |
| `T_Wave_Dispersion_ms` | 1 | repolarization/main measurement | ms | display rounding | REPORT |
| `Avg_QT_{12 leads}_ms` | 12 | reference lead II rendered | ms | reference-lead selection + rounding | 1 REPORT, 11 unresolved |
| `Avg_RR_{12 leads}_ms` | 12 | reference lead II rendered | ms | reference-lead selection + rounding | 1 REPORT, 11 unresolved |
| `Avg_QTc_Bazett_{12 leads}_ms` | 12 | reference lead II rendered | ms | reference-lead selection + rounding | 1 REPORT, 11 unresolved |
| `Avg_QTc_Fridericia_{12 leads}_ms` | 12 | reference lead II rendered | ms | reference-lead selection + rounding | 1 REPORT, 11 unresolved |
| `Beats_{12 leads}` | 12 | none | beats | none | unresolved |
| `Avg_Tpe_{12 leads}_ms` | 12 | reference lead II rendered | ms | reference-lead selection + rounding | 1 REPORT, 11 unresolved |
| `Avg_Tpe_Qt_ratio_{12 leads}` | 12 | none | ratio | none | unresolved |
| `QT_max_{12 leads}_ms` | 12 | none | ms | none | unresolved |
| `QT_min_{12 leads}_ms` | 12 | none | ms | none | unresolved |
| `QT_disp_{12 leads}_ms` | 12 | none | ms | none | unresolved |
| `QT_max_global_ms`, `QT_min_global_ms` | 2 | none | ms | none | unresolved |
| `QT_dispersion_global_ms` | 1 | repolarization/main measurement | ms | display rounding | REPORT |
| `Avg_Tpe_Qt_ratio_GLOBAL` | 1 | copied to context, not rendered/persisted | ratio | none | unresolved |
| `Filtered_P_Duration_ms`, `RMS20_mV`, `LAS20_ms` | 3 | atrial/main measurements | ms / mV | RMS20 ×1000 to µV; display rounding | REPORT |
| `P_SAECG_SNR_dB`, `P_SAECG_Beats_Used` | 2 | SAECG processing | dB / beats | display formatting | TECHNICAL_APPENDIX |
| QRS-SAECG beat counts and SNR | 4 | SAECG processing | beats / dB | display formatting | TECHNICAL_APPENDIX |
| `Filtered_QRS_Duration_ms`, `QRS_RMS40_mV`, `QRS_LAS40_ms` | 3 | SAECG/main measurements | ms / mV | RMS40 ×1000 to µV; display rounding | REPORT |

The 17 current report metrics are:

`Heart_Rate_bpm`, `QRS_Duration_median_ms`, `Avg_RR_II_ms`, `Avg_QT_II_ms`, `Avg_QTc_Bazett_II_ms`, `Avg_QTc_Fridericia_II_ms`, `Avg_Tpe_II_ms`, `QT_dispersion_global_ms`, `T_Wave_Dispersion_ms`, `P_Duration_mean_ms`, `P_Wave_Dispersion_ms`, `Filtered_P_Duration_ms`, `LAS20_ms`, `RMS20_mV`, `Filtered_QRS_Duration_ms`, `QRS_LAS40_ms`, and `QRS_RMS40_mV`.

The 8 current technical metrics are:

`QRS_QC_Status`, `QRS_Delineation_Method`, `QRS_SAECG_Beats_Extracted`, `QRS_SAECG_Beats_Used`, `QRS_SAECG_Beats_Rejected`, `QRS_SAECG_SNR_dB`, `P_SAECG_Beats_Used`, and `P_SAECG_SNR_dB`.

## 6. Ambiguities that block mapping changes

### 6.1 No SP-result persistence layer

`SignalProcessingResult` is built in memory during generation. Only selected values are copied into the transient `GenerationContext`, then serialized into report artifacts when a section uses them. No database table, JSON artifact, repository, or manifest stores the full 228-field result.

Consequently, assigning any unrendered metric to `PERSISTED_ONLY` would be false without designing a new persistence contract. That is outside a mapping-only change and requires an explicit architecture/product decision.

### 6.2 Context-only fields have no governed destination

Two validated mappings already copy values into `GenerationContext` but no section builder consumes them:

- `QRS_Duration_mean_ms -> ecg_parameters.qrs_duration_mean_ms`
- `Avg_Tpe_Qt_ratio_GLOBAL -> ecg_parameters.tpe_qt_ratio_global`

They are neither report fields, technical appendix fields, nor independently persisted. The existing mapping must be preserved, but choosing a visible destination is a report-content decision.

### 6.3 Per-lead policy is undefined

The task suggests “relevant per-lead measurements,” but source code does not define which of the 15-lead P/T or 12-lead QT families are relevant, whether all leads should be exposed, or how an 8-page A4 document should accommodate them without a layout change. Selecting a subset would be an unapproved clinical/product judgment.

### 6.4 Several diagnostics lack an approved reporting meaning

Examples include `T_Late_Flag_Rate_*`, late-T RMS/PTP, per-lead QT extrema/dispersion, R amplitude statistics, and internal valid-beat counts. Their computational meaning can be traced to SP, but their intended audience and report interpretation are not governed. They cannot safely be promoted to a clinical-facing report solely because they exist.

### 6.5 “Intentionally not exposed” is not yet evidenced

The current README documents excluded clinical classification and interpretation, but it does not enumerate the 203 unused numeric metrics or provide field-specific exclusion reasons. Marking all 203 as intentionally unexposed would create policy rather than audit existing policy.

## 7. Existing mappings preserved

All validated mappings named in the task remain unchanged. The audit made no edits to `signal_processing_builder.py`, `GenerationContext`, section builders, templates, schemas, tests, or SP code.

The result-envelope fields remain mapped as follows:

| Envelope field | Destination | Current use |
|---|---|---|
| `reference_lead` | `ecg_parameters.reference_lead` | technical provenance |
| `preprocessing_status` | `signal_quality_metrics.preprocessing_status` | quality/technical provenance |
| `leads_analyzed` | `signal_quality_metrics.leads_analyzed` | technical provenance |
| `r_peak_count` | `signal_quality_metrics.r_peak_count` | quality/technical provenance |

## 8. Unit conversions

Only the two existing conversions are present and validated:

- `RMS20_mV * 1000 -> rms20_uv`
- `QRS_RMS40_mV * 1000 -> rms40_uv`

All other mapped values preserve SP units. No new conversion is proposed.

## 9. Rounding rules

`GenerationContext` retains full floating-point SP values. `section_builders._number()` performs display-only rounding, usually to an integer and to one decimal for RMS/SNR values. This does not mutate the source result.

No report-side HR, RR, QRS, QT, QTc, Tpeak–Tend, dispersion, P-wave, SAECG, rhythm, diagnosis, risk, or recommendation calculation was found.

## 10. SP failure semantics

Current behavior in `build_signal_processing_outputs()` is explicit in source but not safe as final governance:

1. `WaveformReadError` or any unexpected exception is caught.
2. The error is logged.
3. `SignalProcessingOutputs.awaiting_signal_processing()` is returned.
4. Report generation can continue and finish without a distinct failed-SP status.

This conflates “not yet processed” with “processing failed.” Existing enums provide `JobStatus.FAILED` and `ReportStatus.FAILED`, but there is no `COMPLETED_WITH_WARNINGS` job/report state and no `signal_processing_status` field in the generation context/report contract.

Choosing between these alternatives is architecture/product behavior, not a mechanical mapping:

- fail the report-generation job when SP fails; or
- support a partial report with a new explicit failed-SP state and visible warning.

The user’s preferred behavior permits either. Because the choice affects job lifecycle, schemas, API behavior, templates, and tests, this audit does not select one.

## 11. Test coverage and baseline

Baseline executed immediately before this governance audit:

```text
Targeted ingestion/SP/reporting audit suite:
110 passed, 0 failed, 1082 warnings in 15.17s

Complete relevant ingestion/reporting suite:
390 passed, 0 failed, 13697 warnings in 194.45s
```

Current tests verify selected SP-to-context mappings, mV-to-µV conversion, unavailable clinical fields, report formatting, successful report generation, and current fail-soft behavior. No traceability test asserts membership for all 228 concrete keys because no approved final governance registry exists yet.

No post-change test run was required: no executable code or test was changed.

## 12. Known limitations and decisions required

Before implementation, approve all of the following:

1. Whether SP failure fails the entire report job or produces an explicitly warned partial report.
2. Whether a durable full-SP-result artifact/table should exist. Without it, `PERSISTED_ONLY` cannot be used truthfully.
3. Whether `QRS_Duration_mean_ms` and `Avg_Tpe_Qt_ratio_GLOBAL` should be visible, and where.
4. Which, if any, per-lead P/T/QT metrics belong in the existing Technical Appendix.
5. Field-specific reasons for every metric to be marked `INTENTIONALLY_NOT_EXPOSED`.
6. Whether internal diagnostics such as flag rates, amplitudes, extrema, and valid-beat counts are appropriate for clinician-facing or engineering-only output.

## 13. Audit stop point

The matrix discovered ambiguity, so work stops here as requested.

- Files modified: this document and its machine-readable matrix only.
- Production mappings modified: 0.
- New mappings added: 0.
- Previously unmapped/unresolved outputs: 203 of 228.
- SP module source hash before audit: `173ff3c99721b921575ab634cc5b0827289b0fa2da76de27d685ecf7837cdf01` (SHA-256 over sorted source `.py` files plus README, excluding `__pycache__`).
- SP module source hash after audit: identical; no SP file was modified.
- Real WFDB evidence: existing E2E remains PASS; it was not rerun because implementation was intentionally stopped.
- HTML/PDF evidence: existing generated HTML/PDF remain valid; no regeneration was needed because no rendering code changed.
- SP algorithm modified: **No**.

This document does not claim clinical validation and does not assign a final category to ambiguous outputs.
