from pathlib import Path

from archi_twin_context.loaders import load_alert, load_architecture_model, load_mapping

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"


def test_alert_can_be_loaded() -> None:
    alert = load_alert(EXAMPLES_DIR / "alert_temperature_high.json")

    assert alert.alert_id == "alert-001"
    assert alert.asset_id == "boiler-17"
    assert alert.alert_type == "temperature_high"


def test_mapping_can_be_loaded() -> None:
    mapping = load_mapping(EXAMPLES_DIR / "twin_architecture_mapping.yaml")

    assert "boiler-17" in mapping
    assert mapping["boiler-17"].ea_element_id == "tech-heating-control-unit"


def test_architecture_model_can_be_loaded() -> None:
    architecture_model = load_architecture_model(EXAMPLES_DIR / "architecture_model.yaml")

    assert len(architecture_model.elements) == 8
    assert architecture_model.elements[0].name == "Facility Operations"
