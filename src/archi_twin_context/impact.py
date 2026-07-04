from __future__ import annotations

from dataclasses import dataclass

from .models import ArchitectureModel, EAElement, ImpactTreeNode


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


def build_impact_tree(architecture_model: ArchitectureModel, root_element: EAElement) -> ImpactTreeNode:
    """Traverse all reachable architecture relationships from the mapped element"""

    element_index = build_element_index(architecture_model)
    adjacency = _build_traversal_adjacency(architecture_model)
    visited = {root_element.id}
    return _build_impact_tree_node(root_element, None, element_index, adjacency, visited)


def flatten_impact_tree(root: ImpactTreeNode) -> list[ImpactTreeNode]:
    """Return each non-cycle tree node in traversal order"""

    nodes = [root]
    for child in root.children:
        if not child.cycle:
            nodes.extend(flatten_impact_tree(child))
    return nodes


@dataclass(frozen=True)
class _TraversalEdge:
    relationship_id: str | None
    relationship_type: str
    neighbor_id: str
    direction: str


def _build_traversal_adjacency(architecture_model: ArchitectureModel) -> dict[str, list[_TraversalEdge]]:
    adjacency: dict[str, list[_TraversalEdge]] = {element.id: [] for element in architecture_model.elements}
    explicit_pairs: set[tuple[str, str]] = set()

    for relationship in architecture_model.relationships:
        adjacency.setdefault(relationship.source_id, []).append(
            _TraversalEdge(
                relationship_id=relationship.id,
                relationship_type=relationship.type,
                neighbor_id=relationship.target_id,
                direction="outgoing",
            )
        )
        adjacency.setdefault(relationship.target_id, []).append(
            _TraversalEdge(
                relationship_id=relationship.id,
                relationship_type=relationship.type,
                neighbor_id=relationship.source_id,
                direction="incoming",
            )
        )
        explicit_pairs.add((relationship.source_id, relationship.target_id))
        explicit_pairs.add((relationship.target_id, relationship.source_id))

    for element in architecture_model.elements:
        for related_id in element.related_elements:
            if related_id not in adjacency or (element.id, related_id) in explicit_pairs:
                continue
            adjacency[element.id].append(
                _TraversalEdge(
                    relationship_id=None,
                    relationship_type="Related",
                    neighbor_id=related_id,
                    direction="undirected",
                )
            )

        for supported_id in _supported_context_ids(element):
            if supported_id not in adjacency or (element.id, supported_id) in explicit_pairs:
                continue
            adjacency[element.id].append(
                _TraversalEdge(
                    relationship_id=None,
                    relationship_type="Supports",
                    neighbor_id=supported_id,
                    direction="outgoing",
                )
            )

    for edges in adjacency.values():
        edges.sort(key=lambda edge: (edge.relationship_type, edge.neighbor_id))

    return adjacency


def _supported_context_ids(element: EAElement) -> list[str]:
    return (
        element.supported_capabilities
        + element.supported_processes
        + element.supported_applications
    )


def _build_impact_tree_node(
    element: EAElement,
    via_edge: _TraversalEdge | None,
    element_index: dict[str, EAElement],
    adjacency: dict[str, list[_TraversalEdge]],
    visited: set[str],
) -> ImpactTreeNode:
    children: list[ImpactTreeNode] = []
    for edge in adjacency.get(element.id, []):
        child_element = element_index.get(edge.neighbor_id)
        if child_element is None:
            continue

        if child_element.id in visited:
            children.append(_impact_tree_node(child_element, edge, cycle=True))
            continue

        visited.add(child_element.id)
        children.append(_build_impact_tree_node(child_element, edge, element_index, adjacency, visited))

    return ImpactTreeNode(
        element_id=element.id,
        name=element.name,
        type=element.type,
        layer=element.layer,
        relationship_id=via_edge.relationship_id if via_edge else None,
        relationship_type=via_edge.relationship_type if via_edge else None,
        direction=via_edge.direction if via_edge else None,
        children=children,
    )


def _impact_tree_node(element: EAElement, edge: _TraversalEdge, cycle: bool) -> ImpactTreeNode:
    return ImpactTreeNode(
        element_id=element.id,
        name=element.name,
        type=element.type,
        layer=element.layer,
        relationship_id=edge.relationship_id,
        relationship_type=edge.relationship_type,
        direction=edge.direction,
        cycle=cycle,
    )
