"use client";

import { useState, useMemo, useEffect, Suspense } from "react";
import { useAuth } from "@/providers/AuthProvider";
import { getUsers, saveUser, getDoctors, saveDoctor, getPatients, getServiceErrorMessage } from "@/services";
import { formatDate } from "@/lib/utils";
import { PageHeader } from "@/components/layout/PageHeader";
import { useSearchParams } from "next/navigation";
import { Card } from "@/components/ui/Card";
import { StatusBadge, userStatusVariant, patientStatusVariant } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useToast } from "@/components/ui/Toast";
import { Search, Filter, Plus, Mail, UsersRound } from "lucide-react";
import { roleLabels } from "@/config/roles";
import type { User, UserStatus, Doctor, Patient } from "@/types";
import Link from "next/link";

type UserGroup = "users" | "doctors" | "patients";

const groups: Array<{ id: UserGroup; label: string; description: string; addHref: string; addLabel: string }> = [
  { id: "doctors", label: "Doctors", description: "Manage clinical staff profiles and system access.", addHref: "/admin/doctors/new", addLabel: "Add Staff" },
  { id: "patients", label: "Patients", description: "Manage patient profiles and assigned clinicians.", addHref: "/admin/patients/new", addLabel: "Add Patient" }
];

export default function AdminManageUsers() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <AdminManageUsersContent />
    </Suspense>
  );
}

