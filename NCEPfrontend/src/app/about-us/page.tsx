import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { 
  Activity, 
  FlaskConical, 
  RefreshCw, 
  CheckCircle2
} from "lucide-react";
import Link from "next/link";

export default function AboutUsPage() {
  return (
    <div className="flex min-h-screen flex-col bg-[#f8f9fa] font-sans">
      <Navbar />

      <main className="flex-1 pt-[calc(72px+48px)] pb-24">
        {/* Hero Section */}
        <section className="px-6 mx-auto max-w-5xl text-center mb-24">
          <h1 className="text-4xl md:text-5xl lg:text-[56px] font-bold text-[#163c39] mb-6 leading-tight">
            Our Mission: Redefining Neuro-Cardiac Precision
          </h1>
          <p className="text-lg md:text-xl text-secondary max-w-3xl mx-auto leading-relaxed">
            Advancing diagnostic accuracy through state-of-the-art computational modeling, seamless real-time biometric analysis, and an unwavering commitment to clinical integrity in enterprise healthcare.
          </p>
        </section>

        {/* Bridging Neurology & Cardiology */}
        <section className="px-6 mx-auto max-w-container-max mb-28">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
            
            {/* Left Column Text */}
            <div className="lg:col-span-6 flex flex-col justify-center">
              <h2 className="text-3xl md:text-4xl font-bold text-primary mb-6">
                Bridging Neurology &amp; Cardiology
              </h2>
              <p className="text-body-lg text-secondary/90 leading-relaxed mb-6">
                The Neuro Cardiac Electrophysiology Platform (NCEP) is built on a foundation of absolute trust and technical auditability. We understand that in modern enterprise diagnostics, there is zero margin for error.
              </p>
              <p className="text-body-lg text-secondary/90 leading-relaxed">
                By harmonizing complex neurological datasets with high-fidelity cardiac telemetry, NCEP provides clinicians with an unparalleled, unified view of patient health, ensuring decisions are driven by crystal-clear, auditable data.
              </p>
            </div>

            {/* Right Column High-Fidelity Clinical Workstation Visual Card */}
            <div className="lg:col-span-6">
              <div className="relative rounded-2xl overflow-hidden bg-gradient-to-br from-[#0c2f2c] via-[#0f443e] to-[#155e56] p-6 md:p-8 shadow-xl border border-[#2CB5A5]/30">
                
                {/* Header bar of simulated workstation */}
                <div className="flex items-center justify-between pb-4 mb-6 border-b border-white/10">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-400" />
                    <div className="w-3 h-3 rounded-full bg-amber-400" />
                    <div className="w-3 h-3 rounded-full bg-green-400" />
                    <span className="ml-2 text-xs font-mono font-semibold tracking-wider text-on-primary-container">
                      NCEP TELEMETRY SUITE v4.2 • DUAL-MODALITY DIAGNOSTICS
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-white/70">
                    <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    <span>LIVE CLINICAL FEED</span>
                  </div>
                </div>

                {/* Simulated Multi-Monitor Telemetry Display */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                  
                  {/* Monitor 1: Cardiac Telemetry */}
                  <div className="bg-[#061e1b]/80 rounded-xl p-4 border border-white/10 flex flex-col justify-between">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">
                        ECG / Lead II Telemetry
                      </span>
                      <span className="text-xs font-mono text-white/80">72 BPM</span>
                    </div>
                    {/* SVG Waveform */}
                    <div className="h-20 w-full flex items-center overflow-hidden my-2">
                      <svg className="w-full h-12 stroke-emerald-400 fill-none" viewBox="0 0 300 50">
                        <path d="M0,25 L30,25 L40,22 L50,25 L70,25 L75,35 L85,5 L95,45 L105,25 L130,25 L145,15 L160,25 L200,25 L210,22 L220,25 L240,25 L245,35 L255,5 L265,45 L275,25 L300,25" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </div>
                    <div className="flex justify-between text-[11px] text-white/60 font-mono border-t border-white/10 pt-2">
                      <span>QRS: 88ms</span>
                      <span>QTc: 410ms</span>
                      <span>ST: Normal</span>
                    </div>
                  </div>

                  {/* Monitor 2: Neurological EEG Telemetry */}
                  <div className="bg-[#061e1b]/80 rounded-xl p-4 border border-white/10 flex flex-col justify-between">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs font-semibold text-cyan-300 uppercase tracking-wider">
                        EEG Spectral Array
                      </span>
                      <span className="text-xs font-mono text-white/80">Alpha/Theta</span>
                    </div>
                    {/* SVG Waveform */}
                    <div className="h-20 w-full flex items-center overflow-hidden my-2">
                      <svg className="w-full h-12 stroke-cyan-400 fill-none" viewBox="0 0 300 50">
                        <path d="M0,25 C15,10 30,40 45,20 C60,5 75,35 90,25 C105,15 120,40 135,20 C150,5 165,30 180,25 C195,15 210,35 225,20 C240,10 255,40 270,25 C285,15 295,30 300,25" strokeWidth="2" />
                      </svg>
                    </div>
                    <div className="flex justify-between text-[11px] text-white/60 font-mono border-t border-white/10 pt-2">
                      <span>Sync: 99.4%</span>
                      <span>Artifact: 0.1%</span>
                      <span>SEF: 14.2Hz</span>
                    </div>
                  </div>

                </div>

                {/* Footer status bar inside illustration */}
                <div className="bg-black/30 rounded-lg p-3 flex flex-wrap items-center justify-between text-xs text-white/80 border border-white/5">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span>Synchronized Neuro-Cardiac Analytics Engine • Active Clinical Session</span>
                  </div>
                  <span className="text-white/50 font-mono">ID: NCEP-ENTERPRISE-509</span>
                </div>

              </div>
            </div>

          </div>
        </section>

        {/* Core Pillars of Excellence */}
        <section className="px-6 mx-auto max-w-container-max mb-28">
          <h2 className="text-2xl md:text-3xl font-bold text-[#163c39] mb-12 text-center">
            Core Pillars of Excellence
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            
            {/* Card 1 */}
            <div className="bg-white rounded-2xl p-8 border border-border-muted/80 shadow-sm hover:shadow-md transition-all duration-300 flex flex-col items-start">
              <div className="w-12 h-12 rounded-full bg-secondary-container/50 flex items-center justify-center text-primary mb-6">
                <Activity className="h-6 w-6" strokeWidth={2} />
              </div>
              <h3 className="text-lg font-bold text-[#163c39] mb-3">
                Clinical Accuracy
              </h3>
              <p className="text-body-sm text-secondary/80 leading-relaxed">
                Engineered for sub-millisecond telemetry synchronization to ensure every data point reflects absolute physiological reality.
              </p>
            </div>

            {/* Card 2 */}
            <div className="bg-white rounded-2xl p-8 border border-border-muted/80 shadow-sm hover:shadow-md transition-all duration-300 flex flex-col items-start">
              <div className="w-12 h-12 rounded-full bg-secondary-container/50 flex items-center justify-center text-primary mb-6">
                <FlaskConical className="h-6 w-6" strokeWidth={2} />
              </div>
              <h3 className="text-lg font-bold text-[#163c39] mb-3">
                Evidence-Led Design
              </h3>
              <p className="text-body-sm text-secondary/80 leading-relaxed">
                User interfaces crafted specifically for high-stakes diagnostic environments, minimizing cognitive load and prioritizing critical alerts.
              </p>
            </div>

            {/* Card 3 */}
            <div className="bg-white rounded-2xl p-8 border border-border-muted/80 shadow-sm hover:shadow-md transition-all duration-300 flex flex-col items-start">
              <div className="w-12 h-12 rounded-full bg-secondary-container/50 flex items-center justify-center text-primary mb-6">
                <RefreshCw className="h-6 w-6" strokeWidth={2} />
              </div>
              <h3 className="text-lg font-bold text-[#163c39] mb-3">
                Data Integrity
              </h3>
              <p className="text-body-sm text-secondary/80 leading-relaxed">
                End-to-end AES-256 encryption with immutable audit logs, fully compliant with international healthcare data regulations.
              </p>
            </div>

          </div>
        </section>

        {/* Institutional Impact */}
        <section className="px-6 mx-auto max-w-container-max mb-28">
          <div className="bg-surface-container-low rounded-3xl p-8 md:p-12 border border-border-muted/60 relative overflow-hidden flex flex-col md:flex-row items-center justify-between gap-10">
            
            {/* Left Content */}
            <div className="max-w-xl z-10">
              <h2 className="text-2xl font-bold text-primary mb-4">
                Institutional Impact
              </h2>
              <p className="text-body-lg text-secondary/90 leading-relaxed mb-8">
                Deployed in over 50 leading diagnostic centers worldwide, NCEP has fundamentally streamlined the workflow between neurology and cardiology departments. By reducing data silos, our platform has demonstrated a 40% reduction in time-to-diagnosis for complex arrhythmias and neurological events.
              </p>
              <Link
                href="/clinical-evidence"
                className="inline-flex items-center justify-center bg-primary hover:bg-primary/90 text-on-primary font-medium px-6 py-3 rounded-lg shadow-sm transition-all duration-200 hover:scale-[1.02]"
              >
                View Case Studies
              </Link>
            </div>

            {/* Right Graphic: Connected Node Network Diagram */}
            <div className="relative z-10 flex items-center justify-center shrink-0 w-64 h-64 md:w-80 md:h-80">
              <svg className="w-full h-full text-secondary/15" viewBox="0 0 200 200" fill="currentColor">
                {/* Center Node */}
                <circle cx="100" cy="100" r="22" className="fill-secondary/20" />
                <circle cx="100" cy="100" r="14" className="fill-secondary/35" />

                {/* Outer Node 1 (Top) */}
                <line x1="100" y1="100" x2="100" y2="35" stroke="currentColor" strokeWidth="10" strokeLinecap="round" />
                <circle cx="100" cy="35" r="18" className="fill-secondary/20" />
                <circle cx="100" cy="35" r="10" className="fill-secondary/35" />

                {/* Outer Node 2 (Left) */}
                <line x1="100" y1="100" x2="35" y2="95" stroke="currentColor" strokeWidth="10" strokeLinecap="round" />
                <circle cx="35" cy="95" r="18" className="fill-secondary/20" />
                <circle cx="35" cy="95" r="10" className="fill-secondary/35" />

                {/* Outer Node 3 (Right) */}
                <line x1="100" y1="100" x2="165" y2="95" stroke="currentColor" strokeWidth="10" strokeLinecap="round" />
                <circle cx="165" cy="95" r="18" className="fill-secondary/20" />
                <circle cx="165" cy="95" r="10" className="fill-secondary/35" />

                {/* Outer Node 4 (Bottom Left) */}
                <line x1="100" y1="100" x2="60" y2="165" stroke="currentColor" strokeWidth="10" strokeLinecap="round" />
                <circle cx="60" cy="165" r="18" className="fill-secondary/20" />
                <circle cx="60" cy="165" r="10" className="fill-secondary/35" />

                {/* Outer Node 5 (Bottom Right) */}
                <line x1="100" y1="100" x2="140" y2="165" stroke="currentColor" strokeWidth="10" strokeLinecap="round" />
                <circle cx="140" cy="165" r="18" className="fill-secondary/20" />
                <circle cx="140" cy="165" r="10" className="fill-secondary/35" />
              </svg>
            </div>

            {/* Decorative background circle */}
            <div className="absolute right-0 top-1/2 -translate-y-1/2 w-96 h-96 bg-secondary-container/20 rounded-full blur-3xl pointer-events-none" />
          </div>
        </section>

        {/* A Multi-Disciplinary Approach */}
        <section className="px-6 mx-auto max-w-4xl text-center mb-16">
          <h2 className="text-2xl md:text-3xl font-bold text-[#163c39] mb-4">
            A Multi-Disciplinary Approach
          </h2>
          <p className="text-base md:text-lg text-secondary leading-relaxed mb-10 max-w-3xl mx-auto">
            Our team is composed of veteran electrophysiologists, clinical neurologists, and senior data scientists. We believe that technology should serve as a transparent extension of medical expertise, never a black box. This philosophy drives every algorithm we deploy and every interface we design.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4">
            <span className="px-6 py-2.5 rounded-full bg-surface-container border border-border-muted text-body-sm font-medium text-secondary shadow-sm">
              Clinician Led
            </span>
            <span className="px-6 py-2.5 rounded-full bg-surface-container border border-border-muted text-body-sm font-medium text-secondary shadow-sm">
              Open Architecture
            </span>
            <span className="px-6 py-2.5 rounded-full bg-surface-container border border-border-muted text-body-sm font-medium text-secondary shadow-sm">
              Continuous Audit
            </span>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
