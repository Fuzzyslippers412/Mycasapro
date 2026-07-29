# syntax=docker/dockerfile:1.7

FROM golang:1.25-alpine AS builder
WORKDIR /src/app

COPY app/go.mod app/go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod go mod download

COPY app/ ./
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/mycasapro-server ./cmd/server

FROM alpine:3.22
RUN apk add --no-cache ca-certificates tzdata wget \
    && addgroup -S -g 10001 mycasapro \
    && adduser -S -D -H -u 10001 -G mycasapro mycasapro \
    && mkdir -p /app/migrations /data/uploads \
    && chown -R mycasapro:mycasapro /data

WORKDIR /app
COPY --from=builder /out/mycasapro-server /usr/local/bin/mycasapro-server
COPY --from=builder /src/app/migrations ./migrations

ENV APP_ADDR=:8081 \
    APP_MIGRATIONS_DIR=/app/migrations \
    APP_UPLOAD_DIR=/data/uploads

USER mycasapro
EXPOSE 8081
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 \
  CMD wget -qO- http://127.0.0.1:8081/healthz >/dev/null || exit 1
ENTRYPOINT ["/usr/local/bin/mycasapro-server"]
