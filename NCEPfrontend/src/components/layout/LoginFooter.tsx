import { Instagram, Linkedin, Facebook } from "lucide-react";
import Link from "next/link";

export function LoginFooter() {
  return (
    <footer className="relative z-20 w-full bg-primary-container py-4 px-4 sm:px-8 flex flex-col sm:flex-row items-center justify-between text-sm text-on-primary/70 border-t border-on-primary/10">
      <div className="flex flex-col sm:flex-row items-center gap-2 sm:gap-4 mb-4 sm:mb-0">
        <span className="font-medium tracking-wide text-on-primary/90">
          © {new Date().getFullYear()} CardioNexus | All Rights Reserved |
        </span>
        <div className="flex items-center gap-3">
          <Link
            href="https://www.instagram.com/22_neuro/"
            target="_blank"
            rel="noopener noreferrer"
            className="flex h-8 w-8 items-center justify-center rounded-full bg-on-primary/10 text-on-primary/70 transition-transform duration-300 hover:-translate-y-1 hover:scale-110 shadow-sm hover:bg-on-primary/20 hover:text-on-primary"
          >
            <Instagram size={16} strokeWidth={2.5} />
          </Link>
          <Link
            href="https://www.linkedin.com/company/22neuro/"
            target="_blank"
            rel="noopener noreferrer"
            className="flex h-8 w-8 items-center justify-center rounded-full bg-on-primary/10 text-on-primary/70 transition-transform duration-300 hover:-translate-y-1 hover:scale-110 shadow-sm hover:bg-on-primary/20 hover:text-on-primary"
          >
            <Linkedin size={16} strokeWidth={2.5} />
          </Link>
          <Link
            href="https://www.facebook.com/people/22Neuro/61555257793750/"
            target="_blank"
            rel="noopener noreferrer"
            className="flex h-8 w-8 items-center justify-center rounded-full bg-on-primary/10 text-on-primary/70 transition-transform duration-300 hover:-translate-y-1 hover:scale-110 shadow-sm hover:bg-on-primary/20 hover:text-on-primary"
          >
            <Facebook size={16} strokeWidth={2.5} />
          </Link>
        </div>
      </div>
      <div className="font-medium tracking-wide text-on-primary/70 text-xs">
        Secure Clinical Precision Platform
      </div>
    </footer>
  );
}
