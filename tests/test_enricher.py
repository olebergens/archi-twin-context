from pathlib import Path

import pytest

from archi_twin_context.enricher import enrich_alert
from archi_twin_context.loaders import load_alert, load_archimate_xml_model, load_architecture_model, load_mapping
from archi_twin_context.models import AssetMapping

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"
XSD_DIR = Path(__file__).resolve().parents[1] / "xsd"


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


def test_archimate_xml_enrichment_uses_archimate_id_and_impact_tree() -> None:
    alert = load_alert(EXAMPLES_DIR / "alert_machine_vibration.json")
    mappings = load_mapping(EXAMPLES_DIR / "twin_architecture_mapping_manufacturing.yaml")
    architecture_model = load_archimate_xml_model(
        EXAMPLES_DIR / "manufacturing_archimate_model.xml",
        XSD_DIR / "archimate3_Diagram.xsd",
    )

    enriched = enrich_alert(alert, mappings, architecture_model)

    assert enriched.mapped_element.name == "CNC Milling Machine 01"
    assert "Production Operations" in enriched.business_impact["business_capabilities"]
    assert "Equipment Incident Handling" in enriched.business_impact["business_processes"]
    assert enriched.impact_tree is not None
    assert enriched.impact_tree.name == "CNC Milling Machine 01"


def test_archimate_xml_enrichment_can_fallback_to_name_and_tags() -> None:
    alert = load_alert(EXAMPLES_DIR / "alert_machine_vibration.json")
    architecture_model = load_archimate_xml_model(
        EXAMPLES_DIR / "manufacturing_archimate_model.xml",
        XSD_DIR / "archimate3_Diagram.xsd",
    )
    mappings = {
        "cnc-01": AssetMapping(
            asset_id="cnc-01",
            ea_element_id="missing-local-id",
            match_name="CNC Milling Machine 01",
            match_tags=["cnc", "machine"],
            default_bpmn_process="handle-critical-equipment-anomaly",
            owner="Maintenance Department",
        )
    }

    enriched = enrich_alert(alert, mappings, architecture_model)

    assert enriched.mapped_element.id == "equipment-cnc-01"


def test_archimate_xml_enrichment_rejects_mismatched_verification_tags() -> None:
    alert = load_alert(EXAMPLES_DIR / "alert_machine_vibration.json")
    architecture_model = load_archimate_xml_model(
        EXAMPLES_DIR / "manufacturing_archimate_model.xml",
        XSD_DIR / "archimate3_Diagram.xsd",
    )
    mappings = {
        "cnc-01": AssetMapping(
            asset_id="cnc-01",
            ea_element_id="missing-local-id",
            archimate_element_id="equipment-cnc-01",
            match_name="CNC Milling Machine 01",
            match_tags=["unknown-tag"],
        )
    }

    with pytest.raises(ValueError, match="required tags are missing"):
        enrich_alert(alert, mappings, architecture_model)
