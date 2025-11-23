# UltraDL - AI Agent Guidelines

> **Purpose**: Root-level guidelines for AI assistants working across the entire project. For service-specific agent guidelines, see AGENTS.md in each service folder.

---

## 🎯 Project Context

**Ultra YouTube Downloader** is a minimalist web-based YouTube video/audio downloader with:
- **Backend**: Domain-Driven Design (DDD) with Flask + Celery
- **Frontend**: Feature-Sliced Design (FSD) with React + TypeScript
- **Infrastructure**: Terraform modules for GCP

**Key Constraints**:
- Anonymous access only (no authentication)
- Single URL downloads for frontend (batch only via API)
- 5-minute file retention
- Production-only rate limiting
- WSL2 + Docker development environment

---


## 🧭 Core Development Principles

**Backend (DDD)**:
- ✅ Domain layer has ZERO external dependencies
- ✅ Dependencies point inward (Infrastructure → Domain)
- ✅ Use repository pattern for all data access
- ✅ Publish domain events, don't call infrastructure directly

**Frontend (FSD)**:
- ✅ Respect layer hierarchy: app → pages → widgets → features → entities → shared
- ✅ No upward imports (lower layers cannot import higher layers)
- ✅ Features are self-contained with public API (index.ts exports)
- ✅ No feature-to-feature imports (use shared layer)

**IaC (Terraform)**:
- ✅ Use module composition (root module + child modules)
- ✅ Remote state with locking (GCS backend)
- ✅ Validate all input variables
- ✅ Document all outputs clearly


## 📐 Documentation Structure

This project follows a **hierarchical documentation pattern**:

```
root/
├── architecture.md       ← System-wide architecture (you are here)
├── agents.md            ← Root-level AI guidelines (this file)
├── README.md            ← Project overview
├── todo.md              ← Consolidated task tracker
│
├── backend/
│   ├── ARCHITECTURE.md  ← Backend DDD details
│   ├── AGENTS.md        ← Backend-specific AI guidelines
│   ├── README.md        ← Backend service overview
│   └── todo.md          ← Backend-specific tasks
│
├── frontend/
│   ├── ARCHITECTURE.md  ← Frontend FSD details
│   ├── AGENTS.md        ← Frontend-specific AI guidelines
│   ├── README.md        ← Frontend service overview
│   └── todo.md          ← Frontend-specific tasks
│
└── iac/
    ├── ARCHITECTURE.md  ← Terraform module structure
    ├── AGENTS.md        ← IaC-specific AI guidelines
    ├── README.md        ← Infrastructure overview
    └── todo.md          ← IaC-specific tasks
```

**Navigation Rule**: Always start here, then drill down to service-specific documentation.

---
