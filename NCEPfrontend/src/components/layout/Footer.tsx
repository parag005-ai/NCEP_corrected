import Link from "next/link";
import { Instagram, Linkedin, Facebook, Mail, Phone, MapPin, Shield, Heart } from "lucide-react";

import { Logo } from "@/components/ui/Logo";

const quickLinks = [
  { label: "Home", href: "/home" },
  { label: "About Us", href: "/about-us" },
  { label: "Services", href: "https://22neuro.com" },
  { label: "Clinical Evidence", href: "/clinical-evidence" },
  { label: "Blog / Insights", href: "https://22neuro.com" },
  { label: "Support", href: "/support" },
];

const legalLinks = [
  { label: "Terms & Conditions", href: "/terms" },
  { label: "Privacy Policy", href: "https://22neuro.com" },
  { label: "Ethics & Compliance", href: "https://22neuro.com" },
];

const socialLinks = [
  {
    href: "https://www.instagram.com/22_neuro/",
    label: "Instagram",
    icon: Instagram,
  },
  {
    href: "https://www.linkedin.com/company/22neuro/",
    label: "LinkedIn",
    icon: Linkedin,
  },
  {
    href: "https://www.facebook.com/people/22Neuro/61555257793750/",
    label: "Facebook",
    icon: Facebook,
  },
];

export function Footer() {
  return (
    <footer className="relative z-10 w-full overflow-hidden bg-primary-container text-on-primary">

      {/* Main Footer Grid */}
      <div className="relative z-10 mx-auto w-full max-w-container-max px-margin-mobile sm:px-gutter">
        <div className="grid grid-cols-1 gap-10 border-b border-on-primary/10 py-12 md:grid-cols-2 lg:grid-cols-5">

          {/* Brand Column */}
          <div className="flex flex-col gap-4 lg:col-span-2">
            <Logo className="text-on-primary" />
            <div className="mt-1 border-l-2 border-on-primary/40 pl-3">
              <p className="text-[10px] font-bold uppercase tracking-widest text-on-primary/70">
                On a mission to make brain care smarter,
              </p>
              <p className="text-[10px] font-bold uppercase tracking-widest text-on-primary/70">
                kinder, and accessible.
              </p>
            </div>
            <p className="text-body-sm text-on-primary/80 leading-relaxed">
              Transforming Multi-Format ECG &amp; SAECG Signals into Intelligent Clinical Decisions with advanced signal processing, AI-driven analytics, explainable insights, and secure patient data management.
            </p>
          </div>

          {/* Quick Links */}
          <div>
            <h3 className="mb-5 text-[11px] font-bold uppercase tracking-widest text-on-primary">
              Quick Links
            </h3>
            <ul className="flex flex-col gap-2.5">
              {quickLinks.map((link) => (
                <li key={link.label}>
                  <Link
                    href={link.href}
                    {...(link.href.startsWith("http") ? { target: "_blank", rel: "noopener noreferrer" } : {})}
                    className="text-body-sm text-on-primary/70 transition-all duration-200 hover:text-on-primary hover:translate-x-1 inline-block"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Legal & Policies */}
          <div>
            <h3 className="mb-5 text-[11px] font-bold uppercase tracking-widest text-on-primary">
              Legal & Policies
            </h3>
            <ul className="flex flex-col gap-2.5">
              {legalLinks.map((link) => (
                <li key={link.label}>
                  <Link
                    href={link.href}
                    {...(link.href.startsWith("http") ? { target: "_blank", rel: "noopener noreferrer" } : {})}
                    className="text-body-sm text-on-primary/70 transition-all duration-200 hover:text-on-primary hover:translate-x-1 inline-block"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Contact Info */}
          <div>
            <h3 className="mb-5 text-[11px] font-bold uppercase tracking-widest text-on-primary">
              Contact Info
            </h3>
              <ul className="flex flex-col gap-3 text-body-sm text-on-primary/70">
                <li className="flex items-start gap-2">
                  <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-on-primary/50" />
                  <span>POD 3, Transcend Discoveries Private Limited Mendeleev Block, Indian Institute Of Science Education And Research IISER, Pashan, Pune, Maharashtra 411008.</span>
                </li>
                <li className="flex items-center gap-2">
                  <Phone className="h-4 w-4 shrink-0 text-on-primary/50" />
                  <span>7758850500</span>
                </li>
                <li className="flex items-start gap-2">
                  <Mail className="mt-0.5 h-4 w-4 shrink-0 text-on-primary/50" />
                  <span>info@22neuro.com</span>
                </li>
              </ul>

              {/* Social Icons */}
              <div className="mt-5 flex items-center gap-3">
                {socialLinks.map(({ href, label, icon: Icon }) => (
                  <Link
                    key={label}
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={label}
                    className="flex h-9 w-9 items-center justify-center rounded-full border border-on-primary/20 bg-on-primary/10 text-on-primary/70 shadow-sm transition-all duration-300 hover:-translate-y-1.5 hover:scale-110 hover:bg-on-primary/20 hover:text-on-primary hover:shadow-md"
                  >
                    <Icon size={16} strokeWidth={2} />
                  </Link>
                ))}
              </div>
            </div>
        </div>

        {/* Trust Badges Row */}
        <div className="flex flex-col gap-6 border-b border-on-primary/10 py-6 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-on-primary/10">
              <Shield className="h-5 w-5 text-on-primary/80" />
            </div>
            <div>
              <p className="text-[12px] font-bold text-on-primary">Secure. Compliant. Trustworthy.</p>
              <p className="text-[11px] text-on-primary/60">Prioritizing the security and privacy of patient data.</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-on-primary/10">
              <Heart className="h-5 w-5 text-on-primary/80" />
            </div>
            <div>
              <p className="text-[12px] font-bold text-on-primary">Empowering Clinicians. Enhancing Lives.</p>
              <p className="text-[11px] text-on-primary/60">AI-Powered Insights for Better Cardiac Care.</p>
            </div>
          </div>
          {/* <div className="flex items-center gap-2 rounded-md border border-on-primary/10 px-4 py-2 text-[10px] text-on-primary/60">
            <Activity className="h-4 w-4 text-on-primary/40" />
            <span>HIPAA Compliant</span>
            <span className="opacity-40">•</span>
            <span>FDA Certified</span>
            <span className="opacity-40">•</span>
            <span>AES-256 Encryption</span>
          </div> */}
        </div>

        {/* Bottom Bar */}
        <div className="flex flex-col items-center justify-between gap-3 py-5 text-caption md:flex-row">
          <p className="text-on-primary/60">
            © 2026 CardioNexus | All Rights Reserved
          </p>
          {/* <p className="text-[10px] text-on-primary/40 leading-normal max-w-2xl text-center md:text-right">
            <strong className="text-on-primary/50">FDA Clinical Decision Support Notice:</strong> This software is intended for use as a clinical decision support tool. It is not a substitute for direct medical diagnosis or clinical judgment. Clinicians should confirm all automated ECG interpretations against raw patient telemetry data.
          </p> */}
        </div>
      </div>
    </footer>
  );
}
