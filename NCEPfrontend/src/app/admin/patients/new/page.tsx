"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/providers/AuthProvider";
import { savePatient, saveUser, getDoctors, addAuditLog, getServiceErrorMessage, linkExistingPatient } from "@/services";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import type { Patient, User, PatientStatus, Doctor } from "@/types";

export default function AddPatient() {
  const { session } = useAuth();
  const router = useRouter();
  const { toast } = useToast();

  const [mode, setMode] = useState<"new" | "existing">("new");
  const [lookupId, setLookupId] = useState("");
  const [linking, setLinking] = useState(false);
  const [foundPatient, setFoundPatient] = useState<Patient | null>(null);

  const handleLookup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!lookupId.trim()) return;
    setLinking(true);
    setFoundPatient(null);
    try {
      const patient = await linkExistingPatient(lookupId.trim());
      setFoundPatient(patient);
      await addAuditLog({
        id: `log-${Date.now()}`,
        event: "Existing patient linked to hospital",
        eventType: "patient_updated",
        actorId: session?.userId || "unknown",
        actorName: session?.name || "Admin",
        actorRole: session?.role || "admin",
        organisationId: session?.organisationId || "",
        organisationName: "Current Org",
        resource: `Patient ${patient.id}`,
        result: "Success",
        ipAddress: "127.0.0.1",
        timestamp: new Date().toISOString(),
        details: `Patient ${patient.id} (${patient.name}) linked to this hospital -- their existing ECG records and reports are now visible here.`,
      });
      toast(`${patient.name} is now linked to your hospital.`, "success");
    } catch (error) {
      toast(getServiceErrorMessage(error), "error");
    } finally {
      setLinking(false);
    }
  };

  const [formData, setFormData] = useState({
    name: "",
    dateOfBirth: "",
    gender: "Female",
    email: "",
    phone: "",
    address: "",
    assignedDoctorId: "",
    medicalNotes: "",
    status: "Pending Upload" as PatientStatus,
  });

  const [orgDoctors, setOrgDoctors] = useState<Doctor[]>([]);

  useEffect(() => {
    getDoctors()
      .then((docs) =>
        setOrgDoctors(docs.filter((d) => d.organisationId === session?.organisationId))
      )
      .catch((err) => console.error("Error loading doctors:", err));
  }, [session?.organisationId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!session?.organisationId) return;

    try {
      const doctor = orgDoctors.find(d => d.id === formData.assignedDoctorId);
      if (!doctor) {
        toast("Please select an assigned doctor", "error");
        return;
      }
      
      // Basic age calculation
      const birthDate = new Date(formData.dateOfBirth);
      let age = new Date().getFullYear() - birthDate.getFullYear();
      const m = new Date().getMonth() - birthDate.getMonth();
      if (m < 0 || (m === 0 && new Date().getDate() < birthDate.getDate())) {
        age--;
      }

      const newPatId = `pat-${Math.floor(Math.random() * 1000).toString().padStart(3, "0")}`;
      const newUserId = `user-patient-${Math.floor(Math.random() * 10000).toString()}`;
      // Per NCEP convention, a patient's temporary password is their own ID + name --
      // easy for front-desk staff to hand over verbally, and the patient changes it on first login.
      const tempPassword = `${newPatId}_${formData.name}`;

      const newUser: User = {
        id: newUserId,
        email: formData.email,
        name: formData.name,
        password: tempPassword,
        role: "patient",
        organisationId: session.organisationId,
        status: "Active",
        lastActive: "—",
        createdAt: new Date().toISOString().split('T')[0],
      };

      const newPatient: Patient = {
        id: newPatId,
        name: formData.name,
        dateOfBirth: formData.dateOfBirth,
        age: age || 0,
        gender: formData.gender,
        email: formData.email,
        phone: formData.phone,
        address: formData.address,
        assignedDoctorId: formData.assignedDoctorId,
        assignedDoctor: doctor.name,
        organisationId: session.organisationId,
        status: formData.status,
        medicalNotes: formData.medicalNotes,
        createdAt: new Date().toISOString().split('T')[0],
      };

      await saveUser(newUser);
      await savePatient(newPatient);
      
      await addAuditLog({
        id: `log-${Date.now()}`,
        event: "New patient registered",
        eventType: "patient_created",
        actorId: session.userId,
        actorName: session.name,
        actorRole: session.role,
        organisationId: session.organisationId,
        organisationName: "Current Org", 
        resource: `Patient ${newPatId}`,
        result: "Success",
        ipAddress: "127.0.0.1",
        timestamp: new Date().toISOString(),
        details: `${formData.name} registered as new patient`,
      });

      toast(`Patient added. Temporary password: ${tempPassword}`, "success");
      setTimeout(() => router.push("/admin/patients"), 3500);
    } catch (error) {
      toast(getServiceErrorMessage(error), "error");
    }
  };

  return (
    <div className="space-y-8 max-w-3xl">
      <PageHeader
        title="Add New Patient"
        description="Register a new patient, or link one who's already registered at another hospital."
      />

      <div className="flex gap-2 rounded-xl border border-border-muted bg-surface-bright p-1">
        <button
          type="button"
          onClick={() => setMode("new")}
          className={`flex-1 rounded-lg px-4 py-2 text-body-sm font-medium transition-colors ${mode === "new" ? "bg-surface text-primary shadow-sm" : "text-secondary hover:text-on-surface"}`}
        >
          Register New Patient
        </button>
        <button
          type="button"
          onClick={() => setMode("existing")}
          className={`flex-1 rounded-lg px-4 py-2 text-body-sm font-medium transition-colors ${mode === "existing" ? "bg-surface text-primary shadow-sm" : "text-secondary hover:text-on-surface"}`}
        >
          Link Existing Patient (by ID)
        </button>
      </div>

      {mode === "existing" ? (
        <Card className="p-8">
          <form onSubmit={handleLookup} className="space-y-6">
            <p className="text-body-sm text-secondary">
              Enter the patient&apos;s ID to link them to your hospital. Their existing ECG records and reports
              become visible here immediately -- nothing is moved or duplicated, and this works even if the
              patient is currently registered at a different hospital.
            </p>
            <Input
              label="Patient ID *"
              name="lookupId"
              placeholder="e.g. pat-001"
              value={lookupId}
              onChange={(e) => setLookupId(e.target.value)}
              required
            />
            <div className="flex justify-end gap-4 pt-4 border-t border-border-muted">
              <Button variant="outline" type="button" onClick={() => router.back()}>
                Cancel
              </Button>
              <Button type="submit" disabled={linking}>
                {linking ? "Looking up..." : "Look Up & Link"}
              </Button>
            </div>
          </form>

          {foundPatient && (
            <div className="mt-6 rounded-xl border border-border-muted bg-surface-bright p-5">
              <p className="text-body-sm font-medium text-on-surface">{foundPatient.name}</p>
              <p className="mt-1 text-caption text-secondary">
                {foundPatient.id} · {foundPatient.email || "No email on file"}
              </p>
              <Button
                className="mt-4"
                onClick={() => router.push(`/admin/patients/${foundPatient.id}`)}
              >
                View Patient
              </Button>
            </div>
          )}
        </Card>
      ) : (
      <Card className="p-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            <Input
              label="Full Name *"
              name="name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
            />
            <Input
              label="Email Address *"
              type="email"
              name="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
            />
            <Input
              label="Date of Birth *"
              type="date"
              name="dateOfBirth"
              value={formData.dateOfBirth}
              onChange={(e) => setFormData({ ...formData, dateOfBirth: e.target.value })}
              required
            />
            <div className="space-y-1.5">
              <label className="text-body-sm font-medium text-on-surface-variant">Gender *</label>
              <select
                value={formData.gender}
                onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
                className="h-input-height w-full rounded-xl border border-border-muted bg-surface px-4 text-body-lg text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
              >
                <option value="Female">Female</option>
                <option value="Male">Male</option>
                <option value="Other">Other</option>
              </select>
            </div>
            
            <div className="space-y-1.5">
              <label className="text-body-sm font-medium text-on-surface-variant">Assigned Doctor *</label>
              <select
                required
                value={formData.assignedDoctorId}
                onChange={(e) => setFormData({ ...formData, assignedDoctorId: e.target.value })}
                className="h-input-height w-full rounded-xl border border-border-muted bg-surface px-4 text-body-lg text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
              >
                <option value="" disabled>Select Doctor...</option>
                {orgDoctors.map(doc => (
                  <option key={doc.id} value={doc.id}>{doc.name}</option>
                ))}
              </select>
            </div>
            <Input
              label="Phone Number *"
              name="phone"
              value={formData.phone}
              onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
              required
            />
            
            <div className="sm:col-span-2">
              <Input
                label="Home Address"
                name="address"
                value={formData.address}
                onChange={(e) => setFormData({ ...formData, address: e.target.value })}
              />
            </div>
          </div>
          <div className="flex justify-end gap-4 pt-4 border-t border-border-muted">
            <Button variant="outline" type="button" onClick={() => router.back()}>
              Cancel
            </Button>
            <Button type="submit">
              Register Patient
            </Button>
          </div>
        </form>
      </Card>
      )}
    </div>
  );
}
