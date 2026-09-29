# CivicPulse

[![CI Pipeline](https://github.com/AW2522/Civicpulse_SCD/actions/workflows/ci.yml/badge.svg)](https://github.com/AW2522/Civicpulse_SCD/actions/workflows/ci.yml)
[![Docker](https://img.shields.io/badge/Docker-24.0+-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.29+-326CE5?logo=kubernetes&logoColor=white)](https://kubernetes.io/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-8.3-646CFF?logo=vite&logoColor=white)](https://vite.dev/)

> **CS4032 — Software Construction and Design, Assignment 01**  
> Municipal complaint intake, automated AI triage, telemetry monitoring, and operations platform.

---

## 1. Problem Statement

Municipal governance authorities face significant bottlenecks when triaging high volumes of citizen complaints across bilingual contexts (Urdu, Roman Urdu, and English). Citizens often submit critical infrastructure reports (e.g. burst water mains, sparking power lines, open sewer manholes, damaged roads) with variable detail, resulting in delayed prioritization and lack of structured operations telemetry.

**CivicPulse** is a resilient, cloud-native municipal operations console that:
1. Provides an accessible, responsive Single Page Application (SPA) for citizen complaint intake and operator telemetry dashboards.
2. Performs automated, real-time AI classification (Category, Priority, and English Summary) via Groq LLMs (`llama-3.3-70b-versatile`) and Google Gemini.
3. Guarantees zero-downtime high availability through an instant deterministic rule-based fallback heuristic when LLM providers fail or encounter rate limits (HTTP 429).
4. Enforces strict zero-trust network segmentation (isolating PostgreSQL and Redis on non-routable internal networks).
5. Implements continuous delivery with commit-SHA tagged container images, Kustomize overlays, HPA autoscaling, and automated health probing.

---

## 2. Architecture

```mermaid
flowchart TD
    Citizen([Citizen / Browser]) -->|HTTP :5173 / :80| Ingress[Nginx Ingress / Frontend SPA]
    
    subgraph Edge Network ["edge network (Public Bridge)"]
        Ingress -->|/api reverse proxy| Backend[FastAPI Backend Application]
        Backend -->|Outbound HTTPS| GroqLLM[Groq / Gemini AI Provider]
    end

    subgraph Internal Network ["internal network (Isolated & Non-Routable)"]
        Backend -->|Async SQLAlchemy / Port 5432| Postgres[(PostgreSQL 16 · Data Layer)]
        Backend -->|Redis Protocol / Port 6379| Redis[(Redis 7 · Cache & Rate Limit)]
    end

    subgraph Triage Engine ["Triage Fallback Engine"]
        Backend --> TriageFactory{TriageFactory}
        TriageFactory -->|Primary (10s timeout + retry)| GroqLLM
        TriageFactory -->|Fallback on 429/Timeout| RuleFallback[Rule-Based Heuristic Triage]
    end
```

---

## 3. Quickstart (One-Command Setup)

### 3.1 Local Development (Docker Compose)
```bash
# 1. Clone repository
git clone https://github.com/AW2522/Civicpulse_SCD.git
cd Civicpulse_SCD

# 2. Configure environment
cp .env.example .env        # Set POSTGRES_PASSWORD at minimum

# 3. Start the entire stack with hot reload & seeded data
make dev                    # Equivalent to: docker compose -f compose.yaml up --build
```

### 3.2 Verification Endpoints
- **Frontend SPA**: [http://localhost:5173](http://localhost:5173)
- **Backend API Interactive Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Liveness Health Probe**: [http://localhost:8000/health](http://localhost:8000/health)
- **Readiness Dependency Probe**: [http://localhost:8000/ready](http://localhost:8000/ready)

### 3.3 Make Shortcut Commands
```bash
make test         # Runs backend pytest + frontend vitest suites
make lint         # Runs ruff, mypy, and eslint linters
make check        # Runs scripts/check_submission.py linter
make k8s-dev-up   # Deploys manifests to local k3d / kind cluster
make load-test    # Executes k6 load testing suite (load/k6-script.js)
```

### 3.4 End-to-End Integration Run Instructions
To run and verify full-stack integration locally:

1. **Environment Setup**:
   ```bash
   cp .env.example .env
   ```
2. **Start Backend & Infrastructure Stack**:
   ```bash
   docker compose -f compose.yaml up -d --build
   ```
3. **Launch Frontend Development Server**:
   ```bash
   cd frontend
   npm ci
   npm run dev
   ```
4. **Verify Application Connectivity**:
   - Frontend SPA Interface: [http://localhost:5173](http://localhost:5173)
   - Backend API Interactive Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Service Readiness Health Check: [http://localhost:8000/ready](http://localhost:8000/ready)


---

## 4. API Endpoints Specification

| Method | Endpoint | Description | Request Body | Response Codes |
|---|---|---|---|---|
| `POST` | `/api/complaints` | Submit citizen complaint and trigger AI triage | `ComplaintSubmissionForm` (`text`, `location`, `reporter_contact`) | `201 Created`, `400 Bad Request`, `429 Rate Limited` |
| `GET` | `/api/complaints` | List paginated complaints with category/priority filters | Query params: `category`, `priority`, `status`, `page`, `page_size` | `200 OK` (`Paginated<Complaint>`) |
| `GET` | `/api/complaints/{id}` | Get detailed complaint by ID | None | `200 OK`, `404 Not Found` |
| `PATCH`| `/api/complaints/{id}/status` | Transition complaint status | `ComplaintUpdateStatusRequest` (`status`) | `200 OK`, `400 Bad Request`, `409 Conflict` |
| `GET` | `/api/stats` | Aggregated category and priority counts with cache telemetry | None | `200 OK` (includes `X-Cache: HIT/MISS`) |
| `GET` | `/api/meta/providers`| Triage provider status and latency history | None | `200 OK` (`ProvidersMeta`) |
| `GET` | `/health` | Kubernetes container liveness probe | None | `200 OK` (`{"status":"ok"}`) |
| `GET` | `/ready` | Kubernetes readiness probe (Postgres + Redis check) | None | `200 OK`, `503 Service Unavailable` |
| `GET` | `/metrics` | Prometheus metrics scrape endpoint | None | `200 OK` (Prometheus exposition format) |

---

## 5. Architectural Decision Records (ADRs)

Detailed rationale behind foundational architecture choices:
- [ADR 0001: AI Triage Provider Protocol & Fallback Architecture](docs/adr/0001-provider-interface.md)
- [ADR 0002: Frontend Runtime Configuration & Reverse Proxy](docs/adr/0002-frontend-runtime-config.md)
- [ADR 0003: Immutable Deploy-by-SHA Container Tagging](docs/adr/0003-deploy-by-sha.md)
- [ADR 0004: PII Isolation & Prompt Injection Guardrails](docs/adr/0004-pii-data-governance.md)

---

## 6. Running on Kubernetes (k3d / kind)

```bash
# Build container images
docker build -t civicpulse-frontend:dev ./frontend
docker build -t civicpulse-backend:dev ./backend

# Create cluster and import images
k3d cluster create civicpulse-dev --agents 1
k3d image import civicpulse-frontend:dev civicpulse-backend:dev -c civicpulse-dev

# Apply Kustomize overlay
kubectl apply -k k8s/overlays/dev
kubectl -n civicpulse get pods,svc,hpa -w
```

---

## 7. Operations & Demo

- **Operations Runbook**: See [docs/RUNBOOK.md](docs/RUNBOOK.md) for deploy, rollback, log aggregation, and triage failure response playbooks.
- **Engineering Notes**: See [docs/ENGINEERING-NOTES.md](docs/ENGINEERING-NOTES.md) for in-depth answers to Section 5.2 questions with line-level citations.
- **Demo Video Script**: See [docs/DEMO_VIDEO_SCRIPT.md](docs/DEMO_VIDEO_SCRIPT.md) for the timed 5-minute video walkthrough script.

---

## 8. Team Responsibilities

| Area | Lead Owner | Artifacts & Scope |
|---|---|---|
| **Backend & AI Architecture** | Person 1 | FastAPI app, Triage Provider Protocol, Groq/Gemini integration, SQLAlchemy models, Alembic migrations, Redis caching, Rate limiter. |
| **Frontend & DevOps Infrastructure** | Person 2 | React/Vite SPA, ErrorBoundary, Nginx reverse proxy, Multi-stage Dockerfiles, Kubernetes manifests & Kustomize overlays, GitHub Actions CI/CD pipelines, Submission linter. |
