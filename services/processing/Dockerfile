FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for OpenCV and networking
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY services/processing/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared library
COPY shared /app/shared

# Copy service code
COPY services/processing /app

CMD ["python", "worker.py"]
