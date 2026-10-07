import * as React from "react";
import { cn } from "@/lib/utils";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  icon?: React.ReactNode;
  rightElement?: React.ReactNode;
};

export function Input({ className, label, icon, rightElement, id, ...props }: InputProps) {
  const inputId = id ?? props.name;
  return (
    <div className="space-y-1.5">
      {label ? (
        <label htmlFor={inputId} className="ml-1 block text-body-sm font-medium text-on-surface-variant">
          {label}
        </label>
      ) : null}
      <div className="group relative">
        {icon ? <span className="absolute left-4 top-1/2 -translate-y-1/2 text-outline group-focus-within:text-primary">{icon}</span> : null}
        <input
          id={inputId}
          className={cn(
            "h-input-height w-full rounded-xl border border-border-muted bg-surface-bright px-4 text-body-lg text-on-surface outline-none transition-all",
            "placeholder:text-outline focus:border-primary focus:ring-2 focus:ring-primary/15",
            icon && "pl-12",
            rightElement && "pr-12",
            className
          )}
          {...props}
        />
        {rightElement ? (
          <div className="absolute right-4 top-1/2 -translate-y-1/2 flex items-center text-outline">
            {rightElement}
          </div>
        ) : null}
      </div>
    </div>
  );
}
