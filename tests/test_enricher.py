from pathlib import Path

from archi_twin_context.enricher import enrich_alert
from archi_twin_context.loaders import load_alert, load_architecture_model, load_mapping

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"


def test_boiler_alert_maps_to_heating_control_unit() -> None:
    alert = load_alert(EXAMPLES_DIR / "alert_temperature_high.json")
    mappings = load_mapping(EXAMPLES_DIR / "twin_architecture_mapping.yaml")
    architecture_model = load_architecture_model(EXAMPLES_DIR / "architecture_model.yaml")

    enriched = enrich_alert(alert, mappings, architecture_model)

    assert enriched.mapped_element.name == "Heating Control Unit"


def test_business_impact_contains_facility_operations() -> None:
    alert = load_alert(EXAMPLES_DIR / "alert_temperature_high.json")
    mappings = load_mapping(EXAMPLES_DIR / "twin_architecture_mapping.yaml")
    architecture_model = load_architecture_model(EXAMPLES_DIR / "architecture_model.yaml")

    enriched = enrich_alert(alert, mappings, architecture_model)

    assert "Facility Operations" in enriched.business_impact["business_capabilities"]


def test_recommended_owner_uses_mapping_owner() -> None:
    alert = load_alert(EXAMPLES_DIR / "alert_temperature_high.json")
    mappings = load_mapping(EXAMPLES_DIR / "twin_architecture_mapping.yaml")
    architecture_model = load_architecture_model(EXAMPLES_DIR / "architecture_model.yaml")

    enriched = enrich_alert(alert, mappings, architecture_model)

    assert enriched.recommended_owner == "Facility Operations Team"
