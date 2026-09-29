# ADR 0002: Frontend runtime configuration

## Status
Accepted

## Context
Vite bakes every `import.meta.env` value into static JavaScript at build
time. If the backend's origin were one of those values, the resulting image
would only work against one environment, and rebuilding per environment
breaks build-once-deploy-many for the frontend (assignment §2.1).

Two ways to avoid that were considered:

1. **Generate `/config.js` at container start** from environment variables,
   fetched by the SPA before it renders.
2. **Proxy `/api` through nginx** so the frontend never needs an absolute
   backend origin — it only ever calls relative paths like `/api/complaints`.

## Decision
Option 2. `nginx.conf` proxies `location /api/ { proxy_pass
http://backend:8000/api/; }`, and every call in `src/api/client.ts` uses a
relative `/api` base URL. The same built image runs in Compose, k3d/kind and
any future environment unchanged — only the DNS name `backend` needs to
resolve to the right service, which Docker Compose and Kubernetes both do
for free via their own service discovery.

## Consequences
- Simpler than option 1: no entrypoint script, no extra request before the
  app can render, nothing to keep in sync between the ConfigMap and the
  frontend's expectations.
- The frontend genuinely cannot reach any backend other than the one nginx
  is configured to proxy to. That's a feature here (it reinforces the
  edge/internal network segmentation in rubric G), not a limitation — there
  is exactly one backend per environment.
- The one thing this approach can't do that a generated `/config.js` could:
  switch backends at runtime without redeploying the frontend. Not needed
  for this system, since the backend URL is 1:1 with the environment.
- Trade-off recorded, not hidden: if a future requirement needed the same
  frontend image to be pointed at different backends without a redeploy,
  we'd revisit this and move to the `/config.js` approach.
