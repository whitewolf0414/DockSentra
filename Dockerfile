# ──────────────────────────────────────────────────────────────────────────────
# Dockerfile — dockerfile-security-checker (production image)
#
# This file containerises the CLI tool itself and is designed to score 100/100
# when scanned by the tool (dogfooding / self-attestation).
#
# Security guarantees:
#   ✓ no_root_user          — runs as non-root user "scanner"
#   ✓ unpinned_base_image   — pinned to python:3.11.9-slim (no :latest)
#   ✓ hardcoded_secret      — no secrets in ENV or ARG
#   ✓ missing_healthcheck   — HEALTHCHECK instruction present
#   ✓ add_instead_of_copy   — uses COPY only, never ADD
# ──────────────────────────────────────────────────────────────────────────────

FROM python:3.11.9-slim

# OCI image labels (no secrets)
LABEL org.opencontainers.image.title="dockerfile-security-checker"
LABEL org.opencontainers.image.description="CLI tool to scan Dockerfiles for security misconfigurations"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.source="https://github.com/example/dockerfile-security-checker"

# Install OS-level dependencies without caching to keep image small
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python dependencies first (layer caching)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the application code and config (not tests or dev files)
COPY app/      /app/app/
COPY config/   /app/config/

# Create a non-root system user for running the scanner
RUN groupadd -r scanner && useradd -r -g scanner -d /app -s /sbin/nologin scanner \
    && chown -R scanner:scanner /app

# Drop privileges — satisfies no_root_user rule
USER scanner

# Expose the web port
EXPOSE 5000

# Health check — satisfies missing_healthcheck rule
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

# Default command runs the web server
# Override with: docker run <image> python -m app.cli.cli --file /scan/Dockerfile
CMD ["python", "-m", "app.web.app"]
