"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { getOrganisations, getUsers } from "@/services";
import { formatDate } from "@/lib/utils";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusBadge, userStatusVariant } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Pencil, Plus, Search, UsersRound } from "lucide-react";
import type { User } from "@/types";

type UserGroup = "admins" | "doctors" | "patients";

const groups: Array<{ id: UserGroup; label: string; description: string; addHref: string; addLabel: string }> = [
  { id: "admins", label: "Admins", description: "Platform and organisation administrators", addHref: "/superadmin/admins/new", addLabel: "Add Admin" },
  { id: "doctors", label: "Doctors", description: "Doctors, technicians, and clinical staff", addHref: "/superadmin/doctors/new", addLabel: "Add Staff" },
  { id: "patients", label: "Patients", description: "Patient portal accounts and profiles", addHref: "/superadmin/patients/new", addLabel: "Add Patient" },
];

function groupForUser(user: User): UserGroup {
  if (user.role === "admin" || user.role === "superadmin") return "admins";
  return user.role === "doctor" ? "doctors" : "patients";
}

export default function SuperAdminManageUsers() {
  const [activeGroup, setActiveGroup] = useState<UserGroup>("admins");
  const [search, setSearch] = useState("");

  const [organisations, setOrganisations] = useState<import("@/types").Organisation[]>([]);
  const [users, setUsers] = useState<User[]>([]);

  useEffect(() => {
    getOrganisations().then(setOrganisations);
    getUsers().then(setUsers);
  }, []);

  const activeConfig = groups.find((group) => group.id === activeGroup)!;
  const visibleUsers = users.filter((user) => {
    const matchesGroup = groupForUser(user) === activeGroup;
    const searchable = `${user.name} ${user.email}`.toLowerCase();
    return matchesGroup && searchable.includes(search.toLowerCase());
  });

  const getOrganisationName = (organisationId: string) => organisations.find((organisation) => organisation.id === organisationId)?.name || "Platform Wide";

  return (
    <div className="space-y-8">
      <PageHeader
        title="Manage Users"
        description="Add, edit, and manage platform access for administrators, doctors, and patients."
        actions={<Link href={activeConfig.addHref}><Button className="gap-2"><Plus className="h-4 w-4" /> {activeConfig.addLabel}</Button></Link>}
      />

      <div className="flex flex-wrap gap-3" aria-label="User type">
        {groups.map((group) => (
          <button
            key={group.id}
            type="button"
            onClick={() => { setActiveGroup(group.id); setSearch(""); }}
            className={`rounded-full border px-5 py-2.5 text-body-sm font-medium transition-colors ${activeGroup === group.id ? "border-primary bg-primary text-on-primary" : "border-border-muted bg-surface text-secondary hover:border-primary hover:text-primary"}`}
          >
            {group.label}
          </button>
        ))}
      </div>

      <Card className="overflow-hidden">
        <div className="flex flex-col gap-4 border-b border-border-muted bg-surface-bright p-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="font-semibold text-on-surface">{activeConfig.label}</h2>
            <p className="mt-1 text-body-sm text-secondary">{activeConfig.description}</p>
          </div>
          <div className="relative w-full sm:max-w-sm">
            <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-outline" />
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder={`Search ${activeConfig.label.toLowerCase()}...`} className="h-10 w-full rounded-xl border border-border-muted bg-surface px-10 text-body-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary" />
          </div>
        </div>

        {visibleUsers.length > 0 ? (
          <div className="overflow-x-auto max-h-[500px] overflow-y-scroll">
            <table className="w-full text-left text-body-sm relative">
              <thead className="sticky top-0 z-10 border-b border-border-muted bg-surface-bright text-caption text-secondary">
                <tr>
                  <th className="px-6 py-4 font-medium">Name</th>
                  <th className="px-6 py-4 font-medium">Email</th>
                  <th className="px-6 py-4 font-medium">Organisation</th>
                  <th className="px-6 py-4 font-medium">Account Type</th>
                  <th className="px-6 py-4 font-medium">Status</th>
                  <th className="px-6 py-4 font-medium">Last Active</th>
                  <th className="px-6 py-4 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-muted text-on-surface">
                {visibleUsers.map((user) => (
                  <tr key={user.id} className="transition-colors hover:bg-surface-bright/50">
                    <td className="px-6 py-4 font-medium">{user.name}</td>
                    <td className="px-6 py-4 text-secondary">{user.email}</td>
                    <td className="px-6 py-4 text-secondary">{user.role === "superadmin" ? "Platform Wide" : getOrganisationName(user.organisationId)}</td>
                    <td className="px-6 py-4 text-secondary">{user.role === "superadmin" ? "Platform Admin" : user.role === "admin" ? "Org Admin" : user.role === "doctor" ? "Clinical Staff" : "Patient"}</td>
                    <td className="px-6 py-4"><StatusBadge variant={userStatusVariant(user.status)}>{user.status}</StatusBadge></td>
                    <td className="px-6 py-4 text-secondary">{user.lastActive ? formatDate(user.lastActive) : "Never"}</td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex justify-end gap-2">
                        <Link href={`/superadmin/users/edit?userId=${encodeURIComponent(user.id)}`}><Button variant="outline" className="h-8 gap-2"><Pencil className="h-3.5 w-3.5" /> Edit</Button></Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <EmptyState icon={UsersRound} title={`No ${activeConfig.label.toLowerCase()} found`} description="Try a different search or add a new account." />}
      </Card>
    </div>
  );
}
