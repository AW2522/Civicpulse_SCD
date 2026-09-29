# backend/ — Person 1's territory

This directory is intentionally empty except for this note. Everything
outside it (frontend/, compose.yaml, compose.prod.yaml, k8s/, .github/)
assumes the following contract — please flag early if any of it needs to
change, since several other files reference these exact values:

- **Listens on port 8000** inside the container (`compose.yaml`,
  `k8s/base/backend.yaml` both hard-code this).
- **`GET /health`** — liveness only, must not touch the database.
- **`GET /ready`** — 200 only if Postgres and Redis are both reachable,
  503 otherwise.
- **Reads config from environment variables**, not a single pre-built
  connection string:
  - `POSTGRES_HOST`, `POSTGRES_DB`, `POSTGRES_USER` (from a ConfigMap /
    plain env in Compose) + `POSTGRES_PASSWORD` (from a Secret) — please
    assemble `DATABASE_URL` from these yourself rather than expecting one
    pre-built value; Kubernetes can't interpolate a Secret and a ConfigMap
    into a single env var, so `k8s/base/backend.yaml` passes them
    separately.
  - `REDIS_URL` (already a complete URL — no secret component).
  - `TRIAGE_PROVIDER`, `GROQ_API_KEY` (optional, for the `llm` provider).
- **A `Dockerfile`** in this directory, multi-stage, non-root, matching
  the pattern in `frontend/Dockerfile` — `compose.yaml` and `cd.yml` both
  build from `context: backend`.
- **API responses include the `X-Cache` header** on `GET /api/stats`
  (`HIT`/`MISS`) and a `Retry-After` header on 429s — the frontend
  (`src/api/client.ts`, `src/pages/Stats.tsx`) reads both.

See the full contract in the assignment PDF §2.2–2.3 for everything else
(status codes, the state machine, the ten endpoints).
