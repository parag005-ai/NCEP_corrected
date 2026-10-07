"use client";

import { useState } from "react";
import { Mail } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { PasswordField } from "@/components/auth/PasswordField";
import { useAuth } from "@/providers/AuthProvider";

export function LoginCard() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError("");

    if (!email.trim()) {
      setError("Please enter your email or ID.");
      return;
    }
    if (!password.trim()) {
      setError("Please enter your password.");
      return;
    }

    setSubmitting(true);
    try {
      const result = await login(email.trim(), password);
      if (!result.ok) {
        setError(result.error ?? "Login failed.");
        setSubmitting(false);
      }
      // on success, AuthProvider redirects automatically
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed unexpectedly.");
      setSubmitting(false);
    }
  }

  return (
    <Card className="w-full max-w-[480px] rounded-[20px] p-6 sm:p-7 shadow-lg transition-transform duration-500 hover:-translate-y-1">
      <div className="mb-5 text-center">
        <p className="mb-1 text-xs uppercase tracking-widest text-secondary font-semibold">
          SECURE PORTAL ACCESS
        </p>
        <h1 className="text-3xl font-bold text-on-surface sm:text-4xl">Welcome Back</h1>
        <p className="mt-1 text-sm text-secondary">
          Access the Neuro Cardiac Electrophysiology Platform securely.
        </p>
      </div>

      <form className="space-y-4" onSubmit={handleSubmit}>
        <Input
          label="Email or ID"
          name="email"
          type="text"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="name@hospital.org or pat-001"
          icon={<Mail className="h-5 w-5" strokeWidth={1.6} />}
          required
          autoComplete="username"
        />
        <PasswordField
          showForgot
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        {error && (
          <p className="rounded-lg bg-error/5 px-4 py-2.5 text-body-sm font-medium text-error">
            {error}
          </p>
        )}

        <Button type="submit" className="w-full" disabled={submitting}>
          {submitting ? "Signing in…" : "Sign In"}
        </Button>
      </form>

      <div className="mt-5 text-center text-xs text-secondary">
        Need access?{" "}
        <a className="font-medium text-primary hover:underline" href="#">
          Contact your administrator
        </a>
      </div>
    </Card>
  );
}
