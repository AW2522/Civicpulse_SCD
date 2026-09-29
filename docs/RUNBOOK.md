# RUNBOOK — CivicPulse Operations

## 1. Deploy Procedures

### 1.1 Local & Dev (Docker Compose)
To stand up the full stack locally with hot-reload, seeded PostgreSQL database, and Redis cache:
```bash
cp .env.example .env        # ensure POSTGRES_PASSWORD is set
docker compose -f compose.yaml up --build -d
```
Verify readiness:
```bash
curl -fs http://localhost:8000/ready
# Expected: {"status":"ready","postgres":"connected","redis":"connected"}
```
Access endpoints:
- Frontend: http://localhost:5173
- Backend API Docs: http://localhost:8000/docs
- Health Probes: http://localhost:8000/health (liveness), http://localhost:8000/ready (readiness)

### 1.2 Kubernetes Production Overlay (Automated & Manual)
**Automated CD**: Push to `main` triggers `.github/workflows/cd.yml`, which builds images tagged by commit SHA, publishes to GHCR, patches `k8s/overlays/prod`, and applies manifests.

**Manual Deployment to Kubernetes (k3d / kind / cloud cluster)**:
```bash
cd k8s/overlays/prod
kustomize edit set image \
  ghcr.io/REPLACE_OWNER/civicpulse-backend=ghcr.io/<owner>/civicpulse-backend:<sha> \
  ghcr.io/REPLACE_OWNER/civicpulse-frontend=ghcr.io/<owner>/civicpulse-frontend:<sha>

kustomize build . | kubectl apply -f -

kubectl -n civicpulse rollout status deployment/backend
kubectl -n civicpulse rollout status deployment/frontend
```

---

## 2. Rollback Procedures

### 2.1 Fast Rollback (Incident Response — 3 a.m. Procedure)
Use Kubernetes imperative rollback when immediate mitigation is required:
```bash
kubectl -n civicpulse rollout undo deployment/backend
kubectl -n civicpulse rollout undo deployment/frontend
```

### 2.2 Declarative Rollback (Auditable / Post-Incident Procedure)
Once the incident is mitigated, restore the declarative state in Git by reapplying the previous known-good commit SHA:
```bash
PREV_SHA="<previous-stable-git-sha>"
cd k8s/overlays/prod
kustomize edit set image \
  ghcr.io/REPLACE_OWNER/civicpulse-backend=ghcr.io/<owner>/civicpulse-backend:${PREV_SHA} \
  ghcr.io/REPLACE_OWNER/civicpulse-frontend=ghcr.io/<owner>/civicpulse-frontend:${PREV_SHA}

kustomize build . | kubectl apply -f -
```

---

## 3. Reading Logs & Request Tracing

All backend and frontend services log structured JSON to `stdout`:

```bash
# Docker Compose logs
docker compose logs -f backend
docker compose logs -f frontend

# Kubernetes Pod logs
kubectl -n civicpulse logs -f deployment/backend
kubectl -n civicpulse logs -f deployment/frontend

# View logs from a previous crashed container instance
kubectl -n civicpulse logs -f deployment/backend --previous
```

### 3.1 Distributed Request Tracing
Every HTTP request generates or propagates a unique `request_id` via the `X-Request-ID` header.
To trace a specific request across backend log streams:
```bash
kubectl -n civicpulse logs deployment/backend | grep "req_abc123"
```

---

## 4. Triage Failure Playbook

When automated AI complaint triage starts degrading or failing:

### Step 1: Check Provider Health & Fallback Rate
Inspect the provider metadata endpoint:
```bash
curl -s http://localhost:8000/api/meta/providers | jq .
```
Look for `fallback: true` in recent outcomes. If the fallback rate rises above 20%, an upstream LLM issue is occurring.

### Step 2: Inspect Error Logs
Search backend logs for structured fallback warnings:
```bash
kubectl -n civicpulse logs deployment/backend | grep "WARNING" | grep "fallback"
```
Identify the failure reason:
- `HTTP 429 Too Many Requests`: Upstream LLM rate limit exceeded.
- `TimeoutError (10s)`: Upstream LLM latency degradation.
- `JSONDecodeError` or `ValidationError`: Model hallucinated invalid schema.

### Step 3: Switch Active Triage Provider
If the primary LLM provider (Groq/Gemini) is exhausted, switch to local Ollama or rule-based fallback without downtime:
```bash
# Option A: In Kubernetes via ConfigMap
kubectl -n civicpulse patch configmap civicpulse-config --type merge -p '{"data":{"TRIAGE_PROVIDER":"rules"}}'
kubectl -n civicpulse rollout restart deployment/backend

# Option B: In Docker Compose
# Edit .env: TRIAGE_PROVIDER=rules
docker compose -f compose.yaml up -d backend
```

### Step 4: Verify Fallback Invariance
Confirm intake endpoints continue returning HTTP 201 with `"triaged_by": "rules:fallback"`:
```bash
curl -s -X POST http://localhost:8000/api/complaints \
  -H "Content-Type: application/json" \
  -d '{"text":"Gutter overflow and water supply disruption","location":"Block 4"}' | jq .
```
*Expected Result*: Status 201, `category: "water"`, `priority: "high"`, `triaged_by: "rules:fallback"`.

### Step 5: Verify CI Independence
Ensure that CI pipeline configurations (`ci.yml`) strictly use `TRIAGE_PROVIDER=simulated` so automated builds never depend on external API keys or network availability.
