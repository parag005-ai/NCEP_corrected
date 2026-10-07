/* eslint-disable @next/next/no-img-element */
"use client";

import { useMemo, useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { useAuth } from "@/providers/AuthProvider";
import { getECGRecords, getPatientById } from "@/services";
import { formatDate } from "@/lib/utils";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Activity, Download, Settings2, Play, Pause, Search, X } from "lucide-react";
import Link from "next/link";

export default function DoctorECGViewer() {
  const { session } = useAuth();
  const searchParams = useSearchParams();
  const initialEcgId = searchParams?.get("ecgId") || "";

  const [ecgs, setEcgs] = useState<import("@/types").ECGRecord[]>([]);
  const [selectedEcgId, setSelectedEcgId] = useState(initialEcgId);
  const [isPlaying, setIsPlaying] = useState(true);
  const [patient, setPatient] = useState<import("@/types").Patient | null>(null);

  useEffect(() => {
    if (!session?.doctorId) return;
    getECGRecords()
      .then((all) => {
        const filtered = all.filter((e) => e.doctorId === session.doctorId);
        setEcgs(filtered);
        if (!selectedEcgId && filtered[0]) setSelectedEcgId(filtered[0].id);
      })
      .catch((err) => console.error("Error loading ECG records:", err));
  }, [session?.doctorId, selectedEcgId]);

  const selectedEcg = useMemo(() => ecgs.find((e) => e.id === selectedEcgId), [ecgs, selectedEcgId]);

  useEffect(() => {
    if (selectedEcg) {
      getPatientById(selectedEcg.patientId)
        .then((p) => setPatient(p ?? null))
        .catch((err) => console.error("Error loading patient:", err));
    } else {
      setPatient(null);
    }
  }, [selectedEcg]);

  const isImage = selectedEcg?.fileData?.startsWith('data:image/');

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader title="ECG Viewer" description="Interactive viewer for uploaded ECG recordings." />
        <div className="flex w-full flex-col gap-3 self-start sm:w-auto sm:flex-row">
          {selectedEcg ? (
            <div className="flex h-10 items-center rounded-xl border border-border-muted bg-surface px-4 text-body-sm font-medium text-on-surface">
              {selectedEcg.patientName} - {formatDate(selectedEcg.recordingDate)}
            </div>
          ) : null}
        </div>
      </div>

      {!selectedEcg ? (
        <EmptyState title="No ECG Selected" description="Please select an ECG record to view." />
      ) : (
        <div className="space-y-6">
          <Card className="overflow-hidden">
            <div className="flex items-center justify-between border-b border-border-muted bg-surface-bright px-6 py-4">
              <div className="flex items-center gap-4">
                <Button variant="ghost" className="h-8 w-8 p-0" onClick={() => setIsPlaying(!isPlaying)}>
                  {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                </Button>
                <div className="h-4 w-px bg-border-muted" />
                <span className="text-body-sm font-medium text-on-surface">Lead II</span>
                <span className="text-caption text-secondary">25 mm/s, 10 mm/mV</span>
              </div>
              <div className="flex gap-2">
                <Button variant="ghost" className="h-8 w-8 p-0"><Settings2 className="h-4 w-4" /></Button>
                <Button variant="ghost" className="h-8 w-8 p-0"><Download className="h-4 w-4" /></Button>
              </div>
            </div>
            
            {/* The Viewer */}
            <div className="relative h-64 w-full bg-[#f8f9fa] sm:h-96" style={!isImage ? { backgroundImage: "linear-gradient(#e5e7eb 1px, transparent 1px), linear-gradient(90deg, #e5e7eb 1px, transparent 1px)", backgroundSize: "20px 20px" } : undefined}>
              {isImage ? (
                <div className="absolute inset-0 flex items-center justify-center p-4">
                  <img src={selectedEcg.fileData} alt="ECG Record" className="max-h-full max-w-full object-contain" />
                </div>
              ) : (
                <>
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-20">
                    <Activity className="h-full w-full max-w-[80%] text-primary" strokeWidth={0.5} />
                  </div>
                  {/* Mock SVG Waveform */}
                  <svg className="h-full w-full" preserveAspectRatio="none" viewBox="0 0 1000 100">
                    <path
                      d="M0 50 L50 50 L60 40 L70 50 L100 50 L110 55 L120 10 L130 90 L140 50 L170 50 L180 45 L200 50 L250 50 L260 40 L270 50 L300 50 L310 55 L320 10 L330 90 L340 50 L370 50 L380 45 L400 50 L450 50 L460 40 L470 50 L500 50 L510 55 L520 10 L530 90 L540 50 L570 50 L580 45 L600 50 L650 50 L660 40 L670 50 L700 50 L710 55 L720 10 L730 90 L740 50 L770 50 L780 45 L800 50 L850 50 L860 40 L870 50 L900 50 L910 55 L920 10 L930 90 L940 50 L970 50 L980 45 L1000 50"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      className={`text-slate-800 ${isPlaying ? 'animate-[pulse_1.5s_ease-in-out_infinite]' : ''}`}
                    />
                  </svg>
                </>
              )}
            </div>
            
            <div className="border-t border-border-muted bg-warning/10 p-3 text-center">
              <p className="text-caption font-medium text-warning">Demonstration data only. Not for clinical diagnostic use.</p>
            </div>
          </Card>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <Card className="p-6">
              <h3 className="mb-4 text-card-title text-on-surface">Record Metadata</h3>
              <dl className="space-y-3 text-body-sm">
                <div className="flex justify-between border-b border-border-muted pb-2">
                  <dt className="text-secondary">File Name</dt>
                  <dd className="font-medium text-on-surface">{selectedEcg.fileName}</dd>
                </div>
                <div className="flex justify-between border-b border-border-muted pb-2">
                  <dt className="text-secondary">Date</dt>
                  <dd className="font-medium text-on-surface">{formatDate(selectedEcg.recordingDate)}</dd>
                </div>
                <div className="flex justify-between border-b border-border-muted pb-2">
                  <dt className="text-secondary">Device</dt>
                  <dd className="font-medium text-on-surface">{selectedEcg.deviceSource}</dd>
                </div>
                <div className="flex justify-between pb-2">
                  <dt className="text-secondary">Status</dt>
                  <dd><StatusBadge>{selectedEcg.status}</StatusBadge></dd>
                </div>
              </dl>
              <div className="mt-6">
                <Link href={`/doctor/reports/new/edit?ecgId=${selectedEcg.id}`}>
                  <Button className="w-full">Draft Clinical Report</Button>
                </Link>
              </div>
            </Card>

            <Card className="p-6">
              <h3 className="mb-4 text-card-title text-on-surface">Patient Summary</h3>
              {patient ? (
                <dl className="space-y-3 text-body-sm">
                  <div className="flex justify-between border-b border-border-muted pb-2">
                    <dt className="text-secondary">Name</dt>
                    <dd className="font-medium text-on-surface">{patient.name}</dd>
                  </div>
                  <div className="flex justify-between border-b border-border-muted pb-2">
                    <dt className="text-secondary">ID</dt>
                    <dd className="font-medium text-on-surface">{patient.id}</dd>
                  </div>
                  <div className="flex justify-between border-b border-border-muted pb-2">
                    <dt className="text-secondary">Age/Gender</dt>
                    <dd className="font-medium text-on-surface">{patient.age} / {patient.gender}</dd>
                  </div>
                  <div className="mt-4 pt-2">
                    <Link href={`/doctor/patients/${patient.id}`}>
                      <Button variant="outline" className="w-full">View Full Profile</Button>
                    </Link>
                  </div>
                </dl>
              ) : (
                <p className="text-body-sm text-secondary">Patient data unavailable.</p>
              )}
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
