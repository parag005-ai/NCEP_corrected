"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ChevronLeft, Download, FileWarning, Loader2 } from "lucide-react";
import { useAuth } from "@/providers/AuthProvider";
import {
  downloadDetailedReportPdf,
  getDetailedReportHtml,
  getGeneratedReportById,
  getGenerationJob,
  getLatestDetailedReport,
  getReportById,
  getServiceErrorMessage,
  requestReportGeneration,
  type GeneratedReport,
} from "@/services";
import type { ClinicalReport } from "@/types";

const POLL_INTERVAL_MS = 2000;

type ViewState = "loading" | "generating" | "ready" | "unavailable" | "error";

export default function DetailedReportClientPage() {
  const params = useParams();
  const reportId = (params?.reportId as string) ?? "";
  const router = useRouter();
  const { session, loading: authLoading } = useAuth();

  const [clinicalReport, setClinicalReport] = useState<ClinicalReport | undefined>(undefined);
  const [generatedReport, setGeneratedReport] = useState<GeneratedReport | null>(null);
  const [html, setHtml] = useState<string>("");
  const [state, setState] = useState<ViewState>("loading");
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const active = useRef(true);

  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
      if (pollTimer.current) clearTimeout(pollTimer.current);
    };
  }, []);

  // The Detailed Report API is only available to clinical/admin staff.
  useEffect(() => {
    if (!authLoading && session?.role === "patient") {
      router.replace("/access-denied");
    }
  }, [authLoading, session, router]);

  const showReport = useCallback(async (report: GeneratedReport) => {
    try {
      const doc = await getDetailedReportHtml(report.id);
      if (!active.current) return;
      setHtml(doc);
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
          if (report?.htmlUrl) {
            await showReport(report);
          } else {
            setError("Report generation finished, but the document isn't available yet.");
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
    [showReport],
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
        setClinicalReport(report);

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
        if (existing) {
          await showReport(existing);
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

  const handleDownload = async () => {
    if (!generatedReport) return;
    setDownloading(true);
    try {
      await downloadDetailedReportPdf(generatedReport.id, `ncep-detailed-report-${reportId}.pdf`);
    } catch (err) {
      setError(getServiceErrorMessage(err));
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-[#eef1f0]">
      <header className="sticky top-0 z-30 border-b border-[#e0e3e1] bg-white">
        <div className="mx-auto flex h-14 max-w-[1200px] items-center justify-between gap-4 px-5">
          <button
            onClick={() => router.back()}
            className="group flex items-center gap-1.5 text-body-sm font-bold text-[#3e4947] transition-colors hover:text-[#005c55]"
          >
            <ChevronLeft className="h-5 w-5 transition-transform group-hover:-translate-x-0.5" />
            Back to Summary Report
          </button>
          <button
            onClick={handleDownload}
            disabled={state !== "ready" || downloading}
            className="flex items-center gap-2 rounded-lg bg-[#005c55] px-4 py-1.5 text-body-sm font-bold text-white transition-colors hover:bg-[#004d47] disabled:cursor-not-allowed disabled:opacity-40"
          >
            {downloading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
            Download PDF
          </button>
        </div>
      </header>

      <main className="flex flex-1 flex-col">
        {(state === "loading" || state === "generating") && (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 py-24">
            <Loader2 className="h-8 w-8 animate-spin text-[#005c55]" />
            <p className="text-body-md font-medium text-[#181c1c]">
              {state === "loading" ? "Loading report..." : "Generating Detailed Report..."}
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
        )}

        {state === "unavailable" && (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 px-5 py-24 text-center">
            <FileWarning className="h-8 w-8 text-[#6e7977]" />
            <h1 className="text-body-lg font-bold text-[#181c1c]">No Detailed Report available</h1>
            <p className="max-w-sm text-body-sm text-[#4c6360]">
              This clinical report has no ECG recording linked to it, so a Detailed Report cannot be generated.
            </p>
          </div>
        )}

        {state === "error" && (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 px-5 py-24 text-center">
            <FileWarning className="h-8 w-8 text-error" />
            <h1 className="text-body-lg font-bold text-[#181c1c]">Unable to load the Detailed Report</h1>
            <p className="max-w-sm text-body-sm text-[#4c6360]">{error}</p>
          </div>
        )}

        {state === "ready" && (
          <iframe
            title={`Detailed Report ${clinicalReport?.title ?? reportId}`}
            srcDoc={html}
            className="min-h-[85vh] w-full flex-1 border-0 bg-white"
            sandbox="allow-same-origin"
          />
        )}
      </main>
    </div>
  );
}
