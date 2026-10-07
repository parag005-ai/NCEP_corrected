import { BookOpen, ChevronDown, Mail, Phone, Send, Settings2, Stethoscope, UsersRound } from "lucide-react";

import { Footer } from "@/components/layout/Footer";
import { Navbar } from "@/components/layout/Navbar";
import { Button } from "@/components/ui/Button";

const supportChannels = [
  {
    title: "Technical Support",
    description: "Hardware calibration, software integration, and system performance inquiries.",
    phone: "+1 (800) 555-0192",
    email: "tech.ops@ncep.med",
    icon: Settings2,
  },
  {
    title: "Clinical Inquiries",
    description: "Guidance on diagnostic interpretation and advanced electrophysiology features.",
    phone: "+1 (800) 555-0145",
    email: "clinical@ncep.med",
    icon: Stethoscope,
  },
  {
    title: "Account Management",
    description: "Subscription billing, provider licensing, and institutional access control.",
    phone: "+1 (800) 555-0177",
    email: "billing@ncep.med",
    icon: UsersRound,
  },
];

const faqs = [
  "How do I export raw ECG telemetry data?",
  "Is NCEP HIPAA and GDPR compliant?",
  "Can I integrate NCEP with Epic or Cerner?",
  "What is the downtime protocol for maintenance?",
];

export default function SupportPage() {
  return (
    <div className="flex min-h-screen flex-col bg-[#f8faf9] font-sans text-[#181c1c]">
      <Navbar />

      <main className="mx-auto w-full max-w-6xl flex-1 px-6 pb-24 pt-[calc(72px+64px)]">
        <section className="mx-auto max-w-3xl text-center">
          <h1 className="text-4xl font-bold tracking-tight text-[#181c1c] sm:text-5xl">Support Center</h1>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-relaxed text-secondary sm:text-lg">
            How can we help you today? Access our dedicated specialized support channels or find quick answers in our clinical documentation.
          </p>
        </section>

        <section className="mt-16 grid gap-6 md:grid-cols-3">
          {supportChannels.map(({ title, description, phone, email, icon: Icon }) => (
            <article key={title} className="rounded-xl border border-border-muted bg-white p-8 shadow-[0_8px_24px_rgba(20,60,55,0.04)]">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-[#dff1ee] text-primary">
                <Icon className="h-6 w-6" />
              </div>
              <h2 className="mt-6 text-xl font-semibold text-[#181c1c]">{title}</h2>
              <p className="mt-3 min-h-20 text-sm leading-relaxed text-secondary">{description}</p>
              <div className="mt-7 space-y-3 text-sm font-medium text-primary">
                <a href={`tel:${phone.replace(/[^+\d]/g, "")}`} className="flex items-center gap-3 hover:underline">
                  <Phone className="h-4 w-4" /> {phone}
                </a>
                <a href={`mailto:${email}`} className="flex items-center gap-3 hover:underline">
                  <Mail className="h-4 w-4" /> {email}
                </a>
              </div>
            </article>
          ))}
        </section>

        <section className="mt-20 grid gap-12 lg:grid-cols-[1.35fr_0.95fr] lg:items-start">
          <form action="mailto:info@22neuro.com" method="post" encType="text/plain" className="rounded-xl border border-border-muted bg-white p-7 shadow-[0_8px_24px_rgba(20,60,55,0.04)] sm:p-9">
            <h2 className="text-2xl font-semibold">Inquiry Form</h2>
            <p className="mt-2 text-sm leading-relaxed text-secondary">Submit a detailed request and our response team will contact you within 4 business hours.</p>
            <div className="mt-7 grid gap-5 sm:grid-cols-2">
              <label className="block text-xs font-semibold uppercase tracking-wider text-secondary">
                Full name
                <input name="fullName" required placeholder="Dr. Sarah Mitchell" className="mt-2 h-12 w-full rounded-lg border border-[#8e9897] bg-white px-4 text-base font-normal normal-case tracking-normal text-on-surface outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15" />
              </label>
              <label className="block text-xs font-semibold uppercase tracking-wider text-secondary">
                Professional email
                <input name="email" type="email" required placeholder="s.mitchell@hospital.org" className="mt-2 h-12 w-full rounded-lg border border-[#8e9897] bg-white px-4 text-base font-normal normal-case tracking-normal text-on-surface outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15" />
              </label>
            </div>
            <label className="mt-5 block text-xs font-semibold uppercase tracking-wider text-secondary">
              Subject
              <select name="subject" defaultValue="System Integration Inquiry" className="mt-2 h-12 w-full rounded-lg border border-[#8e9897] bg-white px-4 text-base font-normal normal-case tracking-normal text-on-surface outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15">
                <option>System Integration Inquiry</option>
                <option>Technical Support</option>
                <option>Clinical Inquiry</option>
                <option>Account Management</option>
              </select>
            </label>
            <label className="mt-5 block text-xs font-semibold uppercase tracking-wider text-secondary">
              Detailed message
              <textarea name="message" required rows={5} placeholder="Please describe your inquiry in detail, including any specific patient ID (if applicable) or error codes encountered..." className="mt-2 w-full resize-y rounded-lg border border-[#8e9897] bg-white px-4 py-3 text-base font-normal normal-case tracking-normal text-on-surface outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15" />
            </label>
            <Button type="submit" className="mt-6 h-12 w-full rounded-lg font-semibold">
              Send Message <Send className="h-4 w-4" />
            </Button>
          </form>

          <div id="faq">
            <h2 className="text-2xl font-semibold">Frequently Asked Questions</h2>
            <div className="mt-6 space-y-3">
              {faqs.map((question) => (
                <details key={question} className="group rounded-xl border border-border-muted bg-[#f1f4f3]">
                  <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-5 py-5 text-sm font-semibold marker:content-none">
                    {question}
                    <ChevronDown className="h-5 w-5 shrink-0 text-primary transition-transform group-open:rotate-180" />
                  </summary>
                  <p className="border-t border-border-muted px-5 py-4 text-sm leading-relaxed text-secondary">
                    Contact the relevant support channel above for guidance tailored to your organisation and clinical workflow.
                  </p>
                </details>
              ))}
            </div>
            <div className="mt-7 rounded-xl bg-primary-container p-8 text-on-primary">
              <h3 className="text-xl font-semibold">Need detailed manuals?</h3>
              <p className="mt-3 text-sm leading-relaxed text-on-primary/80">Access our comprehensive clinical library with step-by-step diagnostic workflows.</p>
              <a href="#faq" className="mt-6 inline-flex h-11 items-center gap-2 rounded-lg bg-white px-5 text-sm font-semibold text-primary transition hover:bg-white/90">
                Browse Documentation <BookOpen className="h-4 w-4" />
              </a>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
