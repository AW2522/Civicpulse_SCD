from typing import Protocol, Tuple
from app.schemas.triage import TriageResult


class TriageProvider(Protocol):
    """
    Protocol defining the interface for AI Triage providers.
    All implementations must provide the async triage method.
    """
    provider_name: str

    async def triage(self, text: str, location: str) -> Tuple[TriageResult, str, float]:
        """
        Triages complaint text and location.
        Returns:
            Tuple[TriageResult, triaged_by_identifier, latency_ms]
        """
        ...
