"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Activity, AlertTriangle, BarChart3, ChevronLeft, ClipboardList, FileText, FileWarning, Loader2, Settings } from "lucide-react";
import { Logo } from "@/components/ui/Logo";
import { useAuth } from "@/providers/AuthProvider";
import {
  getGeneratedReportById,
  getGenerationJob,
  getLatestDetailedReport,
  getReportById,
  getServiceErrorMessage,
  getSummaryReportDocument,
  requestReportGeneration,
  type GeneratedReport,
  type ReportSection,
  type SummaryReportDocument,
} from "@/services";

const POLL_INTERVAL_MS = 2000;

type ViewState = "loading" | "generating" | "ready" | "unavailable" | "error";

// ─── Helpers ────────────────────────────────────────────────────────────────

function section(summary: SummaryReportDocument, id: string): ReportSection | undefined {
  return summary.sections.find((s) => s.id === id);
}

function value(summary: SummaryReportDocument, sectionId: string, label: string) {
  return section(summary, sectionId)?.values.find((v) => v.label === label);
}

function ValueText({ summary, sectionId, label }: { summary: SummaryReportDocument; sectionId: string; label: string }) {
  const v = value(summary, sectionId, label);
  if (!v) return <span className="text-[13px] text-[#6e7977]">—</span>;
  return (
    <span className={v.isAvailable ? "text-[13px] font-semibold text-[#181c1c]" : "text-[13px] italic text-[#6e7977]"}>
      {v.displayValue}
      {v.isAvailable && v.unit ? ` ${v.unit}` : ""}
    </span>
  );
}

function MetaLabel({ children }: { children: React.ReactNode }) {
  return <div className="text-[9px] font-bold uppercase tracking-widest text-[#6e7977] mb-0.5">{children}</div>;
}

function SectionTitle({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <h2 className="flex items-center gap-2 text-sm font-bold text-[#004d47] mb-4">
      <span className="text-[#005c55]">{icon}</span>
      {children}
    </h2>
  );
}

function ScoreBar({ fraction }: { fraction: number }) {
  const percent = Math.max(0, Math.min(100, fraction * 100));
  const getBarColor = (s: number) => (s < 40 ? "#EF4444" : s < 65 ? "#F59E0B" : "#10B981");
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-2.5 rounded-full bg-[#e0e3e1] overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${percent}%`, backgroundColor: getBarColor(percent) }}
        />
      </div>
      <span className="text-[13px] font-bold text-[#005c55]">{percent.toFixed(0)}%</span>
    </div>
  );
}

function AwaitingNote({ text }: { text: string }) {
  return <p className="text-[12px] italic text-[#6e7977]">{text}</p>;
}

// ─── Main Component ─────────────────────────────────────────────────────────

