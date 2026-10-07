import * as React from "react";
import { cn } from "@/lib/utils";

type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label: string;
};

export function Textarea({ className, label, id, ...props }: TextareaProps) {
  const textareaId = id ?? props.name;
  return (
    <div className="space-y-1.5">
      <label htmlFor={textareaId} className="ml-1 block text-body-sm font-medium text-on-surface-variant">
        {label}
      </label>
      <textarea
        id={textareaId}
        className={cn(
          "min-h-32 w-full rounded-xl border border-border-muted bg-surface-bright px-4 py-3 text-body-lg text-on-surface outline-none transition-all",
          "placeholder:text-outline focus:border-primary focus:ring-2 focus:ring-primary/15",
          className
        )}
        {...props}
      />
    </div>
  );
}
