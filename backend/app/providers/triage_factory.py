import hashlib
import json
import time
from collections import deque
from typing import Dict, Any, List, Tuple, Optional
from app.config import settings
from app.core.logging import logger
from app.core.redis import get_redis_client
from app.schemas.triage import TriageResult
from app.providers.triage_interface import TriageProvider
from app.providers.rule_triage import RuleBasedTriage
from app.providers.simulated_triage import SimulatedTriage
from app.providers.llm_triage import LLMTriage


class TriageManager:
    """
    Orchestrator for AI triage execution:
    - Content-hash Redis caching (24h TTL)
    - Active provider selection based on TRIAGE_PROVIDER
    - Automatic fallback to RuleBasedTriage on exception (emitting WARNING log & triaged_by = rules:fallback)
    - Metrics collection (hit rate, provider status, last 20 outcomes)
    """

    def __init__(self):
        self.rule_provider = RuleBasedTriage()
        self.simulated_provider = SimulatedTriage()
        self.llm_provider = LLMTriage()
        
        # In-memory metrics tracking
        self.total_triage_count: int = 0
        self.cache_hits: int = 0
        self.fallback_count: int = 0
        self.recent_outcomes: deque = deque(maxlen=20)  # Stores last 20 triage outcomes

    def get_active_provider(self) -> TriageProvider:
        provider_type = settings.TRIAGE_PROVIDER.lower()
        if provider_type == "llm":
            return self.llm_provider
        elif provider_type == "rules":
            return self.rule_provider
        else:
            return self.simulated_provider

    async def _get_cached_triage(self, text: str, location: str) -> Optional[Tuple[TriageResult, str]]:
        """Checks Redis for cached triage result using SHA-256 hash of text + location."""
        try:
            redis_client = await get_redis_client()
            content_hash = hashlib.sha256(f"{text.strip()}||{location.strip()}".encode("utf-8")).hexdigest()
            cache_key = f"triage_cache:{content_hash}"
            
            cached_val = await redis_client.get(cache_key)
            if cached_val:
                data = json.loads(cached_val)
                triage_res = TriageResult.model_validate(data["result"])
                provider_tag = data["triaged_by"] + ":cache"
                return triage_res, provider_tag
        except Exception as e:
            logger.warning(f"Failed to query Redis triage cache: {e}")
        return None

    async def _set_cached_triage(self, text: str, location: str, result: TriageResult, provider_tag: str):
        """Caches triage result in Redis with 24h TTL."""
        try:
            redis_client = await get_redis_client()
            content_hash = hashlib.sha256(f"{text.strip()}||{location.strip()}".encode("utf-8")).hexdigest()
            cache_key = f"triage_cache:{content_hash}"
            
            payload = json.dumps({
                "result": result.model_dump(),
                "triaged_by": provider_tag
            })
            await redis_client.set(cache_key, payload, ex=settings.CACHE_TRIAGE_TTL_SECONDS)
        except Exception as e:
            logger.warning(f"Failed to save triage result to Redis cache: {e}")

    async def execute_triage(self, text: str, location: str) -> Tuple[TriageResult, str, float]:
        self.total_triage_count += 1
        start_time = time.perf_counter()

        # Step 1: Check Redis Cache
        cached = await self._get_cached_triage(text, location)
        if cached:
            self.cache_hits += 1
            triage_res, provider_tag = cached
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            self._record_outcome(triage_res, provider_tag, latency_ms, is_cache_hit=True)
            return triage_res, provider_tag, latency_ms

        # Step 2: Try Active Provider
        active_provider = self.get_active_provider()
        try:
            triage_res, provider_tag, latency_ms = await active_provider.triage(text, location)
            # Cache result in Redis
            await self._set_cached_triage(text, location, triage_res, provider_tag)
            self._record_outcome(triage_res, provider_tag, latency_ms, is_cache_hit=False)
            return triage_res, provider_tag, latency_ms
        except Exception as e:
            # Step 3: Fallback Mechanism on Failure
            self.fallback_count += 1
            logger.warning(
                f"Triage provider '{active_provider.provider_name}' failed with error: {e}. Falling back to RuleBasedTriage."
            )
            fallback_res, _, latency_ms = await self.rule_provider.triage(text, location, is_fallback=True)
            provider_tag = "rules:fallback"
            self._record_outcome(fallback_res, provider_tag, latency_ms, is_cache_hit=False)
            return fallback_res, provider_tag, latency_ms

    def _record_outcome(self, result: TriageResult, provider_tag: str, latency_ms: float, is_cache_hit: bool):
        outcome = {
            "timestamp": time.time(),
            "category": result.category.value,
            "priority": result.priority.value,
            "summary": result.summary,
            "confidence": result.confidence,
            "triaged_by": provider_tag,
            "latency_ms": latency_ms,
            "cache_hit": is_cache_hit
        }
        self.recent_outcomes.appendleft(outcome)

    def get_meta_info(self) -> Dict[str, Any]:
        """Returns metadata for GET /api/meta/providers."""
        hit_rate = round((self.cache_hits / self.total_triage_count) * 100, 2) if self.total_triage_count > 0 else 0.0
        return {
            "active_provider": settings.TRIAGE_PROVIDER,
            "provider_class": self.get_active_provider().__class__.__name__,
            "total_triage_requests": self.total_triage_count,
            "cache_hits": self.cache_hits,
            "cache_hit_rate_pct": hit_rate,
            "fallback_count": self.fallback_count,
            "recent_outcomes": list(self.recent_outcomes)
        }


# Global singleton manager instance
triage_manager = TriageManager()
