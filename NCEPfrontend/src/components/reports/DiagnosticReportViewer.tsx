import { Download, Activity, Settings2, ActivitySquare, CheckCircle2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";

export function DiagnosticReportViewer() {
  return (
    <div className="mx-auto max-w-5xl rounded-xl bg-surface-panel shadow-sm border border-border-muted overflow-hidden">
      {/* Top Header / Download Action */}
      <div className="flex items-center justify-end bg-surface px-8 py-4 border-b border-border-muted">
         <Button variant="outline" className="h-9 gap-2">
            <Download className="h-4 w-4" /> Download Report
         </Button>
      </div>

      <div className="px-8 pb-12 pt-8">
        {/* Report Header */}
        <div className="mb-6 flex flex-col justify-between md:flex-row md:items-end">
          <div>
            <h1 className="text-section-title font-bold text-primary mb-2">Diagnostic Report</h1>
            <div className="inline-flex rounded-full bg-surface-container-high px-3 py-1 text-[11px] font-semibold text-secondary">
              ID: 12-Lead Electrocardiogram (ECG)
            </div>
          </div>
          <div className="mt-6 md:mt-0 md:text-right">
            <div className="text-body-lg font-bold text-on-surface mb-1">John Doe</div>
            <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs text-secondary md:flex md:flex-col md:gap-y-1">
              <div className="flex justify-end gap-2"><span className="uppercase text-outline font-semibold text-[10px]">ID:</span> NCEP-8472-A3</div>
              <div className="flex justify-end gap-2"><span className="uppercase text-outline font-semibold text-[10px]">Age/Sex:</span> 38 / Male</div>
              <div className="flex justify-end gap-2"><span className="uppercase text-outline font-semibold text-[10px]">DOB:</span> Oct 12, 1985</div>
              <div className="flex justify-end gap-2"><span className="uppercase text-outline font-semibold text-[10px]">Date:</span> Oct 24, 2023</div>
            </div>
          </div>
        </div>

        <hr className="mb-8 border-t-2 border-primary" />

        {/* Acquisition Details */}
        <div className="mb-8">
          <h2 className="mb-4 flex items-center gap-2 text-body-lg font-bold text-on-surface">
            <ActivitySquare className="h-5 w-5 text-primary" /> Acquisition Details
          </h2>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
             <div className="rounded-lg border border-border-muted p-4">
                <div className="mb-1 text-[10px] font-bold uppercase tracking-wider text-outline">Date/Time</div>
                <div className="font-semibold text-on-surface text-sm">Oct 24, 2023 / 09:14 AM</div>
             </div>
             <div className="rounded-lg border border-border-muted p-4">
                <div className="mb-1 text-[10px] font-bold uppercase tracking-wider text-outline">Speed</div>
                <div className="font-semibold text-on-surface text-sm">25 mm/s</div>
             </div>
             <div className="rounded-lg border border-border-muted p-4">
                <div className="mb-1 text-[10px] font-bold uppercase tracking-wider text-outline">Calibration</div>
                <div className="font-semibold text-on-surface text-sm">10 mm/mV</div>
             </div>
             <div className="rounded-lg border border-border-muted p-4">
                <div className="mb-1 text-[10px] font-bold uppercase tracking-wider text-outline">Device ID</div>
                <div className="font-semibold text-on-surface text-sm">MAC-5500-01</div>
             </div>
          </div>
        </div>

        {/* Technical Parameters */}
        <div className="mb-10">
          <h2 className="mb-4 flex items-center gap-2 text-body-lg font-bold text-on-surface">
            <Settings2 className="h-5 w-5 text-primary" /> Technical Parameters
          </h2>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
             <div className="rounded-lg border border-border-muted p-4 bg-surface-container-lowest">
                <div className="mb-1 text-[10px] font-bold uppercase tracking-wider text-outline">Heart Rate</div>
                <div className="text-on-surface"><span className="text-3xl font-bold text-primary">72</span> <span className="text-xs font-medium text-secondary">bpm</span></div>
             </div>
             <div className="rounded-lg border border-border-muted p-4 bg-surface-container-lowest">
                <div className="mb-1 text-[10px] font-bold uppercase tracking-wider text-outline">PR Interval</div>
                <div className="text-on-surface"><span className="text-2xl font-bold">160</span> <span className="text-xs font-medium text-secondary">ms</span></div>
             </div>
             <div className="rounded-lg border border-border-muted p-4 bg-surface-container-lowest">
                <div className="mb-1 text-[10px] font-bold uppercase tracking-wider text-outline">QRS Duration</div>
                <div className="text-on-surface"><span className="text-2xl font-bold">92</span> <span className="text-xs font-medium text-secondary">ms</span></div>
             </div>
             <div className="rounded-lg border border-border-muted p-4 bg-surface-container-lowest">
                <div className="mb-1 text-[10px] font-bold uppercase tracking-wider text-outline">QT / QTC</div>
                <div className="text-on-surface"><span className="text-2xl font-bold">380 / 418</span> <span className="text-xs font-medium text-secondary">ms</span></div>
             </div>
          </div>
          <div className="mt-4 rounded-lg border border-border-muted p-4 flex items-center gap-8 bg-surface-container-lowest">
             <div className="text-[10px] font-bold uppercase tracking-wider text-outline">Electrical Axis</div>
             <div className="flex gap-6 text-sm font-semibold text-on-surface">
               <div><span className="text-secondary mr-1">P:</span> 54°</div>
               <div><span className="text-secondary mr-1">QRS:</span> 62°</div>
               <div><span className="text-secondary mr-1">T:</span> 48°</div>
             </div>
          </div>
        </div>

        {/* HRV Metrics */}
        <div className="mb-10">
          <h2 className="mb-4 text-center text-card-title font-bold text-primary">HRV Metrics</h2>
          <div className="overflow-hidden rounded-lg border border-primary/20">
             <table className="w-full text-left text-sm">
                <thead className="bg-primary text-on-primary">
                  <tr>
                    <th className="px-4 py-3 font-semibold">Metric</th>
                    <th className="px-4 py-3 font-semibold">Value</th>
                    <th className="px-4 py-3 font-semibold">Visualization</th>
                    <th className="px-4 py-3 font-semibold">Interpretation</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-muted text-on-surface">
                  <tr>
                    <td className="px-4 py-3 font-medium">Mean RR (ms)</td>
                    <td className="px-4 py-3">800.12</td>
                    <td className="px-4 py-3">
                       <div className="flex h-2 w-24 overflow-hidden rounded-full bg-surface-container-high">
                         <div className="w-1/3 bg-warning" />
                         <div className="w-1/3 bg-success" />
                         <div className="w-1/3 bg-critical" />
                       </div>
                    </td>
                    <td className="px-4 py-3 text-secondary">Indicates a healthy heart rate.</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-3 font-medium">RMSSD (ms)</td>
                    <td className="px-4 py-3">72.41</td>
                    <td className="px-4 py-3">
                       <div className="flex h-2 w-24 overflow-hidden rounded-full bg-surface-container-high">
                         <div className="w-1/4 bg-critical" />
                         <div className="w-1/4 bg-warning" />
                         <div className="w-1/4 bg-success" />
                       </div>
                    </td>
                    <td className="px-4 py-3 text-secondary">Strong vagal tone.</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-3 font-medium">SDNN (ms)</td>
                    <td className="px-4 py-3">64.48</td>
                    <td className="px-4 py-3">
                       <div className="flex h-2 w-24 overflow-hidden rounded-full bg-surface-container-high">
                         <div className="w-1/4 bg-warning" />
                         <div className="w-1/2 bg-success" />
                       </div>
                    </td>
                    <td className="px-4 py-3 text-secondary">Good balance.</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-3 font-medium">PNN50 (%)</td>
                    <td className="px-4 py-3">27.65</td>
                    <td className="px-4 py-3">
                       <div className="flex h-2 w-24 overflow-hidden rounded-full bg-surface-container-high">
                         <div className="w-1/3 bg-critical" />
                         <div className="w-1/3 bg-warning" />
                         <div className="w-1/3 bg-success" />
                       </div>
                    </td>
                    <td className="px-4 py-3 text-secondary">High adaptability and strong parasympathetic tone.</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-3 font-medium">Stress Score</td>
                    <td className="px-4 py-3">24.12</td>
                    <td className="px-4 py-3">
                       <div className="flex h-2 w-24 overflow-hidden rounded-full bg-surface-container-high">
                         <div className="w-1/4 bg-success" />
                         <div className="w-1/4 bg-warning" />
                         <div className="w-1/2 bg-critical" />
                       </div>
                    </td>
                    <td className="px-4 py-3 text-secondary">Healthy HRV.</td>
                  </tr>
                </tbody>
             </table>
          </div>
          <div className="mt-4 text-center text-sm font-semibold">
            Heart Rate Variability: <span className="text-success">Healthy HRV</span>
          </div>
        </div>

        {/* Reference Ranges */}
        <div className="mb-10">
          <h2 className="mb-4 text-center text-card-title font-bold text-primary">Reference Ranges</h2>
          <div className="overflow-hidden rounded-lg border border-primary/20">
             <table className="w-full text-left text-sm">
                <thead className="bg-primary text-on-primary">
                  <tr>
                    <th className="px-4 py-3 font-semibold">Metric</th>
                    <th className="px-4 py-3 font-semibold">Reference Range</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-muted text-secondary text-xs">
                  <tr>
                    <td className="px-4 py-2 font-medium text-on-surface">Mean RR (ms)</td>
                    <td className="px-4 py-2">600-1100 ms</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-2 font-medium text-on-surface">SDNN (ms)</td>
                    <td className="px-4 py-2">&gt;50 Normal, 20-50 Moderate, &lt;20 Low</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-2 font-medium text-on-surface">RMSSD (ms)</td>
                    <td className="px-4 py-2">&gt;40 Optimal, 15.7-40 Moderate, &lt;15.7 Low</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-2 font-medium text-on-surface">Residual Stress Score</td>
                    <td className="px-4 py-2">&lt;40 Normal Stress Response, 41-65 Mild Stress, 66-70 Moderate Stress, 71-85 Severe Stress, &gt;86 Extremely Severe Stress</td>
                  </tr>
                </tbody>
             </table>
          </div>
        </div>

        {/* Rhythm & Findings */}
        <div className="mb-6 grid gap-6 md:grid-cols-2">
           <div className="rounded-lg border border-border-muted p-5 bg-surface-container-lowest">
             <h3 className="mb-3 flex items-center gap-2 font-semibold text-primary">
               <Activity className="h-4 w-4" /> Rhythm
             </h3>
             <p className="text-sm text-on-surface">Sinus rhythm, no arrhythmia detected.</p>
           </div>
           <div className="rounded-lg border border-border-muted p-5 bg-surface-container-lowest">
             <h3 className="mb-3 flex items-center gap-2 font-semibold text-primary">
               <AlertCircle className="h-4 w-4" /> Findings
             </h3>
             <ul className="list-disc pl-4 text-sm text-on-surface space-y-1">
               <li>Normal ST segment, no T-wave abnormalities.</li>
               <li>No pathological Q waves.</li>
               <li>No evidence of hypertrophy or blocks.</li>
             </ul>
           </div>
        </div>

        {/* Impression & Comments */}
        <div className="mb-10 space-y-4">
           <div className="rounded-lg border border-primary/20 bg-primary/5 p-5">
             <h3 className="mb-2 flex items-center gap-2 font-semibold text-primary">
               <CheckCircle2 className="h-4 w-4" /> Impression
             </h3>
             <p className="text-sm text-on-surface">
               <strong>Normal sinus rhythm.</strong> Overall tracing is within normal limits for patient age and demographic.
             </p>
           </div>
           
           <div className="rounded-lg border border-border-muted bg-surface-container-low p-5">
             <div className="mb-1 text-[10px] font-bold uppercase tracking-wider text-outline">Clinical Comments</div>
             <p className="text-sm text-on-surface">Recommend clinical correlation. No immediate intervention required.</p>
           </div>
        </div>

        {/* Waveform Analysis */}
        <div className="mb-12">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-card-title font-bold text-on-surface">
              <Activity className="h-5 w-5" /> Waveform Analysis
            </h2>
            <div className="text-[10px] font-semibold uppercase text-secondary flex gap-4">
              <span>Speed: 25 mm/s</span>
              <span>Limb: 10 mm/mV</span>
            </div>
          </div>
          
          <div className="relative h-48 w-full overflow-hidden rounded-lg border border-border-muted bg-surface-bright">
            {/* Grid pattern */}
            <div className="absolute inset-0 opacity-[0.15]" 
                 style={{ backgroundImage: 'linear-gradient(to right, #005c55 1px, transparent 1px), linear-gradient(to bottom, #005c55 1px, transparent 1px)', backgroundSize: '10px 10px' }} />
            <div className="absolute inset-0 opacity-[0.3]" 
                 style={{ backgroundImage: 'linear-gradient(to right, #005c55 1px, transparent 1px), linear-gradient(to bottom, #005c55 1px, transparent 1px)', backgroundSize: '50px 50px' }} />
            
            {/* SVG ECG Waveform Mock */}
            <div className="absolute inset-0 flex items-center px-4">
               <svg viewBox="0 0 1000 100" className="w-full h-full stroke-primary fill-none overflow-visible" preserveAspectRatio="none">
                 <path d="M0,50 L50,50 L60,40 L70,50 L100,50 L110,60 L120,0 L130,100 L140,50 L160,50 L180,35 L200,50 L300,50 L310,40 L320,50 L350,50 L360,60 L370,0 L380,100 L390,50 L410,50 L430,35 L450,50 L550,50 L560,40 L570,50 L600,50 L610,60 L620,0 L630,100 L640,50 L660,50 L680,35 L700,50 L800,50 L810,40 L820,50 L850,50 L860,60 L870,0 L880,100 L890,50 L910,50 L930,35 L950,50 L1000,50" strokeWidth="2" strokeLinejoin="round" />
               </svg>
            </div>
            
            <div className="absolute left-2 top-2 text-[10px] font-bold text-secondary">Lead II</div>
          </div>
        </div>

        {/* Footer Signature */}
        <div className="flex flex-col md:flex-row md:items-end justify-between border-t border-border-muted pt-8">
           <div>
             <div className="text-[10px] uppercase text-outline mb-1">Electronically Signed By</div>
             <div className="text-lg font-serif italic text-primary mb-1">Dr. Sarah Jenkins, MD, FACC</div>
             <div className="text-xs text-secondary">Timestamp: Oct 24, 2023, 09:14 AM EST</div>
           </div>
           
           <div className="mt-6 md:mt-0 flex gap-4">
              {/* <div className="flex items-center gap-2 rounded bg-surface-container-low px-3 py-1.5 text-[10px] font-bold uppercase text-primary">
                 <CheckCircle2 className="h-3 w-3" /> HIPAA Compliant
              </div>
              <div className="flex items-center gap-2 rounded bg-surface-container-low px-3 py-1.5 text-[10px] font-bold uppercase text-primary">
                 <CheckCircle2 className="h-3 w-3" /> FDA Cleared
              </div> */}
           </div>
        </div>

      </div>
    </div>
  );
}
