"use client";

import { useState } from "react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { resetApplicationData } from "@/services";
import { Server, Database, ShieldAlert, Trash2 } from "lucide-react";

export default function SuperAdminSettings() {
  const { toast } = useToast();
  const [resetDialogOpen, setResetDialogOpen] = useState(false);

  const handleReset = async () => {
    await resetApplicationData();
    setResetDialogOpen(false);
    toast("Global database has been reset.", "success");
    setTimeout(() => {
      window.location.href = "/login";
    }, 1500);
  };

  const [activeTab, setActiveTab] = useState<"platform" | "security" | "database">("platform");

  return (
    <div className="space-y-8 max-w-4xl">
      <PageHeader
        title="System Settings"
        description="Global platform configurations and administrative tools."
      />

      <div className="grid grid-cols-1 gap-8 md:grid-cols-4">
        <div className="col-span-1 space-y-1">
          <button 
            onClick={() => setActiveTab("platform")}
            className={`flex w-full items-center gap-3 rounded-xl px-4 py-3 text-body-sm font-medium transition-colors ${activeTab === "platform" ? "bg-secondary-container text-primary" : "text-secondary hover:bg-surface-bright hover:text-on-surface"}`}
          >
            <Server className="h-5 w-5" /> Platform Config
          </button>
          <button 
            onClick={() => setActiveTab("security")}
            className={`flex w-full items-center gap-3 rounded-xl px-4 py-3 text-body-sm font-medium transition-colors ${activeTab === "security" ? "bg-secondary-container text-primary" : "text-secondary hover:bg-surface-bright hover:text-on-surface"}`}
          >
            <ShieldAlert className="h-5 w-5" /> Security Rules
          </button>
          <button 
            onClick={() => setActiveTab("database")}
            className={`flex w-full items-center gap-3 rounded-xl px-4 py-3 text-body-sm font-medium transition-colors ${activeTab === "database" ? "bg-secondary-container text-primary" : "text-secondary hover:bg-surface-bright hover:text-on-surface"}`}
          >
            <Database className="h-5 w-5" /> Database
          </button>
        </div>

        <div className="col-span-1 md:col-span-3 space-y-8">
          {activeTab === "platform" && (
            <Card className="p-8">
              <h3 className="mb-6 text-card-title text-on-surface border-b border-border-muted pb-4">Platform Configuration</h3>
              <div className="space-y-6">
                <Input label="Platform Name" defaultValue="CardioNexus Clinical Precision Platform" />
                <Input label="Support Email" defaultValue="support@ncep.example.com" />
                <div className="flex justify-end">
                  <Button onClick={() => toast("Settings saved.", "success")}>Save Config</Button>
                </div>
              </div>
            </Card>
          )}

          {activeTab === "security" && (
            <Card className="p-8 flex items-center justify-center h-48 text-secondary">
              Security rules configuration coming soon.
            </Card>
          )}

          {activeTab === "database" && (
            <Card className="p-8 border-error/30 bg-error/5">
              <h3 className="mb-4 text-card-title text-error border-b border-error/20 pb-4">Global Data Reset</h3>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-body-sm font-medium text-on-surface">Factory Reset Platform</p>
                  <p className="text-caption text-secondary">Irreversibly wipe all data across all organisations and recreate default mock state. You will be logged out.</p>
                </div>
                <Button 
                  variant="primary" 
                  className="bg-error hover:bg-error/90 shrink-0 gap-2"
                  onClick={() => setResetDialogOpen(true)}
                >
                  <Trash2 className="h-4 w-4" /> Hard Reset
                </Button>
              </div>
            </Card>
          )}
        </div>
      </div>

      <ConfirmDialog
        open={resetDialogOpen}
        title="Factory Reset Platform?"
        description="WARNING: This will destroy all data for all organisations, users, patients, and reports across the entire platform. This action is permanent and cannot be undone."
        variant="danger"
        confirmLabel="Yes, DESTROY all data"
        onConfirm={handleReset}
        onCancel={() => setResetDialogOpen(false)}
      />
    </div>
  );
}
