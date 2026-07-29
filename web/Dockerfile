# syntax=docker/dockerfile:1.7

FROM node:22-alpine AS dependencies
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
ARG MYCASAPRO_INTERNAL_API_URL=http://app:8081
ENV MYCASAPRO_INTERNAL_API_URL=${MYCASAPRO_INTERNAL_API_URL} \
    NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000

RUN addgroup -S -g 10001 mycasapro \
    && adduser -S -D -H -u 10001 -G mycasapro mycasapro

COPY --from=builder --chown=mycasapro:mycasapro /app/.next/standalone ./
COPY --from=builder --chown=mycasapro:mycasapro /app/.next/static ./.next/static

USER mycasapro
EXPOSE 3000
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 \
  CMD wget -qO- http://127.0.0.1:3000/ >/dev/null || exit 1
CMD ["node", "server.js"]
