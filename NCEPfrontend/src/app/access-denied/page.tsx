"use client";

import { ShieldX } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/providers/AuthProvider";
import { getRedirectPath } from "@/services";

export default function AccessDeniedPage() {
  const { session } = useAuth();
  const redirectPath = session ? getRedirectPath(session.role) : "/login";

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-surface px-4">
      <div className="text-center">
        <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-error/10">
          <ShieldX className="h-10 w-10 text-error" strokeWidth={1.5} />
        </div>
        <h1 className="text-section-title text-on-surface">Access Denied</h1>
        <p className="mt-3 max-w-md text-body-lg text-secondary">
          You do not have permission to access this page. Please contact your administrator if you believe this is an error.
        </p>
        <div className="mt-8 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
          {session ? (
            <Link href={redirectPath}>
              <Button>Go to My Dashboard</Button>
            </Link>
          ) : (
            <Link href="/login">
              <Button>Return to Login</Button>
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
