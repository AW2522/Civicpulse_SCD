# ADR 001: Pluggable AI Triage Provider Strategy & Fallback Mechanism

## Status
Accepted

## Context
CivicPulse requires automated triage of citizen complaints (categorization, priority scoring, summary generation). Triage relies on Large Language Model (LLM) inference (e.g., GROQ Llama 3.3 70B), but network latencies, rate limits, API outages, or bad model outputs must not prevent complaint creation or crash the system.

## Decision
We implement a **Strategy & Factory Design Pattern** via a strict abstract provider protocol (`TriageProvider` interface):

1. **Provider Protocol (`TriageProvider`)**:
   - Standardized `triage(text, location)` contract returning structured `TriageResult`, provider metadata tag, and latency in milliseconds.
2. **Provider Implementations**:
   - `LLMTriage`: Primary provider communicating with GROQ Cloud API (10-second request timeout, single retry with exponential backoff & jitter).
   - `RuleBasedTriage`: Deterministic keyword-matching fallback provider for offline execution and instant categorization.
   - `SimulatedTriage`: Mock provider for deterministic CI/CD unit testing and offline development.
3. **Fail-Safe Fallback**:
   - `TriageManager` wraps provider calls in an exception handler. If the primary LLM provider fails, times out, or returns unparseable JSON, the manager seamlessly falls back to `RuleBasedTriage` with tag `"rules:fallback"`, ensuring HTTP 201 Created is ALWAYS returned to the citizen.

## Consequences
- Zero downtime or 500 Internal Server Errors due to upstream AI provider failures.
- Deterministic unit testing using `TRIAGE_PROVIDER=simulated`.
- Seamless addition of future LLM providers (e.g., OpenAI, Anthropic, local Ollama) by implementing `TriageProvider`.
