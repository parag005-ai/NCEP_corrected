"use client";

import { useState } from "react";
import { EyeOff, Eye, Lock } from "lucide-react";
import { cn } from "@/lib/utils";

type PasswordFieldProps = {
  showForgot?: boolean;
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
};

export function PasswordField({ showForgot = true, value, onChange }: PasswordFieldProps) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="space-y-1.5">
      <div className="ml-1 flex items-center justify-between">
        <label htmlFor="password" className="text-body-sm font-medium text-on-surface-variant">
          Password
        </label>
        {showForgot ? (
          <a className="text-caption text-primary hover:underline" href="#">
            Forgot?
          </a>
        ) : null}
      </div>
      <div className="group relative">
        <Lock className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-outline group-focus-within:text-primary" strokeWidth={1.6} />
        <input
          id="password"
          name="password"
          type={visible ? "text" : "password"}
          placeholder="••••••••"
          value={value}
          onChange={onChange}
          autoComplete="current-password"
          required
          className={cn(
            "h-input-height w-full rounded-xl border border-border-muted bg-surface-bright px-12 text-body-lg text-on-surface outline-none transition-all",
            "placeholder:text-outline focus:border-primary focus:ring-2 focus:ring-primary/15",
          )}
        />
        <button
          type="button"
          aria-label={visible ? "Hide password" : "Show password"}
          onClick={() => setVisible((v) => !v)}
          className="absolute right-4 top-1/2 -translate-y-1/2 text-outline transition-colors hover:text-on-surface focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
        >
          {visible ? <Eye className="h-5 w-5" /> : <EyeOff className="h-5 w-5" />}
        </button>
      </div>
    </div>
  );
}
