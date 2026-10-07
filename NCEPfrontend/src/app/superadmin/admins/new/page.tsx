"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/providers/AuthProvider";
import { saveUser, getOrganisations, addAuditLog } from "@/services";
import type { User, Organisation } from "@/types";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { generateTempPassword } from "@/lib/utils";
import { RefreshCw } from "lucide-react";

export default function SuperAdminAddAdmin() {
  const { session } = useAuth();
  const router = useRouter();
  const { toast } = useToast();

  const [formData, setFormData] = useState({
    name: "",
    email: "",
    phone: "",
    role: "admin", // admin or superadmin
    organisationId: "",
    password: generateTempPassword(),
  });

  const isFromNewOrg = typeof window !== "undefined" && new URLSearchParams(window.location.search).get("returnTo")?.includes("/superadmin/hospitals/new");

  const [orgs, setOrgs] = useState<Organisation[]>([]);
  useEffect(() => {
    getOrganisations().then(setOrgs);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // The hospital this admin belongs to doesn't exist yet in this flow --
    // organisationId is a real foreign key, so the user record can't be
    // created until the hospital is. Stash the form and let the hospital
    // form create both (organisation first, then this admin) on submit.
    if (isFromNewOrg) {
      sessionStorage.setItem(
        "pendingHospitalAdmin",
        JSON.stringify({ name: formData.name, email: formData.email, phone: formData.phone, password: formData.password }),
      );
      router.push("/superadmin/hospitals/new");
      return;
    }

    if (formData.role === "admin") {
      if (!orgs.find(o => o.id === formData.organisationId)) {
        toast("Please select a valid organisation from the list", "error");
        return;
      }
    }

    const newUserId = `user-${formData.role}-${Math.floor(Math.random() * 10000).toString()}`;
    const orgId = formData.role === "superadmin" ? "org-001" : formData.organisationId;

    const newUser: User = {
      id: newUserId,
      email: formData.email,
      name: formData.name,
      phone: formData.phone,
      password: formData.password,
      role: formData.role as "admin" | "superadmin",
      organisationId: orgId, // Superadmins usually belong to a platform-level org or default
      status: "Active",
      lastActive: "—",
      createdAt: new Date().toISOString().split('T')[0],
    };

    await saveUser(newUser);

    await addAuditLog({
      id: `log-${Date.now()}`,
      event: "Admin account created",
      eventType: "user_created",
      actorId: session?.userId || "unknown",
      actorName: session?.name || "Superadmin",
      actorRole: session?.role || "superadmin",
      organisationId: orgId,
      organisationName: orgs.find(o => o.id === orgId)?.name || "Platform Wide",
      resource: `User ${newUserId}`,
      result: "Success",
      ipAddress: "127.0.0.1",
      timestamp: new Date().toISOString(),
      details: `${formData.name} onboarded as ${formData.role === 'admin' ? 'Org Admin' : 'Platform Admin'}`,
    });

    toast("Admin member added successfully", "success");
    router.push("/superadmin/users");
  };

  return (
    <div className="space-y-8 max-w-3xl">
      <PageHeader
        title="Add Administrator"
        description="Create a new Hospital Admin or Platform Admin."
      />

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
              label="Phone Number *"
              type="tel"
              name="phone"
              value={formData.phone}
              onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
              placeholder="+91 98765 43210"
              inputMode="tel"
              pattern="[0-9+() -]{7,20}"
              title="Enter a valid phone number"
              required
            />
            <div className="sm:col-span-2">
              <Input
                label="Temporary Password *"
                name="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                required
                rightElement={
                  <button
                    type="button"
                    onClick={() => setFormData({ ...formData, password: generateTempPassword() })}
                    className="hover:text-primary transition-colors focus:outline-none"
                    aria-label="Generate a new password"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>
                }
              />
              <p className="mt-1.5 text-caption text-secondary">
                Share this with the new admin -- they can change it after logging in.
              </p>
            </div>

            <div className="space-y-1.5">
              <label className="text-body-sm font-medium text-on-surface-variant">Admin Type *</label>
              <select
                value={formData.role}
                disabled
                className="h-input-height w-full rounded-xl border border-border-muted bg-surface px-4 text-body-lg text-on-surface outline-none opacity-50 cursor-not-allowed"
              >
                <option value="admin">Hospital Admin</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-body-sm font-medium text-on-surface-variant">Hospital {isFromNewOrg ? "" : "*"}</label>
              {isFromNewOrg ? (
                <div className="h-input-height w-full rounded-xl border border-border-muted bg-surface px-4 py-2 text-body-lg text-secondary">
                  Will be assigned upon hospital creation
                </div>
              ) : (
                <div className="relative">
                  <input
                    required={!isFromNewOrg}
                    type="text"
                    list="org-list"
                    placeholder="Search Hospital..."
                    value={orgs.find(o => o.id === formData.organisationId)?.name || formData.organisationId}
                    onChange={(e) => {
                      const val = e.target.value;
                      const match = orgs.find(o => o.name === val);
                      setFormData({ ...formData, organisationId: match ? match.id : val });
                    }}
                    className="h-input-height w-full rounded-xl border border-border-muted bg-surface px-4 text-body-lg text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                  />
                  <datalist id="org-list">
                    {orgs.map(org => (
                      <option key={org.id} value={org.name} />
                    ))}
                  </datalist>
                </div>
              )}
            </div>
          </div>
          <div className="flex justify-end gap-4 pt-4 border-t border-border-muted">
            <Button variant="outline" type="button" onClick={() => router.back()}>
              Cancel
            </Button>
            <Button type="submit">
              Save Administrator
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

