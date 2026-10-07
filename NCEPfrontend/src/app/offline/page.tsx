import Link from "next/link";
import { ActivitySquare, WifiOff } from "lucide-react";
import { Button } from "@/components/ui/Button";

export default function Offline() {
  return (
    <div className="flex h-screen overflow-hidden flex-col items-center justify-center bg-surface-bright px-4 font-sans">
      {/* Header Logo */}
      <div className="mb-12 flex flex-col items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-surface-container-high text-primary">
          <ActivitySquare className="h-6 w-6" strokeWidth={2} />
        </div>
        <div className="text-center">
          <h1 className="text-body-lg font-bold text-primary">CardioNexus Enterprise</h1>
          <p className="mt-1 text-[9px] font-bold uppercase tracking-[0.2em] text-outline">
            Diagnostic Interface Terminal
          </p>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex w-full max-w-2xl flex-col items-center text-center">
        {/* Glowing Icon & Offline */}
        <div className="relative mt-8 flex flex-col items-center justify-center">
          {/* Subtle green background glow */}
          <div className="absolute top-1/2 -z-10 h-72 w-72 -translate-y-1/2 rounded-full bg-primary/5 blur-[60px]" />
          
          <div className="relative mb-6">
            <div className="flex h-[100px] w-[100px] items-center justify-center rounded-full border border-border-muted bg-surface-panel shadow-sm">
              <WifiOff className="h-12 w-12 text-secondary/70" strokeWidth={1.5} />
            </div>
            {/* Red Alert Badge */}
            <div className="absolute right-0 top-0 flex h-7 w-7 items-center justify-center rounded-full border-4 border-surface-bright bg-[#ffe4e4] text-[#ef4444]">
              <span className="text-sm font-bold">!</span>
            </div>
          </div>

          <h2 className="text-[90px] sm:text-[130px] font-extrabold leading-none tracking-tight text-primary">
            OFFLINE
          </h2>
          <div className="mt-6 h-1 w-24 bg-gradient-to-r from-transparent via-primary/30 to-transparent" />
        </div>

        <h3 className="mt-10 text-headline-lg font-bold text-on-surface">
          Network Connection Lost
        </h3>
        <p className="mt-4 max-w-lg text-body-lg leading-relaxed text-on-surface-variant">
          The diagnostic interface terminal has lost connection to the enterprise network. Please check your internet connectivity and try again.
        </p>

        <div className="mt-10 flex w-full flex-col gap-4 sm:flex-row sm:justify-center">
          <Link href="/">
            <Button variant="primary" className="w-full sm:w-auto px-6">Retry Connection</Button>
          </Link>
          <Link href="/support">
            <Button variant="outline" className="w-full sm:w-auto px-6 bg-surface-panel">Contact Technical Support</Button>
          </Link>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-16 w-full max-w-4xl px-4 text-center">
        <div className="mb-8 flex flex-wrap items-center justify-center gap-y-3 gap-x-8 text-[10px] font-semibold uppercase tracking-wider text-outline">
          {/* <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 stroke-[1.5]" />
            <span>HIPAA COMPLIANT SYSTEM</span>
          </div>
          <div className="hidden h-3 w-[1px] bg-border-muted sm:block" />
          <div className="flex items-center gap-2">
            <PlusSquare className="h-4 w-4 stroke-[1.5]" />
            <span>FDA CLEARED (CLASS II)</span>
          </div>
          <div className="hidden h-3 w-[1px] bg-border-muted sm:block" />
          <div className="flex items-center gap-2">
            <Lock className="h-4 w-4 stroke-[1.5]" />
            <span>AES-256 DATA ENCRYPTION</span>
          </div> */}
        </div>

        <div className="flex flex-col items-center gap-3">
          <div className="text-[10px] font-bold uppercase tracking-[0.25em] text-primary">
            CARDIONEXUS NEURO-CARDIAC ELECTROPHYSIOLOGY PLATFORM
          </div>
          <p className="text-[11px] font-medium text-outline">
            &copy; 2024 Enterprise Diagnostics Group. All system access is logged for compliance.
          </p>
          <div className="flex gap-6 text-[11px] font-medium text-outline">
            <Link href="/security" className="hover:text-primary transition-colors">Security Protocols</Link>
            <Link href="/status" className="hover:text-primary transition-colors">System Status</Link>
            <Link href="/privacy" className="hover:text-primary transition-colors">Privacy Policy</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
