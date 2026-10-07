import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { PricingPlanCards } from "@/components/pricing/PricingPlanCards";

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-surface font-sans text-on-surface flex flex-col">
      <Navbar />

      <main className="flex-1 mx-auto w-full max-w-6xl px-6 py-10 pt-[calc(72px+60px)] pb-32">
        <div className="mb-12 text-center">
          <h1 className="text-hero font-bold text-on-surface">Simple, Transparent Pricing</h1>
          <p className="mt-4 text-body-lg text-secondary max-w-2xl mx-auto">
            Give your clinical team the power of advanced neuro-cardiac analytics. No hidden fees.
          </p>
        </div>

        <PricingPlanCards />
      </main>

      <Footer />
    </div>
  );
}
