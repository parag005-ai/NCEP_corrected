import Link from "next/link";

export function LoginTerms() {
  return (
    <p className="mt-4 max-w-[520px] text-center text-caption leading-relaxed text-secondary">
      By signing in, you agree to the platform&apos;s{" "}
      <Link 
        href="/terms"
        className="font-medium text-primary hover:underline"
      >
        Terms and Conditions
      </Link>
      . This is placeholder text for the CardioNexus Clinical Precision Platform and may be replaced with approved legal content.
    </p>
  );
}
