# Demo Video Script — CivicPulse (CS4032 Assignment 01)

**Duration**: ≤ 5 minutes (Target: 4m 30s)  
**Speakers**: Person 1 (Backend/AI/Data), Person 2 (Frontend/Docker/K8s/CI)  
**Video Goal**: Demonstrate end-to-end functionality from clean clone to production Kubernetes scaling and rollback.

---

### Timeline Overview

| Time | Topic | Speaker | Visual / Terminal Action |
|---|---|---|---|
| **0:00 – 0:40** | Clean clone → One-command quickstart | **Person 2** | `git clone`, `cp .env.example .env`, `make dev`, browser open |
| **0:40 – 1:30** | Live AI Complaint Triage (Urdu & English) | **Person 1** | Frontend submit form (`/`), show Groq response & auto-categorization |
| **1:30 – 2:15** | Triage Fallback Resilience (LLM Outage) | **Person 1** | Disable LLM key, submit complaint, verify `rules:fallback` 201 response |
| **2:15 – 3:00** | Network Segmentation Proof (Isolation) | **Person 2** | `docker compose exec frontend ping postgres` (fails as expected) |
| **3:00 – 3:45** | Kubernetes & HPA Autoscaling Under Load | **Person 2** | `k6 run load/k6-script.js`, `kubectl get hpa,pods -w` scaling out |
| **3:45 – 4:30** | Zero-Downtime Rollback & Wrap-Up | **Person 2 & 1** | `kubectl rollout undo deployment/backend`, summary of results |

---

## Detailed Script & Commands

### Scene 1: Clean Clone to Running Stack (0:00 – 0:40)
**Speaker: Person 2 (Frontend & DevOps Lead)**
> *"Hello! Welcome to our demo of CivicPulse, our municipal complaint intake, triage, and operations platform for CS4032. I'm [Person 2 Name] handling the Frontend, Docker, Kubernetes, and CI/CD pipelines, and with me is [Person 1 Name], who owns the Backend, Data layer, and AI triage provider."*

**Action (Terminal):**
```bash
git clone https://github.com/AW2522/Civicpulse_SCD.git civicpulse-demo
cd civicpulse-demo
cp .env.example .env
make dev
```
> *"With one command — `make dev` — Docker Compose stands up our entire stack: PostgreSQL 16 on an isolated internal network, Redis 7 caching, our FastAPI backend with automated Alembic migrations and seed data, and our React/Vite frontend served by Nginx on port 5173."*

---

### Scene 2: Live AI Complaint Triage in Action (0:40 – 1:30)
**Speaker: Person 1 (Backend & AI Lead)**
> *"Let's test the intake pipeline. I'll open the frontend at `localhost:5173` and submit a real-world municipal complaint in Roman Urdu:
> 'Street 14 main main water supply pipe phat gaya hai, pani pure muhallay main beh raha hai.'"*

**Action (Browser):**
1. Enter problem description and location: `Street 14, G-9/1`.
2. Click **Submit report**.
3. Point to the returned card:
   - Category: `water`
   - Priority: `high`
   - Summary: *"Burst water supply pipe causing widespread flooding across neighborhood street"*
   - Triaged by: `llm:groq`

> *"In under 400 milliseconds, our `LlmTriageProvider` sent the complaint to Groq's LLaMA 3.3 70B model using JSON schema mode, classified it accurately as high-priority water infrastructure, and generated a structured English summary."*

---

### Scene 3: Resilient Triage Fallback (1:30 – 2:15)
**Speaker: Person 1 (Backend & AI Lead)**
> *"Now let's simulate a sudden upstream LLM outage or exhausted free-tier API rate limit. I'll patch the environment to simulate a rate-limited or invalid API key."*

**Action (Terminal & Browser):**
```bash
# In another terminal or via env:
docker compose exec backend env GROQ_API_KEY=invalid_key
```
Submit another complaint: *"Electricity transformer sparking near street pole"*.

> *"Notice that the submission still succeeds with HTTP 201 in under 10 milliseconds! Our `RuleBasedTriage` fallback automatically caught the upstream error, parsed the keywords, and tagged `triaged_by: rules:fallback`. The citizen experiences zero 500 crashes."*

---

### Scene 4: Security & Network Segmentation Proof (2:15 – 3:00)
**Speaker: Person 2 (Frontend & DevOps Lead)**
> *"A key requirement of Rubric G is enforced network segmentation. Our architecture isolates PostgreSQL and Redis on an internal non-routable Docker bridge network. The only service that bridges `edge` and `internal` is the backend."*

**Action (Terminal):**
```bash
docker compose exec frontend ping -c 2 postgres
```
**Expected Output**: `ping: bad address 'postgres'` or packet loss.

> *"As you can see, `frontend` cannot resolve or ping `postgres`. This hard failure proves that even if the public-facing Nginx container were compromised, citizen data in PostgreSQL remains cryptographically and topologically unreachable."*

---

### Scene 5: Kubernetes Manifests & HPA Autoscaling (3:00 – 3:45)
**Speaker: Person 2 (Frontend & DevOps Lead)**
> *"Now let's look at our Kubernetes environment. We deploy our base manifests and overlays using Kustomize. Here we have our Horizontal Pod Autoscaler configured to maintain 70% target CPU utilization."*

**Action (Terminal):**
```bash
kubectl apply -k k8s/overlays/dev
kubectl -n civicpulse get pods,hpa

# Launch load test
k6 run load/k6-script.js
```
**Visual**: Split terminal showing `kubectl -n civicpulse get hpa,pods -w` scaling the backend deployment from 2 replicas up to 5 replicas as CPU utilization rises.

> *"Under synthetic load from our k6 script, the HPA detects the CPU surge and automatically scales our backend pods from 2 to 5 replicas without dropping incoming requests."*

---

### Scene 6: Instant Zero-Downtime Rollback (3:45 – 4:30)
**Speaker: Person 2 & Person 1**
> *"Finally, let's demonstrate our zero-downtime rollback capability. If a bad release is deployed, our runbook prescribes an instant rollout undo."*

**Action (Terminal):**
```bash
kubectl -n civicpulse rollout undo deployment/backend
kubectl -n civicpulse rollout status deployment/backend
```

> *"Kubernetes executes a rolling rollback, replacing pods seamlessly while traffic continues to be served."*

**Closing (Person 1 & 2):**
> *"In summary, CivicPulse combines high-accuracy AI triage, deterministic fallback resilience, strict network isolation, and production-grade CI/CD and Kubernetes orchestration. Thank you!"*
