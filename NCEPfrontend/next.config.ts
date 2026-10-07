import type { NextConfig } from "next";

// NOTE: `output: "export"` (static export for Cloudflare Pages) was removed — a
// backend/DB-driven app renders dynamic routes (e.g. /doctor/patients/[patientId])
// on demand at runtime, which static export cannot do.
const nextConfig: NextConfig = {
  // Traced, minimal server bundle for the Cloud Run container image (deploy/gcp).
  output: "standalone",
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
