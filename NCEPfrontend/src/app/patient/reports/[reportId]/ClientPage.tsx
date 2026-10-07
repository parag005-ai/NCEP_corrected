"use client";
import { use, useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * This route now redirects to the unified Clinical ECG & SAECG Analysis report
 * at /report/[id]. The old per-role report view is no longer used.
 */
export default function PatientReportDetail({ params }: { params: Promise<{ reportId: string }> }) {
  const { reportId } = use(params);
  const router = useRouter();

  useEffect(() => {
    router.replace(`/report/${reportId}`);
  }, [reportId, router]);

  return (
    <div className="flex items-center justify-center min-h-[40vh]">
      <div className="flex flex-col items-center gap-3">
        <div className="h-6 w-6 rounded-full border-2 border-[#005c55] border-t-transparent animate-spin" />
        <p className="text-sm text-[#4c6360]">Loading report…</p>
      </div>
    </div>
  );
}
