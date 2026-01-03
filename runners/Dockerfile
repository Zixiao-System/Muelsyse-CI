FROM rust:1.75 as builder

WORKDIR /app

# Copy manifests
COPY Cargo.toml Cargo.lock ./

# Create dummy main.rs to cache dependencies
RUN mkdir src && \
    echo "fn main() {}" > src/main.rs && \
    cargo build --release && \
    rm -rf src

# Copy actual source
COPY src ./src

# Build for release
RUN cargo build --release

# Runtime image
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    ca-certificates \
    libssl3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy binary from builder
COPY --from=builder /app/target/release/muelsyse-runner /usr/local/bin/

# Create directories
RUN mkdir -p /tmp/muelsyse/workspaces /tmp/muelsyse/artifacts /tmp/muelsyse/cache

# Create non-root user
RUN useradd -m -u 1000 runner && \
    chown -R runner:runner /tmp/muelsyse

USER runner

CMD ["muelsyse-runner"]
