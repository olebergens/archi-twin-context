from __future__ import annotations

from .models import AssetMapping, DigitalTwinAlert, EAElement


def recommend_bpmn_process(
    alert: DigitalTwinAlert,
    mapping: AssetMapping,
    mapped_element: EAElement,
) -> str | None:
    """Recommend a BPMN process for an enriched Digital Twin alert"""

    if mapping.default_bpmn_process:
        return mapping.default_bpmn_process

    process_rules = {
        "temperature_high": "handle-equipment-anomaly",
        "network_latency_high": "investigate-connectivity-issue",
        "availability_low": "handle-service-degradation",
    }
    return process_rules.get(alert.alert_type)
