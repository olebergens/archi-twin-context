from pathlib import Path

from archi_twin_context.engine import EnrichmentEngine, load_engine_model
from archi_twin_context.loaders import load_mapping
from archi_twin_context.models import DigitalTwinAlert, EnrichedAlert

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"
XSD_DIR = Path(__file__).resolve().parents[1] / "xsd"


class FakeSource:
    def __init__(self, alerts: list[DigitalTwinAlert]) -> None:
        self.alerts = alerts
        self.enriched_alert_ids: list[str] = []
        self.failed_alerts: dict[str, str] = {}

    def claim_alerts(self, limit: int) -> list[DigitalTwinAlert]:
        return self.alerts[:limit]

    def mark_enriched(self, alert_id: str) -> None:
        self.enriched_alert_ids.append(alert_id)

    def mark_failed(self, alert_id: str, error_message: str) -> None:
        self.failed_alerts[alert_id] = error_message


class FakeSink:
    def __init__(self) -> None:
        self.enriched_alert_ids: list[str] = []

    def store(self, enriched_alert: EnrichedAlert) -> None:
        self.enriched_alert_ids.append(enriched_alert.alert.alert_id)


def test_load_engine_model_auto_detects_archimate_xml() -> None:
    architecture_model = load_engine_model(
        EXAMPLES_DIR / "manufacturing_archimate_model.xml",
        "auto",
        XSD_DIR / "archimate3_Diagram.xsd",
    )

    assert len(architecture_model.elements) == 15
    assert len(architecture_model.relationships) == 16


def test_enrichment_engine_processes_claimed_alert() -> None:
    alert = DigitalTwinAlert(
        alert_id="alert-engine",
        asset_id="cnc-01",
        alert_type="vibration_high",
        severity="critical",
        value=8.2,
        unit="mm/s",
        timestamp="2026-07-03T12:10:00Z",
        message="Vibration threshold exceeded.",
    )
    mappings = load_mapping(EXAMPLES_DIR / "twin_architecture_mapping_manufacturing.yaml")
    architecture_model = load_engine_model(
        EXAMPLES_DIR / "manufacturing_archimate_model.xml",
        "archimate-xml",
        XSD_DIR / "archimate3_Diagram.xsd",
    )
    source = FakeSource([alert])
    sink = FakeSink()

    engine = EnrichmentEngine(
        source=source,
        sink=sink,
        mappings=mappings,
        architecture_model=architecture_model,
        batch_size=10,
    )

    assert engine.process_once() == 1
    assert sink.enriched_alert_ids == ["alert-engine"]
    assert source.enriched_alert_ids == ["alert-engine"]
