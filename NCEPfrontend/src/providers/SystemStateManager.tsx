"use client";

import React, { useEffect, useState } from "react";
import OfflinePage from "@/app/offline/page";
import MaintenancePage from "@/app/maintenance/page";

export function SystemStateManager({ children }: { children: React.ReactNode }) {
  const [isOffline, setIsOffline] = useState(false);
  const isMaintenance = process.env.NEXT_PUBLIC_MAINTENANCE_MODE === "true";

  useEffect(() => {
    if (typeof navigator !== "undefined") {
      setIsOffline(!navigator.onLine);
    }

    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  if (isMaintenance) {
    return <MaintenancePage />;
  }

  if (isOffline) {
    return <OfflinePage />;
  }

  return <>{children}</>;
}
