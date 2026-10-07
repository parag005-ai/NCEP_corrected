"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/providers/AuthProvider";
import { addAuditLog, getOrganisations, getUserById, saveUser } from "@/services";
import type { Organisation, User, UserStatus } from "@/types";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";

export default function AdminEditor() {
  const { session } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();
  const adminId = searchParams.get("adminId") || "";
  
  const [admin, setAdmin] = useState<User | null>(null);
  const [organisations, setOrganisations] = useState<Organisation[]>([]);

  useEffect(() => {
    getUserById(adminId).then(u => setAdmin(u || null));
    getOrganisations().then(setOrganisations);
  }, [adminId]);
  const [confirmingStatusChange, setConfirmingStatusChange] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    phone: "",
    role: "admin",
    organisationId: "",
    status: "Active" as UserStatus,
  });

  useEffect(() => {
    if (!admin) return;
    setFormData({
      name: admin.name,
      email: admin.email,
      phone: admin.phone || "",
      role: admin.role,
      organisationId: admin.organisationId,
      status: admin.status,
    });
  }, [admin]);

  const saveChanges = async (nextStatus = formData.status) => {
    if (!admin) return;
    if (admin.id === session?.userId && nextStatus !== "Active") {
      toast("You cannot deactivate your own administrator account.", "error");
      return;
    }
    if (formData.role === "admin" && !formData.organisationId) {
      toast("Please select an organisation for this Org Admin.", "error");
      return;
    }

    const organisationId = formData.role === "superadmin" ? "org-001" : formData.organisationId;
    const updatedAdmin = {
      ...admin,
      name: formData.name,
      email: formData.email,
      phone: formData.phone,
      role: formData.role as "admin" | "superadmin",
      organisationId,
      status: nextStatus,
    };
    await saveUser(updatedAdmin);

    await addAuditLog({
      id: `log-${Date.now()}`,
      event: nextStatus !== admin.status ? "Admin account status updated" : "Admin account updated",
      eventType: "user_updated",
      actorId: session?.userId || "unknown",
      actorName: session?.name || "Superadmin",
      actorRole: session?.role || "superadmin",
      organisationId,
      organisationName: organisations.find((organisation) => organisation.id === organisationId)?.name || "Platform Wide",
      resource: `User ${admin.id}`,
      result: "Success",
      ipAddress: "127.0.0.1",
      timestamp: new Date().toISOString(),
      details: `${updatedAdmin.name}'s administrator details were updated${nextStatus !== admin.status ? ` and account status set to ${nextStatus}` : ""}.`,
    });

    toast(nextStatus !== admin.status ? `Admin account ${nextStatus.toLowerCase()}` : "Administrator details updated", "success");
    router.push("/superadmin/admins");
  };

  if (!admin || (admin.role !== "admin" && admin.role !== "superadmin")) {
    return (
      <div className="space-y-8">
        <PageHeader title="Administrator not found" description="The administrator may have been removed or the link is invalid." />
        <EmptyState title="Administrator not found" description="Return to the administrators list to select an account." />
      </div>
    );
  }

  const nextStatus = admin.status === "Active" ? "Inactive" : "Active";

  return (
    <div className="max-w-3xl space-y-8">
      <PageHeader title="Edit Administrator" description="Update administrator details and manage account access." />

      <Card className="p-8">
        <form className="space-y-6" onSubmit={(event) => { event.preventDefault(); saveChanges(); }}>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            <Input label="Full Name *" name="name" value={formData.name} onChange={(event) => setFormData({ ...formData, name: event.target.value })} required />
            <Input label="Email Address *" type="email" name="email" value={formData.email} onChange={(event) => setFormData({ ...formData, email: event.target.value })} required />
            <Input label="Phone Number *" type="tel" name="phone" value={formData.phone} onChange={(event) => setFormData({ ...formData, phone: event.target.value })} placeholder="+91 98765 43210" inputMode="tel" pattern="[0-9+() -]{7,20}" title="Enter a valid phone number" required />

            <div className="space-y-1.5">
              <label className="text-body-sm font-medium text-on-surface-variant">Admin Type *</label>
              <select
                value={formData.role}
                onChange={(event) => setFormData({ ...formData, role: event.target.value, organisationId: event.target.value === "superadmin" ? "org-001" : "" })}
                className="h-input-height w-full rounded-xl border border-border-muted bg-surface px-4 text-body-lg text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
              >
                <option value="admin">Hospital Admin</option>
                <option value="superadmin">Platform Admin (Superadmin)</option>
              </select>
            </div>

            {formData.role === "admin" && (
              <div className="space-y-1.5">
                <label className="text-body-sm font-medium text-on-surface-variant">Hospital *</label>
                <select required value={formData.organisationId} onChange={(event) => setFormData({ ...formData, organisationId: event.target.value })} className="h-input-height w-full rounded-xl border border-border-muted bg-surface px-4 text-body-lg text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary">
                  <option value="" disabled>Select Hospital...</option>
                  {organisations.map((organisation) => <option key={organisation.id} value={organisation.id}>{organisation.name}</option>)}
                </select>
              </div>
            )}

            <div className="space-y-1.5">
              <label className="text-body-sm font-medium text-on-surface-variant">Account Status</label>
              <select value={formData.status} onChange={(event) => setFormData({ ...formData, status: event.target.value as UserStatus })} className="h-input-height w-full rounded-xl border border-border-muted bg-surface px-4 text-body-lg text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary">
                <option value="Active">Active</option>
                <option value="Inactive">Inactive</option>
                <option value="Suspended">Suspended</option>
                <option value="Invited">Invited</option>
              </select>
            </div>
          </div>

          <div className="flex flex-wrap justify-end gap-4 border-t border-border-muted pt-6">
            <Button variant="outline" type="button" onClick={() => router.push("/superadmin/admins")}>Cancel</Button>
            <Button type="submit">Save Changes</Button>
          </div>
        </form>
      </Card>

      <Card className="border-error/30 p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="font-semibold text-on-surface">Account access</h2>
            <p className="mt-1 text-body-sm text-secondary">{nextStatus === "Inactive" ? "Deactivate this account to prevent the administrator from signing in." : "Reactivate this account to restore administrator access."}</p>
          </div>
          <Button variant="outline" type="button" className={nextStatus === "Inactive" ? "border-error text-error hover:bg-error/5" : ""} onClick={() => setConfirmingStatusChange(true)} disabled={admin.id === session?.userId}>
            {nextStatus === "Inactive" ? "Deactivate Administrator" : "Activate Administrator"}
          </Button>
        </div>
        {admin.id === session?.userId && <p className="mt-3 text-caption text-secondary">Your own administrator account cannot be deactivated here.</p>}
      </Card>

      <ConfirmDialog
        open={confirmingStatusChange}
        title={`${nextStatus} administrator?`}
        description={`This will ${nextStatus === "Inactive" ? "prevent" : "allow"} ${admin.name} from signing in.`}
        confirmLabel={nextStatus === "Inactive" ? "Deactivate" : "Activate"}
        variant={nextStatus === "Inactive" ? "danger" : "default"}
        onCancel={() => setConfirmingStatusChange(false)}
        onConfirm={() => { setConfirmingStatusChange(false); saveChanges(nextStatus); }}
      />
    </div>
  );
}
