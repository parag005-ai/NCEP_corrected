"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Activity,
  FileText,
  Printer,
  AlertTriangle,
  CheckCircle,
  BarChart3,
  Zap,
  ClipboardList,
  Settings,
  ChevronLeft,
} from "lucide-react";
import { Logo } from "@/components/ui/Logo";
import { useAuth } from "@/providers/AuthProvider";
import {
  getPatientById,
  getReportById,
  getReportData,
  getServiceErrorMessage,
  type PipelineReportData,
} from "@/services";

// ─── Helpers ────────────────────────────────────────────────────────────────
function ScoreBar({ score }: { score: number }) {
  const clampedScore = Math.max(0, Math.min(100, score));
  const getBarColor = (s: number) => {
    if (s < 40) return "#EF4444";
    if (s < 65) return "#F59E0B";
    return "#10B981";
  };
  return (
    <div className="flex items-center gap-1.5">
      <div className="relative h-2 w-24 rounded-full overflow-hidden flex">
        <div className="flex-1 bg-red-400/70" />
        <div className="flex-1 bg-amber-400/70" />
        <div className="flex-1 bg-emerald-400/70" />
        <div
          className="absolute top-1/2 -translate-y-1/2 w-0.5 h-3.5 rounded-full shadow"
          style={{
            left: `${clampedScore}%`,
            backgroundColor: getBarColor(clampedScore),
          }}
        />
      </div>
    </div>
  );
}

function FlagBadge({ result }: { result: "POSITIVE" | "NEGATIVE" }) {
  if (result === "POSITIVE") {
    return (
      <span className="inline-flex items-center gap-1 rounded-sm px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-red-500 text-white">
        <AlertTriangle className="h-2.5 w-2.5" />
        POSITIVE
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-sm px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-emerald-600 text-white">
      <CheckCircle className="h-2.5 w-2.5" />
      NEGATIVE
    </span>
  );
}

function StatusDot({ color }: { color: "green" | "blue" }) {
  return (
    <span
      className={`inline-block h-2 w-2 rounded-full mr-1 ${
        color === "green" ? "bg-emerald-500" : "bg-blue-500"
      }`}
    />
  );
}

function SectionTitle({
  icon,
  children,
}: {
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <h2 className="flex items-center gap-2 text-sm font-bold text-[#004d47] mb-4">
      <span className="text-[#005c55]">{icon}</span>
      {children}
    </h2>
  );
}

function MetaLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[9px] font-bold uppercase tracking-widest text-[#6e7977] mb-0.5">
      {children}
    </div>
  );
}

const NOT_YET_AVAILABLE = "Not yet available";

function formatMetric(value: number | null, unit: string): string {
  return value === null ? NOT_YET_AVAILABLE : `${value} ${unit}`;
}

function MetaValue({
  children,
  highlighted,
}: {
  children: React.ReactNode;
  highlighted?: boolean;
}) {
  return (
    <div
      className={`text-[13px] font-semibold ${
        highlighted ? "text-emerald-600" : "text-[#181c1c]"
      }`}
    >
      {children}
    </div>
  );
}

