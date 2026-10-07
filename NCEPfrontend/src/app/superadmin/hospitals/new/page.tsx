/* eslint-disable @next/next/no-img-element */
"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/providers/AuthProvider";
import { saveOrganisation, saveUser, addAuditLog, getUsers } from "@/services";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import type { Organisation, User } from "@/types";
import { Building2, Camera } from "lucide-react";

type PendingAdmin = { name: string; email: string; phone: string; password: string };

export default function SuperAdminAddOrganisation() {
  const { session } = useAuth();
  const router = useRouter();
  const { toast } = useToast();

  const [formData, setFormData] = useState({
    name: "",
    address: "",
    contact: "",
    adminId: "",
    plan: "Starter" as "Starter" | "Professional" | "Enterprise",
    logoUrl: "",
  });

  // A brand-new admin (created via the "+ Add Admin" option below) can't be
  // persisted until this organisation exists -- organisationId is a real
  // foreign key. Its details are held here and the User row is only created
  // once this form creates the organisation it needs to point to.
  const [pendingAdmin, setPendingAdmin] = useState<PendingAdmin | null>(null);

  useEffect(() => {
    const stored = sessionStorage.getItem("pendingHospitalAdmin");
    if (stored) {
      setPendingAdmin(JSON.parse(stored) as PendingAdmin);
      sessionStorage.removeItem("pendingHospitalAdmin");
    }
  }, []);

  const [admins, setAdmins] = useState<import("@/types").User[]>([]);
  useEffect(() => {
    getUsers().then(users => setAdmins(users.filter(u => u.role === "admin")));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const newOrgId = `org-${Math.floor(Math.random() * 1000).toString().padStart(3, "0")}`;
    const newAdminUserId = pendingAdmin ? `user-admin-${Math.floor(Math.random() * 10000)}` : null;

    const newOrganisation: Organisation = {
      id: newOrgId,
      name: formData.name,
      address: formData.address,
      contact: formData.contact,
      adminId: newAdminUserId || formData.adminId,
      status: "Active",
      createdAt: new Date().toISOString().split('T')[0],
      totalUsers: pendingAdmin ? 1 : 0,
      totalPatients: 0,
      plan: formData.plan,
      logoUrl: formData.logoUrl || undefined,
    };

    // Organisation must exist first: the admin's organisationId is a real
    // foreign key against it.
    await saveOrganisation(newOrganisation);

    if (pendingAdmin && newAdminUserId) {
      const newAdmin: User = {
        id: newAdminUserId,
        email: pendingAdmin.email,
        name: pendingAdmin.name,
        phone: pendingAdmin.phone,
        password: pendingAdmin.password,
        role: "admin",
        organisationId: newOrgId,
        status: "Active",
        lastActive: "—",
        createdAt: new Date().toISOString().split('T')[0],
      };
      await saveUser(newAdmin);

      await addAuditLog({
        id: `log-${Date.now()}`,
        event: "Admin account created",
        eventType: "user_created",
        actorId: session?.userId || "unknown",
        actorName: session?.name || "Superadmin",
        actorRole: session?.role || "superadmin",
        organisationId: newOrgId,
        organisationName: formData.name,
        resource: `User ${newAdminUserId}`,
        result: "Success",
        ipAddress: "127.0.0.1",
        timestamp: new Date().toISOString(),
        details: `${pendingAdmin.name} onboarded as Org Admin`,
      });
    }

    await addAuditLog({
      id: `log-${Date.now()}`,
      event: "New organisation created",
      eventType: "org_created",
      actorId: session?.userId || "unknown",
      actorName: session?.name || "Superadmin",
      actorRole: session?.role || "superadmin",
      organisationId: newOrgId,
      organisationName: formData.name,
      resource: `Organisation ${newOrgId}`,
      result: "Success",
      ipAddress: "127.0.0.1",
      timestamp: new Date().toISOString(),
      details: `${formData.name} onboarded`,
    });

    toast("Hospital added successfully", "success");
    router.push("/superadmin/hospitals");
  };

  return (
    <div className="space-y-8 max-w-3xl">
      <PageHeader
        title="Add New Hospital"
        description="Onboard a new hospital to the platform."
      />

      <Card className="p-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
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

            <Input
              label="Hospital Name *"
              name="name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
            />
            <Input
              label="Contact Number *"
              name="contact"
              value={formData.contact}
              onChange={(e) => setFormData({ ...formData, contact: e.target.value })}
              required
            />
            
            <div className="sm:col-span-2">
              <Input
                label="Full Address *"
                name="address"
                value={formData.address}
                onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                required
              />
            </div>

            <div className="sm:col-span-2 space-y-1.5">
              <label className="text-body-sm font-medium text-on-surface-variant">Primary Admin (Optional)</label>
              {pendingAdmin ? (
                <div className="flex items-center justify-between rounded-xl border border-border-muted bg-surface px-4 py-2.5">
                  <span className="text-body-lg text-on-surface">
                    {pendingAdmin.name} ({pendingAdmin.email}) <span className="text-caption text-secondary">-- will be created with this hospital</span>
                  </span>
                  <button type="button" onClick={() => setPendingAdmin(null)} className="text-body-sm text-error hover:underline">
                    Remove
                  </button>
                </div>
              ) : (
                <select
                  value={formData.adminId}
                  onChange={(e) => {
                    if (e.target.value === "add_new_admin") {
                      // Redirect to add admin page with returnTo param
                      router.push("/superadmin/admins/new?returnTo=/superadmin/hospitals/new");
                    } else {
                      setFormData({ ...formData, adminId: e.target.value });
                    }
                  }}
                  className="h-input-height w-full rounded-xl border border-border-muted bg-surface px-4 text-body-lg text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                >
                  <option value="" disabled>Select an admin...</option>
                  <option value="add_new_admin">+ Add Admin</option>
                  {admins.map(admin => (
                    <option key={admin.id} value={admin.id}>{admin.name} ({admin.email})</option>
                  ))}
                </select>
              )}
            </div>
            <div className="sm:col-span-2 space-y-1.5">
              <label className="text-body-sm font-medium text-on-surface-variant">Subscription Plan</label>
              <select value={formData.plan} onChange={(e) => setFormData({ ...formData, plan: e.target.value as typeof formData.plan })} className="h-input-height w-full rounded-xl border border-border-muted bg-surface px-4 text-body-lg text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary">
                <option value="Starter">Starter</option>
                <option value="Professional">Professional</option>
                <option value="Enterprise">Enterprise</option>
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-4 pt-4 border-t border-border-muted">
            <Button variant="outline" type="button" onClick={() => router.back()}>
              Cancel
            </Button>
            <Button type="submit">
              Register Hospital
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

