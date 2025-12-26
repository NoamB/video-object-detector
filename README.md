# Video Ingestion and Object Detection System

A scalable, async dual-service system for processing video uploads, extracting frames, and detecting objects using YOLOv8.

## 🚀 Features

- **Service A (Ingestion)**: 
  - Fast, async file upload (FastAPI).
  - Frame extraction (OpenCV).
  - Reliable task publishing to Redis.
- **Service B (Detection Worker)**: 
  - Consumes frames from Redis using **Reliable Queue Pattern** (`BRPOPLPUSH`).
  - Runs YOLOv8 inference.
  - key-value extraction of classes and bounding boxes.
  - Persists results to PostgreSQL.
- **Infrastructure**:
  - Redis with **AOF Persistence** (Zero data loss on broker crash).
  - PostgreSQL for structured data storage.
  - Docker Compose orchestration.

## 🏗 Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for a detailed design document and diagrams.

## 🛠 Setup & Running

### Prerequisites
- Docker & Docker Compose

### Start the System
```bash
docker-compose up --build
```

### Upload a Video
```bash
# Upload a video file to the ingestion service
curl -X POST -F "file=@/path/to/your/video.mp4" http://localhost:8000/upload
```
Response:
```json
{
  "video_id": "c5e9335a-...",
  "status": "accepted",
  "message": "Video accepted for processing"
}
```

## 🔍 Checking Results

You can inspect the results in the PostgreSQL database:
```bash
# Connect to DB container
docker-compose exec postgres psql -U user -d videodb

# Query detections
SELECT * FROM detections ORDER BY timestamp DESC LIMIT 5;
```

### 🗄 Database Management
Run these management scripts from inside the containers using `docker-compose exec`:
- **Initialize Database**:
  ```bash
  docker-compose exec detection-service python scripts/init_db.py
  ```
- **Wipe Database**:
  ```bash
  docker-compose exec detection-service python scripts/drop_db.py
  ```

## 🧪 Development

### Project Structure
```text
.
├── services
│   ├── ingestion       # FastAPI App (Port 8000)
│   └── detection       # Worker Process
├── docker-compose.yml  # Orchestration
└── ARCHITECTURE.md     # Design Documentation
```

### Configuration
Environment variables can be set in `docker-compose.yml`:
- `REDIS_HOST`, `REDIS_PORT`
- `DATABASE_URL`
