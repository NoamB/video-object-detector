# Architecture Design Document

## 1. System Overview
This system is designed for **Video Ingestion, Processing, and Object Detection**. It uses a staged pipeline approach to decouple slow processing tasks (frame extraction and AI inference) from the fast ingestion task.

### Key Goals
- **Scalability**: Each stage of the pipeline can be scaled independently.
- **Reliability**: Message durability via Kafka and manual offset commits.
- **Responsiveness**: Ingestion returns immediately after the video is saved and task is queued.
- **Type Safety**: Pydantic models used for all inter-service communication.

## 2. High-Level Architecture

```mermaid
flowchart TD
    %% Global Styles and Colors (High Contrast)
    classDef container fill:#fcfcfc,stroke:#1a1a1a,stroke-width:2px,stroke-dasharray: 5 5,color:#1a1a1a
    classDef ingestion fill:#e3f2fd,stroke:#0d47a1,stroke-width:2px,color:#0a192f
    classDef processing fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px,color:#0a192f
    classDef detection fill:#fce4ec,stroke:#880e4f,stroke-width:2px,color:#0a192f
    classDef infra fill:#fffde7,stroke:#e65100,stroke-width:2px,color:#0a192f
    classDef module fill:#ffffff,stroke:#333333,stroke-width:1.5px,color:#1a1a1a
    classDef user fill:#ffffff,stroke:#1a1a1a,stroke-width:2px,color:#1a1a1a

    U((User)):::user

    subgraph ContainerA [Service A: Ingestion & Analytics]
        direction TB
        A1["main.py (API)"]:::module
        A2["Templates/Static"]:::module
        A1 --- A2
    end
    class ContainerA ingestion

    subgraph ContainerB [Service B: Processing]
        direction TB
        B1["worker.py (Consumer)"]:::module
        B2["processing.py (OpenCV)"]:::module
        B1 --> B2
    end
    class ContainerB processing

    subgraph ContainerC [Service C: Detection]
        direction TB
        C1["main.py (Consumer)"]:::module
        C2["detector.py (YOLOv8)"]:::module
        C1 --> C2
    end
    class ContainerC detection

    subgraph ContainerI [Infrastructure]
        direction TB
        K[[Kafka Broker]]:::infra
        S[(Shared Storage)]:::infra
        D[(PostgreSQL)]:::infra
    end
    class ContainerI infra

    %% Data Flow
    U -- "(1) Upload" --> A1
    A1 -- "(2) Save Video" --> S
    A1 -- "(3) Publish Task" --> K

    K -- "(4) Fetch Job" --> B1
    B1 -- "(5) Extract" --> B2
    B2 -- "(6) Save Frames" --> S
    B2 -- "(7) Publish Tasks" --> K

    K -- "(8) Fetch Task" --> C1
    C1 -- "(9) Inference" --> C2
    C2 -- "(10) Read Frame" --> S
    C1 -- "(11) Save Result" --> D

    U -- "(12) View Results" --> A1
    A1 -- "(13) Query" --> D
    A1 -- "(14) Stream" --> S

    %% Darker and thicker arrows for better visibility
    linkStyle default stroke:#222,stroke-width:2px,color:#000
```

## 3. Core Components

### Service A: Ingestion & Analytics Service
- **Role**: Entry point for users. Handles uploads, queues video tasks, and serves the dashboard UI/API for viewing results.
- **Tech**: FastAPI (Python), Jinja2, Pydantic.
- **Data Flow**: `Upload -> Disk -> Kafka (video-uploads)` and `DB -> UI`

### Service B: Processing Service
- **Role**: Consumes uploaded videos, extracts individual frames at a specific interval.
- **Tech**: Python Asyncio, OpenCV, Pydantic.
- **Data Flow**: `Kafka (video-uploads) -> Frame Extraction -> Disk -> Kafka (frame-tasks)`

### Service C: Detection Service
- **Role**: Consumes frame tasks and runs object detection.
- **Tech**: Python Asyncio, Ultralytics YOLOv8, SQLAlchemy, Pydantic.
- **Data Flow**: `Kafka (frame-tasks) -> AI Inference -> PostgreSQL`

## 4. Project Structure
```text
├── services
│   ├── ingestion       # FastAPI App + Dashboard (Port 8000)
│   │   ├── main.py
│   │   └── templates/  # Dashboard HTML
│   ├── processing      # Frame Extraction Worker
│   │   ├── worker.py
│   │   └── processing.py
│   └── detection       # AI Inference Worker
│       ├── main.py
│       └── detector.py
├── shared              # Shared schemas, storage, and database logic
│   ├── database.py     # SQLAlchemy/Async engine setup
│   ├── models.py       # SQL Models
│   ├── schemas.py      # Pydantic validation schemas
│   ├── mq.py           # Kafka Producer/Consumer
│   └── storage.py      # File system abstraction
├── scripts             # DB management and diagnostic scripts
│   ├── init_db.py      # Table creation
│   └── drop_db.py      # Database cleanup
└── docker-compose.yml  # System orchestration
```

## 5. Key Design Decisions

### 5.1 Message Broker: Apache Kafka
We use **Apache Kafka** (KRaft mode) for its superior durability and scaling characteristics. All messages are validated using **Pydantic** before publishing and upon consumption.

| Topic | Producer | Consumer | Purpose |
| :--- | :--- | :--- | :--- |
| `video-uploads` | Ingestion | Processing | New videos to be fragmented into frames |
| `frame-tasks` | Processing | Detection | Individual frames to be analyzed by AI |

### 5.2 Storage: Shared Volume
We use a Docker shared volume for storing videos and extracted frames. In a cloud environment, this would be replaced with an S3-compatible object store.

### 5.3 Database: PostgreSQL
Stores structured detection results for querying and visualization. Managed via SQLAlchemy (async).

## 6. Scalability Considerations
- **Independent Scaling**: If frame extraction is slow, we can increase `Processing` replicas. If AI inference is the bottleneck, we scale `Detection`.
- **Kafka Partitions**: Increasing partitions in either topic allows for higher parallel throughput.
