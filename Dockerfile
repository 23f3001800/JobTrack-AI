# Stage 1: pip install dependencies
FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: runtime with Playwright
FROM python:3.11-slim
WORKDIR /app

# Install system packages BEFORE switching user
# WHY apt-get first? playwright install-deps needs root.
# Switching to appuser before this step causes permission errors.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl nodejs npm \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY . .

# Install Playwright + Chromium with all system dependencies
# WHY --with-deps? This flag runs the equivalent of
# playwright install-deps in one command. Without it,
# Chromium launches but immediately crashes on missing libs.
RUN pip install playwright && \
    playwright install chromium --with-deps

# Non-root user setup AFTER Playwright install
RUN useradd -m -u 1001 appuser && \
    mkdir -p workspace && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8001
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')"
  CMD ["uvicorn", "api.main:app", \
     "--host", "0.0.0.0", "--port", "8001"]