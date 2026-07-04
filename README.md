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
- A YAML architecture model or an XSD-validated ArchiMate Model Exchange XML file

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

Run the Docker-based demo production simulation:

```bash
docker compose -f demo/docker-compose.yml up --build
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

Use an ArchiMate Model Exchange XML file with XSD validation:

```bash
archi-twin-context enrich \
  --alert examples/alert_machine_vibration.json \
  --mapping examples/twin_architecture_mapping_manufacturing.yaml \
  --model examples/manufacturing_archimate_model.xml \
  --model-format archimate-xml \
  --xsd xsd/archimate3_Diagram.xsd \
  --report reports/alert_machine_vibration_report.md
```

The bundled example includes `views/diagrams` and validates against the official Open Group ArchiMate Model Exchange XSD files under `xsd/`. Use `xsd/archimate3_Diagram.xsd` when validating models with diagram views.

Run the PostgreSQL-backed demo fountain and enrichment engine with Docker Compose:

```bash
docker compose -f demo/docker-compose.yml up --build
```

The demo Compose setup starts:

- `postgres`: queue and storage for simulated Digital Twin alerts and enriched results
- `twin-fountain`: random but plausible abnormal production events for testing
- `enrichment-engine`: polling worker that enriches new alerts with the ArchiMate XML model

The fountain is deliberately demo infrastructure under `demo/`, not core product logic. It treats `running` as the implicit normal state and only writes events when a machine enters an abnormal state such as `warning`, `fault`, `idle` or `maintenance`.

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

Version 0.2 supports additional mapping confidence fields for ArchiMate XML imports:

```yaml
assets:
  - asset_id: cnc-01
    ea_element_id: dt-cnc-machine-01
    archimate_element_id: equipment-cnc-01
    match_name: CNC Milling Machine 01
    match_tags:
      - cnc
      - machine
      - production
    default_bpmn_process: handle-critical-equipment-anomaly
    owner: Maintenance Department
```

The resolver first tries `archimate_element_id`, then `ea_element_id`, then a name/tag fallback. If `match_name` or `match_tags` are present, they are used as verification constraints.

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

### ArchiMate Model Exchange XML

Version 0.2 can import ArchiMate Model Exchange XML. XML files are validated against an XSD before import. The importer reads:

- `elements/element` with `identifier` and `xsi:type`
- `name` and `documentation`
- `properties` for `owner`, `criticality` and `tags`
- `relationships/relationship` with `source`, `target` and `xsi:type`

The XML is normalized into the internal `ArchitectureModel`, so the enrichment and report flow stays the same for YAML and XML models.

### PostgreSQL Runtime Storage

Version 0.3 adds a small Docker-based demo runtime. PostgreSQL stores simulated Digital Twin events, pending alerts and dashboard-ready enrichment results.

Core tables:

- `assets`: production assets and current abnormal status
- `twin_events`: abnormal event history from the fountain
- `twin_alerts`: queue table processed by the enrichment engine
- `enriched_alerts`: structured enrichment results with JSONB impact data

Markdown is not persisted as the primary output. The engine stores structured fields and JSONB so a later dashboard can filter by asset, severity, risk level, owner, process recommendation and impact tree.

## Roadmap

### Version 0.1

- Read JSON alerts
- Read YAML mappings
- Read YAML EA models
- Enrich alerts with EA context
- Generate Markdown reports
- Recommend BPMN processes

### Version 0.2

- Validate and import ArchiMate Model Exchange XML
- Support ArchiMate element IDs in asset mappings
- Verify mappings with optional name/tag constraints
- Traverse all modeled relationship types with cycle protection
- Render an impact tree in Markdown reports

### Version 0.3

- Add PostgreSQL-backed alert queue and result store
- Add Docker Compose runtime
- Add demo Digital Twin fountain with plausible random abnormal events
- Add standalone enrichment engine with polling source
- Store dashboard-ready enrichment results as structured columns and JSONB

### Version 0.3.1

- Move the demo fountain and demo Docker Compose setup under `demo/`
- Add explicit source and sink adapter contracts
- Isolate PostgreSQL polling and result persistence behind an adapter
- Keep the core CLI focused on enrichment and engine execution

### Version 0.4

- Add FastAPI webhook for Digital Twin alerts
- Add event-source adapter for the enrichment engine
- Add dashboard API for assets, alerts and impact results

### Version 0.5

- Add MQTT input
- Prepare event streaming support

### Version 0.6

- Add Camunda integration
- Trigger BPMN message events
- Start process instances with enriched context

### Version 0.7

- Visualize the impact graph
- Export GraphML or Mermaid
- Generate architecture traceability reports

## Limits Of The MVP

- No real Digital Twin integration
- No real MQTT integration
- No Camunda integration
- No web server
- No UI

The MVP stays small on purpose. It focuses on local enrichment, explainable impact analysis, XSD-validated ArchiMate XML imports and a lightweight PostgreSQL-backed simulation runtime.

## Contributing

Contributions are welcome. Keep changes small, typed and tested. Prefer simple local workflows over framework-heavy additions.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
