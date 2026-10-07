/* eslint-disable @next/next/no-img-element */
"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { Card, CardHeader, CardContent } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { User, Patient } from "@/types";
import {
  changePassword,
  getDoctors,
  getOrganisationById,
  getPatients,
  getServiceErrorMessage,
  getUsers,
  updateOrganisation,
  updateOwnDoctor,
  updateOwnPatient,
  updateSession,
} from "@/services";
import { useAuth } from "@/providers/AuthProvider";
import { useRouter } from "next/navigation";
import { Lock, Mail, Phone, User as UserIcon, Shield, Eye, EyeOff, Camera, Building2 } from "lucide-react";
import { useState } from "react";

type ProfileFormData = {
  name: string;
  email: string;
  phone: string;
  currentPassword?: string;
  password?: string;
  confirmPassword?: string;
};

export function ProfileForm() {
  const { toast } = useToast();
  const router = useRouter();
  void router;
  
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [avatarUrl, setAvatarUrl] = useState<string>("");
  const [orgLogoUrl, setOrgLogoUrl] = useState<string>("");

  const { register, handleSubmit, setValue, formState: { isSubmitting } } = useForm<ProfileFormData>();

  const { session } = useAuth();

  const [user, setUser] = useState<User | null>(null);
  // The backend only lets patients/doctors self-update their contact record's
  // email/phone (PATCH /patients or /doctors); the login User record's own
  // email/phone has no self-service path for any role.
  const canEditContactRecord = user?.role === "patient" || user?.role === "doctor";
  const [patient, setPatient] = useState<Patient | null>(null);

  useEffect(() => {
    if (session) {
      getUsers()
        .then(users => {
          setUser(users.find(u => u.id === session.userId) || null);
        })
        .catch(err => console.error("Error loading profile user:", err));
    }
  }, [session]);

  useEffect(() => {
    if (user) {
      setValue("name", user.name);
      setValue("email", user.email);
      setValue("phone", user.phone || "");
      setAvatarUrl(user.avatarUrl || "");
      if (user.role === "admin") {
        getOrganisationById(user.organisationId)
          .then(org => {
            if (org) {
              setOrgLogoUrl(org.logoUrl || "");
            }
          })
          .catch(err => console.error("Error loading organisation:", err));
      } else if (user.role === "patient") {
        getPatients().then(patients => {
          const p = patients.find(p => p.id === session?.patientId || p.email === user.email);
          if (p) setPatient(p);
        }).catch(err => console.error("Error loading patient:", err));
      }
    }
  }, [user, setValue, session?.patientId]);

  const handleAvatarChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setAvatarUrl(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  if (!session || !user) {
    return <div className="p-4">Loading profile...</div>;
  }

  const onSubmit = async (data: ProfileFormData) => {
    if (data.password) {
      if (data.password !== data.confirmPassword) {
        toast("Passwords do not match.", "error");
        return;
      }
      if (!data.currentPassword) {
        toast("Enter your current password to set a new one.", "error");
        return;
      }
    }

    try {
      // Name and avatar are self-updatable for every role via the session record.
      await updateSession({ ...session, name: data.name, avatarUrl: avatarUrl || undefined });

      if (data.password && data.currentPassword) {
        await changePassword(data.currentPassword, data.password);
      }

      // Email/phone live on the role-specific record (Patient/Doctor); only
      // those roles have a self-service path to update them.
      if (user.role === "patient" && patient) {
        await updateOwnPatient(patient.id, { name: data.name, email: data.email, phone: data.phone });
      } else if (user.role === "doctor") {
        const doctors = await getDoctors();
        const doctor = doctors.find(d => d.userId === user.id);
        if (doctor) {
          await updateOwnDoctor(doctor.id, { name: data.name, email: data.email, phone: data.phone });
        }
      } else if (user.role === "admin") {
        await updateOrganisation(user.organisationId, { logoUrl: orgLogoUrl || undefined });
      }

      toast("Profile updated successfully!", "success");

      // Force a hard navigation or reload to refresh the header name
      window.location.reload();
    } catch (error) {
      toast(getServiceErrorMessage(error), "error");
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <Card>
        <CardHeader 
          title="Profile Information" 
          description="Update your personal details and account settings." 
        />
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            
            {/* Avatar Upload */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6 p-4 rounded-xl border border-border-muted bg-surface-container-low">
              <div className="relative h-20 w-20 rounded-full bg-surface border-2 border-primary/20 overflow-hidden flex items-center justify-center shrink-0">
                {avatarUrl ? (
                  <img src={avatarUrl} alt="Avatar" className="h-full w-full object-cover" />
                ) : (
                  <UserIcon className="h-10 w-10 text-secondary" />
                )}
              </div>
              <div className="space-y-1.5 flex-1">
                <h3 className="text-body-md font-medium text-on-surface">Profile Picture</h3>
                <p className="text-caption text-secondary">
                  Recommended format: PNG, JPG, or WEBP (1:1 square ratio, min 400x400px, max 5MB). Displays in the navigation header and audit trails.
                </p>
                <div className="flex items-center gap-3 pt-1">
                  <label className="cursor-pointer inline-flex items-center gap-2 rounded-xl border border-border-muted bg-surface px-4 py-2 text-body-sm font-medium transition-colors hover:bg-surface-bright focus:outline-none focus:ring-2 focus:ring-primary/20">
                    <Camera className="h-4 w-4 text-primary" />
                    Upload Image
                    <input type="file" className="hidden" accept="image/png,image/jpeg,image/webp,image/svg+xml" onChange={handleAvatarChange} />
                  </label>
                  {avatarUrl && (
                    <button type="button" onClick={() => setAvatarUrl("")} className="text-body-sm text-error hover:underline">
                      Remove
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Admin Organisation Photo Upload */}
            {user.role === "admin" && (
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6 p-4 rounded-xl border border-border-muted bg-surface-container-low">
                <div className="relative h-20 w-20 rounded-xl bg-surface border-2 border-primary/20 overflow-hidden flex items-center justify-center shrink-0">
                  {orgLogoUrl ? (
                    <img src={orgLogoUrl} alt="Hospital Logo" className="h-full w-full object-cover" />
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
                      Upload Hospital Photo
                      <input 
                        type="file" 
                        className="hidden" 
                        accept="image/png,image/jpeg,image/webp,image/svg+xml" 
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) {
                            const reader = new FileReader();
                            reader.onloadend = () => {
                              setOrgLogoUrl(reader.result as string);
                            };
                            reader.readAsDataURL(file);
                          }
                        }} 
                      />
                    </label>
                    {orgLogoUrl && (
                      <button 
                        type="button" 
                        onClick={() => setOrgLogoUrl("")} 
                        className="text-body-sm text-error hover:underline"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Read-Only Fields */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-surface-container-low p-4 rounded-xl border border-border-muted mb-6">
              <div>
                <label className="text-body-sm text-secondary font-medium block mb-1">User ID</label>
                <div className="text-body-lg text-on-surface flex items-center gap-2">
                  <Shield className="w-4 h-4 text-outline" />
                  {user.id}
                </div>
              </div>
              <div>
                <label className="text-body-sm text-secondary font-medium block mb-1">Role</label>
                <div className="text-body-lg text-on-surface capitalize">
                  {user.role}
                </div>
              </div>
            </div>

            {/* Editable Fields */}
            <div className="space-y-4">
              <Input
                label="Full Name"
                icon={<UserIcon className="w-5 h-5" />}
                placeholder="Enter your name"
                {...register("name", { required: true })}
              />
              
              <Input
                label="Email Address"
                type="email"
                icon={<Mail className="w-5 h-5" />}
                placeholder="Enter your email"
                disabled={!canEditContactRecord}
                {...register("email", { required: true })}
              />

              <Input
                label="Phone Number"
                type="tel"
                icon={<Phone className="w-5 h-5" />}
                placeholder="Enter your phone number"
                disabled={!canEditContactRecord}
                {...register("phone")}
              />
              {!canEditContactRecord && (
                <p className="text-caption text-secondary -mt-2">
                  Contact a superadmin to change your login email or phone number.
                </p>
              )}

              <Input
                label="Current Password"
                type={showCurrentPassword ? "text" : "password"}
                icon={<Lock className="w-5 h-5" />}
                placeholder="Required to set a new password"
                rightElement={
                  <button
                    type="button"
                    onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                    className="hover:text-primary transition-colors focus:outline-none"
                    aria-label={showCurrentPassword ? "Hide password" : "Show password"}
                  >
                    {showCurrentPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                }
                {...register("currentPassword")}
              />

              <Input
                label="Password"
                type={showPassword ? "text" : "password"}
                icon={<Lock className="w-5 h-5" />}
                placeholder="Enter a new password"
                rightElement={
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="hover:text-primary transition-colors focus:outline-none"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                }
                {...register("password")}
              />

              <Input
                label="Confirm Password"
                type={showConfirmPassword ? "text" : "password"}
                icon={<Lock className="w-5 h-5" />}
                placeholder="Re-enter your new password"
                rightElement={
                  <button 
                    type="button" 
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="hover:text-primary transition-colors focus:outline-none"
                    aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                  >
                    {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                }
                {...register("confirmPassword")}
              />
            </div>

            <div className="pt-4 flex justify-end">
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Saving..." : "Save Changes"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
