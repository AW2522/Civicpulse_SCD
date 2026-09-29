import asyncio
import time
from typing import Tuple
import httpx
from app.models.complaint import ComplaintCategory, ComplaintPriority
from app.schemas.triage import TriageResult
from app.providers.triage_interface import TriageProvider


class SimulatedTriage(TriageProvider):
    """
    Deterministic simulated triage provider for fast CI unit testing and offline development.
    Supports failure injection flags embedded in complaint text:
    - TRIGGER_500 -> Raises HTTP 500 status exception
    - TRIGGER_429 -> Raises HTTP 429 status exception
    - TRIGGER_TIMEOUT -> Raises asyncio.TimeoutError
    - TRIGGER_PROMPT_INJECTION -> Returns attempted injection string to test guardrails
    """
    provider_name: str = "simulated:default"

    async def triage(self, text: str, location: str) -> Tuple[TriageResult, str, float]:
        start_time = time.perf_counter()

        # Fault Injection Triggers for CI testing
        if "TRIGGER_500" in text:
            raise httpx.HTTPStatusError("Simulated 500 Internal Server Error", request=None, response=httpx.Response(500))
        if "TRIGGER_429" in text:
            raise httpx.HTTPStatusError("Simulated 429 Too Many Requests", request=None, response=httpx.Response(429))
        if "TRIGGER_TIMEOUT" in text:
            raise asyncio.TimeoutError("Simulated LLM Timeout after 10s")

        text_lower = text.lower()
        
        # Categorization logic
        category = ComplaintCategory.OTHER
        if any(w in text_lower for w in ["kachra", "garbage", "trash", "sanitation"]):
            category = ComplaintCategory.SANITATION
        elif any(w in text_lower for w in ["paani", "water", "leak", "tanker"]):
            category = ComplaintCategory.WATER
        elif any(w in text_lower for w in ["bijli", "electricity", "transformer", "power"]):
            category = ComplaintCategory.ELECTRICITY
        elif any(w in text_lower for w in ["khadda", "road", "pothole"]):
            category = ComplaintCategory.ROADS
        elif any(w in text_lower for w in ["light", "police", "crime", "dog", "safety"]):
            category = ComplaintCategory.PUBLIC_SAFETY

        priority = ComplaintPriority.MEDIUM
        if any(w in text_lower for w in ["blast", "fire", "emergency", "critical"]):
            priority = ComplaintPriority.CRITICAL
        elif any(w in text_lower for w in ["urgent", "heavy", "broken", "high"]):
            priority = ComplaintPriority.HIGH
        elif any(w in text_lower for w in ["minor", "low"]):
            priority = ComplaintPriority.LOW

        clean_text = text.replace("\n", " ").strip()
        summary = (clean_text[:137] + "...") if len(clean_text) > 140 else clean_text

        result = TriageResult(
            category=category,
            priority=priority,
            summary=summary,
            confidence=0.95
        )

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return result, self.provider_name, latency_ms
