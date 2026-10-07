"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/providers/AuthProvider";
import { saveDoctor, saveUser, addAuditLog, getOrganisations } from "@/services";
import type { Doctor, User, Organisation } from "@/types";
import { useEffect } from "react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { generateTempPassword } from "@/lib/utils";
import { RefreshCw } from "lucide-react";

export default function SuperAdminAddStaff() {
  const { session } = useAuth();
  const router = useRouter();
  const { toast } = useToast();

  const [formData, setFormData] = useState({
    name: "",
    email: "",
    role: "Doctor",
    speciality: "",
    organisationId: "",
    password: generateTempPassword(),
  });

  const [orgs, setOrgs] = useState<Organisation[]>([]);
  useEffect(() => {
    getOrganisations().then(setOrgs);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.organisationId) {
      toast("Please select an organisation", "error");
      return;
    }

    const newUserId = `user-staff-${Math.floor(Math.random() * 10000).toString()}`;
    const newDocId = `doc-${Math.floor(Math.random() * 1000).toString().padStart(3, "0")}`;

    const newUser: User = {
      id: newUserId,
      email: formData.email,
      name: formData.name,
      password: formData.password,
      role: formData.role === "Technician" ? "doctor" : "doctor", // Keep auth role as doctor for both
      organisationId: formData.organisationId,
      status: "Active",
      lastActive: "—",
      createdAt: new Date().toISOString().split('T')[0],
    };

    const newDoctor: Doctor = {
      id: newDocId,
      userId: newUserId,
      name: formData.name,
      email: formData.email,
      staffId: `STF-${Math.floor(Math.random() * 10000)}`,
      role: formData.role as "Doctor" | "Technician",
      speciality: formData.speciality,
      organisationId: formData.organisationId,
      status: "Active",
      assignedPatientCount: 0,
      lastActive: "—",
      createdAt: new Date().toISOString().split('T')[0],
    };

    await saveUser(newUser);
    await saveDoctor(newDoctor);
    
    await addAuditLog({
      id: `log-${Date.now()}`,
      event: "Staff account created",
      eventType: "user_created",
      actorId: session?.userId || "unknown",
      actorName: session?.name || "Superadmin",
      actorRole: session?.role || "superadmin",
      organisationId: formData.organisationId,
      organisationName: orgs.find(o => o.id === formData.organisationId)?.name || "Unknown Org", 
      resource: `User ${newUserId}`,
      result: "Success",
      ipAddress: "127.0.0.1",
      timestamp: new Date().toISOString(),
      details: `${formData.name} onboarded as ${formData.role}`,
    });

    toast("Staff member added successfully", "success");
    router.push("/superadmin/users");
  };

  return (
    <div className="space-y-8 max-w-3xl">
      <PageHeader
        title="Add Clinical Staff"
        description="Register a new doctor or technician globally."
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
            
            <div className="space-y-1.5">
              <label className="text-body-sm font-medium text-on-surface-variant">Hospital *</label>
              <select
                required
                value={formData.organisationId}
                onChange={(e) => setFormData({ ...formData, organisationId: e.target.value })}
                className="h-input-height w-full rounded-xl border border-border-muted bg-surface px-4 text-body-lg text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
              >
                <option value="" disabled>Select Hospital...</option>
                {orgs.map(org => (
                  <option key={org.id} value={org.id}>{org.name}</option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-body-sm font-medium text-on-surface-variant">Role</label>
              <select
                value={formData.role}
                onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                className="h-input-height w-full rounded-xl border border-border-muted bg-surface px-4 text-body-lg text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
              >
                <option value="Doctor">Doctor</option>
                <option value="Technician">Technician</option>
              </select>
            </div>
            
            <Input
              label="Speciality *"
              name="speciality"
              value={formData.speciality}
              onChange={(e) => setFormData({ ...formData, speciality: e.target.value })}
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
                Share this with the new staff member -- they can change it after logging in.
              </p>
            </div>
          </div>
          <div className="flex justify-end gap-4 pt-4 border-t border-border-muted">
            <Button variant="outline" type="button" onClick={() => router.back()}>
              Cancel
            </Button>
            <Button type="submit">
              Save Staff Member
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
