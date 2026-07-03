# archi-twin-context

`archi-twin-context` is a small Python CLI tool that enriches Digital Twin alerts with Enterprise Architecture context.

It demonstrates how operational events from a Digital Twin can be connected with business, process, application and technology context from Enterprise Architecture or ArchiMate-style models.

## Why This Project?

Digital Twins are strong at representing assets, sensors, states, telemetry, events and alerts. Enterprise Architecture models are strong at explaining business capabilities, processes, applications, technology nodes, ownership and criticality.

In practice, operations teams often need both perspectives at the same time. A technical alert is easier to act on when it includes business impact, affected applications, responsible teams and a recommended process action.

This project is not a replacement for Digital Twin platforms or EA tools. It is a small context bridge between Digital Twin events and Enterprise Architecture information.

## What The Tool Does

The CLI reads a Digital Twin alert, maps the affected asset to an EA element, enriches the alert with architecture context, calculates a simple risk level and recommends a BPMN process action.

Core flow:

```text
Digital Twin Alert
        ↓
Asset-to-EA Mapping
        ↓
Architecture Context
        ↓
Impact Analysis
        ↓
BPMN Process Recommendation
```

## Architecture Idea

The MVP uses three local input files:

- A JSON alert from a Digital Twin-like source
- A YAML mapping between Digital Twin assets and EA elements
- A YAML architecture model with business, application and technology elements

The runtime flow is intentionally simple:

```text
Digital Twin Alert -> EA Context Enrichment -> Impact Report -> BPMN Process Recommendation
```

The tool keeps a trace of the enrichment steps so the generated report remains explainable.

## Installation

```bash
python -m pip install -e .
```

For local development and tests:

```bash
python -m pip install -e ".[dev]"
```

## Local Development

Run the test suite:

```bash
pytest
```

Run the CLI from the repository root after installing in editable mode:

```bash
archi-twin-context enrich --help
```

## Example Usage

```bash
archi-twin-context enrich \
  --alert examples/alert_temperature_high.json \
  --mapping examples/twin_architecture_mapping.yaml \
  --model examples/architecture_model.yaml \
  --report reports/alert_temperature_high_report.md
```

Print the enriched result as JSON as well:

```bash
archi-twin-context enrich \
  --alert examples/alert_network_latency.json \
  --mapping examples/twin_architecture_mapping.yaml \
  --model examples/architecture_model.yaml \
  --json
```

## Example Output

```text
Alert enriched successfully.

Alert: temperature_high
Asset: boiler-17
Mapped EA Element: Heating Control Unit
Risk Level: critical
Recommended Owner: Facility Operations Team
Recommended BPMN Process: handle-critical-equipment-anomaly
Report written to reports/alert_temperature_high_report.md
```

## Data Formats

### Alert JSON

```json
{
  "alert_id": "alert-001",
  "asset_id": "boiler-17",
  "alert_type": "temperature_high",
  "severity": "critical",
  "value": 91.4,
  "unit": "celsius",
  "timestamp": "2026-07-03T12:00:00Z",
  "message": "Temperature threshold exceeded on Boiler 17."
}
```

### Asset-to-EA Mapping YAML

```yaml
assets:
  - asset_id: boiler-17
    ea_element_id: tech-heating-control-unit
    default_bpmn_process: handle-critical-equipment-anomaly
    owner: Facility Operations Team
```

### Architecture Model YAML

```yaml
elements:
  - id: tech-heating-control-unit
    name: Heating Control Unit
    type: TechnologyNode
    layer: Technology
    criticality: high
    owner: Facility Operations Team
    related_elements:
      - app-maintenance-management-system
      - cap-facility-operations
    supported_capabilities:
      - cap-facility-operations
    supported_processes:
      - proc-equipment-incident-handling
    supported_applications:
      - app-maintenance-management-system
    tags:
      - heating
      - sensor
```
