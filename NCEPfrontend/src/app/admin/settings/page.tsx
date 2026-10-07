/* eslint-disable @next/next/no-img-element */
"use client";

import { useState, useEffect } from "react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { getOrganisationById, saveOrganisation, getUsers, saveUser, getCurrentSession, updateSession, resetApplicationData, getServiceErrorMessage } from "@/services";
import { Building2, Bell, Shield, Database, Trash2, Camera, User as UserIcon } from "lucide-react";
import type { Organisation, User } from "@/types";

export default function AdminSettings() {
  const { toast } = useToast();
  const [resetDialogOpen, setResetDialogOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"general" | "notifications" | "security" | "data">("general");

  const [org, setOrg] = useState<Organisation | null>(null);
  const [adminUser, setAdminUser] = useState<User | null>(null);
  const [orgName, setOrgName] = useState("City General Hospital");
  const [orgAddress, setOrgAddress] = useState("12 MG Road, Mumbai 400001");
  const [orgContact, setOrgContact] = useState("+91 22 2345 6789");
  const [orgLogoUrl, setOrgLogoUrl] = useState<string>("");
  const [adminAvatarUrl, setAdminAvatarUrl] = useState<string>("");

  useEffect(() => {
    const loadData = async () => {
      try {
        const session = await getCurrentSession();
        if (session) {
          const users = await getUsers();
          const u = users.find(user => user.id === session.userId);
          if (u) {
            setAdminUser(u);
            setAdminAvatarUrl(u.avatarUrl || "");
          }
          const organisation = await getOrganisationById(session.organisationId || "org-001");
          if (organisation) {
            setOrg(organisation);
            setOrgName(organisation.name);
            setOrgAddress(organisation.address);
            setOrgContact(organisation.contact);
            setOrgLogoUrl(organisation.logoUrl || "");
          }
        }
      } catch (error) {
        console.error("Error loading settings data:", error);
      }
    };
    loadData();
  }, []);

  const handleSaveGeneral = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const session = await getCurrentSession();
      const orgId = org?.id || session?.organisationId || "org-001";
      const updatedOrg: import("@/types").Organisation = {
        id: orgId,
        name: orgName,
        address: orgAddress,
        contact: orgContact,
        logoUrl: orgLogoUrl || undefined,
        createdAt: org?.createdAt || new Date().toISOString(),
        adminId: org?.adminId || session?.userId || "admin-001",
        status: org?.status || "Active",
        totalUsers: org?.totalUsers || 1,
        totalPatients: org?.totalPatients || 0,
      };
      await saveOrganisation(updatedOrg);

      if (adminUser) {
        const updatedUser: User = {
          ...adminUser,
          avatarUrl: adminAvatarUrl || undefined,
        };
        await saveUser(updatedUser);

        if (session) {
          const updatedSession = {
            ...session,
            avatarUrl: adminAvatarUrl || undefined,
          };
          await updateSession(updatedSession);
        }
      }

      toast("Hospital profile and photos saved successfully.", "success");
      setTimeout(() => {
        window.location.reload();
      }, 500);
    } catch (error) {
      toast(getServiceErrorMessage(error), "error");
    }
  };

  const handleReset = async () => {
    try {
      await resetApplicationData();
      setResetDialogOpen(false);
      toast("Demo data has been reset.", "success");
      // Reload to re-initialize seed data and effectively log out since session is cleared
      setTimeout(() => {
        window.location.href = "/login";
      }, 1500);
    } catch (error) {
      toast(getServiceErrorMessage(error), "error");
    }
  };

  return (
    <div className="space-y-8 max-w-4xl">
      <PageHeader
        title="Settings"
        description="Manage organisation preferences and system configurations."
      />

      <div className="grid grid-cols-1 gap-8 md:grid-cols-4">
        {/* Navigation Sidebar */}
        <div className="col-span-1 space-y-1">
          <button 
            onClick={() => setActiveTab("general")}
            className={`flex w-full items-center gap-3 rounded-xl px-4 py-3 text-body-sm font-medium transition-colors ${activeTab === "general" ? "bg-secondary-container text-primary" : "text-secondary hover:bg-surface-bright hover:text-on-surface"}`}
          >
            <Building2 className="h-5 w-5" /> General
          </button>
          <button 
            onClick={() => setActiveTab("notifications")}
            className={`flex w-full items-center gap-3 rounded-xl px-4 py-3 text-body-sm font-medium transition-colors ${activeTab === "notifications" ? "bg-secondary-container text-primary" : "text-secondary hover:bg-surface-bright hover:text-on-surface"}`}
          >
            <Bell className="h-5 w-5" /> Notifications
          </button>
          <button 
            onClick={() => setActiveTab("security")}
            className={`flex w-full items-center gap-3 rounded-xl px-4 py-3 text-body-sm font-medium transition-colors ${activeTab === "security" ? "bg-secondary-container text-primary" : "text-secondary hover:bg-surface-bright hover:text-on-surface"}`}
          >
            <Shield className="h-5 w-5" /> Security
          </button>
          <button 
            onClick={() => setActiveTab("data")}
            className={`flex w-full items-center gap-3 rounded-xl px-4 py-3 text-body-sm font-medium transition-colors ${activeTab === "data" ? "bg-secondary-container text-primary" : "text-secondary hover:bg-surface-bright hover:text-on-surface"}`}
          >
            <Database className="h-5 w-5" /> Data Management
          </button>
        </div>

        {/* Content Area */}
        <div className="col-span-1 md:col-span-3 space-y-8">
          {activeTab === "general" && (
            <Card className="p-8">
              <h3 className="mb-6 text-card-title text-on-surface border-b border-border-muted pb-4">Hospital & Admin Profile</h3>
              <form onSubmit={handleSaveGeneral} className="space-y-6">
                
                {/* Organisation Logo / Photo */}
                <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6 p-4 rounded-xl border border-border-muted bg-surface-container-low">
                  <div className="relative h-20 w-20 rounded-xl bg-surface border-2 border-primary/20 overflow-hidden flex items-center justify-center shrink-0">
                    {orgLogoUrl ? (
                      <img src={orgLogoUrl} alt="Hospital Logo" className="h-full w-full object-cover" />
                    ) : (
                      <Building2 className="h-10 w-10 text-secondary" />
                    )}
                  </div>
                  <div className="space-y-1.5 flex-1">
                    <h4 className="text-body-md font-medium text-on-surface">Hospital Logo / Photo</h4>
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

                {/* Admin Profile Photo */}
                <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6 p-4 rounded-xl border border-border-muted bg-surface-container-low">
                  <div className="relative h-20 w-20 rounded-full bg-surface border-2 border-primary/20 overflow-hidden flex items-center justify-center shrink-0">
                    {adminAvatarUrl ? (
                      <img src={adminAvatarUrl} alt="Admin Avatar" className="h-full w-full object-cover" />
                    ) : (
                      <UserIcon className="h-10 w-10 text-secondary" />
                    )}
                  </div>
                  <div className="space-y-1.5 flex-1">
                    <h4 className="text-body-md font-medium text-on-surface">Admin Profile Photo</h4>
                    <p className="text-caption text-secondary">
                      Recommended format: PNG, JPG, or WEBP (1:1 square ratio, min 400x400px, max 5MB). Displays in the navigation header and audit trails.
                    </p>
                    <div className="flex items-center gap-3 pt-1">
                      <label className="cursor-pointer inline-flex items-center gap-2 rounded-xl border border-border-muted bg-surface px-4 py-2 text-body-sm font-medium transition-colors hover:bg-surface-bright focus:outline-none focus:ring-2 focus:ring-primary/20">
                        <Camera className="h-4 w-4 text-primary" />
                        Upload Admin Photo
                        <input 
                          type="file" 
                          className="hidden" 
                          accept="image/png,image/jpeg,image/webp,image/svg+xml" 
                          onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file) {
                              const reader = new FileReader();
                              reader.onloadend = () => {
                                setAdminAvatarUrl(reader.result as string);
                              };
                              reader.readAsDataURL(file);
                            }
                          }} 
                        />
                      </label>
                      {adminAvatarUrl && (
                        <button 
                          type="button" 
                          onClick={() => setAdminAvatarUrl("")} 
                          className="text-body-sm text-error hover:underline"
                        >
                          Remove
                        </button>
                      )}
                    </div>
                  </div>
                </div>

                <Input label="Hospital Name" value={orgName} onChange={(e) => setOrgName(e.target.value)} required />
                <Input label="Address" value={orgAddress} onChange={(e) => setOrgAddress(e.target.value)} required />
                <Input label="Contact Number" value={orgContact} onChange={(e) => setOrgContact(e.target.value)} required />
                <div className="flex justify-end">
                  <Button type="submit">Save Changes</Button>
                </div>
              </form>
            </Card>
          )}

          {activeTab === "notifications" && (
            <Card className="p-8 flex items-center justify-center h-48 text-secondary">
              Notification settings coming soon.
            </Card>
          )}

          {activeTab === "security" && (
            <Card className="p-8 flex items-center justify-center h-48 text-secondary">
              Security settings coming soon.
            </Card>
          )}

          {activeTab === "data" && (
            <Card className="p-8 border-error/30 bg-error/5">
              <h3 className="mb-4 text-card-title text-error border-b border-error/20 pb-4">Danger Zone</h3>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-body-sm font-medium text-on-surface">Reset Demo Data</p>
                  <p className="text-caption text-secondary">Clear all mock data from localStorage and reset the application to default state. You will be logged out.</p>
                </div>
                <Button 
                  variant="primary" 
                  className="!bg-critical !text-on-primary hover:!bg-critical/90 shrink-0 gap-2 focus-visible:!outline-critical"
                  onClick={() => setResetDialogOpen(true)}
                >
                  <Trash2 className="h-4 w-4" /> Reset Data
                </Button>
              </div>
            </Card>
          )}
        </div>
      </div>

      <ConfirmDialog
        open={resetDialogOpen}
        title="Reset all demo data?"
        description="This action will clear all users, patients, reports, and ECG records from your browser's local storage. This cannot be undone."
        variant="danger"
        confirmLabel="Yes, reset everything"
        onConfirm={handleReset}
        onCancel={() => setResetDialogOpen(false)}
      />
    </div>
  );
}
