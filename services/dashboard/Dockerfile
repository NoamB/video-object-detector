FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY services/dashboard/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared library
COPY shared /app/shared

# Copy service code
COPY services/dashboard /app/dashboard
COPY services/detection/database.py /app/detection/
COPY services/detection/models.py /app/detection/

EXPOSE 8001

CMD ["uvicorn", "dashboard.main:app", "--host", "0.0.0.0", "--port", "8001"]
