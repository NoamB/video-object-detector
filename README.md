# Video Ingestion and Object Detection System

A scalable, asynchronous 3-service system for processing video uploads, extracting frames, and detecting objects.

## 🚀 Features

- **Service A (Ingestion & Analytics)**: 
  - Fast file upload (FastAPI).
  - Reliable task publishing to Kafka (`video-uploads`).
  - Integrated Dashboard for viewing real-time detection results.
- **Service B (Processing Worker)**:
  - Consumes from Kafka (`video-uploads`).
  - Extracts frames using OpenCV.
  - Publishes frame tasks to Kafka (`frame-tasks`).
- **Service C (Detection Worker)**: 
  - Consumes from Kafka (`frame-tasks`).
  - Runs YOLOv8 inference.
  - Persists results to PostgreSQL.
- **Robustness**:
  - Full Type Hinting and Pydantic validation.
  - Automatic Database Initialization.
  - SHA256 Data Integrity Verification.

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

## 🔍 Checking Results

### Dashboard
Visit `http://localhost:8000/` in your browser to view the real-time detection feed.

### Command Line
You can also inspect the results in the PostgreSQL database:
```bash
# Connect to DB container
docker-compose exec postgres psql -U user -d videodb

# Query results
SELECT * FROM detections ORDER BY timestamp DESC LIMIT 5;
```

## 🗄 Database Management
- **Initialize Database**:
  ```bash
  docker-compose exec detection-service python scripts/init_db.py
  ```
- **Drop Database**:
  ```bash
  docker-compose exec detection-service python scripts/drop_db.py
  ```

## 🧪 Development

### Project Structure
```text
├── services
│   ├── ingestion       # FastAPI App + Dashboard (Port 8000)
│   ├── processing      # Frame Extraction Worker
│   └── detection       # AI Inference Worker
├── shared              # Shared schemas, storage, and database logic
├── scripts             # DB management and diagnostic scripts
├── docker-compose.yml  # System orchestration
└── ARCHITECTURE.md     # System design documentation
```
