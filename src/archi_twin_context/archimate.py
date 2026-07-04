from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree

from pydantic import ValidationError

from .models import ArchitectureModel, EAElement, EARelationship

ARCHIMATE_NS = "http://www.opengroup.org/xsd/archimate/3.0/"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
NS = {"a": ARCHIMATE_NS}

BUSINESS_TYPES = {
    "BusinessActor",
    "BusinessRole",
    "BusinessCollaboration",
    "BusinessInterface",
    "BusinessProcess",
    "BusinessFunction",
    "BusinessInteraction",
    "BusinessEvent",
    "BusinessService",
    "BusinessObject",
    "Contract",
    "Representation",
    "Product",
}
APPLICATION_TYPES = {
    "ApplicationComponent",
    "ApplicationCollaboration",
    "ApplicationInterface",
    "ApplicationFunction",
    "ApplicationInteraction",
    "ApplicationProcess",
    "ApplicationEvent",
    "ApplicationService",
    "DataObject",
}
TECHNOLOGY_TYPES = {
    "Node",
    "Device",
    "SystemSoftware",
    "TechnologyCollaboration",
    "TechnologyInterface",
    "Path",
    "CommunicationNetwork",
    "TechnologyFunction",
    "TechnologyProcess",
    "TechnologyInteraction",
    "TechnologyEvent",
    "TechnologyService",
    "Artifact",
    "Equipment",
    "Facility",
    "DistributionNetwork",
    "Material",
    "TechnologyNode",
}
MOTIVATION_TYPES = {
    "Stakeholder",
    "Driver",
    "Assessment",
    "Goal",
    "Outcome",
    "Principle",
    "Requirement",
    "Constraint",
    "Meaning",
    "Value",
}
STRATEGY_TYPES = {"Resource", "Capability", "CourseOfAction", "ValueStream", "BusinessCapability"}
IMPLEMENTATION_TYPES = {"WorkPackage", "Deliverable", "ImplementationEvent", "Plateau", "Gap"}


def load_archimate_model_exchange(path: Path, xsd_path: Path) -> ArchitectureModel:
    """Validate and load an ArchiMate Model Exchange XML file"""

    _ensure_readable_file(path, "ArchiMate XML")
    _ensure_readable_file(xsd_path, "ArchiMate XSD")
    _validate_xml(path, xsd_path)

    try:
        root = ElementTree.parse(path).getroot()
    except ElementTree.ParseError as exc:
        raise ValueError(f"Invalid ArchiMate XML file {path}: {exc}") from exc

    if _local_name(root.tag) != "model":
        raise ValueError(f"Invalid ArchiMate XML file {path}: expected root element 'model'")

    property_definitions = _read_property_definitions(root)
    element_data = _read_elements(root, property_definitions)
    relationships = _read_relationships(root)
    _apply_relationship_context(element_data, relationships)

    try:
        return ArchitectureModel(
            elements=[EAElement(**data) for data in element_data.values()],
            relationships=relationships,
        )
    except ValidationError as exc:
        raise ValueError(f"Invalid ArchiMate model content in {path}: {exc}") from exc


def _validate_xml(path: Path, xsd_path: Path) -> None:
    try:
        import xmlschema
    except ImportError as exc:
        raise RuntimeError(
            "ArchiMate XML validation requires the 'xmlschema' package. "
            "Install the project with python -m pip install -e '.[dev]'."
        ) from exc

    try:
        schema = xmlschema.XMLSchema(str(xsd_path))
        schema.validate(str(path))
    except Exception as exc:
        raise ValueError(f"ArchiMate XML file {path} does not validate against XSD {xsd_path}: {exc}") from exc


def _read_property_definitions(root: ElementTree.Element) -> dict[str, str]:
    definitions: dict[str, str] = {}
    for property_definition in root.findall(".//a:propertyDefinition", NS):
        identifier = property_definition.get("identifier")
        name = _first_child_text(property_definition, "name")
        if identifier and name:
            definitions[identifier] = _normalize_property_name(name)
    return definitions


def _read_elements(
    root: ElementTree.Element,
    property_definitions: dict[str, str],
) -> dict[str, dict[str, object]]:
    elements_node = root.find("a:elements", NS)
    if elements_node is None:
        raise ValueError("Invalid ArchiMate XML file: expected 'elements' container")

    elements: dict[str, dict[str, object]] = {}
    for element in elements_node.findall("a:element", NS):
        identifier = element.get("identifier")
        if not identifier:
            raise ValueError("Invalid ArchiMate XML file: element without identifier")

        element_type = _read_xsi_type(element)
        properties = _read_properties(element, property_definitions)
        tags = _split_list_property(properties.get("tags"))
        tags.extend(_split_list_property(properties.get("tag")))

        elements[identifier] = {
            "id": identifier,
            "name": _first_child_text(element, "name") or identifier,
            "type": element_type,
            "layer": _layer_for_type(element_type),
            "description": _first_child_text(element, "documentation"),
            "criticality": properties.get("criticality") or "medium",
            "owner": properties.get("owner"),
            "related_elements": [],
            "supported_capabilities": [],
            "supported_processes": [],
            "supported_applications": [],
            "tags": _unique_strings(tags),
        }

    return elements


