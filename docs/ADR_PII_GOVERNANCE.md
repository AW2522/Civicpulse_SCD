# ADR 002: Citizen Data Privacy, PII Governance & Prompt Injection Guardrails

## Status
Accepted

## Context
Citizen complaints submitted to CivicPulse often contain Personally Identifiable Information (PII) such as phone numbers, citizen names, or sensitive addresses. Additionally, malicious actors may attempt prompt injection attacks inside complaint text to override AI model classification rules.

## Decision
We enforce strict data governance and AI security controls across the processing pipeline:

1. **PII Sanitization & Isolation**:
   - Citizen contact details (`reporter_contact`) are stored in isolated DB columns and are strictly excluded from prompts sent to external LLM providers. Only complaint text and location are passed to the AI layer.
2. **Prompt Injection Guardrails**:
   - System prompts strictly instruct the LLM to process input text purely as passive data within the defined JSON output schema (`category`, `priority`, `summary`, `confidence`).
   - Output validation enforces enum constraints (`ComplaintCategory`, `ComplaintPriority`). Any out-of-spec or injected model response triggers schema validation errors, causing immediate fallback to `RuleBasedTriage`.
3. **Auditability & Traceability**:
   - Every complaint record persists `triaged_by` (e.g., `llm:groq:llama-3.3-70b-versatile`, `rules:keyword`, `rules:fallback`) and `triage_latency_ms` to maintain full transparency over automated decisions.

## Consequences
- Protects citizen privacy by preventing PII exposure to third-party AI APIs.
- Prevents adversarial prompt injection from subverting system categorization rules.
- Fully auditable automated triage history for municipal supervisors.
