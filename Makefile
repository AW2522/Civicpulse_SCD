.PHONY: help dev dev-down dev-logs lint test build check \
        k8s-dev-up k8s-dev-down k8s-secrets k8s-status load-test

help:
	@echo "make dev          - docker compose up --build (local stack)"
	@echo "make dev-down     - docker compose down -v"
	@echo "make dev-logs     - tail all compose service logs"
	@echo "make lint         - frontend eslint + tsc --noEmit"
	@echo "make test         - frontend vitest run"
	@echo "make build        - frontend production build"
	@echo "make check        - run scripts/check_submission.py"
	@echo "make k8s-dev-up   - create a k3d cluster and apply k8s/overlays/dev"
	@echo "make k8s-dev-down - delete the k3d cluster"
	@echo "make k8s-secrets  - create real k8s Secrets from .env (never commit these)"
	@echo "make k8s-status   - pods, hpa and vpa in the civicpulse namespace"
	@echo "make load-test    - run load/k6-script.js against BASE_URL (default localhost:8000)"

dev:
	docker compose -f compose.yaml up --build

dev-down:
	docker compose -f compose.yaml down -v

dev-logs:
	docker compose -f compose.yaml logs -f

lint:
	cd frontend && npm run lint && npx tsc --noEmit

test:
	cd frontend && npx vitest run

build:
	cd frontend && npm run build

check:
	python3 scripts/check_submission.py

k8s-dev-up:
	k3d cluster create civicpulse-dev --agents 1 --wait
	@echo "Build and import your images, then: kubectl apply -k k8s/overlays/dev"

k8s-dev-down:
	k3d cluster delete civicpulse-dev

k8s-secrets:
	bash scripts/create-k8s-secrets.sh

k8s-status:
	kubectl -n civicpulse get pods,hpa,vpa

load-test:
	k6 run -e BASE_URL=$${BASE_URL:-http://localhost:8000} load/k6-script.js