def _read_relationships(root: ElementTree.Element) -> list[EARelationship]:
    relationships_node = root.find("a:relationships", NS)
    if relationships_node is None:
        return []

    relationships: list[EARelationship] = []
    for relationship in relationships_node.findall("a:relationship", NS):
        identifier = relationship.get("identifier")
        source_id = relationship.get("source")
        target_id = relationship.get("target")
        if not identifier or not source_id or not target_id:
            raise ValueError("Invalid ArchiMate XML file: relationship requires identifier, source and target")

        relationships.append(
            EARelationship(
                id=identifier,
                type=_read_xsi_type(relationship),
                source_id=source_id,
                target_id=target_id,
                name=_first_child_text(relationship, "name"),
                description=_first_child_text(relationship, "documentation"),
            )
        )

    return relationships


def _apply_relationship_context(
    element_data: dict[str, dict[str, object]],
    relationships: list[EARelationship],
) -> None:
    for relationship in relationships:
        source = element_data.get(relationship.source_id)
        target = element_data.get(relationship.target_id)
        if source is None or target is None:
            continue

        _append_unique(source["related_elements"], relationship.target_id)
        _append_unique(target["related_elements"], relationship.source_id)
        _append_supported_context(source, target)
        _append_supported_context(target, source)


def _append_supported_context(element: dict[str, object], related_element: dict[str, object]) -> None:
    related_id = str(related_element["id"])
    related_type = str(related_element["type"])
    related_layer = str(related_element["layer"])

    if _is_capability_type(related_type):
        _append_unique(element["supported_capabilities"], related_id)
    if related_type == "BusinessProcess":
        _append_unique(element["supported_processes"], related_id)
    if related_layer == "Application":
        _append_unique(element["supported_applications"], related_id)


def _read_properties(
    element: ElementTree.Element,
    property_definitions: dict[str, str],
) -> dict[str, str]:
    properties: dict[str, str] = {}
    properties_node = element.find("a:properties", NS)
    if properties_node is None:
        return properties

    for property_node in properties_node.findall("a:property", NS):
        definition_ref = property_node.get("propertyDefinitionRef")
        if not definition_ref:
            continue

        key = property_definitions.get(definition_ref, definition_ref)
        values = [
            _text(value_node)
            for value_node in property_node.findall("a:value", NS)
            if _text(value_node)
        ]
        if values:
            properties[_normalize_property_name(key)] = ", ".join(values)

    return properties


def _read_xsi_type(element: ElementTree.Element) -> str:
    raw_type = element.get(f"{{{XSI_NS}}}type") or element.get("type")
    if not raw_type:
        raise ValueError(f"Invalid ArchiMate XML file: '{_local_name(element.tag)}' is missing xsi:type")
    return raw_type.split(":")[-1]


def _first_child_text(element: ElementTree.Element, child_name: str) -> str | None:
    child = element.find(f"a:{child_name}", NS)
    if child is None:
        return None
    return _text(child)


def _text(element: ElementTree.Element) -> str | None:
    if element.text is None:
        return None
    value = element.text.strip()
    return value or None


def _split_list_property(value: str | None) -> list[str]:
    if not value:
        return []

    parts = value.replace(";", ",").split(",")
    return [part.strip() for part in parts if part.strip()]


def _layer_for_type(element_type: str) -> str:
    if element_type in BUSINESS_TYPES:
        return "Business"
    if element_type in APPLICATION_TYPES:
        return "Application"
    if element_type in TECHNOLOGY_TYPES:
        return "Technology"
    if element_type in MOTIVATION_TYPES:
        return "Motivation"
    if element_type in STRATEGY_TYPES:
        return "Strategy"
    if element_type in IMPLEMENTATION_TYPES:
        return "Implementation"
    return "Other"


def _is_capability_type(element_type: str) -> bool:
    return element_type in {"Capability", "BusinessCapability"}


def _normalize_property_name(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")


def _local_name(tag: str) -> str:
    return tag.rsplit("}", maxsplit=1)[-1]


def _append_unique(values: object, value: str) -> None:
    if not isinstance(values, list):
        return
    if value not in values:
        values.append(value)


def _unique_strings(values: list[str]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        if value not in unique_values:
            unique_values.append(value)
    return unique_values


def _ensure_readable_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label} file does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"{label} path is not a file: {path}")
