# ── Base ──────────────────────────────────────────────────────────────────────
FROM python:3.11-slim

# ── System deps: Tesseract + Arabic lang + Poppler (للـ PDF) ─────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-ara \
    tesseract-ocr-eng \
    poppler-utils \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# ── Python deps ───────────────────────────────────────────────────────────────
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── App files ─────────────────────────────────────────────────────────────────
COPY main.py .
COPY ocr_processor.py .
COPY ollama_corrector.py .

# ── Run ───────────────────────────────────────────────────────────────────────
# Railway بيحدد الـ PORT تلقائياً عن طريق environment variable
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
