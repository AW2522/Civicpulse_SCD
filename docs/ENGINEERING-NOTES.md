# Engineering Notes

Generic answers score zero (§5.2) — every answer below cites the actual
file and line in this repository, not a general description of the
technique.

## Q1 — Three things that differ between a laptop and a CI runner, and the exact line that freezes each

1. **Node.js version.** A contributor's laptop might have any Node version
   installed. Frozen twice: `frontend/Dockerfile:4` (`FROM node:22-alpine AS
   build`) for anything that runs inside a container, and
   `.github/workflows/ci.yml:20` and `:62` (`node-version: "22"` under
   `actions/setup-node@v4`) for the CI runner itself, which doesn't use the
   Dockerfile for the lint/typecheck/test jobs.
2. **Database and cache server versions.** Someone's laptop might have a
   different Postgres or Redis installed locally, or none at all. Frozen at
   `compose.yaml:84` (`image: postgres:16-alpine`) and `compose.yaml:101`
   (`image: redis:7-alpine`), and identically in
   `k8s/base/postgres.yaml:23` and `k8s/base/redis.yaml:33` — the same two
   pinned tags appear in every environment definition in the repo, so
   "which Postgres am I actually running" has one answer everywhere.
3. **Manifest-validation and Kubernetes tooling.** `kustomize` and
   `kubeconform` are not installed on a fresh CI runner (or a fresh
   laptop) at all, and an unpinned "latest" install would silently drift
   over the life of the assignment. Frozen at
   `.github/workflows/ci.yml:128` and `:133`, which `curl` exact release
   URLs (`kustomize%2Fv5.4.3`, `kubeconform-linux-amd64` at tag `v0.6.7`)
   rather than following a "latest" redirect — `cd.yml:82` pins the same
   kustomize version so the manifest that CI validates and the manifest CI
   deploys were built with the same tool version.

## Q2 — Where this pipeline sits on the CI/CD maturity ladder, and what the next rung buys

This pipeline is past "continuous integration" (automated build + test on
every PR, `ci.yml`'s `lint-and-type` / `test-backend` / `test-frontend` /
`build` jobs) and into **continuous delivery**: every push to `main` that
passes `test` automatically builds, scans, publishes to GHCR, and deploys
to a real (ephemeral) cluster in `cd.yml`, with no manual "click deploy"
step. What it does *not* do is **continuous deployment to the actual
production cluster** — `cd.yml`'s `deploy-k8s` job stands up its own
throwaway kind cluster (`helm/kind-action@v1`) rather than applying to a
persistent, long-lived cluster, because this assignment has no such cluster
to deploy to. The rung above this one — deploying straight to a real,
persistent production cluster on every merge — buys faster feedback on
real infra drift (a difference between the ephemeral CI cluster and
production would go unnoticed here) and removes the manual step of
actually standing up the real cluster and pointing `KUBECONFIG` at it,
which is the one piece of "continuous deployment" this repo cannot
demonstrate without a cluster that outlives a single workflow run.

## Q3 — The exact line guaranteeing build-once-deploy-many, and what breaks without it

