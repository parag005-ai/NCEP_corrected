# NCEP Clinical Precision Platform Frontend

Production-style frontend for the Neuro Cardiac Electrophysiology Platform, built from the provided Stitch design system export.

## Tech Stack

- Next.js App Router
- TypeScript
- Tailwind CSS
- Inter via `next/font/google`
- Lucide React icons
- `clsx` and `tailwind-merge`

## Routes

- `/login`
- `/patient/dashboard`, `/patient/registration`, `/patient/details`, `/patient/ecg-upload`, `/patient/reports`
- `/doctor/dashboard`, `/doctor/patients`, `/doctor/patient-details`, `/doctor/ecg-viewer`, `/doctor/reports`, `/doctor/clinical-decision-support`
- `/admin/dashboard`, `/admin/users`, `/admin/patients`, `/admin/reports`, `/admin/settings`
- `/superadmin/dashboard`, `/superadmin/organizations`, `/superadmin/admins`, `/superadmin/audit-logs`, `/superadmin/system-settings`

## Structure

- `src/app` contains App Router pages and role layouts.
- `src/components/ui` contains reusable Stitch-aligned UI primitives.
- `src/components/layout` contains navbar, footer, dashboard shell, sidebar, and page header.
- `src/components/auth`, `patient`, `doctor`, `admin`, and `dashboard` contain feature components.
- `src/config` stores navigation, role labels, and site metadata.
- `src/data` stores centralized mock patients, reports, and dashboard data.
- `src/lib` contains shared utilities.

## Run Locally

```bash
npm install
npm run dev
```

Open `http://localhost:3000`.

## Validate

```bash
npm run lint
npm run type-check
npm run build
```

## Cloudflare Pages Upload

This app is configured for static export with `output: "export"` in `next.config.ts`.

Run:

```bash
npm install
npm run build
```

Upload the generated `cloudflare-upload` folder contents to Cloudflare Pages Direct Upload.

If Cloudflare asks for a build output directory, use:

```text
cloudflare-upload
```

For Direct Upload, select every file and folder inside `cloudflare-upload`, including `_next`, `assets`, `_headers`, and `_redirects`.

## Future Integration

Authentication can be connected by replacing the placeholder login submit handler with a backend auth flow and protecting role routes through middleware. ECG upload can be connected by replacing the mock upload panel with an API-backed file upload service. Role-based access can be wired to server-provided user claims while keeping the current role-aware navigation config.

This project is frontend-only. It does not include backend APIs, database logic, authentication backend, real ECG processing, external service calls, diagnosis, or treatment recommendations.
