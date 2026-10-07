//LoginPage
import { LoginFooter } from "@/components/layout/LoginFooter";
import { Navbar } from "@/components/layout/Navbar";
import { LoginCard } from "@/components/auth/LoginCard";
import { ECGBackground } from "@/components/ui/ECGBackground";
import { LoginTerms } from "@/components/auth/LoginTerms";

export default function LoginPage() {
  return (
    <div className="relative flex min-h-screen flex-col overflow-x-hidden bg-surface">
      <ECGBackground />
      <Navbar showSignIn={false} />
      <main className="relative z-10 flex flex-1 flex-col items-center justify-center px-margin-mobile pb-6 pt-[84px] sm:px-gutter">
        <LoginCard />
        <LoginTerms />
      </main>
      <LoginFooter />
    </div>
  );
}

