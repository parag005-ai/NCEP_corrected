/* eslint-disable @next/next/no-img-element */
"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LogOut, Menu } from "lucide-react";
import { useState, useEffect } from "react";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { roleNavigation } from "@/config/navigation";
import { roleLabels } from "@/config/roles";
import { Logo } from "@/components/ui/Logo";
import { useAuth } from "@/providers/AuthProvider";
import type { Role } from "@/types";
import { cn } from "@/lib/utils";

export function DashboardShell({ role, children }: { role: Role; children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { session, loading, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [sidebarExpanded, setSidebarExpanded] = useState(true);
  const [isMobile, setIsMobile] = useState(false);
  const [showSignoutConfirm, setShowSignoutConfirm] = useState(false);

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 1024);
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  useEffect(() => {
    if (loading) return;
    if (!session) {
      router.replace("/login");
      return;
    }
    if (session.role !== role) {
      router.replace("/access-denied");
    }
  }, [loading, role, router, session]);

  const toggleSidebar = () => {
    if (window.innerWidth >= 1024) {
      setSidebarExpanded((expanded) => !expanded);
      return;
    }
    setMobileOpen((open) => !open);
  };

  // ── Client-side route guard ──
  if (loading || !session || session.role !== role) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  const navItems = roleNavigation[role];

  const settingsHref =
    role === "admin" ? "/admin/settings" :
    role === "superadmin" ? "/superadmin/system-settings" :
    null;

  const profileHref = `/${role}/profile`;

  const initials = session.name
    ? session.name.split(" ").map((n: string) => n[0]).join("").slice(0, 2).toUpperCase()
    : "?";

  return (
    <div className="min-h-screen bg-surface flex flex-col">
      {/* ── Top bar ── */}
      <header className="sticky top-0 z-40 h-header-height border-b border-border-muted bg-surface/95 backdrop-blur">
        <div className="flex h-full items-center justify-between px-margin-mobile sm:px-gutter">
          
          {/* Logo / Sidebar Toggle */}
          <div className="flex items-center">
            {(!sidebarExpanded || isMobile) ? (
              <div
                className="flex items-center cursor-pointer select-none"
                onClick={toggleSidebar}
                title="Open Sidebar"
              >
                <div className="flex h-8 w-8 items-center justify-center mr-2 text-[#0A6B5C]">
                  <Menu className="h-6 w-6" strokeWidth={2.5} />
                </div>
                <span className="text-xl font-bold leading-none tracking-tight text-[#0A6B5C]">CardioNexus</span>
              </div>
            ) : (
              <Link href={`/${role}/dashboard`} className="flex items-center transition-opacity hover:opacity-90">
                <Logo />
              </Link>
            )}
          </div>

          {/* Profile dropdown */}
          <ProfileMenu
            name={session.name}
            initials={initials}
            profileHref={profileHref}
            settingsHref={settingsHref}
            avatarUrl={session.avatarUrl}
          />
        </div>
      </header>

      <div className="flex flex-1 min-w-0 flex-col lg:flex-row">
        {/* ── Mobile overlay ── */}
        {mobileOpen && (
          <div className="fixed inset-0 z-30 bg-black/30 lg:hidden" onClick={() => setMobileOpen(false)} />
        )}

        {/* ── Sidebar ── */}
        <aside
          className={cn(
            "flex flex-col fixed left-0 top-header-height z-30 h-[calc(100vh-72px)] w-72 shrink-0 overflow-y-scroll scrollbar-none border-r border-border-muted bg-surface-container-lowest transition-[transform,width,opacity] duration-300 lg:sticky lg:translate-x-0",
            mobileOpen ? "translate-x-0" : "-translate-x-full",
            sidebarExpanded ? "lg:w-72 lg:opacity-100" : "lg:w-0 lg:overflow-hidden lg:border-r-0 lg:opacity-0",
          )}
        >
          <div className="flex items-center justify-between px-4 py-5">
            <p className="text-caption uppercase text-secondary">{roleLabels[role]} Workspace</p>
            <button
              type="button"
              className="inline-flex h-8 w-8 items-center justify-center rounded-xl text-secondary transition-colors hover:bg-secondary-container/40 hover:text-primary"
              onClick={toggleSidebar}
              title="Close Sidebar"
            >
              <TripleRightArrows className="h-5 w-5 rotate-180" />
            </button>
          </div>
          <nav className="flex flex-col gap-1 px-3 pb-4">
            {navItems.map((item) => {
              const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMobileOpen(false)}
                  className={cn(
                    "flex items-center gap-3 rounded-xl px-4 py-3 text-body-sm font-medium text-secondary transition-colors",
                    "focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary",
                    isActive
                      ? "bg-secondary-container text-primary shadow-sm"
                      : "hover:bg-secondary-container/40 hover:text-primary",
                  )}
                >
                  <Icon className="h-5 w-5" strokeWidth={1.6} />
                  <span className="truncate">{item.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Bottom Section */}
          <div className="mt-auto flex flex-col px-3 pb-4">
            
            {/* Sign Out Button in Sidebar */}
            <button
              type="button"
              onClick={() => setShowSignoutConfirm(true)}
              className="flex items-center gap-3 rounded-xl px-4 py-3 text-body-sm font-medium text-secondary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary hover:bg-[#fff0f0] hover:text-critical"
            >
              <LogOut className="h-5 w-5" strokeWidth={1.6} />
              <span className="truncate">Sign Out</span>
            </button>

            {/* Divider */}
            <div className="my-3 border-t border-border-muted" />

            {/* Version Text */}
            <div className="w-full text-center py-1.5">
              <p className="text-[11px] font-medium tracking-wide text-secondary/70">
                CardioNexus v0.0.1
              </p>
            </div>
          </div>
        </aside>

        {/* ── Main content ── */}
        <main className="w-full min-w-0 flex-1 px-margin-mobile py-8 sm:px-gutter lg:px-8">{children}</main>
      </div>

      <ConfirmDialog
        open={showSignoutConfirm}
        title="Sign Out"
        description="Are you sure you want to sign out of CardioNexus?"
        confirmLabel="Sign Out"
        variant="danger"
        onCancel={() => setShowSignoutConfirm(false)}
        onConfirm={() => {
          setShowSignoutConfirm(false);
          void logout().catch((err) => console.error("Error signing out:", err));
        }}
      />
    </div>
  );
}

// ── Profile dropdown sub-component ──
function ProfileMenu({
  name,
  initials,
  profileHref,
  settingsHref,
  avatarUrl,
}: {
  name: string;
  initials: string;
  profileHref: string;
  settingsHref: string | null;
  avatarUrl?: string;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      {/* Trigger */}
      <button
        type="button"
        id="profile-menu-button"
        aria-haspopup="true"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-xl px-2 py-1.5 text-body-sm text-secondary transition-colors hover:bg-secondary-container/40 hover:text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
      >
        {avatarUrl ? (
          <img src={avatarUrl} alt="Avatar" className="h-8 w-8 rounded-full object-cover" />
        ) : (
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-[11px] font-bold text-on-primary select-none">
            {initials}
          </span>
        )}
        {/* Chevron */}
        <svg
          className={cn("h-4 w-4 transition-transform duration-200", open && "rotate-180")}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>

      {/* Backdrop */}
      {open && (
        <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
      )}

      {/* Dropdown */}
      {open && (
        <div
          role="menu"
          aria-labelledby="profile-menu-button"
          className="absolute right-0 top-full z-50 mt-2 w-52 origin-top-right rounded-2xl border border-border-muted bg-surface-container-lowest py-1.5 shadow-panel"
        >
          {/* User info header */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-border-muted">
            {avatarUrl ? (
              <img src={avatarUrl} alt="Avatar" className="h-9 w-9 shrink-0 rounded-full object-cover" />
            ) : (
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary text-[12px] font-bold text-on-primary select-none">
                {initials}
              </span>
            )}
            <p className="truncate text-body-sm font-semibold text-on-surface">{name}</p>
          </div>

          {/* Profile */}
          <Link
            href={profileHref}
            role="menuitem"
            onClick={() => setOpen(false)}
            className="flex items-center gap-3 px-4 py-2.5 text-body-sm text-secondary transition-colors hover:bg-secondary-container/40 hover:text-primary"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="8" r="4" />
              <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" />
            </svg>
            Profile
          </Link>

          {/* Settings */}
          {settingsHref && (
            <Link
              href={settingsHref}
              role="menuitem"
              onClick={() => setOpen(false)}
              className="flex items-center gap-3 px-4 py-2.5 text-body-sm text-secondary transition-colors hover:bg-secondary-container/40 hover:text-primary"
            >
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
              </svg>
              Settings
            </Link>
          )}
        </div>
      )}
    </div>
  );
}

// ── Custom SVG Icons ──
function TripleRightArrows({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.5}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M4 6l6 6-6 6" />
      <path d="M10 6l6 6-6 6" />
      <path d="M16 6l6 6-6 6" />
    </svg>
  );
}
