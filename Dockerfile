# ============================================================
# JobTrack AI — Production Dockerfile
# ============================================================
# Multi-stage build:
# 1. Python deps → pip install
# 2. Dashboard → Next.js build
# 3. Runtime → Playwright + all artifacts
#
# WHY multi-stage? The builder stages add ~2GB for node_modules
# and build artifacts that the runtime doesn't need. Final image
# is ~800MB (mostly Chromium for Playwright).
# ============================================================

# ── Stage 1: Python dependencies ──
FROM python:3.11-slim AS python-builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Dashboard build ──
FROM node:18-slim AS dashboard-builder
WORKDIR /dashboard
COPY dashboard/package*.json ./
RUN npm ci --production=false
COPY dashboard/ .
# Build-time env var for API URL — overridden at runtime
ENV NEXT_PUBLIC_API_URL=http://localhost:8000
RUN npm run build

# ── Stage 3: Production runtime ──
FROM python:3.11-slim
WORKDIR /app

# Install system packages BEFORE switching user
# WHY apt-get first? Playwright install-deps needs root.
# nodejs is needed to run the Next.js dashboard in standalone mode.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=python-builder /install /usr/local

# Copy the application code
COPY . .

# Copy the pre-built dashboard
COPY --from=dashboard-builder /dashboard/.next ./dashboard/.next
COPY --from=dashboard-builder /dashboard/node_modules ./dashboard/node_modules
COPY --from=dashboard-builder /dashboard/package.json ./dashboard/package.json

# Install Playwright + Chromium with all system dependencies
# WHY --with-deps? This flag installs Chromium's shared library
# dependencies (libglib, libnss, etc.) in one command. Without it,
# Chromium launches but immediately crashes on missing libs.
RUN pip install playwright && \
    playwright install chromium --with-deps

# Non-root user setup AFTER Playwright install
# WHY after? Playwright install needs root to install system libs
RUN useradd -m -u 1001 appuser && \
    mkdir -p workspace && \
    chown -R appuser:appuser /app

# Make entrypoint executable
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

USER appuser

# Expose both API and dashboard ports
EXPOSE 8000 3000

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Entrypoint seeds admin, then exec's into uvicorn
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "api.main:app", \
     "--host", "0.0.0.0", "--port", "8000"]