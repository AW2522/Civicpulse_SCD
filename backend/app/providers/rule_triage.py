import time

from app.models.complaint import ComplaintCategory, ComplaintPriority
from app.providers.triage_interface import TriageProvider
from app.schemas.triage import TriageResult


class RuleBasedTriage(TriageProvider):
    """
    Deterministic rule-based triage fallback provider using Urdu/English keyword matching.
    """
    provider_name: str = "rules:keyword"

    # Category keyword mapping (Urdu-influenced English and English)
    CATEGORY_KEYWORDS = {
        ComplaintCategory.SANITATION: ["kachra", "garbage", "trash", "ganda", "cleanliness", "sweeper", "dustbin", "waste", "nala", "drainage"],
        ComplaintCategory.WATER: ["paani", "water", "tanker", "wasa", "leak", "pipeline", "tap", "sewage", "hydrant", "boring"],
        ComplaintCategory.ELECTRICITY: ["bijli", "electricity", "transformer", "power", "loadshedding", "voltage", "taar", "spark", "wire"],
        ComplaintCategory.ROADS: ["khadda", "pothole", "road", "carpet", "traffic", "signal", "flyover", "speed breaker", "footpath"],
        ComplaintCategory.PUBLIC_SAFETY: ["light", "street light", "dog", "stray", "snatching", "crime", "chori", "police", "danger", "fire"],
    }

    # Priority keyword mapping
    PRIORITY_KEYWORDS = {
        ComplaintPriority.CRITICAL: ["blast", "fire", "hazard", "blackout", "emergency", "touching", "fall", "spill", "children park", "overflowing"],
        ComplaintPriority.HIGH: ["leaking", "broken", "blocked", "daily", "stray dogs", "dark", "heavy"],
        ComplaintPriority.MEDIUM: ["low voltage", "benches", "inconvenience", "uncut", "delay"],
    }

    async def triage(self, text: str, location: str, is_fallback: bool = False) -> tuple[TriageResult, str, float]:
        start_time = time.perf_counter()
        text_lower = text.lower()

        # Determine category
        detected_category = ComplaintCategory.OTHER
        for cat, keywords in self.CATEGORY_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                detected_category = cat
                break

        # Determine priority
        detected_priority = ComplaintPriority.LOW
        for prio, keywords in self.PRIORITY_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                detected_priority = prio
                break

        # Construct concise summary <= 140 chars
        clean_text = text.replace("\n", " ").strip()
        summary_prefix = "[Fallback] " if is_fallback else "[Rule] "
        max_len = 140 - len(summary_prefix)
        summary = summary_prefix + (clean_text[:max_len-3] + "..." if len(clean_text) > max_len else clean_text)

        triage_res = TriageResult(
            category=detected_category,
            priority=detected_priority,
            summary=summary,
            confidence=0.75 if not is_fallback else 0.50
        )

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        provider_tag = "rules:fallback" if is_fallback else "rules:keyword"
        return triage_res, provider_tag, latency_ms
