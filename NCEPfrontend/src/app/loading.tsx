import { Spinner } from "@/components/ui/Spinner";

export default function GlobalLoading() {
  return (
    <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center bg-surface">
      <div className="flex flex-col items-center space-y-4">
        <Spinner size="xl" />
        <p className="text-body-sm text-secondary font-medium animate-pulse">
          Loading...
        </p>
      </div>
    </div>
  );
}
