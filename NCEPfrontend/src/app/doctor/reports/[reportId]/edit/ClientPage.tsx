"use client";

import { useState, useEffect, use } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/providers/AuthProvider";
import { getReportById, getPatients, getECGRecords, saveReport, addAuditLog, getServiceErrorMessage } from "@/services";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import type { ClinicalReport, ReportStatus } from "@/types";

export default function DoctorReportEditor({ params }: { params: Promise<{ reportId: string }> }) {
  const { reportId } = use(params);
  const { session } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();
  
  const initialEcgId = searchParams?.get("ecgId") || "";
  const isNew = reportId === "new";

  const [existingReport, setExistingReport] = useState<ClinicalReport | null>(null);

  useEffect(() => {
    if (!isNew) {
      getReportById(reportId)
        .then((r) => {
          if (r && (r.status === "Approved" || r.status === "Shared")) {
            toast("Approved or Shared reports cannot be edited.", "error");
            router.replace("/doctor/reports");
            return;
          }
          setExistingReport(r ?? null);
        })
        .catch((err) => console.error("Error loading report:", err));
    }
  }, [reportId, isNew, router, toast]);

  const [formData, setFormData] = useState({
    title: "",
    patientId: "",
    ecgRecordId: initialEcgId,
    clinicalObservations: "",
    findings: "",
    interpretation: "",
    recommendations: "",
  });

  useEffect(() => {
    if (existingReport) {
      setFormData({
        title: existingReport.title,
        patientId: existingReport.patientId,
        ecgRecordId: existingReport.ecgRecordId,
        clinicalObservations: existingReport.clinicalObservations,
        findings: existingReport.findings,
        interpretation: existingReport.interpretation,
        recommendations: existingReport.recommendations,
      });
    }
  }, [existingReport]);

  const [myPatients, setMyPatients] = useState<import("@/types").Patient[]>([]);
  const [myECGs, setMyECGs] = useState<import("@/types").ECGRecord[]>([]);

  useEffect(() => {
    if (!session?.doctorId) return;
    const docId = session.doctorId;
    getPatients()
      .then((pts) => setMyPatients(pts.filter((p) => p.assignedDoctorId === docId)))
      .catch((err) => console.error("Error loading patients:", err));
    getECGRecords()
      .then((ecgs) => setMyECGs(ecgs.filter((e) => e.doctorId === docId)))
      .catch((err) => console.error("Error loading ECG records:", err));
  }, [session?.doctorId]);

  const handleSave = async (status: ReportStatus) => {
    if (!session?.doctorId || !session?.organisationId) return;

    try {
      const patient = myPatients.find((p) => p.id === formData.patientId);
      if (!patient) {
        toast("Please select a valid patient.", "error");
        return;
      }

      const newId = isNew ? `rpt-${Math.floor(Math.random() * 1000).toString().padStart(3, "0")}` : reportId;

      const report: ClinicalReport = {
        id: newId,
        title: formData.title || `Clinical Report - ${patient.name}`,
        patientId: patient.id,
        patientName: patient.name,
        doctorId: session.doctorId,
        doctorName: session.name,
        organisationId: session.organisationId,
        ecgRecordId: formData.ecgRecordId,
        clinicalObservations: formData.clinicalObservations,
        findings: formData.findings,
        interpretation: formData.interpretation,
        recommendations: formData.recommendations,
        status: status,
        reviewedBy: status === "Approved" ? session.name : "Pending",
        createdAt: existingReport ? existingReport.createdAt : new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        sharedWithPatient: existingReport ? existingReport.sharedWithPatient : false,
      };

      await saveReport(report);
      
      await addAuditLog({
        id: `log-${Date.now()}`,
        event: isNew ? "Report created" : "Report updated",
        eventType: isNew ? "report_created" : "report_updated",
        actorId: session.userId,
        actorName: session.name,
        actorRole: session.role,
        organisationId: session.organisationId,
        organisationName: "Mock Org",
        resource: `Report ${newId}`,
        result: "Success",
        ipAddress: "127.0.0.1",
        timestamp: new Date().toISOString(),
        details: `Report saved as ${status}`,
      });

      toast(`Report saved as ${status}`, "success");
      router.push("/doctor/reports");
    } catch (error) {
      toast(getServiceErrorMessage(error), "error");
    }
  };

  if (!isNew && existingReport && existingReport.doctorId !== session?.doctorId) {
    if (typeof window !== "undefined") router.replace("/access-denied");
    return null;
  }

  return (
    <div className="space-y-8 max-w-4xl">
      <PageHeader
        title={isNew ? "Create Clinical Report" : "Edit Clinical Report"}
        description="Draft and finalise your clinical findings and recommendations."
      />

      <Card className="p-8">
        <form className="space-y-6" onSubmit={(e) => e.preventDefault()}>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            <Input
              label="Report Title"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              placeholder="e.g., Annual Cardiac Review"
            />
            
            <div className="space-y-1.5">
              <label className="text-body-sm font-medium text-on-surface-variant">Patient</label>
              <select
                value={formData.patientId}
                onChange={(e) => setFormData({ ...formData, patientId: e.target.value })}
                className="h-input-height w-full rounded-xl border border-border-muted bg-surface px-4 text-body-lg text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                disabled={!isNew} // Lock patient once created
              >
                <option value="" disabled>Select patient...</option>
                {myPatients.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-body-sm font-medium text-on-surface-variant">Linked ECG Record (Optional)</label>
            <select
              value={formData.ecgRecordId}
              onChange={(e) => setFormData({ ...formData, ecgRecordId: e.target.value })}
              className="h-input-height w-full rounded-xl border border-border-muted bg-surface px-4 text-body-lg text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            >
              <option value="">None</option>
              {myECGs.filter(e => e.patientId === formData.patientId || !formData.patientId).map((e) => (
                <option key={e.id} value={e.id}>{e.fileName} ({e.recordingDate})</option>
              ))}
            </select>
          </div>
          
          <div className="space-y-1.5">
            <label className="text-body-sm font-medium text-on-surface-variant">Clinical Observations</label>
            <textarea
              className="w-full rounded-xl border border-border-muted bg-surface p-4 text-body-lg text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary min-h-[100px]"
              value={formData.clinicalObservations}
              onChange={(e) => setFormData({ ...formData, clinicalObservations: e.target.value })}
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-body-sm font-medium text-on-surface-variant">Findings</label>
            <textarea
              className="w-full rounded-xl border border-border-muted bg-surface p-4 text-body-lg text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary min-h-[100px]"
              value={formData.findings}
              onChange={(e) => setFormData({ ...formData, findings: e.target.value })}
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-body-sm font-medium text-on-surface-variant">Interpretation</label>
            <textarea
              className="w-full rounded-xl border border-border-muted bg-surface p-4 text-body-lg text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary min-h-[100px]"
              value={formData.interpretation}
              onChange={(e) => setFormData({ ...formData, interpretation: e.target.value })}
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-body-sm font-medium text-primary">Recommendations & Treatment Plan</label>
            <textarea
              className="w-full rounded-xl border border-primary/30 bg-primary/5 p-4 text-body-lg text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary min-h-[100px]"
              value={formData.recommendations}
              onChange={(e) => setFormData({ ...formData, recommendations: e.target.value })}
            />
          </div>

          <div className="flex flex-wrap items-center justify-end gap-3 pt-6 border-t border-border-muted">
            <Button variant="ghost" onClick={() => router.back()}>Cancel</Button>
            <Button variant="outline" onClick={() => handleSave("Draft")} disabled={!formData.patientId}>
              Save Draft
            </Button>
            <Button variant="secondary" onClick={() => handleSave("In Review")} disabled={!formData.patientId}>
              Submit for Review
            </Button>
            <Button onClick={() => handleSave("Approved")} disabled={!formData.patientId}>
              Finalise Report
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}



