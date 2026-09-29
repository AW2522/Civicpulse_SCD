# ADR 0003: Deploy by commit SHA, never by `:latest`

## Status
Accepted

## Context
`cd.yml` builds and pushes two images on every push to `main`. Something has
to decide which tag actually gets applied to the cluster. `:latest` is
tempting because nothing has to change between deploys, but it means
`kubectl describe pod` cannot tell you which commit is actually running —
"what is production running?" has no answer you can paste into `git show`.

## Decision
Every image is pushed with two tags: the commit SHA (`${{ github.sha }}`)
and `latest`. `latest` may be pushed — plenty of tooling expects it to
exist — but it is never the tag applied to a cluster. `k8s/overlays/prod`
starts with an intentionally-unresolvable placeholder image name
(`ghcr.io/REPLACE_OWNER/...`), and `cd.yml`'s `deploy-k8s` job runs
`kustomize edit set image ...=ghcr.io/$OWNER/civicpulse-backend:$SHA`
immediately before `kustomize build | kubectl apply`. The SHA that gets
deployed is exactly the SHA that `build-push` just built and `scan` just
passed — there is no path from a green pipeline to a different image being
deployed.

## Consequences
- `git show <sha>` always answers "what is running" precisely, and rollback
  (`kubectl rollout undo`, or re-applying the previous overlay with the
  previous SHA) is unambiguous because every previous state is named.
- The prod overlay's manifest, as committed, does not itself point at a
  real image — it is only ever built after CI patches the tag in. This is
  intentional: a manifest that resolved to a real image would tempt someone
  to apply it by hand outside the pipeline.
- Cost: one extra `kustomize edit set image` step in CI, and the overlay
  cannot be `kubectl apply`'d directly from a checkout without that step
  (or a manually supplied tag) — acceptable, since bypassing CI to deploy
  is exactly what this ADR exists to prevent.
