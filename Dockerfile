# Multi-stage build to reduce final image size
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ git curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/app/python-packages -r requirements.txt

# Final stage - minimal runtime image
FROM python:3.11-slim

# Install only runtime dependencies for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libatk-bridge2.0-0 libdrm2 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libxkbcommon0 \
    libasound2 libpangocairo-1.0-0 libgtk-3-0 libx11-xcb1 \
    fonts-liberation ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /app/python-packages /usr/local/lib/python3.11/site-packages/

# Install Playwright browser and clean up cache aggressively
RUN playwright install chromium --with-deps && \
    rm -rf /root/.cache/ms-playwright/*.zip && \
    rm -rf /tmp/* && \
    find /root/.cache/ms-playwright -type f -name "*.zip" -delete

# Copy application code
COPY . .

# Create workspace directory
RUN mkdir -p /app/.personal-agent

# Reduce image size by removing unnecessary files
RUN find /usr/local/lib/python3.11/site-packages -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.11/site-packages -type d -name "test" -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.11/site-packages -name "*.pyc" -delete && \
    find /usr/local/lib/python3.11/site-packages -name "*.pyo" -delete && \
    find /usr/local/lib/python3.11/site-packages -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

EXPOSE 8765

ENV PYTHONUNBUFFERED=1
ENV NANOBOT_WORKSPACE=/app/.personal-agent

CMD ["python", "run.py"]

