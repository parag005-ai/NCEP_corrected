import { Download, Filter } from "lucide-react";
import { Button } from "@/components/ui/Button";

const sessions = [
  { id: "#DIAG-88210", facility: "Mayo Clinic Neurology", specialty: "HRV SCAN", tokens: "1,240", cost: "₹1.45", date: "Dec 17, 2024" },
  { id: "#DIAG-88121", facility: "St. Jude Cardiac Unit", specialty: "ECG ANALYSIS", tokens: "950", cost: "₹0.95", date: "Dec 16, 2024" },
  { id: "#DIAG-77643", facility: "Johns Hopkins Res.", specialty: "WAVEFRONT", tokens: "3,400", cost: "₹4.15", date: "Dec 15, 2024" },
];

export function SessionHistoryTable() {
  return (
    <div className="mt-16 w-full">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h3 className="text-card-title font-semibold text-on-surface">Session History</h3>
          <p className="text-body-sm text-secondary">Detailed token breakdown by individual diagnostic sessions.</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" className="h-9 px-4 text-xs font-medium">
            <Download className="mr-2 h-3.5 w-3.5" /> Export CSV
          </Button>
          <Button variant="outline" className="h-9 px-4 text-xs font-medium">
            <Filter className="mr-2 h-3.5 w-3.5" /> Filter
          </Button>
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-border-muted bg-surface-panel shadow-sm">
        <table className="w-full text-left text-body-sm">
          <thead className="bg-surface-container-low text-[10px] font-semibold uppercase tracking-wider text-secondary">
            <tr>
              <th className="px-6 py-4">SESSION ID</th>
              <th className="px-6 py-4">FACILITY</th>
              <th className="px-6 py-4">SPECIALTY</th>
              <th className="px-6 py-4">TOKENS USED</th>
              <th className="px-6 py-4">COST (₹)</th>
              <th className="px-6 py-4">DATE</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-muted">
            {sessions.map((row) => (
              <tr key={row.id} className="hover:bg-surface-container-low/50">
                <td className="px-6 py-4 font-medium text-on-surface">{row.id}</td>
                <td className="px-6 py-4 text-on-surface-variant">{row.facility}</td>
                <td className="px-6 py-4">
                  <span className={`inline-flex items-center rounded bg-opacity-20 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide
                    ${row.specialty === 'HRV SCAN' ? 'bg-primary/20 text-primary' : 
                      row.specialty === 'ECG ANALYSIS' ? 'bg-medical-cyan/20 text-medical-cyan' : 
                      'bg-warning/20 text-warning'}`}>
                    {row.specialty}
                  </span>
                </td>
                <td className="px-6 py-4 text-on-surface-variant">{row.tokens}</td>
                <td className="px-6 py-4 font-medium text-on-surface">{row.cost}</td>
                <td className="px-6 py-4 text-on-surface-variant">{row.date}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="border-t border-border-muted p-4 text-center">
          <button className="text-body-sm font-semibold text-primary hover:underline">
            View All 156 Sessions
          </button>
        </div>
      </div>
    </div>
  );
}
