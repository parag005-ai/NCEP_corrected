"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { topNavItems } from "@/config/navigation";
import { Logo } from "@/components/ui/Logo";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

type NavbarProps = {
  showSignIn?: boolean;
};

export function Navbar({ showSignIn = true }: NavbarProps) {
  const pathname = usePathname();

  const checkIsActive = (href: string) => {
    if (!pathname) return false;
    if (href === "/home" && (pathname === "/home" || pathname === "/")) return true;
    if (href === "/terms" && pathname === "/terms") return true;
    if (href !== "/" && href !== "/home" && pathname.startsWith(href)) return true;
    return pathname === href;
  };

  return (
    <>
      <nav className="fixed top-0 z-50 h-header-height w-full border-b border-border-muted bg-surface/95 shadow-sm backdrop-blur">
      <div className="mx-auto flex h-full w-full max-w-container-max items-center justify-between px-margin-mobile sm:px-gutter">
        <Link href="/" aria-label="CardioNexus Home">
          <Logo compact className="text-primary" />
        </Link>
        <div className="hidden items-center gap-8 md:flex">
          {topNavItems.map((item) => {
            const href = item === "Home" ? "/home" : item === "Platform" ? "/" : `/${item.toLowerCase().replace(" ", "-")}`;
            const isActive = checkIsActive(href);
            return (
              <Link 
                key={item} 
                href={href} 
                className={cn(
                  "relative py-1 text-body-lg transition-all duration-300",
                  isActive
                    ? "font-semibold text-primary"
                    : "font-medium text-secondary hover:text-primary hover:drop-shadow-[0_0_8px_rgba(44,181,165,0.4)] hover:[text-shadow:_0_0_10px_rgba(44,181,165,0.35)]"
                )}
              >
                {item}
                {isActive && (
                  <span className="absolute -bottom-1.5 left-0 right-0 h-[2px] rounded-full bg-primary" />
                )}
              </Link>
            );
          })}
          <Link 
            href="/terms"
            className={cn(
              "relative py-1 text-body-lg transition-all duration-300",
              checkIsActive("/terms")
                ? "font-semibold text-primary"
                : "font-medium text-secondary hover:text-primary hover:drop-shadow-[0_0_8px_rgba(44,181,165,0.4)] hover:[text-shadow:_0_0_10px_rgba(44,181,165,0.35)]"
            )}
          >
            Terms & Conditions
            {checkIsActive("/terms") && (
              <span className="absolute -bottom-1.5 left-0 right-0 h-[2px] rounded-full bg-primary" />
            )}
          </Link>
        </div>
        
        {showSignIn && (
          <div className="flex items-center">
            <Link href="/login">
              <Button variant="outline" className="h-9">Sign in</Button>
            </Link>
          </div>
        )}
      </div>
      </nav>
    </>
  );
}
