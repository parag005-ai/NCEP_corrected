import { Skeleton } from "@/components/ui/Skeleton";
import { Logo } from "@/components/ui/Logo";

export default function ReportLoading() {
  return (
    <div className="min-h-screen bg-[#eef1f0] flex flex-col">
      {/* Skeleton Navbar matching ClientPage */}
      <header className="bg-white border-b border-[#e0e3e1] sticky top-0 z-30">
        <div className="max-w-[1100px] mx-auto px-5 h-12 flex items-center justify-between gap-4">
          <div className="flex items-center shrink-0">
             <Logo className="scale-[0.8] origin-left" />
          </div>
          <div className="flex gap-2">
            <Skeleton className="h-8 w-24 rounded" />
            <Skeleton className="h-8 w-8 rounded-full" />
          </div>
        </div>
      </header>

      {/* Skeleton Main Content */}
      <main className="flex-1 max-w-[1100px] mx-auto w-full px-5 py-6 space-y-4">
        {/* Back button placeholder */}
        <div>
           <Skeleton className="h-4 w-12 rounded" />
        </div>
        <div className="bg-white rounded-xl border border-[#e0e3e1] px-6 py-4 space-y-5">
           <div>
             <Skeleton className="h-8 w-64 rounded mb-2" />
             <Skeleton className="h-4 w-48 rounded" />
           </div>
           <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-[#e0e3e1]">
              <Skeleton className="h-8 w-full rounded" />
              <Skeleton className="h-8 w-full rounded" />
              <Skeleton className="h-8 w-full rounded" />
              <Skeleton className="h-8 w-full rounded" />
           </div>
        </div>
      </main>
    </div>
  );
}
