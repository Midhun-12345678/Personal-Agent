FROM python:3.11-slim

# System deps for Playwright + sentence-transformers
RUN apt-get update && apt-get install -y \
    gcc g++ curl git \
    libnss3 libatk-bridge2.0-0 libdrm2 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libxkbcommon0 \
    libasound2 libpangocairo-1.0-0 libgtk-3-0 libx11-xcb1 \
    wget fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium --with-deps

# Copy source
COPY . .

EXPOSE 8765

CMD ["python", "run.py"]
