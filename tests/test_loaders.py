from pathlib import Path
from xml.etree import ElementTree

import pytest

from archi_twin_context.loaders import load_alert, load_architecture_model, load_mapping
from archi_twin_context.loaders import load_archimate_xml_model

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"
XSD_DIR = Path(__file__).resolve().parents[1] / "xsd"


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


def test_archimate_xml_model_can_be_loaded_with_xsd_validation() -> None:
    architecture_model = load_archimate_xml_model(
        EXAMPLES_DIR / "manufacturing_archimate_model.xml",
        XSD_DIR / "archimate3_Diagram.xsd",
    )

    assert len(architecture_model.elements) == 15
    assert len(architecture_model.relationships) == 16
    assert architecture_model.elements[-1].name == "Packaging Line 03"


def test_archimate_xml_loader_reads_properties_and_relationships() -> None:
    architecture_model = load_archimate_xml_model(
        EXAMPLES_DIR / "manufacturing_archimate_model.xml",
        XSD_DIR / "archimate3_Diagram.xsd",
    )
    elements = {element.id: element for element in architecture_model.elements}

    assert elements["equipment-cnc-01"].owner == "Maintenance Department"
    assert elements["equipment-cnc-01"].criticality == "high"
    assert "cnc" in elements["equipment-cnc-01"].tags
    assert "node-edge-platform" in elements["equipment-cnc-01"].related_elements


def test_archimate_xml_example_contains_diagram_view() -> None:
    root = ElementTree.parse(EXAMPLES_DIR / "manufacturing_archimate_model.xml").getroot()
    namespace = {"a": "http://www.opengroup.org/xsd/archimate/3.0/"}

    view = root.find("a:views/a:diagrams/a:view", namespace)
    nodes = root.findall("a:views/a:diagrams/a:view/a:node", namespace)
    connections = root.findall("a:views/a:diagrams/a:view/a:connection", namespace)

    assert view is not None
    assert view.get("identifier") == "view-manufacturing-impact"
    assert len(nodes) == 15
    assert len(connections) == 16


def test_archimate_xml_loader_rejects_invalid_xml_against_xsd(tmp_path: Path) -> None:
    invalid_xml = tmp_path / "invalid_archimate.xml"
    invalid_xml.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<model xmlns="http://www.opengroup.org/xsd/archimate/3.0/"
       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
       identifier="invalid-model">
  <name>Invalid Model</name>
  <relationships>
    <relationship identifier="rel-invalid" xsi:type="Serving" source="missing-source" />
  </relationships>
</model>
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="does not validate"):
        load_archimate_xml_model(
            invalid_xml,
            XSD_DIR / "archimate3_Diagram.xsd",
        )
