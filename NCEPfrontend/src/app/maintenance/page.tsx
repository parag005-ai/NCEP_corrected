import Link from "next/link";
import { BriefcaseMedical } from "lucide-react";
import { Button } from "@/components/ui/Button";

export default function Maintenance() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-between bg-surface-bright px-4 font-sans py-12">
      <div /> {/* Spacer for flex-between */}

      {/* Main Content */}
      <div className="flex w-full max-w-2xl flex-col items-center text-center">
        {/* Icon */}
        <div className="mb-8 flex items-center justify-center">
          <BriefcaseMedical className="h-14 w-14 text-primary" strokeWidth={2.5} />
        </div>

        <h1 className="text-[40px] font-medium text-primary tracking-tight">
          System Maintenance
        </h1>
        <p className="mt-4 max-w-[500px] text-[15px] text-on-surface-variant leading-relaxed">
          The CardioNexus Diagnostic Platform is undergoing scheduled enhancements to ensure peak precision. We expect to be back online shortly.
        </p>

        <div className="mt-10">
          <Link href="/status">
            <Button variant="outline" className="rounded-full px-8 h-12 border-[#d0d8d6] text-[#4a5855] hover:bg-surface-container-low transition-colors bg-transparent shadow-sm">
              Check System Status
            </Button>
          </Link>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-16 w-full max-w-4xl text-center">
        <div className="mb-6 flex flex-wrap items-center justify-center gap-y-3 gap-x-8 text-[11px] font-medium text-[#a7b5b2] uppercase tracking-widest">
          {/* <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 stroke-[1.5]" />
            <span>HIPAA COMPLIANT</span>
          </div>
          <div className="hidden h-3 w-[1px] bg-[#dce6e3] sm:block" />
          <div className="flex items-center gap-2">
            <PlusSquare className="h-4 w-4 stroke-[1.5]" />
            <span>FDA CLEARED (CLASS II)</span>
          </div>
          <div className="hidden h-3 w-[1px] bg-[#dce6e3] sm:block" />
          <div className="flex items-center gap-2">
            <Lock className="h-4 w-4 stroke-[1.5]" />
            <span>AES-256 ENCRYPTED</span>
          </div> */}
        </div>

        <div className="flex flex-col items-center gap-3">
          <div className="text-[11px] font-bold uppercase tracking-widest text-[#a7b5b2]">
            CARDIONEXUS NEURO-CARDIAC ELECTROPHYSIOLOGY
          </div>
          <p className="text-[11px] font-medium text-[#a7b5b2]">
            &copy; 2024 CardioNexus Platform. Enterprise Grade Diagnostics.
          </p>
          <div className="flex gap-6 text-[11px] font-medium text-[#a7b5b2]">
            <Link href="/privacy" className="hover:text-primary transition-colors">Data Privacy Policy</Link>
            <span className="h-1 w-1 rounded-full bg-[#a7b5b2]/50 self-center"></span>
            <Link href="/support" className="hover:text-primary transition-colors">Technical Support</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
