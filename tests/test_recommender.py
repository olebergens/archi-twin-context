from archi_twin_context.models import AssetMapping, DigitalTwinAlert, EAElement
from archi_twin_context.recommender import recommend_bpmn_process


def _alert(alert_type: str) -> DigitalTwinAlert:
    return DigitalTwinAlert(
        alert_id="alert-test",
        asset_id="asset-test",
        alert_type=alert_type,
        severity="warning",
        value=None,
        unit=None,
        timestamp="2026-07-03T12:00:00Z",
        message=None,
    )


def _mapping(default_process: str | None = None) -> AssetMapping:
    return AssetMapping(
        asset_id="asset-test",
        ea_element_id="element-test",
        default_bpmn_process=default_process,
        owner=None,
    )


def _mapped_element() -> EAElement:
    return EAElement(
        id="element-test",
        name="Test Element",
        type="TechnologyNode",
        layer="Technology",
        description=None,
        criticality="medium",
        owner=None,
        related_elements=[],
        supported_capabilities=[],
        supported_processes=[],
        supported_applications=[],
        tags=[],
    )


def test_mapping_process_has_priority() -> None:
    recommendation = recommend_bpmn_process(
        _alert("temperature_high"),
        _mapping("custom-process"),
        _mapped_element(),
    )

    assert recommendation == "custom-process"


def test_temperature_high_fallback_rule() -> None:
    recommendation = recommend_bpmn_process(
        _alert("temperature_high"),
        _mapping(),
        _mapped_element(),
    )

    assert recommendation == "handle-equipment-anomaly"


def test_vibration_high_fallback_rule() -> None:
    recommendation = recommend_bpmn_process(
        _alert("vibration_high"),
        _mapping(),
        _mapped_element(),
    )

    assert recommendation == "handle-equipment-anomaly"


def test_unknown_alert_type_returns_none() -> None:
    recommendation = recommend_bpmn_process(
        _alert("unknown_alert_type"),
        _mapping(),
        _mapped_element(),
    )

    assert recommendation is None
