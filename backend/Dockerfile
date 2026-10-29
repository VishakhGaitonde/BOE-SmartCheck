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
CMD ["sh", "-c", "echo '1. Starting Python'; python -u -c 'import app.main; print(\"2. APP_IMPORT_OK\", flush=True); import uvicorn, os; print(\"3. Starting Uvicorn\", flush=True); uvicorn.run(\"app.main:app\", host=\"0.0.0.0\", port=int(os.environ.get(\"PORT\", \"10000\")), log_level=\"debug\")'"]