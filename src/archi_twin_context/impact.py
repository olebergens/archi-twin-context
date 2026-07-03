from __future__ import annotations

from .models import ArchitectureModel, EAElement


def calculate_risk_level(alert_severity: str, element_criticality: str) -> str:
    """Calculate a simple risk level from alert severity and EA criticality"""

    severity = alert_severity.strip().lower()
    criticality = element_criticality.strip().lower()
    matrix = {
        ("critical", "high"): "critical",
        ("critical", "medium"): "high",
        ("warning", "high"): "high",
        ("warning", "medium"): "medium",
        ("info", "high"): "medium",
    }
    return matrix.get((severity, criticality), "low")


def build_element_index(architecture_model: ArchitectureModel) -> dict[str, EAElement]:
    """Build an element lookup by EA element id"""

    return {element.id: element for element in architecture_model.elements}


def find_elements_by_type(architecture_model: ArchitectureModel, element_type: str) -> list[EAElement]:
    """Find all EA elements with the given type"""

    expected_type = element_type.lower()
    return [element for element in architecture_model.elements if element.type.lower() == expected_type]


def find_elements_by_layer(architecture_model: ArchitectureModel, layer: str) -> list[EAElement]:
    """Find all EA elements in the given layer"""

    expected_layer = layer.lower()
    return [element for element in architecture_model.elements if element.layer.lower() == expected_layer]


def find_related_elements_by_type(
    architecture_model: ArchitectureModel,
    element: EAElement,
    element_type: str,
) -> list[EAElement]:
    """Find directly related EA elements with the given type"""

    expected_type = element_type.lower()
    return [related for related in _resolve_related_elements(architecture_model, element) if related.type.lower() == expected_type]


def find_related_elements_by_layer(
    architecture_model: ArchitectureModel,
    element: EAElement,
    layer: str,
) -> list[EAElement]:
    """Find directly related EA elements in the given layer"""

    expected_layer = layer.lower()
    return [related for related in _resolve_related_elements(architecture_model, element) if related.layer.lower() == expected_layer]


def _resolve_related_elements(architecture_model: ArchitectureModel, element: EAElement) -> list[EAElement]:
    element_index = build_element_index(architecture_model)
    return [element_index[element_id] for element_id in element.related_elements if element_id in element_index]
