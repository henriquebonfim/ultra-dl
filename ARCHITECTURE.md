# UltraDL - System Architecture

> **Purpose**: High-level architecture overview showing how all services work together. For service-specific details, see local ARCHITECTURE.md files in each folder.

---

## 🏗️ System Overview

```mermaid
graph TB
    subgraph "Client Layer"
        UI[React SPA<br/>Frontend]
    end

    subgraph "API Layer"
        API[Flask REST API<br/>Backend]
        WS[WebSocket Server<br/>Socket.IO]
    end

    subgraph "Processing Layer"
        CELERY[Celery Workers<br/>Background Tasks]
        YTDLP[yt-dlp<br/>YouTube Downloader]
    end

    subgraph "Data Layer"
        REDIS[(Redis<br/>Cache + Queue)]
        FS[File Storage<br/>Local/GCS]
    end

    UI -->|HTTP/REST| API
    UI -.->|WebSocket| WS
    API --> REDIS
    API --> FS
    API -->|Queue Task| CELERY
    CELERY --> REDIS
    CELERY --> YTDLP
    CELERY --> FS
    WS --> REDIS

    style UI fill:#e1f5ff
    style API fill:#fff3e0
    style CELERY fill:#f3e5f5
    style REDIS fill:#ffebee
    style FS fill:#e8f5e9
```

---

## 📐 Architecture Patterns

### Backend: Domain-Driven Design (DDD)

**3-Layer Clean Architecture:**

```mermaid
graph TB
    subgraph "API Layer"
        REST[REST Endpoints<br/>Flask-RESTX]
    end

    subgraph "Application Layer"
        DS[DownloadService]
        JS[JobService]
        VS[VideoService]
        DI[DependencyContainer]
    end

    subgraph "Domain Layer"
        JM[JobManager]
        FM[FileManager]
        VP[VideoProcessor]
        ENT[Entities<br/>DownloadJob, FileMetadata]
        EVT[Domain Events]
    end

    subgraph "Infrastructure Layer"
        RJR[RedisJobRepository]
        RFR[RedisFileRepository]
        GCS[GCSRepository]
        LFS[LocalFileRepository]
        EH[EventHandlers<br/>WebSocket]
    end

    REST --> DS
    REST --> JS
    REST --> VS
    DS --> JM
    JS --> JM
    VS --> VP
    JM --> ENT
    FM --> ENT
    JM -.->|publishes| EVT
    RJR -.->|implements| JM
    RFR -.->|implements| FM
    GCS -.->|implements| FM
    LFS -.->|implements| FM
    EH -.->|subscribes| EVT

    style REST fill:#e3f2fd
    style DS fill:#fff3e0
    style JM fill:#f3e5f5
    style RJR fill:#ffebee
```

**Dependency Rule**: Dependencies point inward (Infrastructure → Domain). Domain has zero external dependencies.

**See**: [backend/ARCHITECTURE.md](./backend/ARCHITECTURE.md) for detailed DDD implementation

---

### Frontend: Feature-Sliced Design (FSD)

**6-Layer Vertical Architecture:**

```mermaid
graph TB
    subgraph "Layer 1: App"
        APP[Providers<br/>Router<br/>Global Styles]
    end

    subgraph "Layer 2: Pages"
        HOME[Home Page]
        DL[Download Page]
    end

    subgraph "Layer 3: Widgets"
        FORM[Video Download Form]
        PROG[Progress Tracker]
        SEL[Format Selector]
    end

    subgraph "Layer 4: Features"
        URL[URL Validation]
        FMT[Format Selection]
        DLMGMT[Download Management]
        TRACK[Progress Tracking]
    end

    subgraph "Layer 5: Entities"
        VIDEO[Video Entity + API]
        JOB[Job Entity + API]
        FORMAT[Format Entity]
    end

    subgraph "Layer 6: Shared"
        UIKIT[UI Components<br/>shadcn/ui]
        UTILS[Utilities]
        APICLIENT[API Client]
    end

    APP --> HOME
    APP --> DL
    HOME --> FORM
    DL --> PROG
    FORM --> URL
    FORM --> SEL
    PROG --> TRACK
    SEL --> FMT
    URL --> VIDEO
    FMT --> FORMAT
    TRACK --> JOB
    VIDEO --> APICLIENT
    JOB --> APICLIENT
    URL --> UIKIT
    PROG --> UIKIT

    style APP fill:#e1f5ff
    style HOME fill:#f3e5f5
    style FORM fill:#fff3e0
    style URL fill:#e8f5e9
    style VIDEO fill:#fce4ec
    style UIKIT fill:#f1f8e9
```

**Import Rule**: Lower layers can only be imported by higher layers. No upward imports.

**Status**: Migration in progress (currently component-based)

**See**: [frontend/ARCHITECTURE.md](./frontend/ARCHITECTURE.md) for FSD migration details

---

### Infrastructure: Terraform Modules

**Module Composition Pattern:**

