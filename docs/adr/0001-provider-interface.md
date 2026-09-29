# ADR 0001: AI Triage Provider Protocol and Fallback Architecture

## Status
Accepted

## Context
The CivicPulse platform processes municipal complaints submitted by citizens in Urdu and English. Each incoming complaint requires automated categorization (e.g., water, electricity, sanitation, roads) and priority scoring (high, normal, low) along with a concise English summary.

The categorization pipeline interacts with third-party Large Language Model (LLM) APIs (such as Groq `llama-3.3-70b-versatile` or Google Gemini) as well as locally hosted models (Ollama). However, external LLM APIs present operational risks:
1. **Network Latency & Flakiness**: External API calls can stall or experience network partitions.
2. **Rate Limits & Outages**: Free and tier-limited API keys can hit 429 rate limit ceilings during traffic spikes.
3. **Non-deterministic Responses**: Model outputs can occasionally produce malformed JSON or hallucinated schemas.
4. **CI/CD Flakiness**: Continuous integration test suites must never depend on external network availability or consume paid tokens.

## Decision
We define an explicit **TriageProvider Protocol** (`app/providers/triage_interface.py`) using Python `typing.Protocol` with a unified async method signature:
`async def triage(self, text: str, location: str) -> TriageResult`.

Key implementation decisions:
1. **Multiple Concrete Providers**:
   - `LlmTriageProvider` (`app/providers/llm_triage.py`): Primary high-accuracy provider interfacing with Groq/Gemini APIs using JSON schema mode.
   - `RuleBasedTriage` (`app/providers/rule_triage.py`): Deterministic keyword/regex heuristic engine covering Urdu and English municipal terms (e.g., "pani", "water", "bijli", "electricity", "kura", "gutter").
   - `SimulatedTriageProvider` (`app/providers/simulated_triage.py`): Deterministic mock provider configured with sub-millisecond responses for CI test pipelines (`ci.yml`).
2. **Resilience & Fallback Mechanism**:
   - Every LLM request is bounded by an explicit **10-second timeout** and a **single jittered retry**.
   - If the LLM call times out, encounters a rate limit (HTTP 429), or fails validation, the system automatically falls back to `RuleBasedTriage` with zero unhandled 500 errors to the citizen.
   - The returned `Complaint` object explicitly tags `triaged_by` as `"rules:fallback"` and logs a structured warning.
3. **Provider Factory**:
   - `TriageFactory` (`app/providers/triage_factory.py`) dynamically instantiates the appropriate provider based on the `TRIAGE_PROVIDER` environment variable (`llm`, `ollama`, `rules`, `simulated`).

## Consequences
### Positive
- **Guaranteed High Availability**: Intake requests always succeed with valid triage, even during total LLM provider outages.
- **Hermetic CI/CD**: Unit, integration, and performance tests run against `SimulatedTriageProvider` without internet access or secret leakage.
- **Extensibility**: New LLM backends (e.g. Anthropic, OpenAI, local vLLM) can be added simply by implementing the protocol without changing core business logic.

### Negative / Trade-offs
- Fallback triage via regex heuristics lacks nuanced contextual understanding compared to large generative models.
- Minor latency overhead (up to 10s timeout + retry) before fallback kicks in when the upstream LLM hangs.
