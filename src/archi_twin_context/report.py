from __future__ import annotations

from pathlib import Path

from .models import EnrichedAlert, ImpactTreeNode


def render_markdown_report(enriched_alert: EnrichedAlert) -> str:
    """Render an enriched alert as a Markdown impact report"""

    alert = enriched_alert.alert
    element = enriched_alert.mapped_element

    lines = [
        "# Digital Twin Alert Impact Report",
        "",
        "## Alert",
        f"- Alert ID: {alert.alert_id}",
        f"- Asset ID: {alert.asset_id}",
        f"- Alert Type: {alert.alert_type}",
        f"- Severity: {alert.severity}",
        f"- Value: {_format_value(alert.value, alert.unit)}",
        f"- Timestamp: {alert.timestamp}",
        f"- Message: {_format_optional(alert.message)}",
        "",
        "## Mapped Architecture Context",
        f"- EA Element: {element.name} ({element.id})",
        f"- Type: {element.type}",
        f"- Layer: {element.layer}",
        f"- Criticality: {element.criticality}",
        f"- Owner: {_format_optional(element.owner)}",
        "",
        "## Business Impact",
        f"- Affected Business Capabilities: {_format_list(enriched_alert.business_impact['business_capabilities'])}",
        f"- Affected Business Processes: {_format_list(enriched_alert.business_impact['business_processes'])}",
        f"- Affected Applications: {_format_list(enriched_alert.business_impact['application_components'])}",
        f"- Affected Technology Nodes: {_format_list(enriched_alert.business_impact['technology_nodes'])}",
        "",
        "## Impact Tree",
    ]

    if enriched_alert.impact_tree:
        lines.extend(_render_impact_tree(enriched_alert.impact_tree))
    else:
        lines.append("- None")

    lines.extend([
        "",
        "## Recommendation",
        f"- Risk Level: {enriched_alert.risk_level}",
        f"- Recommended Owner: {enriched_alert.recommended_owner}",
        f"- Recommended BPMN Process: {_format_optional(enriched_alert.recommended_bpmn_process)}",
        "",
        "## Trace",
    ])

    for index, trace_entry in enumerate(enriched_alert.trace, start=1):
        lines.append(f"{index}. {trace_entry}")

    return "\n".join(lines) + "\n"


def write_markdown_report(enriched_alert: EnrichedAlert, output_path: Path) -> Path:
    """Write a Markdown impact report and return the written path"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_markdown_report(enriched_alert), encoding="utf-8")
    return output_path


def _format_value(value: float | int | str | None, unit: str | None) -> str:
    if value is None:
        return "None"
    if unit:
        return f"{value} {unit}"
    return str(value)


def _format_optional(value: str | None) -> str:
    return value if value else "None"


def _format_list(values: list[str]) -> str:
    return ", ".join(values) if values else "None"


def _render_impact_tree(node: ImpactTreeNode, depth: int = 0) -> list[str]:
    indent = "  " * depth
    relationship = ""
    if node.relationship_type:
        direction = f" {node.direction}" if node.direction else ""
        relationship = f"{node.relationship_type}{direction} -> "

    cycle = " (already visited)" if node.cycle else ""
    lines = [f"{indent}- {relationship}{node.name} [{node.type} / {node.layer}]{cycle}"]
    if node.cycle:
        return lines

    for child in node.children:
        lines.extend(_render_impact_tree(child, depth + 1))
    return lines
