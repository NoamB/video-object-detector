FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy local service requirements.txt to root of workdir
COPY services/ingestion/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared library
COPY shared /app/shared

# Copy service code
COPY services/ingestion /app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
