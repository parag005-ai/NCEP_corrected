/* eslint-disable @next/next/no-img-element */
"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/providers/AuthProvider";
import { addAuditLog, deleteOrganisation, getOrganisationById, saveOrganisation } from "@/services";
import type { Organisation } from "@/types";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { Building2, Camera } from "lucide-react";

export default function SuperAdminOrganisationEditor() {
  const { session } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();
  const organisationId = searchParams.get("organisationId") || "";
  const [organisation, setOrganisation] = useState<Organisation | null>(null);
  
  useEffect(() => {
    getOrganisationById(organisationId).then(o => setOrganisation(o || null));
  }, [organisationId]);
  const [formData, setFormData] = useState({ name: "", address: "", contact: "", status: "Active", plan: "Starter" as "Starter" | "Professional" | "Enterprise", logoUrl: "" });
  const [confirmingStatusChange, setConfirmingStatusChange] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [confirmingFinalDelete, setConfirmingFinalDelete] = useState(false);

  useEffect(() => {
    if (!organisation) return;
    setFormData({ name: organisation.name, address: organisation.address, contact: organisation.contact, status: organisation.status, plan: organisation.plan || "Starter", logoUrl: organisation.logoUrl || "" });
  }, [organisation]);

  if (!organisation) return <div className="space-y-8"><PageHeader title="Hospital not found" description="The selected hospital could not be found." /><EmptyState title="Hospital not found" description="Return to Hospitals and select a hospital." /></div>;

  const saveChanges = async (status = formData.status) => {
    const updatedOrganisation = { ...organisation, name: formData.name, address: formData.address, contact: formData.contact, status: status as "Active" | "Inactive", plan: formData.plan, logoUrl: formData.logoUrl || undefined };
    await saveOrganisation(updatedOrganisation);
    await addAuditLog({ id: `log-${Date.now()}`, event: status !== organisation.status ? "Organisation status updated" : "Organisation details updated", eventType: "org_updated", actorId: session?.userId || "unknown", actorName: session?.name || "Superadmin", actorRole: session?.role || "superadmin", organisationId: organisation.id, organisationName: updatedOrganisation.name, resource: `Organisation ${organisation.id}`, result: "Success", ipAddress: "127.0.0.1", timestamp: new Date().toISOString(), details: `${updatedOrganisation.name} was updated${status !== organisation.status ? ` and marked as ${status}` : ""}.` });
    toast(status !== organisation.status ? `Hospital ${status.toLowerCase()}` : "Hospital details updated", "success");
    router.push("/superadmin/hospitals");
  };

  const deleteConfirmedOrganisation = async () => {
    await deleteOrganisation(organisation.id);
    await addAuditLog({ id: `log-${Date.now()}`, event: "Organisation deleted", eventType: "org_updated", actorId: session?.userId || "unknown", actorName: session?.name || "Superadmin", actorRole: session?.role || "superadmin", organisationId: organisation.id, organisationName: organisation.name, resource: `Organisation ${organisation.id}`, result: "Success", ipAddress: "127.0.0.1", timestamp: new Date().toISOString(), details: `${organisation.name} was deleted after two superadmin confirmations.` });
    toast(`${organisation.name} was deleted`, "success");
    router.push("/superadmin/hospitals");
  };

  const nextStatus = organisation.status === "Active" ? "Inactive" : "Active";

  return (
    <div className="max-w-3xl space-y-8">
      <PageHeader title="Edit Hospital" description="Update hospital details and manage its platform access." />
      <Card className="p-8"><form className="space-y-6" onSubmit={(event) => { event.preventDefault(); saveChanges(); }}><div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        
        {/* Organisation Photo Upload */}
        <div className="sm:col-span-2 flex flex-col sm:flex-row items-start sm:items-center gap-6 p-4 rounded-xl border border-border-muted bg-surface-container-low">
          <div className="relative h-20 w-20 rounded-xl bg-surface border-2 border-primary/20 overflow-hidden flex items-center justify-center shrink-0">
            {formData.logoUrl ? (
              <img src={formData.logoUrl} alt="Hospital preview" className="h-full w-full object-cover" />
            ) : (
              <Building2 className="h-10 w-10 text-secondary" />
            )}
          </div>
          <div className="space-y-1.5 flex-1">
            <h3 className="text-body-md font-medium text-on-surface">Hospital Photo / Logo</h3>
            <p className="text-caption text-secondary">
              Recommended format: PNG, JPG, or WEBP (1:1 square ratio, min 400x400px, max 5MB). Displays in dashboards and patient reports.
            </p>
            <div className="flex items-center gap-3 pt-1">
              <label className="cursor-pointer inline-flex items-center gap-2 rounded-xl border border-border-muted bg-surface px-4 py-2 text-body-sm font-medium transition-colors hover:bg-surface-bright focus:outline-none focus:ring-2 focus:ring-primary/20">
                <Camera className="h-4 w-4 text-primary" />
                Upload Photo
                <input 
                  type="file" 
                  className="hidden" 
                  accept="image/png,image/jpeg,image/webp,image/svg+xml" 
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                      const reader = new FileReader();
                      reader.onloadend = () => {
                        setFormData(prev => ({ ...prev, logoUrl: reader.result as string }));
                      };
                      reader.readAsDataURL(file);
                    }
                  }} 
                />
              </label>
              {formData.logoUrl && (
                <button 
                  type="button" 
                  onClick={() => setFormData(prev => ({ ...prev, logoUrl: "" }))} 
                  className="text-body-sm text-error hover:underline"
                >
                  Remove
                </button>
              )}
            </div>
          </div>
        </div>

        <Input label="Hospital Name *" name="name" value={formData.name} onChange={(event) => setFormData({ ...formData, name: event.target.value })} required />
        <Input label="Contact Number *" type="tel" name="contact" value={formData.contact} onChange={(event) => setFormData({ ...formData, contact: event.target.value })} required />
        <div className="sm:col-span-2"><Input label="Full Address *" name="address" value={formData.address} onChange={(event) => setFormData({ ...formData, address: event.target.value })} required /></div>

        <div className="space-y-1.5"><label className="text-body-sm font-medium text-on-surface-variant">Subscription Plan</label><select value={formData.plan} onChange={(event) => setFormData({ ...formData, plan: event.target.value as typeof formData.plan })} className="h-input-height w-full rounded-xl border border-border-muted bg-surface px-4 text-body-lg text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"><option value="Starter">Starter</option><option value="Professional">Professional</option><option value="Enterprise">Enterprise</option></select></div>
      </div><div className="flex justify-end gap-4 border-t border-border-muted pt-6"><Button variant="outline" type="button" onClick={() => router.push("/superadmin/hospitals")}>Cancel</Button><Button type="submit">Save Changes</Button></div></form></Card>

      <Card className="p-6"><div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="font-semibold text-on-surface">Hospital access</h2><p className="mt-1 text-body-sm text-secondary">{nextStatus === "Inactive" ? "Deactivate this hospital to prevent access to the platform." : "Activate this hospital to restore platform access."}</p></div><Button variant="outline" type="button" onClick={() => setConfirmingStatusChange(true)}>{nextStatus === "Inactive" ? "Deactivate Hospital" : "Activate Hospital"}</Button></div></Card>

      <Card className="border-error/30 p-6"><div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="font-semibold text-error">Delete hospital</h2><p className="mt-1 text-body-sm text-secondary">Permanently remove this hospital from the platform.</p></div><Button variant="outline" type="button" className="border-error text-error hover:bg-error/5" onClick={() => setConfirmingDelete(true)}>Delete Hospital</Button></div></Card>

      <ConfirmDialog open={confirmingStatusChange} title={`${nextStatus} hospital?`} description={`This will ${nextStatus === "Inactive" ? "prevent" : "restore"} hospital access to the platform.`} confirmLabel={nextStatus === "Inactive" ? "Deactivate" : "Activate"} cancelLabel="Cancel" variant={nextStatus === "Inactive" ? "danger" : "default"} onCancel={() => setConfirmingStatusChange(false)} onConfirm={() => { setConfirmingStatusChange(false); saveChanges(nextStatus); }} />
      <ConfirmDialog open={confirmingDelete} title="Are you sure?" description={`Delete ${organisation.name}? You will need to confirm once more before it is removed.`} confirmLabel="Yes, continue" cancelLabel="No, keep hospital" variant="danger" onCancel={() => setConfirmingDelete(false)} onConfirm={() => { setConfirmingDelete(false); setConfirmingFinalDelete(true); }} />
      <ConfirmDialog open={confirmingFinalDelete} title="Final confirmation" description={`Permanently delete ${organisation.name}? This action cannot be undone.`} confirmLabel="Yes, delete hospital" cancelLabel="No, keep hospital" variant="danger" onCancel={() => setConfirmingFinalDelete(false)} onConfirm={deleteConfirmedOrganisation} />
    </div>
  );
}

