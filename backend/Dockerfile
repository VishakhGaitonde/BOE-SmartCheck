FROM python:3.12-slim

# Install Tesseract OCR and build dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libgl1 \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render injects $PORT at runtime — bind to it
CMD ["sh", "-c", "echo Starting FastAPI on port ${PORT:-10000}; exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --log-level debug"]