"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/providers/AuthProvider";
import { saveDoctor, saveUser, addAuditLog, getServiceErrorMessage } from "@/services";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import type { Doctor, User } from "@/types";
import { generateTempPassword } from "@/lib/utils";
import { RefreshCw } from "lucide-react";

export default function AddStaff() {
  const { session } = useAuth();
  const router = useRouter();
  const { toast } = useToast();

  const [formData, setFormData] = useState({
    name: "",
    email: "",
    phone: "",
    role: "Doctor",
    speciality: "Cardiac Electrophysiology",
    password: generateTempPassword(),
  });

  const [isCustomSpeciality, setIsCustomSpeciality] = useState(false);
  const [customSpecialityText, setCustomSpecialityText] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!session?.organisationId) return;

    try {
      const newUserId = `user-staff-${Math.floor(Math.random() * 10000).toString()}`;
      const newDocId = `doc-${Math.floor(Math.random() * 1000).toString().padStart(3, "0")}`;

      const newUser: User = {
        id: newUserId,
        email: formData.email,
        name: formData.name,
        phone: formData.phone,
        password: formData.password,
        role: formData.role === "Technician" ? "doctor" : "doctor", // Keep auth role as doctor for both
        organisationId: session.organisationId,
        status: "Active",
        lastActive: "—",
        createdAt: new Date().toISOString().split('T')[0],
      };

      const newDoctor: Doctor = {
        id: newDocId,
        userId: newUserId,
        name: formData.name,
        email: formData.email,
        phone: formData.phone,
        staffId: `STF-${Math.floor(Math.random() * 10000)}`,
        role: formData.role as "Doctor" | "Technician",
        speciality: formData.speciality,
        organisationId: session.organisationId,
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
        actorId: session.userId,
        actorName: session.name,
        actorRole: session.role,
        organisationId: session.organisationId,
        organisationName: "Current Org", 
        resource: `User ${newUserId}`,
        result: "Success",
        ipAddress: "127.0.0.1",
        timestamp: new Date().toISOString(),
        details: `${formData.name} onboarded as ${formData.role}`,
      });

      toast("Staff member added successfully", "success");
      router.push("/admin/users?tab=doctors");
    } catch (error) {
      toast(getServiceErrorMessage(error), "error");
    }
  };

  return (
    <div className="space-y-8 max-w-3xl">
      <PageHeader
        title="Add Clinical Staff"
        description="Register a new doctor or technician to your hospital."
      />

      <Card className="p-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            <Input
              label="Full Name"
              name="name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
            />
            <Input
              label="Email Address"
              type="email"
              name="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
            />
            <Input
              label="Phone Number"
              type="tel"
              name="phone"
              value={formData.phone}
              onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
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
            <div className="space-y-1.5">
              <label className="text-body-sm font-medium text-on-surface-variant">Speciality</label>
              <select
                value={isCustomSpeciality ? "Custom" : formData.speciality}
                onChange={(e) => {
                  if (e.target.value === "Custom") {
                    setIsCustomSpeciality(true);
                    setFormData({ ...formData, speciality: customSpecialityText });
                  } else {
                    setIsCustomSpeciality(false);
                    setFormData({ ...formData, speciality: e.target.value });
                  }
                }}
                className="h-input-height w-full rounded-xl border border-border-muted bg-surface px-4 text-body-lg text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
              >
                <option value="Cardiac Electrophysiology">Cardiac Electrophysiology</option>
                <option value="Cardiology">Cardiology</option>
                <option value="Neurology">Neurology</option>
                <option value="ECG Technology">ECG Technology</option>
                <option value="Custom">Custom Speciality</option>
              </select>
            </div>

            {isCustomSpeciality && (
              <Input
                label="Custom Speciality"
                name="customSpeciality"
                value={customSpecialityText}
                onChange={(e) => {
                  setCustomSpecialityText(e.target.value);
                  setFormData({ ...formData, speciality: e.target.value });
                }}
                required
                placeholder="Enter custom speciality"
              />
            )}
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
