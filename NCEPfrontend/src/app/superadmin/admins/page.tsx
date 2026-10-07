"use client";

import { useState, useMemo, useEffect } from "react";
import { getUsers, getOrganisations } from "@/services";
import { formatDate } from "@/lib/utils";
import type { User, Organisation } from "@/types";
import { PageHeader } from "@/components/layout/PageHeader";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { StatusBadge, userStatusVariant } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { Search, Filter, Plus, Pencil } from "lucide-react";

export default function SuperAdminAdminsList() {
  const [search, setSearch] = useState("");
  const [orgFilter, setOrgFilter] = useState("All");
  const [typeFilter, setTypeFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState("All");
  
  const [orgs, setOrgs] = useState<Organisation[]>([]);
  const [allAdmins, setAllAdmins] = useState<User[]>([]);

  useEffect(() => {
    getOrganisations().then(setOrgs);
    getUsers().then((u) => setAllAdmins(u.filter((x) => x.role === "admin" || x.role === "superadmin")));
  }, []);

  const filteredAdmins = useMemo(() => {
    return allAdmins.filter((u) => {
      const matchesSearch = u.name.toLowerCase().includes(search.toLowerCase()) || u.email.toLowerCase().includes(search.toLowerCase());
      const matchesOrg = orgFilter === "All" || u.organisationId === orgFilter;
      const matchesType = typeFilter === "All" || u.role === typeFilter;
      const matchesStatus = statusFilter === "All" || u.status === statusFilter;
      
      return matchesSearch && matchesOrg && matchesType && matchesStatus;
    });
  }, [allAdmins, search, orgFilter, typeFilter, statusFilter]);

  const getOrgName = (id: string) => {
    return orgs.find(o => o.id === id)?.name || id;
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title="Platform Administrators"
        description="Manage Platform and Hospital-level administrative accounts."
        actions={
          <Link href="/superadmin/admins/new">
            <Button className="gap-2">
              <Plus className="h-4 w-4" /> Add Admin
            </Button>
          </Link>
        }
      />

      <Card className="overflow-hidden">
        <div className="flex flex-col gap-4 border-b border-border-muted bg-surface-bright p-4 xl:flex-row xl:items-center">
          <div className="relative w-full xl:max-w-xs">
            <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-outline" />
            <input
              type="text"
              placeholder="Search by name or email..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-10 w-full rounded-xl border border-border-muted bg-surface px-10 text-body-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            />
          </div>
          
          <div className="flex flex-wrap items-center gap-2">
            <Filter className="h-5 w-5 text-secondary" />
            <select
              value={orgFilter}
              onChange={(e) => setOrgFilter(e.target.value)}
              className="h-10 max-w-[200px] truncate rounded-xl border border-border-muted bg-surface px-3 text-body-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            >
              <option value="All">All Hospitals</option>
              {orgs.map(o => (
                <option key={o.id} value={o.id}>{o.name}</option>
              ))}
            </select>

            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="h-10 rounded-xl border border-border-muted bg-surface px-3 text-body-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            >
              <option value="All">All Admin Types</option>
              <option value="admin">Hospital Admin</option>
              <option value="superadmin">Platform Admin</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="h-10 rounded-xl border border-border-muted bg-surface px-3 text-body-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            >
              <option value="All">All Statuses</option>
              <option value="Active">Active</option>
              <option value="Invited">Invited</option>
              <option value="Inactive">Inactive</option>
            </select>
          </div>
        </div>

        {filteredAdmins.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-body-sm">
              <thead className="border-b border-border-muted bg-surface-bright text-caption text-secondary">
                <tr>
                  <th className="px-6 py-4 font-medium">Admin Name</th>
                  <th className="px-6 py-4 font-medium">Email</th>
                  <th className="px-6 py-4 font-medium">Hospital</th>
                  <th className="px-6 py-4 font-medium">Admin Type</th>
                  <th className="px-6 py-4 font-medium">Status</th>
                  <th className="px-6 py-4 font-medium">Last Active</th>
                  <th className="px-6 py-4 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-muted text-on-surface">
                {filteredAdmins.map((admin) => (
                  <tr key={admin.id} className="transition-colors hover:bg-surface-bright/50">
                    <td className="px-6 py-4 font-medium">{admin.name}</td>
                    <td className="px-6 py-4 text-secondary">{admin.email}</td>
                    <td className="px-6 py-4 text-secondary">{admin.role === 'superadmin' ? 'Platform Wide' : getOrgName(admin.organisationId)}</td>
                    <td className="px-6 py-4">
                      {admin.role === "superadmin" ? (
                        <span className="font-semibold text-primary">Platform Admin</span>
                      ) : (
                        <span className="text-secondary">Hospital Admin</span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge variant={userStatusVariant(admin.status)}>{admin.status}</StatusBadge>
                    </td>
                    <td className="px-6 py-4 text-secondary">{admin.lastActive ? formatDate(admin.lastActive) : "Never"}</td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex justify-end gap-2">
                        <Link href={`/superadmin/admins/edit?adminId=${encodeURIComponent(admin.id)}`}>
                          <Button variant="outline" className="h-8 gap-2">
                            <Pencil className="h-3.5 w-3.5" /> Edit
                          </Button>
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="No administrators found" description="No admins match your current search filters." />
        )}
      </Card>
    </div>
  );
}
