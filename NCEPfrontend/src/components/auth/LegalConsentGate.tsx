"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import {
  acceptLegalAgreements,
  getRedirectPath,
  getServiceErrorMessage,
  hasAcceptedLegalAgreements,
} from "@/services";
import { useAuth } from "@/providers/AuthProvider";

type DocumentKind = "terms" | "privacy";

const documents: Record<DocumentKind, { title: string; sections: Array<[string, string]> }> = {
  terms: {
    title: "Terms & Conditions",
    sections: [
      ["1. Acceptance", "By using CardioNexus AI, you agree to these Terms and all applicable healthcare, privacy, and professional obligations."],
      ["2. Clinical use", "CardioNexus AI supports qualified healthcare professionals. It does not replace independent clinical judgment, diagnosis, emergency care, or applicable standards of care."],
      ["3. Account security", "Keep your credentials confidential and notify your organisation promptly about suspected unauthorised access. You are responsible for activity performed through your account."],
      ["4. Acceptable use", "Use the platform only for authorised care, administrative, and patient-access purposes. Do not attempt to bypass access controls, interfere with the service, or upload unlawful or harmful content."],
      ["5. Service changes", "We may update the platform and these Terms when required. Material changes will be communicated through the service or your organisation where appropriate."],
    ],
  },
  privacy: {
    title: "Privacy Policy",
    sections: [
      ["1. Information we process", "We process account details, clinical information, ECG records, reports, and technical activity data needed to operate CardioNexus AI and provide authorised care workflows."],
      ["2. How information is used", "Information is used to provide the service, maintain security, support clinical workflows, meet legal obligations, and improve system reliability where permitted."],
      ["3. Access and sharing", "Access is limited to authorised users and organisations according to assigned permissions. Information is shared only when authorised, required for service delivery, or required by law."],
      ["4. Security and retention", "We use reasonable safeguards to protect information and retain it according to applicable law, organisational policy, and the purpose for which it was collected."],
      ["5. Your choices", "Contact your healthcare organisation or platform administrator to request access, correction, or other privacy assistance available under applicable law."],
    ],
  },
};

function LegalDocument({ kind, onClose }: { kind: DocumentKind; onClose: () => void }) {
  const document = documents[kind];
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 p-4" role="dialog" aria-modal="true" aria-labelledby={`${kind}-title`}>
      <div className="flex max-h-[85vh] w-full max-w-2xl flex-col rounded-2xl bg-surface-container-lowest shadow-2xl">
        <div className="flex items-center justify-between border-b border-border-muted px-6 py-4">
          <h2 id={`${kind}-title`} className="text-card-title text-on-surface">{document.title}</h2>
          <button type="button" onClick={onClose} aria-label={`Close ${document.title}`} className="rounded-lg p-2 text-secondary hover:bg-secondary-container/50 hover:text-primary">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="overflow-y-auto px-6 py-5 text-body-sm leading-6 text-on-surface-variant">
          <p className="mb-5">Last updated: July 27, 2026</p>
          {document.sections.map(([heading, content]) => (
            <section key={heading} className="mb-5">
              <h3 className="mb-1 font-semibold text-on-surface">{heading}</h3>
              <p>{content}</p>
            </section>
          ))}
        </div>
        <div className="border-t border-border-muted px-6 py-4 text-right">
          <Button onClick={onClose}>Close</Button>
        </div>
      </div>
    </div>
  );
}

export function LegalConsentGate() {
  const { session, loading } = useAuth();
  const router = useRouter();
  const [checked, setChecked] = useState({ terms: false, privacy: false });
  const [required, setRequired] = useState(false);
  const [document, setDocument] = useState<DocumentKind | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const checkConsent = async () => {
      if (!loading && session) {
        try {
          const accepted = await hasAcceptedLegalAgreements();
          if (active) setRequired(!accepted);
        } catch (error) {
          if (active) {
            console.error("Error checking legal consent:", error);
            setError(getServiceErrorMessage(error));
            setRequired(true);
          }
        }
      } else if (!loading && active) {
        setRequired(false);
      }
    };
    void checkConsent();
    return () => {
      active = false;
    };
  }, [loading, session]);

  if (!required || !session) return null;

  const canContinue = checked.terms && checked.privacy;
  return (
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-slate-950/70 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="legal-consent-title">
        <div className="my-auto w-full max-w-xl rounded-2xl border border-border-muted bg-surface-container-lowest p-7 shadow-2xl sm:p-9">
          <h1 id="legal-consent-title" className="text-headline-lg text-on-surface">Welcome to CardioNexus AI</h1>
          <p className="mt-3 text-body-lg text-secondary">Before accessing your workspace, please review and accept our legal agreements.</p>
          {error && <p className="mt-3 text-body-sm text-error" role="alert">{error}</p>}
          <fieldset className="mt-7 space-y-4">
            <legend className="sr-only">Required legal agreements</legend>
            <div className="flex items-start gap-3 rounded-xl border border-border-muted p-4 hover:bg-surface-container-low">
              <input id="terms-consent" aria-label="I have read and agree to the Terms & Conditions" type="checkbox" checked={checked.terms} onChange={(event) => setChecked((current) => ({ ...current, terms: event.target.checked }))} className="mt-1 h-4 w-4 rounded border-outline text-primary focus:ring-primary" />
              <label htmlFor="terms-consent" className="sr-only">I have read and agree to the Terms &amp; Conditions</label>
              <span className="text-body-sm text-on-surface-variant">I have read and agree to the <button type="button" onClick={() => setDocument("terms")} className="font-semibold text-primary underline underline-offset-2">Terms &amp; Conditions</button>.</span>
            </div>
            <div className="flex items-start gap-3 rounded-xl border border-border-muted p-4 hover:bg-surface-container-low">
              <input id="privacy-consent" aria-label="I have read and agree to the Privacy Policy" type="checkbox" checked={checked.privacy} onChange={(event) => setChecked((current) => ({ ...current, privacy: event.target.checked }))} className="mt-1 h-4 w-4 rounded border-outline text-primary focus:ring-primary" />
              <label htmlFor="privacy-consent" className="sr-only">I have read and agree to the Privacy Policy</label>
              <span className="text-body-sm text-on-surface-variant">I have read and agree to the <button type="button" onClick={() => setDocument("privacy")} className="font-semibold text-primary underline underline-offset-2">Privacy Policy</button>.</span>
            </div>
          </fieldset>
          <Button
            className="mt-7 w-full"
            disabled={!canContinue}
            onClick={async () => {
              try {
                await acceptLegalAgreements();
                setRequired(false);
                router.replace(getRedirectPath(session.role));
              } catch (error) {
                setError(getServiceErrorMessage(error));
              }
            }}
          >
            Continue to CardioNexus AI
          </Button>
        </div>
      </div>
      {document && <LegalDocument kind={document} onClose={() => setDocument(null)} />}
    </>
  );
}
