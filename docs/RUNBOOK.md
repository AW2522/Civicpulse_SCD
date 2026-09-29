# RUNBOOK

## Deploy

**Compose (local/dev):**
```bash
docker compose -f compose.yaml up --build -d
```

**Kubernetes (prod overlay, from CI):** happens automatically in `cd.yml`
on every push to `main` — it builds, pushes to GHCR tagged by commit SHA,
patches `k8s/overlays/prod` to point at that SHA, and applies it to the
cluster. To do the same thing by hand against a real cluster:

```bash
cd k8s/overlays/prod
kustomize edit set image \
  ghcr.io/REPLACE_OWNER/civicpulse-backend=ghcr.io/<owner>/civicpulse-backend:<sha> \
  ghcr.io/REPLACE_OWNER/civicpulse-frontend=ghcr.io/<owner>/civicpulse-frontend:<sha>
kustomize build . | kubectl apply -f -
kubectl -n civicpulse rollout status deployment/backend
kubectl -n civicpulse rollout status deployment/frontend
```

## Roll back

Two mechanisms — use the fast one during an incident, the declarative one
once things are stable:

**Fast (the 3 a.m. answer):**
```bash
kubectl -n civicpulse rollout undo deployment/backend
kubectl -n civicpulse rollout undo deployment/frontend
```

**Declarative (the correct answer once the fire is out):** re-run the
deploy steps above with the previous commit's SHA instead of the current
one. This is auditable — the manifest applied is exactly what was applied
before, not "whatever `rollout undo` happened to restore."

## Read logs

All services log structured JSON to stdout (never to a file — container
filesystems are ephemeral):

```bash
# Compose
docker compose logs -f backend

# Kubernetes
kubectl -n civicpulse logs -f deployment/backend
kubectl -n civicpulse logs -f deployment/backend --previous   # after a restart
```

Every backend log line carries a `request_id` propagated from the
`X-Request-ID` header — grep by it to follow one request across the stack.

## When triage starts failing

1. Check `GET /api/meta/providers` — it names the active provider and the
   last 20 outcomes (provider, latency, fallback y/n). A rising
   `fallback: true` rate is the first signal.
2. Check for a `WARNING` log line with the complaint id, provider, and
   error class — one is logged per triage fallback.
3. If the active provider is `llm` and it's a free-tier rate limit: either
   wait it out, or switch `TRIAGE_PROVIDER` to `ollama` (no external
   dependency, no rate limit) via the ConfigMap and roll the backend
   Deployment.
4. Regardless of cause, `POST /api/complaints` should keep returning 201
   with `triaged_by: "rules:fallback"` — if it's returning 5xx instead,
   that's the actual incident (the fallback itself is broken), not the LLM
   provider being unavailable.
5. Confirm `TRIAGE_PROVIDER=simulated` is used in CI (`ci.yml`) — CI must
   never depend on a live LLM provider's availability.
