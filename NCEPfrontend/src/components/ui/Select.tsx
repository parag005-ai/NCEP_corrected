import * as React from "react";
import { cn } from "@/lib/utils";

type SelectProps = React.SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
  options: string[];
};

export function Select({ className, label, options, id, ...props }: SelectProps) {
  const selectId = id ?? props.name;
  return (
    <div className="space-y-1.5">
      <label htmlFor={selectId} className="ml-1 block text-body-sm font-medium text-on-surface-variant">
        {label}
      </label>
      <select
        id={selectId}
        className={cn(
          "h-input-height w-full rounded-xl border border-border-muted bg-surface-bright px-4 text-body-lg text-on-surface outline-none transition-all",
          "focus:border-primary focus:ring-2 focus:ring-primary/15",
          className
        )}
        {...props}
      >
        {options.map((option) => (
          <option key={option}>{option}</option>
        ))}
      </select>
    </div>
  );
}
