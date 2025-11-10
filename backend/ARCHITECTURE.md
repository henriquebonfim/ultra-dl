# UltraDL Backend — Architecture (diagrams)

Below are two Mermaid diagrams summarizing the backend architecture: a high-level component diagram and a layer/component mapping that shows where to find key files.

### High-level architecture

```mermaid
graph TB
   subgraph Frontend
      UI[React UI]
      WS[WebSocket Client]
   end

   subgraph Backend
      API[Flask API]
      SIO[Socket.IO]
   end

   subgraph Processing
      CW[Celery Workers]
      CB[Celery Beat]
   end

   subgraph Storage
      Redis[(Redis)]
      FS[Local FS]
      GCS[Google Cloud Storage]
   end

   UI -->|HTTP/REST| API
   UI -->|WebSocket| SIO
   API -->|enqueue jobs| CW
   API -->|read/write state| Redis
   CW -->|download & progress| Redis
   CW -->|store files| FS
   CW -->|store files| GCS
   CW -->|broadcast progress| SIO
   CB -->|schedule cleanup| CW

   style UI fill:#e6f7ff
   style API fill:#fff4e1
   style CW fill:#fff0f0
   style Redis fill:#f5e1ff
```

### Layer & component map

```mermaid
flowchart LR
    subgraph Domain
        DM["domain/*<br/>(entities, VOs, interfaces)"]
    end

    subgraph Application
        AS["application/*<br/>(use-case services)"]
    end

    subgraph API
        AP["api/v1/*<br/>(controllers, DTOs)"]
    end

    subgraph Infrastructure
        IR["infrastructure/*<br/>(redis, gcs adapters)"]
    end

    subgraph Tasks
        TK["tasks/*<br/>(celery tasks)"]
    end

    Redis[(Redis)]
    GCS[(GCS)]

    %% Relationships
    AP --> AS
    AS --> DM
    AS --> IR
    TK --> DM
    TK --> IR
    IR --> Redis
    IR --> GCS
    AP --> IR

    %% Clickable links
    click DM "./backend/domain/" "Open domain folder"
    click AS "./backend/application/" "Open application folder"
    click AP "./backend/api/v1/" "Open api/v1 folder"
    click IR "./backend/infrastructure/" "Open infrastructure folder"
    click TK "./backend/tasks/" "Open tasks folder"

```

### Captions & quick notes

- Entry point: `backend/main.py` — wires infra (Redis, Celery, optional Socket.IO, GCS), constructs repos and services, and registers the API blueprint.
- Recommended improvement: introduce `create_app(config=None)` as the composition root for cleaner tests and easier wiring.
- Where to look first: `backend/main.py`, `backend/api/v1/namespaces.py`, `backend/domain/job_management/`, `backend/application/job_service.py`, `backend/tasks/download_task.py`.

If you'd like, I can produce a PNG/SVG of these diagrams or add a 1-line run command under each diagram for convenience.