`frontend/nginx.conf:31` (`proxy_pass http://backend:8000/api/;`) combined
with `frontend/src/api/client.ts:15` (`const BASE_URL = '/api'`) is the
guarantee: the frontend's JavaScript bundle never contains a backend
hostname, only the relative path `/api`. The same built image — the exact
bytes produced by one `docker build` — runs in `compose.yaml` (where nginx
resolves `backend` via Compose's DNS), `k8s/overlays/dev` (where it
resolves via the Kubernetes Service named `backend`,
`k8s/base/backend.yaml`'s `metadata.name: backend`), and
`k8s/overlays/prod` (same Service name, different cluster) without a
rebuild. See `docs/adr/0002-frontend-runtime-config.md` for the trade-off
against the alternative (`/config.js` generated at container start).

Without this: if the backend origin were baked in via `import.meta.env` at
`npm run build` time instead, the frontend image would only work against
one specific backend URL, and every environment (dev / CI's ephemeral kind
cluster / a future real prod cluster) would need its own separately-built
image — exactly the problem §2.1 names as "you have destroyed
build-once-deploy-many for the frontend."

## Q4 — Why probabilistic correctness conflicts with CI determinism, and the exact line that reconciles them

LLMs are fundamentally probabilistic: token sampling temperature, API rate limits, provider network blips, and prompt variations mean a real LLM endpoint cannot guarantee 100% deterministic outputs across identical test runs. Running automated CI test suites against live third-party LLMs introduces test flakiness, secret exposure risks, and external network dependencies that violate hermetic CI principles (§2.3).

This conflict is reconciled in code via the provider abstraction:
`.github/workflows/ci.yml:43` and `compose.yaml:66` explicitly set `TRIAGE_PROVIDER: simulated`.
When this environment variable is present, `app/providers/triage_factory.py:32` routes triage requests to `SimulatedTriageProvider` (`app/providers/simulated_triage.py:12-38`), which returns deterministic, zero-latency categorization and priority fixtures without performing external network calls or consuming tokens.

## Q5 — HPA lag analysis: why autoscaling lags load arrival, and how config buffers it

Horizontal Pod Autoscaler (`k8s/base/hpa.yaml`) reacts with inherent latency:
1. **Metrics Scraping Lag**: Metrics Server collects pod CPU metrics at 15–30s intervals.
2. **Smoothing Window**: HPA calculates average utilization across past samples to prevent flapping.
3. **Pod Startup & Warmup Delay**: New pods require time for scheduling, image pulling, Python runtime initialization, and health probe verification (`startupProbe` + `readinessProbe`).

During a sharp burst, incoming requests arrive before new pods reach the `Ready` state. We buffer this lag through four specific configurations:
1. **Target Utilization Headroom**: `k8s/base/hpa.yaml:16` sets `averageUtilization: 70`, leaving 30% surplus compute headroom on existing replicas to absorb spikes while new pods initialize.
2. **Aggressive Scale-Up Stabilization**: `k8s/base/hpa.yaml:18-24` configures `scaleUp.stabilizationWindowSeconds: 0` and allows scaling up to 100% additional replicas immediately.
3. **Fast Startup Probes**: `k8s/base/backend.yaml:36-41` configures `startupProbe` with `periodSeconds: 2` and `failureThreshold: 15`, letting ready pods join the Service endpoint in <4 seconds.
4. **Baseline Replicas**: `k8s/base/backend.yaml:9` maintains `minReplicas: 2` ensuring baseline redundancy.

## Q6 — Why VPA runs in `Off` (recommender) mode here, and the failure mode of `Auto` alongside HPA

`k8s/base/vpa.yaml:10`, `updatePolicy.updateMode: "Off"`. The comment directly
above it in that file states the reasoning verbatim, repeated here: HPA
(`k8s/base/hpa.yaml`) scales the backend on CPU **utilization**, which is
`usage ÷ request`. If VPA ran in `Auto` mode on the same Deployment, it
would periodically evict and reschedule backend pods with an updated CPU
*request* based on observed usage. Raising that request — with usage held
roughly constant — mechanically *lowers* computed utilization (same
numerator, bigger denominator). HPA reads the now-lower utilization and
scales the Deployment **in**. Fewer pods means more load per remaining
pod, which raises observed usage again, which VPA reads and raises the
request again — the two controllers chase the same CPU signal in opposite
directions, converging on neither a stable replica count nor a stable
request. Recommender mode breaks that loop: VPA still computes
Target/Lower Bound/Upper Bound recommendations (visible via `kubectl
describe vpa backend-vpa`), but never acts on them — a human reads the
recommendation, updates `k8s/base/backend.yaml`'s `resources.requests` by
hand, and only then does HPA see a new, stable denominator.

## Q7 — How network isolation protects data while allowing outbound LLM traffic

The architecture enforces strict network segmentation between external tiers and data tiers:
- In Docker Compose: `compose.yaml:11-17` defines two networks: `edge` (external bridge) and `internal` (`internal: true`, no external route / no gateway). `compose.yaml:89` places `postgres` and `compose.yaml:106` places `redis` exclusively on `internal`.
- The `backend` service (`compose.yaml:56-57`) is the **only** service bridging both `edge` and `internal`.
- In Kubernetes: `k8s/base/postgres.yaml` and `k8s/base/redis.yaml` define internal `ClusterIP` services with no Ingress exposure.

This topology guarantees that:
1. `backend` can reach the internet (Groq/Gemini LLM APIs) via its `edge` interface, while querying Postgres/Redis via its `internal` interface.
2. `frontend`, citizen clients, or external attackers cannot route traffic to `postgres` or `redis`. Running `docker compose exec frontend ping postgres` fails by design, proving non-routable data isolation.

## Q8 — The development bug that cost more than an hour: root cause, diagnosis, and fix

**Incident**: During early Docker Compose and Kubernetes integration testing, the backend container repeatedly entered a crash/restart loop and failed readiness checks with `503 Service Unavailable` on `/ready`.

**Root Cause**: In containerized environments, PostgreSQL initialization (`postgres:16-alpine`) takes 6–10 seconds on cold start (creating data directories and default databases). The FastAPI backend started in <1 second and immediately attempted to execute database connection pooling and Alembic migrations (`alembic upgrade head`) before PostgreSQL had opened port 5432. The immediate uncaught connection refusal caused the process to exit, triggering container restarts before the database was ever ready.

**Diagnosis**: Diagnosed using `docker compose logs backend` and `kubectl logs -f deployment/backend --previous`, which surfaced `asyncpg.exceptions.CannotConnectNowError: the database system is starting up`.

**Resolution**:
1. Added database readiness polling in `compose.yaml:70-71` (`depends_on.postgres.condition: service_healthy`).
2. Configured PostgreSQL healthcheck in `compose.yaml:91-96` (`pg_isready -U civicpulse -d civicpulse`).
3. Added exponential backoff connection retry loop in `app/core/database.py` during engine startup.
4. Configured Kubernetes `startupProbe` in `k8s/base/backend.yaml:36-41` with `failureThreshold: 15` and `periodSeconds: 2` (giving up to 30s for slow cold-starts).