```mermaid
graph TB
    subgraph "Root Module"
        MAIN[main.tf<br/>Orchestrator]
        BACKEND[backend.tf<br/>Remote State]
        VERSIONS[versions.tf<br/>Constraints]
    end

    subgraph "Compute Module"
        VM[VM Instance]
        STARTUP[Startup Script]
        DOCKER[Docker Setup]
    end

    subgraph "Storage Module"
        BUCKET[GCS Bucket]
        LIFECYCLE[Lifecycle Policy]
        IAM[IAM Bindings]
    end

    subgraph "Network Module"
        VPC[VPC Network]
        SUBNET[Subnets]
        FW[Firewall Rules]
    end

    MAIN --> VM
    MAIN --> BUCKET
    MAIN --> VPC
    VM --> STARTUP
    STARTUP --> DOCKER
    BUCKET --> LIFECYCLE
    BUCKET --> IAM
    VPC --> SUBNET
    VPC --> FW

    style MAIN fill:#e3f2fd
    style VM fill:#fff3e0
    style BUCKET fill:#e8f5e9
    style VPC fill:#fce4ec
```

**See**: [iac/ARCHITECTURE.md](./iac/ARCHITECTURE.md) for Terraform implementation

---

## 🔄 Data Flow

### Download Request Flow

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant API as Flask API
    participant R as Redis
    participant C as Celery Worker
    participant YT as yt-dlp
    participant S as Storage

    U->>FE: Enter YouTube URL
    FE->>API: POST /api/v1/videos/resolutions?url=...
    API->>YT: Fetch video metadata
    YT-->>API: Available formats
    API-->>FE: Format list
    FE->>U: Display format options

    U->>FE: Select format & download
    FE->>API: POST /api/v1/downloads/
    API->>R: Create job record
    API->>C: Queue download task
    API-->>FE: Return job_id

    C->>R: Update status: processing
    C->>YT: Download video
    YT-->>C: Video file
    C->>S: Save file
    C->>R: Update status: completed + token

    FE->>API: Poll GET /api/v1/jobs/{job_id}
    API->>R: Get job status
    API-->>FE: Status + progress

    FE->>API: GET /api/v1/downloads/file/{token}
    API->>S: Retrieve file
    S-->>API: File stream
    API-->>FE: Download file
    FE-->>U: Save to disk

    Note over C,S: After 15 minutes
    C->>S: Delete expired file
    C->>R: Delete job record
```

---

## 🔒 Security Architecture

### Rate Limiting (Production Only)

```mermaid
graph LR
    REQ[Client Request] --> CHECK{Environment?}
    CHECK -->|production| REDIS[Redis Rate Limiter]
    CHECK -->|development| ALLOW[Allow All]

    REDIS --> LIMIT{Within Limit?}
    LIMIT -->|Yes| PROCESS[Process Request]
    LIMIT -->|No| REJECT[HTTP 429<br/>Too Many Requests]

    PROCESS --> UPDATE[Update Counters]
    UPDATE --> RESP[Response + Headers]

    style REDIS fill:#ffebee
    style REJECT fill:#ffcdd2
    style ALLOW fill:#c8e6c9
```

**Limits (per Client IP/Day)**:
- 20 video-without-audio requests
- 20 audio-only requests
- 20 video+audio requests
- 60 total jobs

**Implementation**: Redis-based distributed rate limiting with midnight UTC reset

---

## 🗄️ Data Storage Strategy

### Development vs Production

| Aspect | Development | Production |
|--------|-------------|------------|
| **File Storage** | Local filesystem (`/data/downloads`) | Google Cloud Storage |
| **Job State** | Redis (ephemeral) | Redis (persistent) |
| **Rate Limiting** | Disabled | Enabled (Redis-based) |
| **WebSocket** | Optional | Optional |
| **File Retention** | 15 minutes | 15 minutes |

### Storage Abstraction

```mermaid
graph TB
    APP[Application Layer] --> IFACE[IFileRepository<br/>Interface]

    IFACE -.->|implements| LOCAL[LocalFileRepository]
    IFACE -.->|implements| GCS[GCSRepository]

    LOCAL --> FS[Local Filesystem<br/>/data/downloads]
    GCS --> BUCKET[GCS Bucket<br/>ultra-dl-files]

    ENV{GCS_ENABLED?} -->|false| LOCAL
    ENV -->|true| GCS

    style IFACE fill:#f3e5f5
    style LOCAL fill:#e8f5e9
    style GCS fill:#e3f2fd
```

---

## 📊 Service Dependencies

### Backend Dependencies
- **Flask** 3.1.2 - REST API framework
- **Celery** 5.5.3 - Background task queue
- **Redis** 7.0.1 - Cache + message broker
- **yt-dlp** - YouTube video downloader
- **Flask-SocketIO** 5.4.2 - WebSocket support (optional)
- **Flask-RESTX** 1.3.0 - Swagger/OpenAPI docs

### Frontend Dependencies
- **React** 18.3.1 - UI framework
- **TypeScript** 5.9.3 - Type safety
- **Vite** 5.4.21 - Build tool
- **TanStack Query** 5.90.7 - Server state management
- **shadcn/ui** - Component library
- **Tailwind CSS** 3.4.17 - Utility-first CSS

### Infrastructure
- **Docker** + Docker Compose - Local development
- **Terraform** - Infrastructure as Code
- **GCP Compute Engine** - Production VM
- **GCP Cloud Storage** - File storage
- **Nginx** - Reverse proxy

---

## 🔗 Related Documentation

- **[Backend Architecture](./backend/ARCHITECTURE.md)** - DDD implementation details
- **[Frontend Architecture](./frontend/ARCHITECTURE.md)** - FSD migration guide
- **[IaC Architecture](./iac/ARCHITECTURE.md)** - Terraform module structure
- **[README.md](./README.md)** - Project overview and quick start
