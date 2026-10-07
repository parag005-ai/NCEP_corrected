import { Check } from "lucide-react";
import { Button } from "@/components/ui/Button";

const plans = [
  {
    name: "Starter",
    description: "Small practices & clinics",
    price: "₹499",
    features: ["50,000 Tokens/mo", "Basic AI Diagnostic Assist", "Standard support"],
    buttonLabel: "Get Started",
    buttonVariant: "outline" as const,
    highlight: false,
  },
  {
    name: "Clinical",
    description: "Standard hospitals & labs",
    price: "₹1,299",
    features: ["500,000 Tokens/mo", "Advanced Diagnostic Assist", "Multi-User Collab", "Standard API Access"],
    buttonLabel: "Get Started",
    buttonVariant: "primary" as const,
    highlight: true,
  },
  {
    name: "Institutional",
    description: "Large research centers",
    price: "₹4,999",
    features: ["Unlimited Tokens", "Full Super Admin Controls", "Priority Cloud Compute", "On-site Implementation"],
    buttonLabel: "Contact Sales",
    buttonVariant: "outline" as const,
    highlight: false,
  },
];

export function PricingPlanCards() {
  return (
    <div className="mx-auto mt-16 max-w-5xl">
      <div className="mb-10 text-center">
        <h2 className="text-section-title font-semibold text-on-surface">Scalable Diagnostic Power</h2>
        <p className="mt-2 text-body-sm text-secondary">Choose the plan that fits your facility&apos;s patient volume and research requirements.</p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        {plans.map((plan) => (
          <div
            key={plan.name}
            className={`relative flex flex-col rounded-2xl bg-surface-panel p-8 ${
              plan.highlight
                ? "border-2 border-primary shadow-lg ring-4 ring-primary/5"
                : "border border-border-muted shadow-sm"
            }`}
          >
            {plan.highlight && (
              <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 rounded-full bg-primary px-4 py-1.5 text-[10px] font-bold uppercase tracking-wider text-white">
                MOST POPULAR
              </div>
            )}
            
            <div className="mb-2 text-body-lg font-bold text-on-surface">{plan.name}</div>
            <p className="mb-6 text-caption text-secondary">{plan.description}</p>
            
            <div className="mb-8 flex items-baseline text-on-surface">
              <span className="text-hero font-bold">{plan.price}</span>
              <span className="ml-1 text-body-sm font-medium text-secondary">/mo</span>
            </div>

            <ul className="mb-8 flex flex-1 flex-col gap-4">
              {plan.features.map((feature, i) => (
                <li key={i} className="flex items-center gap-3 text-body-sm text-on-surface-variant">
                  <div className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 text-primary">
                    <Check className="h-3 w-3 stroke-[3]" />
                  </div>
                  {feature}
                </li>
              ))}
            </ul>

            <Button variant={plan.buttonVariant} className="w-full">
              {plan.buttonLabel}
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
