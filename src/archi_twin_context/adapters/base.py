from __future__ import annotations

from typing import Protocol

from archi_twin_context.models import DigitalTwinAlert, EnrichedAlert


class DigitalTwinAlertSource(Protocol):
    """Source adapter that claims Digital Twin alerts for enrichment"""

    def claim_alerts(self, limit: int) -> list[DigitalTwinAlert]:
        """Claim up to limit alerts for exclusive processing"""

    def mark_enriched(self, alert_id: str) -> None:
        """Mark an alert as successfully enriched"""

    def mark_failed(self, alert_id: str, error_message: str) -> None:
        """Mark an alert as failed with a useful error message"""


class EnrichmentResultSink(Protocol):
    """Sink adapter that persists enrichment results"""

    def store(self, enriched_alert: EnrichedAlert) -> None:
        """Store one enriched alert"""
