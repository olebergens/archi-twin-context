from pathlib import Path

from archi_twin_context.adapters.postgres import alert_from_row, enriched_alert_record, resolve_database_url
from archi_twin_context.enricher import enrich_alert
from archi_twin_context.loaders import load_alert, load_archimate_xml_model, load_mapping

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"
XSD_DIR = Path(__file__).resolve().parents[1] / "xsd"


def test_resolve_database_url_uses_explicit_value() -> None:
    assert resolve_database_url("postgresql://example") == "postgresql://example"


def test_alert_from_row_prefers_payload_json() -> None:
    row = {
        "payload_json": {
            "alert_id": "alert-row",
            "asset_id": "cnc-01",
            "alert_type": "vibration_high",
            "severity": "critical",
            "value": 8.2,
            "unit": "mm/s",
            "timestamp": "2026-07-03T12:10:00Z",
            "message": "Vibration threshold exceeded.",
        }
    }

    alert = alert_from_row(row)

    assert alert.alert_id == "alert-row"
    assert alert.asset_id == "cnc-01"
    assert alert.value == 8.2


def test_enriched_alert_record_contains_dashboard_fields() -> None:
    alert = load_alert(EXAMPLES_DIR / "alert_machine_vibration.json")
    mappings = load_mapping(EXAMPLES_DIR / "twin_architecture_mapping_manufacturing.yaml")
    architecture_model = load_archimate_xml_model(
        EXAMPLES_DIR / "manufacturing_archimate_model.xml",
        XSD_DIR / "archimate3_Diagram.xsd",
    )
    enriched = enrich_alert(alert, mappings, architecture_model)

    record = enriched_alert_record(enriched)

    assert record["alert_id"] == "alert-003"
    assert record["mapped_element_id"] == "equipment-cnc-01"
    assert record["risk_level"] == "critical"
    assert record["impact_tree_json"] is not None
    assert "Production Operations" in record["business_impact_json"]["business_capabilities"]
