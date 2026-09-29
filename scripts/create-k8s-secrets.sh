#!/usr/bin/env bash
# Creates the real civicpulse-secrets Secret in the civicpulse namespace from
# .env — this is deliberately NOT done by editing k8s/base/secret.yaml,
# whose committed placeholders must stay placeholders. `kubectl create
# --dry-run=client -o yaml | kubectl apply -f -` never writes a file to
# disk, so there's nothing here to accidentally git add.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "error: ${ENV_FILE} not found. Copy .env.example to .env and fill it in first." >&2
  exit 1
fi

set -a
# shellcheck source=/dev/null
source "${ENV_FILE}"
set +a

: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD must be set in .env}"
: "${GROQ_API_KEY:=}"   # optional — fine to be empty if TRIAGE_PROVIDER isn't llm

if ! kubectl get namespace civicpulse >/dev/null 2>&1; then
  kubectl create namespace civicpulse
fi

kubectl create secret generic civicpulse-secrets \
  --namespace civicpulse \
  --from-literal="POSTGRES_PASSWORD=${POSTGRES_PASSWORD}" \
  --from-literal="GROQ_API_KEY=${GROQ_API_KEY}" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "civicpulse-secrets applied in namespace civicpulse."
