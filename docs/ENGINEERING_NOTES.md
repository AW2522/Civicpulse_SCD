# CivicPulse Engineering Notes & Architectural Overview

## 1. 4-Layer Architecture Separation
- **Presentation / Routes (`app/routes/`)**: Pure HTTP request validation, status code mapping, and response serialization. Contains zero raw SQL queries or business logic.
- **Service Layer (`app/services/`)**: Business rule orchestration, state machine transition matrix enforcement, and Redis cache invalidation.
- **Repository Layer (`app/repositories/`)**: Encapsulates 100% of PostgreSQL ORM queries (`select`, `func.count`, composite index queries).
- **Domain Layer (`app/models/`, `app/schemas/`)**: SQLAlchemy 2.0 ORM models and Pydantic validation schemas.

## 2. Status Transition State Machine
Enforces strict lifecycle progression:
- `open` $\rightarrow$ `in_progress`, `resolved`, `rejected`
- `in_progress` $\rightarrow$ `resolved`, `rejected`
- Terminal states: `resolved`, `rejected`
- Invalid transitions (e.g., `resolved` $\rightarrow$ `open`) return HTTP 409 Conflict with detailed error messages.

## 3. High Performance & Caching
- **Stats Read-Through Cache**: `GET /api/stats` leverages Redis with 30s TTL and returns header `X-Cache: HIT|MISS`.
- **Write Invalidation**: `POST /api/complaints` and `PATCH /api/complaints/{id}/status` instantly invalidate `stats_cache` in Redis.
- **Rate Limiting**: IP-based fixed-window rate limiter (5 requests/60s) returning HTTP 429 and `Retry-After` header.

## 4. Observability & Health Probes
- **Liveness (`GET /health`)**: Static 200 OK without touching DB or Redis.
- **Readiness (`GET /ready`)**: Active connectivity checks for Postgres and Redis; returns HTTP 503 if any dependency is unhealthy.
- **Prometheus Exporter (`GET /metrics`)**: Exposes request rates, latencies, and triage fallback counters in standard text format.
