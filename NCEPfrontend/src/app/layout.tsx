import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { siteConfig } from "@/config/site";
import { AuthProvider } from "@/providers/AuthProvider";
import { ToastProvider } from "@/components/ui/Toast";
import { SystemStateManager } from "@/providers/SystemStateManager";
import { LegalConsentGate } from "@/components/auth/LegalConsentGate";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: {
    default: `${siteConfig.name} Clinical Precision Platform`,
    template: `%s | ${siteConfig.name}`,
  },
  description: siteConfig.description,
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased`} suppressHydrationWarning>
        <SystemStateManager>
          <AuthProvider>
            <ToastProvider>{children}</ToastProvider>
            <LegalConsentGate />
          </AuthProvider>
        </SystemStateManager>
      </body>
    </html>
  );
}