export default function SummaryReportClientPage() {
  const params = useParams();
  const reportId = (params?.reportId as string) ?? "";
  const router = useRouter();
  const { session, loading: authLoading } = useAuth();

  const [generatedReport, setGeneratedReport] = useState<GeneratedReport | null>(null);
  const [summary, setSummary] = useState<SummaryReportDocument | null>(null);
  const [state, setState] = useState<ViewState>("loading");
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const active = useRef(true);

  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
      if (pollTimer.current) clearTimeout(pollTimer.current);
    };
  }, []);

  useEffect(() => {
    if (!authLoading && session?.role === "patient") {
      router.replace("/access-denied");
    }
  }, [authLoading, session, router]);

  const showSummary = useCallback(async (report: GeneratedReport) => {
    try {
      const doc = await getSummaryReportDocument(report.id);
      if (!active.current) return;
      setSummary(doc);
      setGeneratedReport(report);
      setState("ready");
    } catch (err) {
      if (!active.current) return;
      setError(getServiceErrorMessage(err));
      setState("error");
    }
  }, []);

  const pollJob = useCallback(
    async (jobId: string) => {
      try {
        const job = await getGenerationJob(jobId);
        if (!active.current) return;
        setProgress(job.progressPercent);
        setStage(job.currentStage ?? null);

        if (job.status === "COMPLETED" && job.reportId) {
          const report = await getGeneratedReportById(job.reportId);
          if (!active.current) return;
          if (report?.summaryUrl) {
            await showSummary(report);
          } else {
            setError("Report generation finished, but the summary isn't available yet.");
            setState("error");
          }
          return;
        }
        if (job.status === "FAILED" || job.status === "CANCELLED") {
          setError(job.errorMessage ?? `Report generation ${job.status.toLowerCase()}.`);
          setState("error");
          return;
        }
        pollTimer.current = setTimeout(() => pollJob(jobId), POLL_INTERVAL_MS);
      } catch (err) {
        if (!active.current) return;
        setError(getServiceErrorMessage(err));
        setState("error");
      }
    },
    [showSummary],
  );

  useEffect(() => {
    if (!reportId || authLoading || session?.role === "patient") return;
    let cancelled = false;

    const load = async () => {
      setState("loading");
      setError(null);
      try {
        const report = await getReportById(reportId);
        if (cancelled) return;

        // `reportId` is usually a ClinicalReport id, but a caller coming
        // straight from upload (no ClinicalReport exists yet) passes the
        // ECG record id directly -- fall back to treating it as one.
        const ecgRecordId = report?.ecgRecordId ?? reportId;
        if (!ecgRecordId) {
          setState("unavailable");
          return;
        }

        const existing = await getLatestDetailedReport(ecgRecordId);
        if (cancelled) return;
        if (existing?.summaryUrl) {
          await showSummary(existing);
          return;
        }

        setState("generating");
        setProgress(0);
        const job = await requestReportGeneration(ecgRecordId);
        if (cancelled) return;
        pollJob(job.id);
      } catch (err) {
        if (cancelled) return;
        setError(getServiceErrorMessage(err));
        setState("error");
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reportId, authLoading, session?.role]);

  if (state === "loading" || state === "generating") {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-[#eef1f0] py-24">
        <Loader2 className="h-8 w-8 animate-spin text-[#005c55]" />
        <p className="text-body-md font-medium text-[#181c1c]">
          {state === "loading" ? "Loading summary..." : "Running signal processing..."}
        </p>
        {state === "generating" && (
          <div className="w-64 space-y-1.5">
            <div className="h-2 w-full overflow-hidden rounded-full bg-[#e0e3e1]">
              <div
                className="h-full rounded-full bg-[#005c55] transition-all duration-500"
                style={{ width: `${Math.max(progress, 4)}%` }}
              />
            </div>
            <p className="text-center text-caption text-[#6e7977]">{stage ?? `${progress}%`}</p>
          </div>
        )}
      </div>
    );
  }

  if (state === "unavailable" || state === "error" || !summary) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-[#eef1f0] px-5 py-24 text-center">
        <FileWarning className={`h-8 w-8 ${state === "error" ? "text-error" : "text-[#6e7977]"}`} />
        <h1 className="text-body-lg font-bold text-[#181c1c]">
          {state === "unavailable" ? "No Summary Report available" : "Unable to load the Summary Report"}
        </h1>
        <p className="max-w-sm text-body-sm text-[#4c6360]">
          {state === "unavailable"
            ? "This report has no ECG recording linked to it, so a Summary cannot be generated."
            : error}
        </p>
      </div>
    );
  }

  const qualityValue = value(summary, "SIGNAL_QUALITY", "Quality score");
  const qualityFraction = qualityValue?.isAvailable && qualityValue.value ? Number(qualityValue.value) : null;
  const clinicalFlagsSection = section(summary, "CLINICAL_FLAGS");
  const interpretationSection = section(summary, "INTERPRETATION");

  return (
    <div className="min-h-screen bg-[#eef1f0] flex flex-col">
      <header className="bg-white border-b border-[#e0e3e1] sticky top-0 z-30">
        <div className="max-w-[1100px] mx-auto px-5 h-12 flex items-center justify-between gap-4">
          <div className="flex items-center shrink-0">
            <Logo className="scale-[0.8] origin-left" />
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <div className="text-right hidden sm:block">
              <div className="text-[12px] font-semibold text-[#181c1c]">
                <ValueText summary={summary} sectionId="DOCTOR_INFORMATION" label="Name" />
              </div>
              <div className="text-[9px] font-medium text-[#6e7977] uppercase tracking-wide">
                <ValueText summary={summary} sectionId="DOCTOR_INFORMATION" label="Speciality" />
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-[1100px] mx-auto w-full px-5 py-6 space-y-4">
        <div className="pb-2 flex items-center justify-between">
          <button
            onClick={() => router.back()}
            className="group flex items-center gap-1.5 text-base font-bold text-[#3e4947] hover:text-[#005c55] transition-colors -ml-1.5"
          >
            <ChevronLeft className="h-5 w-5 transition-transform group-hover:-translate-x-0.5" />
            Back
          </button>
          <button
            onClick={() => router.push(`/report/${reportId}/detailed`)}
            className="flex items-center gap-2 rounded-lg bg-white border border-[#005c55] px-4 py-1.5 text-sm font-bold text-[#005c55] hover:bg-[#005c55] hover:text-white transition-all shadow-sm"
          >
            <FileText className="h-4 w-4" />
            Detailed Report
          </button>
        </div>

        {/* ── TITLE CARD ─────────────────────────────────────────────────── */}
        <div className="bg-white rounded-xl border border-[#e0e3e1] px-6 py-4">
          <h1 className="text-2xl font-extrabold text-[#005c55] leading-tight">{summary.title}</h1>
          <p className="text-[12px] text-[#4c6360] mt-0.5">
            Report version {summary.generation.reportVersion} · Generated{" "}
            {new Date(summary.generation.generatedAt).toLocaleString()}
          </p>

          <div className="mt-5 grid grid-cols-2 sm:grid-cols-4 gap-x-8 gap-y-3 border-t border-[#e0e3e1] pt-4">
            <div><MetaLabel>Patient Name</MetaLabel><ValueText summary={summary} sectionId="PATIENT_INFORMATION" label="Name" /></div>
            <div><MetaLabel>Age / Gender</MetaLabel>
              <div className="text-[13px] font-semibold text-[#181c1c]">
                {value(summary, "PATIENT_INFORMATION", "Age")?.displayValue ?? "—"}
                {" / "}
                {value(summary, "PATIENT_INFORMATION", "Gender")?.displayValue ?? "—"}
              </div>
            </div>
            <div><MetaLabel>Patient ID</MetaLabel><ValueText summary={summary} sectionId="PATIENT_INFORMATION" label="Patient ID" /></div>
            <div><MetaLabel>Leads</MetaLabel><ValueText summary={summary} sectionId="RECORDING_SUMMARY" label="Leads" /></div>
            <div><MetaLabel>Recording Duration</MetaLabel><ValueText summary={summary} sectionId="RECORDING_SUMMARY" label="Duration" /></div>
            <div><MetaLabel>Recording Date</MetaLabel><ValueText summary={summary} sectionId="RECORDING_SUMMARY" label="Recording date" /></div>
            <div><MetaLabel>Physician</MetaLabel><ValueText summary={summary} sectionId="DOCTOR_INFORMATION" label="Name" /></div>
            <div><MetaLabel>ECG Record</MetaLabel><ValueText summary={summary} sectionId="REPORT_HEADER" label="ECG record" /></div>
          </div>

          <div className="mt-4 flex flex-col sm:flex-row items-start sm:items-center gap-3 pt-3 border-t border-[#e0e3e1]">
            <div className="flex items-center gap-2 min-w-[160px]">
              <Settings className="h-3.5 w-3.5 text-[#6e7977]" />
              <div>
                <div className="text-[9px] font-bold uppercase tracking-widest text-[#6e7977]">Validation Status</div>
                <div className="text-[11px] font-semibold text-[#181c1c]">
                  <ValueText summary={summary} sectionId="SIGNAL_QUALITY" label="Validation status" />
                </div>
              </div>
            </div>
            <div className="hidden sm:block h-8 w-px bg-[#e0e3e1]" />
            <div className="flex items-center gap-2 min-w-[160px]">
              <BarChart3 className="h-3.5 w-3.5 text-[#6e7977]" />
              <div>
                <div className="text-[9px] font-bold uppercase tracking-widest text-[#6e7977]">Accepted Beats</div>
                <div className="text-[11px] font-semibold text-[#181c1c]">
                  <ValueText summary={summary} sectionId="SIGNAL_QUALITY" label="Accepted beats" />
                </div>
              </div>
            </div>
            <div className="hidden sm:block h-8 w-px bg-[#e0e3e1]" />
            <div className="flex-1">
              <div className="text-[9px] font-bold uppercase tracking-widest text-[#6e7977] mb-1">Signal Quality Score</div>
              {qualityFraction !== null ? (
                <ScoreBar fraction={qualityFraction} />
              ) : (
                <AwaitingNote text="Awaiting Signal Processing Results" />
              )}
            </div>
          </div>
        </div>

        {/* ── ROW 2: Rhythm & Intervals + Clinical Flags ──────────────────── */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white rounded-xl border border-[#e0e3e1] p-5">
            <SectionTitle icon={<Activity className="h-4 w-4" />}>Rhythm &amp; Intervals</SectionTitle>
            <div className="space-y-3">
              {["Rate", "Rhythm", "PR", "QRS", "QTc"].map((label) => (
                <div key={label} className="flex items-center justify-between border-b border-[#f1f4f3] pb-2 last:border-0 last:pb-0">
                  <span className="text-[12px] text-[#3e4947] font-medium">{label}</span>
                  <ValueText summary={summary} sectionId="RHYTHM_METRICS" label={label} />
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-xl border border-[#e0e3e1] p-5">
            <SectionTitle icon={<AlertTriangle className="h-4 w-4" />}>Clinical Flags</SectionTitle>
            {clinicalFlagsSection?.isAvailable ? (
              <div className="space-y-3">
                {clinicalFlagsSection.values.map((v) => (
                  <div key={v.label} className="flex items-center justify-between">
                    <span className="text-[12px] font-semibold text-[#181c1c]">{v.label}</span>
                    <span className="text-[12px] text-[#181c1c]">{v.displayValue}</span>
                  </div>
                ))}
              </div>
            ) : (
              <AwaitingNote text={clinicalFlagsSection?.displayPlaceholder ?? "Awaiting Signal Processing Results"} />
            )}
          </div>
        </div>

        {/* ── ROW 3: Interpretation ────────────────────────────────────────── */}
        <div className="bg-white rounded-xl border border-[#e0e3e1] p-5">
          <SectionTitle icon={<ClipboardList className="h-4 w-4" />}>Integrated Impression</SectionTitle>
          {interpretationSection?.isAvailable ? (
            <div className="space-y-2">
              {interpretationSection.values.map((v) => (
                <div key={v.label}>
                  <span className="text-[11px] font-bold uppercase tracking-wide text-[#6e7977]">{v.label}: </span>
                  <span className="text-[12px] text-[#181c1c]">{v.displayValue}</span>
                </div>
              ))}
            </div>
          ) : (
            <AwaitingNote text={interpretationSection?.displayPlaceholder ?? "Awaiting Signal Processing Results"} />
          )}
        </div>

        <div className="flex justify-center pb-4">
          <button
            onClick={() => router.push(`/report/${reportId}/detailed`)}
            className="flex items-center gap-2 rounded-lg bg-[#005c55] px-5 py-2 text-body-sm font-bold text-white transition-colors hover:bg-[#004d47]"
          >
            <FileText className="h-4 w-4" />
            View Detailed Report
          </button>
        </div>
      </main>

      <footer className="bg-white border-t border-[#e0e3e1] mt-2">
        <div className="max-w-[1100px] mx-auto px-5 h-12 flex items-center justify-between gap-4">
          <p className="text-[10px] text-[#6e7977]">© 2026 CardioNexus. Enterprise Edition.</p>
          <p className="text-[9px] text-[#6e7977]">
            Pipeline {summary.generation.pipelineVersion} · Schema {summary.generation.schemaVersion}
          </p>
        </div>
      </footer>
    </div>
  );
}
