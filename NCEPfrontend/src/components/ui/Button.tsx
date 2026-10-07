"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

type ButtonVariant = "primary" | "secondary" | "outline" | "ghost";

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
};

const variants: Record<ButtonVariant, string> = {
  primary: "bg-primary-container text-on-primary shadow-sm hover:bg-surface-tint hover:shadow-md",
  secondary: "bg-secondary-container text-primary hover:bg-secondary-container/80",
  outline: "border border-primary text-primary hover:bg-primary/5",
  ghost: "text-secondary hover:bg-secondary-container/45 hover:text-primary"
};

export function Button({ className, variant = "primary", type = "button", ...props }: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(
        "inline-flex h-input-height items-center justify-center gap-2 rounded-xl px-5 text-body-lg font-medium transition-all duration-200",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
        "disabled:pointer-events-none disabled:opacity-60",
        variants[variant],
        className
      )}
      {...props}
    />
  );
}
