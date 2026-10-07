/**
 * pipeline-data.ts
 *
 * Shared type contract for the signal-processing report at /report/[id],
 * matching backend/app/schemas.py's PipelineReportData exactly (see
 * GET /api/reports/{id}/pipeline in backend/app/routers/reports.py).
 *
 * qtInterval/qtcBazett/qtDispersion/tpeakTend/tpeQtRatio/tWaveDispersion are
 * nullable because that pipeline does not run SAECG late-potential or
 * QT/repolarization analysis yet -- the backend returns null rather than a
 * fabricated number, and the UI must render that as "not yet available".
 */

export interface SAECGParameter {
  name: string;
  value: string;
  unit: string;
  interpretation: string;
  score: number;
}

export interface ClinicalFlag {
  name: string;
  result: "POSITIVE" | "NEGATIVE";
  description: string;
}

export interface PipelineReportData {
  processingId: string;
  diagnosticLevel: string;
  clinicalUnit: string;
  platformName: string;

  patientName: string;
  ageSex: string;
  patientId: string;
  leadName: string;

  recordingDuration: string;
  reportDate: string;
  physician: string;

  preprocessingStatus: "Completed" | "In Progress" | "Failed";
  analysisStatus: "Validated" | "Pending" | "Error";
  signalQualityScore: number;

  rPeakCount: number;
  qrsComplexes: number;
  qrsNote: string;
  meanHeartRate: number;

  clinicalFlags: ClinicalFlag[];
  saecgParameters: SAECGParameter[];

  qtInterval: number | null;
  qtcBazett: number | null;
  qtDispersion: number | null;
  tpeakTend: number | null;
  tpeQtRatio: number | null;
  tWaveDispersion: number | null;
  qtcHighlighted: boolean;

  clinicalInsight: string;
  confidenceScore: "High" | "Medium" | "Low";

  automatedAnalysis: string;
  physicianName: string;
  physicianTitle: string;
}
