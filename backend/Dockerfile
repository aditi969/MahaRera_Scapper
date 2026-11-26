FROM python:3.11-slim

# ── Environment variables ─────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app:/app/backend:${PYTHONPATH}" \
    DEBIAN_FRONTEND=noninteractive

# ── System dependencies ──────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Tesseract OCR & English language data
    tesseract-ocr \
    tesseract-ocr-eng \
    # OpenCV headless & PDF processing libraries
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    poppler-utils \
    ghostscript \
    # Network / SSL / Utilities
    curl \
    wget \
    ca-certificates \
    # Build tools for compiled dependencies (psycopg2, etc.)
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Google Chrome (Official Stable Release) ──────────────────────────────────
# Direct .deb download avoids deprecated apt-key and guarantees correct dependencies
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y --no-install-recommends ./google-chrome-stable_current_amd64.deb \
    && rm google-chrome-stable_current_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

# Note: Modern Selenium (4.10+) automatically manages ChromeDriver via built-in
# Selenium Manager for the installed Google Chrome version. No third-party
# 'chromedriver-autoinstall' package is needed.

# ── Python dependencies ──────────────────────────────────────────────────────
WORKDIR /app

# Copy requirements first for Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Application code ─────────────────────────────────────────────────────────
# Copy full codebase (backend, scraper, database schemas, configs)
COPY . .

# Ensure storage directories exist
RUN mkdir -p /app/storage/csv /app/storage/excel /app/storage/temp /app/storage/logs

# ── Runtime ─────────────────────────────────────────────────────────────────
EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
