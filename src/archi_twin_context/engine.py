from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from .adapters.base import DigitalTwinAlertSource, EnrichmentResultSink
from .adapters.postgres import PostgresAlertSource, PostgresEnrichmentResultSink, open_connection
from .enricher import enrich_alert
from .loaders import load_archimate_xml_model, load_architecture_model, load_mapping
from .models import ArchitectureModel, AssetMapping


class EnrichmentEngine:
    def __init__(
        self,
        source: DigitalTwinAlertSource,
        sink: EnrichmentResultSink,
        mappings: dict[str, AssetMapping],
        architecture_model: ArchitectureModel,
        batch_size: int = 10,
        log: Callable[[str], None] | None = None,
    ) -> None:
        self.source = source
        self.sink = sink
        self.mappings = mappings
        self.architecture_model = architecture_model
        self.batch_size = batch_size
        self.log = log

    def process_once(self) -> int:
        alerts = self.source.claim_alerts(self.batch_size)
        if alerts and self.log:
            self.log(f"Claimed {len(alerts)} alert(s) for enrichment.")

        for alert in alerts:
            try:
                enriched_alert = enrich_alert(alert, self.mappings, self.architecture_model)
                self.sink.store(enriched_alert)
                self.source.mark_enriched(alert.alert_id)
                if self.log:
                    self.log(
                        "Enriched alert "
                        f"{alert.alert_id}: asset={alert.asset_id} "
                        f"risk={enriched_alert.risk_level} "
                        f"owner={enriched_alert.recommended_owner}"
                    )
            except Exception as exc:
                self.source.mark_failed(alert.alert_id, str(exc))
                if self.log:
                    self.log(f"Failed to enrich alert {alert.alert_id}: {exc}")
        return len(alerts)


def load_engine_model(model_path: Path, model_format: str, xsd_path: Path | None) -> ArchitectureModel:
    if model_format == "auto":
        model_format = "archimate-xml" if model_path.suffix.lower() == ".xml" else "yaml"

    if model_format == "archimate-xml":
        if xsd_path is None:
            raise ValueError("ArchiMate XML import requires --xsd for schema validation")
        return load_archimate_xml_model(model_path, xsd_path)

    if model_format == "yaml":
        return load_architecture_model(model_path)

    raise ValueError("model_format must be one of: auto, yaml, archimate-xml")


def run_engine(
    database_url: str | None,
    mapping_path: Path,
    model_path: Path,
    model_format: str,
    xsd_path: Path | None,
    poll_interval_seconds: float,
    batch_size: int,
    idle_log_every: int = 10,
) -> None:
    mappings = load_mapping(mapping_path)
    architecture_model = load_engine_model(model_path, model_format, xsd_path)

    with open_connection(database_url) as conn:
        engine = EnrichmentEngine(
            source=PostgresAlertSource(conn),
            sink=PostgresEnrichmentResultSink(conn),
            mappings=mappings,
            architecture_model=architecture_model,
            batch_size=batch_size,
            log=lambda message: print(message, flush=True),
        )
        idle_cycles = 0
        while True:
            processed_count = engine.process_once()
            if processed_count == 0:
                idle_cycles += 1
                if idle_log_every > 0 and idle_cycles % idle_log_every == 0:
                    print("No new alerts available for enrichment.", flush=True)
                time.sleep(poll_interval_seconds)
            else:
                idle_cycles = 0