// ─── Main Component ─────────────────────────────────────────────────────────
export default function ClinicalReportPage() {
  const params = useParams();
  const id = (params?.reportId as string) ?? "NCEP-4492-X";
  const router = useRouter();
  const { session, loading } = useAuth();
  const [clinicalReport, setClinicalReport] = useState<import("@/types").ClinicalReport | undefined>(undefined);
  const [patientObj, setPatientObj] = useState<import("@/types").Patient | undefined>(undefined);
  const [data, setData] = useState<PipelineReportData | null>(null);
  const [reportLoading, setReportLoading] = useState(true);
  const [reportError, setReportError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setReportLoading(true);
    setReportError(null);
    setData(null);
    setClinicalReport(undefined);
    setPatientObj(undefined);

    const loadReport = async () => {
      try {
        const [pipelineData, report] = await Promise.all([getReportData(id), getReportById(id)]);
        if (!active) return;

        setData(pipelineData);
        setClinicalReport(report);
        const patientId = report?.patientId || pipelineData?.patientId;
        if (patientId) {
          const patient = await getPatientById(patientId);
          if (active) setPatientObj(patient);
        }
      } catch (error) {
        if (active) setReportError(getServiceErrorMessage(error));
      } finally {
        if (active) setReportLoading(false);
      }
    };

    void loadReport();
    return () => {
      active = false;
    };
  }, [id]);

  const canViewReport = Boolean(
    session &&
      clinicalReport &&
      (session.role === "superadmin" ||
        (session.role === "admin" && session.organisationId === clinicalReport.organisationId) ||
        (session.role === "doctor" && session.doctorId === clinicalReport.doctorId) ||
        (session.role === "patient" &&
          session.patientId === clinicalReport.patientId &&
          clinicalReport.sharedWithPatient &&
          (clinicalReport.status === "Approved" || clinicalReport.status === "Shared")))
  );

  useEffect(() => {
    if (loading) return;
    if (!session) {
      router.replace("/login");
      return;
    }
    if (clinicalReport && !canViewReport) {
      router.replace("/access-denied");
      return;
    }
    
    // Auto-print logic if requested via table Download button
    if (typeof window !== "undefined") {
      const urlParams = new URLSearchParams(window.location.search);
      if (urlParams.get("print") === "true") {
        const timer = setTimeout(() => {
          window.print();
        }, 800);
        return () => clearTimeout(timer);
      }
    }
  }, [canViewReport, clinicalReport, loading, router, session]);

  const displayPhysicianName = clinicalReport?.doctorName || data?.physicianName || "";
  const displayPatientName =
    clinicalReport?.patientName ||
    patientObj?.name ||
    (data?.patientName === "Patient Record" && clinicalReport?.title?.split("–")[1]?.trim()) ||
    data?.patientName ||
    "";
  const displayPatientId = clinicalReport?.patientId || data?.patientId || "";
  const displayAgeSex = patientObj
    ? `${patientObj.age} Y / ${patientObj.gender}`
    : data?.ageSex || "";

  // Derive physician initials for the avatar (e.g. "Dr. Meera Shah" → "MS")
  const physicianInitials = useMemo(() => {
    const parts = displayPhysicianName.replace(/^Dr\.?\s*/i, "").trim().split(/\s+/);
    return parts.map((p) => p[0]?.toUpperCase() ?? "").join("").slice(0, 2);
  }, [displayPhysicianName]);

  const [physicianNotes, setPhysicianNotes] = useState("");

  if (loading || reportLoading || !session || (clinicalReport && !canViewReport)) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-[#005c55] border-t-transparent" aria-label="Loading report" />
      </div>
    );
  }

  if (reportError || !clinicalReport || !data) {
    return (
      <main className="mx-auto flex min-h-[40vh] max-w-xl flex-col items-center justify-center gap-3 px-5 text-center">
        <h1 className="text-xl font-bold text-[#004d47]">{reportError ? "Unable to load report" : "Report not found"}</h1>
        <p className="text-sm text-[#4c6360]">
          {reportError || "The requested clinical report is unavailable."}
        </p>
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-[#eef1f0] flex flex-col">
      {/* ── NAV BAR ─────────────────────────────────────────────────────── */}
      <header className="bg-white border-b border-[#e0e3e1] sticky top-0 z-30">
        <div className="max-w-[1100px] mx-auto px-5 h-12 flex items-center justify-between gap-4">
          <div className="flex items-center shrink-0">
            <Logo className="scale-[0.8] origin-left" />
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <div className="text-right hidden sm:block">
              <div className="text-[12px] font-semibold text-[#181c1c]">
                {displayPhysicianName}
              </div>
              <div className="text-[9px] font-medium text-[#6e7977] uppercase tracking-wide">
                {data.physicianTitle}
              </div>
            </div>
            <div className="h-8 w-8 rounded-full bg-[#005c55] flex items-center justify-center text-white text-[11px] font-bold">
              {physicianInitials}
            </div>
          </div>
        </div>
      </header>

      {/* ── PAGE BODY ───────────────────────────────────────────────────── */}
      <main className="flex-1 max-w-[1100px] mx-auto w-full px-5 py-6 space-y-4">

        <div className="pb-2 flex items-center justify-between">
          <button
            onClick={() => router.back()}
            className="group flex items-center gap-1.5 text-base font-bold text-[#3e4947] hover:text-[#005c55] transition-colors -ml-1.5 print:hidden"
          >
            <ChevronLeft className="h-5 w-5 transition-transform group-hover:-translate-x-0.5" />
            Back
          </button>
          {session?.role !== "patient" && (
            <button
              onClick={() => router.push(`/report/${id}/detailed`)}
              className="flex items-center gap-2 rounded-lg bg-white border border-[#005c55] px-4 py-1.5 text-sm font-bold text-[#005c55] hover:bg-[#005c55] hover:text-white transition-all shadow-sm print:hidden"
            >
              <FileText className="h-4 w-4" />
              Detailed Report
            </button>
          )}
        </div>

        {/* ── TITLE CARD ─────────────────────────────────────────────────── */}
        <div className="bg-white rounded-xl border border-[#e0e3e1] px-6 py-4">
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
            <div>
              <h1 className="text-2xl font-extrabold text-[#005c55] leading-tight">
                Clinical ECG &amp; SAECG Analysis
              </h1>
              <p className="text-[12px] text-[#4c6360] mt-0.5">
                Diagnostic Level: {data.diagnosticLevel}
              </p>
            </div>
            <div className="flex flex-col items-end gap-1">
            </div>
          </div>

          {/* Patient Info Grid */}
          <div className="mt-5 grid grid-cols-2 sm:grid-cols-4 gap-x-8 gap-y-3 border-t border-[#e0e3e1] pt-4">
            <div><MetaLabel>Patient Name</MetaLabel><MetaValue>{displayPatientName}</MetaValue></div>
            <div><MetaLabel>Age / Sex</MetaLabel><MetaValue>{displayAgeSex}</MetaValue></div>
            <div><MetaLabel>Patient ID</MetaLabel><MetaValue>{displayPatientId}</MetaValue></div>
            <div><MetaLabel>Lead Name</MetaLabel><MetaValue>{data.leadName}</MetaValue></div>
            <div><MetaLabel>Recording Duration</MetaLabel><MetaValue>{data.recordingDuration}</MetaValue></div>
            <div><MetaLabel>Report Date</MetaLabel><MetaValue>{data.reportDate}</MetaValue></div>
            <div><MetaLabel>Physician</MetaLabel><MetaValue>{displayPhysicianName}</MetaValue></div>
            <div><MetaLabel>Processing ID</MetaLabel><MetaValue>{data.processingId}</MetaValue></div>
          </div>

          {/* Status Bar */}
          <div className="mt-4 flex flex-col sm:flex-row items-start sm:items-center gap-3 pt-3 border-t border-[#e0e3e1]">
            <div className="flex items-center gap-2 min-w-[160px]">
              <Settings className="h-3.5 w-3.5 text-[#6e7977]" />
              <div>
                <div className="text-[9px] font-bold uppercase tracking-widest text-[#6e7977]">Preprocessing</div>
                <div className="flex items-center gap-1 text-[11px] font-semibold text-emerald-600">
                  <StatusDot color="green" />{data.preprocessingStatus}
                </div>
              </div>
            </div>
            <div className="hidden sm:block h-8 w-px bg-[#e0e3e1]" />
            <div className="flex items-center gap-2 min-w-[160px]">
              <BarChart3 className="h-3.5 w-3.5 text-[#6e7977]" />
              <div>
                <div className="text-[9px] font-bold uppercase tracking-widest text-[#6e7977]">Analysis Status</div>
                <div className="flex items-center gap-1 text-[11px] font-semibold text-blue-600">
                  <StatusDot color="blue" />{data.analysisStatus}
                </div>
              </div>
            </div>
            <div className="hidden sm:block h-8 w-px bg-[#e0e3e1]" />
            <div className="flex-1">
              <div className="text-[9px] font-bold uppercase tracking-widest text-[#6e7977] mb-1">
                Signal Quality Score
              </div>
              <div className="flex items-center gap-3">
                <div className="flex-1 h-2.5 rounded-full bg-[#e0e3e1] overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-[#005c55] to-emerald-400 transition-all duration-700"
                    style={{ width: `${data.signalQualityScore}%` }}
                  />
                </div>
                <span className="text-[13px] font-bold text-[#005c55]">
                  {data.signalQualityScore}%
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* ── ROW 2: Rhythm & Signal + SAECG Table ─────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-4">
          {/* Left column */}
          <div className="space-y-4">
            {/* Rhythm & Signal */}
            <div className="bg-white rounded-xl border border-[#e0e3e1] p-5">
              <SectionTitle icon={<Activity className="h-4 w-4" />}>
                Rhythm &amp; Signal
              </SectionTitle>
              <div className="space-y-3">
                {[
                  { label: "R-Peak Count", value: data.rPeakCount.toString() },
                  { label: "QRS Complexes", value: data.qrsComplexes.toString(), sub: data.qrsNote },
                  {
                    label: "Mean Heart Rate",
                    value: data.meanHeartRate > 0 ? `${data.meanHeartRate} bpm` : NOT_YET_AVAILABLE,
                    highlight: true,
                  },
                ].map((row) => (
                  <div
                    key={row.label}
                    className="flex items-center justify-between border-b border-[#f1f4f3] pb-2 last:border-0 last:pb-0"
                  >
                    <div>
                      <div className="text-[12px] text-[#3e4947] font-medium">{row.label}</div>
                      {row.sub && (
                        <div className="text-[9px] text-[#6e7977] uppercase tracking-wide">{row.sub}</div>
                      )}
                    </div>
                    <div className={`text-[14px] font-bold ${row.highlight ? "text-[#005c55]" : "text-[#181c1c]"}`}>
                      {row.value}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Clinical Flags */}
            <div className="bg-white rounded-xl border border-[#e0e3e1] p-5">
              <SectionTitle icon={<AlertTriangle className="h-4 w-4" />}>
                Clinical Flags
              </SectionTitle>
              <div className="space-y-3">
                {data.clinicalFlags.map((flag) => (
                  <div key={flag.name}>
                    <div className="flex items-center justify-between mb-0.5">
                      <span className="text-[12px] font-semibold text-[#181c1c]">{flag.name}</span>
                      <FlagBadge result={flag.result} />
                    </div>
                    {flag.description && (
                      <p className="text-[10px] text-[#6e7977] leading-snug pl-0.5">{flag.description}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right column — SAECG Table */}
          <div className="bg-white rounded-xl border border-[#e0e3e1] overflow-hidden">
            <div className="flex items-center justify-between px-5 pt-5 pb-3">
              <SectionTitle icon={<BarChart3 className="h-4 w-4" />}>
                SAECG Detailed Parameters
              </SectionTitle>
              <span className="text-[10px] text-[#6e7977] font-medium italic -mt-4">Units: ms / µV</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-[#005c55] text-white">
                    <th className="px-4 py-2.5 text-left text-[11px] font-semibold">Parameter</th>
                    <th className="px-4 py-2.5 text-left text-[11px] font-semibold">Value</th>
                    <th className="px-4 py-2.5 text-left text-[11px] font-semibold">Visualization</th>
                    <th className="px-4 py-2.5 text-left text-[11px] font-semibold">Interpretation</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#f1f4f3]">
                  {data.saecgParameters.length === 0 && (
                    <tr>
                      <td colSpan={4} className="px-4 py-4 text-center text-[12px] italic text-[#6e7977]">
                        {NOT_YET_AVAILABLE} — SAECG analysis has not run for this report yet.
                      </td>
                    </tr>
                  )}
                  {data.saecgParameters.map((param, i) => (
                    <tr key={param.name} className={i % 2 === 0 ? "bg-white" : "bg-[#f7faf8]"}>
                      <td className="px-4 py-2.5 text-[12px] font-medium text-[#181c1c]">{param.name}</td>
                      <td className="px-4 py-2.5 text-[12px] font-bold text-[#181c1c]">
                        {param.value}{" "}
                        <span className="text-[10px] font-normal text-[#6e7977]">{param.unit}</span>
                      </td>
                      <td className="px-4 py-2.5"><ScoreBar score={param.score} /></td>
                      <td className="px-4 py-2.5 text-[11px] text-[#4c6360] italic">{param.interpretation}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* ── ROW 3: Repolarization & QT ──────────────────────────────── */}
        <div className="bg-white rounded-xl border border-[#e0e3e1] p-5">
          <SectionTitle icon={<Zap className="h-4 w-4" />}>
            Repolarization &amp; QT Analysis
          </SectionTitle>
          <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_320px] gap-6">
            {/* QT Interval Complex */}
            <div>
              <div className="text-[10px] font-bold uppercase tracking-widest text-[#005c55] mb-3 flex items-center gap-1">
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-[#005c55]" />
                QT Interval Complex
              </div>
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-[12px] text-[#3e4947]">QT Interval</span>
                  <span className="text-[13px] font-bold text-[#181c1c]">{formatMetric(data.qtInterval, "ms")}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[12px] text-[#3e4947]">QTc (Bazett)</span>
                  <span className={`text-[14px] font-bold ${data.qtcHighlighted ? "text-emerald-600" : "text-[#181c1c]"}`}>
                    {formatMetric(data.qtcBazett, "ms")}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[12px] text-[#3e4947]">QT Dispersion</span>
                  <span className="text-[13px] font-bold text-[#181c1c]">{formatMetric(data.qtDispersion, "ms")}</span>
                </div>
              </div>
            </div>

            {/* T-Wave Dynamics */}
            <div>
              <div className="text-[10px] font-bold uppercase tracking-widest text-[#005c55] mb-3 flex items-center gap-1">
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-[#005c55]" />
                T-Wave Dynamics
              </div>
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-[12px] text-[#3e4947]">Tpeak→Tend (Tpe)</span>
                  <span className="text-[13px] font-bold text-[#181c1c]">{formatMetric(data.tpeakTend, "ms")}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[12px] text-[#3e4947]">Tpe/QT Ratio</span>
                  <span className="text-[13px] font-bold text-[#181c1c]">{data.tpeQtRatio ?? NOT_YET_AVAILABLE}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[12px] text-[#3e4947]">T-Wave Dispersion</span>
                  <span className="text-[13px] font-bold text-[#181c1c]">{formatMetric(data.tWaveDispersion, "ms")}</span>
                </div>
              </div>
            </div>

            {/* Clinical Insight */}
            <div className="rounded-xl border border-[#bdc9c6] bg-[#f7faf8] p-4">
              <div className="flex items-center gap-1.5 mb-2">
                <ClipboardList className="h-3.5 w-3.5 text-[#005c55]" />
                <span className="text-[10px] font-bold uppercase tracking-widest text-[#005c55]">
                  Clinical Insight
                </span>
              </div>
              <p className="text-[11px] text-[#3e4947] leading-relaxed">{data.clinicalInsight}</p>
              <div className="mt-3 flex items-center justify-between border-t border-[#e0e3e1] pt-2">
                <span className="text-[9px] font-bold uppercase tracking-widest text-[#6e7977]">
                  Confidence Score
                </span>
                <span className={`text-[11px] font-bold ${
                  data.confidenceScore === "High" ? "text-emerald-600"
                    : data.confidenceScore === "Medium" ? "text-amber-500"
                    : "text-red-500"
                }`}>
                  {data.confidenceScore}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* ── ROW 4: Interpretation & Clinical Findings ─────────────────── */}
        <div className="bg-white rounded-xl border border-[#e0e3e1] p-5">
          <SectionTitle icon={<FileText className="h-4 w-4" />}>
            Interpretation &amp; Clinical Findings
          </SectionTitle>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Automated Analysis */}
            <div>
              <div className="text-[10px] font-bold uppercase tracking-widest text-[#6e7977] mb-2">
                Automated System Analysis
              </div>
              <div className="rounded-lg border border-[#e0e3e1] bg-[#f7faf8] p-4">
                <p className="text-[12px] text-[#3e4947] leading-relaxed">
                  {data.automatedAnalysis.split(/(T-Wave Late Potential Flag)/).map((part, i) =>
                    part === "T-Wave Late Potential Flag" ? (
                      <strong key={i} className="text-[#181c1c]">{part}</strong>
                    ) : (
                      part
                    )
                  )}
                </p>
              </div>
            </div>

            {/* Physician Notes */}
            <div>
              <div className="text-[10px] font-bold uppercase tracking-widest text-[#6e7977] mb-2">
                Physician Notes &amp; Signature
              </div>
              <div className="rounded-lg border border-[#e0e3e1] bg-[#f7faf8] p-4 min-h-[120px] flex flex-col">
                <textarea
                  value={physicianNotes}
                  onChange={(e) => setPhysicianNotes(e.target.value)}
                  placeholder={session?.role === "doctor" ? "Click to enter clinical impressions..." : "No clinical impressions recorded."}
                  disabled={session?.role !== "doctor"}
                  className="flex-1 w-full bg-transparent text-[12px] text-[#3e4947] placeholder:text-[#bdc9c6] resize-none outline-none min-h-[70px] disabled:cursor-not-allowed disabled:opacity-80"
                />
                <div className="mt-3 border-t border-[#bdc9c6] pt-3">
                  <div className="text-[14px] font-bold text-[#181c1c] font-serif italic">
                    {displayPhysicianName}
                  </div>
                  <div className="text-[9px] font-bold uppercase tracking-widest text-[#6e7977]">
                    {data.physicianTitle}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* ── FOOTER ──────────────────────────────────────────────────────── */}
      <footer className="bg-white border-t border-[#e0e3e1] mt-2">
        <div className="max-w-[1100px] mx-auto px-5 h-12 flex items-center justify-between gap-4">
          <p className="text-[10px] text-[#6e7977]">
            © 2026 CardioNexus. Enterprise Edition.
          </p>

          <button
            onClick={() => window.print()}
            className="flex items-center gap-2 rounded-lg bg-[#005c55] px-4 py-2 text-[12px] font-semibold text-white hover:bg-[#004d47] transition-colors"
          >
            <Printer className="h-3.5 w-3.5" />
            Download PDF
          </button>
        </div>
      </footer>
    </div>
  );
}
