"use client";

import { useState, useMemo, useRef, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/providers/AuthProvider";
import { addAuditLog, getPatients, getServiceErrorMessage, ingestECGRecord, saveReport } from "@/services";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { Upload, FileUp, ChevronDown, AlertCircle } from "lucide-react";

export default function DoctorECGUpload() {
  const { session } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();
  
  const defaultPatientId = searchParams?.get("patientId") || "";

  const [formData, setFormData] = useState({
    patientId: defaultPatientId,
    recordingDate: new Date().toISOString().split("T")[0],
    deviceSource: "CardioNexus ECG 3000",
    notes: "",
  });
  
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadPercent, setUploadPercent] = useState(0);
  const [stage, setStage] = useState<"uploading" | "processing">("uploading");
  const [uploadError, setUploadError] = useState<string | null>(null);

  const [searchTerm, setSearchTerm] = useState("");
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const [orgPatients, setOrgPatients] = useState<import("@/types").Patient[]>([]);

  useEffect(() => {
    if (!session?.organisationId) return;
    const orgId = session.organisationId;
    getPatients()
      .then((pts) => setOrgPatients(pts.filter((p) => p.organisationId === orgId)))
      .catch((err) => console.error("Error loading patients:", err));
  }, [session?.organisationId]);

  const filteredPatients = useMemo(() => {
    const lower = searchTerm.trim().toLowerCase();
    if (lower.length < 3) return [];
    return orgPatients.filter(
      (p) => p.name.toLowerCase().includes(lower) || p.id.toLowerCase().includes(lower)
    );
  }, [orgPatients, searchTerm]);

  // When patientId changes (e.g. from URL), set the initial search term
  useEffect(() => {
    if (formData.patientId && orgPatients.length > 0) {
      const patient = orgPatients.find(p => p.id === formData.patientId);
      if (patient) {
        setSearchTerm(`${patient.name} (${patient.id})`);
      }
    }
  }, [formData.patientId, orgPatients]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!session?.doctorId || !session?.organisationId) return;
    if (files.length === 0) {
      toast("Please select at least one file to upload.", "error");
      return;
    }

    const patient = orgPatients.find((p) => p.id === formData.patientId);
    if (!patient) {
      toast("Please select a valid patient from the list.", "error");
      return;
    }

    setUploading(true);
    setStage("uploading");
    setUploadPercent(0);
    setUploadError(null);
    completeUpload(patient, files).catch((err) => {
      setUploading(false);
      setUploadError(getServiceErrorMessage(err));
    });
  };

  const completeUpload = async (patient: import("@/types").Patient, uploadFiles: File[]) => {
    const record = await ingestECGRecord(
      {
        patientId: patient.id,
        doctorId: session!.doctorId!,
        deviceSource: formData.deviceSource,
        recordingDate: formData.recordingDate,
        notes: formData.notes,
      },
      uploadFiles,
      { onProgress: setUploadPercent, onAccepted: () => setStage("processing") },
    );

    // Shares the ECG record's id as the ClinicalReport id, so both the
    // Summary (/report/{id}) and Detailed (/report/{id}/detailed) pages
    // resolve this freshly-ingested record through their normal
    // getReportById lookup -- no pre-existing clinical report is needed.
    await saveReport({
      id: record.id,
      title: `ECG Report – ${patient.name}`,
      patientId: patient.id,
      patientName: patient.name,
      doctorId: session!.doctorId!,
      doctorName: session!.name,
      organisationId: session!.organisationId!,
      ecgRecordId: record.id,
      clinicalObservations: "",
      findings: "",
      interpretation: "",
      recommendations: "",
      status: "Draft",
      reviewedBy: "",
      createdAt: "",
      updatedAt: "",
      sharedWithPatient: false,
    });

    await addAuditLog({
      id: `log-${Date.now()}`,
      event: "ECG file uploaded",
      eventType: "ecg_uploaded",
      actorId: session!.userId,
      actorName: session!.name,
      actorRole: session!.role,
      organisationId: session!.organisationId,
      organisationName: "Mock Org",
      resource: `ECG ${record.id}`,
      result: "Success",
      ipAddress: "127.0.0.1",
      timestamp: new Date().toISOString(),
      details: `ECG uploaded for ${patient.name}`,
    });

    toast("ECG processed successfully.", "success");
    router.push(`/report/${record.id}/summary`);
  };

  return (
    <div className="space-y-8 max-w-4xl">
      <PageHeader
        title="Upload ECG Recording"
        description="Upload and associate ECG recordings with your assigned patients."
      />

      <Card className="p-8">
        <form onSubmit={handleSubmit} className="space-y-8">
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            <div className="space-y-1.5" ref={dropdownRef}>
              <label className="text-body-sm font-medium text-on-surface-variant">Select Patient *</label>
              <div className="relative">
                <div 
                  className={`flex h-input-height w-full items-center justify-between rounded-xl border ${isDropdownOpen ? 'border-primary ring-1 ring-primary' : 'border-border-muted'} bg-surface px-4 text-body-lg text-on-surface cursor-text ${uploading ? 'opacity-50 pointer-events-none' : ''}`}
                  onClick={() => setIsDropdownOpen(true)}
                >
                  <input
                    type="text"
                    required={!formData.patientId}
                    placeholder="Search by name or ID..."
                    value={searchTerm}
                    onChange={(e) => {
                      setSearchTerm(e.target.value);
                      setIsDropdownOpen(true);
                      if (formData.patientId) {
                        setFormData({ ...formData, patientId: "" });
                      }
                    }}
                    onFocus={() => setIsDropdownOpen(true)}
                    className="w-full !border-0 bg-transparent !outline-none focus:!ring-0 focus:!shadow-none placeholder:text-on-surface-variant/50"
                  />
                  <ChevronDown className="h-5 w-5 text-on-surface-variant/50 flex-shrink-0 ml-2" />
                </div>

                {isDropdownOpen && searchTerm.trim().length >= 3 && (
                  <div className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-xl border border-border-muted bg-surface py-1 shadow-lg">
                    {filteredPatients.length === 0 ? (
                      <div className="px-4 py-3 text-body-sm text-on-surface-variant">
                        No patients found in your organisation.
                      </div>
                    ) : (
                      filteredPatients.map((p) => (
                        <div
                          key={p.id}
                          className={`cursor-pointer px-4 py-2.5 text-body-md hover:bg-surface-hover ${formData.patientId === p.id ? 'bg-primary/10 text-primary font-medium' : 'text-on-surface'}`}
                          onClick={() => {
                            setFormData({ ...formData, patientId: p.id });
                            setSearchTerm(`${p.name} (${p.id})`);
                            setIsDropdownOpen(false);
                          }}
                        >
                          <div className="flex justify-between items-center">
                            <span>{p.name}</span>
                            <span className="text-body-sm text-on-surface-variant">{p.id}</span>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            </div>
            
            <Input
              label="Recording Date *"
              name="recordingDate"
              type="date"
              required
              value={formData.recordingDate}
              onChange={(e) => setFormData({ ...formData, recordingDate: e.target.value })}
              disabled={uploading}
            />
            
            <div className="space-y-1.5">
              <label className="text-body-sm font-medium text-on-surface-variant">Device / Source *</label>
              <select
                required
                value={formData.deviceSource}
                onChange={(e) => setFormData({ ...formData, deviceSource: e.target.value })}
                className="h-input-height w-full rounded-xl border border-border-muted bg-surface px-4 text-body-lg text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary disabled:opacity-50"
                disabled={uploading}
              >
                <option value="CardioNexus ECG 3000">CardioNexus ECG 3000</option>
                <option value="Holter Monitor H200">Holter Monitor H200</option>
                <option value="CardioScan Pro">CardioScan Pro</option>
                <option value="External File">External File</option>
              </select>
            </div>
            
            <Input
              label="Clinical Notes (Optional)"
              name="notes"
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              placeholder="e.g., Patient experienced slight discomfort"
              disabled={uploading}
            />
          </div>

          <div className="space-y-2">
            <label className="text-body-sm font-medium text-on-surface-variant">Upload File(s) *</label>
            <div className="relative flex min-h-[200px] cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-border-muted bg-surface-bright p-6 text-center transition-colors hover:border-primary hover:bg-surface-bright/80">
              <input
                type="file"
                multiple
                className="absolute inset-0 z-10 h-full w-full cursor-pointer opacity-0"
                accept=".pdf,.csv,.xml,.edf,.dat,.hea,.xyz,.atr,.qrs,.ecg,.dcm,.png,.jpg,.jpeg"
                onChange={(e) => {
                  setFiles(Array.from(e.target.files ?? []));
                  setUploadError(null);
                }}
                disabled={uploading}
              />
              {files.length > 0 ? (
                <div className="flex flex-col items-center gap-2">
                  <FileUp className="h-10 w-10 text-primary" />
                  <ul className="space-y-0.5">
                    {files.map((f) => (
                      <li key={f.name} className="text-body-lg font-medium text-on-surface">{f.name}</li>
                    ))}
                  </ul>
                  <p className="text-caption text-secondary">
                    {(files.reduce((sum, f) => sum + f.size, 0) / 1024 / 1024).toFixed(2)} MB total
                  </p>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-2">
                  <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-secondary-container">
                    <Upload className="h-6 w-6 text-primary" />
                  </div>
                  <p className="text-body-lg font-medium text-on-surface">Click or drag file(s) to upload</p>
                  <p className="text-caption text-secondary">
                    WFDB (.hea + .dat), CSV, XML, EDF, DICOM, SCP-ECG (Max 50MB). Select all companion files
                    (e.g. .hea and .dat) together.
                  </p>
                </div>
              )}
            </div>
            {uploadError && (
              <div className="flex items-start gap-2 rounded-xl border border-error/30 bg-error/5 px-4 py-3 text-body-sm text-error">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{uploadError}</span>
              </div>
            )}
          </div>

          {uploading && (
            <div className="space-y-2">
              <span className="text-body-sm font-medium text-on-surface">
                {stage === "uploading" ? `Uploading... ${uploadPercent}%` : "Processing ECG..."}
              </span>
              <div className="h-2 w-full overflow-hidden rounded-full bg-surface-bright">
                {stage === "uploading" ? (
                  <div
                    className="h-full rounded-full bg-primary transition-all duration-300"
                    style={{ width: `${Math.max(uploadPercent, 4)}%` }}
                  />
                ) : (
                  <div className="h-full w-full origin-left animate-pulse bg-primary" />
                )}
              </div>
            </div>
          )}

          <div className="flex justify-end gap-3 pt-6 border-t border-border-muted">
            <Button variant="ghost" type="button" onClick={() => router.back()} disabled={uploading}>Cancel</Button>
            <Button type="submit" disabled={uploading || files.length === 0 || !formData.patientId}>
              {uploading ? "Processing..." : uploadError ? "Retry Processing" : "Start Upload"}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
