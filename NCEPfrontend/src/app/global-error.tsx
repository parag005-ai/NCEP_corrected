"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/Button";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Global application error:", error);
  }, [error]);

  return (
    <html lang="en">
      <body className="bg-surface text-on-surface flex min-h-screen flex-col items-center justify-center p-6 text-center">
        <div className="flex flex-col items-center gap-4 max-w-md">
          <h1 className="text-headline-md font-bold">Application Error</h1>
          <p className="text-body-md text-secondary">
            {error.message || "A critical global error occurred."}
          </p>
          <Button onClick={() => reset()} variant="primary">
            Reset Application
          </Button>
        </div>
      </body>
    </html>
  );
}
