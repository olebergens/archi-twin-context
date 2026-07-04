from __future__ import annotations

from .impact import (
    build_element_index,
    build_impact_tree,
    calculate_risk_level,
    flatten_impact_tree,
)
from .models import ArchitectureModel, AssetMapping, DigitalTwinAlert, EAElement, EnrichedAlert, ImpactTreeNode
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

    mapped_element, mapping_trace = _resolve_mapped_element(mapping, architecture_model)

    impact_tree = build_impact_tree(architecture_model, mapped_element)
    business_impact = _collect_business_impact(impact_tree)
    recommended_owner = mapping.owner or mapped_element.owner or "Unknown"
    recommended_process = recommend_bpmn_process(alert, mapping, mapped_element)
    risk_level = calculate_risk_level(alert.severity, mapped_element.criticality)
    trace = _build_trace(
        alert,
        mapping,
        mapped_element,
        business_impact,
        recommended_process,
        risk_level,
        mapping_trace,
        impact_tree,
    )

    return EnrichedAlert(
        alert=alert,
        mapped_element=mapped_element,
        business_impact=business_impact,
        recommended_bpmn_process=recommended_process,
        recommended_owner=recommended_owner,
        risk_level=risk_level,
        impact_tree=impact_tree,
        trace=trace,
    )


def _resolve_mapped_element(
    mapping: AssetMapping,
    architecture_model: ArchitectureModel,
) -> tuple[EAElement, list[str]]:
    element_index = build_element_index(architecture_model)
    trace: list[str] = []
    candidate_ids = _unique_strings(
        [
            candidate_id
            for candidate_id in [mapping.archimate_element_id, mapping.ea_element_id]
            if candidate_id
        ]
    )

    for candidate_id in candidate_ids:
        candidate = element_index.get(candidate_id)
        if candidate is None:
            continue

        _verify_mapping_constraints(mapping, candidate)
        trace.append(f"Resolved EA element by explicit id {candidate_id}.")
        if mapping.match_name or mapping.match_tags:
            trace.append("Verified explicit mapping with name/tag constraints.")
        return candidate, trace

    candidates = _find_elements_by_name_and_tags(architecture_model, mapping)
    if len(candidates) == 1:
        candidate = candidates[0]
        trace.append(f"Resolved EA element by name/tag match {candidate.id}.")
        return candidate, trace

    if len(candidates) > 1:
        candidate_list = ", ".join(candidate.id for candidate in candidates)
        raise ValueError(
            f"Mapping for asset_id '{mapping.asset_id}' is ambiguous; "
            f"name/tag constraints match: {candidate_list}"
        )

    raise ValueError(
        f"Mapping for asset_id '{mapping.asset_id}' could not be resolved. "
        f"Tried ids: {', '.join(candidate_ids) or 'none'}"
    )


def _verify_mapping_constraints(mapping: AssetMapping, element: EAElement) -> None:
    if mapping.match_name and mapping.match_name.casefold() != element.name.casefold():
        raise ValueError(
            f"Mapping for asset_id '{mapping.asset_id}' resolved element '{element.id}', "
            f"but expected name '{mapping.match_name}' and found '{element.name}'"
        )

    missing_tags = _missing_match_tags(mapping.match_tags, element.tags)
    if missing_tags:
        raise ValueError(
            f"Mapping for asset_id '{mapping.asset_id}' resolved element '{element.id}', "
            f"but required tags are missing: {', '.join(missing_tags)}"
        )


def _find_elements_by_name_and_tags(
    architecture_model: ArchitectureModel,
    mapping: AssetMapping,
) -> list[EAElement]:
    if not mapping.match_name and not mapping.match_tags:
        return []

    candidates: list[EAElement] = []
    for element in architecture_model.elements:
        if mapping.match_name and mapping.match_name.casefold() != element.name.casefold():
            continue
        if _missing_match_tags(mapping.match_tags, element.tags):
            continue
        candidates.append(element)
    return candidates


def _missing_match_tags(required_tags: list[str], actual_tags: list[str]) -> list[str]:
    actual = {tag.casefold() for tag in actual_tags}
    return [tag for tag in required_tags if tag.casefold() not in actual]


def _collect_business_impact(impact_tree: ImpactTreeNode) -> dict[str, list[str]]:
    elements = flatten_impact_tree(impact_tree)
    capabilities = [node.name for node in elements if _is_capability(node.type)]
    processes = [node.name for node in elements if node.type == "BusinessProcess"]
    applications = [node.name for node in elements if node.layer == "Application"]
    technology_nodes = [node.name for node in elements if node.layer == "Technology"]

    return {
        "business_capabilities": _unique_strings(capabilities),
        "business_processes": _unique_strings(processes),
        "application_components": _unique_strings(applications),
        "technology_nodes": _unique_strings(technology_nodes),
    }


def _build_trace(
    alert: DigitalTwinAlert,
    mapping: AssetMapping,
    mapped_element: EAElement,
    business_impact: dict[str, list[str]],
    recommended_process: str | None,
    risk_level: str,
    mapping_trace: list[str],
    impact_tree: ImpactTreeNode,
) -> list[str]:
    trace = [
        f"Received alert {alert.alert_id} for asset {alert.asset_id}.",
        f"Mapped asset {mapping.asset_id} to EA element {mapped_element.id}.",
    ]
    trace.extend(mapping_trace)

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
    trace.append(f"Traversed architecture impact graph across {len(flatten_impact_tree(impact_tree))} elements.")
    if recommended_process:
        trace.append(f"Recommended BPMN process {recommended_process}.")
    else:
        trace.append("No BPMN process recommendation matched this alert.")

    return trace


def _is_capability(element_type: str) -> bool:
    return element_type in {"BusinessCapability", "Capability"}


def _unique_strings(values: list[str]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        if value not in unique_values:
            unique_values.append(value)
    return unique_values
