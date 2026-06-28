# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM rust:1.82-alpine AS builder

# Build-time C toolchain + musl headers required by `ring` (used by jwt-simple).
# We use rustls, so OpenSSL is not needed at runtime.
RUN apk add --no-cache musl-dev pkgconfig

WORKDIR /workspace

# Copy workspace manifest and all member manifests so Cargo can resolve the
# full dependency graph before any source is present (layer cache optimisation).
COPY Cargo.toml ./
COPY push-worker/Cargo.toml ./push-worker/
COPY rules-engine/Cargo.toml ./rules-engine/

# Stub out real sources so `cargo build` succeeds for the dependency fetch step.
RUN mkdir -p push-worker/src rules-engine/src && \
    echo 'fn main() {}' > push-worker/src/main.rs && \
    echo 'fn main() {}' > rules-engine/src/main.rs

# Compile all dependencies (cached layer — rebuilt only when Cargo.toml changes).
RUN cargo build --release --package push-worker

# Remove the stub binary artefact so Cargo recompiles the real crate below.
RUN rm push-worker/src/main.rs

# Copy the real source and recompile only push-worker.
COPY push-worker/src ./push-worker/src

RUN touch push-worker/src/main.rs && \
    cargo build --release --package push-worker

# ── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM alpine:3.20 AS runtime

# ca-certificates is required for TLS to FCM / APNs / Web Push endpoints.
RUN apk add --no-cache ca-certificates && \
    addgroup -S pushworker && \
    adduser  -S pushworker -G pushworker

COPY --from=builder \
    /workspace/target/release/push-worker \
    /usr/local/bin/push-worker

RUN chmod 755 /usr/local/bin/push-worker

USER pushworker

# Defaults; override via docker-compose environment or K8s env vars.
ENV RUST_LOG=info \
    PUSH_WORKER_CONCURRENCY=8

ENTRYPOINT ["/usr/local/bin/push-worker"]
