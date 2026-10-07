"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/providers/AuthProvider";
import { addAuditLog, deleteUser, getDoctors, getOrganisations, getPatients, getUserById, saveDoctor, savePatient, saveUser } from "@/services";
import type { Organisation, Doctor, Patient, User } from "@/types";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import type { UserStatus } from "@/types";

export default function SuperAdminUserEditor() {
  const { session } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const { toast } = useToast();
  const userId = params.get("userId") || "";
  const [user, setUser] = useState<User | null>(null);
  const [organisations, setOrganisations] = useState<Organisation[]>([]);
  const [doctor, setDoctor] = useState<Doctor | undefined>(undefined);
  const [patient, setPatient] = useState<Patient | undefined>(undefined);

  useEffect(() => {
    getOrganisations().then(setOrganisations);
    getUserById(userId).then(u => setUser(u || null));
  }, [userId]);

  useEffect(() => {
    if (user) {
      if (user.role === 'doctor') {
        getDoctors().then(docs => setDoctor(docs.find((entry) => entry.userId === user.id)));
      } else if (user.role === 'patient') {
        getPatients().then(pats => setPatient(pats.find((entry) => entry.email.toLowerCase() === user.email.toLowerCase())));
      }
    }
  }, [user]);
  const [formData, setFormData] = useState({ name: "", email: "", phone: "", organisationId: "", status: "Active" as UserStatus, speciality: "", staffRole: "Doctor" });
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  useEffect(() => {
    if (!user) return;
    setFormData({ name: user.name, email: user.email, phone: patient?.phone || user.phone || "", organisationId: user.organisationId, status: user.status, speciality: doctor?.speciality || "", staffRole: doctor?.role || "Doctor" });
  }, [doctor, patient, user]);

  const [orgSearch, setOrgSearch] = useState("");
  const [showOrgDropdown, setShowOrgDropdown] = useState(false);
  
  useEffect(() => {
    if (formData.organisationId && organisations.length > 0 && !orgSearch) {
      const org = organisations.find(o => o.id === formData.organisationId);
      if (org) setOrgSearch(org.name);
    }
  }, [formData.organisationId, organisations, orgSearch]);

  if (!user) return <div className="space-y-8"><PageHeader title="User not found" description="The selected account could not be found." /><EmptyState title="User not found" description="Return to Manage Users and select an account." /></div>;

  const typeLabel = user.role === "doctor" ? "Doctor / Staff" : user.role === "patient" ? "Patient" : "Administrator";
  const saveChanges = async () => {
    if (user.id === session?.userId && formData.status !== "Active") { toast("You cannot deactivate your own administrator account.", "error"); return; }
    const updatedUser = { ...user, name: formData.name, email: formData.email, phone: formData.phone, organisationId: formData.organisationId, status: formData.status };
    await saveUser(updatedUser);
    if (doctor) await saveDoctor({ ...doctor, name: formData.name, email: formData.email, organisationId: formData.organisationId, status: formData.status, speciality: formData.speciality, role: formData.staffRole as typeof doctor.role });
    if (patient) await savePatient({ ...patient, name: formData.name, email: formData.email, phone: formData.phone, organisationId: formData.organisationId });
    await addAuditLog({ id: `log-${Date.now()}`, event: "User account updated", eventType: "user_updated", actorId: session?.userId || "unknown", actorName: session?.name || "Superadmin", actorRole: session?.role || "superadmin", organisationId: formData.organisationId, organisationName: organisations.find((organisation) => organisation.id === formData.organisationId)?.name || "Platform Wide", resource: `User ${user.id}`, result: "Success", ipAddress: "127.0.0.1", timestamp: new Date().toISOString(), details: `${formData.name}'s ${typeLabel.toLowerCase()} account was updated.` });
    toast("User details updated", "success");
    router.push("/superadmin/users");
  };

  const deleteAccount = async () => {
    if (user.id === session?.userId) {
      toast("You cannot delete your own administrator account.", "error");
      setConfirmingDelete(false);
      return;
    }
    await deleteUser(user.id);
    await addAuditLog({ id: `log-${Date.now()}`, event: "User account deleted", eventType: "user_deactivated", actorId: session?.userId || "unknown", actorName: session?.name || "Superadmin", actorRole: session?.role || "superadmin", organisationId: user.organisationId, organisationName: organisations.find((organisation) => organisation.id === user.organisationId)?.name || "Platform Wide", resource: `User ${user.id}`, result: "Success", ipAddress: "127.0.0.1", timestamp: new Date().toISOString(), details: `${user.name}'s platform account was deleted by a superadmin.` });
    toast(`${user.name}'s account was deleted`, "success");
    router.push("/superadmin/users");
  };

    return (
    <div className="max-w-3xl space-y-8">
      <PageHeader title={`Edit ${typeLabel}`} description="Update user details, organisation assignment, and account access." />
      <Card className="p-8"><form className="space-y-6" onSubmit={(event) => { event.preventDefault(); saveChanges(); }}><div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        <Input label="Full Name *" name="name" value={formData.name} onChange={(event) => setFormData({ ...formData, name: event.target.value })} required />
        <Input label="Email Address *" type="email" name="email" value={formData.email} onChange={(event) => setFormData({ ...formData, email: event.target.value })} required />
        <Input label="Phone Number" type="tel" name="phone" value={formData.phone} onChange={(event) => setFormData({ ...formData, phone: event.target.value })} placeholder="+91 98765 43210" inputMode="tel" pattern="[0-9+() -]{7,20}" title="Enter a valid phone number" />
        <div className="space-y-1.5 relative">
          <label className="text-body-sm font-medium text-on-surface-variant">Hospital *</label>
          <input 
            type="text" 
            value={orgSearch}
            onChange={(e) => {
              setOrgSearch(e.target.value);
              setShowOrgDropdown(e.target.value.length >= 3);
              if (e.target.value === "") setFormData({ ...formData, organisationId: "" });
            }}
            onFocus={() => { if (orgSearch.length >= 3) setShowOrgDropdown(true) }}
            onBlur={() => setTimeout(() => setShowOrgDropdown(false), 200)}
            disabled={user.role === "superadmin"}
            placeholder="Type at least 3 characters..."
            className="h-input-height w-full rounded-xl border border-border-muted bg-surface px-4 text-body-lg text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary disabled:opacity-50"
            required={user.role !== "superadmin"}
          />
          {showOrgDropdown && !user.role?.includes("superadmin") && (
            <div className="absolute z-10 w-full mt-1 bg-surface border border-border-muted rounded-xl shadow-lg max-h-60 overflow-auto">
              {organisations.filter(o => o.name.toLowerCase().includes(orgSearch.toLowerCase())).map(org => (
                <div 
                  key={org.id} 
                  className="px-4 py-2 hover:bg-surface-bright cursor-pointer text-body-sm text-on-surface"
                  onClick={() => {
                    setOrgSearch(org.name);
                    setFormData({ ...formData, organisationId: org.id });
                    setShowOrgDropdown(false);
                  }}
                >
                  {org.name}
                </div>
              ))}
              {organisations.filter(o => o.name.toLowerCase().includes(orgSearch.toLowerCase())).length === 0 && (
                <div className="px-4 py-2 text-body-sm text-secondary">No hospitals found.</div>
              )}
            </div>
          )}
        </div>
        {doctor && <><div className="space-y-1.5"><label className="text-body-sm font-medium text-on-surface-variant">Staff Role</label><select value={formData.staffRole} onChange={(event) => setFormData({ ...formData, staffRole: event.target.value })} className="h-input-height w-full rounded-xl border border-border-muted bg-surface px-4 text-body-lg text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"><option value="Doctor">Doctor</option><option value="Technician">Technician</option><option value="Support Staff">Support Staff</option></select></div><Input label="Speciality" name="speciality" value={formData.speciality} onChange={(event) => setFormData({ ...formData, speciality: event.target.value })} /></>}
        <div className="space-y-1.5"><label className="text-body-sm font-medium text-on-surface-variant">Account Status</label><select value={formData.status} onChange={(event) => setFormData({ ...formData, status: event.target.value as UserStatus })} className="h-input-height w-full rounded-xl border border-border-muted bg-surface px-4 text-body-lg text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"><option value="Active">Active</option><option value="Inactive">Inactive</option><option value="Suspended">Suspended</option><option value="Invited">Invited</option></select></div>
      </div><div className="flex justify-end gap-4 border-t border-border-muted pt-6"><Button variant="outline" type="button" onClick={() => router.push("/superadmin/users")}>Cancel</Button><Button type="submit">Save Changes</Button></div></form></Card>
      <Card className="border-error/30 p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div><h2 className="font-semibold text-error">Delete account</h2><p className="mt-1 text-body-sm text-secondary">Permanently remove this user&apos;s platform login. Clinical records are retained.</p></div>
          <Button variant="outline" type="button" className="border-error text-error hover:bg-error/5" onClick={() => setConfirmingDelete(true)} disabled={user.id === session?.userId}>Delete User</Button>
        </div>
        {user.id === session?.userId && <p className="mt-3 text-caption text-secondary">Your own administrator account cannot be deleted here.</p>}
      </Card>
      <ConfirmDialog open={confirmingDelete} title="Are you sure?" description={`Delete ${user.name}'s platform account? This cannot be undone.`} confirmLabel="Yes, delete" cancelLabel="No, keep account" variant="danger" onCancel={() => setConfirmingDelete(false)} onConfirm={deleteAccount} />
    </div>
  );
}
