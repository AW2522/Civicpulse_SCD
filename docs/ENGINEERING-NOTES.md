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

## Q6 — Why VPA runs in `Off` (recommender) mode here, and the failure mode of `Auto` alongside HPA

`k8s/base/vpa.yaml`, `updatePolicy.updateMode: "Off"`. The comment directly
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

---

*Q4 (probabilistic correctness / CI determinism), Q5 (HPA lag analysis),
Q7 (internal network vs. hosted LLM) and Q8 (the failure that cost more
than an hour) are Person 1's / joint, and need real measurements this
sandbox can't produce (a live triage run, a real load-test capture, an
actual production incident) — still to be filled in once the system is
actually running end to end.*
