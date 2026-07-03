from __future__ import annotations

from .impact import (
    build_element_index,
    calculate_risk_level,
    find_related_elements_by_layer,
    find_related_elements_by_type,
)
from .models import ArchitectureModel, AssetMapping, DigitalTwinAlert, EAElement, EnrichedAlert
from .recommender import recommend_bpmn_process


def enrich_alert(
    alert: DigitalTwinAlert,
    mappings: dict[str, AssetMapping],
    architecture_model: ArchitectureModel,
) -> EnrichedAlert:
    """Enrich a Digital Twin alert with mapped Enterprise Architecture context"""

    mapping = mappings.get(alert.asset_id)
    if mapping is None:
        raise ValueError(f"No asset mapping found for asset_id '{alert.asset_id}'")

    element_index = build_element_index(architecture_model)
    mapped_element = element_index.get(mapping.ea_element_id)
    if mapped_element is None:
        raise ValueError(
            f"Mapping for asset_id '{alert.asset_id}' references unknown EA element "
            f"'{mapping.ea_element_id}'"
        )

    business_impact = _collect_business_impact(architecture_model, mapped_element)
    recommended_owner = mapping.owner or mapped_element.owner or "Unknown"
    recommended_process = recommend_bpmn_process(alert, mapping, mapped_element)
    risk_level = calculate_risk_level(alert.severity, mapped_element.criticality)
    trace = _build_trace(alert, mapping, mapped_element, business_impact, recommended_process, risk_level)

    return EnrichedAlert(
        alert=alert,
        mapped_element=mapped_element,
        business_impact=business_impact,
        recommended_bpmn_process=recommended_process,
        recommended_owner=recommended_owner,
        risk_level=risk_level,
        trace=trace,
    )


def _collect_business_impact(
    architecture_model: ArchitectureModel,
    mapped_element: EAElement,
) -> dict[str, list[str]]:
    element_index = build_element_index(architecture_model)

    capabilities = _unique_elements(
        _resolve_ids(element_index, mapped_element.supported_capabilities)
        + find_related_elements_by_type(architecture_model, mapped_element, "BusinessCapability")
        + _include_if_type(mapped_element, "BusinessCapability")
    )
    processes = _unique_elements(
        _resolve_ids(element_index, mapped_element.supported_processes)
        + find_related_elements_by_type(architecture_model, mapped_element, "BusinessProcess")
        + _include_if_type(mapped_element, "BusinessProcess")
    )
    applications = _unique_elements(
        _resolve_ids(element_index, mapped_element.supported_applications)
        + find_related_elements_by_type(architecture_model, mapped_element, "ApplicationComponent")
        + _include_if_type(mapped_element, "ApplicationComponent")
    )
    technology_nodes = _unique_elements(
        find_related_elements_by_type(architecture_model, mapped_element, "TechnologyNode")
        + find_related_elements_by_layer(architecture_model, mapped_element, "Technology")
        + _include_if_layer(mapped_element, "Technology")
    )

    return {
        "business_capabilities": [element.name for element in capabilities],
        "business_processes": [element.name for element in processes],
        "application_components": [element.name for element in applications],
        "technology_nodes": [element.name for element in technology_nodes],
    }


def _build_trace(
    alert: DigitalTwinAlert,
    mapping: AssetMapping,
    mapped_element: EAElement,
    business_impact: dict[str, list[str]],
    recommended_process: str | None,
    risk_level: str,
) -> list[str]:
    trace = [
        f"Received alert {alert.alert_id} for asset {alert.asset_id}.",
        f"Mapped asset {mapping.asset_id} to EA element {mapped_element.id}.",
    ]

    for capability in business_impact["business_capabilities"]:
        trace.append(f"Resolved affected business capability {capability}.")
    for process in business_impact["business_processes"]:
        trace.append(f"Resolved affected business process {process}.")
    for application in business_impact["application_components"]:
        trace.append(f"Resolved affected application {application}.")

    trace.append(
        f"Calculated risk level {risk_level} from severity {alert.severity} "
        f"and criticality {mapped_element.criticality}."
    )
    if recommended_process:
        trace.append(f"Recommended BPMN process {recommended_process}.")
    else:
        trace.append("No BPMN process recommendation matched this alert.")

    return trace


def _resolve_ids(element_index: dict[str, EAElement], element_ids: list[str]) -> list[EAElement]:
    return [element_index[element_id] for element_id in element_ids if element_id in element_index]


def _include_if_type(element: EAElement, element_type: str) -> list[EAElement]:
    if element.type.lower() == element_type.lower():
        return [element]
    return []


def _include_if_layer(element: EAElement, layer: str) -> list[EAElement]:
    if element.layer.lower() == layer.lower():
        return [element]
    return []


def _unique_elements(elements: list[EAElement]) -> list[EAElement]:
    seen_ids: set[str] = set()
    unique_elements: list[EAElement] = []
    for element in elements:
        if element.id not in seen_ids:
            seen_ids.add(element.id)
            unique_elements.append(element)
    return unique_elements