function AdminManageUsersContent() {
  const { session } = useAuth();
  const { toast } = useToast();
  const searchParams = useSearchParams();
  const defaultTab = (searchParams.get("tab") as UserGroup) || "doctors";
  
  const [activeGroup, setActiveGroup] = useState<UserGroup>(
    groups.some(g => g.id === defaultTab) ? defaultTab : "doctors"
  );
  const activeConfig = groups.find((group) => group.id === activeGroup);

  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState("All");
  const [specialityFilter, setSpecialityFilter] = useState("All");
  const [page, setPage] = useState(1);
  const itemsPerPage = 10;
  
  const [trigger, setTrigger] = useState(0);

  const [orgUsers, setOrgUsers] = useState<User[]>([]);
  const [orgDoctors, setOrgDoctors] = useState<Doctor[]>([]);
  const [orgPatients, setOrgPatients] = useState<Patient[]>([]);

  const [userToDeactivate, setUserToDeactivate] = useState<User | null>(null);
  const [doctorToDeactivate, setDoctorToDeactivate] = useState<Doctor | null>(null);

  const confirmDeactivateUser = async () => {
    if (userToDeactivate) {
      await toggleUserStatus(userToDeactivate);
      setUserToDeactivate(null);
    }
  };

  const confirmDeactivateDoctor = async () => {
    if (doctorToDeactivate) {
      await toggleDoctorStatus(doctorToDeactivate);
      setDoctorToDeactivate(null);
    }
  };

  const refreshData = () => {
    if (!session?.organisationId) return;
    const orgId = session.organisationId;
    getUsers()
      .then((u) => setOrgUsers(u.filter((x) => x.organisationId === orgId)))
      .catch((err) => console.error("Error loading users:", err));
    getDoctors()
      .then((d) => setOrgDoctors(d.filter((x) => x.organisationId === orgId)))
      .catch((err) => console.error("Error loading doctors:", err));
    getPatients()
      .then((p) => setOrgPatients(p.filter((x) => x.organisationId === orgId)))
      .catch((err) => console.error("Error loading patients:", err));
  };

  useEffect(() => {
    refreshData();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.organisationId, trigger]);

  const filteredPatients = useMemo(() => {
    return orgPatients.filter((p) => {
      const matchesSearch = 
        p.name.toLowerCase().includes(search.toLowerCase()) || 
        p.email.toLowerCase().includes(search.toLowerCase());
      const matchesStatus = statusFilter === "All" || p.status === statusFilter;
      
      return matchesSearch && matchesStatus;
    });
  }, [orgPatients, search, statusFilter]);

  const paginatedPatients = filteredPatients.slice((page - 1) * itemsPerPage, page * itemsPerPage);
  const totalPagesPatients = Math.ceil(filteredPatients.length / itemsPerPage);

  const filteredDoctors = useMemo(() => {
    return orgDoctors.filter((d) => {
      const matchesSearch = 
        d.name.toLowerCase().includes(search.toLowerCase()) || 
        d.staffId.toLowerCase().includes(search.toLowerCase());
      const matchesStatus = statusFilter === "All" || d.status === statusFilter;
      const matchesRole = roleFilter === "All" || d.role === roleFilter;
      const matchesSpeciality = specialityFilter === "All" || d.speciality === specialityFilter;
      
      return matchesSearch && matchesStatus && matchesRole && matchesSpeciality;
    });
  }, [orgDoctors, search, statusFilter, roleFilter, specialityFilter]);

  const paginatedDoctors = filteredDoctors.slice((page - 1) * itemsPerPage, page * itemsPerPage);
  const totalPagesDoctors = Math.ceil(filteredDoctors.length / itemsPerPage);

  const filteredUsers = useMemo(() => {
    return orgUsers.filter((u) => {
      const matchesSearch = 
        u.name.toLowerCase().includes(search.toLowerCase()) || 
        u.email.toLowerCase().includes(search.toLowerCase());
      const matchesStatus = statusFilter === "All" || u.status === statusFilter;
      const matchesRole = roleFilter === "All" || u.role === roleFilter.toLowerCase();
      
      return matchesSearch && matchesStatus && matchesRole;
    });
  }, [orgUsers, search, statusFilter, roleFilter]);

  const paginatedUsers = filteredUsers.slice((page - 1) * itemsPerPage, page * itemsPerPage);
  const totalPagesUsers = Math.ceil(filteredUsers.length / itemsPerPage);

  const toggleUserStatus = async (user: User) => {
    if (user.id === session?.userId) {
      toast("You cannot deactivate your own account.", "error");
      return;
    }
    try {
      const newStatus: UserStatus = user.status === "Active" ? "Inactive" : "Active";
      await saveUser({ ...user, status: newStatus });
      toast(`User ${user.name} marked as ${newStatus}`, "success");
      setTrigger(t => t + 1);
    } catch (error) {
      toast(getServiceErrorMessage(error), "error");
    }
  };

  const resendInvite = (user: User) => {
    toast(`Invitation resent to ${user.email}`, "info");
  };

  const toggleDoctorStatus = async (doctor: Doctor) => {
    try {
      const newStatus = doctor.status === "Active" ? "Inactive" : "Active";
      await saveDoctor({ ...doctor, status: newStatus });
      toast(`Staff member ${doctor.name} marked as ${newStatus}`, "success");
      setTrigger(t => t + 1);
    } catch (error) {
      toast(getServiceErrorMessage(error), "error");
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title="Manage Users"
        description="Add, edit, and manage platform access for administrators, doctors, and staff."
        actions={
          activeConfig ? (
            <Link href={activeConfig.addHref}>
              <Button className="gap-2">
                <Plus className="h-4 w-4" /> {activeConfig.addLabel}
              </Button>
            </Link>
          ) : null
        }
      />

      <div className="flex flex-wrap gap-3" aria-label="User type">
        {groups.map((group) => (
          <button
            key={group.id}
            type="button"
            onClick={() => { 
              setActiveGroup(group.id); 
              setSearch(""); 
              setRoleFilter("All");
              setStatusFilter("All");
              setSpecialityFilter("All");
              setPage(1);
            }}
            className={`rounded-full border px-5 py-2.5 text-body-sm font-medium transition-colors ${
              activeGroup === group.id 
                ? "border-primary bg-primary text-on-primary" 
                : "border-border-muted bg-surface text-secondary hover:border-primary hover:text-primary"
            }`}
          >
            {group.label}
          </button>
        ))}
      </div>

      <Card className="overflow-hidden">
        <div className="flex flex-col gap-4 border-b border-border-muted bg-surface-bright p-5">
          <div>
            <h2 className="font-semibold text-on-surface">{activeConfig?.label}</h2>
            <p className="mt-1 text-body-sm text-secondary">{activeConfig?.description}</p>
          </div>
          
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="relative w-full md:max-w-xs">
              <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-outline" />
              <input
                type="text"
                placeholder={
                  activeGroup === "doctors"
                    ? "Search doctors by name or ID..."
                    : `Search ${activeConfig?.label?.toLowerCase() || 'users'}...`
                }
                value={search}
                onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                className="h-10 w-full rounded-xl border border-border-muted bg-surface px-10 text-body-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
              />
            </div>
            
            <div className="flex flex-wrap items-center gap-2">
              <Filter className="h-5 w-5 text-secondary" />
              {activeGroup === "users" && (
                <>
                  <select
                    value={roleFilter}
                    onChange={(e) => { setRoleFilter(e.target.value); setPage(1); }}
                    className="h-10 rounded-xl border border-border-muted bg-surface px-3 text-body-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                  >
                    <option value="All">All Roles</option>
                    {Object.entries(roleLabels).map(([key, label]) => (
                      <option key={key} value={key}>{label}</option>
                    ))}
                  </select>

                  <select
                    value={statusFilter}
                    onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
                    className="h-10 rounded-xl border border-border-muted bg-surface px-3 text-body-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                  >
                    <option value="All">All Statuses</option>
                    <option value="Active">Active</option>
                    <option value="Invited">Invited</option>
                    <option value="Inactive">Inactive</option>
                    <option value="Suspended">Suspended</option>
                  </select>
                </>
              )}
              
              {activeGroup === "doctors" && (
                <>
                  <select
                    value={roleFilter}
                    onChange={(e) => { setRoleFilter(e.target.value); setPage(1); }}
                    className="h-10 rounded-xl border border-border-muted bg-surface px-3 text-body-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                  >
                    <option value="All">All Roles</option>
                    <option value="Doctor">Doctor</option>
                    <option value="Technician">Technician</option>
                    <option value="Support Staff">Support Staff</option>
                  </select>

                  <select
                    value={specialityFilter}
                    onChange={(e) => { setSpecialityFilter(e.target.value); setPage(1); }}
                    className="h-10 rounded-xl border border-border-muted bg-surface px-3 text-body-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                  >
                    <option value="All">All Specialities</option>
                    <option value="Cardiac Electrophysiology">Cardiac Electrophysiology</option>
                    <option value="Cardiology">Cardiology</option>
                    <option value="Neurology">Neurology</option>
                    <option value="ECG Technology">ECG Technology</option>
                  </select>
                </>
              )}
              
              {activeGroup === "patients" && (
                <select
                  value={statusFilter}
                  onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
                  className="h-10 rounded-xl border border-border-muted bg-surface px-3 text-body-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                >
                  <option value="All">All Statuses</option>
                  <option value="Stable">Stable</option>
                  <option value="Review Required">Review Required</option>
                  <option value="Pending Upload">Pending Upload</option>
                  <option value="Critical">Critical</option>
                </select>
              )}
            </div>
          </div>
        </div>

        {activeGroup === "users" ? (
          paginatedUsers.length > 0 ? (
            <>
              <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
                <table className="w-full text-left text-body-sm relative">
                  <thead className="sticky top-0 z-10 border-b border-border-muted bg-surface-bright text-caption text-secondary">
                    <tr>
                      <th className="px-6 py-4 font-medium">Name</th>
                      <th className="px-6 py-4 font-medium">Email</th>
                      <th className="px-6 py-4 font-medium">Role</th>
                      <th className="px-6 py-4 font-medium">Status</th>
                      <th className="px-6 py-4 font-medium">Last Active</th>
                      <th className="px-6 py-4 font-medium text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-muted text-on-surface">
                    {paginatedUsers.map((user) => (
                      <tr key={user.id} className="transition-colors hover:bg-surface-bright/50">
                        <td className="px-6 py-4 font-medium">{user.name}</td>
                        <td className="px-6 py-4 text-secondary">{user.email}</td>
                        <td className="px-6 py-4 capitalize">{roleLabels[user.role]}</td>
                        <td className="px-6 py-4">
                          <StatusBadge variant={userStatusVariant(user.status)}>{user.status}</StatusBadge>
                        </td>
                        <td className="px-6 py-4 text-secondary">{user.lastActive ? formatDate(user.lastActive) : "Never"}</td>
                        <td className="px-6 py-4 text-right">
                          <div className="flex justify-end gap-2">
                            {user.status === "Invited" && (
                              <Button variant="ghost" className="h-8 p-2 text-secondary" onClick={() => resendInvite(user)} title="Resend Invite">
                                <Mail className="h-4 w-4" />
                              </Button>
                            )}
                            <Button variant="outline" className="h-8" onClick={() => {
                              if (user.status === "Active") {
                                if (user.id === session?.userId) {
                                  toast("You cannot deactivate your own account.", "error");
                                } else {
                                  setUserToDeactivate(user);
                                }
                              } else {
                                toggleUserStatus(user);
                              }
                            }}>
                              {user.status === "Active" ? "Deactivate" : "Activate"}
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {totalPagesUsers > 1 && (
                <div className="flex items-center justify-between border-t border-border-muted bg-surface-bright px-6 py-3">
                  <p className="text-body-sm text-secondary">
                    Showing {(page - 1) * itemsPerPage + 1} to {Math.min(page * itemsPerPage, filteredUsers.length)} of {filteredUsers.length}
                  </p>
                  <div className="flex gap-2">
                    <Button variant="outline" className="h-8" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Prev</Button>
                    <Button variant="outline" className="h-8" onClick={() => setPage(p => Math.min(totalPagesUsers, p + 1))} disabled={page === totalPagesUsers}>Next</Button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <EmptyState icon={UsersRound} title="No users found" description="No users match your current search filters." />
          )
        ) : activeGroup === "doctors" ? (
          paginatedDoctors.length > 0 ? (
            <>
              <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
                <table className="w-full text-left text-body-sm relative">
                  <thead className="sticky top-0 z-10 border-b border-border-muted bg-surface-bright text-caption text-secondary">
                    <tr>
                      <th className="px-6 py-4 font-medium">Name</th>
                      <th className="px-6 py-4 font-medium">Staff ID</th>
                      <th className="px-6 py-4 font-medium">Role</th>
                      <th className="px-6 py-4 font-medium">Speciality</th>
                      <th className="px-6 py-4 font-medium text-center">Patients</th>
                      <th className="px-6 py-4 font-medium">Status</th>
                      <th className="px-6 py-4 font-medium text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-muted text-on-surface">
                    {paginatedDoctors.map((doc) => (
                      <tr key={doc.id} className="transition-colors hover:bg-surface-bright/50">
                        <td className="px-6 py-4 font-medium">
                          {doc.name}
                          <span className="block text-caption font-normal text-secondary">{doc.email}</span>
                        </td>
                        <td className="px-6 py-4 text-secondary">{doc.staffId}</td>
                        <td className="px-6 py-4">{doc.role}</td>
                        <td className="px-6 py-4">{doc.speciality}</td>
                        <td className="px-6 py-4 text-center">{doc.assignedPatientCount}</td>
                        <td className="px-6 py-4">
                          <StatusBadge variant={userStatusVariant(doc.status)}>{doc.status}</StatusBadge>
                        </td>
                        <td className="px-6 py-4 text-right">
                          <Button variant="outline" className="h-8" onClick={() => {
                            if (doc.status === "Active") {
                              setDoctorToDeactivate(doc);
                            } else {
                              toggleDoctorStatus(doc);
                            }
                          }}>
                            {doc.status === "Active" ? "Deactivate" : "Activate"}
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {totalPagesDoctors > 1 && (
                <div className="flex items-center justify-between border-t border-border-muted bg-surface-bright px-6 py-3">
                  <p className="text-body-sm text-secondary">
                    Showing {(page - 1) * itemsPerPage + 1} to {Math.min(page * itemsPerPage, filteredDoctors.length)} of {filteredDoctors.length}
                  </p>
                  <div className="flex gap-2">
                    <Button variant="outline" className="h-8" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Prev</Button>
                    <Button variant="outline" className="h-8" onClick={() => setPage(p => Math.min(totalPagesDoctors, p + 1))} disabled={page === totalPagesDoctors}>Next</Button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <EmptyState icon={UsersRound} title="No staff found" description="No doctors or staff match your current search filters." />
          )
        ) : (
          paginatedPatients.length > 0 ? (
            <>
              <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
                <table className="w-full text-left text-body-sm relative">
                  <thead className="sticky top-0 z-10 border-b border-border-muted bg-surface-bright text-caption text-secondary">
                    <tr>
                      <th className="px-6 py-4 font-medium">Name</th>
                      <th className="px-6 py-4 font-medium">Age & Gender</th>
                      <th className="px-6 py-4 font-medium">Assigned Doctor</th>
                      <th className="px-6 py-4 font-medium">Status</th>
                      <th className="px-6 py-4 font-medium text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-muted text-on-surface">
                    {paginatedPatients.map((patient) => (
                      <tr key={patient.id} className="transition-colors hover:bg-surface-bright/50">
                        <td className="px-6 py-4 font-medium">
                          {patient.name}
                          <span className="block text-caption font-normal text-secondary">{patient.email}</span>
                        </td>
                        <td className="px-6 py-4 text-secondary">{patient.age} / {patient.gender}</td>
                        <td className="px-6 py-4">{patient.assignedDoctor}</td>
                        <td className="px-6 py-4">
                          <StatusBadge variant={patientStatusVariant(patient.status)}>{patient.status}</StatusBadge>
                        </td>
                        <td className="px-6 py-4 text-right">
                          <Link href={`/admin/patients/${patient.id}`}>
                            <Button variant="outline" className="h-8">View</Button>
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {totalPagesPatients > 1 && (
                <div className="flex items-center justify-between border-t border-border-muted bg-surface-bright px-6 py-3">
                  <p className="text-body-sm text-secondary">
                    Showing {(page - 1) * itemsPerPage + 1} to {Math.min(page * itemsPerPage, filteredPatients.length)} of {filteredPatients.length}
                  </p>
                  <div className="flex gap-2">
                    <Button variant="outline" className="h-8" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Prev</Button>
                    <Button variant="outline" className="h-8" onClick={() => setPage(p => Math.min(totalPagesPatients, p + 1))} disabled={page === totalPagesPatients}>Next</Button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <EmptyState icon={UsersRound} title="No patients found" description="No patients match your current search filters." />
          )
        )}
      </Card>
      
      <ConfirmDialog 
        open={!!userToDeactivate} 
        title="Are you sure?" 
        description={`Are you sure you want to deactivate ${userToDeactivate?.name}'s account? They will lose access to the platform.`} 
        confirmLabel="Yes, deactivate" 
        cancelLabel="Cancel" 
        variant="danger" 
        onCancel={() => setUserToDeactivate(null)} 
        onConfirm={confirmDeactivateUser} 
      />
      <ConfirmDialog 
        open={!!doctorToDeactivate} 
        title="Are you sure?" 
        description={`Are you sure you want to deactivate ${doctorToDeactivate?.name}'s account? They will lose access to the platform.`} 
        confirmLabel="Yes, deactivate" 
        cancelLabel="Cancel" 
        variant="danger" 
        onCancel={() => setDoctorToDeactivate(null)} 
        onConfirm={confirmDeactivateDoctor} 
      />
    </div>
  );
}
