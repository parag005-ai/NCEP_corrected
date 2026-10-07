import { Building2, ChevronRight } from "lucide-react";

type SSOButtonProps = {
  onClick?: () => void;
};

export function SSOButton({ onClick }: SSOButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex h-input-height w-full items-center justify-between rounded-full bg-secondary-container px-6 text-body-lg font-medium text-primary-container transition-all duration-300 hover:-translate-y-0.5 hover:bg-secondary-container/80 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
    >
      <span className="flex items-center gap-3">
        <Building2 className="h-5 w-5 text-primary" strokeWidth={1.7} />
        Continue with Institution SSO
      </span>
      <ChevronRight className="h-5 w-5 text-primary" />
    </button>
  );
}
