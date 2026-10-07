import Image from "next/image";
import Link from "next/link";
import { Activity, Shield, HeartPulse, ChevronRight, LayoutGrid, Network, FileBarChart } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { ECGBackground } from "@/components/ui/ECGBackground";

export default function HomePage() {
  return (
    <div className="relative min-h-screen overflow-x-hidden bg-surface font-sans text-on-surface">
      <ECGBackground />
      <div className="relative z-10">
      <Navbar />

      {/* Hero Section */}
      <section className="relative mx-auto flex max-w-7xl flex-col items-center gap-12 px-6 pb-24 pt-[calc(72px+48px)] md:flex-row md:pb-32 md:pt-[calc(72px+80px)]">
        <div className="flex-1 space-y-6">
          <div className="inline-flex items-center gap-2 rounded-full bg-[#e8f4f1] px-3 py-1 text-xs font-medium text-primary border border-primary/20">
            <Activity className="h-3.5 w-3.5" />
            Enterprise-Grade Cardiac Electrophysiology
          </div>
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold leading-tight text-[#163c39]">
            Transforming <span className="text-primary">Multi-Format ECG Signals</span> into Intelligent Clinical Decisions.
          </h1>
          <p className="text-secondary md:text-lg max-w-xl leading-relaxed">
            CardioNexus is an AI-powered platform that transforms multi-format ECG and Signal-Averaged ECG (SAECG) data into clinically actionable insights for advanced diagnostics.
          </p>
          <div className="flex flex-wrap items-center gap-4 pt-4">
            <Link href="/login">
              <Button className="h-12 px-6 text-base group">
                Explore the Platform <ChevronRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
              </Button>
            </Link>
            <Link href="/clinical-evidence">
              <Button variant="outline" className="h-12 px-6 text-base">
                Clinical Evidence
              </Button>
            </Link>
          </div>
        </div>
        <div className="flex-1 relative w-full h-[300px] md:h-[450px]">
          <div className="absolute inset-0 rounded-xl shadow-2xl border border-border-muted overflow-hidden">
            <Image
              src="/image1.jpeg"
              alt="CardioNexus ECG diagnostic dashboard"
              fill
              sizes="(min-width: 768px) 50vw, 100vw"
              className="object-cover object-left"
              priority
            />
          </div>
        </div>
      </section>

      {/* Pillars Section */}
      <section className="bg-surface-bright py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-[#163c39] mb-4">The Five Pillars of Clinical Precision</h2>
            <p className="text-secondary">Our modular architecture ensures every heartbeat is captured, processed, and analyzed with clinical-grade accuracy.</p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Top Row Cards */}
            <div className="md:col-span-1 bg-white p-8 rounded-2xl border border-border-muted shadow-sm hover:shadow-md transition-shadow">
              <div className="w-12 h-12 rounded-xl bg-[#e8f4f1] flex items-center justify-center text-primary mb-6">
                <LayoutGrid className="h-6 w-6" />
              </div>
              <h3 className="text-xl font-bold text-[#163c39] mb-3">Standardized ECG Ingestion</h3>
              <p className="text-sm text-secondary leading-relaxed">Universal compatibility with legacy DICOM, PDF, and high-fidelity RAW signal formats from any device manufacturer.</p>
            </div>
            
            <div className="md:col-span-2 bg-white p-8 rounded-2xl border border-border-muted shadow-sm hover:shadow-md transition-shadow flex flex-col sm:flex-row gap-8 items-center">
              <div className="flex-1">
                <div className="w-12 h-12 rounded-xl bg-[#e8f4f1] flex items-center justify-center text-primary mb-6">
                  <HeartPulse className="h-6 w-6" />
                </div>
                <h3 className="text-xl font-bold text-[#163c39] mb-3">Advanced Signal Processing</h3>
                <p className="text-sm text-secondary leading-relaxed">Proprietary filtering algorithms remove noise while preserving subtle microvolt fluctuation essential for SAECG analysis.</p>
              </div>
              <div className="relative w-full sm:w-64 h-40 rounded-xl border border-border-muted overflow-hidden">
                <Image
                  src="/image2.png"
                  alt="Clinical workstation displaying real-time ECG diagnostics"
                  fill
                  sizes="256px"
                  className="object-cover"
                />
              </div>
            </div>

            {/* Bottom Row Cards */}
            <div className="md:col-span-1 bg-[#163c39] text-white p-8 rounded-2xl shadow-lg relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-primary/20 rounded-full blur-3xl -mr-10 -mt-10"></div>
              <div className="w-12 h-12 rounded-xl bg-white/10 flex items-center justify-center text-white mb-6 backdrop-blur-sm">
                <Network className="h-6 w-6" />
              </div>
              <h3 className="text-xl font-bold mb-3">AI-Driven Analytics</h3>
              <p className="text-sm text-white/80 leading-relaxed">Deep learning models trained on millions of clinical cases provide real-time risk stratification for arrhythmias and sudden cardiac death predictors.</p>
            </div>

            <div className="md:col-span-1 bg-white p-8 rounded-2xl border border-border-muted shadow-sm hover:shadow-md transition-shadow">
              <div className="w-12 h-12 rounded-xl bg-[#e8f4f1] flex items-center justify-center text-primary mb-6">
                <FileBarChart className="h-6 w-6" />
              </div>
              <h3 className="text-xl font-bold text-[#163c39] mb-3">Explainable Clinical Reporting</h3>
              <p className="text-sm text-secondary leading-relaxed">Clear, visual reports that explain the &quot;why&quot; behind every AI inference, providing the clinical context physicians need.</p>
            </div>

            <div className="md:col-span-1 bg-white p-8 rounded-2xl border border-border-muted shadow-sm hover:shadow-md transition-shadow">
              <div className="w-12 h-12 rounded-xl bg-[#e8f4f1] flex items-center justify-center text-primary mb-6">
                <Shield className="h-6 w-6" />
              </div>
              <h3 className="text-xl font-bold text-[#163c39] mb-3">Secure Patient Data Management</h3>
              <p className="text-sm text-secondary leading-relaxed mb-6">AES-256 encrypted storage with granular access controls and full audit logging to meet the most stringent global healthcare standards.</p>
              <div className="flex flex-wrap gap-2">
                {/* <span className="inline-flex items-center gap-1 rounded bg-surface px-2 py-1 text-[10px] font-semibold text-secondary uppercase border border-border-muted"><ShieldCheck className="h-3 w-3" /> HIPAA COMPLIANT</span>
                <span className="inline-flex items-center gap-1 rounded bg-surface px-2 py-1 text-[10px] font-semibold text-secondary uppercase border border-border-muted"><CheckCircle2 className="h-3 w-3" /> FDA CLEARED</span>
                <span className="inline-flex items-center gap-1 rounded bg-surface px-2 py-1 text-[10px] font-semibold text-secondary uppercase border border-border-muted"><Lock className="h-3 w-3" /> SOC2-ISO</span> */}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Empowering Section */}
      <section className="py-24 px-6 max-w-7xl mx-auto flex flex-col md:flex-row items-center gap-16">
        <div className="flex-1 relative w-full">
           <div className="bg-white rounded-3xl p-4 shadow-xl border border-border-muted relative z-10 aspect-[4/5] flex flex-col">
              <div className="bg-surface-bright border border-border-muted flex-1 rounded-2xl overflow-hidden relative">
                <Image
                  src="/image3.jpeg"
                  alt="Doctor reviewing patient ECG data across dual monitors"
                  fill
                  sizes="(min-width: 768px) 40vw, 90vw"
                  className="object-cover"
                />
              </div>
           </div>
           
           {/* Floating Stats Card */}
           <div className="absolute -bottom-8 -right-8 md:-right-12 z-20 bg-white rounded-2xl shadow-2xl p-6 border border-border-muted flex items-center gap-8">
              <div>
                <div className="text-4xl font-bold text-[#163c39] flex items-baseline">99<span className="text-xl text-secondary ml-1">%</span></div>
                <div className="text-[10px] font-semibold text-secondary uppercase tracking-wider mt-1">ACCURACY</div>
              </div>
              <div className="w-px h-12 bg-border-muted"></div>
              <div>
                <div className="text-4xl font-bold text-[#163c39] flex items-baseline">15<span className="text-xl text-secondary ml-1">m</span></div>
                <div className="text-[10px] font-semibold text-secondary uppercase tracking-wider mt-1">TIME SAVED</div>
              </div>
           </div>
        </div>
        <div className="flex-1 mt-12 md:mt-0">
          <h2 className="text-3xl md:text-4xl font-bold text-[#163c39] mb-6">Empowering Clinical Decision Making</h2>
          <p className="text-secondary mb-10 text-lg leading-relaxed">CardioNexus isn&apos;t just a tool; it&apos;s a partner in diagnostic excellence, providing the support clinicians need for early detection and risk stratification.</p>
          
          <div className="space-y-8">
            <div className="flex gap-4">
              <div className="mt-1 w-10 h-10 rounded-full bg-[#e8f4f1] flex items-center justify-center text-primary shrink-0">
                <Activity className="h-5 w-5" />
              </div>
              <div>
                <h4 className="text-xl font-bold text-[#163c39] mb-2">Early Diagnosis</h4>
                <p className="text-secondary text-sm leading-relaxed">Identify subtle markers of cardiac dysfunction months before symptoms manifest through advanced SAECG profiling.</p>
              </div>
            </div>
            
            <div className="flex gap-4">
              <div className="mt-1 w-10 h-10 rounded-full bg-[#e8f4f1] flex items-center justify-center text-primary shrink-0">
                <Network className="h-5 w-5" />
              </div>
              <div>
                <h4 className="text-xl font-bold text-[#163c39] mb-2">Risk Stratification</h4>
                <p className="text-secondary text-sm leading-relaxed">Automated scoring systems that rank patient risk levels based on multi-parametric signal analysis.</p>
              </div>
            </div>
            
            <div className="flex gap-4">
              <div className="mt-1 w-10 h-10 rounded-full bg-[#e8f4f1] flex items-center justify-center text-primary shrink-0">
                <LayoutGrid className="h-5 w-5" />
              </div>
              <div>
                <h4 className="text-xl font-bold text-[#163c39] mb-2">Clinical Consensus</h4>
                <p className="text-secondary text-sm leading-relaxed">Shared dashboards and standardized reporting facilitate collaboration between cardiology teams and specialists.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Badges Bar */}
      <div className="border-y border-border-muted bg-white py-8">
        <div className="max-w-7xl mx-auto px-6 flex flex-wrap justify-center gap-8 md:gap-24 opacity-60">
           {/* <div className="flex items-center gap-2 text-sm font-bold text-[#163c39] tracking-widest"><ShieldCheck className="h-5 w-5" /> HIPAA COMPLIANT</div>
           <div className="flex items-center gap-2 text-sm font-bold text-[#163c39] tracking-widest"><CheckCircle2 className="h-5 w-5" /> FDA CLASS II</div>
           <div className="flex items-center gap-2 text-sm font-bold text-[#163c39] tracking-widest"><Lock className="h-5 w-5" /> AES-256 BIT SECURE</div>
           <div className="flex items-center gap-2 text-sm font-bold text-[#163c39] tracking-widest"><Shield className="h-5 w-5" /> GDPR READY</div> */}
        </div>
      </div>

      {/* Footer */}
      <Footer />
      </div>
    </div>
  );
}
