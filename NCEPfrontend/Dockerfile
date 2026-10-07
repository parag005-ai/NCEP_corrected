# syntax=docker/dockerfile:1
FROM node:20-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# NEXT_PUBLIC_* vars are inlined into the client bundle at build time, so the
# backend's Cloud Run URL must be known before this stage runs (see
# deploy/gcp/03-deploy-frontend.sh, which builds this image after the backend
# is deployed).
ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}
ENV NEXT_TELEMETRY_DISABLED=1

# Plain `next build` -- skips scripts/prepare-cloudflare-upload.mjs, which is
# Cloudflare Pages-specific and irrelevant to this Cloud Run image.
RUN npm run build:next

FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Cloud Run injects PORT; the Next.js standalone server respects it directly.
ENV PORT=8080
EXPOSE 8080

CMD ["node", "server.js"]
