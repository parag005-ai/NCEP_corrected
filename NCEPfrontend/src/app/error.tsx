"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/Button";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Application runtime error caught by boundary:", error);
  }, [error]);

  return (
    <div className="flex min-h-[400px] flex-col items-center justify-center gap-4 text-center p-6">
      <h2 className="text-headline-sm font-semibold text-on-surface">Something went wrong</h2>
      <p className="text-body-md text-secondary max-w-md">
        {error.message || "An unexpected error occurred."}
      </p>
      <Button onClick={() => reset()} variant="primary">
        Try Again
      </Button>
    </div>
  );
}
