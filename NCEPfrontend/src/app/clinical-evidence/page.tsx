import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { Button } from "@/components/ui/Button";
import { 
  Download, 
  Activity, 
  Database, 
  Building2,
  ArrowRight,
  MonitorCheck,
  CheckCircle2
} from "lucide-react";

export default function ClinicalEvidencePage() {
  return (
    <div className="flex min-h-screen flex-col bg-[#f8f9fa] font-sans">
      <Navbar />
      
      <main className="flex-1 pt-[calc(72px+64px)] pb-24">
        {/* HERO SECTION */}
        <section className="px-6 mx-auto max-w-5xl text-center mb-24">
          <div className="inline-flex items-center rounded-full bg-[#e6f4f1] px-4 py-1.5 text-xs font-bold tracking-widest text-primary mb-8 border border-[#cce8e4]">
            ISO 13485 CERTIFIED PLATFORM
          </div>
          <h1 className="text-4xl md:text-5xl lg:text-[56px] font-bold text-[#163c39] mb-6 leading-tight">
            Clinical Validation & Scientific Rigor
          </h1>
          <p className="text-lg md:text-xl text-secondary max-w-3xl mx-auto mb-10 leading-relaxed">
            CardioNexus AI is built upon a foundation of extensive clinical trials and peer-reviewed research. We maintain the highest standards of diagnostic accuracy through continuous validation against gold-standard ground truth.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button className="h-12 px-6 rounded-lg font-semibold shadow-sm flex items-center gap-2 w-full sm:w-auto">
              <Download className="h-4 w-4" />
              Download Technical Brief
            </Button>
            <Button variant="outline" className="h-12 px-6 rounded-lg font-semibold w-full sm:w-auto border-border-muted hover:bg-surface text-[#163c39]">
              Request Trial Access
            </Button>
          </div>
        </section>

        {/* STATS SECTION */}
        <section className="px-6 mx-auto max-w-6xl mb-32">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Stat 1 */}
            <div className="bg-white rounded-2xl p-8 flex flex-col items-center text-center shadow-[0_4px_24px_rgba(0,0,0,0.02)] border border-black/5">
              <div className="h-14 w-14 rounded-full bg-[#e6f4f1] flex items-center justify-center mb-6">
                <Activity className="h-6 w-6 text-primary" />
              </div>
              <div className="text-4xl font-bold text-[#163c39] mb-3">99.8%</div>
              <div className="text-sm font-semibold text-[#163c39] mb-3">Signal Accuracy</div>
              <p className="text-xs text-secondary leading-relaxed">Validated against MIT-BIH and AHA clinical arrhythmia databases.</p>
            </div>
            
            {/* Stat 2 */}
            <div className="bg-white rounded-2xl p-8 flex flex-col items-center text-center shadow-[0_4px_24px_rgba(0,0,0,0.02)] border border-black/5">
              <div className="h-14 w-14 rounded-full bg-[#e6f4f1] flex items-center justify-center mb-6">
                <Database className="h-6 w-6 text-primary" />
              </div>
              <div className="text-4xl font-bold text-[#163c39] mb-3">1M+</div>
              <div className="text-sm font-semibold text-[#163c39] mb-3">Waveforms Analyzed</div>
              <p className="text-xs text-secondary leading-relaxed">Training data comprised of diverse patient demographics and pathologies.</p>
            </div>

            {/* Stat 3 */}
            <div className="bg-white rounded-2xl p-8 flex flex-col items-center text-center shadow-[0_4px_24px_rgba(0,0,0,0.02)] border border-black/5">
              <div className="h-14 w-14 rounded-full bg-[#e6f4f1] flex items-center justify-center mb-6">
                <Building2 className="h-6 w-6 text-primary" />
              </div>
              <div className="text-4xl font-bold text-[#163c39] mb-3">40+</div>
              <div className="text-sm font-semibold text-[#163c39] mb-3">Institutional Partners</div>
              <p className="text-xs text-secondary leading-relaxed">Collaborative data sharing and validation with leading medical centers.</p>
            </div>
          </div>
        </section>

        {/* RESEARCH LIBRARY */}
        <section className="px-6 mx-auto max-w-6xl mb-32">
          <div className="flex flex-col md:flex-row md:items-end justify-between mb-10 gap-6">
            <div className="max-w-xl">
              <h2 className="text-2xl font-bold text-[#163c39] mb-3">Research Library</h2>
              <p className="text-sm text-secondary leading-relaxed">
                Explore our latest publications and clinical whitepapers defining the future of electrophysiology.
              </p>
            </div>
            <div className="flex items-center gap-1 bg-black/5 p-1 rounded-lg self-start md:self-auto text-xs font-medium text-secondary">
              <button className="px-4 py-1.5 bg-white rounded-md shadow-sm text-primary">All</button>
              <button className="px-4 py-1.5 hover:text-primary transition-colors">Clinical Trials</button>
              <button className="px-4 py-1.5 hover:text-primary transition-colors">Whitepapers</button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Card 1 */}
            <div className="bg-white rounded-2xl p-8 flex flex-col shadow-[0_4px_24px_rgba(0,0,0,0.02)] border border-black/5">
              <div className="inline-block bg-[#f1f3f5] rounded text-[10px] font-bold uppercase tracking-wider text-secondary px-2 py-1 mb-6 self-start">
                JOURNAL OF CARDIOLOGY | <span className="font-medium">June 2023</span>
              </div>
              <h3 className="text-lg font-bold text-[#163c39] mb-4 leading-snug">Nexus Core: Accuracy in Arrhythmia Detection</h3>
              <p className="text-xs text-secondary leading-relaxed flex-1 mb-8">
                A multi-center double-blind study evaluating the sensitivity and specificity of the Nexus Core engine across 15,000 unique patient encounters.
              </p>
              <a href="#" className="inline-flex items-center gap-2 text-xs font-bold text-primary hover:underline">
                Read Full Publication <ArrowRight className="h-3 w-3" />
              </a>
            </div>

            {/* Card 2 */}
            <div className="bg-white rounded-2xl p-8 flex flex-col shadow-[0_4px_24px_rgba(0,0,0,0.02)] border border-black/5">
              <div className="inline-block bg-[#f1f3f5] rounded text-[10px] font-bold uppercase tracking-wider text-secondary px-2 py-1 mb-6 self-start">
                INTERNAL REPORT | <span className="font-medium">Nov 2023</span>
              </div>
              <h3 className="text-lg font-bold text-[#163c39] mb-4 leading-snug">Real-time Neuro-Cardiac Predictive Analysis</h3>
              <p className="text-xs text-secondary leading-relaxed flex-1 mb-8">
                Detailing the correlation between autonomic nervous system indicators and acute cardiac events using proprietary AI modeling.
              </p>
              <a href="#" className="inline-flex items-center gap-2 text-xs font-bold text-primary hover:underline">
                View Methodology <ArrowRight className="h-3 w-3" />
              </a>
            </div>

            {/* Card 3 */}
            <div className="bg-white rounded-2xl p-8 flex flex-col shadow-[0_4px_24px_rgba(0,0,0,0.02)] border border-black/5">
              <div className="inline-block bg-[#f1f3f5] rounded text-[10px] font-bold uppercase tracking-wider text-secondary px-2 py-1 mb-6 self-start">
                WHITE PAPER | <span className="font-medium">Jan 2024</span>
              </div>
              <h3 className="text-lg font-bold text-[#163c39] mb-4 leading-snug">The Future of AI in Electrophysiology</h3>
              <p className="text-xs text-secondary leading-relaxed flex-1 mb-8">
                An industry outlook on the integration of generative diagnostic tools in clinical EP labs and bedside monitoring systems.
              </p>
              <a href="#" className="inline-flex items-center gap-2 text-xs font-bold text-primary hover:underline">
                Download PDF <Download className="h-3 w-3" />
              </a>
            </div>
          </div>
        </section>
      </main>

      {/* TECHNICAL METHODOLOGY (Full Width Background) */}
      <section className="bg-white py-24 border-y border-black/5">
        <div className="px-6 mx-auto max-w-6xl">
          <div className="flex flex-col lg:flex-row items-center gap-16">
            {/* Left Image Side */}
            <div className="w-full lg:w-1/2">
              <div className="bg-surface rounded-2xl p-4 shadow-xl border border-black/5 mb-4">
                {/* Abstract UI representation since we don't have the exact image */}
                <div className="aspect-[4/3] bg-white rounded-lg border border-border-muted flex flex-col overflow-hidden">
                  <div className="h-8 border-b border-border-muted bg-[#f8f9fa] flex items-center px-4 gap-2">
                     <div className="w-2.5 h-2.5 rounded-full bg-red-400"></div>
                     <div className="w-2.5 h-2.5 rounded-full bg-yellow-400"></div>
                     <div className="w-2.5 h-2.5 rounded-full bg-green-400"></div>
                  </div>
                  <div className="flex-1 p-6 flex flex-col gap-4 bg-slate-50">
                    <div className="w-1/3 h-4 bg-slate-200 rounded"></div>
                    <div className="flex-1 flex gap-4">
                       <div className="w-1/4 h-full bg-white border border-slate-200 rounded flex flex-col gap-2 p-2">
                         <div className="w-full h-2 bg-slate-100 rounded"></div>
                         <div className="w-3/4 h-2 bg-slate-100 rounded"></div>
                       </div>
                       <div className="w-3/4 h-full bg-white border border-slate-200 rounded relative overflow-hidden flex items-center">
                          {/* Fake ECG Line */}
                          <svg width="100%" height="60%" preserveAspectRatio="none" viewBox="0 0 100 100" className="opacity-20 text-primary">
                             <path d="M0,50 L20,50 L25,30 L35,80 L45,20 L55,90 L65,40 L70,50 L100,50" stroke="currentColor" strokeWidth="2" fill="none" vectorEffect="non-scaling-stroke" />
                          </svg>
                       </div>
                    </div>
                  </div>
                </div>
              </div>
              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-3 bg-surface p-4 rounded-xl border border-black/5 text-sm font-semibold text-[#163c39] shadow-sm">
                  <CheckCircle2 className="h-5 w-5 text-primary" /> Ground-Truth Verified Dataset
                </div>
                <div className="flex items-center gap-3 bg-surface p-4 rounded-xl border border-black/5 text-sm font-semibold text-[#163c39] shadow-sm">
                  <MonitorCheck className="h-5 w-5 text-primary" /> Real-time Morphological Analysis
                </div>
              </div>
            </div>

            {/* Right Text Side */}
            <div className="w-full lg:w-1/2">
              <h2 className="text-2xl font-bold text-[#163c39] mb-10">Technical Methodology</h2>
              
              <div className="space-y-8">
                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-10 h-10 rounded-full border-2 border-primary/20 text-primary flex items-center justify-center font-bold text-sm bg-primary/5">
                    01
                  </div>
                  <div>
                    <h4 className="text-base font-bold text-[#163c39] mb-2">Advanced Denoising</h4>
                    <p className="text-sm text-secondary leading-relaxed">
                      Proprietary Fourier-transform algorithms that isolate cardiac signals from electrical interference and muscular artifacts with zero data loss.
                    </p>
                  </div>
                </div>

                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-10 h-10 rounded-full border-2 border-primary/20 text-primary flex items-center justify-center font-bold text-sm bg-primary/5">
                    02
                  </div>
                  <div>
                    <h4 className="text-base font-bold text-[#163c39] mb-2">Morphological Analysis</h4>
                    <p className="text-sm text-secondary leading-relaxed">
                      Deep learning architectures specifically tuned for P-wave, QRS-complex, and T-wave segmentation to detect subtle ischemic changes.
                    </p>
                  </div>
                </div>

                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-10 h-10 rounded-full border-2 border-primary/20 text-primary flex items-center justify-center font-bold text-sm bg-primary/5">
                    03
                  </div>
                  <div>
                    <h4 className="text-base font-bold text-[#163c39] mb-2">Ground Truth Calibration</h4>
                    <p className="text-sm text-secondary leading-relaxed">
                      Iterative model refinement using high-fidelity invasive EP study recordings as the definitive reference point for all AI labeling.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>



      {/* CTA SECTION */}
      <section className="px-6 mx-auto w-full max-w-6xl py-24">
        <div className="bg-[#0b3c37] rounded-3xl p-12 md:p-16 text-center text-white relative overflow-hidden shadow-2xl">
          {/* Subtle background pattern */}
          <div className="absolute inset-0 opacity-10">
             <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
               <defs>
                 <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                   <path d="M 40 0 L 0 0 0 40" fill="none" stroke="currentColor" strokeWidth="1"/>
                 </pattern>
               </defs>
               <rect width="100%" height="100%" fill="url(#grid)" />
             </svg>
          </div>
          
          <div className="relative z-10 max-w-2xl mx-auto flex flex-col items-center">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">Ready for Precise Diagnostics?</h2>
            <p className="text-white/80 text-sm md:text-base mb-10 leading-relaxed max-w-md">
              Access our full scientific dossier or schedule a deep-dive methodology briefing with our clinical science team.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 w-full justify-center">
              <Button className="bg-white text-[#0b3c37] hover:bg-white/90 h-12 px-6 rounded-lg font-semibold flex items-center justify-center gap-2 w-full sm:w-auto shadow-xl">
                <Download className="h-4 w-4" /> Download Full Clinical Whitepaper
              </Button>
              <Button variant="outline" className="h-12 px-6 rounded-lg font-semibold border-white/20 text-white hover:bg-white/10 w-full sm:w-auto">
                Request Methodology Briefing
              </Button>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
